# -*- coding: utf-8 -*-
"""实施包⑨ 验收：数据库反向（`db2jwd`）—— 目录宏/内置表 → SectionTable → pkpm*Sect 反算 → .jwd。

跑法：``python test/check_db2jwd_sections.py``（只读 G: 原件与 _recon；产物写 test/_rt_out/）

验收三条（与任务书一一对应）：

  ① 用 ``G:/…/PKPM（PDMS数据库）.txt`` → dbparse → SectionTable → ``pkpm*Sect`` 反算 → 写 .jwd
     → 用 ``jwd_read`` 读回，**外键全部可解析**；
  ② 闭环：再把读回的截面喂回 ``jwd2db``（= 按契约 §k.4 的优先级重查规格），**规格名与来源一致**
     （差异逐条列清单）；
  ③ 明确列出**信息损失**（族码 32 槽序、Kind=2 等未知项的处置）。

源的选择：若 ``engine/sectionlib.py`` + ``engine/dbparse.py`` 已交付 ⇒ 用**真**模块
（``parse_db_macro_file`` → ``SectionTable`` → ``to_jwd_sections``）；否则用本脚本内置的
**替身**：读 ``engine/section_table.csv``（= 契约 §k.2 规定的目录宏机械投影，带 meta.json 的
源 sha256/行数），并用目录宏原件做**溯源抽查**（计数器 + SPRFILE PARA + DTSET DPRO 逐条比对）。
替身与真模块的差别只在这层"取数"，§k.3 的编码规则、写库、读回、闭环全部走交付代码
（``jwd_write.shapeval_for`` / ``write_jwd_sections`` / ``jwd_read`` / ``secmap``）。
"""
import csv
import glob
import io
import json
import os
import re
import shutil
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, '..'))
ENGINE = os.path.join(PKG, 'engine')
sys.path.insert(0, ENGINE)
sys.path.insert(0, HERE)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from canonical import Section, Model                                        # noqa: E402
import jwd_write                                                            # noqa: E402
import _jwd_read_stub as stub                                               # noqa: E402

PLUG = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'
MACRO = os.path.join(PLUG, 'PKPM（PDMS数据库）.txt')
MATCH = os.path.join(PLUG, 'PKPM转PDMS截面匹配文件.txt')
JWD_SAMPLE = os.path.join(PLUG, 'JLCJ2.jwd')
CSV = os.path.join(ENGINE, 'section_table.csv')
OUTDIR = os.path.join(HERE, '_rt_out')
fails = []


def check(cond, label, detail=''):
    print('  [%s] %s %s' % ('OK' if cond else 'FAIL', label, detail))
    if not cond:
        fails.append(label)


def jload(s):
    return json.loads(s) if s else {}


# ================================================================ 0. 源
print('=== 0. 截面源：优先真 dbparse/sectionlib，否则内置表替身 + 目录宏溯源抽查 ===')
real_mode = False
try:
    import sectionlib as _sl                                              # noqa: F401
    import dbparse as _dp                                                 # noqa: F401
    real_mode = hasattr(_sl, 'SectionTable') and hasattr(_dp, 'parse_db_macro_file')
except Exception:
    real_mode = False
check(True, '源模式 = %s' % ('真 sectionlib+dbparse' if real_mode else
                             '内置表 engine/section_table.csv（替身）'), '')
rows = []
with io.open(CSV, encoding='utf-8-sig', newline='') as fh:
    rows = list(csv.DictReader(fh))
meta = json.load(io.open(os.path.join(ENGINE, 'section_table.meta.json'), encoding='utf-8'))
print('  内置表 %d 行；meta.stats=%s' % (len(rows), meta['stats']))
check(len(rows) == 3176 and meta['output_rows'] == 3176, '表规模 3,176 行（契约 §k.2）')

raw = open(MACRO, 'rb').read()
mtxt = raw.decode('utf-8-sig')
mlines = mtxt.split('\r\n')
n_spr = sum(1 for l in mlines if l.strip().startswith('NEW SPRFILE'))
n_spc = sum(1 for l in mlines if l.strip().startswith('NEW SPCOMPONENT'))
n_cat = sum(1 for l in mlines if l.strip().startswith('NEW STCATEGORY'))
n_dts = sum(1 for l in mlines if l.strip().startswith('NEW DTSET'))
check(raw[:3] == b'\xef\xbb\xbf' and len(mlines) == 70301
      and n_spr == 2920 and n_spc == 2920 and n_cat == 57 and n_dts == 57,
      '目录宏原件：BOM + 70,301 行 + SPRFILE/SPCOMPONENT 2,920 + STCATEGORY/DTSET 57'
      '（契约 §m.3 的期望数）',
      '行%d spr%d spc%d cat%d dts%d' % (len(mlines), n_spr, n_spc, n_cat, n_dts))

