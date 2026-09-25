# -*- coding: utf-8 -*-
"""实施包⑨ 侦察：内置转化表 engine/section_table.csv 的实际内容 + 与目录宏的交叉核对。

只读；输出到 stdout（由调用方重定向）。运行：python test/probe_v2_db_source.py
"""
import csv
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, '..'))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

CSV = os.path.join(PKG, 'engine', 'section_table.csv')
MACRO = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\PKPM（PDMS数据库）.txt'


def load_rows(path):
    with io.open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


rows = load_rows(CSV)
print('=== 1. 表规模 ===')
print('  行数 =', len(rows))
print('  列 =', list(rows[0].keys()))
print('  meta.json =', json.load(io.open(os.path.join(PKG, 'engine',
      'section_table.meta.json'), encoding='utf-8'))['stats'])


def dist(key, limit=30):
    d = {}
    for r in rows:
        d[r[key]] = d.get(r[key], 0) + 1
    items = sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))
    return items[:limit], len(d)


print('\n=== 2. 分布 ===')
for col in ('kind', 'family_code', 'mat', 'is_parametric', 'confidence'):
    items, n = dist(col)
    print('  %-14s 取值数=%-4d %s' % (col, n, items))

print('\n=== 3. 各 kind 的 dims 键空间（决定能否按 §k.3 反算）===')
by_kind = {}
for r in rows:
    by_kind.setdefault(int(r['kind'] or 0), []).append(r)
for k in sorted(by_kind):
    rs = by_kind[k]
    keys = set()
    for r in rs:
        keys |= set(json.loads(r['dims_json'] or '{}').keys())
    print('  Kind=%-4d n=%-5d dims 键 = %s' % (k, len(rs), sorted(keys)))
    fams = {}
    for r in rs:
        fams[int(r['family_code'] or 0)] = fams.get(int(r['family_code'] or 0), 0) + 1
    print('             family_code 分布 = %s' % sorted(fams.items(), key=lambda x: -x[1])[:12])

print('\n=== 4. 抽样（每 kind 前 3 条，看 shapeval/dims/extra 的实际形状）===')
for k in sorted(by_kind):
    print('  --- Kind=%d' % k)
    for r in by_kind[k][:3]:
        print('    key=%-26s pkpm=%-20s fam=%-4s spec=%s'
              % (r['key'][:26], r['pkpm_name'][:20], r['family_code'], r['pdms_spec_path']))
        print('       shapeval=%r' % (r['shapeval'][:70],))
        print('       dims=%s' % (r['dims_json'][:120],))
        ex = json.loads(r['extra_json'] or '{}')
        print('       extra keys=%s' % sorted(ex.keys())[:14])

print('\n=== 5. §k.3 反算可行性（按 kind 逐条判定）===')
def need(r, *keys):
    d = json.loads(r['dims_json'] or '{}')
    return all(d.get(k) is not None for k in keys)

print('  Kind=26 且 family==39（需 H,B,tf,tw）: %d / 共 %d'
      % (sum(1 for r in by_kind.get(26, []) if int(r['family_code'] or 0) == 39
             and need(r, 'H', 'B', 'tf', 'tw')), len(by_kind.get(26, []))))
print('  Kind=26 且 family!=39（§k.3: 不可反算）: %d'
      % sum(1 for r in by_kind.get(26, []) if int(r['family_code'] or 0) != 39))
k303 = by_kind.get(303, [])
print('  Kind=303 且 dims 有 spec_str,d,lib_family: %d / 共 %d'
      % (sum(1 for r in k303 if need(r, 'spec_str', 'd', 'lib_family')), len(k303)))
shared = set()
for r in k303:
    shared |= set(json.loads(r['dims_json'] or '{}').keys())
print('    Kind=303 的 dims 键空间 =', sorted(shared))
print('  Kind=1 且 dims 有 B,H: %d / 共 %d'
      % (sum(1 for r in by_kind.get(1, []) if need(r, 'B', 'H')), len(by_kind.get(1, []))))
print('  Kind=3 且 dims 有 d: %d / 共 %d'
      % (sum(1 for r in by_kind.get(3, []) if need(r, 'd')), len(by_kind.get(3, []))))
