# -*- coding: utf-8 -*-
"""侦察 6：DATAL 里的 TEXT / DATA 对应哪些 PML 类型码（只读）。"""
import os
import re

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB'
FILES = ['paragon\\objects\\catdtseelement.pmlobj',
         'paragon\\objects\\catgetelement.pmlobj',
         'paragon\\objects\\catrefdata.pmlobj',
         'paragon\\objects\\catptseelement.pmlobj',
         'paragon\\objects\\catgmseelement.pmlobj',
         'paragon\\objects\\cgeocataupgrade.pmlobj',
         'common\\forms\\memberslist.pmlfrm',
         'common\\functions\\memberslist.pmlfnc',
         'common\\functions\\dbodtyplist.pmlfnc']
PAT = re.compile(r"(?i)(\|\s*(DATA|TEXT|TXTE|DTDA)\s*\||'\s*(DATA|TEXT|TXTE|DTDA)\s*'|"
                 r"elementTypes\[|longTypes\[|categoryTypes\[|typeTypes\[)")

for rel in FILES:
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        print('MISSING ' + rel)
        continue
    t = open(p, 'rb').read().decode('gbk', 'replace')
    hits = [(i, l) for i, l in enumerate(t.splitlines(), 1) if PAT.search(l)]
    if not hits:
        continue
    print('===== %s（%d 行命中）' % (rel, len(hits)))
    for i, l in hits[:30]:
        print('%5d| %s' % (i, l.strip()[:140]))
