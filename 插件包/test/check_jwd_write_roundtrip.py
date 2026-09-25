# -*- coding: utf-8 -*-
"""实施包④ 验收①：样本 ``JLCJ2.jwd`` → Model → ``.jwd'`` → 读回 Model，逐表行数与关键列比对。

跑法：``python test/check_jwd_write_roundtrip.py``

本脚本自己带一个**只读装配器**（与 ``test/test_contract_selfcheck.py`` 同源的契约 §a.5 公式，
非交付代码——交付的 ``jwd_read.py`` 属实施包①），因为本包只交付 ``jwd_write.py`` /
``pdms_dump.py``。比对分四层：

  1. DDL 逐字核对：``engine/jwd_write.py`` 里的每条 SQL 都是 ``_recon/jwd_dump/00_schema.txt``
     的子串（合同 §b.3「原样嵌入」）；产物的表/索引集合、``PRAGMA encoding`` 与样本一致。
  2. 表级：46 张表逐表行数——写出的 vs 样本（差异逐条列出并给出理由）。
  3. 关键列：父表（楼层/节点/截面/板/荷载…）逐行逐列与样本比对；
     子表按"外键 + 几何 + 编号"关键列比对。
  4. 模型级：写出的库用同一装配器读回 ⇒ ``Model`` 的 JSON 规范形式与首轮**逐字节相同**
     （忽略读取期的 ``note``/``source``/``notes``/``table`` 等注解字段）。
  5. 外键：按 46 条 DDL 里的 ``REFERENCES`` 逐列 SQL 检查"非空外键在父表里都能解析"。

只读 G: 下的样本原件；只写 ``test/_rt_out/`` 下本脚本自己的产物（同目录、固定文件名、覆盖写）。
"""
import io
import json
import os
import re
import shutil
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, '..', 'engine')
sys.path.insert(0, ENGINE)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from canonical import Level, Joint, Section, Member, Slab, Load, Model   # noqa: E402
import jwd_write                                                         # noqa: E402

PLUG = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'
JWD = os.path.join(PLUG, 'JLCJ2.jwd')
SCHEMA = r'D:\AI_Work\PKPM数据解析\_recon\jwd_dump\00_schema.txt'
OUTDIR = os.path.join(HERE, '_rt_out')
OUT = os.path.join(OUTDIR, 'JLCJ2.roundtrip.jwd')

fails = []


def check(cond, label, detail=''):
    print('  [%s] %s %s' % ('OK' if cond else 'FAIL', label, detail))
    if not cond:
        fails.append(label)


def dec(b):
    if not isinstance(b, bytes):
        return b
    for enc in ('ascii', 'utf-8'):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode('gbk', 'replace')


def open_ro(path):
    con = sqlite3.connect('file:' + path.replace('\\', '/') + '?mode=ro', uri=True)
    con.text_factory = dec
    return con


# ---------------------------------------------------------------- 装配器（契约 §a.5）
def shapeval_params(sv):
    toks = [t for t in (sv or '').split(',')]
    while toks and toks[-1] == '':
        toks.pop()
    return toks[1:-2], toks


def packed_str(params):
    buf = bytearray()
    for t in params[1:7]:
        v = int(float(t or 0))
        buf.append(v & 0xFF)
        buf.append((v >> 8) & 0xFF)
    return bytes(buf).split(b'\x00')[0].decode('ascii', 'replace')


def dims_of(kind, params):
    if kind == 1 and len(params) >= 2:
        return {'B': float(params[0]), 'H': float(params[1])}
    if kind == 2 and len(params) >= 6:
        return {'Tw': float(params[0]), 'H': float(params[1]), 'B1': float(params[2]),
                'T1': float(params[3]), 'B2': float(params[4]), 'T2': float(params[5])}
    if kind == 3 and len(params) >= 1:
        return {'d': float(params[0])}
    if kind == 26 and len(params) >= 7:
        return {'family': int(float(params[0])), 'subtype': int(float(params[1])),
                'H': float(params[2]), 'B': float(params[4]), 'tf': float(params[5]),
                'tw': float(params[6])}
    if kind == 303 and len(params) >= 30:
        return {'family': int(float(params[0])), 'spec_str': packed_str(params),
                'd': float(params[17]), 'b': float(params[19]),
                'lib_family': int(float(params[26]))}
    return {}


