# -*- coding: utf-8 -*-
"""临时探针 8（本会话自建）：用户匹配文件里与「圆/管」相关的条目 + .pdt 的 KIND=3 块。"""
import os, re

SD = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
MAP = os.path.join(SD, "PKPM转PDMS截面匹配文件.txt")
PDT = os.path.join(SD, "1_PM.pdt")
out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_acc_probe_round.txt"),
           "w", encoding="utf-8")


def read(p):
    data = open(p, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return data.decode(enc)
        except Exception:
            pass
    return data.decode("gbk", "replace")


t = read(MAP)
print("==== 匹配文件里含 圆/管/TUBE/PIPE/CIRCLE 的条目 ====", file=out)
for i, l in enumerate(t.splitlines(), 1):
    s = l.strip()
    if s.startswith("//"):
        continue
    if re.search(r"圆|管|TUBE|PIPE|CIRCLE", s):
        print(i, s[:160], file=out)

p = read(PDT).splitlines()
print("==== 1_PM.pdt 的 KIND=3 块（含前后）====", file=out)
for i, l in enumerate(p):
    if l.strip().startswith("KIND=3,"):
        for j in range(max(0, i - 2), min(len(p), i + 4)):
            print(j + 1, p[j].rstrip()[:200], file=out)
        print("---", file=out)
print("==== 1_PM.pdt 里所有 SHAPE=3 的块 ====", file=out)
for i, l in enumerate(p):
    if re.search(r"SHAPE=3\b", l):
        for j in range(max(0, i - 1), min(len(p), i + 6)):
            print(j + 1, p[j].rstrip()[:200], file=out)
        print("---", file=out)
out.close()
print("done")
