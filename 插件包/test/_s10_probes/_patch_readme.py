# -*- coding: utf-8 -*-
"""在 pdms/README.txt 末尾追加「导出数据库（目录/规格）」一节（UTF-8 无 BOM + LF，与原文一致）。"""
import os

P = r'D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\pdms\README.txt'
raw = open(P, 'rb').read()
text = raw.decode('utf-8')
assert '\r\n' not in text, '原文不是 LF'
assert text.endswith('\n'), '原文末尾值得确认'

SECTION = """
导出数据库（目录/规格）—— pkpmjwddbexport.pmlfnc
================================================

做什么
------
把当前 PDMS 的 **Catalogue（目录）** 与 **Specification（等级/规格）** 导出成一份
`DB Listing` 文本，与用户原件 `PKPM（PDMS数据库）.txt` 同格式，供 Python 侧
`engine/dbparse.py` 解析（契约 v2 §l.5 的 12 条解析规则、§D.4 夹具）。

入口（PML，双击或命令行）
------------------------
  !!pkpmjwddbexport( <输出文件全路径> )       缺省入口：自动遍历根 + 缺省选项
  !!pkpmjwddbexportWith( <文件>, <根串>, <选项> )  显式给根（空格分隔的元素全名）与选项
  !!pkpmjwddbroots()                          遍历出根：全部 CATALOGUE(CATA) + 全部 SPWLD(SPWL)
  !!pkpmjwddbinventory()                      按类型计数（预检 / 给 dbparse 做地面真值核对）
  !!pkpmjwddbcounts( <元素> )                 某容器的直接子元素按类型计数
窗体 `pkpmjwd.pmlfrm` 的「③ 导出目录/规格」按钮就是调 `!!pkpmjwddbexport`；
返回值形如 `OK|file=…|bytes=…|roots=…|cata=…|spwl=…|sprf=…|spco=…|first=…`。

怎么做的（关键：不是手写这份文本）
----------------------------------
这份文本是 PDMS **核心 DATAL/DATALOG 引擎**的产物，有 24 条文本级坑（`$` 续行、纯值续行、
类型全名/缩写混用、`OLD` 无 `END`、`END` 可省、词值含空格不加引号、`PPRO ( ATTRIB DESP[n] )`
表达式、`NARE`/`PSTR`/`GSTR`/`DTRE`/`CATR` 的「序号+宿主」引用、`LOCK` 零值属性……逐条带
样本行号见 `_recon/db_pdms_catalogue.md` §5.3 坑清单 1..24）。手写 PML 属性 dump 无法稳定复现它。

因此本文件**照抄 PDMS 自己的做法**：`rptoutput.pmlfrm` 也只是「ALPHA FILE 打开输出文件 +
写头尾注释 + 核心 `OUTPUT` 命令出正文」的包装 ——
  * `rptoutput.pmlfrm:707,737`      `OUTPUT $!options $!itemsText`（正文由核心写，含 `INPUT BEGIN/END/FINISH`）
  * `rptoutput.pmlfrm:724-729`      头部 6 行 `WRITEALPHAFILE`（本函数逐字照抄）
  * `rptoutput.pmlfrm:3584-3596`    尾部 `footerComment()` 9 行（逐字照抄）+ `:744` 的注释行
  * `rptoutput.pmlfrm:2887`         `ALPHA FILE "<文件>" <模式>`
  * `rptoutput.pmlfrm:2302-2307,734-737`  传给 `OUTPUT` 的是元素 **fullName**（不是 name）
  * `rptoutput.pmlfrm:691` + `rptoutputopts.pmlfrm:144-163`  选项构成与 AVEVA 默认值
    （standard+udas+connections ⇒ 不写 `PASS/NOUDA/BRIEF`；`TABULATE` 用 `' 0 '` ⇒ 产物无缩进，
    与用户样本 `PKPM（PDMS数据库）.txt` 的零缩进一致）
  * `nucdesooutput.pmlobj:52-79`    非窗体 PML 里 `alpha file` / `writealphafile` / `output` 的实际用法
    （两遍式：`output pass 1` = `NEW…END`，`pass 2` = `OLD…`）
  * `mds\\common\\functions\\output.pmlfnc:32-36`   `OUTPUT` 可在 `define function` 里执行
  * `mds\\design\\objects\\mdshealthchkdata.pmlobj:1193,1195`、`pipefabricationmanager\\design\\objects\\pfpipeconsistencycheck.pmlobj:113-120`
                                    `ALPHA FILE` / `ALPHA FILE END` 在 `.pmlobj` 里的实例与全路径写法
遍历侧（`CATA/SPWL/STSE/STCA/TEXT/DTSE/DATA/PTSE/PLIN/GMSE/SPRF/SPEC/SELE/SPCO` 类型码 + 集合函数）：
  * `common\\functions\\collectallfor.pmlfnc:35`、`findspecworlds.pmlfnc:41`、`findspecs.pmlfnc:56`、
    `admin\\forms\\admdbset.pmlfrm:224`（表达式可空）
  * `paragon\\objects\\cgeocataupgrade.pmlobj:282`（目录 = `CATA`）、`:510`（`PLIN`）
  * `paragon\\forms\\catcreate.pmlfrm:138-179,187-235`、`paragon\\objects\\catrefdata.pmlobj:263-292`（两张 elementTypes/longTypes 表）
  * `paragon\\objects\\catdtseelement.pmlobj:140,148,590`（`DATA`）、`catgetelement.pmlobj:240,339`（`TEXT`）
  * `common\\functions\\clock.pmlfnc:31,34`、`common\\objects\\clock.pmlobj:23-38`、
    `common\\functions\\dbchangesinit.pmlfnc:50,60-73`（日期文本）

与 `_recon/db_pdms_catalogue.md` §1.3 的一处不一致（以本机安装为准）
-------------------------------------------------------------------
该表把 `CATALOGUE` 对到代码 `CATE`；本机安装里 **`CATA` 才是 Catalogue**：
`paragon\\forms\\catcreate.pmlfrm:142` `elementTypes[5] = |CATA|` 对应 `:192` `longTypes[5] = |Catalogue|`，
且 `paragon\\objects\\cgeocataupgrade.pmlobj:282` `var !catas collect all CATA`、`:283` 后接
`NEW CATA`；`CATE` 的标签是 `:206` 的 `|Category|`。本函数按 `CATA` 取目录。

未实机验证（**必须先跑一遍再依赖**）
------------------------------------
1. `alpha file` / `output` 在 `define function` 里的可执行性（本机只有 .pmlobj/.pmlfrm 里的实例；
   函数里的实例是 `mds\\common\\functions\\output.pmlfnc:35` 的 `output oldformat ce`）。
2. 产物行分隔符（未见 ALPHA FILE 产物的字节样本；契约只要求读方能吃 LF/CRLF）。
3. 在 Paragon 之外（如 Design）运行时 `collectAllFor` 的 `dbType` 范围 —— 若根数=0，函数会
   返回 `ERR|没有找到可导出的根…`，此时请进 PARAGON（`pdms.bat Paragon`，内部 `des.exe -module=81`）
   并打开 Catalogue 库后重跑。

替代路径（上面任一条不成立时）
------------------------------
1. **官方 GUI 途径（零代码）**：Paragon → 菜单 `Utilities → DB Listing...`
   （`PMLLIB\\paragon\\forms\\appcatmain.pmlfrm:189` `'DB Listing...' … call !!displayOutput('Datal')`）
   → `rptoutput.pmlfrm` 表单 → `Add → CE/List` 选 `CATALOGUE /PKPM_USER`、`SPWLD /PKPM_USER_SECTION`、
   `CATALOGUE /PKPM_STSS`、`SPWLD /PKPM_LIB`（以及 `/PKPMDATA`）→ 目标切 `File` → `Apply`。
   这条途径产出的就是 dbparse 要的格式（用户两份原件就是这么来的，文件名默认 `DBOutput.txt`）。
2. **PML 直读目录对象（比文本更稳，但要另写映射）**：`_recon/db_pdms_catalogue.md` §5.4(c) 列了
   Paragon 的包装器（`catcateelement/catdtseelement/catptseelement/catgmseelement/catscomelement/…`），
   可在 PDMS 里把目录读成结构化数据（CSV），完全绕开文本坑；代价是 dbparse 之外要再写一条读入通道。
3. **不建议**：自己用 PML 逐属性拼这份文本（就是本文件头说的 24 条坑，做不到与核心一致）。

命名与占位说明
--------------
本目录上方「计划文件（S2 实施包负责）」一节的三个文件名是架构包的计划名；
本次（实施包⑩）按任务要求交付的实际文件名是：
  `pkpmjwdexport.pmlfnc`（几何导出）、`pkpmjwd.pmlfrm`（窗体）、`pkpmjwdrun.mac`（入口宏）、
  `pkpmjwddbexport.pmlfnc`（本文件所述的目录/规格导出）。
"""

open(P, 'wb').write((text + SECTION).encode('utf-8'))
print('已追加，README.txt 现在 %d 字节' % os.path.getsize(P))
