# -*- coding: utf-8 -*-
"""找 $P 行内带 $!this.<gadget>.val 的既有实例（验证窗体方法里 $P 插值写法）。"""
import os
import re

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB'
hits = []
pat_dollar_this = re.compile(r'\$P\s.*\$!this\.')
pat_p_any = re.compile(r'^\s*\$P\s+\S')
for dp, dn, fns in os.walk(ROOT):
    for fn in fns:
        if not fn.lower().endswith(('.pmlfrm', '.pmlfnc', '.pmlobj')):
            continue
        p = os.path.join(dp, fn)
        try:
            lines = open(p, 'rb').read().decode('gbk', 'replace').splitlines()
        except Exception:
            continue
        for i, l in enumerate(lines, 1):
            if pat_dollar_this.search(l):
                hits.append('%s:%d: %s' % (os.path.relpath(p, ROOT), i, l.strip()[:130]))
print('$P + $!this. 实例：%d 条' % len(hits))
for h in hits[:12]:
    print('  ' + h)
