# -*- coding: utf-8 -*-
"""R3 探针：看 check_v3_contract 的失败项。"""
t = open(r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\test\_r5_v3contract.txt",
         "rb").read().decode("utf-8", "replace")
for i, l in enumerate(t.splitlines(), 1):
    if "FAIL" in l:
        print(i, l[:200])
