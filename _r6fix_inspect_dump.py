# -*- coding: utf-8 -*-
"""R6 修复员临时脚本：检查实机 dump 的记录构成与 #SCTN token 布局（只读）。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from collections import Counter

raw = open(r'D:\AI_Work\PKPM数据解析\PKPM2PDMS_v2.1.0\验收\R6导出\export_test.dump.txt', 'rb').read()
print('size', len(raw))
text = raw.decode('utf-8-sig')
lines = text.splitlines()
print('total lines', len(lines))
c = Counter(l.split()[0] for l in lines if l.strip())
print(dict(c))
cc = Counter(len(l.split()) for l in lines if l.startswith('#SCTN'))
print('sctn tokencounts', dict(cc))
for l in lines:
    if l.startswith('#SCTN') and ' BEAM ' in l:
        print('BEAM:', repr(l)); break
for l in lines:
    if l.startswith('#SCTN') and ' HBRACE ' in l:
        print('HBRACE:', repr(l)); break
print('tail3:')
for x in lines[-3:]:
    print(repr(x))
