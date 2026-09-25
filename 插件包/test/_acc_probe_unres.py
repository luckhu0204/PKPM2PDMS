# -*- coding: utf-8 -*-
"""临时探针（本会话自建）：查样本匹配文件里与 Kind=3 / 32335 相关的条目。"""
import io, os, re, sys

P = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\PKPM转PDMS截面匹配文件.txt"
data = open(P, "rb").read()
print("bytes", len(data))
t = None
for enc in ("utf-8", "gbk", "utf-8-sig"):
    try:
        t = data.decode(enc)
        print("decoded with", enc)
        break
    except Exception as e:
        print(enc, "fail", repr(e)[:80])
lines = t.splitlines()
print("lines", len(lines))
print("--- first 20 ---")
for i, l in enumerate(lines[:20]):
    print(i, repr(l))
print("--- lines mentioning 32335 ---")
for i, l in enumerate(lines):
    if "32335" in l:
        print(i, repr(l))
print("--- lines mentioning Kind-ish '3#' ---")
c = 0
for i, l in enumerate(lines):
    if re.search(r"(^|[^0-9])3#", l):
        print(i, repr(l))
        c += 1
        if c > 40:
            break
print("count 3# =", c)
print("--- lines mentioning 20,5 or '20#5' ---")
for i, l in enumerate(lines):
    if "20#5" in l or "5,20" in l:
        print(i, repr(l))
print("--- last 10 ---")
for i, l in enumerate(lines[-10:]):
    print(len(lines) - 10 + i, repr(l))
