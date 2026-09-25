# -*- coding: utf-8 -*-
"""实施包② 探针 4：样本真正需要的键是否已在原件里（决定 secmap_extra.txt 内容）。

用法： python test\\pdt_secmap_probe4.py
"""
import io
import sqlite3
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PLUG = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'
SECMAP = PLUG + '\\PKPM转PDMS截面匹配文件.txt'
CAT = PLUG + '\\PKPM（PDMS数据库）.txt'

keys = {}
for i, ln in enumerate(open(SECMAP, 'rb').read().decode('gbk').split('\r\n'), 1):
    s = ln.strip()
    if not s or s.startswith('//') or ',' not in s:
        continue
    l, r = s.split(',', 1)
    l = l.strip()
    r = ' '.join(r.split())
    if not r.startswith('/'):
        r = '/' + r
    keys[l] = (i, r)

CHECK = ['6-B250*10.00', '6-B200*10.00', '1-D194X8.0', '3#20', 'T120', 'T100',
         'T600', '矩750X750', '矩300X600', 'HN400X200', 'HW200X200', '圆形4800',
         '薄壁方钢管: B25', '薄壁方钢管: B20', '热轧无缝圆钢管', 'B250*10.00',
         '3-B250X10.0', 'RECT', 'H', 'ANGEL', 'CIRCLE']
for k in CHECK:
    print('%-20s -> %s' % (k, keys.get(k, '** NOT IN FILE **')))

# what the pdt sample itself references
PDT = PLUG + '\\1_PM.pdt'
t = open(PDT, 'rb').read().decode('gbk')
import re
names = sorted(set(re.findall(r'NAME=([^,\r\n]*)', t)))
print('\n$DEFFRAMESECTION / $DEFWASLABSECTION NAME values:')
for n in names:
    print('   %-20r -> %s' % (n, keys.get(n.strip(), '** NOT IN FILE **')))

# catalogue macro leaf existence for candidate extra entries
comp = set()
for ln in open(CAT, 'rb').read().decode('utf-8-sig').splitlines():
    s = ln.strip()
    if s.startswith('NEW SPCOMPONENT '):
        comp.add(s[len('NEW SPCOMPONENT '):].split()[0])
owners = {c.lstrip('/').split('/')[0] for c in comp}
print('\nmacro owners=%d' % len(owners))
for p in ['/USER_RECT-SPEC/Rectangle_Profile', '/USER_H-SPEC/H_Profile',
          '/USER_CIRCLE-SPEC/Circle_Profile', '/TUBE_TUBE-SPEC/D20X2.0',
          '/Concrete_Wall-SPEC/WALL-300', '/Concrete_Slab-SPEC/T120',
          '/H_INTERNATIONAL-SPEC/HN400X200', '/RECT_SQUARE50018-SPEC/B250*10.0',
          '/RECT_SQUARE6728_2002-SPEC/B250*10.00', '/TUBE_TUBE-SPEC/D194X8.0']:
    print('   %-42s comp=%s owner=%s' % (
        p, p in comp, p.lstrip('/').split('/')[0] in owners))
print('DONE')
