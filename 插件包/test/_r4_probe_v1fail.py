# -*- coding: utf-8 -*-
"""R3 探针 9：看 v1 回归失败详情。"""
t = open(r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\test\_r4_v1_regress.txt",
         "rb").read().decode("utf-8", "replace")
i = t.find("[FAIL]")
print(t[i:i + 1600])
