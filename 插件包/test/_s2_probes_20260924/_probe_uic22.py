# -*- coding: utf-8 -*-
"""临时侦察脚本 22：collectMembersOf 实现 + order.pmlfrm 的 COLL ALL 上下文（只读）。"""
import os

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
PMLLIB = os.path.join(ROOT, 'PMLLIB')

def show(rel, a, z, enc='gbk'):
    p = os.path.join(PMLLIB, rel)
    t = open(p, 'rb').read().decode(enc, 'replace')
    lines = t.splitlines()
    print('===== %s (lines %d..%d of %d)' % (rel, a, min(z, len(lines)), len(lines)))
    for i, l in enumerate(lines[a - 1:z], a):
        print('%4d| %s' % (i, l.rstrip()))

show(os.path.join('common', 'functions', 'collectmembersof.pmlfnc'), 1, 60)
print()
show(os.path.join('common', 'functions', 'findfirstmember.pmlfnc'), 34, 70)
print()
show(os.path.join('mypml', 'forms', 'order.pmlfrm'), 55, 95)
