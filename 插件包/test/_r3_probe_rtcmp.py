# -*- coding: utf-8 -*-
"""R3 探针：对比链式引用宏与旧宏的 db2jwd 反算结果（应逐字段一致）。"""
import sqlite3
import sys

sys.path.insert(0, r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\engine")
from canonical import Model  # noqa: E402
import jwd_read  # noqa: E402

a = jwd_read.read_jwd(r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\test\_acc_tmp\r3_db2jwd.jwd")
b = jwd_read.read_jwd(r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\test\_acc_tmp\r2old_db2jwd.jwd")
import json
ja = json.loads(a.to_json())
jb = json.loads(b.to_json())
diff = []
for k in sorted(set(ja) | set(jb)):
    if k in ("source", "notes", "contract_version"):
        continue
    if ja.get(k) != jb.get(k):
        diff.append(k)
print("差异域：", diff or "无（逐字段一致，除 source/notes）")
print("counts a:", a.counts())
print("counts b:", b.counts())
names_a = sorted(s.name for s in a.sections.values())
names_b = sorted(s.name for s in b.sections.values())
print("截面名一致：", names_a == names_b, "n=", len(names_a))
