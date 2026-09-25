# -*- coding: utf-8 -*-
"""临时侦察脚本 13：找本机 PMLLIB 里"遍历结构树"的 PML 惯用法（只读）。"""
import os, re

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
PMLLIB = os.path.join(ROOT, 'PMLLIB')

pat_file = re.compile(r'(?i)SBFRAMEWORK|FRMWORK')
pat_line = re.compile(r'(?i)^\s*(do\s+\S+\s+values|collect\s+all|first\s+\w+|!?\S+\s*=\s*next|next\b)')
pat_line2 = re.compile(r'(?i)(do\s+\S+\s+values|MEMB|CHILD|OWNER)')

found = []
for dirpath, dirnames, filenames in os.walk(PMLLIB):
    for fn in filenames:
        if not fn.lower().endswith(('.pmlfnc', '.pmlfrm', '.pmlobj', '.mac')):
            continue
        p = os.path.join(dirpath, fn)
        try:
            t = open(p, 'rb').read().decode('gbk', 'replace')
        except Exception:
            continue
        lines = t.splitlines()
        hits = [(i, l) for i, l in enumerate(lines, 1) if re.search(r'(?i)SBFRAMEWORK|FRMWORK', l)]
        if len(hits) >= 2 and len(hits) < 40:
            found.append((os.path.relpath(p, PMLLIB), len(hits), hits))

found.sort(key=lambda x: x[1])
print('files mentioning FRMWORK/SBFRAMEWORK: %d' % len(found))
for rel, n, hits in found[:12]:
    print('===== %s  (%d lines)' % (rel, n))
    for i, l in hits[:8]:
        print('   %d: %s' % (i, l.strip()[:150]))
