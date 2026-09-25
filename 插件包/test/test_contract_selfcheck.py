# -*- coding: utf-8 -*-
"""架构自检（不是交付的 jwd_read.py）：用真实样本 JLCJ2.jwd 验证 canonical.py 契约。

覆盖：
 1. canonical.py 的 JSON 往返（同内容 -> 同字节）
 2. canonical.py 的 validate() 在真实 JWD 上 **无 E- 项**（只有预期的 W- 报告项）
 3. 契约 §a.4 的 ShapeVal 解码规则（Kind 1/2/3/26/303）在样本 28 个截面上成立
 4. 契约 §e 的候选键规则：Kind=303 的 `<库族码>-<打包规格串>` 能在用户原件里命中

运行：python test/test_contract_selfcheck.py
只读样本；不写任何文件。
"""
import io
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from canonical import (CONTRACT_VERSION, Level, Joint, Section, Member, Slab, Load,
                       Resolution, Model, TOL, SHORT_MEMBER_MM)

PLUG = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'
JWD = os.path.join(PLUG, 'JLCJ2.jwd')
SECMAP = os.path.join(PLUG, 'PKPM转PDMS截面匹配文件.txt')

fails = []


def check(cond, label, detail=''):
    print('  [%s] %s %s' % ('OK' if cond else 'FAIL', label, detail))
    if not cond:
        fails.append(label)


# ---------------------------------------------------------------- 0. 往返
print('=== 0. 手工构造的小模型：JSON 往返 ===')
m0 = Model(source='unit-test', source_format='jwd')
m0.levels = [Level(1, 101, 1, -2000.0, -1000.0, 1000.0),
             Level(2, 102, 2, -1000.0, 6600.0, 7600.0)]
m0.joints = {7: Joint(7, 2, 100.0, 200.0, 6600.0, no=1)}
m0.sections = {9: Section(9, 1, 6, '', {'B': 300.0, 'H': 600.0}, table='beam', no=1,
                          shapeval='1,300,600,6,9', params=['300', '600'])}
m0.members = [Member(11, 'beam', 2, 9, (100.0, 200.0, 6600.0), (600.0, 200.0, 6600.0),
                     ecc=(0.0,), grid_id=5)]
m0.slabs = [Slab(21, 2, [(0.0, 0.0), (1000.0, 0.0), (1000.0, 1000.0)],
                 z=6600.0, thickness=120.0)]
m0.loads = [Load(31, 'joint-point', 7, (28.0, None, 0.0), ['28.00', '', '0.00'],
                 load_sect_id=1007)]
j1 = m0.to_json()
j2 = Model.from_json(j1).to_json()
check(j1 == j2, 'JSON 往返字节一致', '(%d bytes)' % len(j1))
check(Model.from_json(j1).members[0].start == (100.0, 200.0, 6600.0), 'tuple 往返')
check(m0.validate() == [], '小模型 validate() 无问题', str(m0.validate()))
m0.members[0].end = (100.0, 200.0, 6600.0)
check(any(s.startswith('E-MEM-ZERO') for s in m0.validate()), '零长度构件被 E- 抓到')
m0.members[0].end = (600.0, 200.0, 6600.0)
m0.slabs[0].polygon = [(0.0, 0.0), (1.0, 0.0)]
check(any(s.startswith('E-SLAB-POLY') for s in m0.validate()), '多边形<3 顶点被 E- 抓到')
check(Resolution().status == 'unresolved', 'Resolution 默认 status=unresolved')
check(CONTRACT_VERSION == '1.0', 'CONTRACT_VERSION', CONTRACT_VERSION)

# ------------------------------------------------- 1/2/3/4. 真实 JWD 上验证
print('\n=== 1. 真实 JWD：按契约公式装配 Model 并 validate() ===')


def dec(b):
    """契约 §9.1：逐值 ASCII -> UTF-8 -> GBK。"""
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


