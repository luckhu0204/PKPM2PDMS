# -*- coding: utf-8 -*-
"""测试用只读装配器 / 外键检查器（**不是交付代码**）。

交付的 ``jwd_read.py`` 属实施包①；本文件只服务本包的验收脚本，公式与
``test/test_contract_selfcheck.py``（契约编制期的架构自检）同源，见契约 §a.5。

被 ``test/check_jwd_write_roundtrip.py``（验收①）与 ``test/check_dump_to_jwd.py``
（验收②）共用。
"""
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))

from canonical import Level, Joint, Section, Member, Slab, Load, Model    # noqa: E402


def dec(b):
    """契约 §b.2 的逐值解码：ASCII -> UTF-8 -> GBK。"""
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
    """契约 §a.5 的装配公式（只读样本/产物）。"""
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


def fk_declarations(ddl_statements):
    """从 46 条 CREATE TABLE 里抽 (子表, 子列, 父表) 三元组。"""
    out = []
    for stmt in ddl_statements:
        tbl = re.match(r'CREATE TABLE\s+(\w+)', stmt).group(1)
        body = stmt[stmt.index('(') + 1:]
        for col, parent in re.findall(r'(\w+)\s+INTEGER\s+REFERENCES\s+(\w+)\s*\(', body):
            out.append((tbl, col, parent))
    return out


def fk_violations(con, ddl_statements):
    """逐条外键 SQL 检查"非空外键在父表里是否都能解析"，返回 [(子表, 子列, 父表, 行数)]。"""
    bad = []
    for tbl, col, parent in fk_declarations(ddl_statements):
        n = con.execute('SELECT COUNT(*) FROM "%s" WHERE "%s" IS NOT NULL AND "%s" NOT IN '
                        '(SELECT ID FROM "%s")' % (tbl, col, col, parent)).fetchone()[0]
        if n:
            bad.append((tbl, col, parent, n))
    return bad
