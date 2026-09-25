# -*- coding: utf-8 -*-
"""临时探针 7（本会话自建）：1_PM.pdt 里的 $DEF*SECTION 段（含 SHAPE/NAME）。"""
import os, re

SD = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
P = os.path.join(SD, "1_PM.pdt")
out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_acc_probe_pdtsec.txt"),
           "w", encoding="utf-8")
data = open(P, "rb").read()
t = None
for enc in ("utf-8-sig", "utf-8", "gbk"):
    try:
        t = data.decode(enc)
        print("enc", enc, file=out)
        break
    except Exception:
        pass
lines = t.splitlines()
print("lines", len(lines), file=out)
print("---- $ 段名统计 ----", file=out)
cnt = {}
for l in lines:
    s = l.strip()
    if s.startswith("$") or s.startswith("SECTION") or re.match(r"^\$?[A-Z]{4,}", s):
        key = s.split()[0] if s.split() else s
        cnt[key] = cnt.get(key, 0) + 1
for k, v in sorted(cnt.items()):
    print("   %-30s %d" % (k, v), file=out)
print("---- SECTION 段（含 SHAPE=）----", file=out)
for i, l in enumerate(lines, 1):
    if "SHAPE=" in l:
        print(i, l.strip()[:220], file=out)
print("---- 任何出现 SHAPE 的上下文（前后 4 行）----", file=out)
seen = set()
for i, l in enumerate(lines):
    if "SHAPE" in l:
        a = max(0, i - 3)
        b = min(len(lines), i + 4)
        key = (a, b)
        if key in seen:
            continue
        seen.add(key)
        if len(seen) > 6:
            break
        for j in range(a, b):
            print("   ", j + 1, lines[j].strip()[:200], file=out)
        print("   ---", file=out)
out.close()
print("done")
