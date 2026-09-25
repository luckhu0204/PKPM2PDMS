# -*- coding: utf-8 -*-
"""临时侦察脚本 10：谁调用了 mypml 的表单；表单文件的头部写法（只读）。"""
import os, re

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
PMLLIB = os.path.join(ROOT, 'PMLLIB')

targets = ['StlGrating', 'GRIDDESIGN', 'createGrating']
hits = {t: [] for t in targets}
exts = ('.uic', '.mac', '.xml', '.txt', '.pmlfrm', '.pmlfnc', '.pmlobj')
for dirpath, dirnames, filenames in os.walk(PMLLIB):
    for fn in filenames:
        if not fn.lower().endswith(exts):
            continue
        p = os.path.join(dirpath, fn)
        try:
            b = open(p, 'rb').read()
        except Exception:
            continue
        for t in targets:
            if t.encode('ascii') in b:
                hits[t].append(os.path.relpath(p, ROOT))
for t in targets:
    print('=== %s : %d hit(s)' % (t, len(hits[t])))
    for h in hits[t][:25]:
        print('   ', h)
    if len(hits[t]) > 25:
        print('    ... +%d' % (len(hits[t]) - 25))

print()
print('=== StlGrating.pmlfrm head/tail (GBK) ===')
p = os.path.join(PMLLIB, 'mypml', 'forms', 'StlGrating.pmlfrm')
t = open(p, 'rb').read().decode('gbk')
print(t[:1200])
print('   ...TAIL...')
print(t[-400:])
