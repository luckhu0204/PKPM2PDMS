# -*- coding: utf-8 -*-
"""侦察：define function 内 $P / $m / .upcase() / .size() 的实例（只读）。"""
import os
import re

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB'
EXTS = ('.pmlfnc', '.pmlfrm', '.pmlobj')
res = {'$P': [], '$m': [], 'upcase': [], 'size()': []}
for dirpath, dirnames, filenames in os.walk(ROOT):
    for fn in filenames:
        if not fn.lower().endswith(EXTS):
            continue
        p = os.path.join(dirpath, fn)
        try:
            lines = open(p, 'rb').read().decode('gbk', 'replace').splitlines()
        except Exception:
            continue
        rel = os.path.relpath(p, ROOT)
        in_func = False
        for i, raw in enumerate(lines, 1):
            l = raw.strip()
            low = l.lower()
            if re.match(r'(?i)^define\s+function\b', low):
                in_func = True
            elif re.match(r'(?i)^endfunction\b', low):
                in_func = False
            if not in_func:
                continue
            if low.startswith('$p ') and len(res['$P']) < 6:
                res['$P'].append('%s:%d: %s' % (rel, i, l[:120]))
            if low.startswith('$m ') and len(res['$m']) < 6:
                res['$m'].append('%s:%d: %s' % (rel, i, l[:120]))
            if '.upcase()' in l and len(res['upcase']) < 6:
                res['upcase'].append('%s:%d: %s' % (rel, i, l[:120]))
            if re.search(r'(?i)\.size\(\)', l) and len(res['size()']) < 6:
                res['size()'].append('%s:%d: %s' % (rel, i, l[:120]))
for k, v in res.items():
    print('=== 函数内 %s（%d 条）' % (k, len(v)))
    for s in v:
        print('   ' + s)
