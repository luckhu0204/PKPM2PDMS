# -*- coding: utf-8 -*-
"""实施包④ 验收②：手写 dump 文本 → ``parse_dump`` → ``write_jwd`` → 外键全部可解析。

跑法：``python test/check_dump_to_jwd.py``

夹具（本目录，手写、UTF-8 存放便于审阅；测试时按契约 §c.1 转成 **GBK+CRLF** 再读）::

    fixture_dump_min.txt   —— 契约 §c.4 的**最小示例逐字**（CONTRACT.md 474-493 行）
    fixture_dump_ext.txt   —— 覆盖：2 层 / 参数化族 RECT+H / 型钢库名 / 303 键 /
                              "-" 哨兵 / 未命中 SPREF / 无 "~" 尾部的 PANE /
                              带厚度与不带厚度的 STWALL / FRMW /GRID 下被忽略的 #SCTN /
                              斜支撑（ori=S 与 ctype 一致）/ bangle≠0

校验层次：
  1. ``parse_dump`` 解析结果（层/节点/构件/板/墙/截面/notes）与夹具的**逐条手算期望**一致；
  2. ``write_jwd`` 产物的外键（按 46 条 DDL 的 REFERENCES 逐列 SQL）**零未解析**；
  3. 产物读回 ⇒ 几何/编号/截面与写前一致（除契约规定不写进 .jwd 的墙）；
  4. 反算出的 ShapeVal 逐条核对（Kind=1/2 能反算；Kind=26/303 缺证据 ⇒ 空 + 报告）；
  5. E-PARSE 负例（缺父级/坏 token/缺 #END/未知记录…）逐个必须抛 ``DumpSyntaxError``；
  6. 单位：``UNITS m`` 换算、缺 ``UNITS`` 行按 mm + note。

只读 G: 下的样本原件与 _recon；只写本目录 ``_rt_out/`` 下自己的产物（固定名、覆盖写）。
"""
import io
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
sys.path.insert(0, HERE)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from canonical import TOL                                                    # noqa: E402
import jwd_write                                                             # noqa: E402
import pdms_dump                                                             # noqa: E402
import _jwd_read_stub as stub                                                # noqa: E402

PLUG = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'
MATCH = os.path.join(PLUG, 'PKPM转PDMS截面匹配文件.txt')
OUTDIR = os.path.join(HERE, '_rt_out')

fails = []


def check(cond, label, detail=''):
    print('  [%s] %s %s' % ('OK' if cond else 'FAIL', label, detail))
    if not cond:
        fails.append(label)


# ---------------------------------------------------------------- SectionMap 替身
class _ReverseStand:
    """``secmap.SectionMap.reverse()`` 的测试替身（契约 §e.2 的解析规则 + §e.6 的"首条"）。

    实施包②交付 ``engine/secmap.py`` 后，本脚本会优先用真的 ``SectionMap``。
    """

    def __init__(self, path):
        self.rev = {}
        with io.open(path, 'rb') as f:
            txt = f.read().decode('gbk')
        for ln in txt.split('\r\n'):
            s = ln.strip()
            if not s or s.startswith('//') or ',' not in s:
                continue
            if set(s) <= {'/'}:
                continue
            l, r = s.split(',', 1)
            r = ' '.join(r.split())
            if not r.startswith('/'):
                r = '/' + r
            self.rev.setdefault(r, l.strip())      # 加载顺序中第一条（§e.6）

    def reverse(self, spec_path):
        return self.rev.get(spec_path)


def make_gbk(src, dst):
    """把 UTF-8 夹具按契约 §c.1 转成 GBK + CRLF，返回路径。"""
    if not os.path.isdir(OUTDIR):
        os.makedirs(OUTDIR)
    with io.open(src, 'r', encoding='utf-8') as f:
        txt = f.read()
    data = txt.replace('\r\n', '\n').replace('\n', '\r\n').encode('gbk')
    with open(dst, 'wb') as f:
        f.write(data)
    return dst


# ---------------------------------------------------------------- 0. 备用 SectionMap
print('=== 0. 截面匹配器（优先用真 secmap.py，否则用测试替身）===')
smap = None
try:
    sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
    import secmap as _secmap                                            # noqa: F401
    smap = _secmap.SectionMap.load(MATCH)
    print('  使用 engine/secmap.py 的 SectionMap.load(%s)' % MATCH)
