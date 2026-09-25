# -*- coding: utf-8 -*-
"""把「③ 导出数据库（目录/规格）」按加法方式写进 pdms/pkpmjwd.pmlfrm（GBK 空间内精确插入）。

只插入，不删改既有行；每处插入都先断言锚点唯一存在。
"""
import os

P = r'D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\pdms\pkpmjwd.pmlfrm'
text = open(P, 'rb').read().decode('gbk').replace('\r\n', '\n')

A_OLD = """   path down
   text .status '状态' tagwid $!tw width 62 is string
"""
A_NEW = """   path down
   para .line6 '③ 导出数据库（目录/规格）：PDMS DB Listing 文本，供 Python 侧 dbparse 解析'
   path down
   text .dbPath '导出文件' tagwid $!tw width 62 is string
   !this.dbPath.val = '%PDMSUSER%/pkpmjwd_dboutput.txt'
   path right
   button .runDb '导出目录/规格' width 16 callback '!this.runDb()'

   path down
   text .status '状态' tagwid $!tw width 62 is string
"""

B_OLD = """------------------------------------------------------------------------------
-- 关闭窗体
------------------------------------------------------------------------------
define method .close()
"""
B_NEW = """------------------------------------------------------------------------------
-- ③ 导出数据库（目录/规格）为 DB Listing 文本（调用 !!pkpmjwddbexport）
--    机制、出处与未验证项见 pdms/pkpmjwddbexport.pmlfnc 文件头与 pdms/README.txt
------------------------------------------------------------------------------
define method .runDb()
   !out = !this.dbPath.val
   if (!out.unset() or !out.length() le 0) then
      !this.status.val = '请先填写目录/规格导出文件路径'
      !!alert.message('请先填写目录/规格导出文件路径')
      return
   endif
   !this.status.val = '正在导出目录/规格到 ' & !out & ' …'
   $P PKPM-JWD：开始导出目录/规格（DB Listing）到 $!out
   !res = !!pkpmjwddbexport(!out)
   !this.status.val = '目录/规格导出： ' & !res
   $P PKPM-JWD：$!res
   !!alert.message('目录/规格导出结果： ' & !res)
endmethod
-- End of method .runDb


------------------------------------------------------------------------------
-- 关闭窗体
------------------------------------------------------------------------------
define method .close()
"""

C_OLD = """   para .line5 '      命令行入口： $m "%PMLLIB%/pkpmjwd/pkpmjwdrun.mac"'
"""
C_NEW = """   para .line5 '      命令行入口： $m "%PMLLIB%/pkpmjwd/pkpmjwdrun.mac"'
   path down
   para .line7 '      命令行导出目录/规格： !!pkpmjwddbexport( <输出文件> )'
   path down
   para .line8 '      地面真值计数：       !!pkpmjwddbinventory()'
"""

for old, new, label in ((A_OLD, A_NEW, '③ 控件块'), (B_OLD, B_NEW, '.runDb 方法'), (C_OLD, C_NEW, '提示行')):
    n = text.count(old)
    assert n == 1, '锚点「%s」期望 1 处，实际 %d 处' % (label, n)
    text = text.replace(old, new)
    print('已插入：%s' % label)

open(P, 'wb').write(text.replace('\n', '\r\n').encode('gbk'))
print('written %s (%d 字节)' % (P, os.path.getsize(P)))
