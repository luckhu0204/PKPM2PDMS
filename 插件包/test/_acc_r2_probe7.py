# -*- coding: utf-8 -*-
"""临时探针 R2-7：用 recon 的 DLL token 数据独立复算 759 对（自己实现判定规则）。"""
import collections
import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
R = r"D:\AI_Work\PKPM数据解析\_recon\dbsect"
PKG = r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出"
CJK = re.compile(r"^[\u4e00-\u9fff]+")
NUMP = re.compile(r"^\d+-")
norm = lambda n: CJK.sub("", (n or "").strip()).upper()
norm2 = lambda n: NUMP.sub("", norm(n))

tokens = json.load(open(os.path.join(R, "_dll_tokens.json"), encoding="utf-8"))
dll_pairs = json.load(open(os.path.join(R, "_dll_pairs_full.json"), encoding="utf-8"))
rows1 = json.load(open(os.path.join(R, "_match_rows.json"), encoding="utf-8"))
print("tokens=%d dll_pairs=%d match_rows=%d" % (len(tokens), len(dll_pairs), len(rows1)))
print("token sample:", tokens[:3])
print("pair sample:", dll_pairs[:3])
print("row sample:", rows1[:3])

code_re = re.compile(r"^[-\d]+(,[^,]*)*$")
LO, HI = 0x20640, 0x33A90
explicit, carry, last = {}, {}, None
for t in tokens:
    if code_re.match(t["s"]):
        last = t["s"]
    elif last is not None:
        carry[t["s"]] = last
for p in dll_pairs:
    if LO <= p["name_off"] <= HI and LO <= p["code_off"] <= HI:
        explicit[p["name"]] = p["code"]
dll_all = set(list(explicit) + list(carry))
print("dll_all = %d (explicit %d + carry %d)" % (len(dll_all), len(explicit), len(carry)))

by_norm = collections.defaultdict(list)
for k in dll_all:
    by_norm[norm(k)].append(k)
    by_norm[norm2(k)].append(k)
pairs = []
for r in rows1:
    for raw in by_norm.get(norm2(r["pkpm"]), []):
        if raw != r["pkpm"]:
            pairs.append((r["pkpm"], raw))
            break
print("recon-rule case pairs = %d" % len(pairs))
print("samples:", pairs[:5])

# 包内表（engine/section_table.csv）的同口径复算
import csv
with open(os.path.join(PKG, "engine", "section_table.csv"), encoding="utf-8-sig", newline="") as fh:
    recs = list(csv.DictReader(fh))
by_norm_b = collections.defaultdict(list)
for r in recs:
    e = json.loads(r.get("extra_json") or "{}")
    names = [str(e.get("dll_table_entry") or "")]
    names += re.findall(r"dll=([^;]+)", str(e.get("name_variants") or ""))
    for n in names:
        n = n.strip()
        if n:
            by_norm_b[norm(n)].append(n)
            by_norm_b[norm2(n)].append(n)
pairs_b = []
missing = []
for r in rows1:
    hit = None
    for raw in by_norm_b.get(norm2(r["pkpm"]), []):
        if raw != r["pkpm"]:
            hit = raw
            break
    if hit:
        pairs_b.append((r["pkpm"], hit))
    else:
        missing.append(r["pkpm"])
print("builtin-table-rule case pairs = %d ; matching rows without a variant = %d"
      % (len(pairs_b), len(missing)))
print("missing sample (first 20):", missing[:20])
