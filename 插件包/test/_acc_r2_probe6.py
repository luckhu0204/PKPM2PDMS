# -*- coding: utf-8 -*-
"""临时探针 R2-6：大小写/写法差异对数的独立重算（DLL 串 + 目录宏 + 匹配文件 + 包内表）。"""
import collections
import csv
import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
S = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
MAP = os.path.join(S, "PKPM转PDMS截面匹配文件.txt")
DLL = os.path.join(S, "P-TRANS", "PDMSxCA_Addin121.dll")
PKG = r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出"
BUILTIN = os.path.join(PKG, "engine", "section_table.csv")
CJK = re.compile(r"^[\u4e00-\u9fff]+")
NUMP = re.compile(r"^\d+-")
norm = lambda n: CJK.sub("", (n or "").strip()).upper()
norm2 = lambda n: NUMP.sub("", norm(n))

# 匹配文件左值
rows = []
for i, ln in enumerate(open(MAP, "rb").read().decode("gbk").replace("\r\n", "\n").split("\n"), 1):
    s = ln.strip()
    if not s or s.startswith("//") or set(s) == {"/"} or "," not in s:
        continue
    rows.append((i, s.split(",", 1)[0].strip()))
print("matching lefts = %d" % len(rows))

# DLL UTF-16LE 名字（几种过滤口径）
dll = open(DLL, "rb").read()
dtxt = dll.decode("utf-16-le", "ignore")
NAME_CHARS = re.compile(r"^[A-Za-z0-9\[\]\+\-\*\.xX/_]+$")
cand = set()
for m in re.finditer(r"[\x20-\x7e]{2,40}", dtxt):
    s = m.group(0).strip()
    if not NAME_CHARS.match(s):
        continue
    if not re.search(r"[A-Za-z]", s):
        continue
    if "." in s and not s.startswith(("[", "L", "C", "H", "I", "T", "Z", "D", "B", "P", "R", "U")):
        continue
    cand.add(s)
print("dll name candidates = %d" % len(cand))

dll_by_norm = collections.defaultdict(list)
for k in cand:
    dll_by_norm[norm(k)].append(k)
    dll_by_norm[norm2(k)].append(k)

pairs_n2 = [(a, v) for _i, a in rows for v in dll_by_norm.get(norm2(a), []) if v != a]
pairs_n1 = [(a, v) for _i, a in rows for v in dll_by_norm.get(norm(a), []) if v != a]
print("norm2-rule pairs (one per matching row, first variant) = %d" % len({a for a, _v in pairs_n2}))
print("norm-rule  pairs (one per matching row, first variant) = %d" % len({a for a, _v in pairs_n1}))
print("samples:", pairs_n2[:5])

# 包内表：name_variants / dll 列
with open(BUILTIN, encoding="utf-8-sig", newline="") as fh:
    rd = csv.DictReader(fh)
    cols = rd.fieldnames
    recs = list(rd)
print("builtin cols = %s" % cols)
print("builtin rows = %d" % len(recs))
ex = recs[0].get("extra_json", "")
print("extra_json sample keys:", sorted(json.loads(ex).keys())[:40])
cnt_variant = 0
for r in recs:
    e = json.loads(r.get("extra_json") or "{}")
    nv = e.get("name_variants") or ""
    dlls = [t[4:] for t in nv.split(";") if t.strip().startswith("dll=")]
    match = [t[6:] for t in nv.split(";") if t.strip().startswith("match=")]
    if dlls and match and any(d != match[0] for d in dlls):
        cnt_variant += 1
print("builtin rows with a differing dll spelling = %d" % cnt_variant)
