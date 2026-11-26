# -*- coding: utf-8 -*-
"""pytest 夹具：TestClient + 角色矩阵 + 期望表。

角色：member_manager（site 级），被测员工只属于会所 A。
"""
from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from stubapp import store as S          # noqa: E402
from stubapp.main import app            # noqa: E402

ROLE = "member_manager"
SITE_A, SITE_B = "site-a", "site-b"

# 允许项：(code, 期望 scope)
ALLOW = [
    ("crm.member.read", "site"),
    ("event.read", "site"),
    ("space.booking.read", "site"),
    ("crm.member.write", "self"),
    ("crm.followup.write", "self"),
    ("crm.contact.read_sensitive", "self"),
    ("opp.demand.read", "self"),
    ("opp.demand.write", "self"),
    ("kb.article.read", "org"),
    ("ai.assistant.use", "self"),
]

# 禁止项：期望 403
DENY = [
    "crm.export", "opp.match.write", "opp.assign", "lead.prospect.read",
    "lead.assign", "front.visitor.write", "event.manage", "content.publish",
    "kb.article.publish", "dash.exec.read", "iam.user.read", "sys.config.manage",
]


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


def hdr(staff: str = S.ME, site: str = SITE_A) -> dict:
    return {"X-Staff-Id": staff, "X-Site-Id": site}


@pytest.fixture()
def as_me(client):
    """会所 A 上下文 + 会员经理本人。"""
    return lambda path, **kw: client.get(path, headers=hdr(), **kw)