def nums(s):
    return [float(t) for t in (s or '').split(',') if t.strip()]


def build_model(jwd_path):
    """按契约 §a.5 从 .jwd 装配 Model（只读；等价于 jwd_read.py 的公式，非交付代码）。"""
    con = open_ro(jwd_path)
    q = con.execute
    model = Model(source=jwd_path, source_format='jwd')
    for fid, no, name, sid, lvl, h in q('SELECT ID, No_, Name, StdFlrID, LevelB, Height '
                                        'FROM pkpmFloor ORDER BY LevelB'):
        model.levels.append(Level(sid, fid, no, lvl, lvl + h, h, name or ''))
    lvm = model.level_map()
    for jid, no, sid, x, y, hd in q('SELECT ID, No_, StdFlrID, X, Y, HDiff FROM pkpmJoint'):
        model.joints[jid] = Joint(jid, sid, x, y, lvm[sid].z_top + (hd or 0), no, hd or 0)
    for tbl, tag in (('pkpmBeamSect', 'beam'), ('pkpmColSect', 'col'),
                     ('pkpmBraceSect', 'brace')):
        for sid, no, name, mat, kind, sv in q('SELECT ID, No_, Name, Mat, Kind, ShapeVal '
                                              'FROM %s' % tbl):
            params, _ = shapeval_params(sv)
            model.sections[sid] = Section(sid, kind, mat, name or '',
                                          dims_of(kind, params), tag, no, sv or '', params,
                                          'reader-note')
    grids = {r[0]: (r[1], r[2]) for r in q('SELECT ID, Jt1ID, Jt2ID FROM pkpmGrid')}
    for mid, no, sid, secid, jt, ex, ey, rot, hdb in q(
            'SELECT ID, No_, StdFlrID, SectID, JtID, EccX, EccY, Rotation, HDiffB '
            'FROM pkpmColSeg'):
        L, j = lvm[sid], model.joints[jt]
        model.members.append(Member(mid, 'column', sid, secid,
                                    (j.x + (ex or 0), j.y + (ey or 0), L.z_bot + (hdb or 0)),
                                    (j.x + (ex or 0), j.y + (ey or 0), L.z_top),
                                    rot or 0.0, (ex or 0, ey or 0), no, None, jt, '',
                                    hdb or 0.0, 0.0))
    for mid, no, sid, secid, grid, ecc, h1, h2, rot, jy in q(
            'SELECT ID, No_, StdFlrID, SectID, GridID, Ecc, HDiff1, HDiff2, Rotation, '
            'JYDef FROM pkpmBeamSeg'):
        L = lvm[sid]
        g1, g2 = grids[grid]
        a, b = model.joints[g1], model.joints[g2]
        model.members.append(Member(mid, 'beam', sid, secid,
                                    (a.x, a.y, L.z_top + (h1 or 0)),
                                    (b.x, b.y, L.z_top + (h2 or 0)),
                                    rot or 0.0, (ecc or 0.0,), no, grid, None, jy or '',
                                    h1 or 0.0, h2 or 0.0))
    for mid, no, sid, secid, j1, j2, ex1, ey1, h1, ex2, ey2, h2, rot in q(
            'SELECT ID, No_, StdFlrID, SectID, Jt1ID, Jt2ID, EccX1, EccY1, HDiff1, EccX2, '
            'EccY2, HDiff2, Rotation FROM pkpmBraceSeg'):
        L = lvm[sid]
        a, b = model.joints[j1], model.joints[j2]
        model.members.append(Member(mid, 'brace', sid, secid,
                                    (a.x + (ex1 or 0), a.y + (ey1 or 0), L.z_top + (h1 or 0)),
                                    (b.x + (ex2 or 0), b.y + (ey2 or 0), L.z_top + (h2 or 0)),
                                    rot or 0.0, (ex1 or 0, ey1 or 0, ex2 or 0, ey2 or 0),
                                    no, None, None, '', h1 or 0.0, h2 or 0.0))
    for sid, no, sf, gids, vx, vy, vz, hole, th, dead, live in q(
            'SELECT ID, No_, StdFlrID, GridsID, VertexX, VertexY, VertexZ, RoomIsHole, '
            'Thickness, dead, live FROM pkpmSlab'):
        L = lvm[sf]
        model.slabs.append(Slab(sid, sf, list(zip(nums(vx), nums(vy))), L.z_top,
                                th or 0.0, bool(hole), dead or 0.0, live or 0.0,
                                [int(t) for t in (gids or '').split(',') if t.strip()], no))
    ls = {r[0]: (r[3], r[4]) for r in q('SELECT ID, No, Loadname, ElementKind, ShapeVal '
                                        'FROM pkpmLoadSect')}
    for lid, no, secid, ty, eid, p1, npc, px, py, pz, sf in q(
            'SELECT ID, No, SectID, Type, ElementID, strParas1, nPtCnt, strParasX, '
            'strParasY, strParasZ, StdFlrID FROM pkpmLoadSeg'):
        ek, sv = ls.get(secid, (None, ''))
        raw = [t for t in (sv or '').split(',') if t != '']
        vals = []
        for t in raw:
            try:
                vals.append(float(t))
            except Exception:
                vals.append(None)
        model.loads.append(Load(lid, 'beam-line' if ek == 12 else 'joint-point', eid,
                                tuple(vals), raw, secid, 0))
    con.close()
    return model


