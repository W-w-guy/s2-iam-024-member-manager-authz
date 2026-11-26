# -*- coding: utf-8 -*-
"""生成测试夹具（确定性构造，无随机、无外部数据源）。

用法：python tools/gen_fixtures.py
产出：fixtures/{members,demands,followups,events,bookings,articles}.json + summary.json
重跑结果稳定（写死顺序与编号），可与包内文件逐一比对。
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "fixtures")
ORG = "org-fake-001"
ME, PEER, OB = "staff-mm-001", "staff-mm-002", "staff-mm-003"
SITES = [("site-a", ME, "own"), ("site-a", PEER, "peer"), ("site-b", OB, "b")]


def rows(kind, per_site, prefix):
    out, n = [], 0
    for site, owner, tag in SITES:
        for i in range(per_site):
            n += 1
            out.append({"id": "%s-%03d" % (prefix, n), "kind": kind, "org_id": ORG,
                        "site_id": site, "owner_id": owner, "tag": tag,
                        "seq": i + 1})
    return out


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    members = rows("crm.member", 3, "mem")
    for m in members:
        n = int(m["id"].split("-")[1])
        m.update({"name": "会员%s%02d（虚构）" % (m["tag"].upper(), m["seq"]),
                  "phone": "1380000%04d" % n, "email": "fake%03d@example.invalid" % n,
                  "level": "gold" if m["seq"] == 1 else "silver"})
    data = {
        "members": members,
        "demands": [dict(r, id="dem-00%d" % (i + 1)) for i, r in
                    enumerate(rows("opp.demand", 2, "dem")[:2])] + [
            {"id": "dem-003", "kind": "opp.demand", "org_id": ORG, "site_id": "site-a", "owner_id": PEER, "tag": "peer", "seq": 1},
            {"id": "dem-004", "kind": "opp.demand", "org_id": ORG, "site_id": "site-b", "owner_id": OB, "tag": "b", "seq": 1}],
        "followups": [{"id": "fu-001", "kind": "crm.followup", "org_id": ORG, "site_id": "site-a", "owner_id": ME, "tag": "own", "seq": 1},
                      {"id": "fu-002", "kind": "crm.followup", "org_id": ORG, "site_id": "site-a", "owner_id": ME, "tag": "own", "seq": 2},
                      {"id": "fu-003", "kind": "crm.followup", "org_id": ORG, "site_id": "site-a", "owner_id": PEER, "tag": "peer", "seq": 1}],
        "events": [{"id": "ev-001", "kind": "event", "org_id": ORG, "site_id": "site-a", "owner_id": PEER, "tag": "site", "seq": 1},
                   {"id": "ev-002", "kind": "event", "org_id": ORG, "site_id": "site-a", "owner_id": PEER, "tag": "site", "seq": 2}],
        "bookings": [{"id": "bk-%03d" % i, "kind": "space.booking", "org_id": ORG, "site_id": "site-a", "owner_id": ME, "tag": "site", "seq": i} for i in (1, 2, 3)],
        "articles": [{"id": "kb-%03d" % i, "kind": "kb.article", "org_id": ORG, "site_id": "site-a", "owner_id": PEER, "tag": "org", "seq": i} for i in (1, 2)],
    }
    for k, v in data.items():
        with open(os.path.join(OUT, k + ".json"), "w", encoding="utf-8") as f:
            json.dump(v, f, ensure_ascii=False, indent=1, sort_keys=True)
    summary = {"org": ORG, "sites": 2, "staff": 3,
               "counts": {k: len(v) for k, v in data.items()},
               "note": "确定性构造，无随机；重跑结果逐字节一致"}
    with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1, sort_keys=True)
    print("夹具已生成：", summary["counts"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
