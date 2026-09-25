# -*- coding: utf-8 -*-
"""探针 R3-3：PMLLIB 出处精确行号核对。"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
PD = r"D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB"
for rel, kw in ((r"TIANGONG\functions\tgautonum.pmlfnc", "EXIST"),
                (r"TIANGONG\functions\tgautonum.pmlfnc", "do "),
                (r"mypml\forms\GRIDDESIGN.pmlfrm", ".string()"),
                (r"mypml\forms\GRIDDESIGN.pmlfrm", "APPEND"),
                (r"assembly\functions\assybuildname.pmlfnc", "FALSEA"),
                (r"aba\Forms\abaarealib.pmlfrm", "TRUEA"),
                (r"aba\Forms\abauserview.pmlfrm", "EXIST")):
    p = os.path.join(PD, rel)
    if not os.path.isfile(p):
        print("MISSING", rel)
        continue
    L = open(p, "rb").read().decode("gbk", "replace").replace("\r\n", "\n").split("\n")
    hits = [(i + 1, l.strip()[:100]) for i, l in enumerate(L) if kw in l]
    print("%s  %r -> %s" % (rel, kw, hits[:4]))
