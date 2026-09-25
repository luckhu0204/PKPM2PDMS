# -*- coding: utf-8 -*-
"""扫描 test/*.py 里与 pdt_write / $END / $DEFFRAMESECTION / 写出相关的断言。"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

T = r'D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\test'
KEYS = ('pdt_write', 'write_pdt', 'PdtOptions', '$END', '$DEFFRAMESECTION',
        'endswith', 'skeleton', 'exi', 'exr')

for fn in sorted(os.listdir(T)):
    if not fn.endswith('.py'):
        continue
    p = os.path.join(T, fn)
    lines = open(p, encoding='utf-8', errors='replace').read().split('\n')
    hits = [(i, l) for i, l in enumerate(lines, 1)
            if any(k in l for k in KEYS)]
    if hits:
        print('=== %s (%d hits, %d lines) ===' % (fn, len(hits), len(lines)))
        for i, l in hits[:25]:
            print('  %4d %s' % (i, l.strip()[:150]))
