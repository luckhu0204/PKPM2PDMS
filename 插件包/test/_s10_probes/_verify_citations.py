# -*- coding: utf-8 -*-
"""逐条核对 pkpmjwddbexport.pmlfnc 文件头里引用的 (文件:行号) 是否真实存在，
并把被引用的行原文打印出来（本机 PDMS 安装内，只读）。

用法： python _verify_citations.py [PML 文件]
"""
import os
import re
import sys

PMLLIB = r'D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB'
SRC = sys.argv[1] if len(sys.argv) > 1 else \
    r'D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\pdms\pkpmjwddbexport.pmlfnc'

text = open(SRC, 'rb').read().decode('gbk')
CITE = re.compile(r'([A-Za-z0-9_\\\.\-]+\.(?:pmlfnc|pmlfrm|pmlobj|mac)):(\d+)(?:-(\d+))?')

# 建立 basename -> 绝对路径 索引（同名多份时全部保留）
index = {}
for dirpath, dirnames, filenames in os.walk(PMLLIB):
    for fn in filenames:
        if fn.lower().endswith(('.pmlfnc', '.pmlfrm', '.pmlobj', '.mac')):
            index.setdefault(fn.lower(), []).append(os.path.join(dirpath, fn))

seen = []
for m in CITE.finditer(text):
    key = (m.group(1), m.group(2), m.group(3))
    if key not in seen:
        seen.append(key)

print('### 共提取到 %d 条引用' % len(seen))
ok = 0
bad = 0
for name, a, b in seen:
    base = os.path.basename(name.replace('\\', '/')).lower()
    cands = index.get(base, [])
    if not cands:
        print('!! 找不到文件： %s' % name)
        bad += 1
        continue
    # 优先取 relpath 与引用后缀匹配的那份
    hit = cands[0]
    for c in cands:
        if name.replace('/', '\\').lower() in c.lower():
            hit = c
            break
    lines = open(hit, 'rb').read().decode('gbk', 'replace').splitlines()
    a1 = int(a)
    z1 = int(b) if b else a1
    if z1 > len(lines):
        print('!! 行号越界： %s:%s（该文件仅 %d 行）' % (name, a, len(lines)))
        bad += 1
        continue
    print('--- %s:%s-%s   ← %s' % (name, a, z1, os.path.relpath(hit, PMLLIB)))
    for i in range(a1, min(z1, a1 + 6) + 1):
        print('    %5d| %s' % (i, lines[i - 1].strip()[:130]))
    if z1 - a1 > 6:
        print('    ...（其余 %d 行略）' % (z1 - a1 - 6))
    ok += 1

print()
print('### 引用核对：可解析 %d 条，异常 %d 条' % (ok, bad))
