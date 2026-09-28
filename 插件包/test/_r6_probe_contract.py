# -*- coding: utf-8 -*-
"""R6 临时探针：CONTRACT.md 里 §o.4/§o.5/F.2 的宏模板原文（只读）。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DOC = "D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/插件包/spec/CONTRACT.md"
print("exists", os.path.isfile(DOC))
doc = open(DOC, encoding="utf-8").read()
lines = doc.splitlines()
for i, ln in enumerate(lines, 1):
    if ("pkpm2pdmsFuncPath" in ln or "pkpm2pdmsFuncMissing" in ln or "defined(!!pkpm2pdmsUniquename)"
            or "Synonym translation" in ln or "-- ----" in ln or ln.startswith("## §o")
            or re.match(r"^#{1,4} .*F\.2", ln) or "附录 F" in ln):
        print("%5d|%s" % (i, ln))
print("=" * 70)
# 打印 §o.5 附近与 F.2 附近的代码块
blocks = list(re.finditer(r"```pml\r?\n(.*?)```", doc, re.S))
print("pml blocks:", len(blocks))
for bi, b in enumerate(blocks, 1):
    txt = b.group(1)
    first = txt.splitlines()[0] if txt.splitlines() else ""
    mark = ""
    if "pkpm2pdmsFuncPath" in txt:
        mark += " [FuncPath]"
    if "LABEL /PKPM2PDMSERR" in txt:
        mark += " [LABEL尾]"
    if "define function !!pkpm2pdmsUniquename" in txt:
        mark += " [F.1函数]"
    line_no = doc[:b.start()].count("\n") + 1
    print("  block %d @L%d  %s | %s" % (bi, line_no, first[:70], mark))
