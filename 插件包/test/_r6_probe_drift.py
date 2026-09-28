# -*- coding: utf-8 -*-
"""R6 临时探针：CONTRACT.md / engine 文档里与本次改动冲突或需同步的行（漂移清单）。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DOC = r"D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/插件包/spec/CONTRACT.md"
NEEDLES = ("pkpm2pdmsFuncPath", "自动生成", "单位：", "构件 %d", "命名约定",
           "pml_func_path", "auto2pdms", "$S-  -- Synonym")

lines = open(DOC, encoding="utf-8").read().splitlines()
print("=== CONTRACT.md（%d 行）漂移相关行 ===" % len(lines))
for i, ln in enumerate(lines, 1):
    hit = [n for n in NEEDLES if n in ln]
    if hit:
        print("%5d [%s] %s" % (i, ",".join(hit), ln.strip()[:200]))

R = r"D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/插件包/engine/README.txt"
print("\n=== engine/README.txt（是否存在 %s）===" % os.path.isfile(R))
if os.path.isfile(R):
    rl = open(R, encoding="utf-8", errors="replace").read().splitlines()
    print("行数", len(rl))
    for i, ln in enumerate(rl, 1):
        if any(n in ln for n in ("pml_func_path", "pkpm2pdmsFuncPath", "预载", "$M",
                                 "jwd2pdms", "TOOLS", "auto2pdms", "宏头", "Synonym")):
            print("%5d|%s" % (i, ln.rstrip()[:180]))
