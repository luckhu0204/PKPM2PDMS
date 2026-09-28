# -*- coding: utf-8 -*-
"""临时探针 3（验收测试编写用，跑完即删）：pdt/jwd 对比 + 往返表计数。"""
import io
import os
import sqlite3
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ENG = r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\engine"
sys.path.insert(0, ENG)
OUT = r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\test\_acc_tmp"
os.makedirs(OUT, exist_ok=True)

import jwd_read, jwd_write, pdt_read  # noqa: E402

JWD = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\JLCJ2.jwd"
PDT = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\1_PM.pdt"

mj = jwd_read.read_jwd(JWD)
mp = pdt_read.read_pdt(PDT)


def bbox(model):
    xs, ys, zs = [], [], []
    for m in model.members:
        for p in (m.start, m.end):
            xs.append(p[0]); ys.append(p[1]); zs.append(p[2])
    for s in model.slabs:
        for p in s.polygon:
            xs.append(p[0]); ys.append(p[1])
        zs.append(s.z)
    for w in model.walls:
        for p in w.loop:
            xs.append(p[0]); ys.append(p[1]); zs.append(p[2])
    if not xs:
        return None
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def desc(name, m):
    c = m.counts()
    print("-- %s --" % name)
    print("   counts:", c)
    print("   levels(z_bot,z_top,height,no):",
          [(l.stdflr_id, l.z_bot, l.z_top, l.height, l.no) for l in m.sorted_levels()])
    print("   bbox:", bbox(m))
    print("   slabs holes:", sum(1 for s in m.slabs if s.is_hole),
          "slab thickness set:", sorted({s.thickness for s in m.slabs}))
    print("   walls:", [(w.id, w.thickness, w.z_bot, w.z_top, len(w.loop)) for w in m.walls])
    print("   notes:", len(m.notes))
    for n in m.notes[:6]:
        print("      *", n[:160])


desc("read_jwd(JLCJ2.jwd)", mj)
desc("read_pdt(1_PM.pdt)", mp)

print()
print("== pdt section kinds/dims (sample) ==")
for k, s in sorted(mp.sections.items()):
    print("  id=%-6s kind=%-3s mat=%-3s name=%-14r dims=%s" % (s.id, s.kind, s.mat, s.name, s.dims))

print()
print("== round trip ==")
rt = os.path.join(OUT, "rt.jwd")
stats = jwd_write.write_jwd(mj, rt)
mr = jwd_read.read_jwd(rt)
print("write_jwd stats: rows=%s members=%s slabs=%s loads=%s" % (stats["rows"], stats["members"], stats["slabs"], stats["loads"]))
print("model1 counts:", mj.counts())
print("model2 counts:", mr.counts())


def tabcount(path):
    con = sqlite3.connect('file:' + path.replace('\\', '/') + '?mode=ro', uri=True)
    out = {}
    for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        out[t] = con.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
    con.close()
    return out


a, b = tabcount(JWD), tabcount(rt)
print("%-24s %8s %8s %s" % ("table", "orig", "rt", "diff"))
for t in sorted(a):
    print("%-24s %8d %8d %s" % (t, a[t], b[t], "" if a[t] == b[t] else "<<< %+d" % (b[t] - a[t])))
print()
print("orig nonempty tables:", sorted(t for t in a if a[t]))
