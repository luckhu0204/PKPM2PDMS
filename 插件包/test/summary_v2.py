# -*- coding: utf-8 -*-
"""汇总本包各验收脚本的输出（实施包⑨）。跑法：python test/summary_v2.py"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
for f in ('test/_db2jwd_out.txt', 'test/_rt_out.txt', 'test/_dump_chain_out.txt',
          'test/_deliverables_out.txt'):
    s = io.open(f, encoding='utf-8').read()
    tail = s[s.rfind('FAIL 项'):].replace('\n', ' ')[:120]
    print('%-30s [OK]=%-4d [FAIL]=%-3d  %s' % (f, s.count('[OK]'), s.count('[FAIL]'), tail))
