# -*- coding: utf-8 -*-
"""R6 临时探针：量出参考 DB Output 宏的分隔线宽度与 Date 行形态。"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"G:/工作/PDMS相关/00 PDMS插件/02 实用插件/PKPM导入导出插件/P-TRANS/pkpm_section_DBOutput.txt"
lines = open(p, "rb").read().decode("gbk").split("\r\n")
for idx in (0, 1, 2, 3, 4, 70295, 70296, 70297, 70298, 70299, 70300, 70301, 70302, 70303, 70304, 70305):
    ln = lines[idx]
    print("%5d len=%-3d %r" % (idx + 1, len(ln), ln))
sep = lines[1]
print("separator: prefix=%r dashes=%d total=%d" % (sep[:3], sep.count("-"), len(sep)))