# 溯源抽查：宏的 SPRFILE PARA / DTSET DPRO ↔ 内置表 dims
def macro_sprfiles(lines):
    out, cur = {}, None
    for i, l in enumerate(lines):
        s = l.strip()
        m = re.match(r'NEW SPRFILE (\S+)', s)
        if m:
            cur = m.group(1)
            out[cur] = {'line': i + 1, 'gtyp': '', 'para': []}
            continue
        if cur is None:
            continue
        if s.startswith('GTYP '):
            out[cur]['gtyp'] = s.split(None, 1)[1]
        elif s.startswith('PARA '):
            out[cur]['para'].extend(x for x in s.split()[1:] if x != '$')
        elif s.startswith('NEW '):
            cur = None
    return out


spr = macro_sprfiles(mlines)
print('  宏内解析出 SPRFILE %d 条（含续行拼接：行尾 "$" 表示续行）' % len(spr))
by_name = {r['pkpm_name']: r for r in rows if r['pkpm_name']}
gt = {}
for v in spr.values():
    gt[v['gtyp']] = gt.get(v['gtyp'], 0) + 1
print('  宏 SPRFILE 的 GTYP 分布 = %s（轮廓几何类型，**不作** PKPM 使用位置依据）'
      % sorted(gt.items(), key=lambda x: -x[1])[:8])
probe = [('HN450X200', ('H', 'B', 'tw', 'tf')),
         ('HN300X150', ('H', 'B', 'tw', 'tf')),
         ('HN200X100', ('H', 'B', 'tw', 'tf'))]
ok_probe, detail = True, []
for nm, order in probe:
    sp = spr.get('/' + nm)
    r = by_name.get(nm)
    if not sp or not r:
        ok_probe = False
        detail.append('%s 缺失' % nm)
        continue
    d = jload(r['dims_json'])
    vals = [float(x) for x in sp['para'][:4]]
    pair = dict(zip(('H', 'B', 'tw', 'tf'), vals))
    same = all(abs(float(d[k]) - pair[k]) < 1e-9 for k in pair)
    ok_probe = ok_probe and same
    detail.append('%s PARA%s vs dims %s → %s' % (nm, tuple(vals),
                                                {k: d[k] for k in pair}, same))
check(ok_probe, '溯源抽查：宏 SPRFILE PARA 前 4 项(h,b,tw,tf) 与内置表 dims 逐项一致',
      '; '.join(detail))


def macro_dtset_defaults(lines, stcat):
    """取某 STCATEGORY 的 DTSET DATA 条目（DKEY/DPRO），用于 §l.6 的 RECT/CIRCLE 模板。

    做法（与 ``test/probe_v2_db_dtset.py`` 一致，实测可行）：先按栈式 ``NEW``/``END``
    求该 STCATEGORY 的**配对 ``END``**，再在其区间内只取含 ``DKEY`` 的 ``NEW DATA`` 块
    （``PTSSET/PLINE`` 用 ``PKEY``，不会混进来）。
    """
    def block_range(i):
        depth, j = 0, i
        while j < len(lines):
            s = lines[j].strip()
            if s.startswith('NEW '):
                depth += 1
            elif s == 'END':
                depth -= 1
                if depth <= 0:
                    return i, j
            j += 1
        return i, len(lines) - 1

    starts = [i for i, l in enumerate(lines)
              if re.match(r'NEW\s+STCATEGORY\s+%s\s*$' % re.escape(stcat), l.strip())]
    if not starts:
        return []
    a, b = block_range(starts[0])
    out, k = [], a
    while k <= b:
        if re.match(r'NEW\s+DATA\s*$', lines[k].strip()):
            _, e = block_range(k)
            blk = [lines[x].strip() for x in range(k, e + 1)]
            if any(x.startswith('DKEY ') for x in blk):
                dk = next(x.split(None, 1)[1] for x in blk if x.startswith('DKEY '))
                dp = next((x.split(None, 1)[1] for x in blk if x.startswith('DPRO ')), '')
                dt = next((x.split(None, 1)[1] for x in blk if x.startswith('DTIT ')), '')
                m = re.search(r'\(?\s*(-?[0-9.]+)', dp)
                out.append((dt.strip("' "), dk, float(m.group(1)) if m else None, k + 1))
            k = e + 1
        else:
            k += 1
    return out


rect_def = macro_dtset_defaults(mlines, '/USER_RECT')
circ_def = macro_dtset_defaults(mlines, '/USER_CIRCLE')
print('  /USER_RECT DTSET =', rect_def)
print('  /USER_CIRCLE DTSET =', circ_def)
check([x[0] for x in rect_def] == ['B', 'H'] and [x[2] for x in rect_def] == [500.0, 500.0],
      '§l.6 的 RECT 模板：DTSET DKEY B/H 的 DPRO = 500/500（宏 L2836/L2846）',
      str(rect_def))
check([x[0] for x in circ_def] == ['D'] and circ_def[0][2] == 300.0,
      '§l.6 的 CIRCLE 模板：DTSET DKEY D 的 DPRO = 300（宏 L2504）', str(circ_def))

# ================================================================ 1. 编码保真
print('\n=== 1. ShapeVal 反算保真（拿 JLCJ2 样本 28 行做标尺）===')
from _jwd_read_stub import shapeval_params, dims_of                          # noqa: E402
con = stub.open_ro(JWD_SAMPLE)
sample = []
for tbl, tag in (('pkpmBeamSect', 'beam'), ('pkpmColSect', 'col'),
                 ('pkpmBraceSect', 'brace')):
    for sid, no, name, mat, kind, sv in con.execute(
            'SELECT ID, No_, Name, Mat, Kind, ShapeVal FROM %s ORDER BY ID' % tbl):
        params, _ = shapeval_params(sv)
        sample.append({'table': tag, 'id': sid, 'name': name or '', 'mat': mat,
                       'kind': kind, 'sv': sv, 'params': params,
                       'dims': dims_of(kind, params)})
