# -*- coding: utf-8 -*-
"""临时探针 R2-2：看生成的目录宏结构（重复名 / 两遍 / 族链）。"""
import collections
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_acc_r2_out")

for f in ["jwd2db.mac", "pdt2db.mac", "closure2.mac"]:
    p = os.path.join(OUT, f)
    t = open(p, encoding="utf-8", newline="").read().split("\r\n")
    comp = [l.split()[-1] for l in t if l.strip().startswith("NEW SPCOMPONENT")]
    spr = [l.split()[-1] for l in t if l.strip().startswith("NEW SPRFILE")]
    sel = [l.strip() for l in t if l.strip().startswith("NEW SELEC")]
    cat = [l.split()[-1] for l in t if l.strip().startswith("NEW STCATEGORY")]
    sts = [l.split()[-1] for l in t if l.strip().startswith("NEW STSECTION")]
    old = [l.strip() for l in t if l.strip().startswith("OLD ")]
    print("=== %s lines=%d" % (f, len(t)))
    print("  NEW=%d END=%d OLD=%d" % (sum(1 for l in t if l.strip().startswith("NEW ")),
                                      sum(1 for l in t if l.strip() == "END"), len(old)))
    print("  SPRFILE=%d unique=%d" % (len(spr), len(set(spr))))
    print("  SPCOMPONENT=%d unique=%d dup=%s"
          % (len(comp), len(set(comp)), [k for k, v in collections.Counter(comp).items() if v > 1]))
    print("  STCATEGORY(%d)=%s" % (len(cat), cat))
    print("  STSECTION(%d)=%s" % (len(sts), sts))
    print("  SELEC(%d)=%s" % (len(sel), sel[:12]))
    print("  OLD kinds=%s" % collections.Counter(o.split()[1] if len(o.split()) > 1 else "?" for o in old))
    print("  head:")
    for l in t[:8]:
        print("    " + repr(l))
    print("  first family block:")
    i = [n for n, l in enumerate(t) if "NEW STCATEGORY" in l]
    if i:
        for l in t[i[0]:i[0] + 40]:
            print("    " + repr(l))
    print()
