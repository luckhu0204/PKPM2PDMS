# -*- coding: utf-8 -*-
"""临时侦察脚本 27：窗体收尾/para 写法/字符串方法/alert 的本机用法（只读）。"""
import os, re, collections

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
PMLLIB = os.path.join(ROOT, 'PMLLIB')

pats = {
    '.kill()': re.compile(r'(?i)\.\s*kill\s*\(\s*\)'),
    'para inline': re.compile(r'(?i)^\s*para\s+\.\w+\s+[\'\|]'),
    'para text': re.compile(r'(?i)^\s*para\s+\.\w+\s+.*\btext\b'),
    '.before(': re.compile(r'(?i)\.\s*before\s*\('),
    '.lowcase(': re.compile(r'(?i)\.\s*lowcase\s*\('),
    'alert.message': re.compile(r'(?i)!!\s*alert\s*\.\s*message'),
    'chr(': re.compile(r'(?i)\bchr\s*\('),
    '$m ': re.compile(r'(?i)\$m\s+"'),
    'formtitle': re.compile(r'(?i)\.\s*formtitle'),
    '$P ': re.compile(r'(?i)^\s*\$P\s+\S'),
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
