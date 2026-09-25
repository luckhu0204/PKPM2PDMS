# -*- coding: utf-8 -*-
"""临时探针 2（验收测试编写用，跑完即删）：直接从原始样本取事实（自带解码）。"""
import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

JWD = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\JLCJ2.jwd"


def dec(b):
    if not isinstance(b, bytes):
        return b
    for enc in ('ascii', 'utf-8'):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode('gbk', 'replace')


con = sqlite3.connect('file:' + JWD.replace('\\', '/') + '?mode=ro', uri=True)
con.text_factory = dec
q = con.execute

print("== used sections per seg table (SectID, count) ==")
for t in ('pkpmBeamSeg', 'pkpmColSeg', 'pkpmBraceSeg'):
    print(" ", t, q("SELECT SectID, COUNT(*) FROM %s GROUP BY SectID ORDER BY SectID" % t).fetchall())
print()
print("== all sections of the three tables ==")
for t in ('pkpmBeamSect', 'pkpmColSect', 'pkpmBraceSect'):
    for r in q("SELECT ID,No_,Name,Mat,Kind,ShapeVal FROM %s ORDER BY ID" % t):
        print("  %-14s ID=%-6s No_=%-3s Mat=%s Kind=%-4s name=%-16r sv=%r" % (t, r[0], r[1], r[2], r[3], r[4], r[5]))
print()
print("== slab thickness (non-hole) ==")
print(" ", q("SELECT Thickness, COUNT(*) FROM pkpmSlab WHERE RoomIsHole<>1 GROUP BY Thickness ORDER BY Thickness").fetchall())
print("  holes:", q("SELECT COUNT(*) FROM pkpmSlab WHERE RoomIsHole=1").fetchone()[0])
print("  non-hole with T != 0:", q("SELECT COUNT(*) FROM pkpmSlab WHERE RoomIsHole<>1 AND Thickness<>0").fetchone()[0])
print()
print("== pkpmLoadSect ==")
for r in q("SELECT ID,No,Loadname,ElementKind,ShapeVal FROM pkpmLoadSect ORDER BY ID"):
    print("  ", r)
print()
print("== pkpmSysInfo ID=2 ==", q("SELECT ID,ParaVal FROM pkpmSysInfo WHERE ID=2").fetchall())
print("== pkpmProperty names ==")
print(" ", q("SELECT Name,COUNT(*) FROM pkpmProperty GROUP BY Name ORDER BY Name").fetchall())
print()
print("== joints: HDiff nonzero count ==", q("SELECT COUNT(*) FROM pkpmJoint WHERE HDiff<>0").fetchone()[0])
print("== beam/col/brace HDiff nonzero ==")
print("  beam HDiff1/2:", q("SELECT COUNT(*) FROM pkpmBeamSeg WHERE HDiff1<>0 OR HDiff2<>0").fetchone()[0])
print("  brace:", q("SELECT COUNT(*) FROM pkpmBraceSeg WHERE HDiff1<>0 OR HDiff2<>0").fetchone()[0])
print("  col HDiffB:", q("SELECT COUNT(*) FROM pkpmColSeg WHERE HDiffB<>0").fetchone()[0])
print("== slab VertexZ distinct ==", q("SELECT DISTINCT VertexZ FROM pkpmSlab LIMIT 10").fetchall())
con.close()
