# -*- coding: utf-8 -*-
"""临时探针 R2-10：两样本"用到的截面"及其期望规格（准则 12 的独立期望集）。"""
import collections
import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = r"D:\AI_Work\PKPM数据解析"
PKG = os.path.join(ROOT, "PKPM-JWD导入导出")
sys.path.insert(0, os.path.join(PKG, "engine"))
sys.path.insert(0, os.path.join(PKG, "test"))
OUT = os.path.join(PKG, "test", "_acc_r2_out")
S = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
import pdt_read  # noqa: E402

for tag, f in (("jwd2db", "jwd2db.report.json"), ("pdt2db", "pdt2db.report.json")):
    d = json.load(open(os.path.join(OUT, f), encoding="utf-8"))
    print("=== %s skipped=%s" % (tag, json.dumps(d.get("skipped"), ensure_ascii=False)[:900]))
    print("    warnings:")
    for w in (d.get("warnings") or [])[:12]:
        print("      - %s" % w[:200])

mp = pdt_read.read_pdt(os.path.join(S, "1_PM.pdt"))
used = collections.Counter(m.section for m in mp.members)
print()
print("pdt used sections (%d distinct): %s" % (len(used), sorted(used.items())))
for sid in sorted(used):
    sec = mp.sections.get(sid)
    print("   %-7s kind=%-3s name=%-16r dims=%s" % (sid, sec.kind, sec.name,
                                                     {k: v for k, v in sec.dims.items() if v}))
unused = sorted(set(mp.sections) - set(used))
print("pdt unused sections: %d -> kinds %s" % (len(unused), collections.Counter(mp.sections[u].kind for u in unused)))
print("pdt slabs thickness set:", sorted({s.thickness for s in mp.slabs}), "walls:", [(w.thickness) for w in mp.walls])
# $DEFWASLABSECTION 名字
raw = open(os.path.join(S, "1_PM.pdt"), "rb").read().decode("gbk")
waslab = re.findall(r"NAME=(T\d+), TYPE=\d+, T1=([\d.]+)", raw)
print("$DEFWASLABSECTION rows:", waslab)
