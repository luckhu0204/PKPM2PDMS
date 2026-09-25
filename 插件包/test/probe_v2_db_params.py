# -*- coding: utf-8 -*-
"""实施包⑨ 侦察 2：参数化族行（RECT/CIRCLE/H/…）在表里的形状 + 目录宏里对应 DTSET 的 DPRO。

只读。运行：python test/probe_v2_db_params.py
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

with io.open(CSV, encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
by_key = {r['key']: r for r in rows}

print('=== 1. USER_* / 参数化族行 ===')
for k in ('RECT', 'CIRCLE', 'H', 'XI', 'TUBE', 'PIPE', 'C', 'T', 'Z', 'CROSS', 'I'):
    r = by_key.get(k)
    if not r:
        print('  %-8s 不在表里' % k)
        continue
    print('  %-8s key=%-8s pkpm=%-8s fam=%-3s kind=%-3s mat=%s spec=%s'
          % (k, r['key'], r['pkpm_name'], r['family_code'], r['kind'], r['mat'],
             r['pdms_spec_path']))
    print('           shapeval=%r is_parametric=%s dims=%s'
          % (r['shapeval'], r['is_parametric'], r['dims_json'][:100]))
    print('           params=%s' % (r['params_json'][:200],))
    ex = json.loads(r['extra_json'] or '{}')
    print('           extra.pdms_stcategory=%s param_count=%s stcategory_param_count=%s'
          % (ex.get('pdms_stcategory'), ex.get('param_count'),
             ex.get('stcategory_param_count')))

print('\n=== 2. 目录宏：/USER_RECT、/USER_CIRCLE、/USER_H 的 DTSET 块（逐行） ===')
raw = open(MACRO, 'rb').read().decode('utf-8-sig')
lines = raw.split('\r\n')
for name in ('/USER_RECT', '/USER_CIRCLE', '/USER_H'):
    idx = [i for i, l in enumerate(lines)
           if re.match(r'NEW\s+STCATEGORY\s+%s\s*$' % re.escape(name), l.strip())]
    print('  --- NEW STCATEGORY %s 行号=%s' % (name, [i + 1 for i in idx]))
    if not idx:
        continue
    i = idx[0]
    j = i
    depth = 0
    out = []
    while j < len(lines) and j < i + 200:
        s = lines[j].strip()
        out.append('   %6d| %s' % (j + 1, lines[j]))
        if s.startswith('NEW '):
            depth += 1
        elif s == 'END':
            depth -= 1
            if depth <= 0 and j > i:
                break
        j += 1
    for l in out:
        print(l)

print('\n=== 3. 目录宏：PARA 与表 dims 的交叉核对（抽 5 个族码 39 的截面） ===')
# 每个 SPRFILE 的 GTYP + PARA
cur = None
spara = {}
for i, l in enumerate(lines):
    s = l.strip()
    m = re.match(r'NEW SPRFILE (\S+)', s)
    if m:
        cur = m.group(1)
        spara[cur] = {'line': i + 1, 'gtyp': '', 'para': []}
        continue
    if cur is None:
        continue
    if s.startswith('GTYP '):
        spara[cur]['gtyp'] = s.split(None, 1)[1]
    elif s.startswith('PARA '):
        spara[cur]['para'].extend(s.split()[1:])
    elif s == 'END' or s.startswith('NEW '):
        if s.startswith('NEW '):
            cur = None
print('  解析出 SPRFILE 数 =', len(spara))
for key in ('/HN450X200', '/HN300X150', '/HW200X200', '/B250*10.00', '/D194X8.0'):
    sp = spara.get(key)
    if not sp:
        cands = [k for k in spara if k.strip('/') == key.strip('/')]
        sp = spara.get(cands[0]) if cands else None
        print('  %-14s 直接名未命中，候选=%s' % (key, cands[:3]))
    if not sp:
        print('  %-14s 不在宏里' % key)
        continue
    nums = [x for x in sp['para'] if x != '$']
    print('  %-14s L%-6d gtyp=%-5s PARA=%s' % (key, sp['line'], sp['gtyp'], ' '.join(nums)))
    prow = by_key.get(key.strip('/'))
    if prow:
        print('                表 dims=%s' % (prow['dims_json'][:110],))
