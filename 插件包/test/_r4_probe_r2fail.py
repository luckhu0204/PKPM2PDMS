# -*- coding: utf-8 -*-
"""R3 探针 12：看 R2 门禁这次失败在哪一条。"""
t = open(r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\test\_r4_r2_regress.txt",
         "rb").read().decode("utf-8", "replace")
for i, l in enumerate(t.splitlines(), 1):
    if "[FAIL]" in l or l.startswith("**") or "failedCount" in l:
        print(i, l[:170])
