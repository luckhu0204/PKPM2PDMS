# -*- coding: utf-8 -*-
"""R3 探针：看 db2jwd 对链式引用宏的解析错误。"""
import json

r = json.load(open(r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\test\_acc_tmp\r3_db2jwd.json",
                   encoding="utf-8"))
print("errors:")
for e in r.get("errors") or []:
    print("  -", e[:400])
print("warnings:")
for w in (r.get("warnings") or [])[:10]:
    print("  -", w[:300])