except Exception as exc:
    smap = _ReverseStand(MATCH)
    print('  engine/secmap.py 不可用（%s）⇒ 使用测试替身 _ReverseStand（同一解析规则）'
          % type(exc).__name__)
check(smap.reverse('/H_INTERNATIONAL-SPEC/HN450X200') == 'HN450X200',
      "reverse('/H_INTERNATIONAL-SPEC/HN450X200') == 'HN450X200'",
      repr(smap.reverse('/H_INTERNATIONAL-SPEC/HN450X200')))
check(smap.reverse('/USER_RECT-SPEC/Rectangle_Profile') == 'RECT', 'RECT 族可逆查')
check(smap.reverse('/UNKNOWN-SPEC/NO_MATCH_1') is None, '未知 SPREF 逆查为 None')

# ---------------------------------------------------------------- 1. §c.4 最小示例
print('\n=== 1. 契约 §c.4 最小示例（逐字夹具）===')
f_min = make_gbk(os.path.join(HERE, 'fixture_dump_min.txt'),
                 os.path.join(OUTDIR, 'fixture_dump_min.gbk.txt'))
raw = open(f_min, 'rb').read()
check(b'\r\n' in raw and not raw.replace(b'\r\n', b'').count(b'\n'),
      '夹具已按契约 §c.1 转成 CRLF', '%d 字节' % len(raw))
txt = pdms_dump.load_dump(f_min)
m = pdms_dump.parse_dump(txt, smap)
cm = m.counts()
print('  counts:', {k: cm[k] for k in ('levels', 'joints', 'sections', 'members',
                                       'members_total', 'slabs', 'walls')})
check(cm['members'] == {'beam': 1, 'column': 2, 'brace': 0}, '构件分类',
      str(cm['members']))
check(cm['slabs'] == 1 and cm['walls'] == 1 and cm['joints'] == 5 and cm['levels'] == 3,
      '板 1 / 墙 1 / 节点 5 / 平面型 Level 3', str(cm))
z = sorted(l.z_bot for l in m.levels)
check(z == [-2000.0, -1000.0, 1000.0], 'Level 标高 = 出现过的 Z 升序去重', str(z))
check(all(l.height == 0 and l.floor_id == 0 for l in m.levels), '平面型 Level（height=0）')
col1 = [x for x in m.members if x.no == 1 and x.type == 'column'][0]
col2 = [x for x in m.members if x.no == 2 and x.type == 'column'][0]
bm1 = [x for x in m.members if x.type == 'beam'][0]
check(col1.start == (400.0, 400.0, -2000.0) and col1.end == (400.0, 400.0, -1000.0),
      '#STL_COL_1 几何 = (400,400,-2000)→(400,400,-1000)', str(col1.start) + str(col1.end))
check(bm1.start == (400.0, 400.0, -1000.0) and bm1.end == (6400.0, 400.0, -1000.0),
      '#BM_1 几何正确（契约 §c.4 的逐行读法）')
check(col2.jusl == 'rboc' and col2.meml == 'rboc' and col2.rotation == 0.0,
      'JUSL/MEML/BANG 映射', '%r %r %r' % (col2.jusl, col2.meml, col2.rotation))
s1 = [s for s in m.slabs if s.no == 1][0]
check(len(s1.polygon) == 4 and s1.z == -1000.0 and s1.thickness == 120.0
      and s1.spec_path == '/USER_RECT-SPEC/Rectangle_Profile' and s1.ori == 'YNZU'
      and s1.sjus == 'dbot', '#PANE → Slab（4 顶点 / z=-1000 / 厚 120 / 尾 3 token）',
      '%s %s %s' % (len(s1.polygon), s1.z, s1.thickness))
w1 = m.walls[0]
check(w1.z_bot == -2000.0 and w1.z_top == 1000.0 and w1.thickness == 300.0
      and len(w1.loop) == 4, '#STWALL → Wall（4 点回路 / z_top=z_bot+3000 / 厚 300）',
      '%s %s %s' % (w1.z_bot, w1.z_top, w1.thickness))
kinds = sorted((s.kind, s.name) for s in m.sections.values())
check(len(m.sections) == 3 and (26, 'HN450X200') in kinds and (26, 'HN300X150') in kinds
      and (1, '') in kinds, '截面：HN 名 → Kind=26、RECT → Kind=1', str(kinds))
check(all(x.kind != 0 for x in m.sections.values()), '无未识别截面')
print('  notes:')
for n in m.notes:
    print('   -', n)

