# -*- coding: utf-8 -*-
"""临时探针 R2-9：准则 9/10/12/13/14 的关键事实。"""
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
PKG = os.path.join(ROOT, "PKPM2PDMS导入导出")
CLI = os.path.join(PKG, "engine", "cli.py")
OUT = os.path.join(PKG, "test", "_acc_r2_out")
S = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
sys.path.insert(0, os.path.join(PKG, "engine"))
sys.path.insert(0, os.path.join(PKG, "test"))
import pdt_read, jwd_read  # noqa: E402  (SUT)

# ---------- a) dbsections --from-builtin 可复现性
for fmt, name in (("csv", "frombuiltin.csv"), ("json", "frombuiltin.json")):
    p = subprocess.run([sys.executable, CLI, "dbsections", "--from-builtin",
                        "--out", os.path.join(OUT, name), "--format", fmt],
                       cwd=ROOT, capture_output=True)
    print("dbsections --from-builtin --format %s exit=%d" % (fmt, p.returncode))
builtin = os.path.join(PKG, "engine", "section_table.csv")
b1 = open(builtin, "rb").read()
b2 = open(os.path.join(OUT, "frombuiltin.csv"), "rb").read()
print("builtin csv sha=%s ; from-builtin csv sha=%s ; identical=%s"
      % (hashlib.sha256(b1).hexdigest()[:16], hashlib.sha256(b2).hexdigest()[:16], b1 == b2))
j = json.load(open(os.path.join(OUT, "frombuiltin.json"), encoding="utf-8"))
print("from-builtin json type=%s len=%s" % (type(j).__name__, len(j) if hasattr(j, "__len__") else "?"))

# ---------- b) jwd2pdt 产物结构 + 读回
pt = open(os.path.join(OUT, "jwd2pdt.pdt"), "rb").read()
print("pdt bytes=%d bom=%s loneLF=%d" % (len(pt), pt[:3] == b"\xef\xbb\xbf",
                                         sum(1 for i, c in enumerate(pt) if c == 0x0A and (i == 0 or pt[i - 1] != 0x0D))))
lines = pt.decode("gbk").replace("\r\n", "\n").split("\n")
segs = [l.strip() for l in lines if l.startswith("$")]
print("pdt segments in order (%d): %s" % (len(segs), segs))
print("first 4 lines:", [repr(l) for l in lines[:4]])
print("last 4 lines:", [repr(l) for l in lines[-4:]])
# 段行数
cnt = collections.Counter()
cur = None
for l in lines:
    if l.startswith("$"):
        cur = l.strip()
        continue
    if l.strip():
        cnt[cur] += 1
print("records per segment:", dict(cnt))
m1 = jwd_read.read_jwd(os.path.join(S, "JLCJ2.jwd"))
m2 = pdt_read.read_pdt(os.path.join(OUT, "jwd2pdt.pdt"))
print("model1 counts:", json.dumps(m1.counts(), ensure_ascii=False))
print("model2 counts:", json.dumps(m2.counts(), ensure_ascii=False))


def bbox(m):
    pts = [p for x in m.members for p in (x.start, x.end)]
    for s in m.slabs:
        pts.extend((p[0], p[1], s.z) for p in s.polygon)
    for w in m.walls:
        pts.extend(w.loop)
    return (min(p[0] for p in pts), min(p[1] for p in pts), min(p[2] for p in pts),
            max(p[0] for p in pts), max(p[1] for p in pts), max(p[2] for p in pts))


print("bbox1:", bbox(m1))
print("bbox2:", bbox(m2))
print("member z set equal:", sorted({round(x.start[2], 6) for x in m1.members} | {round(x.end[2], 6) for x in m1.members})
      == sorted({round(x.start[2], 6) for x in m2.members} | {round(x.end[2], 6) for x in m2.members}))

# ---------- c) DLL 格式串（自己在字节里搜 UTF-16LE）
dll = open(os.path.join(S, "P-TRANS", "PDMSxCA_Addin121.dll"), "rb").read()
want = ["ID={0}, NAME={1}, SHAPE={2}", "KIND={0}, B1={1}", "T1={0}, T2={1}",
        "M={0}, RI={1}", "EXI= {0}", ",{0}, {1}", "EXR= {0}",
        "ID= {0}, X= {1", "ID={0}, NODES={1}", "ID={0}, TYPE={1}, NETID={2}",
        "ID={0}, TYPE={1}, SECTID={2}", "NO={0}, HI={1}", "ID={0}, NAME={1}, TYPE={2}, T1={3",
        "ID={0}, NAME={1}, TYPE={2}, ES={3", "NUB={0}, NETID=", "ID={0}, NUB={1}", "{0:F3}"]
