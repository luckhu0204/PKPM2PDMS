# -*- coding: utf-8 -*-
"""实施包⑥ 自检：内置转化表装载 + 截面四向往返（契约 §k / §l.6 / §j.4.7）。

跑什么
------
1. **内置转化表**：``engine/section_table.csv`` 的行数/列序/BOM/sha256（与 meta 比对）+
   ``SectionTable.to_csv()`` 与文件**逐字节**一致；
2. **未解码项登记**：8 条 ``confidence='unknown'`` 逐条打印"怎么才能确认"；
3. **四向往返**（对**两个样本里出现的每一个截面**做 ``decode → encode → decode``）：

   * ``jwd2db``：``JLCJ2.jwd`` 的每一行截面 → ``decode_shapeval`` → 记录 → ``encode_shapeval``
     → ``decode_shapeval``，两次 ``dims`` 必须相同，且回算串与样本**逐字节**一致；
   * ``db2jwd``：内置表 3,176 行 → ``to_jwd_sections()``（§l.6 覆盖范围）→ 逐条回算自校验；
   * ``pdt2db``：``1_PM.pdt`` 的每一条 ``$DEFFRAMESECTION``（含 4 条 ``$DEFWASLABSECTION``）
     → ``decode_defframesection`` → 记录 → ``encode_defframesection`` → ``decode_defframesection``；
   * ``db2pdt``：内置表里可进 ``$DEFFRAMESECTION`` 的行 → 5 行 → 回读 → 再回算；
   * **附加**：``.jwd ↔ .pdt`` 交叉（``jwd→pdt`` 5 行、``pdt→jwd`` ShapeVal），
     以及 ``db2jwd`` 的**闭环集合相等**（§l.6 闭环判据 1/3）。

判定分级（**不许把"说清楚了的不可能"混进"意外失败"**）
------------------------------------------------------

* ``PASS``      —— 往返闭合（含逐字节一致）；
* ``DECLARED``  —— 契约/侦察已声明**不可生成**的项（Kind=2、Kind=26 族码≠39、族码未解的 4 行、
  ``.jwd`` 无力学量…），逐条给出**原因 + 信息损失 + 怎么才能确认**；
* ``FAIL``      —— 契约声称可回算却闭合不了的**意外失败**（本脚本给 0 才算通过）。

运行：``cd /d D:\\AI_Work\\PKPM数据解析\\PKPM-JWD导入导出``
      ``python test\\check_sectionlib_roundtrip.py``
"""

import csv
import hashlib
import io
import json
import os
import re
import sqlite3
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PKG, 'engine'))

import sectionlib as S                                        # noqa: E402
from canonical import RESOLVED, Section                        # noqa: E402
from secmap import SectionMap                                  # noqa: E402

