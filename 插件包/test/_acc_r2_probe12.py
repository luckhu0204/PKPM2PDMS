# -*- coding: utf-8 -*-
"""探针 R2-12：确认 r2_* 产物到底在哪（路径是否存在）。"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_acceptance_r2_out")
print("HERE =", repr(HERE))
print("OUT  =", repr(OUT), "isdir=", os.path.isdir(OUT))
print("entries:", dir(os.path.join(HERE)) if False else None)
for root, dirs, files in os.walk(HERE):
    if "_acc" in root:
        print("DIR:", repr(root))
        for f in sorted(files):
            if f.startswith("r2_") or f.startswith("_"):
                print("    ", repr(f), os.path.getsize(os.path.join(root, f)))
        break
for p in ("r2_jwd2pdt.pdt", "r2_jwd2db.mac", "r2_from_builtin.csv"):
    q = os.path.join(OUT, p)
    print("%-22s exists=%s" % (p, os.path.exists(q)))
print("all dirs under HERE:", [d for d in os.listdir(HERE) if os.path.isdir(os.path.join(HERE, d))])
