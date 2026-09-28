# -*- coding: utf-8 -*-
"""R6 临时探针：核对 ① 的根因（只读 安装程序构建/src/engine_launcher.py 与 pdms-net/EngineRunner.cs）。"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = "D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0"


def show(path, needles, lo=None, hi=None):
    print("=" * 78)
    print(path)
    print("=" * 78)
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError as e:
        print("  <读取失败>", e)
        return
    for i, ln in enumerate(lines, 1):
        if lo is not None and hi is not None:
            if lo <= i <= hi:
                print("%5d|%s" % (i, ln))
            continue
        if any(n in ln for n in needles):
            print("%5d|%s" % (i, ln))


show(ROOT + "/安装程序构建/src/engine_launcher.py",
     ["--cli", "--request", "tkinter", "def main", "argv"])
show(ROOT + "/插件包/pdms-net/EngineRunner.cs", [], 60, 110)
