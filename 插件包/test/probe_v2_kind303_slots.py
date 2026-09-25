# -*- coding: utf-8 -*-
"""只读：取 .jwd 样本里 3 条 Kind=303 的 ShapeVal 原文与字段计数（校准 §k.3 的槽位算法）。"""
import io
import os
import sqlite3
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
JWD = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\JLCJ2.jwd'
con = sqlite3.connect('file:' + JWD.replace('\\', '/') + '?mode=ro', uri=True)
con.text_factory = lambda b: b.decode('gbk', 'replace') if isinstance(b, bytes) else b
for tbl in ('pkpmColSect', 'pkpmBraceSect'):
    for sid, no, name, mat, kind, sv in con.execute(
            'SELECT ID,No_,Name,Mat,Kind,ShapeVal FROM %s ORDER BY ID' % tbl):
        if kind != 303:
            continue
        fields = sv.split(',')
        print('%s ID=%s name=%r' % (tbl, sid, name))
        print('  split_len=%d  last=%r' % (len(fields), fields[-3:]))
        print('  原文=%s' % sv)
        # 打印非零槽位（下标 = split 下标）
        nz = [(i, f) for i, f in enumerate(fields) if f.strip() not in ('', '0')]
        print('  非零槽: %s' % nz)
con.close()
