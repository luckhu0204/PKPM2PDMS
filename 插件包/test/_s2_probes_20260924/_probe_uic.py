# -*- coding: utf-8 -*-
"""临时侦察脚本：打印 PDMS 安装内 .uic / Addins.xml 的真实字节与结构（只读）。"""
import os, sys

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'

def dump(name, n=1600):
    p = os.path.join(ROOT, name)
    if not os.path.exists(p):
        print('--- MISSING', name)
        return
    b = open(p, 'rb').read()
    print('===== %s size=%d BOM=%s CRLF=%d LF=%d' % (
        name, len(b), b[:3] == b'\xef\xbb\xbf', b.count(b'\r\n'), b.count(b'\n') - b.count(b'\r\n')))
    try:
        t = b.decode('utf-8-sig')
    except Exception as e:
        t = b.decode('gbk', 'replace')
        print('   (utf-8 decode failed: %s)' % e)
    print(t[:n])
    print('   ...total lines=%d' % (t.count('\n') + 1))

for f in ['design.uic', 'tgtext.uic', 'tgspec.uic', 'pdcopilot.uic', 'DesignAddins.xml']:
    dump(f)