# 写回 + 读回
jwd_min = os.path.join(OUTDIR, 'dump_min.jwd')
res = jwd_write.write_jwd(m, jwd_min)
print('  write_jwd: rows=%d skipped=%s' % (res['rows'], res['skipped']))
for x in res['skipped']:
    print('    skipped:', x)
con = stub.open_ro(jwd_min)
bad = stub.fk_violations(con, jwd_write._DDL_TABLES)
check(not bad, '验收②：产物外键**全部可解析**（%d 条外键）'
      % len(stub.fk_declarations(jwd_write._DDL_TABLES)), str(bad))
check(con.execute('PRAGMA encoding').fetchone()[0] == 'UTF-8', 'PRAGMA encoding = UTF-8')
check(con.execute('SELECT COUNT(*) FROM pkpmWallSeg').fetchone()[0] == 0,
      'pkpmWallSeg 写 0 行（墙不写进 .jwd，契约 §a.8）')
check([r[0] for r in con.execute('SELECT Name FROM pkpmBeamSect ORDER BY ID')] ==
      ['HN300X150'], 'pkpmBeamSect.Name = HN300X150',
      str([r[0] for r in con.execute('SELECT Name FROM pkpmBeamSect')]))
check([r[0] for r in con.execute('SELECT Name FROM pkpmColSect ORDER BY ID')] ==
      ['HN450X200', ''], 'pkpmColSect.Name = HN450X200 + 参数化族留空名'
      '（参数化族的族键只进 dims/note——样本里 Kind=1 的 Name 本来就是空串）',
      str([r[0] for r in con.execute('SELECT Name FROM pkpmColSect')]))
names = dict(zip([r[0] for r in con.execute('SELECT ID FROM pkpmColSect')],
                 [r[0] for r in con.execute('SELECT Name FROM pkpmColSect')]))
rect = [s for s in m.sections.values() if s.kind == 1][0]
check(names.get(rect.id) == '' and rect.dims == {'B': 600.0},
      '参数化族 RECT 的识别依据只落在 dims（B=600，H 缺）', str(rect.dims))
sv = [r[0] for r in con.execute('SELECT ShapeVal FROM pkpmColSect ORDER BY ID')]
print('  pkpmColSect.ShapeVal =', sv)
check(sv[0] == '' and sv[1] == '', 'Kind=26（缺 tf/tw）与 Kind=1（RECT 只给 1 个 DESP）'
                                   '都写空 ShapeVal 并在 warnings 里报告')
con.close()
m2 = stub.build_model(jwd_min)
c2 = m2.counts()
check(c2['members'] == cm['members'] and c2['slabs'] == cm['slabs']
      and c2['walls'] == 0 and c2['joints'] == cm['joints'],
      '读回：构件/板/节点数一致，墙按契约 §a.8 未写进 .jwd',
      '%s vs %s' % (cm['members'], c2['members']))
g1 = sorted(tuple(x.start) + tuple(x.end) for x in m.members)
g2 = sorted(tuple(x.start) + tuple(x.end) for x in m2.members)
check(g1 == g2, '读回：全部构件端点几何一致', '%d 根' % len(g1))
check(sorted(tuple(p) for p in m.slabs[0].polygon) ==
      sorted(tuple(p) for p in m2.slabs[0].polygon), '读回：板多边形一致')

# ---------------------------------------------------------------- 2. 扩展夹具
print('\n=== 2. 扩展手写夹具（参数化族 / 型钢名 / 303 键 / "-" 哨兵 / 忽略 GRID）===')
f_ext = make_gbk(os.path.join(HERE, 'fixture_dump_ext.txt'),
                 os.path.join(OUTDIR, 'fixture_dump_ext.gbk.txt'))
me = pdms_dump.parse_dump(pdms_dump.load_dump(f_ext), smap)
ce = me.counts()
print('  counts:', {k: ce[k] for k in ('levels', 'joints', 'sections', 'members',
                                       'members_total', 'slabs', 'walls')})
check(ce['members'] == {'beam': 3, 'column': 3, 'brace': 2}, '构件分类 3 柱/3 梁/2 支撑',
      str(ce['members']))
check(ce['levels'] == 3 and sorted(l.z_bot for l in me.levels) == [-3000.0, 0.0, 3000.0],
      '平面型 Level = {-3000, 0, 3000}')
