# -*- coding: utf-8 -*-
"""R6 临时探针：确认 R2 的两个 FAIL 与本次改动无关（mtimes + check_7 源码）。"""
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PKG = r"D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/插件包"
for f in ("install/install.ps1", "engine/macgen.py", "engine/cli.py",
          "test/acceptance_r2.py"):
    p = os.path.join(PKG, f)
    print("%-28s %s  %d 字节" % (f, time.strftime("%Y-%m-%d %H:%M:%S",
                                                  time.localtime(os.path.getmtime(p))),
                                 os.path.getsize(p)))
print("现在                        ", time.strftime("%Y-%m-%d %H:%M:%S"))
print("_recon 存在                  ",
      os.path.isdir(r"D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/_recon"))

t = open(os.path.join(PKG, "test/acceptance_r2.py"), encoding="utf-8").read().splitlines()
print("\n--- acceptance_r2.py 里 check_7 / DRYRUN 相关行 ---")
for i, l in enumerate(t, 1):
    if "DRYRUN" in l or "check_7" in l or "-DryRun" in l or "INSTALL_PS1" in l:
        print("%5d|%s" % (i, l))
