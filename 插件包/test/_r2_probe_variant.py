# -*- coding: utf-8 -*-
"""R2 探针 2（本会话自建）：对照「引擎变体索引」与「测试的 DLL 名集口径」在那 8 行上的差别。"""
import collections
import json
import os
import re
import sys

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PKG, "engine"))
sys.path.insert(0, os.path.join(PKG, "test"))

import dbparse  # noqa: E402
import sectionlib  # noqa: E402

OUT = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_r2_probe_variant.txt"),
           "w", encoding="utf-8")

TARGETS = {250: "3-L25x16x3", 256: "3-L45x28x3", 259: "3-L50X32X4", 260: "3-L56x36x3",
           261: "3-L56x36x4", 262: "3-L56x36x5", 1362: "8-B100*4.00", 1523: "9-B120X80X4.00"}

# ---- 引擎侧索引
builtin = sectionlib.load_builtin() if hasattr(sectionlib, "load_builtin") else None
print("sectionlib 顶层名字:", [n for n in dir(sectionlib) if not n.startswith("_")][:40], file=OUT)
if builtin is None:
    for cand in ("BuiltinTable", "load_table", "load_default", "load"):
        if hasattr(sectionlib, cand):
            print("  try", cand, file=OUT)
            builtin = getattr(sectionlib, cand)()
            break
print("builtin:", type(builtin).__name__, "recs", len(getattr(builtin, "recs", []) or []), file=OUT)

idx = dbparse._variant_index(builtin, None)
print("引擎 idx 键数:", len(idx), file=OUT)

REC = r"D:\AI_Work\PKPM数据解析\_recon\dbsect"
sys.path.insert(0, os.path.join(PKG, "test"))
import acceptance_r2 as acc  # noqa: E402

names, idx_t = acc._dll_variant_index()
print("测试 DLL 名集:", len(names), "索引键数:", len(idx_t), file=OUT)

for lineno, left in sorted(TARGETS.items()):
    k2 = dbparse.norm_pkpm2(left)
    k1 = dbparse.norm_pkpm(left)
    eng = [x for x in idx.get(k2, []) if x != left]
    eng1 = [x for x in idx.get(k1, []) if x != left]
    tst = [x for x in idx_t.get(k2, []) if x != left]
    print("行 %-5d %-16r key2=%-14s" % (lineno, left, k2), file=OUT)
    print("     引擎 idx[k2]=%s  idx[k1]=%s" % (idx.get(k2), idx.get(k1)), file=OUT)
    print("     测试 idx[k2]=%s（变体 %s）" % (idx_t.get(k2), tst[:3]), file=OUT)

# 包内表里是否有这些 DLL 名（任意行）
dll_names = collections.Counter()
for rec in (getattr(builtin, "recs", []) or []):
    e = getattr(rec, "extra", None) or {}
    for n in ([str(e.get("dll_table_entry") or "")]
              + re.findall(r"dll=([^;]+)", str(e.get("name_variants") or ""))):
        n = n.strip()
        if n:
            dll_names[n] += 1
print("包内表 dll 名总数:", len(dll_names), file=OUT)
for n in ("L25x16x3", "3-L25x16x3", "L45x28x3", "L50x32x4", "L56x36x3", "L56x36x4",
          "L56x36x5", "6-B100*4.00", "8-B100*4.00", "7-B120*80*4.00", "9-B120*80*4.00",
          "9-B120X80X4.00"):
    print("   包内表含 %-16r : %s" % (n, dll_names.get(n, 0)), file=OUT)
OUT.close()
print("done")
