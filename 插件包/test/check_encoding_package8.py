# -*- coding: utf-8 -*-
"""核验本包产物的编码/换行（§g）：.py UTF-8 无 BOM；.pdt GBK 无 BOM + CRLF。"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
PKG = r'D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出'
for rel in ('engine\\pdt_write.py', 'engine\\pdt_read.py', 'test\\pdt_write_selfcheck.py'):
    d = open(os.path.join(PKG, rel), 'rb').read()
    ok = True
    try:
        d.decode('utf-8')
    except Exception as e:
        ok = str(e)
    print('%-34s bytes=%-7d BOM=%-5s utf8=%s' % (rel, len(d), d[:3] == b'\xef\xbb\xbf', ok))
for rel in ('test\\out\\jwd2pdt_roundtrip.pdt', 'test\\out\\pdt2pdt_roundtrip.pdt',
            'test\\out\\db2pdt.pdt', 'test\\out\\db2pdt_sections.pdt',
            'test\\out\\db2pdt_sections_only.pdt'):
    p = os.path.join(PKG, rel)
    if not os.path.isfile(p):
        print('%-34s MISSING' % rel)
        continue
    d = open(p, 'rb').read()
    print('%-34s bytes=%-8d BOM=%-5s gbk=%-5s CRLF=%-6d bareLF=%d  tail=%r'
          % (rel, len(d), d[:3] == b'\xef\xbb\xbf', bool(d.decode('gbk')),
             d.count(b'\r\n'), d.count(b'\n') - d.count(b'\r\n'), d[-8:]))
