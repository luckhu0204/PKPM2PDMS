# -*- coding: utf-8 -*-
"""侦察 5：CATA vs CATE —— 目录（Catalogue）到底用哪个类型码（只读）。"""
import os
import re

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB'
EXTS = ('.pmlfnc', '.pmlfrm', '.pmlobj', '.mac')
PATS = {
    '|CATA| literal': re.compile(r'(?i)\|\s*CATA\s*\|'),
    "'CATA' string": re.compile(r"(?i)['\"]\s*CATA\s*['\"]"),
    '|CATE| literal': re.compile(r'(?i)\|\s*CATE\s*\|'),
    "'CATE' string": re.compile(r"(?i)['\"]\s*CATE\s*['\"]"),
    'COLLECT ALL CATA': re.compile(r'(?i)\b(collect|coll)\s+(all\s+)?CATA\b'),
    'NEW CATA': re.compile(r'(?i)\bnew\s+CATA\b'),
    'DB Listing 全名 CATALOGUE': re.compile(r'(?i)\bCATALOGUE\b'),
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
                if pat.search(line) and len(HITS[k]) < 12:
                    HITS[k].append('%s:%d: %s' % (rel, i, line.strip()[:140]))
for k in PATS:
    print('=== %s : %d 行' % (k, len(HITS[k])))
    for s in HITS[k]:
        print('    ' + s)
