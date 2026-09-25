# -*- coding: utf-8 -*-
"""临时侦察脚本 24：order.txt 是谁写的、用什么调用写的（只读）。"""
import os, re

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
PMLLIB = os.path.join(ROOT, 'PMLLIB')

pat = re.compile(r'(?i)writefile|writerecord|object\s+file|\.open\s*\(|order\.txt')
for rel in [os.path.join('mypml', 'forms', 'order.pmlfrm'),
            os.path.join('mypml', 'forms', 'pipeorder.pmlfrm')]:
    p = os.path.join(PMLLIB, rel)
    if not os.path.exists(p):
        print('MISSING', rel)
        continue
    t = open(p, 'rb').read().decode('gbk', 'replace')
    print('===== %s' % rel)
    for i, l in enumerate(t.splitlines(), 1):
        if pat.search(l):
            print('%4d| %s' % (i, l.strip()[:170]))

print()
print('=== order.txt 前 6 行（字节级）===')
p = os.path.join(PMLLIB, 'mypml', 'forms', 'order.txt')
b = open(p, 'rb').read()
print(repr(b[:400]))

print()
print('=== common/functions/ascii.pmlfnc ===')
p = os.path.join(PMLLIB, 'common', 'functions', 'ascii.pmlfnc')
print(open(p, 'rb').read().decode('gbk', 'replace')[:2200])
