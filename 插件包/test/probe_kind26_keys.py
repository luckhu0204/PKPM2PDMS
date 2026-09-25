# -*- coding: utf-8 -*-
"""只读：Kind=26 型钢库截面的候选键命中情况（供 CONTRACT §e 定死候选键顺序）。"""
import io
import os
import sqlite3
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
P = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'

txt = open(os.path.join(P, 'PKPM转PDMS截面匹配文件.txt'), 'rb').read().decode('gbk')
keys = {}
for ln in txt.split('\r\n'):
    s = ln.strip()
    if not s or s.startswith('//') or ',' not in s:
        continue
    l, r = s.split(',', 1)
    r = ' '.join(r.split())
    keys[l.strip()] = r if r.startswith('/') else '/' + r

con = sqlite3.connect('file:' + os.path.join(P, 'JLCJ2.jwd').replace('\\', '/') + '?mode=ro',
                      uri=True)
con.text_factory = lambda b: b.decode('gbk', 'replace') if isinstance(b, bytes) else b

for t in ('pkpmBeamSect', 'pkpmColSect', 'pkpmBraceSect'):
    for sid, no, name, mat, kind, sv in con.execute(
            'SELECT ID,No_,Name,Mat,Kind,ShapeVal FROM %s' % t):
        if kind != 26:
            continue
        p = [x for x in sv.split(',') if x != ''][1:-2]
        fam, sub = p[0], p[1]
        cands = [name, '%s-%s' % (sub, name)]
        hit = [(c, keys[c]) for c in cands if c in keys]
        print('%-14s fam=%-3s sub=%-3s H=%-5s B=%-5s cands=%s hit=%s'
              % (repr(name), fam, sub, p[2], p[4], cands, hit))
con.close()