con.close()
print('  样本截面 %d 行（按 Kind：%s）'
      % (len(sample), {k: sum(1 for s in sample if s['kind'] == k)
                       for k in sorted(set(s['kind'] for s in sample))}))
# (a) 原文路径（params 在）—— v1 行为必须逐字不变
bad_a = []
for s in sample:
    sec = Section(s['id'], s['kind'], s['mat'], s['name'], s['dims'], s['table'], 0,
                  s['sv'], s['params'])
    sv, miss = jwd_write.shapeval_for(sec)
    if sv != s['sv']:
        bad_a.append((s['table'], s['id'], s['sv'], sv, miss))
check(not bad_a, '(a) 原文路径：28/28 行的 ShapeVal **逐字相同**（v1 行为未变）',
      str(bad_a[:2]))
# (b) 构造路径（清空 params）—— R2 §k.3 的模板
ok_b, unenc, bad_b = 0, [], []
for s in sample:
    sec = Section(s['id'], s['kind'], s['mat'], s['name'], s['dims'], s['table'], 0,
                  '', [])
    sv, miss = jwd_write.shapeval_for(sec)
    if not sv:
        unenc.append((s['table'], s['id'], s['kind'], s['name'], miss))
    elif sv == s['sv']:
        ok_b += 1
    else:
        bad_b.append((s['table'], s['id'], s['kind'], s['sv'], sv, miss))
print('  (b) 构造路径：%d 行逐字相同；%d 行不可构造（预期）' % (ok_b, len(unenc)))
for u in unenc:
    print('      不可构造 %s ID=%s Kind=%s name=%r ← %s' % (u[0], u[1], u[2], u[3], u[4]))
check(ok_b == 27 and len(unenc) == 1 and not bad_b,
      '(b) 27/28 逐字相同 + 1 行（Kind=26 族码 32 的 [18a）按 §k.3 报"不可构造"'
      '（Kind=2 按 §a.4 解码的逆照常编码：样本 2/2 行逐字复现；理由见 §5 与引擎文档）',
      'bad=%s' % (bad_b[:2],))
kinds_unenc = sorted(u[2] for u in unenc)
check(kinds_unenc == [26],
      '唯一不可构造的是 §k.3/§l.6 点名的 Kind=26 族码≠39（6 尺寸槽顺序未知）', str(kinds_unenc))

# 303 的构造路径单独逐槽比对（样本 3 行）
print('  Kind=303 构造路径逐槽比对（样本 3 行）:')
n303 = 0
for s in sample:
    if s['kind'] != 303:
        continue
    sec = Section(s['id'], 303, s['mat'], s['name'], s['dims'], s['table'], 0, '', [])
    sv, miss = jwd_write.shapeval_for(sec)
    a, b = sv.split(','), s['sv'].split(',')
    diff = [(i, b[i], a[i]) for i in range(min(len(a), len(b))) if a[i] != b[i]]
    print('    ID=%-6s 槽数 %d/%d 差异 %s' % (s['id'], len(a), len(b), diff or '无'))
    check(sv == s['sv'], 'Kind=303 ID=%s 构造结果与样本**逐字段相同**（84 字段）' % s['id'],
          str(diff))
    n303 += 1
check(n303 == 3, '样本 3 行 Kind=303 全部比对过', str(n303))

# ================================================================ 2. 覆盖范围
print('\n=== 2. §l.6 覆盖范围（可反算 / 不可反算）===')
sections = {'beam': [], 'col': [], 'brace': []}
not_closable, next_id = {}, 100000


def put(rec, kind, dims, key):
    global next_id
    next_id += 1
    name = rec['pkpm_name']
    sections['beam'].append(Section(next_id, kind, int(rec['mat'] or 5), name, dims,
                                    '', 0, '', [], sectionlib_note(rec, kind)))


def sectionlib_note(rec, kind):
    return ('内置表 confidence=%s source=%s；db2jwd 构造（§l.6 覆盖族）'
            % (rec['confidence'], rec['source']))


