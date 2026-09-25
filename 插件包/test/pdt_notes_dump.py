# -*- coding: utf-8 -*-
"""把 read_pdt 的全部 notes 打到控制台（人工复核用；只读）。"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pdt_read import read_pdt                                   # noqa: E402

PDT = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\1_PM.pdt'
m = read_pdt(PDT)
print('notes = %d' % len(m.notes))
for i, n in enumerate(m.notes, 1):
    print('%2d. %s' % (i, n))
print('\nsuspicious notes (含"跳过"/"未能解析"/"不一致"):')
for n in m.notes:
    if '跳过' in n or '未能解析' in n or '不一致' in n:
        print('  ! %s' % n)
