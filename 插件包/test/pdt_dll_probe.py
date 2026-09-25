# -*- coding: utf-8 -*-
"""探针 ⑧-1：自己从 PDMSxCA_Addin121.dll 里提取 .pdt 行式格式串（UTF-16LE、NUL 截断）。

不依赖契约附录 D.1 的转述：本脚本自己扫全文件里的 UTF-16LE 串，按关键词筛出
段/行式相关的格式串并打印「文件偏移 + 原文」，供 check ③ 逐字核对。

用法： python test\\pdt_dll_probe.py [关键字正则]
"""
import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DLL = (r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'
       r'\P-TRANS\PDMSxCA_Addin121.dll')

KEYWORDS = sys.argv[1] if len(sys.argv) > 1 else \
    r'ID=|KIND=|T1=|M=|EXI|EXR|NODES=|NODEE=|FLOORID=|NETID=|SECTID=|SLABID|NO=|HI=|' \
    r'BL=|TL=|WID=|LEN=|HEI=|NUB=|TYPE=|EC='

data = open(DLL, 'rb').read()
print('DLL = %s' % DLL)
print('size = %d bytes' % len(data))

# UTF-16LE 串提取：可打印 ASCII（含空格/逗号/花括号/等号），至少 8 个字符
rx = re.compile(rb'(?:[\x20-\x7e]\x00){8,}')
pat = re.compile(KEYWORDS)
found = []
for m in rx.finditer(data):
    s = m.group(0).decode('utf-16-le')
    if pat.search(s):
        found.append((m.start(), s))
print('candidate format strings: %d' % len(found))
for off, s in found:
    print('  0x%06X  %r' % (off, s))

print('\n--- "$" 段名 / 其它短串 ---')
rx2 = re.compile(rb'(?:[\x20-\x7e]\x00){2,}')
seg = re.compile(r'^(S?[A-Z_]+|\\$[A-Z]+)$')
for m in rx2.finditer(data):
    s = m.group(0).decode('utf-16-le')
    if s.startswith('$') or seg.match(s.strip()) and len(s) >= 6:
        print('  0x%06X  %r' % (m.start(), s))