def norm(d):
    """规范化：去掉读取期注解字段（note/source/source_format/notes/contract_version/units）。"""
    d = dict(d)
    for k in ('note', 'source', 'source_format', 'notes', 'contract_version', 'units'):
        d.pop(k, None)
    for s in d.get('sections', {}).values():
        s.pop('note', None)
    return json.dumps(d, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


# ================================================================ 0. DDL 逐字核对
print('=== 0. DDL 逐字核对（契约 §b.3「原样嵌入」）===')
raw = io.open(SCHEMA, encoding='utf-8').read()
missing = [s for s in jwd_write._DDL_TABLES + jwd_write._DDL_INDEXES if s not in raw]
check(not missing, 'jwd_write.py 里 %d 条语句全部逐字出现在 00_schema.txt'
      % (len(jwd_write._DDL_TABLES) + len(jwd_write._DDL_INDEXES)),
      '缺 %d 条' % len(missing) if missing else '')
check(len(jwd_write._DDL_TABLES) == 46 and len(jwd_write._DDL_INDEXES) == 79,
      'DDL 条数 = 46 表 / 79 索引',
      '%d / %d' % (len(jwd_write._DDL_TABLES), len(jwd_write._DDL_INDEXES)))
check(len(jwd_write.TABLE_NAMES) == 46 and
      set(jwd_write.TABLE_NAMES) == set(re.findall(r'CREATE TABLE (\w+)', raw)),
      'TABLE_NAMES 与 schema 的 46 张表一致')

# ================================================================ 1. 装配 + 写回
print('\n=== 1. 样本 → Model → write_jwd ===')
if not os.path.isdir(OUTDIR):
    os.makedirs(OUTDIR)
m1 = build_model(JWD)
c1 = m1.counts()
print('  首轮 Model counts =', c1)
res = jwd_write.write_jwd(m1, OUT)
print('  write_jwd: rows=%d tables=%d skipped=%d warnings=%d'
      % (res['rows'], len([1 for v in res['tables'].values() if v]),
         len(res['skipped']), len(res['warnings'])))
for s in res['skipped']:
    print('    skipped:', s)
check(os.path.isfile(OUT), '产物存在', OUT)
check(set(res.keys()) == {'tables', 'rows', 'members', 'slabs', 'walls', 'loads',
                          'skipped', 'warnings'}, '返回值键与契约 §b.3 一致',
      str(sorted(res.keys())))

# ================================================================ 2. 读回
print('\n=== 2. 读回 .jwd\' 并比对 ===')
m2 = build_model(OUT)
c2 = m2.counts()
print('  回读 Model counts =', c2)
check(c1 == c2, '回读的 counts() 与首轮一致', '%s vs %s' % (c1, c2))
eq = norm(m1.to_dict()) == norm(m2.to_dict())
check(eq, 'Model JSON 规范形式逐字节一致（忽略 note/source/table 等读取期注解）')
if not eq:
    a, b = norm(m1.to_dict()), norm(m2.to_dict())
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            print('    首个差异 @%d:\n      A ...%s\n      B ...%s' % (i, a[i - 80:i + 80], b[i - 80:i + 80]))
            break
    print('    长度 %d vs %d' % (len(a), len(b)))

con1, con2 = open_ro(JWD), open_ro(OUT)
check(con2.execute('PRAGMA encoding').fetchone()[0] == 'UTF-8', 'PRAGMA encoding = UTF-8')
t1 = set(r[0] for r in con1.execute("SELECT name FROM sqlite_master WHERE type='table'"))
t2 = set(r[0] for r in con2.execute("SELECT name FROM sqlite_master WHERE type='table'"))
check(t1 == t2 and len(t2) == 46, '46 张表名与样本一致', '%d vs %d' % (len(t1), len(t2)))
i1 = set(r[0] for r in con1.execute("SELECT name FROM sqlite_master WHERE type='index' "
                                    "AND name NOT LIKE 'sqlite_autoindex%'"))
i2 = set(r[0] for r in con2.execute("SELECT name FROM sqlite_master WHERE type='index' "
                                    "AND name NOT LIKE 'sqlite_autoindex%'"))
check(i1 == i2 and len(i2) == 79, '79 条显式索引名与样本一致', '%d vs %d' % (len(i1), len(i2)))

# ================================================================ 3. 逐表行数
print('\n=== 3. 逐表行数（写出 vs 样本）===')
#: 契约 §b.3 允许"合成/不承载"的表——差异必须在这里有名字（其余表要求行数相同）
EXPECTED_DIFF = {
    'pkpmAxis': '每根梁一行 pkpmAxis 的**合成**结果（契约 §b.3 允许简化，§12#13）',
    'pkpmGrid': '轴网由梁端点合成：样本 604 行里有 6 行是不被任何梁引用的轴线网格',
    'pkpmLoadSect': '只写被 pkpmLoadSeg 引用到的荷载截面；样本另有未被引用的荷载截面行'
                    '（规范模型只能从 LoadSeg 看到被引用的那些）',
    'pkpmProperty': '只写构件材料等级 HNTDJ/GANGH；样本另有 Sp*/roomrf/support/DXF 设计属性',
    'pkpmSysInfo': '规范模型不承载工程名（样本 ID=2 = "JLCJ2"）',
    'pkpmStdFlrPara': '规范模型不承载每标准层 26 项设计参数',
    'pkpmSatTowPara': '施工/塔吊参数（规范模型不承载）',
    'pkpmSatTowReinInfo': '施工/塔吊参数（规范模型不承载）',
    'pkpmSatTower': '施工/塔吊参数（规范模型不承载）',
}
print('  样本 LoadSect 未被 LoadSeg 引用的行数:',
      con1.execute('SELECT COUNT(*) FROM pkpmLoadSect WHERE ID NOT IN '
                   '(SELECT DISTINCT SectID FROM pkpmLoadSeg WHERE SectID IS NOT NULL)')
      .fetchone()[0])
diff, unexpected = [], []
for (t,) in con1.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
    n1 = con1.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0]
    n2 = con2.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0]
    if n1 != n2:
        diff.append((t, n1, n2))
        if t not in EXPECTED_DIFF:
            unexpected.append((t, n1, n2))
