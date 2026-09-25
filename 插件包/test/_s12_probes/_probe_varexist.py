# -*- coding: utf-8 -*-
"""侦察：VAR ... EXIST 写法的全部实例 + 是否有 define function 内的实例（只读）。"""
import os
import re

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB'
EXTS = ('.pmlfnc', '.pmlfrm', '.pmlobj', '.mac')
EXIST = []
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
            if re.search(r'(?i)^var\s+\S+\s+EXIST\b', low):
                EXIST.append('%s%s:%d: %s' % (rel, '(函数内)' if in_func else '', i, l[:130]))
print('VAR ... EXIST 实例 %d 条：' % len(EXIST))
for s in EXIST:
    print('   ' + s)
