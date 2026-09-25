# -*- coding: utf-8 -*-
"""检查本包 PML 里是否存在"靠行尾运算符续行"的写法（这类写法在 PML1/PML2 里语义不同，
本包一律避免，改为拆成多条赋值）。"""
import os

PDMS = r'D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\pdms'
for n in ['pkpmjwdexport.pmlfnc', 'pkpmjwd.pmlfrm', 'pkpmjwdrun.mac']:
    p = os.path.join(PDMS, n)
    t = open(p, 'rb').read().decode('gbk')
    hits = [(i, l) for i, l in enumerate(t.split('\r\n'), 1)
            if l.rstrip().endswith('&') or l.rstrip().endswith('$')]
    print('=== %s：行尾续行候选 %d 处' % (n, len(hits)))
    for i, l in hits:
        print('%4d| %s' % (i, l))
