# -*- coding: utf-8 -*-
"""AC 校验器：一条命令复核本单全部验收点，任何一条不满足 -> 退出码 1。

用法：
  python verify_3007.py                # 全部（含变异测试）
  python verify_3007.py --no-mutate    # 跳过变异测试

对应工单 acceptance_criteria 四条：
  AC1 参数化用例覆盖 10 个允许项与 12 个禁止项，全部通过
  AC2 crm.member.read 探针 6 条、crm.member.write 探针只 3 条
  AC3 改同事记录 404、本人记录改 owner_id 403
  AC4 crm.export 返回 403 且响应体 error 为 permission_denied
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

ALLOW = ["crm.member.read", "event.read", "space.booking.read", "crm.member.write",
         "crm.followup.write", "crm.contact.read_sensitive", "opp.demand.read",
         "opp.demand.write", "kb.article.read", "ai.assistant.use"]
DENY = ["crm.export", "opp.match.write", "opp.assign", "lead.prospect.read",
        "lead.assign", "front.visitor.write", "event.manage", "content.publish",
        "kb.article.publish", "dash.exec.read", "iam.user.read", "sys.config.manage"]

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print("[%s] %s | %s" % (" OK " if ok else "FAIL", name, detail))
    return ok


def run(cmd, timeout=900):
    env = dict(os.environ)
    env["PYTHONPATH"] = ROOT
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def direct_probe():
    """不经 pytest，直接打接口桩，拿原始状态码与响应体（AC4 要的是响应体字段）。"""
    from fastapi.testclient import TestClient
    from stubapp import store as S
    from stubapp.main import app
    c = TestClient(app)
    h = {"X-Staff-Id": S.ME, "X-Site-Id": "site-a"}
    return c, h


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-mutate", action="store_true")
    a = ap.parse_args()

    xml = os.path.join(ROOT, "report", "junit.xml")
    rc, out = run([sys.executable, "-m", "pytest", "-q", "--junitxml=" + xml])
    check("AC1 pytest 全绿（40 条参数化用例）", rc == 0, "rc=%d" % rc)
    if rc != 0:
        print(out[-1500:])

    tests = fails = 0
    ids = []
    if os.path.isfile(xml):
        root = ET.parse(xml).getroot()
        for s in root.iter("testsuite"):
            tests += int(s.get("tests", 0))
            fails += int(s.get("failures", 0)) + int(s.get("errors", 0))
        ids = [tc.get("name", "") for tc in root.iter("testcase")]
    check("AC1 JUnit XML: 40 条 / 0 失败", tests == 40 and fails == 0,
          "tests=%d failures=%d" % (tests, fails))
    miss_a = [c for c in ALLOW if not any(c in i for i in ids)]
    miss_d = [c for c in DENY if not any(c in i for i in ids)]
    check("AC1 10 个允许项逐项有用例", not miss_a, "缺=%s" % miss_a)
    check("AC1 12 个禁止项逐项有用例", not miss_d, "缺=%s" % miss_d)

    c, h = direct_probe()
    r1 = c.get("/__probe__/crm.member.read/records", headers=h)
    b1 = r1.json() if r1.status_code == 200 else {}
    check("AC2 crm.member.read 探针返回 6 条（会所A）",
          r1.status_code == 200 and b1.get("count") == 6,
          "rc=%d count=%s ids=%s" % (r1.status_code, b1.get("count"), b1.get("ids")))
    r2 = c.get("/__probe__/crm.member.write/records", headers=h)
    b2 = r2.json() if r2.status_code == 200 else {}
    check("AC2 crm.member.write 探针只返回本人 3 条",
          r2.status_code == 200 and b2.get("count") == 3,
          "rc=%d count=%s ids=%s" % (r2.status_code, b2.get("count"), b2.get("ids")))

    r3 = c.patch("/api/crm/members/mem-004", json={"level": "diamond"}, headers=h)
    check("AC3 改同事负责的记录返回 404", r3.status_code == 404,
          "rc=%d body=%s" % (r3.status_code, r3.text[:120]))
    r4 = c.patch("/api/crm/members/mem-001", json={"owner_id": "staff-mm-002"}, headers=h)
    check("AC3 本人记录改 owner_id 返回 403", r4.status_code == 403,
          "rc=%d body=%s" % (r4.status_code, r4.text[:120]))

    r5 = c.get("/__probe__/crm.export", headers=h)
    e5 = ((r5.json() or {}).get("detail") or {}) if r5.status_code == 403 else {}
    check("AC4 crm.export 返回 403", r5.status_code == 403, "rc=%d" % r5.status_code)
    check("AC4 响应体 error == permission_denied", e5.get("error") == "permission_denied",
          "error=%s" % e5.get("error"))
    bad_err = []
    for code in DENY:
        rr = c.get("/__probe__/" + code, headers=h)
        d = ((rr.json() or {}).get("detail") or {})
        if rr.status_code != 403 or d.get("error") != "permission_denied":
            bad_err.append((code, rr.status_code, d.get("error")))
    check("AC4 12 个禁止项 error 全部为 permission_denied", not bad_err, "异常=%s" % bad_err)

    hb = {"X-Staff-Id": "staff-mm-001", "X-Site-Id": "site-b"}
    bad_b = [code for code in ALLOW
             if c.get("/__probe__/" + code, headers=hb).status_code != 403]
    check("附加 跨会所（切到 B）10 个允许项全部 403", not bad_b, "漏=%s" % bad_b)

    src = open(os.path.join(ROOT, "tests", "test_role_member_manager.py"), encoding="utf-8").read()
    check("附加 失败信息含角色/权限点/期望/实际",
          all(k in src for k in ("角色=", "权限点=", "期望=", "实际=")), "")
    check("附加 用例参数化生成", src.count("@pytest.mark.parametrize") >= 3,
          "parametrize=%d" % src.count("@pytest.mark.parametrize"))
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    lacking = [x for x in ALLOW + DENY if x not in readme]
    check("附加 README 用例清单覆盖 22 个权限点", not lacking, "缺=%s" % lacking)
    check("附加 角色矩阵可解析", os.path.isfile(os.path.join(ROOT, "role_matrix.yml")), "")

    if not a.no_mutate:
        rc2, out2 = run([sys.executable, "tools/mutate_3007.py"])
        m = re.search(r"MUTATION (PASS|FAIL)（(\d+)/(\d+) 被抓到）", out2)
        check("附加 变异测试 7/7 被抓到（用例非恒真）",
              rc2 == 0 and bool(m) and m.group(1) == "PASS", m.group(0) if m else "未解析到结论")

    passed = sum(1 for _, ok in RESULTS if ok)
    print("\nTOTAL %d, PASS %d, FAIL %d" % (len(RESULTS), passed, len(RESULTS) - passed))
    json.dump([{"name": n, "ok": ok} for n, ok in RESULTS],
              open(os.path.join(ROOT, "report", "verify_result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
