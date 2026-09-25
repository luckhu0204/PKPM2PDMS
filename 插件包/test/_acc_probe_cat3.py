# -*- coding: utf-8 -*-
"""临时探针 3（本会话自建）：看目录宏前若干行 + SPRFILE/SPCOMPONENT 行样例。"""
import os, re

SD = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
CAT = os.path.join(SD, "PKPM（PDMS数据库）.txt")
out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_acc_probe_cat3.txt"),
           "w", encoding="utf-8")
data = open(CAT, "rb").read()
print("first bytes:", data[:8].hex(), file=out)
for enc in ("utf-8-sig", "utf-8", "gbk"):
    try:
        t = data.decode(enc)
        print("decoded", enc, file=out)
        break
    except Exception as e:
        print("fail", enc, repr(e)[:60], file=out)
lines = t.splitlines()
print("lines", len(lines), file=out)
print("---- first 30 ----", file=out)
for i, l in enumerate(lines[:30]):
    print(i, repr(l), file=out)
print("---- 3 SPRFILE samples ----", file=out)
c = 0
for i, l in enumerate(lines):
    if "SPRFILE" in l:
        print(i, repr(l), file=out)
        c += 1
        if c >= 3:
            break
print("---- 3 SPCOMPONENT samples ----", file=out)
c = 0
for i, l in enumerate(lines):
    if "SPCOMPONENT" in l:
        print(i, repr(l), file=out)
        c += 1
        if c >= 3:
            break
print("---- lines with TUBE ----", file=out)
c = 0
for i, l in enumerate(lines):
    if "TUBE" in l:
        print(i, repr(l), file=out)
        c += 1
        if c >= 25:
            break
print("---- lines with 20 in TUBE/CIRCLE context ----", file=out)
c = 0
for i, l in enumerate(lines):
    if "TUBE_TUBE-SPEC" in l and "20" in l:
        print(i, repr(l), file=out)
        c += 1
        if c >= 20:
            break
out.close()
print("done")
