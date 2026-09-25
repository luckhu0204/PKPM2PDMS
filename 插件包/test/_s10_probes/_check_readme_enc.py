# -*- coding: utf-8 -*-
"""判定 pdms/README.txt 的编码与换行（只读）。"""
import os

P = r'D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\pdms\README.txt'
b = open(P, 'rb').read()
print('size=%d BOM=%s CRLF=%d LF=%d' % (len(b), b[:3] == b'\xef\xbb\xbf',
                                        b.count(b'\r\n'), b.count(b'\n') - b.count(b'\r\n')))
for enc in ('utf-8', 'gbk'):
    try:
        t = b.decode(enc)
        print('%-6s OK  首行=%r' % (enc, t.splitlines()[0]))
    except UnicodeDecodeError as exc:
        print('%-6s FAIL %s' % (enc, exc))
