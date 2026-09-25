# -*- coding: utf-8 -*-
"""临时侦察脚本 12：查看 PMLLIB\pml.index 的格式（只读，不修改）。"""
import os, re

P = r'D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB\pml.index'
b = open(P, 'rb').read()
print('size=%d  NUL=%d  CRLF=%d  LF=%d' % (len(b), b.count(b'\x00'), b.count(b'\r\n'), b.count(b'\n')))
t = b.decode('gbk', 'replace')
lines = t.splitlines()
print('lines=%d' % len(lines))
print('--- first 15 lines ---')
for l in lines[:15]:
    print(repr(l[:200]))
print('--- lines containing aidshow / spiralstair / yhadmexpunge ---')
for kw in ['aidshow', 'spiralstair', 'yhadmexpunge', 'sdnfinver3']:
    hit = [l for l in lines if kw.lower() in l.lower()]
    print('  %-15s %d hit(s): %s' % (kw, len(hit), hit[:2]))
