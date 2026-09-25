# -*- coding: utf-8 -*-
"""临时侦察脚本 25：PML 里"执行宏/命令行"的惯用法（只读）。"""
import os, re, collections

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
PMLLIB = os.path.join(ROOT, 'PMLLIB')

pats = {
    'runMacro': re.compile(r'(?i)\brunmacro\b'),
    'docommand/doCommand': re.compile(r'(?i)\bdocommand\b|\bdocommandline\b'),
    '!!command': re.compile(r'(?i)!!\s*command'),
    'macro()': re.compile(r'(?i)\.\s*macro\s*\('),
    '$M ': re.compile(r"(?i)(\|\s*\$m\s|\'\s*\$m\s|\.\.\.\s*\$m\s)"),
    'pmlmacro': re.compile(r'(?i)\bpmlmacro\b'),
    'EXECUTE': re.compile(r'(?i)\bexecute\s'),
    'AppCntrl command': re.compile(r'(?i)appcntrl\.\s*\w+'),
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
                    if len(samples[name]) < 12:
                        samples[name].append('%s:%d: %s' % (os.path.relpath(p, PMLLIB), i, l.strip()[:160]))

for name in pats:
    print('=== %s : %d hit(s)' % (name, counts[name]))
    for s in samples[name]:
        print('    ' + s)