covered_by_kind, details = {}, []
rect_derived, overlong, overlong_lib = [], [], {}
for r in rows:
    fc = int(r['family_code'] or 0)
    d = jload(r['dims_json'])
    stcat = jload(r['extra_json']).get('pdms_stcategory') or ''
    if fc == 39 and all(d.get(k) is not None for k in ('H', 'B', 'tf', 'tw')):
        put(r, 26, {'family': 39, 'subtype': 1, 'H': d['H'], 'B': d['B'],
                    'tf': d['tf'], 'tw': d['tw']}, r['key'])
        covered_by_kind[26] = covered_by_kind.get(26, 0) + 1
    elif fc == 77 and '-' in r['key']:
        lib, spec = r['key'].split('-', 1)
        dd = d.get('d')
        if dd is None:
            # 矩形管（B<a>*<b>*<t>）在内置表里没有 d 键（只有 B/H/t）⇒ 按规格串首数字取 d
            # （§k.3 的前置条件要求调用方给出 d；槽 20 的另一边长未观测，仍写 d —— 见 §5 损失清单）
            m = re.match(r'^[A-Za-z]([0-9.]+)', spec)
            dd = float(m.group(1)) if m else None
            rect_derived.append((r['key'], d.get('B'), d.get('H'), d.get('t'), dd))
        if len(spec) > 12:
            overlong.append((r['key'], len(spec)))
            overlong_lib[lib] = overlong_lib.get(lib, 0) + 1
        put(r, 303, {'family': 77, 'lib_family': int(lib), 'spec_str': spec, 'd': dd,
                     'b': dd}, r['key'])
        covered_by_kind[303] = covered_by_kind.get(303, 0) + 1
    elif stcat == '/USER_RECT':
        put(r, 1, {'B': rect_def[0][2], 'H': rect_def[1][2]}, r['key'])
        covered_by_kind[1] = covered_by_kind.get(1, 0) + 1
    elif stcat == '/USER_CIRCLE' or fc == 3:
        put(r, 3, {'d': circ_def[0][2]}, r['key'])
        covered_by_kind[3] = covered_by_kind.get(3, 0) + 1
    else:
        key = stcat or ('family_code %d' % fc)
        not_closable[key] = not_closable.get(key, 0) + 1
covered = sum(covered_by_kind.values())
print('  可反算 %d 条（按 Kind：%s）' % (covered, dict(sorted(covered_by_kind.items()))))
print('  其中矩形管（表里无 d 键、按规格串首数字取 d）%d 条，样例 key/B/H/t/取到的 d：%s'
      % (len(rect_derived), rect_derived[:4]))
print('  其中规格串 > 12 字符（超出 6 槽×2 的打包容量）%d 条，样例 %s'
      % (len(overlong), overlong[:4]))
print('      按库族码分布（1=热轧无缝圆管 4=冷弯矩形管GB50018 5=冷弯圆管 6=方管GB6728'
      ' 7=矩形管GB6728 8=方管GB178 9=矩形管GB178）：%s'
      % sorted(overlong_lib.items()))
print('  不可反算 %d 条，按族（前 12）：%s'
      % (sum(not_closable.values()),
         sorted(not_closable.items(), key=lambda x: -x[1])[:12]))
check(covered == 1331 and covered_by_kind == {1: 1, 3: 1, 26: 130, 303: 1199},
      '§l.6 的 ✅ 覆盖 = 1,331 条（26:130 / 303:1199 / 1:1 / 3:1）', str(covered_by_kind))
check(sum(not_closable.values()) == 3176 - covered,
      '§l.6 的 ❌ 覆盖 = %d 条（跳过 + 报告，不静默）' % sum(not_closable.values()))

# ================================================================ 3. 验收①：写库 + 读回
print('\n=== 3. 验收①：write_jwd_sections → 外键全解析 + jwd_read 读回 ===')
if not os.path.isdir(OUTDIR):
    os.makedirs(OUTDIR)
OUT = os.path.join(OUTDIR, 'db_sections.jwd')
res = jwd_write.write_jwd_sections(sections, OUT, opts={'project': 'JLCJ2'})
written = res['tables']['pkpmBeamSect']
print('  write_jwd_sections: rows=%d 三张截面表=%s'
      % (res['rows'], {k: res['tables'][k] for k in
                       ('pkpmBeamSect', 'pkpmColSect', 'pkpmBraceSect')}))
print('  warnings 条数=%d；skipped 条数=%d' % (len(res['warnings']), len(res['skipped'])))
check(set(res.keys()) == {'tables', 'rows', 'members', 'slabs', 'walls', 'loads',
                          'skipped', 'warnings'}, '返回值键同 §b.3')
check(len(res['tables']) == 46 and written == covered - len(overlong)
      and len(res['skipped']) == len(overlong),
      '46 张表的行数都报出；可反算的 %d 条里 %d 条写进 pkpmBeamSect，%d 条因规格串超打包'
      '容量被跳过并逐条报告（不截断、不静默）'
      % (covered, written, len(overlong)),
      str(res['skipped'][:1]))
check(any('截面定义文件' in x for x in res['warnings']),
      'warnings 注明"这是截面定义文件，不含几何"（§l.6）')
con = stub.open_ro(OUT)
check(con.execute('PRAGMA encoding').fetchone()[0] == 'UTF-8', 'PRAGMA encoding=UTF-8')
tabs = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
idxs = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='index' "
                                 "AND name NOT LIKE 'sqlite_autoindex%'")]
check(len(tabs) == 46 and len(idxs) == 79, '46 张表 + 79 条索引（DDL 同 §b.3）',
      '%d/%d' % (len(tabs), len(idxs)))
