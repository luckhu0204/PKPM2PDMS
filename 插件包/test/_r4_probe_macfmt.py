# -*- coding: utf-8 -*-
"""R3 探针 10：看 R3 宏里 NEW SBFR / NEW SCTN 的实际形态（v1 计数为何为 0）。"""
t = open(r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\test\_acceptance_out\JLCJ2.mac",
         "rb").read().decode("gbk")
lines = t.split("\r\n")
shown = 0
for i, l in enumerate(lines):
    s = l.strip()
    if s.startswith("NEW SBFR") or s.startswith("NEW SCTN") or "SBFR" in s[:30]:
        print("%5d %s" % (i + 1, l[:150]))
        shown += 1
        if shown >= 24:
            break