check(ce['slabs'] == 2 and ce['walls'] == 2, '板 2 / 墙 2')
notes = '\n'.join(me.notes)
for key, label in (('W-DUMP-NOSPEC', '无 "~" 尾部的 PANE 记为 W-DUMP-NOSPEC'),
                   ('W-DUMP-NOTHICK', '无厚度尾部的 STWALL 记为 W-DUMP-NOTHICK'),
                   ('轴网线', 'FRMW /GRID 下的 #SCTN 被忽略并计数'),
                   ('未在截面匹配文件里逆查命中', '未命中 SPREF 落 note'),
                   ('"-" 哨兵', '"-" 哨兵落 note')):
    check(key in notes, label)
by_name = {s.name: s for s in me.sections.values()}
print('  截面:', [(s.id, s.kind, s.name, s.dims) for s in me.sections.values()])
k0 = [s for s in me.sections.values() if s.kind == 0]
check(len(k0) == 2 and all(s.dims == {} and s.name == '' for s in k0),
      "未识别截面（'-' 哨兵 + 未命中 SPREF）⇒ kind=0、dims 空、name 空（不猜）",
      str([(s.id, s.dims) for s in k0]))
hl = [x for x in me.members if x.type == 'brace' and abs(x.rotation - 15.0) < TOL]
check(len(hl) == 1, 'bangle=15 落到 Member.rotation（度，不随单位换算）',
      str([x.rotation for x in me.members]))
hb = hl[0]
check(hb.start == (500.0, 500.0, 3000.0) and hb.end == (5500.0, 500.0, 0.0)
      and abs(hb.hdiff_end - (-3000.0)) < TOL,
      'H 族支撑几何 + hdiff_end = 末端标高 − 层顶（-3000）',
      '%s %s %s' % (hb.start, hb.end, hb.hdiff_end))
jwd_ext = os.path.join(OUTDIR, 'dump_ext.jwd')
rese = jwd_write.write_jwd(me, jwd_ext)
print('  write_jwd: rows=%d' % rese['rows'])
for x in rese['skipped']:
    print('    skipped:', x)
cone = stub.open_ro(jwd_ext)
bad = stub.fk_violations(cone, jwd_write._DDL_TABLES)
check(not bad, '验收②（扩展夹具）：产物外键全部可解析', str(bad))
rows = {t: cone.execute('SELECT COUNT(*) FROM %s' % t).fetchone()[0]
        for t in ('pkpmStdFlr', 'pkpmFloor', 'pkpmJoint', 'pkpmAxis', 'pkpmGrid',
                  'pkpmColSect', 'pkpmBeamSect', 'pkpmBraceSect', 'pkpmColSeg',
                  'pkpmBeamSeg', 'pkpmBraceSeg', 'pkpmSlab', 'pkpmSlabHole')}
print('  产物表行数:', rows)
check(rows['pkpmStdFlr'] == 2 and rows['pkpmFloor'] == 2,
      '平面型两层归并成 2 个楼层（契约 §b.3）', str(rows))
check(rows['pkpmColSeg'] == 3 and rows['pkpmBeamSeg'] == 3 and rows['pkpmBraceSeg'] == 2,
      '段表行数 = 3 柱 / 3 梁 / 2 支撑')
check(rows['pkpmGrid'] == 3 and rows['pkpmAxis'] == 3, '每根梁一行 pkpmGrid + pkpmAxis')
sv = dict(zip([r[0] for r in cone.execute('SELECT ID FROM pkpmBraceSect')],
              [r[0] for r in cone.execute('SELECT ShapeVal FROM pkpmBraceSect')]))
print('  pkpmBraceSect.ShapeVal =', sv)
h_id = [s.id for s in me.sections.values() if s.name == '' and s.kind == 2][0]
check(sv.get(h_id) == '2,8,300,200,12,200,12,5,%d,' % h_id,
      'Kind=2 的 ShapeVal 由 H 族 DESP 反算（契约 §a.4 的 Tw,H,B1,T1,B2,T2）',
      repr(sv.get(h_id)))
k303 = [s for s in me.sections.values() if s.kind == 303]
check(len(k303) == 1 and k303[0].dims.get('lib_family') == 6
      and k303[0].dims.get('spec_str') == 'B250*10.00'
      and k303[0].dims.get('d') == 250.0 and k303[0].dims.get('b') == 250.0,
      '303 键 6-B250*10.00 → lib_family/spec_str/d/b（契约 §e.1 候选键 2）',
      str(k303[0].dims))
