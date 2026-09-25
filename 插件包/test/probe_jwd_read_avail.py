# -*- coding: utf-8 -*-
"""探测：实施包① 的 jwd_read.py 是否已可用（决定验收①要不要加跨模块交叉核对）。"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    import jwd_read
    print('jwd_read 可 import；公开名字：',
          [n for n in dir(jwd_read) if not n.startswith('_')][:20])
    m = jwd_read.read_jwd(r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\JLCJ2.jwd')
    print('counts =', m.counts())
    print('sections:', len(m.sections), 'notes:', len(m.notes))
except Exception as exc:
    import traceback
    traceback.print_exc()
