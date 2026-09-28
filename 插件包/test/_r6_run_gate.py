# -*- coding: utf-8 -*-
"""R6 临时运行器：只跑 acceptance_r3 的**检查 20（把关）**，不跑 build.cmd / 部署检查。

背景：check 20 断言宏的唯一化调用计数与宏结构（〔R6〕标准化后已改写），
本次改动必须回跑它；但 acceptance_r3.main() 会连带跑 16（真编译，会写 pdms-net/dist）
等属于其他实施包的检查 ⇒ 这里只调 check_gate 一个函数（同一份代码、同一断言）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", errors="replace",
                  closefd=False, buffering=1)

import acceptance_r3 as A

ch = A._Checker()
A.check_gate(ch)
for cid, title, errors, details in ch.items:
    print("[%s] 检查 %s：%s" % ("FAIL" if errors else "PASS", cid, title))
    for d in details:
        print("        %s" % d)
    for e in errors:
        print("        ** %s" % e)
print("FAIL 项 = %d" % len(ch.failed()))
sys.exit(1 if ch.failed() else 0)
