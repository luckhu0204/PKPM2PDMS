# -*- coding: utf-8 -*-
"""侦察：do 循环内 / handle 块内 return 的本机实例（决定唯一化函数的实现形态）。"""
import os
import re

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB'
EXTS = ('.pmlfnc', '.pmlfrm', '.pmlobj')

in_do = []
in_handle = []
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
        depth_do = 0
        depth_handle = 0
        for i, raw in enumerate(lines, 1):
            l = raw.strip()
            low = l.lower()
            # 粗粒度深度跟踪（注释行跳过）
            if low.startswith('--'):
                continue
            if re.match(r'(?i)^(do)\b', low):
                depth_do += 1
            elif re.match(r'(?i)^enddo\b', low):
                depth_do -= 1
            elif re.match(r'(?i)^handle\b', low):
                depth_handle += 1
            elif re.match(r'(?i)^endhandle\b', low):
                depth_handle -= 1
            elif re.match(r'(?i)^return\b', low):
                if depth_do > 0 and len(in_do) < 8:
                    in_do.append('%s:%d: %s' % (rel, i, l[:120]))
                if depth_handle > 0 and len(in_handle) < 8:
                    in_handle.append('%s:%d: %s' % (rel, i, l[:120]))

print('=== do 循环内 return（样例 %d 条）' % len(in_do))
for s in in_do:
    print('   ' + s)
print()
print('=== handle 块内 return（样例 %d 条）' % len(in_handle))
for s in in_handle:
    print('   ' + s)
