# -*- coding: utf-8 -*-
"""R6 修复员临时脚本：检查待改文件的编码/换行（只读）。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
files = [
    r'D:\AI_Work\PKPM数据解析\PKPM2PDMS_v2.1.0\插件包\pdms\pkpm2pdmssctn.pmlfnc',
    r'D:\AI_Work\PKPM数据解析\PKPM2PDMS_v2.1.0\插件包\pdms\pkpm2pdmsnum.pmlfnc',
    r'D:\AI_Work\PKPM数据解析\PKPM2PDMS_v2.1.0\插件包\engine\secmap_extra.txt',
]
for p in files:
    raw = open(p, 'rb').read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    try:
        raw.decode('utf-8'); u8 = True
    except UnicodeDecodeError:
        u8 = False
    try:
        raw.decode('gbk'); gk = True
    except UnicodeDecodeError:
        gk = False
    print(p.split('\\')[-1], 'BOM=', bom, 'utf8=', u8, 'gbk=', gk,
          'CRLF=', raw.count(b'\r\n'), 'LF=', raw.count(b'\n'))
