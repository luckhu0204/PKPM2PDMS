# -*- coding: utf-8 -*-
"""R3 探针 6：找 check_v2_db 的容器后缀断言与 pdt_write 的 re 使用。"""
import re

t = open(r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\test\check_v2_db.py", encoding="utf-8").read()
for i, l in enumerate(t.splitlines(), 1):
    if "唯一" in l or "suffix" in l or "2026" in l or re.search(r"d\{8\}", l):
        print(i, l.strip()[:160])
print("---- pdt_write.py 的 re 使用 ----")
t2 = open(r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\engine\pdt_write.py",
          encoding="utf-8").read()
for i, l in enumerate(t2.splitlines(), 1):
    if "re." in l:
        print(i, l.strip()[:120])
