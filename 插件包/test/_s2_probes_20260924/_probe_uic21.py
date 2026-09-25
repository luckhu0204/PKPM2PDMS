# -*- coding: utf-8 -*-
"""临时侦察脚本 21：查 collectMembersOf / findFirstMember / kCollectAllFor 的定义与签名（只读）。"""
import os, re

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
PMLLIB = os.path.join(ROOT, 'PMLLIB')

want = ['collectmembersof', 'findfirstmember', 'kcollectallfor', 'kcollectall', 'isimperiallength']
found = {}
for dirpath, dirnames, filenames in os.walk(PMLLIB):
    for fn in filenames:
        n = fn.lower()
        for w in want:
            if n.startswith(w) and n.endswith(('.pmlfnc', '.pmlobj')):
                found.setdefault(w, []).append(os.path.join(dirpath, fn))

for w in want:
    print('=== %s -> %s' % (w, [os.path.relpath(p, PMLLIB) for p in found.get(w, [])]))

print()
for w, paths in found.items():
    for p in paths[:1]:
        t = open(p, 'rb').read().decode('gbk', 'replace')
        lines = t.splitlines()
        print('===== %s' % os.path.relpath(p, PMLLIB))
        for i, l in enumerate(lines[:60], 1):
            if re.search(r'(?i)define\s+(function|method)|^\s*--\s*(Arguments|Return|Description)|^\s*--\s+\d\s', l):
                print('%4d| %s' % (i, l.rstrip()[:160]))
