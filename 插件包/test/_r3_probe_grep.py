# -*- coding: utf-8 -*-
"""R3 探针 4：定位 pdt_write_selfcheck 里「读回截面数 == 输入截面数 27 vs 28」的检查代码。"""
t = open(r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\test\pdt_write_selfcheck.py",
         encoding="utf-8").read().splitlines()
for i, l in enumerate(t, 1):
    if "截面" in l and ("check" in l or "vs" in l or "len(" in l):
        print(i, l.strip()[:150])
