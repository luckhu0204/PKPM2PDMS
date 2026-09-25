# -*- coding: utf-8 -*-
"""临时探针 2（本会话自建）：定向查 TUBE / USER_CIRCLE / USER_PIPE 族与 φ20。"""
import os, re

SD = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
CAT = os.path.join(SD, "PKPM（PDMS数据库）.txt")


def read(p):
    data = open(p, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return data.decode(enc)
        except Exception:
            pass
    return data.decode("gbk", "replace")


t = read(CAT)
lines = t.splitlines()
want_fams = ("TUBE_TUBE-SPEC", "TUBE_TUBE50018-SPEC", "TUBE_TUBE6728_2002-SPEC",
             "USER_CIRCLE-SPEC", "USER_PIPE-SPEC", "USER_TUBE-SPEC")
for fam in want_fams:
    names = [l.strip().split()[-1] for l in lines
             if l.strip().startswith("NEW SPRFILE") and ("/" + fam + "/") in l]
    print("== %s : %d" % (fam, len(names)))
    for n in names[:80]:
        print("   ", n)
print("== 含 20 的 TUBE 名 ==")
for l in lines:
    s = l.strip()
    if s.startswith("NEW SPRFILE") and "-SPEC/" in s:
        nm = s.split()[-1]
        tail = nm.rsplit("/", 1)[-1]
        if re.search(r"(?<![0-9])20(?![0-9])", tail):
            print("   ", nm)
print("== 含 圆钢/圆形/圆管 的行 ==")
for i, l in enumerate(lines, 1):
    if re.search(r"圆钢|圆形|圆管", l):
        print(i, l.strip()[:160])
print("== PARA 行样例（TUBE_TUBE-SPEC 第一个） ==")
idx = [i for i, l in enumerate(lines) if l.strip().startswith("NEW SPRFILE") and "/TUBE_TUBE-SPEC/" in l]
if idx:
    i0 = idx[0]
    for l in lines[i0:i0 + 14]:
        print("   ", l.rstrip()[:160])
print("== USER_CIRCLE-SPEC 定义块 ==")
idx = [i for i, l in enumerate(lines) if l.strip().startswith("NEW SPRFILE") and "/USER_CIRCLE-SPEC/" in l]
if idx:
    i0 = idx[0]
    for l in lines[max(0, i0 - 6):i0 + 20]:
        print("   ", l.rstrip()[:160])
