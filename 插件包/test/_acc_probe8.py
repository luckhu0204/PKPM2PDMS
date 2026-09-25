# -*- coding: utf-8 -*-
"""临时探针 8：自造 dump → pdms2jwd → 外键解析检查。"""
import io
import os
import re
import sqlite3
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = r"D:\AI_Work\PKPM数据解析"
OUT = os.path.join(ROOT, "PKPM-JWD导入导出", "test", "_acc_tmp")
MAP = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\PKPM转PDMS截面匹配文件.txt"

DUMP = [
    '#PKPM-JWD-PDMSDUMP 1.0',
    'UNITS mm',
    '#SITE /PKPM_JWD',
    '#ZONE /ACCTEST',
    '#STRU /MAINFRAME',
    '#FRMW /STL_FRAME/EL1',
    '#SBFR /COLUMN',
    '#SCTN /STL_COL_1 COLUMN /H_INTERNATIONAL-SPEC/HN450X200 400 400 -2000 400 400 -1000 U rboc rboc 0',
    '#SCTN /STL_COL_2 COLUMN /USER_RECT-SPEC/Rectangle_Profile 600 600 600 -2000 600 600 -1000 U rboc rboc 0',
    '#SBFR /BEAM',
    '#SCTN /BM_1 BEAM /H_INTERNATIONAL-SPEC/HN300X150 400 400 -1000 6400 400 -1000 E lbos lbos 0',
    '#SBFR /HBRACE',
    '#SCTN /HB_1 HBRACE /TUBE_TUBE-SPEC/D194X8.0 400 400 -1000 6400 400 -1000 S - - 0',
    '#SBFR /VBRACE',
    '#FRMW /FLOOR&WALL',
    '#SBFR /SLAB',
    '#PANE /SLAB_1 120 400 400 -1000 6400 400 -1000 6400 4400 -1000 400 4400 -1000 ~ /Concrete_Slab-SPEC/T120 YNZU dbot',
    '#SBFR /WALL',
    '#STWALL /W_1 /Concrete_Wall-SPEC/WALL-600 3000 0 0 -2000 6000 0 -2000 ~ 600',
    '#FRMW /GRID',
    '#SCTN /AXIS_1 BEAM /H_INTERNATIONAL-SPEC/HN300X150 0 0 0 1000 0 0 E - - 0',
    '#END',
]
dpath = os.path.join(OUT, "acc_fixture_dump.txt")
with open(dpath, 'wb') as fh:
    fh.write(("\r\n".join(DUMP) + "\r\n").encode('gbk'))
jpath = os.path.join(OUT, "acc_fixture.jwd")
rpath = os.path.join(OUT, "acc_fixture.report.json")
cmd = [sys.executable, os.path.join(ROOT, "PKPM-JWD导入导出", "engine", "cli.py"),
       "pdms2jwd", dpath, "--out", jpath, "--secmap", MAP, "--report", rpath]
p = subprocess.run(cmd, capture_output=True, cwd=ROOT)
print("exit", p.returncode)
print(p.stdout.decode('utf-8', 'replace'))
print(p.stderr.decode('utf-8', 'replace')[:2000])

con = sqlite3.connect('file:' + jpath.replace('\\', '/') + '?mode=ro', uri=True)
con.text_factory = lambda b: b.decode('utf-8', 'replace') if isinstance(b, bytes) else b
print("tables with rows:")
tot = 0
for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
    n = con.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
    if n:
        print("   %-20s %d" % (t, n))
        tot += n
print("total rows", tot)
# FK check
bad = 0
checked = 0
for (tbl, sql) in con.execute("SELECT name, sql FROM sqlite_master WHERE type='table'"):
    if not sql:
        continue
    for mo in re.finditer(r'(\w+)\s+[^,]*?REFERENCES\s+(\w+)\s*\(\s*(\w+)\s*\)', sql):
        col, rtbl, rcol = mo.groups()
        if rtbl == tbl and col == rcol:
            continue
        rows = con.execute('SELECT DISTINCT "%s" FROM "%s" WHERE "%s" IS NOT NULL' % (col, tbl, col)).fetchall()
        for (v,) in rows:
            checked += 1
            n = con.execute('SELECT COUNT(*) FROM "%s" WHERE "%s" = ?' % (rtbl, rcol), (v,)).fetchone()[0]
            if not n:
                bad += 1
                if bad < 10:
                    print("  BAD FK %s.%s=%r -> %s.%s" % (tbl, col, v, rtbl, rcol))
print("FK pairs checked=%d unresolvable=%d" % (checked, bad))
print("colseg:", con.execute("SELECT ID,No_,StdFlrID,SectID,JtID,HDiffB FROM pkpmColSeg").fetchall())
print("beamseg:", con.execute("SELECT ID,No_,StdFlrID,SectID,GridID,HDiff1,HDiff2 FROM pkpmBeamSeg").fetchall())
print("braceseg:", con.execute("SELECT ID,No_,StdFlrID,SectID,Jt1ID,Jt2ID,HDiff1,HDiff2 FROM pkpmBraceSeg").fetchall())
print("floor:", con.execute("SELECT ID,No_,StdFlrID,LevelB,Height FROM pkpmFloor").fetchall())
print("slab count:", con.execute("SELECT COUNT(*) FROM pkpmSlab").fetchone()[0])
con.close()
