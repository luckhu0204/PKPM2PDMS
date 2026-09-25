# -*- coding: utf-8 -*-
"""R2 探针 3（本会话自建）：逐行对照引擎口径与测试口径的大小写变体，定位差在哪 8 行。"""
import collections
import json
import os
import re
import sys

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PKG, "engine"))
sys.path.insert(0, os.path.join(PKG, "test"))

import dbparse            # noqa: E402
import sectionlib         # noqa: E402
import acceptance_r2 as acc   # noqa: E402

OUT = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_r2_probe_variant2.txt"),
           "w", encoding="utf-8")

table = sectionlib.load_builtin_table()
print("builtin recs:", len(table.recs), file=OUT)
idx_eng = dbparse._variant_index(table, None)
print("引擎 idx 键数:", len(idx_eng), file=OUT)
names, idx_tst = acc._dll_variant_index()
print("测试 DLL 名集:", len(names), "键数:", len(idx_tst), file=OUT)

rows = acc._parse_match_rows()
print("匹配文件行数:", len(rows), file=OUT)

eng_hits, tst_hits, lost = [], [], []
for (i, left, rhs) in rows:
    e = [x for x in idx_eng.get(dbparse.norm_pkpm2(left), []) if x != left]
    t = [x for x in idx_tst.get(acc._norm_pkpm2(left), []) if x != left]
    if e:
        eng_hits.append((i, left, e[0]))
    if t:
        tst_hits.append((i, left, t[0]))
    if t and not e:
        lost.append((i, left, t[0], t[:4]))
print("引擎命中 %d 行；测试命中 %d 行；差 %d 行" % (len(eng_hits), len(tst_hits), len(lost)),
      file=OUT)
print("---- 差额行（测试有变体、引擎没有）----", file=OUT)
for i, left, v, allv in lost:
    print("  行 %-5d 左值 %-18r 测试变体 %-18r 全部候选 %s" % (i, left, v, allv), file=OUT)
    k1, k2 = dbparse.norm_pkpm(left), dbparse.norm_pkpm2(left)
    print("       引擎 idx[k1]=%s idx[k2]=%s" % (idx_eng.get(k1), idx_eng.get(k2)), file=OUT)
    # 包内表里有没有任何名字归一后落在同一键上
    hits = []
    for rec in table.recs:
        e2 = rec.extra or {}
        for n in ([str(e2.get("dll_table_entry") or "")]
                  + re.findall(r"dll=([^;]+)", str(e2.get("name_variants") or ""))):
            n = n.strip()
            if n and dbparse.norm_pkpm2(n) == k2:
                hits.append((rec.pkpm_name, n, e2.get("dll_table_entry")))
    print("       包内表同键（norm2）的 DLL 名: %s" % (hits[:6],), file=OUT)

print("---- 引擎命中里不属于测试命中的（反向）----", file=OUT)
tst_set = {(i, left) for (i, left, _v) in tst_hits}
for i, left, v in eng_hits:
    if (i, left) not in tst_set:
        print("  行 %-5d 左值 %-18r 引擎变体 %r（测试无）" % (i, left, v), file=OUT)
OUT.close()
print("done")
