# -*- coding: utf-8 -*-
"""实施包④ 写回前置侦察（只读样本）：存储类型 / 常量列 / ID 规律。

运行：python test/probe_wr_sample.py
只读 G: 下的样本原件；不写任何文件（输出在 stdout，由调用方重定向）。
"""
import io
import os
import sqlite3
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PLUG = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'
JWD = os.path.join(PLUG, 'JLCJ2.jwd')

con = sqlite3.connect('file:' + JWD.replace('\\', '/') + '?mode=ro', uri=True)


def dec(b):
    """契约 §b.2 的逐值解码（ASCII -> UTF-8 -> GBK）。"""
    if not isinstance(b, bytes):
        return b
    for enc in ('ascii', 'utf-8'):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode('gbk', 'replace')


con.text_factory = dec
q = con.execute


def show(title, sql, n=8):
    print('\n### %s\n%s' % (title, sql))
    try:
        rows = q(sql).fetchall()
    except Exception as e:
        print('  ERR', e)
        return
    for r in rows[:n]:
        print('  ', r)
    print('   (%d rows)' % len(rows))


print('===== 1. 各表 TEXT 列的 storage class（typeof）=====')
for tbl, cols in (('pkpmBeamSect', 'ID,No_,Name,Mat,Kind,ShapeVal'),
                  ('pkpmColSect', 'ID,No_,Name,Mat,Kind,ShapeVal'),
                  ('pkpmBraceSect', 'ID,No_,Name,Mat,Kind,ShapeVal'),
                  ('pkpmLoadSect', 'ID,No,Loadname,ElementKind,ShapeVal'),
                  ('pkpmLoadSeg', 'ID,No,SectID,Type,ElementID,strParas1,'
                                  'nPtCnt,strParasX,strParasY,strParasZ,StdFlrID'),
                  ('pkpmSlab', 'ID,No_,StdFlrID,GridsID,VertexX,VertexY,VertexZ'),
                  ('pkpmFloor', 'ID,No_,Name,StdFlrID,LevelB,Height'),
                  ('pkpmAxis', 'ID,No_,StdFlrID,Jt1ID,Jt2ID,Name'),
                  ('pkpmProperty', 'ID,Name,Type,ShapeVal'),
                  ('pkpmSysInfo', 'ID,ParaVal'),
                  ('pkpmBeamSeg', 'ID,No_,StdFlrID,SectID,GridID,Ecc,HDiff1,HDiff2,'
                                  'Rotation,JYDef')):
    print('\n-- %s' % tbl)
    types = ', '.join("typeof(%s)" % c.strip() for c in cols.split(','))
    print('   ', q('SELECT %s FROM %s LIMIT 1' % (types, tbl)).fetchone())

print('\n===== 2. 截面表原文（每 Kind 一条，看 ShapeVal 的 repr）=====')
for tbl in ('pkpmBeamSect', 'pkpmColSect', 'pkpmBraceSect'):
    for r in q('SELECT ID, No_, Name, Mat, Kind, ShapeVal FROM %s ORDER BY Kind' % tbl):
        print('  %-14s %s' % (tbl, r))

print('\n===== 3. LoadSect / LoadSeg（No 与 ID 的规律、常量列）=====')
show('pkpmLoadSect', 'SELECT ID, No, Loadname, ElementKind, ShapeVal FROM pkpmLoadSect '
                     'ORDER BY ID', 20)
show('pkpmLoadSeg 前 6 行', 'SELECT * FROM pkpmLoadSeg ORDER BY ID LIMIT 6', 6)
print('  LoadSeg No 是否 == 行序 1..n:',
      q('SELECT COUNT(*) FROM (SELECT ID, No, ROW_NUMBER() OVER (ORDER BY ID) rn '
        'FROM pkpmLoadSeg) WHERE No <> rn').fetchone())
print('  LoadSeg ID 范围:', q('SELECT MIN(ID), MAX(ID) FROM pkpmLoadSeg').fetchone())
print('  LoadSect ID 范围:', q('SELECT MIN(ID), MAX(ID) FROM pkpmLoadSect').fetchone())
print('  LoadSeg StdFlrID 取值:',
      q('SELECT DISTINCT StdFlrID FROM pkpmLoadSeg').fetchall())
print('  LoadSeg Type 取值:', q('SELECT DISTINCT Type FROM pkpmLoadSeg').fetchall())
print('  LoadSeg strParas1 取值:',
      q('SELECT DISTINCT strParas1 FROM pkpmLoadSeg').fetchall())

print('\n===== 4. Slab（前 2 行全列 + 常量列取值）=====')
cur = q('SELECT * FROM pkpmSlab ORDER BY ID LIMIT 2')
names = [d[0] for d in cur.description]
for r in cur.fetchall():
    print('  ---')
    for k, v in zip(names, r):
        if v not in (0, 0.0, None, ''):
            print('    %-28s = %r' % (k, v))
