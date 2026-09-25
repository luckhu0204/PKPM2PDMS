# -*- coding: utf-8 -*-
"""汇总两个验收脚本的输出（本包自查用）。"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
for f in ('test/_rt_out.txt', 'test/_dump_chain_out.txt', 'test/_wr_sample.txt'):
    s = io.open(f, encoding='utf-8').read()
    print('%-26s [OK]=%-4d [FAIL]=%-3d' % (f, s.count('[OK]'), s.count('[FAIL]')))
    i = s.rfind('FAIL 项')
    if i >= 0:
        print('   ', s[i:i + 160].replace('\n', ' '))
