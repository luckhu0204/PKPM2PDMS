# -*- coding: utf-8 -*-
"""临时探针 6：往返逐列比对事实 + 其余独立事实。"""
import io
import os
import sqlite3
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
JWD = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\JLCJ2.jwd"
RT = r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\test\_acc_tmp\rt.jwd"
MAP = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\PKPM转PDMS截面匹配文件.txt"


def dec(b):
    if not isinstance(b, bytes):
        return b
    for enc in ('ascii', 'utf-8'):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode('gbk', 'replace')


def con(p):
    c = sqlite3.connect('file:' + p.replace('\\', '/') + '?mode=ro', uri=True)
    c.text_factory = dec
    return c


A, B = con(JWD), con(RT)

COLS = {
    'pkpmStdFlr': ('ID', 'No_', 'Height'),
    'pkpmFloor': ('ID', 'No_', 'Name', 'StdFlrID', 'LevelB', 'Height'),
    'pkpmJoint': ('ID', 'No_', 'StdFlrID', 'X', 'Y', 'HDiff'),
    'pkpmColSeg': ('ID', 'No_', 'StdFlrID', 'SectID', 'JtID', 'EccX', 'EccY', 'Rotation', 'HDiffB'),
    'pkpmBeamSeg': ('ID', 'No_', 'StdFlrID', 'SectID', 'GridID', 'Ecc', 'HDiff1', 'HDiff2', 'Rotation', 'JYDef'),
    'pkpmBraceSeg': ('ID', 'No_', 'StdFlrID', 'SectID', 'Jt1ID', 'Jt2ID', 'EccX1', 'EccY1', 'HDiff1', 'EccX2', 'EccY2', 'HDiff2', 'Rotation'),
    'pkpmSlab': ('ID', 'No_', 'StdFlrID', 'GridsID', 'VertexX', 'VertexY', 'VertexZ', 'RoomIsHole', 'Thickness', 'dead', 'live', 'nEdge', 'xc', 'yc'),
    'pkpmSlabHole': ('ID', 'No_', 'StdFlrID', 'SectID', 'JtID', 'SlabID', 'EccX', 'EccY', 'Rotation'),
    'pkpmBeamSect': ('ID', 'No_', 'Name', 'Mat', 'Kind', 'ShapeVal'),
    'pkpmColSect': ('ID', 'No_', 'Name', 'Mat', 'Kind', 'ShapeVal'),
    'pkpmBraceSect': ('ID', 'No_', 'Name', 'Mat', 'Kind', 'ShapeVal'),
    'pkpmLoadSect': ('ID', 'No', 'Loadname', 'ElementKind', 'ShapeVal'),
    'pkpmLoadSeg': ('ID', 'No', 'SectID', 'Type', 'ElementID', 'strParas1', 'nPtCnt', 'strParasX', 'strParasY', 'strParasZ', 'StdFlrID'),
    'pkpmProperty': ('ID', 'Name', 'Type', 'ShapeVal'),
}
for t, cols in COLS.items():
    q = "SELECT %s FROM %s ORDER BY ID" % (','.join(cols), t)
    ra = A.execute(q).fetchall()
    rb = B.execute(q).fetchall()
    diffcols = []
    if len(ra) == len(rb):
        for i, (x, y) in enumerate(zip(ra, rb)):
            if tuple(x) != tuple(y):
                # find differing columns
                for j, c in enumerate(cols):
                    if x[j] != y[j]:
                        if c not in diffcols:
                            diffcols.append(c)
                        if len(diffcols) < 4 and c in ('No_', 'Name', 'ShapeVal', 'VertexZ', 'GridID', 'Loadname'):
                            print("    [%s] row %d col %s: orig=%r rt=%r" % (t, i, c, x[j], y[j]))
                        break
    print("%-16s rows %4d/%-4d diffcols=%s" % (t, len(ra), len(rb), diffcols))

print()
print("== unused grids / loadsect / concrete members (independent facts) ==")
usedgrids = {r[0] for r in A.execute("SELECT DISTINCT GridID FROM pkpmBeamSeg")}
allgrids = {r[0] for r in A.execute("SELECT ID FROM pkpmGrid")}
print("  grids: total=%d used=%d unused=%d" % (len(allgrids), len(usedgrids), len(allgrids - usedgrids)))
usedsect = {r[0] for r in A.execute("SELECT DISTINCT SectID FROM pkpmLoadSeg")}
allsect = {r[0] for r in A.execute("SELECT ID FROM pkpmLoadSect")}
print("  loadsect: total=%d used=%d unused=%d" % (len(allsect), len(usedsect), len(allsect - usedsect)))
tot = 0
for seg, sec in (('pkpmBeamSeg', 'pkpmBeamSect'), ('pkpmColSeg', 'pkpmColSect'), ('pkpmBraceSeg', 'pkpmBraceSect')):
    n = A.execute("SELECT COUNT(*) FROM %s s JOIN %s t ON s.SectID=t.ID WHERE t.Mat=6" % (seg, sec)).fetchone()[0]
    print("  concrete members in %s: %d" % (seg, n))
    tot += n
print("  concrete members total:", tot)
print("  GANGH values:", A.execute("SELECT DISTINCT ShapeVal FROM pkpmProperty WHERE Name='GANGH'").fetchall())
print("  HNTDJ values:", A.execute("SELECT DISTINCT ShapeVal FROM pkpmProperty WHERE Name='HNTDJ'").fetchall())
print()
txt = open(MAP, 'rb').read().decode('gbk')
n_ju = [l for l in txt.replace('\r\n', '\n').split('\n') if l.strip().startswith('矩')]
print("mapping lines starting with 矩:", len(n_ju), n_ju[:5])
print("mapping lines exactly '矩300X600,', any 矩3:", [l for l in txt.replace('\r\n','\n').split('\n') if '矩300X600' in l])
print("mapping contains 'T120':", [l for l in txt.replace('\r\n','\n').split('\n') if l.strip().startswith('T120')])
print("mapping contains '3#20':", [l for l in txt.replace('\r\n','\n').split('\n') if l.strip().startswith('3#20')])
A.close(); B.close()