def shapeval_params(sv):
    """契约 §a.4：切分 -> 去掉尾部 (Mat, ID) -> 参数体原文。"""
    toks = [t for t in (sv or '').split(',')]
    while toks and toks[-1] == '':
        toks.pop()
    return toks[1:-2], toks


def packed_str(params):
    """契约 §a.4：Kind=303 槽 2..7 = 16 位字符对，首字符在低字节，NUL 截断。"""
    out = bytearray()
    for t in params[1:7]:
        v = int(float(t)) if t else 0
        out.append(v & 0xFF)
        out.append((v >> 8) & 0xFF)
    return bytes(out).split(b'\x00')[0].decode('ascii', 'replace')


def dims_of(kind, params):
    d = {}
    if kind == 1 and len(params) >= 2:
        d = {'B': float(params[0]), 'H': float(params[1])}
    elif kind == 2 and len(params) >= 6:
        d = {'Tw': float(params[0]), 'H': float(params[1]), 'B1': float(params[2]),
             'T1': float(params[3]), 'B2': float(params[4]), 'T2': float(params[5])}
    elif kind == 3 and len(params) >= 1:
        d = {'d': float(params[0])}
    elif kind == 26 and len(params) >= 7:
        d = {'family': int(float(params[0])), 'subtype': int(float(params[1])),
             'H': float(params[2]), 'B': float(params[4]), 'tf': float(params[5]),
             'tw': float(params[6])}
    elif kind == 303 and len(params) >= 30:
        d = {'family': int(float(params[0])), 'spec_str': packed_str(params),
             'd': float(params[17]), 'b': float(params[19]),
             'lib_family': int(float(params[26]))}
    return d


model = Model(source=JWD, source_format='jwd')
for fid, no, name, sid, lvl, h in q('SELECT ID, No_, Name, StdFlrID, LevelB, Height '
                                    'FROM pkpmFloor ORDER BY LevelB'):
    model.levels.append(Level(sid, fid, no, lvl, lvl + h, h, name or ''))
lvm = model.level_map()

for jid, no, sid, x, y, hd in q('SELECT ID, No_, StdFlrID, X, Y, HDiff FROM pkpmJoint'):
    model.joints[jid] = Joint(jid, sid, x, y, lvm[sid].z_top + (hd or 0), no, hd or 0)

sec_kind = {}
for tbl, tag in (('pkpmBeamSect', 'beam'), ('pkpmColSect', 'col'),
                 ('pkpmBraceSect', 'brace')):
    for sid, no, name, mat, kind, sv in q('SELECT ID, No_, Name, Mat, Kind, ShapeVal '
                                          'FROM %s' % tbl):
        params, _ = shapeval_params(sv)
        dims = dims_of(kind, params)
        sec_kind[sid] = kind
        model.sections[sid] = Section(sid, kind, mat, name or '', dims, tag, no,
                                      sv or '', params, 'selfcheck')

grids = {r[0]: (r[1], r[2]) for r in q('SELECT ID, Jt1ID, Jt2ID FROM pkpmGrid')}
for mid, no, sid, secid, jt, ex, ey, rot, hdb in q(
        'SELECT ID, No_, StdFlrID, SectID, JtID, EccX, EccY, Rotation, HDiffB '
        'FROM pkpmColSeg'):
    L = lvm[sid]
    j = model.joints[jt]
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


def nums(s):
    return [float(t) for t in (s or '').split(',') if t.strip()]


