# -*- coding: utf-8 -*-
"""把自检输出里的 FAIL/关键行挑出来（避免 cmd 的引号与编码问题）。"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
p = sys.argv[1] if len(sys.argv) > 1 else r'D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\test\_pdtw_out.txt'
keys = sys.argv[2:] or ['[FAIL]', '[OK]', '不匹配', '不自治', 'L4', 'L5', '读回', 'bbox']
for l in open(p, encoding='utf-8', errors='replace').read().split('\n'):
    if any(k in l for k in keys):
        print(l)
