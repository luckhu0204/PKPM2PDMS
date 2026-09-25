# -*- coding: utf-8 -*-
"""临时侦察脚本 15：找 PML 文件读写与坐标分量取值的本机惯用法（只读）。"""
import os, re, collections

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
PMLLIB = os.path.join(ROOT, 'PMLLIB')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_probe_io_out.txt')

tokens = {
    'object FILE': re.compile(r'(?i)\bobject\s+file\b'),
    '.open(': re.compile(r'(?i)\.\s*open\s*\('),
    'writefile': re.compile(r'(?i)\bwritefile\b'),
    'writeRecord': re.compile(r'(?i)\bwriteRecord\b'),
    '.print(': re.compile(r'(?i)\.\s*print\s*\('),
    'newfile': re.compile(r'(?i)\bnewfile\b'),
    '.east': re.compile(r'(?i)\.\s*east\b'),
    '.north': re.compile(r'(?i)\.\s*north\b'),
    '.up': re.compile(r'(?i)\.\s*up\b'),
    'poss': re.compile(r'(?i)\.\s*poss\b'),
    'define function': re.compile(r'(?i)^\s*define\s+function'),
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
                    if len(samples[name]) < 12:
                        samples[name].append('%s:%d: %s' % (os.path.relpath(p, PMLLIB), i, l.strip()[:170]))

lines = []
for name in tokens:
    lines.append('=== %s : %d hit(s)' % (name, counts[name]))
    lines.extend('    ' + s for s in samples[name])
open(OUT, 'w', encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines))
