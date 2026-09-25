# -*- coding: utf-8 -*-
"""临时探针 6（本会话自建）：看插件自带的 pkpm_section_DBOutput.txt（截面库输出）。"""
import os, re

SD = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
P = os.path.join(SD, "P-TRANS", "pkpm_section_DBOutput.txt")
out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_acc_probe_dbout.txt"),
           "w", encoding="utf-8")


def read(p):
    data = open(p, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return data.decode(enc), enc
        except Exception:
            pass
    return data.decode("gbk", "replace"), "gbk-replace"


t, enc = read(P)
print("enc", enc, "bytes", os.path.getsize(P), file=out)
lines = t.splitlines()
print("lines", len(lines), file=out)
print("---- first 40 ----", file=out)
for i, l in enumerate(lines[:40]):
    print(i, repr(l[:200]), file=out)
print("---- lines mentioning 20 / 圆 ----", file=out)
c = 0
for i, l in enumerate(lines):
    if "圆" in l:
        print("R", i, repr(l[:200]), file=out)
        c += 1
        if c > 30:
            break
print("---- lines whose fields contain a lone '20' ----", file=out)
c = 0
for i, l in enumerate(lines):
    fs = re.split(r"[\s,]+", l.strip())
    if "20" in fs:
        print("T", i, repr(l[:200]), file=out)
        c += 1
        if c > 40:
            break
out.close()
print("done")
