# -*- coding: utf-8 -*-
"""临时侦察脚本 16：unset / pavert / ploop / catref / units 的本机 PML 用法（只读）。"""
import os, re, collections

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
PMLLIB = os.path.join(ROOT, 'PMLLIB')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_probe_io2_out.txt')

tokens = {
    'unset()': re.compile(r'(?i)\.\s*unset\s*\(\s*\)'),
    'pavert': re.compile(r'(?i)\bpavert'),
    'ploop': re.compile(r'(?i)\bploop'),
    'catref': re.compile(r'(?i)catref|cat\s*ref'),
    'units': re.compile(r'(?i)\bunits\b'),
    'heig': re.compile(r'(?i)\.heig\b'),
    'speq/spre': re.compile(r'(?i)\.\s*(spre|spref)\b'),
    'to text': re.compile(r'(?i)\.string\s*\(\s*\)'),
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
            for name, pat in tokens.items():
                if pat.search(l):
                    counts[name] += 1
                    if len(samples[name]) < 14:
                        samples[name].append('%s:%d: %s' % (os.path.relpath(p, PMLLIB), i, l.strip()[:165]))

lines = []
for name in tokens:
    lines.append('=== %s : %d hit(s)' % (name, counts[name]))
    lines.extend('    ' + s for s in samples[name])
open(OUT, 'w', encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines))
