# -*- coding: utf-8 -*-
"""临时探针（本会话自建）：在样本侧找 Kind=3 / φ20 的规格证据。"""
import io, os, re, sys

SD = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"


def read(p):
    data = open(p, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return data.decode(enc)
        except Exception:
            pass
    return data.decode("gbk", "replace")


# ---- 1) 目录宏：SPEC 属主 + 截面名
cat = os.path.join(SD, "PKPM（PDMS数据库）.txt")
t = read(cat)
owners = re.findall(r"NEW\s+(?:SPCOMPONENT|SPRFILE)\s+(\S+)", t)
print("catalogue lines", t.count("\n"), "SPCOMPONENT/SPRFILE matches", len(owners))
specowners = sorted({m.group(1) for m in re.finditer(r"\b(\S+-SPEC)\b", t)})
print("SPEC owners (%d):" % len(specowners), specowners[:60])
# 含 20 的圆/管/钢条目
cands = sorted({m.group(1) for m in re.finditer(r"/([A-Z_0-9]*)-(?:SPEC|CATALOGUE)[^\s]*", t)})
print("families:", cands[:80])
name_lines = [l for l in t.splitlines() if re.search(r"NEW SPRFILE", l)]
print("NEW SPRFILE count", len(name_lines))
for l in name_lines:
    s = l.strip()
    if re.search(r"(?i)(D20|20X|X20|φ20|ROD|BAR|CIRCLE|TUBE)", s):
        print("   ", s)
print("---- all SPRFILE names, unique families ----")
fam = {}
for l in name_lines:
    s = l.strip().split()[-1]
    f = s.split("/")[1] if s.count("/") > 1 else s
    fam.setdefault(f, []).append(s)
for k, v in sorted(fam.items()):
    print("%-40s %d  e.g. %s" % (k, len(v), v[0]))
print("---- lines mentioning KIND/圆形/圆钢 ----")
for i, l in enumerate(t.splitlines(), 1):
    if re.search(r"圆钢|圆形|圆管|钢管", l):
        print(i, l.strip()[:140])
