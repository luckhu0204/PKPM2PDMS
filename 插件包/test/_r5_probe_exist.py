# -*- coding: utf-8 -*-
"""R3 探针：定位 pmlfnc 里剩余的 EXIST 行。"""
t = open(r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\pdms\pkpmjwduniquename.pmlfnc",
         "rb").read().decode("gbk")
out = open(r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\test\_r5_probe_exist.txt",
           "w", encoding="utf-8")
for i, l in enumerate(t.splitlines(), 1):
    if "EXIST" in l:
        print(i, l.strip()[:170], file=out)
out.close()
print("done")
