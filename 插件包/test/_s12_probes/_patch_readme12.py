# -*- coding: utf-8 -*-
"""在 pdms/README.txt 追加「命名唯一化（重名加 re）」一节（UTF-8 无 BOM + LF，与原文一致）。"""
import os

P = r'D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\pdms\README.txt'
text = open(P, 'rb').read().decode('utf-8')

SECTION = """
命名唯一化（重名加 re）—— pkpmjwduniquename.pmlfnc
==================================================

需求与契约
----------
宏里的名字不能与 PDMS 库中已有模型重名：重名自动加后缀 `re`（仍冲突则 `re2`、`re3`…）。
判定发生在 PDMS 运行期 ⇒ 逻辑在 PML，宏/窗体调用它（CONTRACT v3 §o，附录 F.1 是逐字夹具）。

入口
----
  !!pkpmjwdUniquename(!base)   主函数：候选 = base, base&'re', base&'re2'…base&'re99'（共 100 个），
                               返回第一个可用名；全部占用 ⇒ 记 FAIL 并返回 ''（导入宏的
                               ONERROR GOLABEL /PKPMJWDERR 会中止整宏，绝不跳过）。
  !!pkpmjwdRenamesCount()      改名记录条数（窗体统计用）
  !!pkpmjwdRenamesFailCount()  其中 FAIL 条数
  !!pkpmjwdRenamesShow()       逐条 $P 输出 TYPE|原名|实际名（窗体「改名清单」按钮）
预载：入口宏 pkpmjwdrun.mac 先行 `$M "%PMLLIB%/pkpmjwd/pkpmjwduniquename.pmlfnc"`
（$M 加载 %PMLLIB% 下 .pmlfnc 的本机出处：admin\\forms\\adminapplic.pmlfrm:205）；
macgen 生成的导入宏头部也自带同样的 $M 预载行（契约 §o.4 模板）。

窗体显示
--------
`pkpmjwd.pmlfrm` 的「改名统计」栏在每次「运行导入宏」后显示
「本次因重名改名 N 个，失败 M 个（累计 K 条）」——用运行前后
`!!pkpmjwdRenamesCount()/!!pkpmjwdRenamesFailCount()` 的差值计算；
宏报错（ONERROR 中止）时也能给出统计（$m 包在 handle any / elsehandle any 里）。
「改名清单」按钮把记录逐条输出到命令窗。窗体不消毁记录；
report.renames（§o.7）才是唯一真相，生成文件里仍是原名。

占用探测的两种已证实写法（§o.3；本函数两种都处理）
--------------------------------------------------
本机 PMLLIB 里 `VAR !x EXIST <名>` 有两种并存用法：
  (a) 值判定：存在='TRUEA'、不存在='FALSEA'，VAR 本身不报错 ——
      assembly\\functions\\assybuildname.pmlfnc:47-50,64-65（VAR 后直接 .eq('FALSEA')，无 handle）、
      aba\\Forms\\abaarealib.pmlfrm:304-306（.eq('TRUEA') ⇒ "already exists"）、
      aba\\Forms\\abauserview.pmlfrm:859-860、TIANGONG\\functions\\tgautonum.pmlfnc:34-41；
  (b) 错误捕获：VAR 包在 handle (2,109)（Undefined name）——
      aba\\Forms\\abaarealib.pmlfrm:107-114（注释原文 -- Undefined name）。
若只按附录 F.1 夹具的「落到 (2,109) ⇒ 可用、否则 ⇒ 占用」，则全新库的空間名
（VAR 正常返回 'FALSEA'）会被误判为占用，函数永远 FAIL —— 即 F.1 末尾
「夹具表达算法、落地要能跑」的情形。本函数：handle (2,109) 命中 ⇒ 可用（冻结语义），
VAR 正常返回时按 (a) 判值（'TRUEA' ⇒ 占用，否则可用）。冻结要素不变：
候选序列 / EXIST+(2,109) / 记录格式 'TYPE|原名|实际名' / FAIL 语义。

与 F.1 的另一处必要偏差：TYPE 通道
----------------------------------
F.1 在函数内读 `!pkpmjwdType`（单 !）。PML 单 ! 变量只在定义作用域可见，
跨作用域须用双 ! 全局。本函数读 `!!pkpmjwdType`（undefined ⇒ '?'）；
调用方两个名字都赋值，兼容两种作用域模型。
defined()/undefined() 出处：nucdesogwall.pmlobj:206 / tginjectdesignmenu.pmlfnc:16,33。

自测
----
`python test\\check_uniquify_logic.py` —— 用 Python **复刻逻辑**做单元自测
（含任务指定场景：库里已有 NAME、NAMEre ⇒ 返回 NAMEre2；19 项断言）。
**这是逻辑等价复刻，不是 PML 实机**：本包全程未启动 PDMS、未部署
（§p.10：不运行 install/deploy、不改 D:/AVEVA、不写 G 盘）。
"""

open(P, 'wb').write((text + SECTION).encode('utf-8'))
print('已追加，README.txt 现在 %d 字节' % os.path.getsize(P))
