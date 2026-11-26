# -*- coding: utf-8 -*-
"""虚构夹具数据：1 个集团、会所 A/B、9 条会员记录（A 本人 3 / A 同事 3 / B 3）。

全部为虚构标识，无真实个人信息（姓名用「会员A01」式代号，手机号用 1380000xxxx 段）。
"""
from __future__ import annotations

import os

ORG = {"id": "org-fake-001", "name": "虚构商务会员空间集团"}
SITES = [{"id": "site-a", "name": "会所A", "org_id": ORG["id"]},
         {"id": "site-b", "name": "会所B", "org_id": ORG["id"]}]

ME = "staff-mm-001"          # 会员经理测试员（只在会所 A）
COLLEAGUE = "staff-mm-002"   # 会所 A 同事
SITE_B_OWNER = "staff-mm-003"

STAFF = {
    ME: {"id": ME, "name": "会员经理测试员（虚构）", "role": "member_manager",
         "org_id": ORG["id"], "sites": ["site-a"]},
    COLLEAGUE: {"id": COLLEAGUE, "name": "会所A同事（虚构）", "role": "member_manager",
                "org_id": ORG["id"], "sites": ["site-a"]},
    SITE_B_OWNER: {"id": SITE_B_OWNER, "name": "会所B会员经理（虚构）", "role": "member_manager",
                   "org_id": ORG["id"], "sites": ["site-b"]},
}

def _load(name: str) -> list:
    """从 fixtures/ 读（由 tools/gen_fixtures.py 生成；缺文件时回落内联构造）。"""
    import json
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures", name + ".json")
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return []


def _members():
    rows = _load("members")
    if rows:
        return rows
    rows = []
    n = 0
    for site, owner, tag in (("site-a", ME, "own"), ("site-a", COLLEAGUE, "peer"), ("site-b", SITE_B_OWNER, "b")):
        for i in range(3):
            n += 1
            rows.append({"id": f"mem-{n:03d}", "kind": "crm.member", "org_id": ORG["id"],
                         "site_id": site, "owner_id": owner, "tag": tag,
                         "name": f"会员{tag.upper()}{i+1:02d}（虚构）",
                         "phone": f"1380000{n:04d}", "email": f"fake{n:03d}@example.invalid",
                         "level": "gold" if i == 0 else "silver"})
    return rows

MEMBERS = _members()
DEMANDS = [
    {"id": "dem-001", "kind": "opp.demand", "org_id": ORG["id"], "site_id": "site-a", "owner_id": ME, "tag": "own"},
    {"id": "dem-002", "kind": "opp.demand", "org_id": ORG["id"], "site_id": "site-a", "owner_id": ME, "tag": "own"},
    {"id": "dem-003", "kind": "opp.demand", "org_id": ORG["id"], "site_id": "site-a", "owner_id": COLLEAGUE, "tag": "peer"},
    {"id": "dem-004", "kind": "opp.demand", "org_id": ORG["id"], "site_id": "site-b", "owner_id": SITE_B_OWNER, "tag": "b"},
]
FOLLOWUPS = [
    {"id": "fu-001", "kind": "crm.followup", "org_id": ORG["id"], "site_id": "site-a", "owner_id": ME, "tag": "own"},
    {"id": "fu-002", "kind": "crm.followup", "org_id": ORG["id"], "site_id": "site-a", "owner_id": ME, "tag": "own"},
    {"id": "fu-003", "kind": "crm.followup", "org_id": ORG["id"], "site_id": "site-a", "owner_id": COLLEAGUE, "tag": "peer"},
]
EVENTS = [{"id": f"ev-{i:03d}", "kind": "event", "org_id": ORG["id"], "site_id": "site-a", "owner_id": COLLEAGUE, "tag": "site"} for i in (1, 2)]
BOOKINGS = [{"id": f"bk-{i:03d}", "kind": "space.booking", "org_id": ORG["id"], "site_id": "site-a", "owner_id": ME, "tag": "site"} for i in (1, 2, 3)]
ARTICLES = [{"id": f"kb-{i:03d}", "kind": "kb.article", "org_id": ORG["id"], "site_id": "site-a", "owner_id": COLLEAGUE, "tag": "org"} for i in (1, 2)]

DATASETS = {
    "crm.member": MEMBERS,
    "crm.followup": _load("followups") or FOLLOWUPS,
    "opp.demand": _load("demands") or DEMANDS,
    "event": _load("events") or EVENTS,
    "space.booking": _load("bookings") or BOOKINGS,
    "kb.article": _load("articles") or ARTICLES,
}
