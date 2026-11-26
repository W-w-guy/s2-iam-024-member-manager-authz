# -*- coding: utf-8 -*-
"""变异测试：把接口桩/矩阵改坏 N 处，每一处都必须让 pytest 变红。

为什么必须做：40 条用例全绿只能证明"当前实现符合期望"，不能证明"用例抓得住错"。
只有改坏能红，才能说明这些用例真的在判 403/404，而不是恒真。

用法：python tools/mutate_3007.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MUTATIONS = [
    ("矩阵错误授予 crm.export", "role_matrix.yml",
     "      kb.article.read: {scope: org}",
     "      kb.article.read: {scope: org}\n      crm.export: {scope: org}"),
    ("把 crm.member.read 范围从 site 改 self", "role_matrix.yml",
     "      crm.member.read: {scope: site}", "      crm.member.read: {scope: self}"),
    ("删掉站点校验（跨会所不再 403）", "stubapp/matrix.py",
     "    if req_site not in (user_sites or []):",
     "    if False and req_site not in (user_sites or []):"),
    ("PATCH 不再按范围隐藏同事记录", "stubapp/main.py",
     '    if c["scope"] == "self" and rec["owner_id"] != c["staff"]["id"]:',
     "    if False:"),
    ("允许把 owner_id 改成别人", "stubapp/main.py",
     '    if body.owner_id and body.owner_id != rec["owner_id"]:',
     "    if False:"),
    ("敏感字段接口不校验归属", "stubapp/main.py",
     '    if rec is None or (c["scope"] == "self" and rec["owner_id"] != c["staff"]["id"]):',
     "    if rec is None:"),
    ("矩阵漏掉 crm.member.write", "role_matrix.yml",
     "      crm.member.write: {scope: self}\n", ""),
]


def run_pytest(path: str) -> tuple[int, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = path
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x"], cwd=path,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main() -> int:
    rc, out = run_pytest(ROOT)
    ok0 = rc == 0
    print("[%s] 原件必须全绿" % (" OK " if ok0 else "FAIL"))
    if not ok0:
        print(out[-1200:])
        return 1
    bad = 0
    work = tempfile.mkdtemp(prefix="mut3007_")
    for i, (name, rel, old, new) in enumerate(MUTATIONS, 1):
        dst = os.path.join(work, "m%d" % i)
        shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(
            "__pycache__", ".pytest_cache", "report"))
        p = os.path.join(dst, rel)
        src = open(p, encoding="utf-8").read()
        if old not in src:
            print("[FAIL] 变异 %d「%s」锚点没命中（%s）" % (i, name, rel))
            bad += 1
            continue
        open(p, "w", encoding="utf-8").write(src.replace(old, new, 1))
        rc, out = run_pytest(dst)
        caught = rc != 0
        print("[%s] 变异 %d「%s」 -> %s" % (" OK " if caught else "FAIL", i, name,
                                           "被抓到" if caught else "竟然全绿，用例是假的"))
        if not caught:
            bad += 1
    print("\n变异副本留在：%s" % work)
    print("MUTATION %s（%d/%d 被抓到）" % ("PASS" if bad == 0 else "FAIL",
                                          len(MUTATIONS) - bad, len(MUTATIONS)))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