empty = [t for t in tabs if con.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0] == 0]
print('  非空表 = %s' % [t for t in tabs if t not in empty])
bad = stub.fk_violations(con, jwd_write._DDL_TABLES)
check(not bad, '验收①：**外键全部可解析**（45 条 REFERENCES 逐列 SQL 检查）', str(bad))
childs = [x for x in ('pkpmBeamSeg', 'pkpmColSeg', 'pkpmBraceSeg', 'pkpmMidBeamSeg',
                      'pkpmSubBeam', 'pkpmCantiSlab')]
print('  引用截面表的子表行数（都应为 0 ⇒ 父表引用完整）：%s'
      % {t: con.execute('SELECT COUNT(*) FROM %s' % t).fetchone()[0] for t in childs})
check(all(con.execute('SELECT COUNT(*) FROM %s' % t).fetchone()[0] == 0 for t in childs),
      '没有子表行引用缺席的父表（本文件只含截面定义）')
check(con.execute('SELECT ParaVal FROM pkpmSysInfo WHERE ID=2').fetchone()[0] == 'JLCJ2',
      'opts.project 写进 pkpmSysInfo.ID=2（§l.6 的括注）')
tail = []
for t in ('pkpmBeamSect',):
    for sid, kind, sv in con.execute('SELECT ID, Kind, ShapeVal FROM %s' % t):
        f = [x for x in sv.split(',') if x != '']
        if int(f[-1]) != sid or int(f[0]) != kind:
            tail.append((sid, kind, sv))
check(not tail, '§a.4 不变式：每行 ShapeVal 的首字段 == Kind、末字段 == 本行 ID',
      str(tail[:2]))
con.close()

import jwd_read                                                              # noqa: E402
m = jwd_read.read_jwd(OUT)
print('  jwd_read 读回：sections=%d（按表 %s）；E- 项 %d'
      % (len(m.sections), {t: sum(1 for s in m.sections.values() if s.table == t)
                           for t in ('beam', 'col', 'brace')},
         len(m.errors())))
check(len(m.sections) == written, '读回截面数 = 写入数（%d）' % written)
check(not m.errors(), '读回 Model 无 E- 项', str(m.errors()[:3]))
km = {k: sum(1 for s in m.sections.values() if s.kind == k)
      for k in sorted(set(s.kind for s in m.sections.values()))}
exp_km = {1: 1, 3: 1, 26: 130, 303: 1199 - len(overlong)}
check(km == exp_km, '读回的 Kind 分布与原表一致（303 少 %d 条超容量串）' % len(overlong),
      '%s vs %s' % (km, exp_km))
# 逐条比对 dims（读回 vs 源）—— 这是"反算正确"的最强检查
src_map = {}
for key, table in (('beam', 'pkpmBeamSect'),):
    pass
src_by_kind = {}
for r in rows:
    fc = int(r['family_code'] or 0)
    d = jload(r['dims_json'])
    if fc == 39 and all(d.get(k) is not None for k in ('H', 'B', 'tf', 'tw')):
        src_by_kind[('26', r['pkpm_name'])] = {'H': float(d['H']), 'B': float(d['B']),
                                              'tf': float(d['tf']), 'tw': float(d['tw'])}
    elif fc == 77 and '-' in r['key']:
        lib, spec = r['key'].split('-', 1)
        dd = d.get('d')
        if dd is None:
            mo = re.match(r'^[A-Za-z]([0-9.]+)', spec)
            dd = float(mo.group(1)) if mo else None
        src_by_kind[('303', r['pkpm_name'])] = {'lib_family': int(lib), 'spec_str': spec,
                                                'd': dd}
n_cmp, bad_cmp = 0, []
for s in m.sections.values():
    sk = (str(s.kind), s.name)
    if sk not in src_by_kind:
        continue
    n_cmp += 1
    for k, v in src_by_kind[sk].items():
        got = s.dims.get(k)
        if v is None:
            continue
        if k == 'spec_str':
            ok_k = (str(got) == str(v))
        else:
            ok_k = (got is not None and abs(float(got) - float(v)) <= 1e-9)
        if not ok_k:
            bad_cmp.append((s.kind, s.name, k, v, got))
check(n_cmp == 1329 - len(overlong) and not bad_cmp,
      '读回后 Kind=26/303 的 dims 与原表逐项一致（%d 条比对；超容量串已跳过）' % n_cmp,
      str(bad_cmp[:3]))

# 三表分派的变体（证明 writer 支持三张表各自的 ID/No_ 空间）
print('  变体：把 Kind=1 放 col、Kind=3 放 brace、26/303 放 beam —— 三表各自的 ID/No_ 空间')
var = {'beam': [], 'col': [], 'brace': []}
var['col'] = [s for s in sections['beam'] if s.kind == 1][:1]
var['brace'] = [s for s in sections['beam'] if s.kind == 3][:1]
var['beam'] = [s for s in sections['beam'] if s.kind in (26, 303)]
OUT2 = os.path.join(OUTDIR, 'db_sections_split.jwd')
res2 = jwd_write.write_jwd_sections(var, OUT2)
con2 = stub.open_ro(OUT2)
cnt = {t: con2.execute('SELECT COUNT(*) FROM %s' % t).fetchone()[0]
       for t in ('pkpmBeamSect', 'pkpmColSect', 'pkpmBraceSect')}
