# -*- coding: utf-8 -*-
"""临时侦察脚本 6：在框架程序集里找 MacroCommand 的实现键（只读）。"""
import re, os

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
FILES = ['Aveva.ApplicationFramework.dll',
         'Aveva.ApplicationFramework.Implementation.dll',
         'Aveva.ApplicationFramework.Presentation.dll',
         'Aveva.ApplicationFramework.Presentation.Implementation.dll',
         'Aveva.ApplicationFramework.Presentation.Customize.dll']

def strings(b):
    out = {}
    # ASCII
    for m in re.finditer(rb'[\x20-\x7e]{4,}', b):
        out[m.group(0).decode('latin-1')] = 'ascii'
    # UTF-16LE
    for m in re.finditer(rb'(?:[\x20-\x7e]\x00){4,}', b):
        out[m.group(0).decode('utf-16-le')] = 'utf16'
    return out

for f in FILES:
    p = os.path.join(ROOT, f)
    ss = strings(open(p, 'rb').read())
    hits = [s for s in ss if re.search(r'(?i)macro|pml', s)]
    print('=====', f, 'hits=', len(hits))
    for s in sorted(hits):
        print('   [%s] %s' % (ss[s], s[:150]))