for t, a, b in diff:
    print('  差异 %-20s 样本 %5d → 写出 %5d  %s' % (t, a, b, EXPECTED_DIFF.get(t, '！！未预期')))
check(not unexpected, '除契约允许的合成/不承载表外，逐表行数与样本相同（%d/46 表完全相同）'
      % (46 - len(diff)), str(unexpected) if unexpected else '')
same = 46 - len(diff)
print('  行数完全相同的表：%d 张；有差异：%d 张（全部有理由）' % (same, len(diff)))

# ================================================================ 4. 关键列逐行比对
print('\n=== 4. 关键列逐行比对 ===')
KEY = {
    'pkpmStdFlr': ('ID', 'No_', 'Height'),
    'pkpmFloor': ('ID', 'No_', 'Name', 'StdFlrID', 'LevelB', 'Height'),
    'pkpmJoint': ('ID', 'No_', 'StdFlrID', 'X', 'Y', 'HDiff'),
    'pkpmBeamSect': ('ID', 'No_', 'Name', 'Mat', 'Kind', 'ShapeVal'),
    'pkpmColSect': ('ID', 'No_', 'Name', 'Mat', 'Kind', 'ShapeVal'),
    'pkpmBraceSect': ('ID', 'No_', 'Name', 'Mat', 'Kind', 'ShapeVal'),
    'pkpmBeamSeg': ('ID', 'No_', 'StdFlrID', 'SectID', 'GridID', 'Ecc', 'HDiff1',
                    'HDiff2', 'Rotation', 'JYDef'),
    'pkpmColSeg': ('ID', 'No_', 'StdFlrID', 'SectID', 'JtID', 'EccX', 'EccY', 'Rotation',
                   'HDiffB', 'ColcapId', 'Cut_Col', 'Cut_Cap', 'Cut_Slab'),
    'pkpmBraceSeg': ('ID', 'No_', 'StdFlrID', 'SectID', 'Jt1ID', 'Jt2ID', 'EccX1', 'EccY1',
                     'HDiff1', 'EccX2', 'EccY2', 'HDiff2', 'Rotation'),
    'pkpmSlab': ('ID', 'No_', 'StdFlrID', 'GridsID', 'VertexX', 'VertexY', 'VertexZ',
                 'RoomIsHole', 'Thickness', 'dead', 'live', 'nEdge', 'cc', 'Shape',
                 'xc', 'yc'),
    'pkpmSlabHole': ('StdFlrID', 'SectID', 'JtID', 'SlabID', 'EccX', 'EccY', 'Rotation'),
    'pkpmLoadSect': ('ID', 'ElementKind', 'ShapeVal'),
    'pkpmLoadSeg': ('ID', 'No', 'SectID', 'Type', 'ElementID', 'strParas1', 'nPtCnt',
                    'strParasX', 'strParasY', 'strParasZ', 'StdFlrID'),
}
for t, cols in KEY.items():
    where = ''
    if t == 'pkpmLoadSect':      # 样本有未被引用的荷载截面行（见 EXPECTED_DIFF），只比被引用的
        where = ' WHERE ID IN (SELECT DISTINCT SectID FROM pkpmLoadSeg)'
    q = 'SELECT %s FROM "%s"%s ORDER BY %s' % (','.join(cols), t, where, cols[0])
    a = con1.execute(q).fetchall()
    b = con2.execute(q).fetchall()
    if t == 'pkpmSlabHole':
        a = sorted(a, key=lambda r: r[3])
        b = sorted(b, key=lambda r: r[3])
    if a == b:
        print('  [OK] %-16s %3d 行 × %2d 列全部一致' % (t, len(a), len(cols)))
    else:
        n = sum(1 for x, y in zip(a, b) if x != y)
        print('  [FAIL] %-14s 行数 %d/%d，不一致 %d 行；示例：' % (t, len(a), len(b), n))
        for x, y in zip(a, b):
            if x != y:
                print('      样本 %r\n      写出 %r' % (x, y))
                break
        fails.append('%s 关键列不一致' % t)

