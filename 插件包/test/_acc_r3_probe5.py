# -*- coding: utf-8 -*-
"""探针 R3-5：R3 验收脚本三次运行（含脏沙箱重跑）的确定性与耗时。"""
import io
import subprocess
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
SCRIPT = r"PKPM2PDMS导入导出\test\acceptance_r3.py"
outs = []
for i in range(3):
    t = time.time()
    p = subprocess.run([sys.executable, SCRIPT], capture_output=True)
    e = time.time() - t
    outs.append(p.stdout)
    o = p.stdout.decode("utf-8", "replace")
    print("run%d exit=%d %.1fs %s" % (i, p.returncode, e, o.strip().splitlines()[-1]))
print("all identical:", all(o == outs[0] for o in outs))
if not all(o == outs[0] for o in outs):
    a, b = outs[0], outs[-1]
    d = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), None)
    print("first diff at", d)
    print("a:", a[max(0, d - 80):d + 80])
    print("b:", b[max(0, d - 80):d + 80])
