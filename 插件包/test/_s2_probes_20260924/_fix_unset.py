# -*- coding: utf-8 -*-
"""一次性加固：PANE 取值时把 unset/badref 判断拆成两个 if（避免 or 两边都求值时的取属性风险）。"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(os.path.dirname(HERE), 'pdms', 'pkpmjwdexport.pmlfnc')
text = open(P, 'rb').read().decode('gbk').replace('\r\n', '\n')

OLD = """   if (!loop.unset() or !loop.badref()) then
      return ''
   endif
"""
NEW = """   if (!loop.unset()) then
      return ''
   endif
   if (!loop.badref()) then
      return ''
   endif
"""
OLD2 = """   if (!scope.unset() or !scope.badref()) then
      return 'ERR|导出范围无效（未指定元素或 DBREF 无效）'
   endif
"""
NEW2 = """   if (!scope.unset()) then
      return 'ERR|导出范围无效（未指定导出范围元素）'
   endif
   if (!scope.badref()) then
      return 'ERR|导出范围无效（DBREF 无效）'
   endif
"""
for old, new, label in ((OLD, NEW, 'PANE loop'), (OLD2, NEW2, '参数检查 scope')):
    n = text.count(old)
    assert n == 1, '%s：期望 1 处，实际 %d 处' % (label, n)
    text = text.replace(old, new)
    print('已替换：%s' % label)

open(P, 'wb').write(text.replace('\n', '\r\n').encode('gbk'))
print('written %s (%d 字节)' % (P, os.path.getsize(P)))
