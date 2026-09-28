# -*- coding: utf-8 -*-
"""R3 探针：确认生成的宏里 TYPE 通道/故障注入行已是新形态（!!pkpm2pdmsType / EXIST $!n）。"""
t = open(r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\test\_acc_r3_out\r3_jwd2pdms.mac",
         "rb").read().decode("gbk")
lines = t.split("\r\n")
dbl = sum(1 for l in lines if l.strip().startswith("!!pkpm2pdmsType = '"))
sgl = sum(1 for l in lines if l.strip().startswith("!pkpm2pdmsType = '"))
fatal_new = sum(1 for l in lines if "var !pkpm2pdmsFatal EXIST $!n" in l)
fatal_old = sum(1 for l in lines if "var !pkpm2pdmsFatal EXIST /$!n" in l)
calls = sum(1 for l in lines if "!!pkpm2pdmsUniquename('" in l)
types = sorted({l.strip() for l in lines if l.strip().startswith("!!pkpm2pdmsType = '")})
print("!!pkpm2pdmsType 赋值行 =", dbl, "；残留单 ! 赋值 =", sgl)
print("故障注入 EXIST $!n =", fatal_new, "；旧形 EXIST /$!n =", fatal_old)
print("唯一化调用 =", calls)
print("TYPE 取值样例：", types)
