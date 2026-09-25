# -*- coding: utf-8 -*-
"""验证 object ARRAY() 的本机出处（只读）。"""
import os
import re

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB'
EXTS = ('.pmlfnc', '.pmlfrm', '.pmlobj', '.mac')
HITS = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    for fn in filenames:
        if not fn.lower().endswith(EXTS):
            continue
        p = os.path.join(dirpath, fn)
        try:
            t = open(p, 'rb').read().decode('gbk', 'replace')
        except Exception:
            continue
        for i, l in enumerate(t.splitlines(), 1):
            if re.search(r'(?i)object\s+ARRAY\s*\(\s*\)', l):
                HITS.append((os.path.relpath(p, ROOT), i, l.strip()[:130]))
print('object ARRAY() 命中 %d 行' % len(HITS))
for rel, i, l in HITS[:20]:
    print('   %s:%d: %s' % (rel, i, l))
