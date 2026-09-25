# -*- coding: utf-8 -*-
"""侦察 3：CLOCK 变量的用法 + collectAllFor 的定义与签名（只读）。"""
import os
import re

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB'
EXTS = ('.pmlfnc', '.pmlfrm', '.pmlobj', '.mac')

clock = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    for fn in filenames:
        if not fn.lower().endswith(EXTS):
            continue
        p = os.path.join(dirpath, fn)
        try:
            t = open(p, 'rb').read().decode('gbk', 'replace')
        except Exception:
            continue
        rel = os.path.relpath(p, ROOT)
        for i, line in enumerate(t.splitlines(), 1):
            if re.search(r'(?i)\bCLOCK\b', line) and len(clock) < 25:
                clock.append('%s:%d: %s' % (rel, i, line.strip()[:130]))

print('===== CLOCK 用法样例（%d 行）' % len(clock))
for s in clock:
    print('   ' + s)

print()
print('===== collectAllFor 的定义位置')
for dirpath, dirnames, filenames in os.walk(ROOT):
    for fn in filenames:
        if fn.lower().startswith('collectallfor'):
            p = os.path.join(dirpath, fn)
            t = open(p, 'rb').read().decode('gbk', 'replace')
            print('--- %s' % os.path.relpath(p, ROOT))
            for i, line in enumerate(t.splitlines(), 1):
                if re.search(r'(?i)define\s+function|Arguments|Return:|^\s*--\s+\d\s', line):
                    print('   %4d| %s' % (i, line.strip()[:140]))
