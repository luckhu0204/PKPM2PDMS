# -*- coding: utf-8 -*-
"""把「命名唯一化」按加法接进 pdms/pkpmjwd.pmlfrm 与 pdms/pkpmjwdrun.mac（GBK 内精确锚点插入）。

只插入/最小改写；每处先断言锚点唯一存在。
"""
import os

PKG = r'D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出'


def load(name):
    p = os.path.join(PKG, name)
    return open(p, 'rb').read().decode('gbk').replace('\r\n', '\n'), p


def save(p, text):
    open(p, 'wb').write(text.replace('\n', '\r\n').encode('gbk'))
    print('written %s (%d 字节)' % (p, os.path.getsize(p)))


def patch(text, old, new, label):
    n = text.count(old)
    assert n == 1, '锚点「%s」期望 1 处，实际 %d 处' % (label, n)
    print('已插入：%s' % label)
    return text.replace(old, new)


# ============================ pkpmjwd.pmlfrm ============================
text, p = load(r'pdms\pkpmjwd.pmlfrm')

# 1) 文件头功能行（加一行 ④）
text = patch(text, """-- 功能   : ① 运行导入宏（Python 侧 macgen 生成的 .mac，用 $m 方式执行）
--          ② 导出当前模型到 #PKPM-JWD-PDMSDUMP 文本（调用 !!pkpmjwdexport）
""", """-- 功能   : ① 运行导入宏（Python 侧 macgen 生成的 .mac，用 $m 方式执行）
--          ② 导出当前模型到 #PKPM-JWD-PDMSDUMP 文本（调用 !!pkpmjwdexport）
--          ④ 命名唯一化统计：导入宏自动对重名加 re/re2/…（CONTRACT v3 §o），
--            运行前后调 !!pkpmjwdRenamesCount()/!!pkpmjwdRenamesFailCount()
--            算出「本次因重名改名 N 个」并显示；「改名清单」按钮逐条输出
""", '文件头功能行')

# 2) ① 区块：改名统计 text + 改名清单按钮（插在 runMac 按钮之后）
text = patch(text, """   text .macroPath '宏文件' tagwid $!tw width 62 is string
   path right
   button .runMac '运行导入宏' width 16 callback '!this.runMac()'
""", """   text .macroPath '宏文件' tagwid $!tw width 62 is string
   path right
   button .runMac '运行导入宏' width 16 callback '!this.runMac()'
   path down
   text .renCount '改名统计' tagwid $!tw width 62 is string
   !this.renCount.val = '尚未运行导入宏'
   path right
   button .showRenames '改名清单' width 12 callback '!this.showRenames()'
""", '① 区块改名统计控件')

# 3) 底部说明（加一行）
text = patch(text, """   para .line8 '      地面真值计数：       !!pkpmjwddbinventory()'
""", """   para .line8 '      地面真值计数：       !!pkpmjwddbinventory()'
   path down
   para .line9 '      唯一化：导入宏对重名自动加 re/re2/…（CONTRACT v3 §o）；'
   path down
   para .lineA '      改名清单按钮把 TYPE|原名|实际名 逐条输出到命令窗'
""", '底部说明行')