for col in ('cc', 'TransWay', 'Ang1', 'Ang2', 'Shape', 'xc', 'yc', 'TwoWaySlab',
            'EdgeSupport', 'ProfilSlabConcertW', 'ProfilSlabWorkLoad',
            'ProfilSlabbhou', 'nEdge', 'Thickness'):
    print('  DISTINCT %-22s %s' % (col, q('SELECT DISTINCT %s FROM pkpmSlab' % col)
                                   .fetchall()[:8]))
print('  Slab ID 范围:', q('SELECT MIN(ID), MAX(ID), COUNT(*) FROM pkpmSlab').fetchone())
print('  nEdge == 顶点数?  反例数:',
      q("SELECT COUNT(*) FROM pkpmSlab WHERE nEdge <> "
        "(LENGTH(VertexX) - LENGTH(REPLACE(VertexX, ',', '')) + 1)").fetchone())
print('  VertexZ 取值:', q('SELECT DISTINCT VertexZ FROM pkpmSlab').fetchall()[:5])
print('  VertexZ 与 pkpmFloor.Height 对应:',
      q('SELECT DISTINCT s.VertexZ, f.Height FROM pkpmSlab s '
        'JOIN pkpmFloor f ON f.StdFlrID = s.StdFlrID').fetchall())
print('  GridsID 示例:', q('SELECT ID, GridsID FROM pkpmSlab ORDER BY ID LIMIT 2')
      .fetchall())
print('  VertexX 示例:', q('SELECT ID, VertexX, VertexY FROM pkpmSlab ORDER BY ID LIMIT 2')
      .fetchall())

print('\n===== 5. SlabHole =====')
show('pkpmSlabHole 前 6 行', 'SELECT * FROM pkpmSlabHole ORDER BY ID LIMIT 6', 6)
print('  ID 范围:', q('SELECT MIN(ID), MAX(ID), COUNT(*) FROM pkpmSlabHole').fetchone())
print('  No_ 是否 1..n 按 ID 序:',
      q('SELECT COUNT(*) FROM (SELECT ID, No_, ROW_NUMBER() OVER (ORDER BY ID) rn '
        'FROM pkpmSlabHole) WHERE No_ <> rn').fetchone())
print('  ID 与 SlabID 的关系（前 8）:',
      q('SELECT ID, SlabID, No_, StdFlrID FROM pkpmSlabHole ORDER BY ID LIMIT 8').fetchall())

print('\n===== 6. StdFlr / Floor =====')
show('pkpmStdFlr', 'SELECT * FROM pkpmStdFlr')
show('pkpmFloor', 'SELECT * FROM pkpmFloor')
print('  StdFlr.ID == Floor.StdFlrID:',
      q('SELECT COUNT(*) FROM pkpmFloor f JOIN pkpmStdFlr s ON s.ID = f.StdFlrID')
      .fetchone())
print('  Floor.ID 范围:', q('SELECT MIN(ID), MAX(ID) FROM pkpmFloor').fetchone())
print('  StdFlr.No_ 取值:', q('SELECT ID, No_ FROM pkpmStdFlr').fetchall())

print('\n===== 7. Joint / Grid / Axis =====')
show('pkpmJoint 前 5', 'SELECT * FROM pkpmJoint ORDER BY ID LIMIT 5')
print('  Joint ID 范围/个数:',
      q('SELECT MIN(ID), MAX(ID), COUNT(*) FROM pkpmJoint').fetchone())
print('  Joint No_ 层内是否 1..n 按 (y,x):',
      q('SELECT COUNT(*) FROM pkpmJoint j WHERE j.No_ <> '
        '(SELECT COUNT(*) FROM pkpmJoint k WHERE k.StdFlrID = j.StdFlrID '
        ' AND (k.Y < j.Y OR (k.Y = j.Y AND k.X <= j.X)))').fetchone())
show('pkpmGrid 前 6', 'SELECT * FROM pkpmGrid ORDER BY ID LIMIT 6')
show('pkpmAxis 前 6', 'SELECT * FROM pkpmAxis ORDER BY ID LIMIT 6')
print('  Grid ID 范围/个数:',
      q('SELECT MIN(ID), MAX(ID), COUNT(*) FROM pkpmGrid').fetchone())
print('  Axis ID 范围/个数:',
      q('SELECT MIN(ID), MAX(ID), COUNT(*) FROM pkpmAxis').fetchone())
print('  Grid 未被 BeamSeg 引用的条数:',
      q('SELECT COUNT(*) FROM pkpmGrid g WHERE NOT EXISTS '
        '(SELECT 1 FROM pkpmBeamSeg b WHERE b.GridID = g.ID)').fetchone())
