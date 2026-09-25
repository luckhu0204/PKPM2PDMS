# -*- coding: utf-8 -*-
"""打印自检输出汇总（OK / FAIL / EXTERNAL 计数 + 结论段）。"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
p = sys.argv[1] if len(sys.argv) > 1 else \
    r'D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\test\_pdtw_out.txt'
t = open(p, encoding='utf-8', errors='replace').read()
print('OK=%d  FAIL=%d  EXTERNAL=%d'
      % (t.count('[OK]'), t.count('[FAIL]'), t.count('[EXTERNAL]')))
i = t.find('=== 结论 ===')
print(t[i:] if i >= 0 else '(no 结论 section)')
