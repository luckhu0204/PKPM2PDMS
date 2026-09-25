# -*- coding: utf-8 -*-
"""临时侦察脚本 23：PDMS 写出的文本文件换行符 + PML 里是否有 char() 类函数（只读）。"""
import os, re, time

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
PMLLIB = os.path.join(ROOT, 'PMLLIB')

# 1) 检查疑似 PDMS 写出的文本文件
cands = [os.path.join(PMLLIB, 'mypml', 'forms', 'order.txt')]
USERDIRS = [os.path.expandvars(r'%PDMSUSER%'), r'D:\AVEVA\Plant\PDMS12.1.SP4\PDMSWK']
for d in USERDIRS:
    if d and os.path.isdir(d):
        for dirpath, dirnames, filenames in os.walk(d):
            for fn in filenames[-40:]:
                cands.append(os.path.join(dirpath, fn))
        break

for p in cands[:25]:
    if not os.path.exists(p):
        print('MISSING', p)
        continue
    try:
        b = open(p, 'rb').read()
    except Exception as e:
        print('ERR', p, e)
        continue
    crlf, lf = b.count(b'\r\n'), b.count(b'\n') - b.count(b'\r\n')
    print('%-70s size=%-8d CRLF=%-6d LF=%-6d  mtime=%s' % (
        os.path.relpath(p, ROOT)[:70], len(b), crlf, lf, time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(p)))))

print()
print('=== char()/chr() in PML ===')
pat = re.compile(r'(?i)\b(char|chr|ascii|repr)\s*\(')
hits = 0
for dirpath, dirnames, filenames in os.walk(PMLLIB):
    for fn in filenames:
        if not fn.lower().endswith(('.pmlfnc', '.pmlfrm', '.pmlobj', '.mac')):
            continue
        p = os.path.join(dirpath, fn)
        try:
            t = open(p, 'rb').read().decode('gbk', 'replace')
        except Exception:
            continue
        for i, l in enumerate(t.splitlines(), 1):
            if pat.search(l):
                hits += 1
                if hits <= 12:
                    print('%s:%d: %s' % (os.path.relpath(p, PMLLIB), i, l.strip()[:150]))
print('total', hits)
