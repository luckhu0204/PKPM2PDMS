# -*- coding: utf-8 -*-
"""R6 临时探针：列出 test/ 里所有"活"测试（非 _ 前缀 .py）对宏文本的断言行。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = "D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/插件包/test"
NEEDLES = ["pkpm2pdmsFuncPath", "pkpm2pdmsFuncMissing", "$M <", "Synonym translation",
           "ONERROR GOLABEL", "LABEL /PKPM2PDMSERR", "!!pkpm2pdmsUniquename",
           "TOOLS", "auto2pdms", "jwd2pdms", "pdt2pdms"]
files = sorted(f for f in os.listdir(HERE)
               if f.endswith(".py") and not f.startswith("_"))
for fn in files:
    p = os.path.join(HERE, fn)
    txt = open(p, encoding="utf-8", errors="replace").read()
    hits = []
    for i, ln in enumerate(txt.splitlines(), 1):
        for n in NEEDLES:
            if n in ln:
                hits.append((i, n, ln.strip()[:160]))
                break
    if hits:
        print("### %s  (%d)" % (fn, len(hits)))
        for i, n, ln in hits:
            print("   %5d [%s] %s" % (i, n, ln))
