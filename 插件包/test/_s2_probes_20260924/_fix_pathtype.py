# -*- coding: utf-8 -*-
"""一次性修复：-PathType File → -PathType Leaf（Windows PowerShell 5.1 的枚举名）。"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
INST = os.path.join(os.path.dirname(HERE), 'install')
n = 0
for name in ['install.ps1', 'uninstall.ps1']:
    p = os.path.join(INST, name)
    b = open(p, 'rb').read()
    c = b.count(b'-PathType File')
    if c:
        b = b.replace(b'-PathType File', b'-PathType Leaf')
        open(p, 'wb').write(b)
        n += c
    print('%s : %d 处' % (name, c))
print('合计 %d 处' % n)
