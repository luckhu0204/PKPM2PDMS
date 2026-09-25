# -*- coding: utf-8 -*-
"""临时侦察脚本 20：PAVERT/顶点位置、|SBFR|/|FRMW| 类型码、墙集合写法（只读）。"""
import os, re, collections

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
PMLLIB = os.path.join(ROOT, 'PMLLIB')

pats = {
    '.pos.east/north/up': re.compile(r'(?i)\.\s*pos\s*\.\s*(east|north|up)\b'),
    '.pave': re.compile(r'(?i)\.\s*pave'),
    'pavert var/iter': re.compile(r'(?i)(pavert|pave)\b.*\b(east|north|up|pos)\b'),
    '|SBFR|': re.compile(r'(?i)\|SBFR\w*\|'),
    '|FRMW|': re.compile(r'(?i)\|FRMW\w*\|'),
    '|ZONE|': re.compile(r'(?i)\|ZONE\w*\|'),
    '|PLOO|': re.compile(r'(?i)\|PLOO\w*\|'),
    'coll all wall': re.compile(r'(?i)coll\s+all\s*(st?wall|wall)\w*'),
    'STWALL substr': re.compile(r'(?i)\bstwall\b'),
    'vertex pos': re.compile(r'(?i)\bvrt[xv]\.\s*pos'),
    'element.members': re.compile(r'(?i)\.\s*members\s*(\[|$|\s)'),
}

counts = collections.Counter()
samples = collections.defaultdict(list)
for dirpath, dirnames, filenames in os.walk(PMLLIB):
    for fn in filenames:
        if not fn.lower().endswith(('.pmlfnc', '.pmlfrm', '.pmlobj', '.mac')):
            continue
        p = os.path.join(dirpath, fn)
        try:
            t = open(p, 'rb').read().decode('gbk', 'replace')
        except Exception:
            continue
        for i, l in enumerate(t.splitlines(), 1):
            for name, pat in pats.items():
                if pat.search(l):
                    counts[name] += 1
                    if len(samples[name]) < 10:
                        samples[name].append('%s:%d: %s' % (os.path.relpath(p, PMLLIB), i, l.strip()[:150]))

for name in pats:
    print('=== %s : %d hit(s)' % (name, counts[name]))
    for s in samples[name]:
        print('    ' + s)
