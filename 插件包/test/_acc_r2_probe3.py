# -*- coding: utf-8 -*-
"""临时探针 R2-3：看重复 SPRFILE/SPCOMPONENT 的归属（是否同一父级）。"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_acc_r2_out")
text = open(os.path.join(OUT, "jwd2db.mac"), encoding="utf-8", newline="").read()
lines = text.split("\r\n")
# 打印 /USER_RECT 族整块
start = [n for n, l in enumerate(lines) if "NEW STCATEGORY /USER_RECT" in l][0]
end = [n for n, l in enumerate(lines) if n > start and l.strip().startswith("NEW STCATEGORY")]
end = end[0] if end else len(lines)
print("---- /USER_RECT family block: lines %d..%d (%d lines)" % (start, end, end - start))
for l in lines[start:end]:
    print(repr(l))
print()
print("---- /USER_H family block:")
s2 = [n for n, l in enumerate(lines) if "NEW STCATEGORY /USER_H" in l][0]
e2 = [n for n, l in enumerate(lines) if n > s2 and l.strip().startswith("NEW STCATEGORY")]
e2 = e2[0] if e2 else len(lines)
print("lines %d..%d" % (s2, e2))
for l in lines[s2:e2]:
    print(repr(l))
print()
print("---- second pass (first 40 OLD lines):")
olds = [n for n, l in enumerate(lines) if l.strip().startswith("OLD ")]
for l in lines[olds[0] - 3:olds[0] + 40]:
    print(repr(l))
print()
print("---- tail:")
for l in lines[-10:]:
    print(repr(l))
