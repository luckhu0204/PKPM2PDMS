# -*- coding: utf-8 -*-
"""打印 pdms/ 下 PML 文件的指定行段（GBK 解码），用于人工复核语法。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PDMS = os.path.join(os.path.dirname(HERE), 'pdms')

name = sys.argv[1]
a = int(sys.argv[2])
b = int(sys.argv[3])
text = open(os.path.join(PDMS, name), 'rb').read().decode('gbk')
lines = text.split('\r\n')
print('===== %s  行 %d..%d / 共 %d 行' % (name, a, b, len(lines)))
for i, l in enumerate(lines[a - 1:b], a):
    print('%4d| %s' % (i, l))
