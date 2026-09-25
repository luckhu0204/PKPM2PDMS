# -*- coding: utf-8 -*-
"""探针 R2-14：四次运行逐字节确定性核对。"""
import io
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
SCRIPT = r"PKPM-JWD导入导出\test\acceptance_r2.py"
outs = []
for i in range(4):
    p = subprocess.run([sys.executable, SCRIPT], capture_output=True)
    outs.append(p.stdout)
    print("run%d exit=%d bytes=%d" % (i, p.returncode, len(p.stdout)))
for i in range(1, 4):
    a, b = outs[0], outs[i]
    d = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), None)
    print("run0 vs run%d: identical=%s firstdiff=%s" % (i, a == b, d))
    if d is not None:
        print("   a=", a[max(0, d - 70):d + 70])
        print("   b=", b[max(0, d - 70):d + 70])
