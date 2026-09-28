# -*- coding: utf-8 -*-
"""交付物编码核验（契约 §g）：Python 源码 UTF-8 无 BOM；secmap_extra.txt GBK+CRLF 无 BOM。"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HERE = r'D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出'
for p, enc in ((HERE + r'\engine\pdt_read.py', 'utf-8'),
               (HERE + r'\engine\secmap.py', 'utf-8'),
               (HERE + r'\test\pdt_secmap_selfcheck.py', 'utf-8'),
               (HERE + r'\engine\secmap_extra.txt', 'gbk')):
    d = open(p, 'rb').read()
    ok = True
    try:
        d.decode(enc)
    except Exception as exc:
        ok = str(exc)
    print('%-52s bytes=%-7d BOM=%-5s %s-decode=%-5s CRLF=%d bareLF=%d'
          % (p.split('PKPM2PDMS导入导出\\')[1], len(d), d[:3] == b'\xef\xbb\xbf',
             enc, ok, d.count(b'\r\n'), d.count(b'\n') - d.count(b'\r\n')))
