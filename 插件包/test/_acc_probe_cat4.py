# -*- coding: utf-8 -*-
"""临时探针 4（本会话自建）：SPCOMPONENT 族清单 + TUBE_TUBE-SPEC 全表 + 小直径圆截面。"""
import os, re

SD = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
CAT = os.path.join(SD, "PKPM（PDMS数据库）.txt")
out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_acc_probe_cat4.txt"),
           "w", encoding="utf-8")


def read(p):
    data = open(p, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return data.decode(enc)
        except Exception:
            pass
    return data.decode("gbk", "replace")


t = read(CAT)
lines = t.splitlines()
comps = [l.strip().split(None, 2)[2].strip() for l in lines
         if re.match(r"^NEW\s+SPCOMPONENT\s+\S", l.strip())]
print("NEW SPCOMPONENT count", len(comps), file=out)
fams = {}
for c in comps:
    parts = c.split("/")
    fam = parts[1] if len(parts) > 1 else "(root)"
    fams.setdefault(fam, []).append(c)
print("families (%d):" % len(fams), file=out)
for k in sorted(fams):
    print("  %-38s %4d  e.g. %s" % (k, len(fams[k]), fams[k][0]), file=out)

for fam in ("TUBE_TUBE-SPEC", "USER_CIRCLE-SPEC", "USER_PIPE-SPEC", "USER_TUBE-SPEC",
            "CIRCLE-SPEC", "ROD-SPEC", "PIPE-SPEC", "USER_L-SPEC"):
    v = fams.get(fam)
    print("== %s: %s entries" % (fam, len(v) if v else 0), file=out)
    if v:
        print("   all:", v, file=out)

print("== 所有名字里 D<数字>X 的（直径 <= 60）==", file=out)
for c in comps:
    m = re.search(r"/D(\d+(?:\.\d+)?)X", c)
    if m and float(m.group(1)) <= 60:
        print("   ", c, file=out)
print("== 所有名字里含 20 的圆截面候选（D20 / φ20 / R20）==", file=out)
for c in comps:
    nm = c.rsplit("/", 1)[-1]
    if re.search(r"(?i)(^|[^0-9])(D?20)([^0-9]|$)", nm):
        print("   ", c, file=out)

print("== 目录宏里 SPRFILE 的 PARA 行（看圆形族参数名）==", file=out)
i0 = next((i for i, l in enumerate(lines) if "USER_CIRCLE-SPEC/Circle_Profile" in l), None)
if i0 is not None:
    for l in lines[max(0, i0 - 30):i0 + 12]:
        print("   ", l.rstrip()[:150], file=out)
out.close()
print("done")
