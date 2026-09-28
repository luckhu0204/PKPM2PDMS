# -*- coding: utf-8 -*-
"""R3 探针 8：看收集器日志的 ERR/异常/结尾。"""
t = open(r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\test\_r4_collect_log.txt",
         "rb").read().decode("utf-8", "replace")
lines = t.splitlines()
print("总行数", len(lines))
for i, l in enumerate(lines, 1):
    if ("ERR" in l or "Traceback" in l or "错误" in l or "exception" in l.lower()
            or "哈希" in l):
        print(i, l[:200])
print("---- 尾部 25 行 ----")
for l in lines[-25:]:
    print(l[:180])
