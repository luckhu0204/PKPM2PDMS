# -*- coding: utf-8 -*-
"""列出规范化后含运算符比较的全部行，便于逐行核对括号是否平衡。"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PDMS = os.path.join(os.path.dirname(HERE), 'pdms')
OPS = re.compile(r'\s(lt|gt|le|ge|eq|neq)\s')
for name in ['pkpmjwdexport.pmlfnc', 'pkpmjwd.pmlfrm']:
    path = os.path.join(PDMS, name)
    text = open(path, 'rb').read().decode('utf-8')
    print('===== %s' % name)
    for i, l in enumerate(text.splitlines(), 1):
        if OPS.search(l):
            bal = l.count('(') - l.count(')')
            flag = 'BAL' if bal == 0 else 'BAD(%+d)' % bal
            print('%4d %-9s |%s' % (i, flag, l))
