# -*- coding: utf-8 -*-
"""S3-v2 开发探针：看 jwd2pdt 的段统计 / skipped 分类 / 报告 db 块。

跑法：``python PKPM2PDMS导入导出\\test\\_s3_cli\\probe_v2.py [report.json ...]``
只读产物，不写任何东西。
"""
from __future__ import annotations

import io
import json
import os
import sys
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def show(path):
    print("=" * 78)
    print(path)
    rep = json.load(io.open(path, encoding="utf-8"))
    print("tool=%s source_format=%s" % (rep.get("tool"), rep.get("source_format")))
    st = rep.get("stats") or {}
    print("stats keys: %s" % sorted(st))
    for k in ("segments", "ids", "rows", "tables", "write", "verify", "reverse",
              "secmap_backfilled", "panel_recs", "table_recs", "table_rows",
              "table_columns", "table_format", "table_sha256", "macro_bytes",
              "macro_lines", "containers"):
        if k in st:
            print("  %s = %s" % (k, json.dumps(st[k], ensure_ascii=False, sort_keys=True)[:400]))
    sk = rep.get("skipped") or []
    print("skipped=%d 分类：%s" % (len(sk), dict(Counter(x.get("what") for x in sk))))
    for x in sk[:5]:
        print("   - %s" % json.dumps(x, ensure_ascii=False)[:220])
    print("assumptions=%d" % len(rep.get("assumptions") or []))
    for a in (rep.get("assumptions") or [])[:14]:
        print("   - %s" % a[:170])
    db = rep.get("db") or {}
    print("db keys: %s" % sorted(db))
    for k in ("generated", "parsed", "cross_check", "closure", "safety"):
        v = db.get(k)
        if isinstance(v, dict):
            print("  db.%s: %s" % (k, json.dumps(v, ensure_ascii=False, sort_keys=True)[:500]))
    print("db.losses=%d 条" % len(db.get("losses") or []))
    print("warnings=%d（前 3）" % len(rep.get("warnings") or []))
    for w in (rep.get("warnings") or [])[:3]:
        print("   - %s" % w[:170])


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
        args = [os.path.join(out, f) for f in
                ("sample_jwd.report.json", "sample_db.report.json")]
    for p in args:
        show(p)