# R2 变更（契约 §0.4-4 / §k.3）：槽 32 不再"语义未解"—— 样本 3/3 行实测把它定为**形状码**
# （方矩 16672 / 圆 16640），故 dump 侧反查出的 Kind=303 现在能按模板造出完整 ShapeVal。
_sv303 = sv.get(k303[0].id) or ''
_t = _sv303.split(',')
check(_t[:2] == ['303', '77'] and len(_t) == 84 and _t[18] == '250' and _t[20] == '250'
      and _t[27] == '6' and _t[30] == '5' and _t[32] == '16672' and _t[81] == '-1'
      and _t[82] == str(k303[0].id),
      'Kind=303 按 R2 §k.3 模板反算出完整 84 字段 ShapeVal（槽 32 = 16672 方矩管；'
      'v1 曾按"禁止使用槽 32"留空 —— §0.4-4 授权变更）', repr(_sv303))
colds = dict(zip([r[0] for r in cone.execute('SELECT ID FROM pkpmColSect')],
                 [r[0] for r in cone.execute('SELECT ShapeVal FROM pkpmColSect')]))
rect_id = [s.id for s in me.sections.values() if s.kind == 1][0]
print('  pkpmColSect.ShapeVal =', colds)
check(colds.get(rect_id) == '1,500,500,6,%d,' % rect_id,
      'Kind=1 的 ShapeVal 由 RECT 族 DESP 反算（契约 §a.4：<Kind>,B,H,Mat,ID）',
      repr(colds.get(rect_id)))
warn = '\n'.join(rese['warnings'])
check('ShapeVal 无法完整反算' in warn, 'ShapeVal 缺口写进返回值 warnings')
check(any(x['what'] == 'wall' for x in rese['skipped']), '墙逐条进 skipped（契约 §b.3）')
cone.close()
me2 = stub.build_model(jwd_ext)
check(sorted(tuple(x.start) + tuple(x.end) for x in me.members) ==
      sorted(tuple(x.start) + tuple(x.end) for x in me2.members),
      '读回：扩展夹具全部构件几何一致')
check(me2.slabs[1].thickness == 150.0 and me2.slabs[1].z == 3000.0,
      '读回：第二块板（无 ~ 尾部）几何/厚度一致',
      '%s %s' % (me2.slabs[1].thickness, me2.slabs[1].z))

# ---------------------------------------------------------------- 3. E-PARSE 负例
print('\n=== 3. E-PARSE 负例（契约 §c.3，CLI 按 §f.2 码 2 退出）===')
HEAD = '#PKPM-JWD-PDMSDUMP 1.0\nUNITS mm\n#SITE /S\n#ZONE /Z\n#STRU /R\n#FRMW /F\n'
BAD = [
    ('缺 #END', HEAD + '#SBFR /COLUMN\n'
     '#SCTN /C COLUMN /H_INTERNATIONAL-SPEC/HN300X150 0 0 0 0 0 1000 U na na 0\n'),
    ('首行不是头', 'XXX 1.0\nUNITS mm\n#END\n'),
    ('#SBFR 缺 #FRMW 父级', '#PKPM-JWD-PDMSDUMP 1.0\nUNITS mm\n#SITE /S\n#ZONE /Z\n'
     '#STRU /R\n#SBFR /COLUMN\n#END\n'),
    ('#SCTN token 不足 14', HEAD + '#SBFR /COLUMN\n#SCTN /C COLUMN - 0 0 0 U na na 0\n'),
    ('#SCTN 的 desp 非数字', HEAD + '#SBFR /COLUMN\n'
     '#SCTN /C COLUMN - abc 0 0 0 0 0 1000 U na na 0\n'),
    ('#SCTN 的 ctype 非法', HEAD + '#SBFR /COLUMN\n'
     '#SCTN /C COL 0 0 0 0 0 0 1000 U na na 0\n'),
    ('#PANE 顶点不足 3', HEAD + '#SBFR /SLAB\n#PANE /P 100 0 0 0 1000 0 0\n'),
    ('#PANE 尾部不是 3 个 token', HEAD + '#SBFR /SLAB\n'
     '#PANE /P 100 0 0 0 1000 0 0 1000 1000 0 ~ /A /B\n'),
    ('#PANE 只有孤立的 ~', HEAD + '#SBFR /SLAB\n'
     '#PANE /P 100 0 0 0 1000 0 0 1000 1000 0 ~\n'),
    ('#PANE 顶点 U 不一致', HEAD + '#SBFR /SLAB\n'
     '#PANE /P 100 0 0 0 1000 0 0 1000 1000 5\n'),
    ('#STWALL token 数非法', HEAD + '#SBFR /WALL\n#STWALL /W /A 3000 0 0 -1 100\n'),
    ('未知记录', HEAD + '#SBFR /COLUMN\n#FOO bar\n'),
    ('UNITS 值非法', '#PKPM-JWD-PDMSDUMP 1.0\nUNITS inch\n#END\n'),
    ('#END 之后有内容', HEAD + '#END\n#SITE /S2\n'),
    ('name 含 ~', HEAD + '#SBFR /COLUMN\n'
     '#SCTN /C~1 COLUMN - 0 0 0 0 0 1000 U na na 0\n'),
]
for label, text in BAD:
    try:
        pdms_dump.parse_dump(text, smap)
        check(False, 'E-PARSE: %s' % label, '未抛异常')
    except pdms_dump.DumpSyntaxError as exc:
        ok = str(exc).startswith('E-PARSE')
        check(ok, 'E-PARSE: %s' % label, str(exc)[:96])
    except Exception as exc:
        check(False, 'E-PARSE: %s' % label, '抛了 %r' % exc)

