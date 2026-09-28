# -*- coding: utf-8 -*-
"""R2 探针 4（本会话自建）：源表 vs 包内表 的 dll 标注（针对 8 行差额涉及的 pkpm 名）。"""
import csv
import io
import json
import os

ROOT = r"D:\AI_Work\PKPM数据解析"
SRC = os.path.join(ROOT, r"_recon\dbsect\pkpm_pdms_section_table.csv")
BUILT = os.path.join(ROOT, r"PKPM2PDMS导入导出\engine\section_table.csv")
OUT = open(os.path.join(ROOT, r"PKPM2PDMS导入导出\test\_r2_probe_srcdll.txt"), "w",
           encoding="utf-8")

NAMES = ["3-L25x16x3", "L25X16X3", "3-L45x28x3", "L45X28X3", "3-L50X32X4", "L50X32X4",
         "3-L56x36x3", "L56X36X3", "3-L56x36x4", "L56X36X4", "3-L56x36x5", "L56X36X5",
         "8-B100*4.00", "6-B100*4.00", "9-B120*80*4.00", "7-B120*80*4.00"]


def load(p):
    return list(csv.DictReader(io.StringIO(open(p, "rb").read().decode("utf-8-sig"))))


srecs = load(SRC)
brecs = load(BUILT)
print("源表行 %d；包内表行 %d" % (len(srecs), len(brecs)), file=OUT)
for n in NAMES:
    s = [r for r in srecs if (r.get("pkpm_name") or "").strip() == n]
    b = [r for r in brecs if (r.get("pkpm_name") or "").strip() == n
         or (r.get("key") or "").strip() == n]
    print("== %r 源表 %d 条 / 包内 %d 条" % (n, len(s), len(b)), file=OUT)
    for r in s:
        print("   源: family_code=%r shapeval=%r spec=%r in_dll=%r dll_source=%r "
              "dll_table_entry=%r name_variants=%r"
              % (r.get("family_code"), r.get("shapeval_encoding"), r.get("pdms_spec_path"),
                 r.get("in_dll_table"), r.get("dll_code_source"),
                 r.get("dll_table_entry"), r.get("name_variants")), file=OUT)
    for r in b:
        e = json.loads(r.get("extra_json") or "{}")
        print("   包: key=%r family=%r kind=%r spec=%r conf=%r src=%r dll_source=%r "
              "dll_entry=%r"
              % (r.get("key"), r.get("family_code"), r.get("kind"), r.get("pdms_spec_path"),
                 r.get("confidence"), r.get("source"), e.get("dll_code_source"),
                 e.get("dll_table_entry")), file=OUT)
        print("        extra.name_variants=%r" % (e.get("name_variants"),), file=OUT)
        print("        extra 键: %s" % sorted(e.keys()), file=OUT)
OUT.close()
print("done")