# ================================================================ 4b. 列级差异清单
print('\n=== 4b. 列级差异清单（同一批 ID 上逐列比对；用来量化"关键列"之外还剩什么差异）===')
for t, order in (('pkpmSlab', 'ID'), ('pkpmLoadSeg', 'ID'), ('pkpmLoadSect', 'ID'),
                 ('pkpmProperty', 'ID')):
    cols = [d[1] for d in con1.execute('PRAGMA table_info("%s")' % t)]
    where = ''
    if t == 'pkpmLoadSect':
        where = ' WHERE ID IN (SELECT DISTINCT SectID FROM pkpmLoadSeg)'
    sel = 'SELECT %s FROM "%s"%s' % (','.join(cols), t, where)
    a = {r[0]: r for r in con1.execute(sel)}
    b = {r[0]: r for r in con2.execute(sel)}
    diff_cols = []
    for i, c in enumerate(cols):
        n = 0
        for k in sorted(set(a) & set(b)):
            if a[k][i] != b[k][i]:
                n += 1
        if n:
            diff_cols.append((c, n))
    print('  %-14s 共同行 %3d：逐列不一致的列 %s' % (t, len(set(a) & set(b)),
                                                 diff_cols if diff_cols else '无'))

# ================================================================ 4c. 文本列字节
print('\n=== 4c. 文本列字节规则（契约 §b.3 / jwd_format.md §9.1）===')
gbk_name = '薄壁方钢管: B25'
for tag, con in (('样本', con1), ('写出', con2)):
    row = con.execute('SELECT typeof(Name), hex(Name) FROM pkpmColSect WHERE ID = 3985'
                      ).fetchone()
    print('  %s pkpmColSect(3985): typeof=%s hex=%s' % (tag, row[0], row[1][:48] + '…'))
    check(row[0] == 'text' and row[1].upper().startswith(gbk_name.encode('gbk').hex().upper()),
          '%s：中文截面名是 TEXT 存储类里的 GBK 字节' % tag)
