# -*- coding: utf-8 -*-
"""契约导航：列出 CONTRACT.md 的标题行与含指定关键词的行号。"""
import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

P = r'D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\spec\CONTRACT.md'
KEYS = sys.argv[1:] or ['pdt_write', 'db2pdt', 'pdt2db', 'pdt']
t = open(P, encoding='utf-8').read().split('\n')
print('total lines = %d' % len(t))
print('--- headings ---')
for i, l in enumerate(t, 1):
    if re.match(r'^#{1,4} ', l):
        print('%5d %s' % (i, l[:120]))
print('--- keyword hits ---')
for k in KEYS:
    print('### %s' % k)
    for i, l in enumerate(t, 1):
        if k in l:
            print('%5d %s' % (i, l.strip()[:130]))
