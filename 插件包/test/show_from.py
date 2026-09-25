# -*- coding: utf-8 -*-
"""打印文件里从某个标记开始的一段（调试/取证用）。"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
p = sys.argv[1]
mark = sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 3000
t = open(p, encoding='utf-8', errors='replace').read()
i = t.find(mark)
print(t[i:i + n] if i >= 0 else '(mark %r not found)' % mark)
