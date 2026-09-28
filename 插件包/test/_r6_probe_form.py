# -*- coding: utf-8 -*-
"""R6 临时探针：窗体如何构造 --request 的 args（看 tool 与位置参数键名）。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/插件包/pdms-net/PKPM2PDMSForm.cs"
lines = open(p, encoding="utf-8").read().splitlines()
print("total", len(lines))
for i, ln in enumerate(lines, 1):
    if re.search(r'"(jwd|pdt|pdms|db|src|out|secmap|extra|project|base|angle|unit|report)"', ln) \
            or "EngineRunner" in ln or "cmbOp" in ln or "BuildRequest" in ln:
        print("%5d|%s" % (i, ln))