# 4) runMac：前后计数 + $m 包 handle/elsehandle（elsehandle any：aba\\Forms\\ababuildkeyplan.pmlfrm:391 等 1767 处）
text = patch(text, """   !this.status.val = '正在运行导入宏 …'
   $P PKPM-JWD：开始运行导入宏 $!p
   $m "$!p"
   !this.status.val = '导入宏已执行： ' & !p
   $P PKPM-JWD：导入宏执行完毕
   !!alert.message('导入宏已执行完毕：' & !p)
endmethod
""", """   !this.status.val = '正在运行导入宏 …'
   $P PKPM-JWD：开始运行导入宏 $!p

   -- 运行前取改名记录基线（函数未加载时 handle any 兜底，t0/f0 保持 -1）
   !t0 = -1
   !f0 = -1
   handle any
      !t0 = !!pkpmjwdRenamesCount()
      !f0 = !!pkpmjwdRenamesFailCount()
   endhandle

   -- 运行导入宏；宏内 ONERROR …RETURN ERROR 报错时 elsehandle 接住，仍统计改名
   !macOk = TRUE
   handle any
      $m "$!p"
   elsehandle any
      !macOk = FALSE
   endhandle

   -- 运行后取计数，算「本次」改名/失败个数（契约 §o.7：report.renames 是唯一真相，
   -- 这里的数字只是窗体显示）
   !t1 = -1
   !f1 = -1
   handle any
      !t1 = !!pkpmjwdRenamesCount()
      !f1 = !!pkpmjwdRenamesFailCount()
   endhandle
   if (!t0 ge 0 and !t1 ge 0) then
      !nr = (!t1 - !f1) - (!t0 - !f0)
      !nf = !f1 - !f0
      !this.renCount.val = '本次因重名改名 ' & !nr.string() & ' 个，失败 ' & !nf.string() & ' 个（累计 ' & !t1.string() & ' 条）'
   else
      !this.renCount.val = '唯一化函数未加载（pkpmjwduniquename.pmlfnc），无法统计'
   endif
   $P PKPM-JWD：$!this.renCount.val

   if (!macOk.not()) then
      !this.status.val = '导入宏执行报错（详见命令窗，ONERROR 已中止）；改名统计已更新'
      !!alert.message('导入宏执行报错（ONERROR 已中止）；改名统计见「改名统计」栏')
      return
   endif

   !this.status.val = '导入宏已执行： ' & !p
   $P PKPM-JWD：导入宏执行完毕
   !!alert.message('导入宏已执行完毕：' & !p)
endmethod
""", 'runMac 计数与容错')

# 5) 新方法 .showRenames()（插在 .runMac 结束之后、② 之前）
text = patch(text, """-- End of method .runMac


------------------------------------------------------------------------------
-- ② 导出当前模型到文本（调用 !!pkpmjwdexport）
""", """-- End of method .runMac


------------------------------------------------------------------------------
-- 改名清单：调 !!pkpmjwdRenamesShow() 把 TYPE|原名|实际名 逐条 $P 到命令窗
-- （函数未加载时 elsehandle any 兜底）
------------------------------------------------------------------------------
define method .showRenames()
   handle any
      !!pkpmjwdRenamesShow()
      !this.status.val = '改名清单已输出到命令窗'
   elsehandle any
      !this.status.val = '唯一化函数未加载：请用入口宏 pkpmjwdrun.mac 重开窗体'
      !!alert.message('唯一化函数未加载（pkpmjwduniquename.pmlfnc）；入口宏会自动 $M 预载')
   endhandle
endmethod
-- End of method .showRenames


------------------------------------------------------------------------------
-- ② 导出当前模型到文本（调用 !!pkpmjwdexport）
""", 'showRenames 方法')

save(p, text)

# ============================ pkpmjwdrun.mac ============================
text, p = load(r'pdms\pkpmjwdrun.mac')

text = patch(text, """-- 菜单   : 装完菜单后由 design.uic 的
--          <Command><Type>Macro</Type><Macro>show !!pkpmjwd</Macro></Command>
--          直接打开窗体，本宏只是命令行兜底入口
-- ===========================================================================

$P PKPM-JWD导入导出：加载操作窗体 …
show !!pkpmjwd
""", """-- 菜单   : 装完菜单后由 design.uic 的
--          <Command><Type>Macro</Type><Macro>show !!pkpmjwd</Macro></Command>
--          直接打开窗体，本宏只是命令行兜底入口
-- 唯一化 : 本宏先 $M 预载命名唯一化函数（CONTRACT v3 §o：重名自动加 re/re2/…）；
--          macgen 生成的导入宏头部也会自带同样的 $M 预载行（§o.4 模板），
--          因此单独 $M 导入宏也能工作。窗体「改名统计」栏显示本次改名个数。
--          （$M 加载 %PMLLIB% 下 .pmlfnc 的出处：
--            admin\\forms\\adminapplic.pmlfrm:205
--            $M "%PMLLIB%/limbo/functions/moduleswitch.pmlfnc"）
-- ===========================================================================

-- 预载命名唯一化函数；失败不中止（窗体对未加载有 handle any 兜底，
-- 导入宏头部还有自己的 $M 预载行）
$P PKPM-JWD导入导出：预载命名唯一化函数 …
$M "%PMLLIB%/pkpmjwd/pkpmjwduniquename.pmlfnc"
   handle any
      $P PKPM-JWD：唯一化函数预载失败（不影响打开窗体；导入宏会自带 $M 预载行）
   endhandle

$P PKPM-JWD导入导出：加载操作窗体 …
show !!pkpmjwd
""", 'run.mac 预载与说明')

save(p, text)
print('done')
