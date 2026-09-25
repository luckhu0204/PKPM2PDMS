# -*- coding: utf-8 -*-
"""R3 探针：定位 §0.4 表格第 89 行的多余竖线。"""
lines = open(r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\spec\CONTRACT.md",
             encoding="utf-8").read().split("\n")
l = lines[88]
print("line 89 col-count:", l.count("|") - 1)
out = open(r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\test\_r5_probe_line89.txt",
           "w", encoding="utf-8")
for i, c in enumerate(l):
    if c == "|":
        print("pipe %2d at char %5d: ...%s..." % (i, i, l[max(0, i - 25):i + 25]), file=out)
print("cell 文本：", [c.strip()[:60] for c in l.split("|")], file=out)
out.close()