SAMPLES = (r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件')
JWD = os.path.join(SAMPLES, 'JLCJ2.jwd')
PDT = os.path.join(SAMPLES, '1_PM.pdt')
MATCH = os.path.join(SAMPLES, 'PKPM转PDMS截面匹配文件.txt')

CSV_PATH = os.path.join(PKG, 'engine', 'section_table.csv')
META_PATH = os.path.join(PKG, 'engine', 'section_table.meta.json')

fails = []
declared = []


def check(cond, label, detail=''):
    print('  [%s] %s %s' % ('OK' if cond else 'FAIL', label, detail))
    if not cond:
        fails.append(label)
    return bool(cond)


# --------------------------------------------------------------------------
# 通用工具
# --------------------------------------------------------------------------

def _num(v):
    if v is None or v == '':
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return int(f) if f.is_integer() else f


def _eq(a, b, tol=1e-9):
    na, nb = _num(a), _num(b)
    if na is not None and nb is not None:
        return abs(float(na) - float(nb)) <= tol
    return str(a) == str(b)


_RE_SPEC_T = (re.compile(r'^B[0-9.]+(?:\*[0-9.]+)*\*([0-9.]+)$'),
              re.compile(r'^D[0-9.]+X([0-9.]+)$'))
_RE_NUMS = re.compile(r'[0-9]+(?:\.[0-9]+)?')


def spec_thickness(spec):
    """从打包规格串里取壁厚（``B250*10.00``→10、``B300*200*12.00``→12、``D194X8.0``→8）。

    这是 §a.4 的 ``Kind=303`` **没有**独立壁厚槽位的补偿路径：壁厚信息在打包串里、不在 ``dims`` 键上。
    """
    s = str(spec or '')
    if s.count('*') >= 2:
        tail = s.rsplit('*', 1)[1]
        return _num(tail)
    m = _RE_SPEC_T[0].match(s) or _RE_SPEC_T[1].match(s)
    return _num(m.group(1)) if m else None


def compare_dims(d1, d2, kind):
    """``decode`` 两次的 dims 比较（**只要求 d1 的信息不丢、不变**）。

    :returns: ``(ok, missing, changed, derived)``：``missing``/``changed`` 为空才算 ok；
        ``derived`` 是被编解码器"搬进打包串"的键（信息性，不算失败）。
        ``Kind=303`` 的键允许由打包串携带：内置表 77 族 1,199 行实测"串里第 1 个数 == d/H、
        第 2 个数 == B、末个数 == t"，所以**数值能在串里找到**即视为已携带（串就是身份）。
    """
    missing, changed, derived = [], [], []
    extra = [k for k in (d2 or {}) if k not in (d1 or {})]
    nums = None
    if kind == 303 and (d2 or {}).get('spec_str'):
        nums = [float(x) for x in _RE_NUMS.findall(d2['spec_str'])]
    for k, v in (d1 or {}).items():
        if k in (d2 or {}) and _eq(v, d2[k]):
            continue
        if nums is not None:
            nv = _num(v)
            if nv is not None and any(abs(float(nv) - x) <= 1e-9 for x in nums):
                derived.append('%s=%r（在打包串 %r 里）' % (k, v, d2['spec_str']))
                continue
        (changed if k in (d2 or {}) else missing).append(
            '%s: %r -> %r' % (k, v, (d2 or {}).get(k)))
    return (not missing and not changed), missing, changed, derived + extra


def note_declared(direction, what, key, why, loss, how=""):
    declared.append({'direction': direction, 'what': what, 'key': key, 'why': why,
                     'loss': loss, 'how_to_confirm': how})


def s_is_covered(rec):
    """§l.6 的 ✅ 覆盖范围：族码 39 → Kind=26；族码 77 → Kind=303；RECT/CIRCLE 模板。"""
    k = S.effective_kind(rec)
    if k == 26 and S.family_of(rec) == 39:
        return True
    if k == 303:
        return True
    if S._norm_ws(rec.pkpm_name) in (S.TEMPLATE_RECT_KEY, S.TEMPLATE_CIRCLE_KEY):
        return True
    return False


# --------------------------------------------------------------------------
# 样本读取（只读；.jwd 用只读 sqlite，.pdt 用 GBK 逐行）
# --------------------------------------------------------------------------

def dec(b):
    if not isinstance(b, bytes):
        return b
    for enc in ('ascii', 'utf-8'):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode('gbk', 'replace')


def read_jwd_sections(path):
    """``[(table, ID, No_, Name, Mat, Kind, ShapeVal)]``（契约 §b.2 的混合编码规则）。"""
    con = sqlite3.connect('file:' + path.replace('\\', '/') + '?mode=ro', uri=True)
    con.text_factory = dec
    out = []
    for t in ('pkpmBeamSect', 'pkpmColSect', 'pkpmBraceSect', 'pkpmWallSect'):
        cols = [r[1] for r in con.execute('PRAGMA table_info(%s)' % t)]
        if not cols:
            continue
        want = [c for c in ('ID', 'No_', 'Name', 'Mat', 'Kind', 'ShapeVal') if c in cols]
        if 'Kind' not in want or 'ShapeVal' not in want:
            continue
        sql = 'SELECT %s FROM %s ORDER BY ID' % (', '.join(want), t)
        for row in con.execute(sql):
            d = dict(zip(want, row))
            out.append((t.replace('pkpm', '').replace('Sect', '').lower(),
                        int(d.get('ID') or 0), int(d.get('No_') or 0), d.get('Name') or '',
                        int(d.get('Mat') or 0), int(d.get('Kind') or 0),
                        (d.get('ShapeVal') or '')))
    con.close()
    return out


def read_pdt_sections(path):
    """``(frames, waslab)``：``frames`` = 每条 5 行的原文；``waslab`` = ``$DEFWASLABSECTION`` 行。"""
    text = open(path, 'rb').read().decode('gbk')
    lines = text.splitlines()
    frames, waslab = [], []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith('$DEFFRAMESECTION'):
            j = i + 1
            while j < len(lines) and not lines[j].startswith('$'):
                if not lines[j].strip():
                    break
                if lines[j].lstrip().startswith('ID='):
                    frames.append([lines[j + k].rstrip() for k in range(5)])
                    j += 5
                else:
                    j += 1
            i = j
            continue
        if ln.startswith('$DEFWASLABSECTION'):
            j = i + 1
            while j < len(lines) and not lines[j].startswith('$'):
                if lines[j].strip():
                    waslab.append(lines[j].rstrip())
                j += 1
            i = j
            continue
        i += 1
    return frames, waslab


# ==========================================================================
print('=' * 78)
print('【1】内置转化表 engine/section_table.csv（契约 §k.2）')
print('=' * 78)
raw = open(CSV_PATH, 'rb').read()
meta = json.load(open(META_PATH, encoding='utf-8'))
table = S.load_builtin_table()
print('  文件 %d B（含 BOM=%s）；meta.source_rows=%s output_rows=%s'
      % (len(raw), raw[:3] == b'\xef\xbb\xbf', meta['source_rows'], meta['output_rows']))
print('  load_builtin_table() 行数 = %d' % len(table))
check(len(table) == 3176, '加载行数 = 3,176', str(len(table)))
check(S.load_builtin_table() is table, '二次加载命中缓存（同一对象）')
check(not S.verify_builtin_table(), '与 section_table.meta.json 完全一致（行数/列序/BOM/CRLF/sha256/回写对称）')
check(len(table.to_csv().encode('utf-8')) == len(raw)
      and table.to_csv().encode('utf-8') == raw, 'to_csv() 与文件逐字节一致')
by_conf = {}
for r in table:
    by_conf[r.confidence] = by_conf.get(r.confidence, 0) + 1
print('  confidence 分布 = %s' % sorted(by_conf.items()))
print('  族码已知 %d / shapeval 非空 %d / 参数化 %d'
      % (len([r for r in table if r.family_code]),
         len([r for r in table if r.shapeval]),
         len([r for r in table if r.is_parametric])))
vals = table.validate()
kind_cnt = {}
for v in vals:
    kind_cnt[v.split()[0]] = kind_cnt.get(v.split()[0], 0) + 1
print('  validate() 问题 %d 条：%s' % (len(vals), sorted(kind_cnt.items())))
check(not [v for v in vals if v.startswith('E-')],
      '无 E- 级问题（键/规格路径唯一、confidence 词表、desp_index 一致）',
      str([v for v in vals if v.startswith('E-')][:3]))

print()
print('=' * 78)
print('【2】未解码项登记（confidence=unknown + 怎么才能确认）')
print('=' * 78)
items = S.unknown_items()
for it in items:
    print('  - %-20s %s' % (it['id'], it['subject']))
    print('      confidence=%s  affects=%s' % (it['confidence'], ','.join(it['affects'])))
    print('      现状：%s' % it['what'].replace('\n', ' ')[:150])
    print('      怎么才能确认：%s' % it['how_to_confirm'])
check(len(items) >= 8 and all(x['confidence'] == 'unknown' for x in items),
      '未解码项全部 confidence=unknown（8 条契约点名 + 自检新发现）', str(len(items)))
check(all(x.get('how_to_confirm') for x in items), '每一条都写了"怎么才能确认"')
hit = table.unknown_rows()
hit_cnt = {}
for iid, r in hit:
    hit_cnt[iid] = hit_cnt.get(iid, 0) + 1
print('  内置表里触到未解码项的行：%s' % sorted(hit_cnt.items()))
check(set(hit_cnt) <= set(S.UNKNOWN_ITEM_IDS), '登记表覆盖内置表里出现的全部未解码项')

# ==========================================================================
print()
print('=' * 78)
print('【3】方向 jwd2db：JLCJ2.jwd 的全部截面（decode → encode → decode）')
print('=' * 78)
jwd_rows = read_jwd_sections(JWD)
print('  样本 %s：%d 行截面（%s）' % (os.path.basename(JWD), len(jwd_rows),
      ', '.join('%s=%d' % (t, len([x for x in jwd_rows if x[0] == t]))
                for t in sorted(set(x[0] for x in jwd_rows)))))
jwd_pass, jwd_fail, jwd_decl = [], [], []
for tbl, sid, no, name, mat, kind, sv in jwd_rows:
    tag = '%s ID=%d name=%r Kind=%d' % (tbl, sid, name, kind)
    try:
        d1 = S.decode_shapeval(kind, sv)
    except ValueError as e:
        jwd_fail.append('%s 首次解码失败：%s' % (tag, e))
        continue
    sec = Section(id=sid, kind=kind, mat=mat, name=name, dims=d1, table=tbl, no=no,
                  shapeval=sv, params=[])
    rec = S.rec_from_section(sec, builtin=table)
    try:
        sv2 = S.encode_shapeval(rec, sec_id=sid, mat=mat)
    except ValueError as e:
        jwd_decl.append('%s：%s' % (tag, e))
        note_declared('jwd2db', 'section-shapeval', tag, str(e),
                      '该截面的具体尺寸无法回算成 ShapeVal（.jwd 侧只能保留原串）',
                      '见 UNKNOWN_DECODE_ITEMS：%s' % ','.join(S._unencodable_items(kind, rec)))
        continue
    d2 = S.decode_shapeval(kind, sv2)
    ok, missing, changed, extra = compare_dims(d1, d2, kind)
    byte_ok = (sv2 == sv)
    if ok and byte_ok:
        jwd_pass.append(tag)
        print('  [OK] %-46s dims=%s' % (tag, json.dumps(d1, ensure_ascii=False)))
    else:
        jwd_fail.append('%s：dims ok=%s missing=%s changed=%s；逐字节一致=%s\n       样本=%s\n       回算=%s'
                        % (tag, ok, missing, changed, byte_ok, sv, sv2))
print('  —— jwd2db：PASS %d / DECLARED %d / FAIL %d' % (len(jwd_pass), len(jwd_decl), len(jwd_fail)))
for x in jwd_decl:
    print('  [DECLARED] %s' % x)
for x in jwd_fail:
    print('  [FAIL] %s' % x)
check(not jwd_fail, 'jwd2db：样本 28 行全部闭合或已声明不可生成',
      '%d 行意外失败' % len(jwd_fail))
check(len(jwd_pass) + len(jwd_decl) == len(jwd_rows), 'jwd2db：每一行都被处理（无静默跳过）')
print('  jwd2db 闭合率 = %d/%d = %.1f%%（另 %d 行已在契约里声明不可生成）'
      % (len(jwd_pass), len(jwd_rows), 100.0 * len(jwd_pass) / max(1, len(jwd_rows)), len(jwd_decl)))

# ==========================================================================
print()
print('=' * 78)
print('【4】方向 db2jwd：内置表 → to_jwd_sections() → 回算自校验（§l.6 覆盖范围）')
print('=' * 78)
rep = {}
secs = table.to_jwd_sections(report=rep)
print('  to_jwd_sections()：beam=%d col=%d brace=%d（skipped=%d unknown=%d）'
      % (len(secs['beam']), len(secs['col']), len(secs['brace']),
         len(rep['skipped']), len(rep['unknown'])))
dbj_pass, dbj_fail = 0, []
seen_paths = set()
for t in ('beam', 'col', 'brace'):
    for sec in secs[t]:
        tag = '%s id=%d name=%r kind=%d' % (t, sec.id, sec.name, sec.kind)
        try:
            d1 = S.decode_shapeval(sec.kind, sec.shapeval)
            rec = S.rec_from_section(sec, builtin=table)
            sv2 = S.encode_shapeval(rec, sec_id=sec.id, mat=sec.mat)
            d2 = S.decode_shapeval(sec.kind, sv2)
        except ValueError as e:
            dbj_fail.append('%s：%s' % (tag, e))
            continue
        ok, missing, changed, _ = compare_dims(d1, d2, sec.kind)
        if ok and sv2 == sec.shapeval:
            dbj_pass += 1
            seen_paths.add(S._norm_path(rec.pdms_spec_path))
            if rec.pdms_spec_path:
                back = S.from_pdms(rec.pdms_spec_path)
                if back is None or S._norm_path(back.pdms_spec_path) != S._norm_path(rec.pdms_spec_path):
                    dbj_fail.append('%s：from_pdms(%s) 闭环失败'
                                    % (tag, rec.pdms_spec_path))
        else:
            dbj_fail.append('%s：dims ok=%s missing=%s changed=%s；sv 一致=%s'
                            % (tag, ok, missing, changed, sv2 == sec.shapeval))
tot_db = sum(len(secs[t]) for t in ('beam', 'col', 'brace'))
print('  —— db2jwd：PASS %d / FAIL %d（产出 %d 个 Section，去重规格 %d 个）'
      % (dbj_pass, len(dbj_fail), tot_db, len(seen_paths)))
for x in dbj_fail[:10]:
    print('  [FAIL] %s' % x)
if len(dbj_fail) > 10:
    print('  [FAIL] …另有 %d 条' % (len(dbj_fail) - 10))
check(not dbj_fail, 'db2jwd：每条产出的 ShapeVal 回算自洽且 from_pdms 闭环', str(len(dbj_fail)))
skip_reasons = {}
for sk in rep['skipped']:
    key = (sk['kind'], sk['family_code'])
    skip_reasons.setdefault(key, []).append(sk)
print('  跳过（§l.6 的 ❌ 覆盖）按 (Kind, 族码) 归类：')
for (k, f), v in sorted(skip_reasons.items()):
    print('     Kind=%-4s 族码=%-5s %4d 条  未解码项=%s'
          % (k, f, len(v), sorted({i for x in v for i in x['unknown_items']})))
check(bool(rep['skipped']), '不可生成的规格**逐条**列入报告（不静默丢弃）',
      '%d 条' % len(rep['skipped']))
for u in rep['unknown']:
    print('  [unknown] %s（%s）：%s' % (u['key'], ','.join(u['unknown_items']), u['reason'][:100]))

# 闭环判据 1（§l.6）：反算出的规格集合 → from_pdms → 集合逐个相等
want = {S._norm_path(r.pdms_spec_path) for r in table
        if r.pdms_spec_path and s_is_covered(r)}
print('  §l.6 闭环：可反算的规格 %d 个 → from_pdms 逐个回查' % len(want))
miss = [p for p in sorted(want) if S.from_pdms(p) is None]
check(not miss, '闭环判据 1：from_pdms 能查回每个可反算的规格路径', str(miss[:3]))

# ==========================================================================
print()
print('=' * 78)
print('【5】方向 pdt2db：1_PM.pdt 的全部截面（decode → encode → decode）')
print('=' * 78)
frames, waslab = read_pdt_sections(PDT)
print('  样本 %s：$DEFFRAMESECTION %d 条（每条 5 行）、$DEFWASLABSECTION %d 条'
      % (os.path.basename(PDT), len(frames), len(waslab)))
pdt_pass, pdt_fail, pdt_decl = [], [], []
for block in frames:
    f1 = S.decode_defframesection(block)
    tag = 'SHAPE=%s ID=%s name=%r' % (f1['shape'], f1['id'], f1['name'])
    rec = S.rec_from_defframesection(f1)
    # .pdt 不含型钢 tf/tw ⇒ 按 §k.5 的 pdt2db 声明，从**目录宏**（内置表按名命中）补齐
    hit = table.get(pkpm_name=rec.pkpm_name) if rec.pkpm_name else None
    if hit is not None:
        rec.pdms_spec_path = hit.pdms_spec_path
        rec.pdms_catalogue = hit.pdms_catalogue
        for k in ('tf', 'tw'):
            if k not in rec.dims and k in (hit.dims or {}):
                rec.dims[k] = hit.dims[k]
        rec.extra['builtin_key'] = hit.key
    try:
        lines2 = S.encode_defframesection(rec, sec_id=f1['id'], mat=f1['m'])
    except ValueError as e:
        pdt_decl.append('%s：%s' % (tag, e))
        note_declared('pdt2db', 'section-defframesection', tag, str(e),
                      '该形状无法回算成 $DEFFRAMESECTION（须写占位块，§j.7.1）',
                      '见 UNKNOWN_DECODE_ITEMS：%s' % ','.join(S._unencodable_items(
                          S.effective_kind(rec), rec)))
        continue
    f2 = S.decode_defframesection(lines2)
    same = all(f1[k] == f2[k] for k in f1)
    byte_ok = [x.rstrip() for x in lines2] == [x.rstrip() for x in block]
    if same and byte_ok:
        pdt_pass.append(tag)
        print('  [OK] %-38s B1=%-6s H1=%-6s M=%s NAME1=%r'
              % (tag, f1['b1'], f1['h1'], f1['m'], f1['name1']))
    else:
        diff = [k for k in f1 if f1[k] != f2[k]]
        pdt_fail.append('%s：字段不一致 %s；逐字节一致=%s\n       样本=%s\n       回算=%s'
                        % (tag, diff, byte_ok, block[:2], lines2[:2]))
print('  —— pdt2db：PASS %d / DECLARED %d / FAIL %d' % (len(pdt_pass), len(pdt_decl), len(pdt_fail)))
for x in pdt_decl:
    print('  [DECLARED] %s' % x)
for x in pdt_fail:
    print('  [FAIL] %s' % x)
check(not pdt_fail, 'pdt2db：32 条 $DEFFRAMESECTION 逐字节闭合', '%d 条意外失败' % len(pdt_fail))
check(len(pdt_pass) + len(pdt_decl) == len(frames), 'pdt2db：每一条都被处理（无静默跳过）')
print('  pdt2db 闭合率 = %d/%d = %.1f%%'
      % (len(pdt_pass), len(frames), 100.0 * len(pdt_pass) / max(1, len(frames))))

# 4 条 $DEFWASLABSECTION（墙/板截面：不建 Section，走 Section.for_panel + secmap，§b.4/§e.6）
sm = SectionMap.load(MATCH) if os.path.exists(MATCH) else None
if sm is None:
    print('  [WARN] 截面匹配文件不存在 ⇒ 跳过墙板截面与 to_pdms 的 secmap 分支')
else:
    print('  SectionMap 已加载：%d 条原件映射（额外 %d 条）'
          % (len(sm.entries), len(sm.extra_entries)))
    for ln in waslab:
        d = {}
        for chunk in ln.split(','):
            if '=' in chunk:
                k, v = chunk.split('=', 1)
                d[k.strip()] = v.strip()
        th = _num(d.get('T1'))
        name = d.get('NAME', '')
        sec = Section.for_panel('slab', th, name)
        res = sm.resolve(sec, 'slab')
        print('     %-8s T1=%-8s → %-42s status=%-10s desp=%s'
              % (name, th, res.spec_path or '-', res.status, res.desp_params))
        # 厚度必须落地：要么走参数化族的 DESP，要么厚度体现在规格名里（T120 / WALL-600）
        ok = bool(res.spec_path) and (
            (bool(res.desp_params) and _eq(res.desp_params[0], th))
            or (str(int(th)) in res.spec_path))
        if not ok:
            pdt_fail.append('$DEFWASLABSECTION %s 未能给出"规格 + 厚度"（status=%s spec=%s desp=%s）'
                            % (name, res.status, res.spec_path, res.desp_params))
    check(not [x for x in pdt_fail if 'DEFWASLABSECTION' in x],
          '4 条 $DEFWASLABSECTION 的厚度都能落到规格（DESP 或规格名）', str(pdt_fail[-2:]))

# ==========================================================================
print()
print('=' * 78)
print('【6】方向 db2pdt：to_jwd_sections() 的产出 → $DEFFRAMESECTION 5 行 → 回读（§j.4.7）')
print('=' * 78)
dpd_pass, dpd_decl, dpd_fail = 0, {}, 0
for t in ('beam', 'col', 'brace'):
    for sec in secs[t]:
        rec = S.rec_from_section(sec, builtin=table)
        kind = S.output_kind(rec)
        if kind not in (1, 3, 26):
            key = 'kind=%s family=%s' % (kind, S.family_of(rec))
            dpd_decl[key] = dpd_decl.get(key, 0) + 1
            continue
        if kind == 26 and S.family_of(rec) != 39:
            key = 'kind=26 family=%s' % S.family_of(rec)
            dpd_decl[key] = dpd_decl.get(key, 0) + 1
            continue
        try:
            lines = S.encode_defframesection(rec, sec_id=sec.id, mat=sec.mat)
            f1 = S.decode_defframesection(lines)
            rec2 = S.rec_from_defframesection(f1)
            lines2 = S.encode_defframesection(rec2, sec_id=f1['id'], mat=f1['m'])
            f2 = S.decode_defframesection(lines2)
        except ValueError as e:
            dpd_fail += 1
            if dpd_fail <= 5:
                print('  [FAIL] %s：%s' % (rec.key, e))
            continue
        want_b1 = rec.dims.get('B', rec.dims.get('d'))
        if f1 == f2 and _eq(f1['b1'], want_b1):
            dpd_pass += 1
        else:
            dpd_fail += 1
            if dpd_fail <= 5:
                print('  [FAIL] %s：f1 != f2 或 B1 不符（f1=%s dims=%s）'
                      % (rec.key, {k: f1[k] for k in ('b1', 'h1', 'shape')}, rec.dims))
print('  —— db2pdt：PASS %d / FAIL %d' % (dpd_pass, dpd_fail))
print('  不可进 .pdt 的行（§j.7.1 写占位块）：%d 类，共 %d 行'
      % (len(dpd_decl), sum(dpd_decl.values())))
for k, v in sorted(dpd_decl.items())[:8]:
    print('     %-24s %4d 行' % (k, v))
check(dpd_fail == 0, 'db2pdt：可表达的行全部闭合', str(dpd_fail))

# ==========================================================================
print()
print('=' * 78)
print('【7】附加：.jwd ↔ .pdt 交叉（jwd→pdt 5 行 / pdt→jwd ShapeVal）')
print('=' * 78)
cross_pass, cross_decl, cross_fail = 0, [], []
for tbl, sid, no, name, mat, kind, sv in jwd_rows:
    tag = '%s ID=%d name=%r Kind=%d' % (tbl, sid, name, kind)
    d1 = S.decode_shapeval(kind, sv)
    rec = S.rec_from_section(Section(id=sid, kind=kind, mat=mat, name=name, dims=d1,
                                     table=tbl, no=no, shapeval=sv, params=[]), builtin=table)
    try:
        lines = S.encode_defframesection(rec, sec_id=sid, mat=mat)
        f = S.decode_defframesection(lines)
    except ValueError as e:
        cross_decl.append('%s：%s' % (tag, e))
        note_declared('jwd2pdt', 'section-defframesection', tag, str(e),
                      '$DEFFRAMESECTION 没有该形状的表达（§j.7.1 写占位块，'
                      'NUM值全 0）⇒ .jwd 侧的这个截面无法进 .pdt，几何可用但截面尺寸丢失',
                      '见 UNKNOWN_DECODE_ITEMS：%s' % ','.join(
                          S.unencodable_item_ids(S.effective_kind(rec), rec)))
        continue
    if f['shape'] in (1, 3, 39) and f['exi'][-1] == sid:
        cross_pass += 1
    else:
        cross_fail.append('%s：%s' % (tag, f))
print('  jwd→pdt：PASS %d / DECLARED %d / FAIL %d' % (cross_pass, len(cross_decl), len(cross_fail)))
for x in cross_decl:
    print('  [DECLARED] %s' % x)
for x in cross_fail:
    print('  [FAIL] %s' % x)
check(not cross_fail, 'jwd→pdt：可表达的截面全部闭合')

x_pass, x_decl, x_fail = 0, [], []
for block in frames:
    f1 = S.decode_defframesection(block)
    tag = 'SHAPE=%s ID=%s name=%r' % (f1['shape'], f1['id'], f1['name'])
    rec = S.rec_from_defframesection(f1)
    hit = table.get(pkpm_name=rec.pkpm_name) if rec.pkpm_name else None
    if hit is not None:
        for k in ('tf', 'tw'):
            if k not in rec.dims and k in (hit.dims or {}):
                rec.dims[k] = hit.dims[k]
    kind = S.output_kind(rec)
    try:
        sv2 = S.encode_shapeval(rec, sec_id=f1['id'], mat=f1['m'])
    except ValueError as e:
        x_decl.append('%s：%s' % (tag, e))
        continue
    d2 = S.decode_shapeval(kind, sv2)
    if d2:
        x_pass += 1
    else:
        x_fail.append('%s：%s' % (tag, d2))
print('  pdt→jwd：PASS %d / DECLARED %d / FAIL %d' % (x_pass, len(x_decl), len(x_fail)))
for x in x_decl:
    print('  [DECLARED] %s' % x)
for x in x_fail:
    print('  [FAIL] %s' % x)
check(not x_fail, 'pdt→jwd：可表达的截面全部闭合')
# 交叉一致性：同名字（HN400X200/HW200X200）在两个样本里的 tf/tw 应一致
for nm in ('HN400X200', 'HW200X200'):
    a = [x for x in jwd_rows if x[3] == nm]
    b = [S.decode_defframesection(x) for x in frames
         if S.decode_defframesection(x)['name'] == nm]
    if a and b:
        da = S.decode_shapeval(a[0][5], a[0][6])
        hb = table.get(pkpm_name=nm)
        same = (_eq(da['H'], b[0]['h1']) and _eq(da['B'], b[0]['b1'])
                and _eq(da['tf'], hb.dims.get('tf')) and _eq(da['tw'], hb.dims.get('tw')))
        print('  交叉 %-10s .jwd H/B/tf/tw=%s/%s/%s/%s  .pdt H1/B1=%s/%s  目录宏 tf/tw=%s/%s  ⇒ %s'
              % (nm, da['H'], da['B'], da['tf'], da['tw'], b[0]['h1'], b[0]['b1'],
                 hb.dims.get('tf'), hb.dims.get('tw'), '一致' if same else '不一致'))
        check(same, '交叉一致：%s 的 .jwd / .pdt / 目录宏 尺寸互证' % nm)

# ==========================================================================
print()
print('=' * 78)
print('【8】信息损失申报（契约 §k.5 冻结清单，逐方向）')
print('=' * 78)
for d in S.LOSS_DIRECTIONS:
    lst = table.loss_report(d)
    sev = {}
    for x in lst:
        sev[x['severity']] = sev.get(x['severity'], 0) + 1
    print('  %-8s %d 项 %s' % (d, len(lst), sorted(sev.items())))
    for x in lst:
        if x['severity'] in ('unknown', 'loss'):
            print('      [%s] %s' % (x['severity'], x['field']))
    check(bool(lst), '%s：损失清单非空（8 条冻结项）' % d)
    check(bool([x for x in lst if x['severity'] in ('unknown', 'loss', 'partial')]),
          '%s：至少一条 loss/partial/unknown' % d)
try:
    table.loss_report('nope')
    check(False, '非法 direction 应抛 ValueError')
except ValueError:
    check(True, '非法 direction 抛 ValueError')

# ==========================================================================
print()
print('=' * 78)
print('【9】结论')
print('=' * 78)
print('  两个样本的截面总数：%d（.jwd %d + .pdt %d）'
      % (len(jwd_rows) + len(frames), len(jwd_rows), len(frames)))
print('  方向 jwd2db ：PASS %2d / %2d   DECLARED %d'
      % (len(jwd_pass), len(jwd_rows), len(jwd_decl)))
print('  方向 db2jwd ：PASS %2d         FAIL %d（产出 %d 个 Section）'
      % (dbj_pass, len(dbj_fail), tot_db))
print('  方向 pdt2db ：PASS %2d / %2d   DECLARED %d'
      % (len(pdt_pass), len(frames), len(pdt_decl)))
print('  方向 db2pdt ：PASS %2d         FAIL %d' % (dpd_pass, dpd_fail))
print('  附加 jwd→pdt：PASS %2d / %2d   DECLARED %d' % (cross_pass, len(jwd_rows), len(cross_decl)))
print('  附加 pdt→jwd：PASS %2d / %2d   DECLARED %d' % (x_pass, len(frames), len(x_decl)))
tot = len(jwd_rows) + len(frames)
print('  样本截面四向闭合率（可回算的必需 100%%）= %.1f%%'
      % (100.0 * (len(jwd_pass) + len(pdt_pass)) / tot))
print()
print('  已声明的不可生成项（原因 + 信息损失 + 怎么确认，逐条）：')
by_dir = {}
for x in declared:
    by_dir.setdefault(x['direction'], []).append(x)
for d in sorted(by_dir):
    print('   [%s] 共 %d 条：' % (d, len(by_dir[d])))
    for x in by_dir[d]:
        print('      - %s' % x['key'])
        print('        原因：%s' % x['why'])
        print('        损失：%s' % x['loss'])
        print('        确认：%s' % x['how_to_confirm'])
print()
print('  未解码项（confidence=unknown）%d 条：%s' % (len(items), [i['id'] for i in items]))
print()
print('  FAIL 项：%d %s' % (len(fails), fails if fails else '（全部检查通过）'))
sys.exit(1 if fails else 0)
