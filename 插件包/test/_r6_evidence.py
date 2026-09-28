# -*- coding: utf-8 -*-
"""R6 证据：把两个 auto2pdms 产物宏的头 12 行/尾 10 行原文与计数核验落到一份文本里。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

R6 = r"D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/验收/R6日志"
NAMED = ("SITE", "ZONE", "STRU", "FRMW", "SBFR", "SCTN", "PANE", "STWALL")

for tag, fn in (("JLCJ2.jwd（jwd 分支）", "auto_jwd.mac"),
                ("1_PM.pdt（pdt 分支）", "auto_pdt.mac")):
    p = os.path.join(R6, fn)
    print("=" * 78)
    print("源：%s" % tag)
    print("宏：%s" % p)
    print("=" * 78)
    if not os.path.isfile(p):
        print("  <不存在>")
        continue
    raw = open(p, "rb").read()
    print("字节 = %d；BOM = %s；CRLF = %d；孤立 LF = %d"
          % (len(raw), raw[:3] == b"\xef\xbb\xbf", raw.count(b"\r\n"),
             raw.replace(b"\r\n", b"").count(b"\n")))
    lines = raw.decode("gbk").split("\r\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    print("行数 = %d" % len(lines))
    print("--- 宏头 12 行 ---")
    for i in range(12):
        print("%3d|%s" % (i + 1, lines[i]))
    print("--- 宏尾 10 行 ---")
    for i in range(len(lines) - 10, len(lines)):
        print("%3d|%s" % (i + 1, lines[i]))
    calls = sum(1 for l in lines if "!!pkpm2pdmsUniquename(" in l)
    news = sum(1 for l in lines if re.match(r"\s*NEW (%s) \$!n$" % "|".join(NAMED), l))
    guards = sum(1 for l in lines if "var !pkpm2pdmsFatal EXIST $!n" in l)
    print("--- 计数核验 ---")
    print("!!pkpm2pdmsUniquename 调用 = %d；创建元素（NEW <T> $!n）= %d；空名守卫 = %d"
          % (calls, news, guards))
    for bad in ("pkpm2pdmsFuncMissing", "pkpm2pdmsFuncPath", "FuncPath", "$M <",
                "defined(!!pkpm2pdmsUniquename)"):
        print("  含 %-30s : %d 处" % (bad, sum(1 for l in lines if bad in l)))
    print()