# ---------------------------------------------------------------- 4. 单位
print('\n=== 4. 单位（契约 §c.1：只有长度量换算；bangle 恒为度）===')
t_m = ('#PKPM-JWD-PDMSDUMP 1.0\nUNITS m\n#SITE /S\n#ZONE /Z\n#STRU /R\n#FRMW /F\n'
       '#SBFR /COLUMN\n#SCTN /C1 COLUMN - 0.5 0.5 -3 0.5 0.5 0 U na na 45\n#END\n')
mm = pdms_dump.parse_dump(t_m, smap)
check(mm.members[0].start == (500.0, 500.0, -3000.0)
      and mm.members[0].end == (500.0, 500.0, 0.0) and mm.members[0].rotation == 45.0,
      'UNITS m：0.5 → 500 mm，bangle=45 不换算', str(mm.members[0].start) +
      str(mm.members[0].rotation))
t_cm = t_m.replace('UNITS m', 'UNITS cm')
mc = pdms_dump.parse_dump(t_cm, smap)
check(mc.members[0].start == (5.0, 5.0, -30.0), 'UNITS cm：0.5 → 5 mm',
      str(mc.members[0].start))
t_no = t_m.replace('UNITS m\n', '')
mn = pdms_dump.parse_dump(t_no, smap)
check(mn.members[0].start == (0.5, 0.5, -3.0) and any('UNITS' in n for n in mn.notes),
      '缺 UNITS 行 ⇒ 按 mm 且 notes 留痕', str(mn.members[0].start))
check(pdms_dump.UNIT_FACTOR == {'mm': 1.0, 'cm': 10.0, 'm': 1000.0}, '单位系数表')

# ---------------------------------------------------------------- 5. 其他接口约束
print('\n=== 5. 接口约束（契约 §b.1 / §c.1）===')
try:
    pdms_dump.parse_dump(b'#PKPM-JWD-PDMSDUMP 1.0\n#END\n')
    check(False, 'parse_dump 拒绝 bytes（要求 str）')
except TypeError as exc:
    check(True, 'parse_dump 拒绝 bytes（要求 str）', str(exc)[:80])
try:
    pdms_dump.load_dump(__file__)          # 本文件是 UTF-8，按 GBK 读必然失败
    check(False, 'load_dump 遇到非 GBK 字节必须报错')
except UnicodeDecodeError as exc:
    check(True, 'load_dump 按 GBK 读，失败即抛（契约 §c.1 禁止 errors=replace）',
          str(exc)[:80])
pdms_dump.set_default_section_map(smap)
mn2 = pdms_dump.parse_dump(pdms_dump.load_dump(f_min))
check(any(s.name == 'HN450X200' for s in mn2.sections.values()),
      '冻结签名 parse_dump(text) + set_default_section_map 也能逆查截面名')
pdms_dump.set_default_section_map(None)

