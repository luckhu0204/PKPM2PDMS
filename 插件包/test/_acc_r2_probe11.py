# -*- coding: utf-8 -*-
"""临时探针 R2-11：检查 9 的文件尾真相 + 检查 14 的 19 行投影差异。"""
import collections
import csv
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
PKG = r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出"
OUT = os.path.join(PKG, "test", "_acceptance_r2_out")
p = os.path.join(OUT, "r2_jwd2pdt.pdt")
raw = open(p, "rb").read()
print("tail bytes = %r" % raw[-24:])
txt = raw.decode("gbk")
lines = txt.replace("\r\n", "\n").split("\n")
print("last 6 lines = %r" % lines[-6:])
print("lone LF in tail? %d" % sum(1 for i, c in enumerate(raw[-24:]) if c == 0x0A and raw[-24:][i - 1] != 0x0D))
print("ends with $END\\r\\n\\r\\n ? %s" % raw.endswith(b"$END\r\n\r\n"))
print("blank lines immediately before $END: %d"
      % sum(1 for l in lines[-6:-1] if not l.strip()))

# ---- 检查 14：19 行投影差异
csvp = os.path.join(PKG, "engine", "section_table.csv")
meta = json.load(open(os.path.join(PKG, "engine", "section_table.meta.json"), encoding="utf-8"))
src = meta["source"]
srecs = list(csv.DictReader(io.StringIO(open(src, encoding="utf-8-sig").read())))
recs = list(csv.DictReader(io.StringIO(open(csvp, encoding="utf-8-sig").read())))
print("src rows=%d out rows=%d" % (len(srecs), len(recs)))
print("src cols (%d): %s" % (len(srecs[0]), list(srecs[0].keys())))
diffcols = collections.Counter()
examples = []
for a, b in zip(srecs, recs):
    want_key = (b["pkpm_name"] or b["pdms_spec_path"])
    kind = next((v for v in (a.get("jwd_kind"), a.get("pdt_kind")) if v not in (None, "")), "0")
    try:
        kind = str(int(float(kind)))
    except (TypeError, ValueError):
        kind = "0"
    fam = a.get("family_code") or "0"
    try:
        fam = str(int(float(fam)))
    except (TypeError, ValueError):
        fam = "0"
    pairs = [("key", b["key"], want_key),
             ("pkpm_name", b["pkpm_name"], (a.get("pkpm_name") or "").strip()),
             ("family_code", b["family_code"], fam),
             ("kind", b["kind"], kind),
             ("shapeval", b["shapeval"], (a.get("shapeval_encoding") or "")),
             ("pdms_spec_path", b["pdms_spec_path"], (a.get("pdms_spec_path") or "").strip()),
             ("confidence", b["confidence"], (a.get("confidence") or "").strip()),
             ("source", b["source"], (a.get("source") or "").strip())]
    for name, got, want in pairs:
        if got != want:
            diffcols[name] += 1
            if len(examples) < 12:
                examples.append((name, "out=%r" % got, "src=%r" % want,
                                 a.get("pkpm_name"), a.get("pdms_spec_path")))
print("diff cols:", dict(diffcols))
for e in examples:
    print("   ", e)
