# -*- coding: utf-8 -*-
"""实施包② 探针 2：目录宏里 4 个"坏映射族"的实际 SPCOMPONENT 名单（只读）。

用法： python test\\pdt_secmap_probe2.py
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PLUG = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'
SECMAP = PLUG + '\\PKPM转PDMS截面匹配文件.txt'
CAT = PLUG + '\\PKPM（PDMS数据库）.txt'

OWNERS = ('/DOUBLE_L_EQUAL_CROSS-SPEC/', '/DOUBLE_L_UNEQUAL_LONG-SPEC/',
          '/DOUBLE_L_UNEQUAL_SHORT-SPEC/', '/DOUBLE_THIN_L_COIL_EQUAL-SPEC/')


def leaf(p):
    return p.rsplit('/', 1)[1]


def head(leafstr):
    """leaf 的字母前缀（第一个数字之前的部分）。"""
    i = 0
    while i < len(leafstr) and not leafstr[i].isdigit():
        i += 1
    return leafstr[:i]


comp = []
for ln in open(CAT, 'rb').read().decode('utf-8-sig').splitlines():
    s = ln.strip()
    if s.startswith('NEW SPCOMPONENT '):
        comp.append(s[len('NEW SPCOMPONENT '):].split()[0])

for o in OWNERS:
    mine = [c for c in comp if c.startswith(o)]
    print('%s -> %d macros' % (o, len(mine)))
    print('   first 3: %s' % [leaf(m) for m in mine[:3]])
    print('   last 3 : %s' % [leaf(m) for m in mine[-3:]])
    print('   letter prefixes: %s' % sorted({head(leaf(m)) for m in mine}))

sec = open(SECMAP, 'rb').read().decode('gbk')
pairs = []
for i, ln in enumerate(sec.split('\r\n'), 1):
    s = ln.strip()
    if not s or s.startswith('//') or ',' not in s:
        continue
    l, r = s.split(',', 1)
    l = l.strip()
    r = ' '.join(r.split())
    if not r.startswith('/'):
        r = '/' + r
    pairs.append((i, l, r))
for o in OWNERS:
    mine = [(i, l, r) for i, l, r in pairs if r.startswith(o)]
    print('%s -> %d secmap rows; first3=%s last3=%s'
          % (o, len(mine), [leaf(r) for _, _, r in mine[:3]],
             [leaf(r) for _, _, r in mine[-3:]]))
    print('   secmap letter prefixes: %s' % sorted({head(leaf(r)) for _, _, r in mine}))
print('DONE')
