# -*- coding: utf-8 -*-
"""R3 探针 5：to_jwd_sections 产物的身份分析（sid vs (NAME,SHAPE)）。"""
import collections
import os
import sys

sys.path.insert(0, r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\engine")
import sectionlib  # noqa: E402

secs = sectionlib.load_builtin_table().to_jwd_sections()
all_secs = [s for t in ("beam", "col", "brace") for s in secs[t]]
print("总记录数（beam+col+brace）:", len(all_secs))
ids = [s.id for s in all_secs]
print("唯一 sid:", len(set(ids)))
ns = [(s.name, s.kind) for s in all_secs]
print("唯一 (name,kind):", len(set(ns)))
both = {(s.id, s.name, s.kind) for s in all_secs}
print("唯一 (sid,name,kind):", len(both))
c = collections.Counter(ids)
dups = {k: v for k, v in c.items() if v > 1}
print("出现 >1 次的 sid 数:", len(dups), "（即 col+brace 同体复制）")
c2 = collections.Counter(ns)
dups2 = {k: v for k, v in c2.items() if v > 1}
print("出现 >1 次的 (name,kind) 数:", len(dups2))
for k, v in list(dups2.items())[:6]:
    ids_for = sorted({s.id for s in all_secs if (s.name, s.kind) == k})
    print("   ", k, "x", v, "sids:", ids_for[:4])
