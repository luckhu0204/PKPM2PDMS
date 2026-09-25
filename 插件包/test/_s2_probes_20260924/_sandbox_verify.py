# -*- coding: utf-8 -*-
"""沙箱验证：安装后 design.uic 与原文件的差异必须只有本包追加的条目。"""
import difflib
import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
SB = os.path.join(HERE, '_sandbox')
SUB = sys.argv[1] if len(sys.argv) > 1 else 'PDMS_SANDBOX'
orig = open(os.path.join(SB, 'design.uic.orig'), 'rb').read()
cur = open(os.path.join(SB, SUB, 'design.uic'), 'rb').read()

print('原文件 : %d 字节  BOM=%s  CRLF=%d  裸LF=%d' % (
    len(orig), orig[:3] == b'\xef\xbb\xbf', orig.count(b'\r\n'),
    orig.count(b'\n') - orig.count(b'\r\n')))
print('现文件 : %d 字节  BOM=%s  CRLF=%d  裸LF=%d' % (
    len(cur), cur[:3] == b'\xef\xbb\xbf', cur.count(b'\r\n'),
    cur.count(b'\n') - cur.count(b'\r\n')))

a = orig.decode('utf-8-sig').splitlines()
b = cur.decode('utf-8-sig').splitlines()
print('\n差异（unified diff，原 → 现）：')
for line in difflib.unified_diff(a, b, 'design.uic.orig', 'design.uic.installed', lineterm='', n=1):
    print('  ' + line)

for name, data in (('原', orig), ('现', cur)):
    try:
        root = ET.fromstring(data.decode('utf-8-sig'))
        tools = root.find('{www.aveva.com}Tools')
        bar = root.find('{www.aveva.com}MenuBar')
        names = [t.get('Name') for t in tools]
        print('\n%s：XML 可解析；Tools 内条目 %d 个： %s' % (name, len(names), names))
        print('   MenuBar 条目： %s' % [t.get('Name') for t in bar])
    except Exception as exc:
        print('\n%s：XML 解析失败 %s' % (name, exc))

# 逐行核对：原文件的每一行都仍在现文件里，且顺序不变
i = 0
kept = 0
for line in a:
    while i < len(b) and b[i] != line:
        i += 1
    if i < len(b):
        kept += 1
        i += 1
print('\n原文件 %d 行中有 %d 行按原顺序保留在现文件里（应为全部保留）' % (len(a), kept))
print('结论：%s' % ('只追加、未改动既有行' if kept == len(a) else '既有行被改动，需检查'))
