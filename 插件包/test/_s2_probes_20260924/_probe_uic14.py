# -*- coding: utf-8 -*-
"""临时侦察脚本 14：统计 PML 里元素导航惯用法（members / children / first-next 等）。"""
import os, re, collections

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
PMLLIB = os.path.join(ROOT, 'PMLLIB')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_probe_nav_out.txt')

tokens = {
    'members': re.compile(r'(?i)\.\s*members\b'),
    'MEM of': re.compile(r'(?i)\bmem\s+of\b'),
    'children': re.compile(r'(?i)\.\s*children\b'),
    'values $!': re.compile(r'(?i)\bdo\s+\S+\s+values\s'),
    'first ': re.compile(r'(?i)\bfirst\s+[A-Z]'),
    '= next': re.compile(r'(?i)=\s*next\b'),
    'nextb': re.compile(r'(?i)\bnextb\b'),
    'dbref': re.compile(r'(?i)\bdbref\b'),
    'collall': re.compile(r'(?i)\bcoll\s+all\b'),
    'for ... in': re.compile(r'(?i)\bfor\b.*\bin\b'),
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
                    if len(samples[name]) < 10:
                        samples[name].append('%s:%d: %s' % (os.path.relpath(p, PMLLIB), i, l.strip()[:160]))

lines = []
for name in tokens:
    lines.append('=== %s : %d hit(s)' % (name, counts[name]))
    lines.extend('    ' + s for s in samples[name])
open(OUT, 'w', encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines))
