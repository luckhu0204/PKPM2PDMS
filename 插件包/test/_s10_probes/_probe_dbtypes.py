# -*- coding: utf-8 -*-
"""侦察 2：目录元素类型码字面量 + .pmlfnc 里 alpha file 的实际用法（只读）。"""
import os
import re

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB'
EXTS = ('.pmlfnc', '.pmlfrm', '.pmlobj', '.mac')

WORDS = ['SPRF', 'SPRFILE', 'DTSE', 'DTSET', 'PTSE', 'PTSSET', 'PTSET', 'GMSE', 'GMSSET',
         'GMSET', 'STSE', 'STSECTION', 'STCA', 'STCATEGORY', 'TEXT', 'CATE', 'SPCO',
         'SPCOMPONENT', 'SPEC', 'SPWL', 'SELE', 'PLINE']
FOUND = {w: [] for w in WORDS}
ALPHA = []

for dirpath, dirnames, filenames in os.walk(ROOT):
    for fn in filenames:
        if not fn.lower().endswith(EXTS):
            continue
        p = os.path.join(dirpath, fn)
        try:
            t = open(p, 'rb').read().decode('gbk', 'replace')
        except Exception:
            continue
        rel = os.path.relpath(p, ROOT)
        for w in WORDS:
            pat = re.compile(r'(?i)\|\s*%s\s*\|' % re.escape(w))
            for i, line in enumerate(t.splitlines(), 1):
                if pat.search(line) and len(FOUND[w]) < 3:
                    FOUND[w].append('%s:%d: %s' % (rel, i, line.strip()[:130]))
        if re.search(r'(?i)\balpha\s+file\b', t) and fn.lower().endswith(('.pmlfnc', '.pmlobj')):
            for i, line in enumerate(t.splitlines(), 1):
                if re.search(r'(?i)\balpha\s+file\b', line) or re.search(r'(?i)^\s*output\b', line):
                    ALPHA.append('%s:%d: %s' % (rel, i, line.strip()[:130]))

print('===== |类型码| 字面量样例')
for w in WORDS:
    if FOUND[w]:
        print('--- |%s|' % w)
        for s in FOUND[w]:
            print('     ' + s)

print()
print('===== .pmlfnc / .pmlobj 里的 alpha file / output 用法（全部）')
for s in ALPHA:
    print('   ' + s)
