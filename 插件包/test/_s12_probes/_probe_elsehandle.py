# -*- coding: utf-8 -*-
"""侦察：elsehandle 的形态分布（handle any / elsehandle any 是否有先例）。"""
import os
import re
import collections

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB'
EXTS = ('.pmlfnc', '.pmlfrm', '.pmlobj', '.mac')
cnt = collections.Counter()
samples = {}
for dirpath, dirnames, filenames in os.walk(ROOT):
    for fn in filenames:
        if not fn.lower().endswith(EXTS):
            continue
        p = os.path.join(dirpath, fn)
        try:
            lines = open(p, 'rb').read().decode('gbk', 'replace').splitlines()
        except Exception:
            continue
        rel = os.path.relpath(p, ROOT)
        for i, raw in enumerate(lines, 1):
            l = raw.strip()
            m = re.match(r'(?i)^(elsehandle)\s*(.*)$', l)
            if m:
                key = m.group(2).strip().lower()[:20] or '(none)'
                cnt[key] += 1
                if len(samples.get(key, [])) < 4:
                    samples.setdefault(key, []).append('%s:%d: %s' % (rel, i, l[:110]))
for k, n in cnt.most_common(12):
    print('elsehandle %-12s : %d' % (k, n))
    for s in samples.get(k, []):
        print('     ' + s)
