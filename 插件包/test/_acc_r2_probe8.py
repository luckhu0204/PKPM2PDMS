# -*- coding: utf-8 -*-
"""临时探针 R2-8：转化表可复现性 + 8 条丢失的大小写对 + 其余待定事实。"""
import collections
import hashlib
import io
import json
import os
import re
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = r"D:\AI_Work\PKPM数据解析"
PKG = os.path.join(ROOT, "PKPM-JWD导入导出")
S = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
R = os.path.join(ROOT, "_recon", "dbsect")
OUT = os.path.join(PKG, "test", "_acc_r2_out")
CJK = re.compile(r"^[\u4e00-\u9fff]+")
NUMP = re.compile(r"^\d+-")
norm = lambda n: CJK.sub("", (n or "").strip()).upper()
norm2 = lambda n: NUMP.sub("", norm(n))

# ---- 1) 转化表 + meta
csvp = os.path.join(PKG, "engine", "section_table.csv")
metap = os.path.join(PKG, "engine", "section_table.meta.json")
meta = json.load(open(metap, encoding="utf-8"))
print("meta keys:", sorted(meta.keys()))
print("meta =", json.dumps(meta, ensure_ascii=False)[:1200])
raw = open(csvp, "rb").read()
print("csv bytes=%d bom=%s sha256=%s" % (len(raw), raw[:3] == b"\xef\xbb\xbf",
                                         hashlib.sha256(raw).hexdigest()))
txt = raw.decode("utf-8-sig")
rows = [l for l in txt.replace("\r\n", "\n").split("\n")]
print("csv lines=%d header=%r" % (len(rows), rows[0]))
print("csv data rows=%d" % (len(rows) - 1 - (1 if rows[-1] == "" else 0)))
src = os.path.join(R, "pkpm_pdms_section_table.csv")
sraw = open(src, "rb").read()
print("source csv bytes=%d sha256=%s" % (len(sraw), hashlib.sha256(sraw).hexdigest()))
stxt = sraw.decode("utf-8-sig").replace("\r\n", "\n").split("\n")
print("source lines=%d" % len(stxt))

# ---- 2) build_section_table.py 接口
bt = open(os.path.join(PKG, "test", "build_section_table.py"), encoding="utf-8").read()
print("build_section_table.py head:", bt[:400].replace("\n", " | ")[:400])
for m in re.finditer(r"add_argument\(([^)]*)\)", bt):
    print("   arg:", m.group(1)[:120])

# ---- 3) 8 条丢失的大小写对（recon DLL 名集 vs 包内表）
tokens = json.load(open(os.path.join(R, "_dll_tokens.json"), encoding="utf-8"))
pairs_raw = json.load(open(os.path.join(R, "_dll_pairs_full.json"), encoding="utf-8"))
rows1 = json.load(open(os.path.join(R, "_match_rows.json"), encoding="utf-8"))
code_re = re.compile(r"^[-\d]+(,[^,]*)*$")
LO, HI = 0x20640, 0x33A90
explicit, carry, last = {}, {}, None
for t in tokens:
    if code_re.match(t["s"]):
        last = t["s"]
    elif last is not None:
        carry[t["s"]] = last
for p in pairs_raw:
    if LO <= p["name_off"] <= HI and LO <= p["code_off"] <= HI:
        explicit[p["name"]] = p["code"]
dll_all = set(list(explicit) + list(carry))
by_norm = collections.defaultdict(list)
for k in dll_all:
    by_norm[norm(k)].append(k)
    by_norm[norm2(k)].append(k)
import csv as _csv
with open(csvp, encoding="utf-8-sig", newline="") as fh:
    recs = list(_csv.DictReader(fh))
by_norm_b = collections.defaultdict(list)
for r in recs:
    e = json.loads(r.get("extra_json") or "{}")
    names = [str(e.get("dll_table_entry") or "")] + re.findall(r"dll=([^;]+)", str(e.get("name_variants") or ""))
    for n in names:
        n = n.strip()
        if n:
            by_norm_b[norm(n)].append(n)
            by_norm_b[norm2(n)].append(n)
lost = []
for r in rows1:
    a = [v for v in by_norm.get(norm2(r["pkpm"]), []) if v != r["pkpm"]]
    b = [v for v in by_norm_b.get(norm2(r["pkpm"]), []) if v != r["pkpm"]]
    if a and not b:
        lost.append((r["line"], r["pkpm"], sorted(set(a))[:3]))
print("rows with a DLL variant that the in-package table lost = %d" % len(lost))
for x in lost:
    print("   line=%s pkpm=%r dll=%s" % x)

# ---- 4) SPRFILE macro-only
DB = os.path.join(S, "PKPM（PDMS数据库）.txt")
text = open(DB, "rb").read().decode("utf-8-sig")
logical, buf = [], ""
for ln in text.replace("\r\n", "\n").split("\n"):
    s = ln.rstrip()
    if s.endswith("$"):
        buf += s[:-1] + " "
        continue
    logical.append((buf + s).strip())
    buf = ""
spr = {l.split(None, 2)[2] for l in logical if l.startswith("NEW SPRFILE")}
comp = {l.split(None, 2)[2] for l in logical if l.startswith("NEW SPCOMPONENT")}
mrows = []
for i, ln in enumerate(open(os.path.join(S, "PKPM转PDMS截面匹配文件.txt"), "rb").read().decode("gbk").replace("\r\n", "\n").split("\n"), 1):
    s = ln.strip()
    if not s or s.startswith("//") or set(s) == {"/"} or "," not in s:
        continue
    mrows.append((i, s.split(",", 1)[0].strip(), " ".join(s.split(",", 1)[1].split())))
rhs = {" ".join(r[2].split()) for r in mrows}
rhs_n = {r if r.startswith("/") else "/" + r for r in rhs}
leaves = {r.lstrip("/").split("/")[-1] for r in rhs_n}
print("SPRFILE=%d  distinct leaf names used by matching file=%d  SPRFILE not used=%d"
      % (len(spr), len(leaves), len(spr - leaves)))
print("SPCOMPONENT not used = %d" % len(comp - rhs_n))