for sid, no, sf, gids, vx, vy, vz, hole, th, dead, live in q(
        'SELECT ID, No_, StdFlrID, GridsID, VertexX, VertexY, VertexZ, RoomIsHole, '
        'Thickness, dead, live FROM pkpmSlab'):
    L = lvm[sf]
    xs, ys = nums(vx), nums(vy)
    model.slabs.append(Slab(sid, sf, list(zip(xs, ys)), L.z_top, th or 0.0, bool(hole),
                            dead or 0.0, live or 0.0,
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

model.notes.append('架构自检装配（等价于 jwd_read.py 的公式），非交付代码')

cnt = model.counts()
print('  counts =', cnt)
exp = {'levels': 5, 'joints': 382, 'members_total': 811, 'slabs': 222,
       'slabs_holes': 29, 'loads_total': 121, 'sections': 28}
check(cnt['levels'] == 5 and cnt['joints'] == 382 and cnt['members_total'] == 811
      and cnt['slabs'] == 222 and cnt['slabs_holes'] == 29 and cnt['loads_total'] == 121
      and cnt['sections'] == 28, '计数与侦察报告一致', str(exp))
check(cnt['members'] == {'beam': 598, 'column': 200, 'brace': 13},
      '构件分类计数', str(cnt['members']))
check(cnt['loads'] == {'beam-line': 77, 'joint-point': 44}, '荷载分类计数')

problems = model.validate()
errs = [s for s in problems if s.startswith('E-')]
warns = [s for s in problems if s.startswith('W-')]
print('  validate: E-%d  W-%d' % (len(errs), len(warns)))
for s in errs:
    print('    ', s)
kinds = {}
for s in warns:
    kinds[s.split(':')[0]] = kinds.get(s.split(':')[0], 0) + 1
for k in sorted(kinds):
    print('     %s x %d' % (k, kinds[k]))
check(not errs, '真实 JWD 上无 E- 项（契约不变式成立）')
check(any(s.startswith('W-MEM-ZRANGE') for s in warns),
      'HDiff2=6650 的异常支撑落在 W-MEM-ZRANGE')
check(any(s.startswith('W-MEM-SHORT') for s in warns), '极短梁落在 W-MEM-SHORT')

# ------------------------------------------------------ 3/4. ShapeVal 与候选键
print('\n=== 2. ShapeVal 解码规则 + §e 候选键规则 ===')
txt = open(SECMAP, 'rb').read().decode('gbk')
secmap = {}
for ln in txt.split('\r\n'):
    s = ln.strip()
    if not s or s.startswith('//') or (s.startswith('/') and ',' not in s):
        continue
    if ',' not in s:
        continue
    l, r = s.split(',', 1)
    r = ' '.join(r.split())
    secmap[l.strip()] = r if r.startswith('/') else '/' + r

by_kind = {}
for s in model.sections.values():
    by_kind.setdefault(s.kind, []).append(s)
for k in sorted(by_kind):
    print('  Kind=%-4s n=%-3d dims[0]=%s' % (k, len(by_kind[k]), by_kind[k][0].dims))

k303 = [s for s in model.sections.values() if s.kind == 303]
hits = []
for s in k303:
    key = '%s-%s' % (s.dims['lib_family'], s.dims['spec_str'])
    hits.append((s.name, key, secmap.get(key)))
for n, k, v in hits:
    print('  303: %-16s key=%-16s -> %s' % (n, k, v))
check(all(v for _, _, v in hits), 'Kind=303 的 <库族码>-<规格串> 全部命中原件')

k26 = [s for s in model.sections.values() if s.kind == 26]
miss1 = [s.name for s in k26 if s.name and s.name not in secmap]
miss2 = [s.name for s in k26
         if not (s.name in secmap or ('%s-%s' % (s.dims['subtype'], s.name)) in secmap)]
print('  Kind=26 共 %d：只按 Name 命中 %d 个（未中 %s）；'
      '叠加 <子类型>-<Name> 候选后未中 %d 个 %s'
      % (len(k26), len(k26) - len(miss1), miss1, len(miss2), miss2))
check(len(miss1) == 1 and miss1 == ['[18a'],
      'Kind=26 只用 Name 时 [18a 未命中（需子类型前缀）')
check(not miss2, 'Kind=26 用 {Name, <子类型>-<Name>} 两个候选键后 8/8 命中')
check(secmap.get('2-[18a') == '/C_LIGHT-SPEC/CL18a',
      '[18a -> 2-[18a -> /C_LIGHT-SPEC/CL18a')

print('\n=== 结论 ===')
print('FAIL 项: %d %s' % (len(fails), fails if fails else ''))
sys.exit(1 if fails else 0)
