# -*- coding: utf-8 -*-
"""检查 nucroommcreation.pmlfnc 里 object 的用法（验证契约 F.1 的出处说法）。"""
import re

p = r'D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB\Building_Design\pmllib\room_manager\functions\nucroommcreation.pmlfnc'
t = open(p, 'rb').read().decode('gbk', 'replace')
print('总行数', t.count('\n') + 1)
hits = [(i, l) for i, l in enumerate(t.splitlines(), 1) if re.search(r'(?i)\bobject\b', l)]
print('object 命中', len(hits))
for i, l in hits[:12]:
    print('%5d| %s' % (i, l.strip()[:130]))
