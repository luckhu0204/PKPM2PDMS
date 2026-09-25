# -*- coding: utf-8 -*-
"""R3 探针：确认生成的宏里 TYPE 通道/故障注入行已是新形态（!!pkpmjwdType / EXIST $!n）。"""
t = open(r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\test\_acc_r3_out\r3_jwd2pdms.mac",
         "rb").read().decode("gbk")
lines = t.split("\r\n")
dbl = sum(1 for l in lines if l.strip().startswith("!!pkpmjwdType = '"))
sgl = sum(1 for l in lines if l.strip().startswith("!pkpmjwdType = '"))
fatal_new = sum(1 for l in lines if "var !pkpmjwdFatal EXIST $!n" in l)
fatal_old = sum(1 for l in lines if "var !pkpmjwdFatal EXIST /$!n" in l)
calls = sum(1 for l in lines if "!!pkpmjwdUniquename('" in l)
types = sorted({l.strip() for l in lines if l.strip().startswith("!!pkpmjwdType = '")})
print("!!pkpmjwdType 赋值行 =", dbl, "；残留单 ! 赋值 =", sgl)
print("故障注入 EXIST $!n =", fatal_new, "；旧形 EXIST /$!n =", fatal_old)
print("唯一化调用 =", calls)
print("TYPE 取值样例：", types)
