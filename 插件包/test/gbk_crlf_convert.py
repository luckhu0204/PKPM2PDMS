# -*- coding: utf-8 -*-
"""把 engine/secmap_extra.txt 从 UTF-8 落成契约 §g 要求的 **GBK + CRLF + 无 BOM**。

契约 §g：``engine/secmap_extra.txt`` 必须是 GBK、CRLF、无 BOM。编辑时用 UTF-8 写、
用本脚本转码落盘（先编码再写，失败即报错——不依赖平台默认编码）。

用法： python test\\gbk_crlf_convert.py <path> [<path> ...]
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

paths = sys.argv[1:]
if not paths:
    print('用法: python test\\gbk_crlf_convert.py <path> [<path> ...]')
    sys.exit(2)

for p in paths:
    with open(p, 'rb') as fh:
        raw = fh.read()
    text = raw.decode('utf-8')
    if text.startswith('\ufeff'):
        text = text[1:]
    text = text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')
    data = text.encode('gbk')          # 先编码（失败即报错，不写坏文件）
    with open(p, 'wb') as fh:
        fh.write(data)
    back = open(p, 'rb').read()
    same = back.decode('gbk').replace('\r\n', '\n') == text.replace('\r\n', '\n')
    print('%s: %d bytes  BOM=%s  CRLF=%d  bareLF=%d  gbk-roundtrip=%s'
          % (os.path.basename(p), len(back), back[:3] == b'\xef\xbb\xbf',
             back.count(b'\r\n'), back.count(b'\n') - back.count(b'\r\n'), same))