bad2 = stub.fk_violations(con2, jwd_write._DDL_TABLES)
con2.close()
m2 = jwd_read.read_jwd(OUT2)
print('  三表行数 = %s；读回 %d 条；外键违规 %d' % (cnt, len(m2.sections), len(bad2)))
check(cnt == {'pkpmBeamSect': 1329 - len(overlong), 'pkpmColSect': 1, 'pkpmBraceSect': 1}
      and not bad2 and len(m2.sections) == written,
      '三张表各自的 ID/No_ 空间正确、外键仍全解析')

# ================================================================ 4. 验收②：闭环
print('\n=== 4. 验收②：闭环（读回的截面 → jwd2db → 规格名与来源逐个相等）===')
sys.path.insert(0, ENGINE)
import secmap                                                                 # noqa: E402
smap = secmap.SectionMap.load(MATCH)
by_pkpm = {r['pkpm_name']: r for r in rows if r['pkpm_name']}
by_spec = {r['pdms_spec_path']: r for r in rows}
src_specs = set()
for s in sections['beam']:
    rec = by_pkpm.get(s.name)
    if rec and (s.kind != 303 or len(s.dims.get('spec_str') or '') <= 12):
        src_specs.add(rec['pdms_spec_path'])     # 超容量串本方向写不出去，单独列 not_closable
got_specs, diff_specs = set(), []
CLOSED = {}
for s in m.sections.values():
    rec = by_pkpm.get(s.name)
    spec = rec['pdms_spec_path'] if rec else None
    how = 'builtin.name'
    if spec is None:                       # §e.1 的候选键
        cands = [('%s-%s' % (s.dims.get('lib_family'), s.dims.get('spec_str')))
                 if s.kind == 303 else None,
                 ('%s-%s' % (s.dims.get('subtype'), s.name)) if s.kind == 26 else None]
        for c in cands:
            if c and c in by_pkpm:
                spec, how = by_pkpm[c]['pdms_spec_path'], 'builtin.candidate'
                break
    if spec is None and smap is not None:  # §k.4 的第 2 优先级
        r2 = smap.resolve(s, 'beam')
        if r2.ok:
            spec, how = r2.spec_path, 'secmap.' + r2.status
    if spec is None:
        diff_specs.append({'key': s.name, 'kind': s.kind, 'why': 'jwd2db 侧无法定位规格'})
    else:
        CLOSED[s.name] = how
    got_specs.add(spec)
print('  来源侧规格路径 %d 个；读回→jwd2db 侧 %d 个' % (len(src_specs), len(got_specs)))
print('  定位方式分布：', {h: list(CLOSED.values()).count(h)
                          for h in sorted(set(CLOSED.values()))})
missing = sorted(x for x in (src_specs - got_specs) if x)
extra = sorted(x for x in (got_specs - src_specs) if x)
print('  集合差异：只在来源侧 %d 个，只在读回侧 %d 个' % (len(missing), len(extra)))
check(src_specs == got_specs and not diff_specs,
      '闭环：**规格路径集合逐个相等**（%d 个），无差异条目' % len(src_specs),
      'missing=%s extra=%s' % (missing[:3], extra[:3]))

# 契约 §l.6 的 closure 三键（covered / not_closable / differences）
closure = {
    'covered': len(CLOSED),
    'not_closable': (
        [{'family': k, 'n': v, 'why': '§l.6 的 ❌ 覆盖：族码/槽序未知，不可反算'}
         for k, v in sorted(not_closable.items(), key=lambda x: -x[1])] +
        [{'key': k, 'n': 1, 'why': '规格串 %d 字符 > 打包槽容量 12（§a.4/§k.3），无法表达'
          % n} for k, n in overlong]),
    'differences': [],
}
print('  §l.6 的 closure 三键：covered=%d，not_closable=%d 组（族 %d + 超容量 %d）'
      % (closure['covered'], len(closure['not_closable']), len(not_closable),
         len(overlong)))
check(closure['covered'] == written and len(closure['not_closable']) >= 10,
      'closure 三键齐备（covered / not_closable / differences）且 covered == 写出数（%d）'
      % written)

# 数值差异清单（§l.6 判据 2 的"允许差异"：PARA 精度 vs PKPM 取整）
print('  数值差异清单（内置表 extra.jwd_shapeval ↔ 本次反算，忽略行 ID）:')
n_diff = 0
for r in rows:
    jsv = jload(r['extra_json']).get('jwd_shapeval')
    if not jsv:
        continue
    src = [s for s in sections['beam'] if s.name == r['pkpm_name']]
    if not src:
        continue
    mine = jwd_write.shapeval_for(src[0])[0]
    a = [x for x in jsv.split(',') if x != '']
    b = [x for x in mine.split(',') if x != '']
    d_all = [(i, a[i], b[i]) for i in range(min(len(a), len(b))) if a[i] != b[i]]
    d = [x for x in d_all if x[0] != len(a) - 1]        # 末字段 = 行 ID：本来就该不同
    n_diff += 1
    print('    %-12s 样本 %s' % (r['pkpm_name'], jsv))
    print('                 本次 %s' % mine)
    print('                 差异 %s%s' % (d or '无',
          '（另有末字段=行 ID 不同，设计如此）' if len(d) != len(d_all) else ''))
    if d:
        closure['differences'].append(
            {'key': r['pkpm_name'],
             'why': '；'.join('字段 %d：样本 %s vs 本次 %s' % x for x in d),
             'note': 'PARA 精度高于 PKPM 取整（§k.5 的 db2jwd 第 7 行）；两者映射同一规格名 ⇒ '
                     '不算失败'})
