# -*- coding: utf-8 -*-
"""临时侦察脚本 18：打印 scale-STRU.mac（PLOOP/PAVERT 遍历范例）与 COMUNITS 相关实现（只读）。"""
import os

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
PMLLIB = os.path.join(ROOT, 'PMLLIB')

def show(rel, a=0, z=None, enc='gbk'):
    p = os.path.join(PMLLIB, rel)
    t = open(p, 'rb').read().decode(enc, 'replace')
    lines = t.splitlines()
    z = z if z is not None else len(lines)
    print('===== %s  (lines %d..%d of %d)' % (rel, a + 1, min(z, len(lines)), len(lines)))
    for i, l in enumerate(lines[a:z], a + 1):
        print('%4d| %s' % (i, l))

show(os.path.join('mypml', 'forms', 'scale-STRU.mac'), 80, 160)
print()
show(os.path.join('common', 'functions', 'comunitsconvert.pmlfnc'))
print()
show(os.path.join('common', 'objects', 'comunits.pmlobj'), 0, 90)