print('  shapeval 非空（可直接当 ShapeVal 用，只换尾部 ID）: %d'
      % sum(1 for r in rows if (r['shapeval'] or '').strip()))
print('  含 jwd_id 的行: %d'
      % sum(1 for r in rows if 'jwd_id' in json.loads(r['extra_json'] or '{}')))
print('  jwd_id 示例:', [(r['key'], json.loads(r['extra_json'] or '{}').get('jwd_id'))
                         for r in rows
                         if json.loads(r['extra_json'] or '{}').get('jwd_id')][:6])

print('\n=== 6. family 77（薄壁管/钢管族）的规格串形状 ===')
f77 = [r for r in rows if int(r['family_code'] or 0) == 77]
print('  n =', len(f77))
shapes = {}
for r in f77:
    s = json.loads(r['dims_json'] or '{}').get('spec_str') or ''
    shapes.setdefault(s[:1], 0)
    shapes[s[:1]] = shapes[s[:1]] + 1
print('  规格串首字符分布 =', sorted(shapes.items(), key=lambda x: -x[1]))
for r in f77[:6]:
    d = json.loads(r['dims_json'] or '{}')
    print('    %-22s spec_str=%-14s d=%-8s lib=%s kind=%s'
          % (r['key'][:22], d.get('spec_str'), d.get('d'), d.get('lib_family'), r['kind']))
seps = {}
for r in f77:
    s = json.loads(r['dims_json'] or '{}').get('spec_str') or ''
    seps['star2' if s.count('*') == 2 else ('star1' if s.count('*') == 1 else 'other')] = \
        seps.get('star2' if s.count('*') == 2 else ('star1' if s.count('*') == 1 else 'other'), 0) + 1
print('  形状（* 个数）分布 =', seps)

print('\n=== 7. 目录宏交叉核对（只读前 200 行做计数 + 抽 1 个 SPRFILE 的 PARA）===')
raw = open(MACRO, 'rb').read()
txt = raw.decode('utf-8-sig')
lines = txt.split('\r\n')
print('  行数 =', len(lines), ' BOM =', raw[:3] == b'\xef\xbb\xbf')
for pat in ('NEW SPRFILE', 'NEW SPCOMPONENT', 'NEW STSECTION', 'NEW STCATEGORY',
            'NEW TEXT', 'NEW DTSET', 'NEW DATA', 'NEW PTSSET', 'NEW PLINE',
            'NEW GMSSET', 'NEW PROFILE', 'NEW SPECIFICATION', 'NEW SELEC', 'OLD'):
    print('   %-20s %d' % (pat, sum(1 for l in lines if l.strip().startswith(pat))))
# 抽一个 SPRFILE 的 PARA：找 /HN450X200（行号见 db_pkpm_sections 的证据）
idx = [i for i, l in enumerate(lines) if l.strip().startswith('NEW SPRFILE')
       and 'HN450X200' in l]
print('  /HN450X200 的 NEW SPRFILE 行号（1 基）:', [i + 1 for i in idx])
for i in idx[:1]:
    print('  --- 该处 ±12 行原文 ---')
    for j in range(max(0, i - 2), min(len(lines), i + 13)):
        print('   %6d| %s' % (j + 1, lines[j]))
# SPCOMPONENT /H_INTERNATIONAL-SPEC/HN450X200
idx2 = [i for i, l in enumerate(lines) if 'H_INTERNATIONAL-SPEC/HN450X200' in l]
print('  含 /H_INTERNATIONAL-SPEC/HN450X200 的行:', [i + 1 for i in idx2][:6])
# 参数化族样例：/USER_RECT / /USER_CIRCLE 的 DTSET
for name in ('/USER_RECT', '/USER_CIRCLE', '/USER_H'):
    idx3 = [i for i, l in enumerate(lines) if re.search(r'NEW\s+STCATEGORY\s+%s\b' % re.escape(name), l)]
    print('  NEW STCATEGORY %s 行号: %s' % (name, [i + 1 for i in idx3][:3]))
