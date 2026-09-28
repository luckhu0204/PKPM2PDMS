# -*- coding: utf-8 -*-
"""R3 探针 6：收集器 --list-only 的跳过与计划（确认 R3 目录在计划里、_selftest 被跳过）。"""
import subprocess
import sys

COL = r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\deliver\collect_to_workspace.py"
p = subprocess.run([sys.executable, COL, "--list-only", "--refresh"], capture_output=True)
t = p.stdout.decode("utf-8", "replace") + p.stderr.decode("utf-8", "replace")
print("退出码", p.returncode)
for key in ("_selftest", "_pybuild", "_rootsim", "pdms-net", "engine\\dist",
            "pkpm2pdmsuniquename", "待复制文件数"):
    lines = [l.strip() for l in t.splitlines() if key in l]
    print("== %s : %d 行" % (key, len(lines)))
    for l in lines[:4]:
        print("   ", l[:170])
