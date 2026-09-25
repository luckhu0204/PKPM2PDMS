# -*- coding: utf-8 -*-
"""临时探针 7：独立复算 jwd 几何 + pdt 节点包围盒（验证公式实现）。"""
import io
import re
import sqlite3
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ENG = r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\engine"
sys.path.insert(0, ENG)
import jwd_read, pdt_read  # noqa: E402

JWD = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\JLCJ2.jwd"
PDT = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\1_PM.pdt"


def dec(b):
    if not isinstance(b, bytes):
        return b
    for enc in ('ascii', 'utf-8'):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode('gbk', 'replace')


def num(v, d=0.0):
    if v is None:
        return d
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return d
    try:
        return float(s)
    except ValueError:
        return d


con = sqlite3.connect('file:' + JWD.replace('\\', '/') + '?mode=ro', uri=True)
con.text_factory = dec
lv = {r[0]: (r[1], r[2]) for r in con.execute("SELECT StdFlrID, LevelB, Height FROM pkpmFloor")}
lev = {k: (num(v[0]), num(v[0]) + num(v[1]), num(v[1])) for k, v in lv.items()}
jt = {}
for r in con.execute("SELECT ID, X, Y, HDiff, StdFlrID FROM pkpmJoint"):
    jt[r[0]] = (num(r[1]), num(r[2]), num(r[3]), r[4])
grid = {r[0]: (r[1], r[2]) for r in con.execute("SELECT ID, Jt1ID, Jt2ID FROM pkpmGrid")}

exp = {}
for r in con.execute("SELECT ID, StdFlrID, JtID, EccX, EccY, HDiffB FROM pkpmColSeg"):
    mid, sf, jj, ex, ey, hb = r[0], r[1], r[2], num(r[3]), num(r[4]), num(r[5])
    j = jt[jj]
    zb, zt, h = lev[sf]
    exp[mid] = ('column', sf, (j[0] + ex, j[1] + ey, zb + hb), (j[0] + ex, j[1] + ey, zt))
for r in con.execute("SELECT ID, StdFlrID, GridID, HDiff1, HDiff2 FROM pkpmBeamSeg"):
    mid, sf, g, h1, h2 = r[0], r[1], r[2], num(r[3]), num(r[4])
    a, b = grid[g]
    ja, jb = jt[a], jt[b]
    zb, zt, h = lev[sf]
    exp[mid] = ('beam', sf, (ja[0], ja[1], zt + h1), (jb[0], jb[1], zt + h2))
for r in con.execute("SELECT ID, StdFlrID, Jt1ID, Jt2ID, EccX1, EccY1, HDiff1, EccX2, EccY2, HDiff2 FROM pkpmBraceSeg"):
    mid, sf, a, b = r[0], r[1], r[2], r[3]
    ex1, ey1, h1, ex2, ey2, h2 = (num(r[i]) for i in range(4, 10))
    ja, jb = jt[a], jt[b]
    zb, zt, h = lev[sf]
    exp[mid] = ('brace', sf, (ja[0] + ex1, ja[1] + ey1, zt + h1),
                (jb[0] + ex2, jb[1] + ey2, zt + h2))

m = jwd_read.read_jwd(JWD)
bad = 0
badz = 0
for mem in m.members:
    e = exp.get(mem.id)
    if e is None:
        print("member not in recompute:", mem.id)
        bad += 1
        continue
    if e[0] != mem.type or e[1] != mem.level:
        print("type/level mismatch", mem.id, e[0], mem.type, e[1], mem.level)
        bad += 1
    for got, want in ((mem.start, e[2]), (mem.end, e[3])):
        if any(abs(a - b) > 1e-6 for a, b in zip(got, want)):
            bad += 1
            if abs(got[2] - want[2]) > 1e-6:
                badz += 1
            if bad < 6:
                print("geom mismatch", mem.id, mem.type, got, want)
print("jwd members: model=%d recomputed=%d mismatches=%d (z-only %d)" % (len(m.members), len(exp), bad, badz))

# levels
print("levels equal:", sorted((l.stdflr_id, l.z_bot, l.z_top, l.height) for l in m.levels) ==
      sorted((k, v[0], v[1], v[2]) for k, v in lev.items()))
# joints
jb = 0
for j in m.joints.values():
    x, y, hd, sf = jt[j.id]
    zb, zt, h = lev[sf]
    if abs(j.x - x) > 1e-6 or abs(j.y - y) > 1e-6 or abs(j.z - (zt + hd)) > 1e-6:
        jb += 1
print("joints mismatched:", jb, "of", len(m.joints))
# slabs
sb = 0
vz = 0
for s in m.slabs:
    zb, zt, h = lev[s.level] if False else ((0, 0, 0))
for r in con.execute("SELECT ID, StdFlrID, VertexZ FROM pkpmSlab"):
    sid, sf, vztext = r[0], r[1], r[2]
    zb, zt, h = lev[sf]
    vals = [num(t) for t in str(vztext).split(',') if t.strip()]
    if any(abs(v - h) > 1e-6 for v in vals):
        vz += 1
print("slabs whose VertexZ != height:", vz)
print("model slab z == level z_top for all:", all(abs(s.z - lev[s.level][1]) < 1e-6 for s in m.slabs))
con.close()

# pdt node bbox
raw = open(PDT, 'rb').read().decode('gbk')
xs, ys, zs = [], [], []
sec = None
for ln in raw.replace('\r\n', '\n').split('\n'):
    s = ln.strip()
    if s.startswith('$'):
        sec = s.split()[0]
        continue
    if sec != '$NODECOOR' or not s or s.startswith(';'):
        continue
    mo = re.match(r'ID=\s*(-?\d+),\s*X=\s*(-?[\d.]+),\s*Y=\s*(-?[\d.]+),\s*Z=\s*(-?[\d.]+)', s)
    if mo:
        xs.append(float(mo.group(2)))
        ys.append(float(mo.group(3)))
        zs.append(float(mo.group(4)))
print("pdt nodes:", len(xs), "bbox:", (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)))
mp = pdt_read.read_pdt(PDT)
bx = []
for mm in mp.members:
    for p in (mm.start, mm.end):
        bx.append(p)
for sl in mp.slabs:
    for p in sl.polygon:
        bx.append((p[0], p[1], sl.z))
for w in mp.walls:
    bx.extend(w.loop)
print("pdt model bbox:", (min(p[0] for p in bx), min(p[1] for p in bx), min(p[2] for p in bx),
                          max(p[0] for p in bx), max(p[1] for p in bx), max(p[2] for p in bx)))
