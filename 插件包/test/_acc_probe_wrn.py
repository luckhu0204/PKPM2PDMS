# -*- coding: utf-8 -*-
"""临时探针 10（本会话自建）：插件警告文件 + DLL 串里的「圆形/圆钢」与 Kind 族表线索。"""
import os, re, glob

SD = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
REC = r"D:\AI_Work\PKPM数据解析\_recon"
out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_acc_probe_wrn.txt"),
           "w", encoding="utf-8")


def read(p):
    data = open(p, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return data.decode(enc), enc
        except Exception:
            pass
    return data.decode("gbk", "replace"), "gbk-replace"


p = os.path.join(SD, "Pm[SPAS]转PDMS的信息提示.WRN")
if os.path.isfile(p):
    t, enc = read(p)
    print("==== WRN", os.path.basename(p), enc, os.path.getsize(p), "bytes ====", file=out)
    print(t, file=out)
p = os.path.join(SD, "安装使用方法.txt")
if os.path.isfile(p):
    t, enc = read(p)
    print("==== 安装使用方法.txt", enc, "====", file=out)
    print(t[:3000], file=out)

# 匹配文件里是否有「圆形/圆钢」左值
mapf = read(os.path.join(SD, "PKPM转PDMS截面匹配文件.txt"))[0]
print("==== 匹配文件里以 圆 开头的左值 ====", file=out)
for i, l in enumerate(mapf.splitlines(), 1):
    s = l.strip()
    if s.startswith("//"):
        continue
    left = s.split(",", 1)[0].strip()
    if left and ("圆" in left or "D20" in left.upper() or left.upper().endswith("20")):
        print(i, s[:140], file=out)

# 侦察 DLL 串：圆/圆形/圆钢
for pat in ("圆",):
    for f in sorted(glob.glob(os.path.join(REC, "str_*.txt")) + glob.glob(os.path.join(REC, "s2_*.txt"))):
        try:
            t, enc = read(f)
        except Exception:
            continue
        hits = [(i, l.strip()) for i, l in enumerate(t.splitlines(), 1) if pat in l]
        if hits:
            print("==== %s : %d hits ====" % (os.path.basename(f), len(hits)), file=out)
            for i, l in hits[:40]:
                print("   ", i, l[:170], file=out)
out.close()
print("done")