check(con1.execute('SELECT hex(Name) FROM pkpmColSect WHERE ID=3985').fetchone()[0] ==
      con2.execute('SELECT hex(Name) FROM pkpmColSect WHERE ID=3985').fetchone()[0],
      '样本与写出物的 Name 字节完全相同（GBK 字节级一致）')

# ================================================================ 5. 外键全解析
print('\n=== 5. 外键逐列检查（按 46 条 DDL 里的 REFERENCES）===')
fk = []
for stmt in jwd_write._DDL_TABLES:
    tbl = re.match(r'CREATE TABLE\s+(\w+)', stmt).group(1)
    body = stmt[stmt.index('(') + 1:]
    for col, parent in re.findall(r'(\w+)\s+INTEGER\s+REFERENCES\s+(\w+)\s*\(', body):
        fk.append((tbl, col, parent))
print('  DDL 里的外键声明共 %d 条' % len(fk))
bad = []
for tbl, col, parent in fk:
    n1 = con1.execute('SELECT COUNT(*) FROM "%s" WHERE "%s" IS NOT NULL AND "%s" NOT IN '
                      '(SELECT ID FROM "%s")' % (tbl, col, col, parent)).fetchone()[0]
    n2 = con2.execute('SELECT COUNT(*) FROM "%s" WHERE "%s" IS NOT NULL AND "%s" NOT IN '
                      '(SELECT ID FROM "%s")' % (tbl, col, col, parent)).fetchone()[0]
    if n1 or n2:
        bad.append((tbl, col, parent, n1, n2))
for r in bad:
    print('   未解析 %s.%s -> %s : 样本 %d 行 / 写出 %d 行' % r)
