# -*- coding: utf-8 -*-
"""临时侦察脚本 26：runMacro 的出处 + 官方 runmacro.pmlfrm 写法（只读）。"""
import os, re

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
PMLLIB = os.path.join(ROOT, 'PMLLIB')

# 1) runMacro 是核心函数还是 PMLLIB 文件？
for dirpath, dirnames, filenames in os.walk(PMLLIB):
    for fn in filenames:
        if fn.lower().startswith('runmacro'):
            print('FILE:', os.path.relpath(os.path.join(dirpath, fn), PMLLIB))
for dirpath, dirnames, filenames in os.walk(ROOT):
    if 'PMLLIB' in dirpath:
        continue
    for fn in filenames:
        if fn.lower() in ('runmacro.pmlfnc',):
            print('OUTSIDE PMLLIB:', os.path.join(dirpath, fn))

# 2) 官方 runmacro.pmlfrm
p = os.path.join(PMLLIB, 'common', 'forms', 'runmacro.pmlfrm')
if os.path.exists(p):
    t = open(p, 'rb').read().decode('gbk', 'replace')
    print('===== common/forms/runmacro.pmlfrm (%d lines)' % (t.count(chr(10)) + 1))
    for i, l in enumerate(t.splitlines(), 1):
        if i <= 90:
            print('%4d| %s' % (i, l.rstrip()))

# 3) 核心函数是否存在：查 PDMS 核心库字符串
lib = os.path.join(ROOT, 'pdmsdll.dll')
print()
print('=== 核心字符串 runMacro 检索 ===')
for f in ['pdmsdll.dll', 'pdms.dll', 'des.exe', 'mon.exe']:
    q = os.path.join(ROOT, f)
    if os.path.exists(q):
        b = open(q, 'rb').read()
        for needle in (b'runMacro', b'RUNMACRO'):
            print('  %-12s %-10s hits=%d' % (f, needle.decode(), b.count(needle)))
