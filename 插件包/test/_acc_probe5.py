# -*- coding: utf-8 -*-
"""临时探针 5：检查产出宏的结构。"""
import io
import re
import sys
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
p = r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\test\_acc_tmp\JLCJ2.mac"
raw = open(p, 'rb').read()
print('bytes', len(raw), 'bom?', raw[:3] == b'\xef\xbb\xbf')
t = raw.decode('gbk')
lines = t.split('\r\n')
print('split-crlf parts', len(lines), 'lone LF?', b'\n' in raw.replace(b'\r\n', b''))
c = Counter()
for l in lines:
    s = l.strip()
    if s.startswith('NEW SCTN'):
        c['NEW SCTN'] += 1
    if s.startswith('NEW PANE'):
        c['NEW PANE'] += 1
    if s.startswith('NEW STWALL'):
        c['NEW STWALL'] += 1
    if s.startswith('SPREF'):
        c['SPREF'] += 1
    if s.startswith('SPRE '):
        c['SPRE'] += 1
    if s.startswith('DESP'):
        c['DESP'] += 1
    if 'UNRESOLVED SECTION' in s:
        c['marker'] += 1
    if s.startswith('NEW SBFR'):
        c['SBFR' + s.split()[-1]] += 1
print(c)
# per-SCTN block analysis
blocks = []
cur = None
for l in lines:
    s = l.strip()
    if s.startswith('NEW SCTN') or s.startswith('NEW PANE') or s.startswith('NEW STWALL'):
        cur = {'head': s, 'spec': False, 'desp': False, 'marker': False}
        blocks.append(cur)
    if cur is None:
        continue
    if s.startswith('SPREF') or s.startswith('SPRE '):
        cur['spec'] = True
    if s.startswith('DESP'):
        cur['desp'] = True
    if 'UNRESOLVED SECTION' in s:
        cur['marker'] = True
print('blocks', len(blocks))
n_nospec = [b for b in blocks if not b['spec'] and not b['desp']]
print('blocks without SPREF/DESP:', len(n_nospec))
n_nomarker = [b for b in n_nospec if not b['marker']]
print('  of which without UNRESOLVED marker:', len(n_nomarker))
from collections import Counter as C2
kinds = C2()
for b in n_nospec:
    kinds[b['head'].split()[1][:8]] += 1
print('  sample heads:', [b['head'] for b in n_nospec[:3]])
i = [n for n, l in enumerate(lines) if l.strip().startswith('-- UNRESOLVED SECTION')][:2]
for n in i:
    print('---')
    for l in lines[n - 3:n + 5]:
        print(repr(l))
