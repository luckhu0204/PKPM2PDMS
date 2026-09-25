# -*- coding: utf-8 -*-
"""一次性规范化脚本：把 PML 里的 .lt(/.gt(/.le(/.ge(/.eq(/.neq( 改成运算符写法。

理由：本机 PMLLIB 里 `.le()`/`.eq()` 等方法式比较只在本机未见稳定先例，
      而运算符写法有直接出处（common\functions\findfirstmember.pmlfnc:37,41,48
      的 `!owner.mCount() lt 1`、`!type.length() le 0`、`!type.length() gt 0`）。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PDMS = os.path.join(os.path.dirname(HERE), 'pdms')
PAIRS = [('.lt(', ' lt '), ('.gt(', ' gt '), ('.le(', ' le '),
         ('.ge(', ' ge '), ('.neq(', ' neq '), ('.eq(', ' eq ')]

total = 0
for name in ['pkpmjwdexport.pmlfnc', 'pkpmjwd.pmlfrm']:
    path = os.path.join(PDMS, name)
    with open(path, 'rb') as f:
        text = f.read().decode('utf-8')
    print('===== %s' % name)
    for old, new in PAIRS:
        n = text.count(old)
        if n:
            text = text.replace(old, new)
            total += n
            print('   %-6s -> %-6s  %d 处' % (old, new, n))
    with open(path, 'wb') as f:
        f.write(text.encode('utf-8'))
print('替换合计： %d 处' % total)
sys.exit(0)
