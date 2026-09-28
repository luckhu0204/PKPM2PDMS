# -*- coding: utf-8 -*-
"""R3 探针：看收集器第二轮失败的输出。"""
t = open(r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\test\_r5_collect_log.txt",
         "rb").read().decode("utf-8", "replace")
lines = t.splitlines()
print("总行数", len(lines))
print("---- 尾部 30 行 ----")
for l in lines[-30:]:
    print(l[:190])
