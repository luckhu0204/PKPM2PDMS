# -*- coding: utf-8 -*-
"""侦察 4：函数里取"当前日期时间文本"的可用写法（CLOCK / DATE / 时间函数）。"""
import os
import re

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB'
EXTS = ('.pmlfnc', '.pmlfrm', '.pmlobj', '.mac')
PATS = {
    'object CLOCK': re.compile(r'(?i)\bobject\s+CLOCK\b'),
    'object DATE': re.compile(r'(?i)\bobject\s+DATE\b'),
    'var ... CLOCK': re.compile(r'(?i)\bvar\s+\S+\s+CLOCK\b'),
    '!!clock': re.compile(r'(?i)!!\s*clock\b'),
    'clock()': re.compile(r'(?i)\.\s*clock\s*\(|clock\s*\(\s*\)'),
    'timeText/dateText': re.compile(r'(?i)\b(datetime|dateNow|now\(\))'),
    'DATE methods': re.compile(r'(?i)\.\s*(monthstring|year|hour|second|minute|date|time)\s*\(\)'),
}
HITS = {k: [] for k in PATS}
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
        for i, line in enumerate(t.splitlines(), 1):
            for k, pat in PATS.items():
                if pat.search(line) and len(HITS[k]) < 10:
                    HITS[k].append('%s:%d: %s' % (rel, i, line.strip()[:130]))
for k in PATS:
    print('=== %s : %d 行' % (k, len(HITS[k])))
    for s in HITS[k]:
        print('    ' + s)

print()
print('=== admin/functions/adminobjects.pmlfnc 25-45')
p = os.path.join(ROOT, 'admin', 'functions', 'adminobjects.pmlfnc')
for i, l in enumerate(open(p, 'rb').read().decode('gbk', 'replace').splitlines(), 1):
    if 25 <= i <= 45:
        print('%4d| %s' % (i, l))
