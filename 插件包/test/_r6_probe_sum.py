# -*- coding: utf-8 -*-
"""R6 临时探针：汇总四个静态检查脚本的结论。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
base = r"D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/插件包/test/"
for f in ("_r6_chk_v3contract.txt", "_r6_chk_v2contract.txt",
          "_r6_chk_selfcheck.txt", "_r6_chk_pml.txt"):
    p = base + f
    print("### %s" % f)
    if not os.path.isfile(p):
        print("    <不存在>")
        continue
    t = open(p, encoding="utf-8", errors="replace").read().splitlines()
    fails = [l for l in t if "FAIL" in l]
    print("    行数 %d" % len(t))
    for l in t[-4:]:
        print("    | %s" % l)
    if fails:
        print("    FAIL 行（前 12）：")
        for l in fails[:12]:
            print("      %s" % l)
