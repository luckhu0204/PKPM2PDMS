# -*- coding: utf-8 -*-
"""扫描 engine/*.py 里对 v2 新模块（pdt_write/sectionlib/dbparse/dbmacro）的引用。"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ENG = r'D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\engine'
KEYS = ('pdt_write', 'sectionlib', 'dbparse', 'dbmacro', 'write_pdt',
        'encode_defframesection', 'parse_db_macro', 'PdtOptions')
for fn in sorted(os.listdir(ENG)):
    if not fn.endswith('.py'):
        continue
    p = os.path.join(ENG, fn)
    lines = open(p, encoding='utf-8').read().split('\n')
    hits = [(i, l.strip()) for i, l in enumerate(lines, 1)
            if any(k in l for k in KEYS)]
    print('=== %s  (%d hits, %d lines)' % (fn, len(hits), len(lines)))
    for i, l in hits[:20]:
        print('  %4d %s' % (i, l[:160]))
