# -*- coding: utf-8 -*-
"""临时侦察脚本 17：PANE→PLOOP→PAVERT 的遍历写法 + COMUNITS 定义（只读）。"""
import os, re, collections

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
PMLLIB = os.path.join(ROOT, 'PMLLIB')

pats = {
    '.ploop': re.compile(r'(?i)\.\s*ploop\b'),
    'COLL ALL PAVERT/PLOO': re.compile(r'(?i)coll\s+all\s+(pavert|ploo\w*)\b'),
    'PAVERT type': re.compile(r'(?i)\bpavert\b(?![a-z])'),
    'LOOP attr': re.compile(r'(?i)\.\s*loop\b'),
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
                    if len(samples[name]) < 20:
                        samples[name].append('%s:%d: %s' % (os.path.relpath(p, PMLLIB), i, l.strip()[:170]))

for name in pats:
    print('=== %s : %d hit(s)' % (name, counts[name]))
    for s in samples[name]:
        print('    ' + s)

print()
print('=== comunits.pmlobj 位置 ===')
for dirpath, dirnames, filenames in os.walk(PMLLIB):
    for fn in filenames:
        if fn.lower().startswith('comunit'):
            print('   ', os.path.join(os.path.relpath(dirpath, PMLLIB), fn))
