# -*- coding: utf-8 -*-
"""临时侦察脚本 2：扫描 PDMS 根下全部 .uic，列出 Command 的 Type/Key 取值分布（只读）。"""
import os, re, glob

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
pat = re.compile(r'<(\w+)Tool Name="([^"]*)">(.*?)</\1Tool>', re.S)
cmdpat = re.compile(r'<Type>([^<]*)</Type>\s*<Key>([^<]*)</Key>', re.S)

types = {}
for p in sorted(glob.glob(os.path.join(ROOT, '*.uic'))):
    b = open(p, 'rb').read()
    t = b.decode('utf-8-sig', 'replace')
    for m in pat.finditer(t):
        kind, name, body = m.group(1), m.group(2), m.group(3)
        c = cmdpat.search(body)
        key = c.group(2) if c else '(no command)'
        ty = c.group(1) if c else '-'
        types.setdefault(ty, []).append((os.path.basename(p), kind, name, key))

for ty in sorted(types):
    lst = types[ty]
    print('=== Type=%s  count=%d' % (ty, len(lst)))
    for row in lst[:40]:
        print('    %s  %sTool=%s  Key=%s' % row)
    if len(lst) > 40:
        print('    ... +%d more' % (len(lst) - 40))
