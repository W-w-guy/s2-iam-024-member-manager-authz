# -*- coding: utf-8 -*-
"""pii 扫描：确认交付包里没有真实个人信息。

白名单（本包虚构约定，写死）：
  · 手机号 1380000xxxx —— 虚构段，不算命中
  · 邮箱 @example.invalid —— 保留域名，不算命中
  · 姓名一律带「（虚构）」后缀
命中即非零退出码，便于接 CI。

用法：python tools/pii_scan.py [--dir .]
"""
from __future__ import annotations

import argparse
import os
import re
import sys

SKIP_DIR = {"__pycache__", ".pytest_cache", "report", ".git"}
TEXT_EXT = {".py", ".md", ".json", ".jsonl", ".yml", ".yaml", ".txt", ".ini", ".xml"}

PATTERNS = [
    ("手机号", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("邮箱", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("身份证", re.compile(r"(?<!\d)[1-9]\d{16}[0-9Xx](?!\d)")),
    ("银行卡", re.compile(r"(?<!\d)\d{16,19}(?!\d)")),
]


def allowed(kind: str, val: str) -> bool:
    if kind == "手机号":
        return val.startswith("1380000")
    if kind == "邮箱":
        return val.endswith("@example.invalid")
    if kind == "银行卡":
        return val.startswith("1380000") or len(val) > 19
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args()
    scanned, hits, files = 0, [], 0
    for dp, dns, fns in os.walk(a.dir):
        dns[:] = [d for d in dns if d not in SKIP_DIR]
        for fn in fns:
            if os.path.splitext(fn)[1].lower() not in TEXT_EXT:
                continue
            p = os.path.join(dp, fn)
            files += 1
            try:
                txt = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for kind, rx in PATTERNS:
                for m in rx.finditer(txt):
                    scanned += 1
                    if not allowed(kind, m.group(0)):
                        hits.append((os.path.relpath(p, a.dir), kind, m.group(0)))
    print("扫描文件 %d 个，候选串 %d 个，命中（非白名单）%d 处" % (files, scanned, len(hits)))
    for h in hits[:20]:
        print("  HIT", h)
    return 0 if not hits else 1


if __name__ == "__main__":
    sys.exit(main())
