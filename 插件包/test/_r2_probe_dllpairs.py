# -*- coding: utf-8 -*-
"""R2 探针 5（本会话自建）：recon DLL 名/码对里，那 8 个键的另一拼写是什么、配什么码。"""
import collections
import json
import os

REC = r"D:\AI_Work\PKPM数据解析\_recon\dbsect"
OUT = open(r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\test\_r2_probe_dllpairs.txt", "w",
           encoding="utf-8")

pairs = json.load(open(os.path.join(REC, "_dll_pairs_full.json"), encoding="utf-8"))
tokens = json.load(open(os.path.join(REC, "_dll_tokens.json"), encoding="utf-8"))
print("pairs:", len(pairs), "tokens:", len(tokens), file=OUT)
print("pair[0]:", json.dumps(pairs[0], ensure_ascii=False), file=OUT)

WANT = ["3-L25x16x3", "L25x16x3", "3-L45x28x3", "L45x28x3", "3-L50x32x4", "L50x32x4",
        "3-L56x36x3", "L56x36x3", "3-L56x36x4", "L56x36x4", "3-L56x36x5", "L56x36x5",
        "8-B100*4.00", "6-B100*4.00", "9-B120*80*4.00", "7-B120*80*4.00",
        "L50X32X4", "L56X36X3"]

by_name = collections.defaultdict(list)
for p in pairs:
    by_name[p.get("name")].append(p)
print("---- pairs 里这些名字 ----", file=OUT)
for n in WANT:
    for p in by_name.get(n, []):
        print("  %-16r code=%-40r name_off=%s code_off=%s"
              % (n, p.get("code"), p.get("name_off"), p.get("code_off")), file=OUT)

print("---- tokens 里这些名字（上下文：前一条 token）----", file=OUT)
idx = {t["s"]: i for i, t in enumerate(tokens)}
for n in WANT:
    i = idx.get(n)
    if i is None:
        print("  %-16r 不在 token 流" % n, file=OUT)
        continue
    ctx = [t["s"] for t in tokens[max(0, i - 3):i + 3]]
    print("  %-16r 位置 %-6d 上下文 %s" % (n, i, ctx), file=OUT)

print("---- 含 'L25x16x3' 子串的所有 token ----", file=OUT)
for t in tokens:
    s = t["s"]
    if "25x16x3" in s.lower():
        print("   %r" % (s,), file=OUT)
print("---- 含 '100*4.00' 的所有 token ----", file=OUT)
for t in tokens:
    s = t["s"]
    if "100*4.00" in s.lower():
        print("   %r" % (s,), file=OUT)
print("---- 含 '120*80*4.00' 的所有 token ----", file=OUT)
for t in tokens:
    s = t["s"]
    if "120*80*4" in s.lower():
        print("   %r" % (s,), file=OUT)
OUT.close()
print("done")
