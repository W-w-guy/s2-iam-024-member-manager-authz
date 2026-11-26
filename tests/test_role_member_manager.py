# -*- coding: utf-8 -*-
"""S2-IAM-024 会员经理越权回归：参数化用例。

失败信息统一打印「角色 / 权限点 / 期望 / 实际 / 判定依据」，
便于集成方在真实系统上直接定位。
"""
from __future__ import annotations

import pytest

from conftest import ALLOW, DENY, ROLE, SITE_A, SITE_B, hdr
from stubapp import store as S
from stubapp.matrix import load_matrix, role_permissions


@pytest.mark.parametrize("code,scope", ALLOW, ids=[c for c, _ in ALLOW])
def test_allow_codes_return_200(client, code, scope):
    r = client.get(f"/__probe__/{code}", headers=hdr())
    assert r.status_code == 200, (f"角色={ROLE} 权限点={code} 期望=200 实际={r.status_code} "
                                 f"响应={r.text[:200]}")
    body = r.json()
    assert body["allow"] is True
    assert body["scope"] == scope, f"权限点={code} 期望范围={scope} 实际范围={body['scope']}"
    assert body["role"] == ROLE
    assert body["site"] == SITE_A


@pytest.mark.parametrize("code", DENY, ids=DENY)
def test_deny_codes_return_403(client, code):
    r = client.get(f"/__probe__/{code}", headers=hdr())
    assert r.status_code == 403, (f"角色={ROLE} 权限点={code} 期望=403 实际={r.status_code} "
                                 f"响应={r.text[:200]}")
    det = r.json()["detail"]
    assert det["code"] == code
    # AC4：响应体 error 必须是 permission_denied（统一错误码，便于前端与网关判别）
    assert det["error"] == "permission_denied", f"{code} 的 error 应为 permission_denied，实际 {det.get('error')}"


def test_member_read_records_site_scope(client):
    r = client.get("/__probe__/crm.member.read/records", headers=hdr())
    assert r.status_code == 200, f"期望=200 实际={r.status_code}"
    body = r.json()
    assert body["scope"] == "site"
    assert body["count"] == 6, f"会所A 会员期望=6 实际={body['count']} ids={body['ids']}"
    assert sorted(body["ids"]) == [f"mem-{i:03d}" for i in range(1, 7)]


def test_member_write_records_self_only(client):
    r = client.get("/__probe__/crm.member.write/records", headers=hdr())
    assert r.status_code == 200
    body = r.json()
    assert body["scope"] == "self"
    assert body["count"] == 3, f"本人负责会员期望=3 实际={body['count']} ids={body['ids']}"
    assert sorted(body["ids"]) == ["mem-001", "mem-002", "mem-003"]


def test_patch_peer_member_returns_404(client):
    """同事负责的会员：不允许写，且不泄露记录存在性（404 而非 403）。"""
    peer = next(m for m in S.MEMBERS if m["tag"] == "peer")
    r = client.patch(f"/api/crm/members/{peer['id']}", json={"level": "diamond"}, headers=hdr())
    assert r.status_code == 404, (f"角色={ROLE} 记录={peer['id']}(同事) 期望=404 "
                                 f"实际={r.status_code} 响应={r.text[:200]}")


def test_patch_own_member_change_owner_returns_403(client):
    own = next(m for m in S.MEMBERS if m["tag"] == "own")
    r = client.patch(f"/api/crm/members/{own['id']}", json={"owner_id": S.COLLEAGUE}, headers=hdr())
    assert r.status_code == 403, (f"角色={ROLE} 记录={own['id']}(本人) 改 owner_id "
                                 f"期望=403 实际={r.status_code} 响应={r.text[:200]}")


def test_patch_own_member_level_returns_200(client):
    """正对照：本人记录改非归属字段必须成功，否则上面的 403 可能是"什么都写不了"。"""
    own = next(m for m in S.MEMBERS if m["tag"] == "own")
    r = client.patch(f"/api/crm/members/{own['id']}", json={"level": "diamond"}, headers=hdr())
    assert r.status_code == 200, f"期望=200 实际={r.status_code} 响应={r.text[:200]}"
    assert r.json()["level"] == "diamond"


def test_contact_sensitive_peer_returns_404(client):
    peer = next(m for m in S.MEMBERS if m["tag"] == "peer")
    r = client.get(f"/api/crm/members/{peer['id']}/contact", headers=hdr())
    assert r.status_code == 404, (f"角色={ROLE} 记录={peer['id']}(同事) 读敏感字段 "
                                 f"期望=404 实际={r.status_code}")


def test_contact_sensitive_own_returns_200(client):
    own = next(m for m in S.MEMBERS if m["tag"] == "own")
    r = client.get(f"/api/crm/members/{own['id']}/contact", headers=hdr())
    assert r.status_code == 200, f"期望=200 实际={r.status_code}"
    assert r.json()["phone"].startswith("1380000")


@pytest.mark.parametrize("code", [c for c, _ in ALLOW], ids=[c for c, _ in ALLOW])
def test_cross_site_all_allow_denied(client, code):
    """切到会所 B：员工不属于 B，全部允许项也必须 403。"""
    r = client.get(f"/__probe__/{code}", headers=hdr(site=SITE_B))
    assert r.status_code == 403, (f"角色={ROLE} 权限点={code} 上下文=会所B 期望=403 "
                                 f"实际={r.status_code} 响应={r.text[:200]}")


def test_matrix_declares_exactly_this_role():
    m = load_matrix()
    perms = role_permissions(m, ROLE)
    assert perms, f"角色矩阵缺 {ROLE}"
    for code, scope in ALLOW:
        assert code in perms, f"矩阵缺允许项 {code}"
        assert perms[code]["scope"] == scope, f"{code} 范围应为 {scope}"
    for code in DENY:
        assert code not in perms, f"矩阵错误地授予了禁止项 {code}"
    assert len(perms) == len(ALLOW), f"矩阵权限点数量应为 {len(ALLOW)}，实际 {len(perms)}"
