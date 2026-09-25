# -*- coding: utf-8 -*-
"""比较两个 .pdt 的差异行（定位幂等性差异）。"""
import io
import sys
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
a, b = sys.argv[1], sys.argv[2]
A = open(a, 'rb').read().decode('gbk').replace('\r\n', '\n').split('\n')
B = open(b, 'rb').read().decode('gbk').replace('\r\n', '\n').split('\n')
print('lines A=%d B=%d' % (len(A), len(B)))
diff = [(i, x, y) for i, (x, y) in enumerate(zip(A, B), 1) if x != y]
print('差分行数 = %d' % len(diff))
for i, x, y in diff[:12]:
    print('L%-6d A=%r' % (i, x[:120]))
    print('       B=%r' % (y[:120],))
if len(A) != len(B):
    print('长度不同：A 多 %s / B 多 %s' % (len(A) - len(B), len(B) - len(A)))
