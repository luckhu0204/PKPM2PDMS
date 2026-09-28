# -*- coding: utf-8 -*-
"""临时探针 10：报告 sections.detail 实际内容 + 原件是否含 303 原名。"""
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
rep = json.load(open(r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\test\_acc_tmp\JLCJ2.report.json", encoding='utf-8'))
print("keys:", sorted(rep.keys()))
print("counts:", rep["counts"])
print("stats.commands:", rep.get("stats", {}).get("commands"))
print("stats.secmap:", {k: v for k, v in (rep.get("stats", {}).get("secmap") or {}).items() if k != 'prefixes'})
print()
for d in rep["sections"]["detail"]:
    print("  table=%-6s id=%-7s kind=%-4s name=%-16r status=%-11s source=%-9s spec=%-45s used_by=%s" %
          (d["table"], d["id"], d["kind"], d["name"], d["status"], d["source"], d["spec_path"], d["used_by"]))
print()
print("unresolved ids:", [(d["table"], d["id"], d["name"]) for d in rep["sections"]["unresolved"]])
print("geometry_anomalies:", len(rep["geometry_anomalies"]))
from collections import Counter
print(Counter(a.split(':')[0] for a in rep["geometry_anomalies"]))
print("skipped:", json.dumps(rep["skipped"], ensure_ascii=False)[:800])
print()
MAP = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\PKPM转PDMS截面匹配文件.txt"
txt = open(MAP, 'rb').read().decode('gbk')
for needle in ('薄壁', '热轧无缝', 'HN450X200', '[18a', '矩'):
    hits = [l.strip() for l in txt.replace('\r\n', '\n').split('\n') if needle in l]
    print("map contains %r: %d %s" % (needle, len(hits), hits[:3]))