print('  Axis 未被 Grid 引用的条数:',
      q('SELECT COUNT(*) FROM pkpmAxis a WHERE NOT EXISTS '
        '(SELECT 1 FROM pkpmGrid g WHERE g.AxisID = a.ID)').fetchone())
print('  Grid No_ 层内是否 1..n 按 ID:',
      q('SELECT COUNT(*) FROM pkpmGrid g WHERE g.No_ <> '
        '(SELECT COUNT(*) FROM pkpmGrid k WHERE k.StdFlrID = g.StdFlrID '
        ' AND k.ID <= g.ID)').fetchone())
print('  Axis StdFlrID 分布:',
      q('SELECT StdFlrID, COUNT(*) FROM pkpmAxis GROUP BY StdFlrID').fetchall())
print('  Axis 是否 (StdFlrID, Jt1ID, Jt2ID) 去重:',
      q('SELECT COUNT(*), COUNT(DISTINCT StdFlrID || "-" || Jt1ID || "-" || Jt2ID) '
        'FROM pkpmAxis').fetchone())

print('\n===== 8. 构件段表样例 =====')
show('pkpmBeamSeg 前 4', 'SELECT * FROM pkpmBeamSeg ORDER BY ID LIMIT 4')
show('pkpmColSeg 前 4', 'SELECT * FROM pkpmColSeg ORDER BY ID LIMIT 4')
show('pkpmBraceSeg 全部', 'SELECT * FROM pkpmBraceSeg ORDER BY ID LIMIT 4')
print('  ColSeg Cut_* 取值:',
      q('SELECT DISTINCT Cut_Col, Cut_Cap, Cut_Slab FROM pkpmColSeg').fetchall())
print('  ColSeg ColcapId 取值:',
      q('SELECT DISTINCT ColcapId FROM pkpmColSeg').fetchall())
print('  BeamSeg No_ 层内是否 1..n 按 ID:',
      q('SELECT COUNT(*) FROM pkpmBeamSeg b WHERE b.No_ <> '
        '(SELECT COUNT(*) FROM pkpmBeamSeg k WHERE k.StdFlrID = b.StdFlrID '
        ' AND k.ID <= b.ID)').fetchone())

print('\n===== 9. pkpmProperty =====')
show('Property HNTDJ 前 4', "SELECT * FROM pkpmProperty WHERE Name='HNTDJ' LIMIT 4")
show('Property GANGH 前 4', "SELECT * FROM pkpmProperty WHERE Name='GANGH' LIMIT 4")
print('  Property.Name 计数:',
      q('SELECT Name, Type, COUNT(*) FROM pkpmProperty GROUP BY Name, Type '
        'ORDER BY COUNT(*) DESC').fetchall())
print('  HNTDJ 行数 vs 构件+板:',
      q("SELECT (SELECT COUNT(*) FROM pkpmProperty WHERE Name='HNTDJ'), "
        "(SELECT COUNT(*) FROM pkpmBeamSeg) + (SELECT COUNT(*) FROM pkpmColSeg) + "
        "(SELECT COUNT(*) FROM pkpmBraceSeg) + (SELECT COUNT(*) FROM pkpmSlab)").fetchone())
print('  HNTDJ 的 ID 是否 == 构件/板 ID:',
      q("SELECT COUNT(*) FROM pkpmProperty p WHERE p.Name='HNTDJ' AND p.ID IN "
        "(SELECT ID FROM pkpmBeamSeg UNION SELECT ID FROM pkpmColSeg UNION "
        " SELECT ID FROM pkpmBraceSeg UNION SELECT ID FROM pkpmSlab)").fetchone())
print('  Property ID 范围:', q('SELECT MIN(ID), MAX(ID) FROM pkpmProperty').fetchone())
print('  Property.ShapeVal typeof:',
      q("SELECT typeof(ShapeVal), typeof(Name), ShapeVal FROM pkpmProperty "
        "WHERE Name='HNTDJ' LIMIT 1").fetchone())

print('\n===== 10. SysInfo =====')
show('pkpmSysInfo 前 4', 'SELECT ID, typeof(ParaVal), ParaVal FROM pkpmSysInfo LIMIT 4')
show('pkpmSysInfo ID=2', 'SELECT ID, typeof(ParaVal), ParaVal FROM pkpmSysInfo WHERE ID=2')