json.dump(closure, io.open(os.path.join(OUTDIR, 'db2jwd_closure.json'), 'w',
                           encoding='utf-8'), ensure_ascii=False, indent=1)
print('  closure.differences = %d 条（已写入 db2jwd_closure.json）'
      % len(closure['differences']))
check(n_diff >= 1, '取到 %d 条"样本原始 ShapeVal"做数值差异比对（其余 26/303 用内置表 '
                   'dims 自校验）' % n_diff)
# ================================================================ 5. 信息损失
print('\n=== 5. 验收③：信息损失清单（族码 32 槽序 / Kind=2 等未知项的处置）===')
LOSS = [
    ('族码 32/31/33/36/37/38/40/66/71/72/73 的 6 尺寸槽顺序未知',
     'unknown', '跳过 + 报告：本次 %d 条不可反算（按族见上）；族码 32 的实测：样本 [18a 行'
     '在清空 params 后按 §k.3 报"不可构造"' % sum(not_closable.values()),
     'db_pkpm_sections.md §4.4 表；契约 §k.3 的 26 行只列族码 39；§12#19'),
    ('Kind=303 规格串 > 12 字符（6 槽 × 2 字符的打包容量）', 'unknown',
     '跳过 + 报告：本次实测 %d 条（族 77 的 1,199 条里 %.1f%%）—— **拒绝编码，绝不截断**。'
     '注：DLL 键表里存在 14 字符串（jwd_format.md §3.2 的 "B300*200*12.00"）⇒ 真实编码可能用'
     '更多打包槽，但样本只观测到 6 槽 ⇒ 按契约不猜'
     % (len(overlong), 100.0 * len(overlong) / 1199.0),
     'contract §a.4/§k.3 的槽 2..7；db_pkpm_sections.md §4.4「长度超过容量则无法表达」'),
    ('Kind=2（焊接 H）字段语义未知（§12#4）', 'unknown',
     '**处置**：db2jwd 的族→Kind 表（§l.6）里没有任何族映射到 Kind=2 ⇒ 该方向不会请求它；'
     '对"带 §a.4 槽位键的 Kind=2"（Tw,H,B1,T1,B2,T2）按解码的逆编码（样本 2/2 行逐字复现，'
     'v1 行为不变），且写库时逐条 warning 提示交错序未证实；只有既无槽位键又无 params 原文时拒绝。'
     '§k.3 的字面"抛 unencodable"与本处置的差异已在引擎文档里写明（依据：§l.6「v1 的 write_jwd '
     '不动」与 §l.6 的族→Kind 表）',
     'jwd_format.md §9.3#5；契约 §k.3/§k.5；引擎 jwd_write._shapeval_body 的注释'),
    ('Kind=303 槽 27/32 只能按规则推（27=名首数字、32=方/圆）', 'partial',
     '本次用样本 3/3 行的槽位实测把两条规则定死（B→16672、D→16640）；'
     '族 77 的 1,199 条规格串首字符只有 B/D ⇒ 全覆盖',
     'contract §k.3；test/_v2_slots.txt §1/§2'),
    ('Kind=303 矩形管（B<a>*<b>*<t>）的槽 20（另一边长）**未观测**', 'unknown',
     '按 §k.3 沿用 d 写槽 20；本次矩形管行数=%d（若存在则其槽 20 是"沿用 d"而非真实另一边长）'
     % sum(1 for r in rows if int(r['family_code'] or 0) == 77
           and (r['key'].split('-', 1)[-1].count('*') == 2)),
     'contract §k.3 的 303 行括注'),
    ('目录宏 PARA 的精度高于 PKPM 自己的取整', 'partial',
     '例：HN300X150 的 tw —— PARA 6.5 vs .jwd 样本 6（本次反算写 6.5，见上"数值差异清单"）',
     '本次 C10/db_pkpm_sections §4.4；契约 §k.5 的 db2jwd 第 7 行'),
    ('族码 19 / TRAPEZOID / DOUBLE_C / RECT 的族码值未解', 'unknown',
     'RECT 按 §l.6 的模板构造 Kind=1（B/H 取 DTSET DPRO=500/500），族码不参与编码；'
     '其余按族跳过',
     'db_pkpm_sections.md §2.3/§8.3；conflicts §4.3'),
    ('Mat：内置表全部 = 5（钢）', 'partial',
     'RECT 族构造出的 Kind=1 也写 Mat=5；PKPM 样本里 Kind=1 恒为 Mat=6（混凝土）'
     '⇒ 该行必须人工确认（内置表 confidence/§l.6 都标 unknown）',
     'contract §k.2 的 mat 行；jwd_format.md §1.5'),
    ('db 侧没有"截面用在哪类构件"的信息 ⇒ 三张表的落位是策略决定', 'unknown',
     '本次替身把 1,331 条全部写进 pkpmBeamSect（并另跑一个三表分派变体证明 writer 支持）；'
     '真 to_jwd_sections 可按自己的策略分派',
     'contract §l.6 未规定；本次实测'),
    ('目录宏 SPRFILE 有、匹配文件没有的 344 条；匹配文件右值失效 256 条', 'partial',
     '本方向只覆盖 §l.6 的族（39/77/RECT/CIRCLE）⇒ 这些条目不参与；'
     '若某条 39/77 的 key 不在匹配文件里，闭环会把它列进"差异清单"',
     'contract §l.5 的验收阈值表'),
]
for field, sev, why, ev in LOSS:
    print('  [%s] %s\n       处置：%s\n       依据：%s' % (sev, field, why, ev))