n_bad_out = sum(r[4] for r in bad)
n_bad_sample = sum(r[3] for r in bad)
check(len(fk) >= 40, '外键声明条数 ≥ 40', str(len(fk)))
check(n_bad_out == 0, '写出产物的未解析外键行数 = 0（共查 %d 条外键）' % len(fk),
      '样本自身基线 = %d 行' % n_bad_sample)

con1.close()
con2.close()

print('\n=== 6. 跨模块端到端：交付的 engine/jwd_read.py 读样本 → write_jwd → 再用它读回 ===')
try:
    import jwd_read as _real_read
    OUT2 = os.path.join(OUTDIR, 'JLCJ2.real.jwd')
    a = _real_read.read_jwd(JWD)
    res2 = jwd_write.write_jwd(a, OUT2)
    b = _real_read.read_jwd(OUT2)
    print('  read_jwd(样本).counts()  =', a.counts())
    print('  read_jwd(产物).counts()  =', b.counts())
    print('  样本 material 统计: C30=%d 空=%d'
          % (sum(1 for m in a.members if m.material == 'C30'),
             sum(1 for m in a.members if not m.material)))
    print('  产物 material 统计: C30=%d 空=%d'
          % (sum(1 for m in b.members if m.material == 'C30'),
             sum(1 for m in b.members if not m.material)))
    con2 = open_ro(OUT2)
    print('  产物 pkpmProperty 行数 = %d（样本 3574，其中构件材料 HNTDJ/GANGH 各 1033）'
          % con2.execute('SELECT COUNT(*) FROM pkpmProperty').fetchone()[0])
    bad2 = []
    for stmt in jwd_write._DDL_TABLES:
        tbl = re.match(r'CREATE TABLE\s+(\w+)', stmt).group(1)
        body = stmt[stmt.index('(') + 1:]
        for col, parent in re.findall(r'(\w+)\s+INTEGER\s+REFERENCES\s+(\w+)\s*\(', body):
            n = con2.execute('SELECT COUNT(*) FROM "%s" WHERE "%s" IS NOT NULL AND "%s" '
                             'NOT IN (SELECT ID FROM "%s")' % (tbl, col, col, parent)
                             ).fetchone()[0]
            if n:
                bad2.append((tbl, col, parent, n))
    con2.close()
    check(not bad2, '端到端产物外键全部可解析', str(bad2))
    check(a.counts() == b.counts(), '交付 reader 读样本与读产物的 counts() 一致')
    ja, jb = norm(a.to_dict()), norm(b.to_dict())
    check(ja == jb, '交付 reader 读出的 Model 规范 JSON **逐字节一致**'
                    '（含 material / 截面参数 / 全部几何）')
    if ja != jb:
        for i in range(min(len(ja), len(jb))):
            if ja[i] != jb[i]:
                print('    首个差异 @%d:\n      A ...%s\n      B ...%s'
                      % (i, ja[i - 90:i + 90], jb[i - 90:i + 90]))
                break
        print('    长度 %d vs %d' % (len(ja), len(jb)))
    check(not b.errors(), '交付 reader 读产物无 E- 项', str(b.errors()[:3]))
    check([w.split(':')[0] for w in a.warnings()] == [w.split(':')[0] for w in b.warnings()],
          '交付 reader 在样本与产物上的 W- 类型分布一致',
          '%s vs %s' % ([w.split(':')[0] for w in a.warnings()],
                        [w.split(':')[0] for w in b.warnings()]))
    print('  write_jwd 返回值: rows=%d, warnings=%d 条' % (res2['rows'],
                                                          len(res2['warnings'])))
except ImportError as exc:
    print('  [SKIP] engine/jwd_read.py 不可用（%s）—— 跨模块核对未运行' % exc)
except Exception as exc:
    check(False, '交付 reader 交叉核对', '%r' % (exc,))

print('\n=== 结论 ===')
print('产出文件：%s' % OUT)
print('FAIL 项: %d %s' % (len(fails), fails if fails else ''))
sys.exit(1 if fails else 0)
