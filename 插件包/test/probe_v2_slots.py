# -*- coding: utf-8 -*-
"""实施包⑨ 侦察 4：Kind=303 的槽位实测 + 族 39/77 的行形状 + 覆盖范围计数。

只读。运行：python test/probe_v2_slots.py
"""
import csv
import io
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(PKG, 'engine'))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
JWD = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\JLCJ2.jwd'
CSV = os.path.join(PKG, 'engine', 'section_table.csv')

print('=== 1. 样本 Kind=303 的 ShapeVal 逐字段（下标 / 值 / 非零位置）===')
con = sqlite3.connect('file:' + JWD.replace('\\', '/') + '?mode=ro', uri=True)


def dec(b):
    if not isinstance(b, bytes):
        return b
    for e in ('ascii', 'utf-8'):
        try:
            return b.decode(e)
        except Exception:
            pass
    return b.decode('gbk', 'replace')


con.text_factory = dec
for tbl in ('pkpmColSect', 'pkpmBraceSect'):
    for sid, kind, sv in con.execute('SELECT ID, Kind, ShapeVal FROM %s WHERE Kind=303 '
                                     'ORDER BY ID' % tbl):
        f = sv.split(',')
        nz = [(i, f[i]) for i in range(len(f)) if f[i] not in ('', '0')]
        print('  %s ID=%s split_len=%d 非零槽=%s' % (tbl, sid, len(f), nz))
con.close()

print('\n=== 2. 内置表：族 39 / 77 / RECT / CIRCLE 的行形状 ===')
with io.open(CSV, encoding='utf-8-sig', newline='') as fh:
    rows = list(csv.DictReader(fh))


def fam(r):
    return int(r['family_code'] or 0)


def stcat(r):
    return json.loads(r['extra_json'] or '{}').get('pdms_stcategory') or ''


f39 = [r for r in rows if fam(r) == 39]
f77 = [r for r in rows if fam(r) == 77]
print('  族 39: n=%d；kind 列取值=%s' % (len(f39), sorted(set(r['kind'] for r in f39))))
print('      dims 键并集 =', sorted(set(k for r in f39
                                       for k in json.loads(r['dims_json'] or '{}'))))
print('      全都有 H,B,tf,tw: %s' % all(
    all(json.loads(r['dims_json'] or '{}').get(k) is not None for k in ('H', 'B', 'tf', 'tw'))
    for r in f39))
print('      pkpm_name 非空: %d；stcategory 取值=%s'
      % (sum(1 for r in f39 if r['pkpm_name']), sorted(set(stcat(r) for r in f39))))
print('      shapeval 样例 =', [r['shapeval'] for r in f39[:3]])
print('      in_jwd_sample=%d' % sum(1 for r in f39
      if json.loads(r['extra_json'] or '{}').get('in_jwd_sample')))
print('  族 77: n=%d；kind 列取值=%s' % (len(f77), sorted(set(r['kind'] for r in f77))))
print('      dims 键并集 =', sorted(set(k for r in f77
                                       for k in json.loads(r['dims_json'] or '{}'))))
print('      lib_family 分布 =', sorted(
    set(json.loads(r['dims_json'] or '{}').get('lib_family') for r in f77)))
lead = {}
for r in f77:
    k = r['key']
    m = k.split('-', 1)
    spec = m[1] if len(m) == 2 else k
    lead[spec[:1]] = lead.get(spec[:1], 0) + 1
print('      规格串（key 去前缀）首字符分布 =', sorted(lead.items(), key=lambda x: -x[1]))
print('      key 无 "<N>-" 前缀的行数 =', sum(1 for r in f77 if '-' not in r['key']))
print('      pkpm_name == key 的行数 =', sum(1 for r in f77 if r['pkpm_name'] == r['key']))
print('      pkpm_name 非空 =', sum(1 for r in f77 if r['pkpm_name']))
print('      样例:', [(r['key'], r['pkpm_name'],
                       json.loads(r['dims_json'] or '{}').get('d'),
                       json.loads(r['dims_json'] or '{}').get('t')) for r in f77[:4]])
print('  参数化族行（is_parametric=true，共 %d 条）:'
      % sum(1 for r in rows if r['is_parametric'] == 'true'))
for r in rows:
    if r['is_parametric'] == 'true':
        print('      key=%-8s stcat=%-14s fam=%-3s spec=%s' % (r['key'], stcat(r),
                                                              r['family_code'],
                                                              r['pdms_spec_path']))

print('\n=== 3. §l.6 覆盖范围计数（按族） ===')
cover, skip = [], {}
for r in rows:
    fc, sc = fam(r), stcat(r)
    d = json.loads(r['dims_json'] or '{}')
    if fc == 39 and all(d.get(k) is not None for k in ('H', 'B', 'tf', 'tw')):
        cover.append(('26', r))
    elif fc == 77 and '-' in r['key'] and (r['pkpm_name'] or ''):
        cover.append(('303', r))
    elif sc == '/USER_RECT':
        cover.append(('1', r))
    elif sc == '/USER_CIRCLE' or fc == 3:
        cover.append(('3', r))
    else:
        skip[sc or ('family %d' % fc)] = skip.get(sc or ('family %d' % fc), 0) + 1
from collections import Counter
print('  可反算覆盖 = %d 条：%s' % (len(cover), Counter(k for k, _ in cover)))
print('  不可反算（跳过）= %d 条，按 stcategory 前 20：'
      % sum(skip.values()))
for k, v in sorted(skip.items(), key=lambda x: -x[1])[:20]:
    print('      %-24s %d' % (k, v))

print('\n=== 4. 族 77 的 spec_str 长度/字符检查（打包串容量）===')
bad = []
for r in f77:
    spec = r['key'].split('-', 1)[1] if '-' in r['key'] else r['key']
    if len(spec) > 12 or not spec.isascii():
        bad.append((r['key'], spec, len(spec)))
print('  超过 12 字符或非 ASCII 的 spec_str 行数 =', len(bad))
for b in bad[:10]:
    print('      %s spec=%r len=%d' % b)