check(len(LOSS) == 10 and all(x[1] in ('loss', 'partial', 'unknown') for x in LOSS),
      '信息损失清单 %d 条，severity 全部在 §k.5 的词表内' % len(LOSS))
json.dump([{'field': f, 'severity': s, 'reason': w, 'evidence': e} for f, s, w, e in LOSS],
          io.open(os.path.join(OUTDIR, 'db2jwd_losses.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('  已写出 %s' % os.path.join(OUTDIR, 'db2jwd_losses.json'))

# ================================================================ 6. 边界与自卫
print('\n=== 6. 边界与自卫（空输入 / dict 输入 / ID 重复 / 未知键 / 不覆盖样本）===')
OUT3 = os.path.join(OUTDIR, 'db_sections_empty.jwd')
res3 = jwd_write.write_jwd_sections({}, OUT3)
c3 = stub.open_ro(OUT3)
n3 = [t for t in ('pkpmBeamSect', 'pkpmColSect', 'pkpmBraceSect')
      if c3.execute('SELECT COUNT(*) FROM %s' % t).fetchone()[0]]
n_tab3 = c3.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
c3.close()
check(res3['rows'] == 0 and not n3 and n_tab3 == 46
      and any('0 行' in x for x in res3['warnings']),
      '空输入：仍建 46 张表、三张截面表 0 行、warnings 明示', str(res3['warnings'][-2:]))

# dict 形式输入 + 未知键 + 每表独立 ID 空间
d_in = {'col': [{'id': 7, 'kind': 1, 'mat': 6, 'name': '矩300X600',
                 'dims': {'B': 300, 'H': 600}}],
        'zzz': [{'id': 1, 'kind': 1, 'mat': 6, 'name': 'x', 'dims': {'B': 1, 'H': 1}}]}
OUT4 = os.path.join(OUTDIR, 'db_sections_dict.jwd')
res4 = jwd_write.write_jwd_sections(d_in, OUT4, opts={'project': 'P', 'oops': 1})
c4 = stub.open_ro(OUT4)
row = c4.execute('SELECT ID, No_, Name, Mat, Kind, ShapeVal FROM pkpmColSect').fetchall()
c4.close()
print('  dict 输入写出：%s' % (row,))
check(row == [(7, 1, '矩300X600', 6, 1, '1,300,600,6,7,')],
      'dict 形式 Section（kind=1）→ 行与 ShapeVal 正确', str(row))
check(any('未知键' in x for x in res4['warnings'])
      and any('未知键' in x for x in res4['warnings']),
      'sections 的未知键 zzz 与 opts 的未知键 oops 都被报告（不静默）')

bad_in = {'beam': [sections['beam'][0], sections['beam'][0]]}
try:
    jwd_write.write_jwd_sections(bad_in, os.path.join(OUTDIR, 'should_not_exist2.jwd'))
    check(False, '表内 ID 重复必须抛 ValueError')
except ValueError as exc:
    check('ID 重复' in str(exc), '表内 ID 重复 ⇒ ValueError（.jwd 主键唯一性）',
          str(exc)[:70])
check(not os.path.isfile(os.path.join(OUTDIR, 'should_not_exist2.jwd')), '抛错时不产出文件')

# ShapeVal 自带 ID ≠ 行 ID 时：只改末字段（§a.4 的不变式）
alt = {'beam': [Section(999, 26, 5, 'HN450X200',
                        {'family': 39, 'subtype': 1, 'H': 450, 'B': 200, 'tf': 14, 'tw': 9},
                        'beam', 1, '26,39,1,450,0,200,14,9,0,5,4484,', [])]}
OUT5 = os.path.join(OUTDIR, 'db_sections_reid.jwd')
res5 = jwd_write.write_jwd_sections(alt, OUT5)
c5 = stub.open_ro(OUT5)
sv5 = c5.execute('SELECT ID, ShapeVal FROM pkpmBeamSect').fetchone()
c5.close()
check(sv5 == (999, '26,39,1,450,0,200,14,9,0,5,999,'),
      'ShapeVal 自带的末字段（4484）按行 ID（999）改写，其余逐字保留', str(sv5))
print('  产物清单：%s'
      % sorted(os.path.basename(p) for p in glob.glob(os.path.join(OUTDIR, 'db_sections*'))))

print('\n=== 结论 ===')
print('产物：%s' % OUT)
print('FAIL 项: %d %s' % (len(fails), fails if fails else ''))
sys.exit(1 if fails else 0)
