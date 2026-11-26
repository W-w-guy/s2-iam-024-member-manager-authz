# -*- coding: utf-8 -*-
"""权限内核（stub）：role_matrix + 角色/站点/归属三级判定。

判定顺序（写死，测试依赖它）：
  1) 站点校验：请求上下文 site_id 必须在该员工的 site 列表内，否则一律 403；
  2) 权限校验：code 必须在角色矩阵里，否则 403；
  3) 数据范围：site -> 本站全部；self -> 只 operator 本人；org -> 全组织；
     范围在 records 探针里体现为 WHERE，在写接口上体现为 404/403。
"""
from __future__ import annotations

import os
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
MATRIX_PATH = os.path.join(os.path.dirname(HERE), "role_matrix.yml")


def load_matrix(path: str | None = None) -> dict:
    with open(path or MATRIX_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def role_permissions(matrix: dict, role: str) -> dict:
    return (matrix.get("roles") or {}).get(role, {}).get("permissions") or {}


def decide(matrix: dict, role: str, code: str, req_site: str, user_sites: list[str]) -> tuple[bool, str, str]:
    """返回 (allow, scope, reason)。reason 用于失败信息打印。"""
    if req_site not in (user_sites or []):
        return False, "", f"site {req_site} not in user sites {user_sites}"
    perms = role_permissions(matrix, role)
    if code not in perms:
        return False, "", f"code {code} not granted to role {role}"
    scope = (perms[code] or {}).get("scope", "self")
    return True, scope, f"granted scope={scope}"
