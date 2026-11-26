# -*- coding: utf-8 -*-
"""接口桩：@require_permission + /__probe__ 探针（真实系统的接口尚未合并，按本单矩阵构造）。

约定：
  * 请求头 X-Staff-Id / X-Site-Id 表示「当前员工」与「当前会所上下文」；
  * 探针 /__probe__/{code} 返回判定结果，/__probe__/{code}/records 返回按范围过滤后的记录；
  * 一律先判站点（不在员工 sites 内 -> 403），再判角色权限，最后才是数据范围。
"""
from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from . import store as S
from .matrix import decide, load_matrix

MATRIX = load_matrix()
app = FastAPI(title="S2-IAM-024 stub · 会员经理越权回归", version="1.0.0")


def ctx(staff_id: str = Header(..., alias="X-Staff-Id"),
        site_id: str = Header(..., alias="X-Site-Id")) -> dict:
    me = S.STAFF.get(staff_id)
    if me is None:
        raise HTTPException(401, detail={"error": "unknown staff"})
    return {"staff": me, "site": site_id}


def require_permission(code: str):
    """依赖工厂：返回 FastAPI 依赖函数，未授权统一 403。"""
    def _dep(c: dict = Depends(ctx)):
        allow, scope, reason = decide(MATRIX, c["staff"]["role"], code, c["site"], c["staff"]["sites"])
        if not allow:
            raise HTTPException(403, detail={"error": "permission_denied", "code": code,
                                             "role": c["staff"]["role"],
                                             "site": c["site"], "reason": reason})
        c["scope"] = scope
        return c
    return _dep


ALIAS = {"crm.contact": "crm.member"}


def _dataset(code: str) -> list:
    key = code.rsplit(".", 1)[0] if code.count(".") >= 2 else code
    return S.DATASETS.get(ALIAS.get(key, key), [])


def _scoped(rows: list, c: dict) -> list:
    sc = c.get("scope")
    if sc == "org":
        return [r for r in rows if r["org_id"] == c["staff"]["org_id"]]
    if sc == "site":
        return [r for r in rows if r["site_id"] == c["site"]]
    return [r for r in rows if r["owner_id"] == c["staff"]["id"]]


@app.get("/healthz")
def healthz():
    return {"ok": True, "records": sum(len(v) for v in S.DATASETS.values())}


@app.get("/__probe__/{code}")
def probe(code: str, c: dict = Depends(ctx)):
    allow, scope, reason = decide(MATRIX, c["staff"]["role"], code, c["site"], c["staff"]["sites"])
    body = {"code": code, "role": c["staff"]["role"], "site": c["site"], "allow": allow, "scope": scope}
    if not allow:
        raise HTTPException(403, detail=dict(body, error="permission_denied", reason=reason))
    return body


@app.get("/__probe__/{code}/records")
def probe_records(code: str, c: dict = Depends(ctx)):
    allow, scope, reason = decide(MATRIX, c["staff"]["role"], code, c["site"], c["staff"]["sites"])
    if not allow:
        raise HTTPException(403, detail={"error": "permission_denied", "code": code, "reason": reason})
    c["scope"] = scope
    rows = _scoped(_dataset(code), c)
    return {"code": code, "scope": scope, "count": len(rows), "ids": [r["id"] for r in rows]}


class MemberPatch(BaseModel):
    owner_id: str | None = None
    level: str | None = None


@app.patch("/api/crm/members/{mid}")
def patch_member(mid: str, body: MemberPatch, c: dict = Depends(require_permission("crm.member.write"))):
    rec = next((r for r in S.MEMBERS if r["id"] == mid), None)
    if rec is None:
        raise HTTPException(404, detail={"error": "not found"})
    if c["scope"] == "self" and rec["owner_id"] != c["staff"]["id"]:
        raise HTTPException(404, detail={"error": "not found"})   # 越权读友商记录：不给存在性
    if body.owner_id and body.owner_id != rec["owner_id"]:
        raise HTTPException(403, detail={"error": "cannot change ownership", "field": "owner_id"})
    if body.level:
        rec["level"] = body.level
    return {"id": rec["id"], "owner_id": rec["owner_id"], "level": rec["level"]}


@app.get("/api/crm/members/{mid}/contact")
def member_contact(mid: str, c: dict = Depends(require_permission("crm.contact.read_sensitive"))):
    rec = next((r for r in S.MEMBERS if r["id"] == mid), None)
    if rec is None or (c["scope"] == "self" and rec["owner_id"] != c["staff"]["id"]):
        raise HTTPException(404, detail={"error": "not found"})
    return {"id": rec["id"], "phone": rec["phone"], "email": rec["email"]}
