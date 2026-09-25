# -*- coding: utf-8 -*-
"""两处加法修补：
  1) pkpmjwddbexport.pmlfnc 头部的 clock.pmlfnc 路径笔误 common\\ -> limbo\\（引用核对脚本发现的）；
  2) install/install.ps1 的 $required 清单加上新文件 pkpmjwddbexport.pmlfnc
     （否则安装器不会装它，⑩ 的能力装不上去）。
两个文件都是 GBK；只做 ASCII 层替换并断言。
"""
import os

PKG = r'D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出'

# 1) 引用笔误
p1 = os.path.join(PKG, 'pdms', 'pkpmjwddbexport.pmlfnc')
b1 = open(p1, 'rb').read()
old1 = b'--     common\\functions\\clock.pmlfnc:31,34'
new1 = b'--     limbo\\functions\\clock.pmlfnc:31,34'
assert b1.count(old1) == 1, '锚点不唯一：%d' % b1.count(old1)
open(p1, 'wb').write(b1.replace(old1, new1))
print('已修正引用： common\\functions\\clock.pmlfnc -> limbo\\functions\\clock.pmlfnc')

# 2) 安装器清单
p2 = os.path.join(PKG, 'install', 'install.ps1')
b2 = open(p2, 'rb').read()
old2 = b"$required = @('pkpmjwd.pmlfrm', 'pkpmjwdexport.pmlfnc', 'pkpmjwdrun.mac')"
new2 = b"$required = @('pkpmjwd.pmlfrm', 'pkpmjwdexport.pmlfnc', 'pkpmjwddbexport.pmlfnc', 'pkpmjwdrun.mac')"
assert b2.count(old2) == 1, '锚点不唯一：%d' % b2.count(old2)
open(p2, 'wb').write(b2.replace(old2, new2))
print('已把 pkpmjwddbexport.pmlfnc 加入 install.ps1 的安装清单')
