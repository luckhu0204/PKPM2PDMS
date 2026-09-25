# -*- coding: utf-8 -*-
"""临时侦察脚本 3：在 ApplicationFramework 程序集里找 Command 的 Type 枚举取值（只读）。"""
import re, os

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
FILES = ['Aveva.ApplicationFramework.Presentation.dll',
         'Aveva.ApplicationFramework.Presentation.Implementation.dll',
         'Aveva.ApplicationFramework.Presentation.Customize.dll',
         'Aveva.ApplicationFramework.dll']

def strings(b):
    out = set()
    for enc in ('ascii', 'utf-16-le'):
        for m in re.finditer(rb'(?:[\x20-\x7e]\x00){4,}|[\x20-\x7e]{4,}', b):
            try:
                s = m.group(0).decode(enc if enc == 'ascii' else 'utf-16-le')
            except Exception:
                continue
            out.add(s)
    return out

for f in FILES:
    p = os.path.join(ROOT, f)
    if not os.path.exists(p):
        print('MISSING', f)
        continue
    ss = strings(open(p, 'rb').read())
    print('=====', f)
    for s in sorted(ss):
        if re.search(r'(?i)\b(PML|CommandType|Instance|Class)\b', s) and len(s) < 80:
            print('   ', s)
