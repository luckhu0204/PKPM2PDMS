# -*- coding: utf-8 -*-
"""打印产物 .pdt 的指定行区间（调试用）。"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
p = sys.argv[1]
a, b = int(sys.argv[2]), int(sys.argv[3])
L = open(p, 'rb').read().decode('gbk').replace('\r\n', '\n').split('\n')
for i in range(max(0, a - 1), min(len(L), b)):
    print('%5d|%s' % (i + 1, L[i]))
