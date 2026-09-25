# -*- coding: utf-8 -*-
"""在 pkpmjwddbexport.pmlfnc 的文件头补一条实测记录（WRITEALPHAFILE 去尾空格）。"""
import os

P = r'D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\pdms\pkpmjwddbexport.pmlfnc'
t = open(P, 'rb').read().decode('gbk').replace('\r\n', '\n')

OLD = """--     rptoutput.pmlfrm:744             调用方 comment = 'End Data Listing    Date : … '
"""
NEW = """--     rptoutput.pmlfrm:744             调用方 comment = 'End Data Listing    Date : … '
--     实测（本次会话比对用户样本 L1/L70300）：WRITEALPHAFILE 会去掉行尾空格 ——
--     rptoutput 的字面量 `'$S-  -- Synonym translation OFF '`（尾空格）与样本实际字节
--     `$S-  -- Synonym translation OFF`（无尾空格）一致；本文件照抄字面量，产物同字节。
"""
n = t.count(OLD)
assert n == 1, '锚点 %d 处' % n
open(P, 'wb').write(t.replace(OLD, NEW).replace('\n', '\r\n').encode('gbk'))
print('已补记，%d 字节' % os.path.getsize(P))