print('\n===== 11. 表清单 / 行数（基线）=====')
rows = q("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
print('  非系统表数:', len(rows))
tot = 0
for (t,) in rows:
    c = q('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0]
    tot += c
    print('   %-24s %5d' % (t, c))
print('  合计行数:', tot)

print('\n===== 12. 索引清单 ====')
idx = q("SELECT type, name, tbl_name FROM sqlite_master WHERE type='index' "
        "ORDER BY tbl_name, name").fetchall()
print('  索引数:', len(idx))
print('  其中 sqlite_autoindex 数:',
      sum(1 for r in idx if r[1].startswith('sqlite_autoindex')))
print('  其中显式 CREATE INDEX 数:',
      sum(1 for r in idx if not r[1].startswith('sqlite_autoindex')))
print('  表语句数:',
      q("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone())

print('\n===== 13. 写回用：TEXT 存储类 + 非 UTF-8 字节的可行性与读回 ====')
mem = sqlite3.connect(':memory:')
mem.execute('PRAGMA encoding="UTF-8"')
mem.execute('CREATE TABLE t (ID INTEGER PRIMARY KEY, Name TEXT, Raw TEXT)')
name_gbk = '薄壁方钢管: B25'.encode('gbk')
mem.execute('INSERT INTO t(ID, Name, Raw) VALUES (1, CAST(? AS TEXT), ?)',
            (name_gbk, name_gbk))
mem.commit()
print('  CAST(? AS TEXT) 后 typeof/bytes:',
      mem.execute('SELECT typeof(Name), hex(Name) FROM t').fetchone())
print('  直接插 BLOB 后 typeof:',
      mem.execute('SELECT typeof(Raw) FROM t').fetchone())
print('  预期 GBK hex:', name_gbk.hex().upper())
mem2 = sqlite3.connect(':memory:')          # 不设 text_factory：应报错（证明是真字节）
mem2.execute('CREATE TABLE t (Name TEXT)')
mem2.execute('INSERT INTO t VALUES (CAST(? AS TEXT))', (name_gbk,))
try:
    print('  默认 text_factory 读回:', mem2.execute('SELECT Name FROM t').fetchone())
except Exception as e:
    print('  默认 text_factory 读回失败（预期）:', e)
mem2.text_factory = dec
print('  dec text_factory 读回:', mem2.execute('SELECT Name FROM t').fetchone())
print('  PRAGMA encoding:', mem2.execute('PRAGMA encoding').fetchone())
mem.close()
mem2.close()
print('\n===== 14. pkpmSlab 全列 DISTINCT（决定哪些列可写常量）=====')
cols = [d[1] for d in q('PRAGMA table_info(pkpmSlab)')]
for c in cols:
    vals = q('SELECT DISTINCT "%s" FROM pkpmSlab' % c).fetchall()
    uniq = sorted(set(repr(v[0]) for v in vals))
    print('  %-28s n=%-3d %s' % (c, len(uniq), uniq if len(uniq) <= 6 else uniq[:6] + ['...']))

print('\n  xc == bbox 中心? 反例行数:')
print('   ', q("""SELECT COUNT(*) FROM pkpmSlab WHERE
      ABS(xc - (CAST(SUBSTR(VertexX,1,INSTR(VertexX,',')-1) AS REAL) +
                CAST(SUBSTR(VertexX, LENGTH(RTRIM(VertexX,',')), LENGTH(VertexX)) AS REAL))/2) > 0.01
      """).fetchone())
print('  xc/yc 与顶点均值差（前 5，看是包围盒中心还是形心近似）:')
for r in q('SELECT ID, xc, yc, VertexX, VertexY FROM pkpmSlab ORDER BY ID LIMIT 5'):
    xs = [float(t) for t in r[3].split(',') if t.strip()]
    ys = [float(t) for t in r[4].split(',') if t.strip()]
    print('    ID=%d xc=%.2f bbox=%.2f mean=%.2f | yc=%.2f bbox=%.2f mean=%.2f'
          % (r[0], r[1], (min(xs) + max(xs)) / 2, sum(xs) / len(xs),
             r[2], (min(ys) + max(ys)) / 2, sum(ys) / len(ys)))
print('  包围盒中心 vs xc/yc 全表反例（>0.01）:',
      q('SELECT COUNT(*) FROM pkpmSlab').fetchone())
bad = 0
for r in q('SELECT ID, xc, yc, VertexX, VertexY FROM pkpmSlab'):
    xs = [float(t) for t in r[3].split(',') if t.strip()]
    ys = [float(t) for t in r[4].split(',') if t.strip()]
    if abs(r[1] - (min(xs) + max(xs)) / 2) > 0.01 or abs(r[2] - (min(ys) + max(ys)) / 2) > 0.01:
        bad += 1
print('  包围盒中心反例数:', bad)

print('\n===== 15. nEdge == 顶点数（去掉尾逗号后）=====')
bad = 0
for sid, ne, vx in q('SELECT ID, nEdge, VertexX FROM pkpmSlab'):
    n = len([t for t in vx.split(',') if t.strip()])
    if n != ne:
        bad += 1
        if bad <= 3:
            print('   反例 ID=%s nEdge=%s 顶点数=%s' % (sid, ne, n))
print('  反例数:', bad)

con.close()
