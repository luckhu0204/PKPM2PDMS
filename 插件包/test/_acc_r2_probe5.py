# -*- coding: utf-8 -*-
"""临时探针 R2-5：在 recon 脚本里找 759 大小写差异的判定规则。"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
p = r"D:\AI_Work\PKPM数据解析\_recon\dbsect\21_final.py"
src = open(p, encoding="utf-8", errors="replace").read()
lines = src.split("\n")
keys = ["759", "case", "variant", "lower", "spell", "\u5927\u5c0f\u5199", "\u62fc\u5199"]
for n, l in enumerate(lines, 1):
    if any(k in l for k in keys):
        print("%4d %s" % (n, l[:220]))
print("---- total lines", len(lines))
