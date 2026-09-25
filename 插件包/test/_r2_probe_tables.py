# -*- coding: utf-8 -*-
"""R2 探针（本会话自建）：查两张表的列与缺失 DLL 拼写的行。"""
import csv
import io
import json
import os
import re

ROOT = r"D:\AI_Work\PKPM数据解析"
SRC = os.path.join(ROOT, r"_recon\dbsect\pkpm_pdms_section_table.csv")
BUILT = os.path.join(ROOT, r"PKPM-JWD导入导出\engine\section_table.csv")
META = os.path.join(ROOT, r"PKPM-JWD导入导出\engine\section_table.meta.json")
MAP = (r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
       r"\PKPM转PDMS截面匹配文件.txt")
DLLTOK = os.path.join(ROOT, r"_recon\dbsect\_dll_tokens.json")

TARGET_LINES = {250: "3-L25x16x3", 256: "3-L45x28x3", 259: "3-L50X32X4",
                260: "3-L56x36x3", 261: "3-L56x36x4", 262: "3-L56x36x5",
                1362: "8-B100*4.00", 1523: "9-B120X80X4.00"}


def load(p):
    raw = open(p, "rb").read()
    t = raw.decode("utf-8-sig")
    return raw, t, list(csv.DictReader(io.StringIO(t)))


sraw, stxt, srecs = load(SRC)
braw, btxt, brecs = load(BUILT)
print("SRC bytes", len(sraw), "rows", len(srecs), "cols", list(srecs[0].keys()))
print("BUILT bytes", len(braw), "rows", len(brecs), "cols", list(brecs[0].keys()))
print("meta:", json.dumps(json.load(open(META, encoding="utf-8")), ensure_ascii=False)[:600])

# 匹配文件的左值（用 secmap 的解析规则）
mtxt = open(MAP, "rb").read().decode("gbk")
rows = []
for i, line in enumerate(mtxt.replace("\r\n", "\n").split("\n"), 1):
    s = line.strip()
    if not s or s.startswith("//") or set(s) == {"/"} or "," not in line:
        continue
    left, right = line.split(",", 1)
    rows.append((i, left.strip(), " ".join(right.split())))
print("match rows", len(rows))

for lineno, left in TARGET_LINES.items():
    hit = [r for r in rows if r[0] == lineno]
    print("--- 行 %d %r -> %r" % (lineno, left, hit[0][1] if hit else None))
    if not hit:
        continue
    want = hit[0][1]
    s = [r for r in srecs if (r.get("pkpm_name") or "").strip() == want
         or (r.get("key") or "").strip() == want]
    b = [r for r in brecs if (r.get("pkpm_name") or "").strip() == want
         or (r.get("key") or "").strip() == want]
    print("   源表命中 %d 条；包内表命中 %d 条" % (len(s), len(b)))
    if s:
        print("   源表 extra:", (s[0].get("extra") or "")[:400])
        print("   源表 name_variants:", (s[0].get("name_variants") or "")[:200])
    if b:
        print("   包内 extra_json:", (b[0].get("extra_json") or "")[:400])

tok = json.load(open(DLLTOK, encoding="utf-8"))
print("DLL tokens type:", type(tok).__name__,
      (list(tok)[:5] if isinstance(tok, dict) else len(tok)))
