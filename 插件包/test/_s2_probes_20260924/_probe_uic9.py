# -*- coding: utf-8 -*-
"""临时侦察脚本 9：打印安装内使用 <Type>Macro</Type> 的真实的 .uic 片段（只读）。"""
import os, re

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
FILES = [os.path.join(ROOT, 'HistoryToolbar.uic'),
         os.path.join(ROOT, 'Tags.uic'),
         os.path.join(ROOT, 'LexiconGUI.uic'),
         os.path.join(ROOT, 'Schematic Model Manager', 'Resources', 'SmmToolsMenu.uic')]

for p in FILES:
    if not os.path.exists(p):
        print('MISSING', p)
        continue
    b = open(p, 'rb').read()
    t = b.decode('utf-8-sig', 'replace')
    print('=====', os.path.relpath(p, ROOT), 'size=%d BOM=%s CRLF=%d' % (len(b), b[:3] == b'\xef\xbb\xbf', b.count(b'\r\n')))
    for m in re.finditer(r'<Command>(.*?)</Command>', t, re.S):
        body = m.group(1)
        if 'Macro' in body:
            print('   <Command>%s</Command>' % body.strip()[:400])