# ---------------------------------------------------------------- 6. 材料属性 / 覆盖写 / 自卫
print('\n=== 6. pkpmProperty（材料等级）/ 覆盖写 / ID 重复的自卫 ===')
import copy                                                              # noqa: E402
import glob                                                              # noqa: E402
me3 = copy.deepcopy(me)
me3.members[0].material = 'C30'
me3.members[1].material = 'Q235'
jwd_p = os.path.join(OUTDIR, 'dump_ext_prop.jwd')
res3 = jwd_write.write_jwd(me3, jwd_p)
conp = stub.open_ro(jwd_p)
prop = conp.execute('SELECT ID, Name, Type, ShapeVal FROM pkpmProperty ORDER BY ID').fetchall()
print('  pkpmProperty:', prop)
check(prop == [(me3.members[0].id, 'HNTDJ', 5, '30.00'),
               (me3.members[1].id, 'GANGH', 5, '235.00')],
      "Member.material='C30'/'Q235' → pkpmProperty HNTDJ/GANGH（契约 §b.2/§b.3）",
      str(prop))
check(not stub.fk_violations(conp, jwd_write._DDL_TABLES), '带材料属性时外键仍全解析')
conp.close()

# 覆盖写（同一路径第二次写必须成功，且不留临时文件）
rows_before = res3['rows']
res4 = jwd_write.write_jwd(me3, jwd_p)
check(res4['rows'] == rows_before and os.path.isfile(jwd_p), '同路径覆盖写成功')
check(not glob.glob(os.path.join(OUTDIR, '*.tmp')), '不留临时文件（.tmp 已 os.replace 走）',
      str(glob.glob(os.path.join(OUTDIR, '*.tmp'))))

# ID 重复必须中止（不要写出半个库）
bad_model = copy.deepcopy(me)
bad_model.members.append(copy.deepcopy(bad_model.members[0]))
try:
    jwd_write.write_jwd(bad_model, os.path.join(OUTDIR, 'should_not_exist.jwd'))
    check(False, '构件 ID 重复必须抛 ValueError')
except ValueError as exc:
    check('ID 重复' in str(exc), '构件 ID 重复 ⇒ ValueError（.jwd 主键唯一性）',
          str(exc)[:70])
check(not os.path.isfile(os.path.join(OUTDIR, 'should_not_exist.jwd')),
      '抛错时不产出文件')

# 合成节点路径（模型里没有节点表时：契约 §b.3 的 pkpmJoint 合成规则）
me4 = copy.deepcopy(me)
me4.joints = {}
jwd_nj = os.path.join(OUTDIR, 'dump_ext_nojoints.jwd')
res4 = jwd_write.write_jwd(me4, jwd_nj)
conn = stub.open_ro(jwd_nj)
n_j = conn.execute('SELECT COUNT(*) FROM pkpmJoint').fetchone()[0]
n_dup = conn.execute('SELECT COUNT(*) FROM (SELECT ID FROM pkpmJoint GROUP BY ID '
                     'HAVING COUNT(*) > 1)').fetchone()[0]
pts = set()
for x in me.members:
    pts.add((round(x.start[0], 3), round(x.start[1], 3), round(x.start[2], 3)))
    if x.type != 'column':      # 柱顶不需要节点：pkpmColSeg 只有 JtID（柱底）
        pts.add((round(x.end[0], 3), round(x.end[1], 3), round(x.end[2], 3)))
print('  无节点模型：合成 %d 个节点，期望 %d 个（柱起点 + 梁/支撑两端，去重）'
      % (n_j, len(pts)))
check(n_j == len(pts), '模型不带节点时按构件端点合成 pkpmJoint（三维点去重；'
                       '柱顶不需要节点，与样本 pkpmColSeg 只有 JtID 一致）',
      '%d vs %d' % (n_j, len(pts)))
check(n_dup == 0, '合成节点的 ID 不重复（主键唯一）', '重复 %d 个' % n_dup)
bad = stub.fk_violations(conn, jwd_write._DDL_TABLES)
check(not bad, '无节点模型：产出外键仍全部可解析', str(bad))
check(any('合成了' in x for x in res4['warnings']), '合成节点写进返回值 warnings')
mnj = stub.build_model(jwd_nj)
check(sorted(tuple(x.start) + tuple(x.end) for x in mnj.members) ==
      sorted(tuple(x.start) + tuple(x.end) for x in me4.members),
      '无节点模型：读回构件几何一致')
conn.close()

print('\n=== 结论 ===')
print('产物：%s' % OUTDIR)
print('FAIL 项: %d %s' % (len(fails), fails if fails else ''))
sys.exit(1 if fails else 0)
