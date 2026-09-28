# -*- coding: utf-8 -*-
"""临时探针 11：往返后 pkpmSlabHole / pkpmLoadSect / pkpmProperty 的逐行真相。"""
import io
import sqlite3
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
JWD = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\JLCJ2.jwd"
RT = r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\test\_acceptance_out\JLCJ2.roundtrip.jwd"


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
cols = ("ID", "No_", "StdFlrID", "SectID", "JtID", "SlabID", "EccX", "EccY", "Rotation")
ra = A.execute("SELECT %s FROM pkpmSlabHole ORDER BY ID" % ",".join(cols)).fetchall()
rb = B.execute("SELECT %s FROM pkpmSlabHole ORDER BY ID" % ",".join(cols)).fetchall()
print("orig holes (%d):" % len(ra))
for r in ra[:6]:
    print("   ", r)
print("rt holes (%d):" % len(rb))
for r in rb[:6]:
    print("   ", r)
print("orig SlabIDs sorted:", sorted(r[5] for r in ra)[:8], "...")
print("rt SlabIDs sorted:", sorted(r[5] for r in rb)[:8], "...")
diff = [(x, y) for x, y in zip(ra, rb) if x[1:] != y[1:]]
print("rows differing beyond ID:", len(diff))
for x, y in diff[:4]:
    print("   orig", x)
    print("   rt  ", y)

print()
print("== pkpmSlab hole rows: (ID, No_, StdFlrID, RoomIsHole) ==")
print("orig:", A.execute("SELECT ID,No_,StdFlrID,RoomIsHole FROM pkpmSlab WHERE RoomIsHole=1 ORDER BY ID").fetchall()[:5])
print("rt  :", B.execute("SELECT ID,No_,StdFlrID,RoomIsHole FROM pkpmSlab WHERE RoomIsHole=1 ORDER BY ID").fetchall()[:5])
print()
print("== pkpmLoadSect orig vs rt (ID, No, Loadname, ElementKind, ShapeVal) ==")
ra = A.execute("SELECT ID,No,Loadname,ElementKind,ShapeVal FROM pkpmLoadSect ORDER BY ID").fetchall()
rb = B.execute("SELECT ID,No,Loadname,ElementKind,ShapeVal FROM pkpmLoadSect ORDER BY ID").fetchall()
om = {r[0]: r for r in ra}
for r in rb:
    o = om.get(r[0])
    print("   ID=%-6s orig=%s" % (r[0], o))
    print("   %s rt  =%s" % (" " * len("ID=%-6s" % r[0]), r))
print()
print("== pkpmProperty: rt rows vs orig rows with same ID ==")
orows = A.execute("SELECT ID,Name,Type,ShapeVal FROM pkpmProperty").fetchall()
oset = set(orows)
rrows = B.execute("SELECT ID,Name,Type,ShapeVal FROM pkpmProperty ORDER BY ID").fetchall()
print("orig rows=%d unique=%d; rt rows=%d; rt rows not in orig set=%d"
      % (len(orows), len(oset), len(rrows), sum(1 for r in rrows if r not in oset)))
for r in [x for x in rrows if x not in oset][:5]:
    same = [o for o in orows if o[0] == r[0]]
    print("   rt %s ; orig same ID: %s" % (r, same))
A.close(); B.close()
