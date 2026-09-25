# -*- coding: utf-8 -*-
"""临时侦察脚本 11：统计 PMLLIB 下 .pmlfrm/.pmlfnc 的目录深度分布（只读）。"""
import os, collections

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
PMLLIB = os.path.join(ROOT, 'PMLLIB')

depth = collections.Counter()
samples = {}
for dirpath, dirnames, filenames in os.walk(PMLLIB):
    rel = os.path.relpath(dirpath, PMLLIB)
    d = 0 if rel == '.' else rel.count(os.sep) + 1
    for fn in filenames:
        if fn.lower().endswith(('.pmlfrm', '.pmlfnc', '.pmlobj')):
            key = (fn.lower().rsplit('.', 1)[1], d)
            depth[key] += 1
            samples.setdefault(key, []).append(os.path.join(rel, fn))

for k in sorted(depth):
    print('%-10s depth=%d  count=%d' % (k[0], k[1], depth[k]))
    for s in samples[k][:4]:
        print('              e.g. %s' % s)
