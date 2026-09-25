# -*- coding: utf-8 -*-
"""把 test/_ddl_block.py 的内容拼进 engine/jwd_write.py 的 # <<<DDL_BLOCK>>> 标记处。

运行：python test/splice_ddl.py
只改本包自己的两个文件；不删任何文件。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, '..', 'engine', 'jwd_write.py')
BLOCK = os.path.join(HERE, '_ddl_block.py')
MARKER = '# <<<DDL_BLOCK>>>'

src = io.open(TARGET, encoding='utf-8').read()
blk = io.open(BLOCK, encoding='utf-8').read().rstrip('\n')
n = src.count(MARKER)
if n != 1:
    print('标记出现 %d 次（要求恰好 1 次），未做改动' % n)
    sys.exit(1)
io.open(TARGET, 'w', encoding='utf-8', newline='\n').write(src.replace(MARKER, blk))
print('已拼接：%s <- %s（源码 %d 字节）' % (TARGET, BLOCK, len(src)))
