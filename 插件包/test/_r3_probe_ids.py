# -*- coding: utf-8 -*-
"""R3 探针 2（本会话自建）：按段核对全局流水号 N 的跨类唯一性（NET/SETELEMENT 共体除外）。"""
import collections
import os
import re
import sys

sys.path.insert(0, r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\engine")
import jwd_read  # noqa: E402
import pdt_read  # noqa: E402
import pdt_write  # noqa: E402

TMP = r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\test\_acc_tmp"
P = os.path.join(TMP, "r3_jwd2pdt.pdt")
model = jwd_read.read_jwd(
    r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\JLCJ2.jwd")
pdt_write.write_pdt(model, P, pdt_write.PdtOptions(skeleton="full"))
t = open(P, "rb").read().decode("gbk")

# 按段收集 ID（只看各段的主行 ID=）
seg = None
per_seg = collections.defaultdict(list)
for ln in t.splitlines():
    s = ln.strip()
    if s.startswith("$"):
        seg = s.split()[0]
        continue
    m = re.match(r"ID=\s*(\d+)\s*,", s)
    if m and seg:
        per_seg[seg].append(int(m.group(1)))

n_of = {}
for k, ids in per_seg.items():
    ns = [i // 100 for i in ids]
    print("%-20s 行数 %-5d N 范围 [%d..%d]  N 唯一=%s"
          % (k, len(ids), min(ns), max(ns), len(set(ns)) == len(ns)))
    if k in ("$NET", "$SETELEMENT"):
        continue          # 两者按 §j.3 有意共享同一批 ID
    for n in ns:
        n_of.setdefault(n, []).append(k)

conf = {n: v for n, v in n_of.items() if len(v) > 1}
print("除 $NET/$SETELEMENT 共体外，跨类复用的 N：", len(conf), "（应为 0）")
for n, v in sorted(conf.items())[:8]:
    print("   N=%d -> %s" % (n, v))
story = per_seg.get("$STORY", [])
print("$STORY 的 ID（楼层号，非 N×100 体系）：", story)
