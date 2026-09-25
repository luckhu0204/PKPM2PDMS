# -*- coding: utf-8 -*-
"""临时侦察脚本 19：确认元素类型码（SITE/ZONE/STRU/FRMW/SBFR/SCTN/PANE/STWALL）的本机用法（只读）。"""
import os, re, collections

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
PMLLIB = os.path.join(ROOT, 'PMLLIB')

pats = {
    'type eq |SITE|': re.compile(r'(?i)type\s+eq\s+\|SITE\|'),
    'type eq |ZONE|': re.compile(r'(?i)type\s+eq\s+\|ZONE\|'),
    'type eq |STRU|': re.compile(r'(?i)type\s+eq\s+\|STRU\w*\|'),
    'type eq |FRMW|': re.compile(r'(?i)type\s+eq\s+\|FRMW\w*\|'),
    'type eq |SBFR|': re.compile(r'(?i)type\s+eq\s+\|SBFR\w*\|'),
    'type eq |SCTN|': re.compile(r'(?i)type\s+eq\s+\|SCTN\|'),
    'type eq |PANE|': re.compile(r'(?i)type\s+eq\s+\|PANE\w*\|'),
    'type eq |STWALL|': re.compile(r'(?i)type\s+eq\s+\|STWALL\|'),
    'COLL ALL SITE': re.compile(r'(?i)coll\s+all\s+SITE\w*\b'),
    'COLL ALL ZONE': re.compile(r'(?i)coll\s+all\s+ZONE\w*\b'),
    'COLL ALL STRU': re.compile(r'(?i)coll\s+all\s+STRU\w*\b'),
    'COLL ALL FRMW': re.compile(r'(?i)coll\s+all\s+FRMW\w*\b'),
    'COLL ALL SBFR': re.compile(r'(?i)coll\s+all\s+SBFR\w*\b'),
    'COLL ALL SCTN': re.compile(r'(?i)coll\s+all\s+SCTN\b'),
    'COLL ALL PANE': re.compile(r'(?i)coll\s+all\s+PANE\w*\b'),
    'COLL ALL STWALL': re.compile(r'(?i)coll\s+all\s+STWALL\b'),
    'CE =': re.compile(r'(?i)!!\s*ce\s*='),
    'type is': re.compile(r'(?i)\.\s*type\b'),
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
                    if len(samples[name]) < 8:
                        samples[name].append('%s:%d: %s' % (os.path.relpath(p, PMLLIB), i, l.strip()[:150]))

for name in pats:
    print('=== %s : %d hit(s)' % (name, counts[name]))
    for s in samples[name]:
        print('    ' + s)
