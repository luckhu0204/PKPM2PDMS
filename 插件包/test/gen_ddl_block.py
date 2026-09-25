# -*- coding: utf-8 -*-
"""从 _recon/jwd_dump/00_schema.txt 提取 SQL 语句，生成 jwd_write.py 的 _DDL 片段。

运行：python test/gen_ddl_block.py > test/_ddl_block.py
只读 _recon 下的既有文件；产物是本包自己的临时片段（不是交付物）。
"""
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SCHEMA = r'D:\AI_Work\PKPM数据解析\_recon\jwd_dump\00_schema.txt'

tables, indexes = [], []
with io.open(SCHEMA, encoding='utf-8') as f:
    for raw in f:
        s = raw.rstrip('\n').rstrip('\r')
        if s.startswith('CREATE TABLE '):
            tables.append(s)
        elif s.startswith('CREATE INDEX '):
            indexes.append(s)

print('# _DDL_TABLES / _DDL_INDEXES —— 逐字取自 _recon\\jwd_dump\\00_schema.txt')
print('# （该文件与样本 JLCJ2.jwd 的 sqlite_master 一致；提取脚本 test/gen_ddl_block.py）')
print('# CREATE TABLE 数 = %d，CREATE INDEX 数 = %d' % (len(tables), len(indexes)))
print('_DDL_TABLES = [')
for t in tables:
    assert "'" not in t, t
    print('    %r,' % t)
print(']')
print()
print('_DDL_INDEXES = [')
for t in indexes:
    assert "'" not in t, t
    print('    %r,' % t)
print(']')
