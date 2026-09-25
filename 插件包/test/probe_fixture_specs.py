# -*- coding: utf-8 -*-
"""查证夹具要用的 SPREF 是否真的在截面匹配文件里（只读原件）。"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PATH = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\PKPM转PDMS截面匹配文件.txt'
WANT = ['/H_INTERNATIONAL-SPEC/HN450X200', '/H_INTERNATIONAL-SPEC/HN300X150',
        '/H_INTERNATIONAL-SPEC/HN400X200', '/USER_RECT-SPEC/Rectangle_Profile',
        '/USER_H-SPEC/H_Profile', '/C_COMMON-SPEC/[18a', '/C_LIGHT-SPEC/CL18a',
        '/RECT_SQUARE6728_2002-SPEC/B250*10.00', '/Concrete_Wall-SPEC/WALL-300',
        '/TUBE_TUBE-SPEC/D194X8.0']

txt = io.open(PATH, 'rb').read().decode('gbk')
fwd = {}
for ln in txt.split('\r\n'):
    s = ln.strip()
    if not s or s.startswith('//') or (',' not in s):
        continue
    l, r = s.split(',', 1)
    r = ' '.join(r.split())
    if not r.startswith('/'):
        r = '/' + r
    fwd.setdefault(r, []).append(l.strip())

for w in WANT:
    print('%-42s -> %r' % (w, fwd.get(w)))
print()
print('反查（右值 -> 左值）首条：')
for w in WANT:
    v = fwd.get(w)
    print('  %-42s => %s' % (w, v[0] if v else None))
