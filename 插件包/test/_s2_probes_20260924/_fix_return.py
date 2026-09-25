# -*- coding: utf-8 -*-
"""一次性修复：把靠行尾 & 续行的 return 拆成多条赋值（不依赖续行语义）。"""
import os

P = r'D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\pdms\pkpmjwdexport.pmlfnc'
text = open(P, 'rb').read().decode('gbk').replace('\r\n', '\n')

OLD = """   return 'OK|site=1|zone=' & !nZ.string() & '|stru=' & !nS.string() & '|frmw=' & !nF.string() &
          '|sbfr=' & !nB.string() & '|sctn=' & !nC.string() & '|pane=' & !nP.string() &
          '|stwall=' & !nW.string() & '|skip=' & !nSkip.string() &
          '|unit=' & !wUnit & '|lines=' & !n.string()
"""
NEW = """   !res = 'OK|site=1|zone=' & !nZ.string()
   !res = !res & '|stru=' & !nS.string() & '|frmw=' & !nF.string()
   !res = !res & '|sbfr=' & !nB.string() & '|sctn=' & !nC.string() & '|pane=' & !nP.string()
   !res = !res & '|stwall=' & !nW.string() & '|skip=' & !nSkip.string()
   !res = !res & '|unit=' & !wUnit & '|lines=' & !n.string()
   return !res
"""
n = text.count(OLD)
assert n == 1, '期望 1 处，实际 %d 处' % n
text = text.replace(OLD, NEW)
open(P, 'wb').write(text.replace('\n', '\r\n').encode('gbk'))
print('已替换，写入 %s（%d 字节）' % (P, os.path.getsize(P)))