for w in want:
    b = w.encode("utf-16-le")
    i = dll.find(b)
    print("DLL %-42r off=%s" % (w, hex(i) if i >= 0 else None))

# ---------- d) 两个建模型宏的层结构
for tag, f in (("jwd", "jwd2pdms.mac"), ("pdt", "pdt2pdms.mac")):
    t = open(os.path.join(OUT, f), "rb").read().decode("gbk")
    ls = t.split("\r\n")
    frmw = [l.split()[-1] for l in ls if l.strip().startswith("NEW FRMW")]
    us = sorted({float(m.group(1)) for l in ls if l.strip().startswith(("POSS E", "POSE E", "POS E"))
                 for m in [re.search(r"U (-?[\d.]+)\s*$", l.strip())] if m})
    print("%s macro: FRMW=%s" % (tag, frmw))
    print("   distinct U=%s" % us)

# ---------- e) jwd2db/pdt2db 覆盖（期望规格集由我自算）
MAP = os.path.join(S, "PKPM转PDMS截面匹配文件.txt")
EXTRA = os.path.join(PKG, "engine", "secmap_extra.txt")


def parse_map(paths):
    fwd = {}
    for p in paths:
        for line in open(p, "rb").read().decode("gbk").replace("\r\n", "\n").split("\n"):
            s = line.strip()
            if not s or s.startswith("//") or s.startswith("@") or set(s) == {"/"} or "," not in s:
                continue
            a, b = s.split(",", 1)
            b = " ".join(b.split())
            fwd[a.strip()] = b if b.startswith("/") else "/" + b
    return fwd


fwd = parse_map([MAP, EXTRA])
print("mapping rows=%d" % len(fwd))
for tag, f in (("jwd2db", "jwd2db.mac"), ("pdt2db", "pdt2db.mac")):
    t = open(os.path.join(OUT, f), "rb").read().decode("ascii")
    comps = {l.split()[-1] for l in t.replace("\r\n", "\n").split("\n")
             if l.strip().startswith("NEW SPCOMPONENT")}
    print("%s: unique SPCOMPONENT=%d" % (tag, len(comps)))
    for spec in ("/Concrete_Slab-SPEC/T100", "/Concrete_Slab-SPEC/T120",
                 "/Concrete_Wall-SPEC/WALL-600", "/USER_RECT-SPEC/Rectangle_Profile",
                 "/USER_CIRCLE-SPEC/Circle_Profile", "/USER_H-SPEC/H_Profile"):
        print("    %-45s %s" % (spec, "有" if spec in comps else "缺"))

# ---------- f) 闭环：a.jwd 的截面 → 我的期望规格 vs closure2.mac
dbj = os.path.join(OUT, "db2jwd_from_jwd2db.jwd")
m3 = jwd_read.read_jwd(dbj)
print("reverse .jwd sections:", len(m3.sections), "tables:", collections.Counter(s.table for s in m3.sections.values()))
exp = set()
for s in m3.sections.values():
    cands = []
    if s.name:
        cands.append(s.name)
    if s.kind == 26:
        sub = s.dims.get("subtype")
        if sub is not None and s.name:
            cands.append("%g-%s" % (sub, s.name) if isinstance(sub, float) else "%s-%s" % (sub, s.name))
    if s.kind == 303 and s.dims.get("spec_str"):
        cands.append("%g-%s" % (s.dims.get("lib_family"), s.dims["spec_str"]))
    hit = next((fwd[c] for c in cands if c in fwd), None)
    if hit is None and s.kind == 1:
        hit = "/USER_RECT-SPEC/Rectangle_Profile"
    if hit is None and s.kind == 3:
        hit = "/USER_CIRCLE-SPEC/Circle_Profile"
    if hit is None and s.kind == 2:
        hit = "/USER_H-SPEC/H_Profile"
    exp.add(hit or "<none:%s:%s>" % (s.id, s.kind))
t2 = open(os.path.join(OUT, "closure2.mac"), "rb").read().decode("ascii")
c2 = {l.split()[-1] for l in t2.replace("\r\n", "\n").split("\n")
      if l.strip().startswith("NEW SPCOMPONENT")}
print("expected(closure step2) =", sorted(exp))
print("actual   (closure2.mac) =", sorted(c2))
print("equal =", exp == c2, "| actual - expected =", sorted(c2 - exp), "| expected - actual =", sorted(exp - c2))
