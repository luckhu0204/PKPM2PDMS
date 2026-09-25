# -*- coding: utf-8 -*-
"""沙箱验证：卸载后 design.uic 是否逐字节回到安装前，以及包目录是否已被移走。"""
import difflib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SB = os.path.join(HERE, '_sandbox')
SUB = sys.argv[1] if len(sys.argv) > 1 else 'PDMS_SANDBOX2'
a = open(os.path.join(SB, 'design.uic.orig'), 'rb').read()
b = open(os.path.join(SB, SUB, 'design.uic'), 'rb').read()
print('安装前 %d 字节 / 卸载后 %d 字节 / 逐字节相同 = %s' % (len(a), len(b), a == b))
d = list(difflib.unified_diff(a.decode('utf-8-sig').splitlines(),
                              b.decode('utf-8-sig').splitlines(),
                              'orig', 'after-uninstall', lineterm=''))
print('行差异：%s' % ('无' if not d else ''))
for l in d:
    print('  ' + l)

pkg = os.path.join(SB, SUB, 'PMLLIB', 'pkpmjwd')
print('\n包目录仍存在 = %s' % os.path.isdir(pkg))
print('PMLLIB 下的条目： %s' % sorted(os.listdir(os.path.join(SB, SUB, 'PMLLIB'))))
print('sandbox 根下的文件： %s' % sorted(os.listdir(os.path.join(SB, SUB))))
