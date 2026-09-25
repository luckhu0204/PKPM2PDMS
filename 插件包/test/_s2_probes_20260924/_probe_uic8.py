# -*- coding: utf-8 -*-
"""临时侦察脚本 8：定位 PML310 / MacroCommand 字面量在框架程序集里的上下文（只读）。"""
import re, os

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
FILES = ['Aveva.ApplicationFramework.Presentation.Implementation.dll',
         'Aveva.ApplicationFramework.Presentation.Customize.dll']

def ctx(b, needle):
    out = []
    for m in re.finditer(re.escape(needle), b):
        a = max(0, m.start() - 200)
        z = min(len(b), m.end() + 200)
        seg = b[a:z]
        # 抽取该段内可见串
        ss = [s.decode('latin-1') for s in re.findall(rb'[\x20-\x7e]{3,}', seg)]
        ss += [s.decode('utf-16-le') for s in re.findall(rb'(?:[\x20-\x7e]\x00){3,}', seg)]
        out.append((m.start(), ss))
    return out

for f in FILES:
    b = open(os.path.join(ROOT, f), 'rb').read()
    print('=====', f)
    for needle in [b'PML310', b'MacroCommand', b'Instance', b'Class']:
        hits = ctx(b, needle)
        print('  -- needle=%s hits=%d' % (needle.decode(), len(hits)))
        for off, ss in hits[:6]:
            print('     off=0x%X  %s' % (off, ' | '.join(ss)[:600]))
