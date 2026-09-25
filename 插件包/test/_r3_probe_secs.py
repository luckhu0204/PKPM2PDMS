# -*- coding: utf-8 -*-
"""R3 探针 3：找 jwd2pdt 读回后丢失的那个截面。"""
import os
import re
import sys

sys.path.insert(0, r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\engine")
import jwd_read  # noqa: E402
import pdt_read  # noqa: E402
import pdt_write  # noqa: E402

JWD = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\JLCJ2.jwd"
P = r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\test\_acc_tmp\r3_probe_secs.pdt"
m0 = jwd_read.read_jwd(JWD)
pdt_write.write_pdt(m0, P, pdt_write.PdtOptions(skeleton="full"))
m1 = pdt_read.read_pdt(P)

t = open(P, "rb").read().decode("gbk")
file_secs = re.findall(r"^\s+ID=(\d+), NAME=([^,]*), SHAPE=(\d+)", t, re.M)
print("文件里 $DEFFRAMESECTION 记录 %d 条" % len(file_secs))
print("m0.sections %d 个；m1.sections %d 个" % (len(m0.sections), len(m1.sections)))
print("文件记录：")
for sid, nm, sh in file_secs:
    print("   ID=%s NAME=%r SHAPE=%s" % (sid, nm, sh))
print("m1 读到的：")
for sid, s in sorted(m1.sections.items()):
    print("   ID=%s NAME=%r kind=%s" % (sid, s.name, s.kind))
print("notes：")
for n in m1.notes:
    if "DEFFRAMESECTION" in n or "截面" in n:
        print("   -", n[:260])
