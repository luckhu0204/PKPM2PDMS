# -*- coding: utf-8 -*-
"""R3 探针 11：唯一化调用行的确切语法（用于 v1 计数解析）。"""
t = open(r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\test\_acceptance_out\JLCJ2.mac",
         "rb").read().decode("gbk")
lines = t.split("\r\n")
shown = 0
for i, l in enumerate(lines):
    if "Uniquename" in l:
        print("%5d %s" % (i + 1, l[:170]))
        shown += 1
        if shown >= 8:
            break
print("---- SBFR/COLUMN 附近 12 行 ----")
for i, l in enumerate(lines):
    if l.strip() == "NEW SBFR $!n" and shown < 40:
        for j in range(max(0, i - 6), i + 2):
            print("%5d %s" % (j + 1, lines[j][:150]))
        shown += 40
        break
