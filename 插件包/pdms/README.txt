pdms/ —— PDMS 端 PML 包（**GBK 无 BOM + CRLF**）
==============================================

计划文件（S2 实施包负责；本目录为其落点）
----------------------------------------
  pkpmjwd_import.pmlfnc    执行 Python 生成的 .mac（或直接读 PDMSDUMP 文本建结构）
  pkpmjwd_export.pmlfnc    遍历 STRU/FRMW/SBFR/SCTN/PANE/STWALL → 写 PDMSDUMP 文本
                           格式契约见 spec/CONTRACT.md §c（首行 #PKPM-JWD-PDMSDUMP 1.0）
  pkpmjwd.pmlfrm           操作窗体（选文件 / 勾选构件类别 / 基点与转角 / 导出）
  pkpmjwd_run.mac          命令行入口示例（$S- … $S+ 包裹）

必须遵守
--------
  * 编码 **GBK 无 BOM**、换行 **CRLF**；含中文注释时尤其如此（否则 PDMS 报 CP Syntax Error）。
  * 只允许使用 spec/CONTRACT.md §d.3 列出的语法（每条都带本机 PDMS 安装内的文件+行号出处）。
    新增语法必须先改契约并给出出处，禁止自造。
  * 导出文本的每个字段含义与顺序必须与 §c 完全一致；`UNITS` 行缺省 mm。
  * 不改 PDMS 安装内任何既有文件（安装动作集中在 install/）。
  * 界面文字用中文；窗体风格可参考本机既有做法（PMLLIB\mypml\forms\*.pmlfrm）。

参考（本机只读）
----------------
  D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB\mypml\forms\StlGrating.pmlfrm        板/SCTN 的建法
  D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB\design\functions\sctlcrelem.pmlfnc     SPREF/SPRE 归属
  D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB\mypml\forms\GRIDDESIGN.pmlfrm          层级与命名
  D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB\MYTOOLS\test\Tekla2PDMS\sdnf\functions\sdnfinver3.pmlfnc
                                                                        SCTN 全属性清单（最同构）

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
  * `mds\common\functions\output.pmlfnc:32-36`   `OUTPUT` 可在 `define function` 里执行
  * `mds\design\objects\mdshealthchkdata.pmlobj:1193,1195`、`pipefabricationmanager\design\objects\pfpipeconsistencycheck.pmlobj:113-120`
                                    `ALPHA FILE` / `ALPHA FILE END` 在 `.pmlobj` 里的实例与全路径写法
遍历侧（`CATA/SPWL/STSE/STCA/TEXT/DTSE/DATA/PTSE/PLIN/GMSE/SPRF/SPEC/SELE/SPCO` 类型码 + 集合函数）：
  * `common\functions\collectallfor.pmlfnc:35`、`findspecworlds.pmlfnc:41`、`findspecs.pmlfnc:56`、
    `admin\forms\admdbset.pmlfrm:224`（表达式可空）
  * `paragon\objects\cgeocataupgrade.pmlobj:282`（目录 = `CATA`）、`:510`（`PLIN`）
  * `paragon\forms\catcreate.pmlfrm:138-179,187-235`、`paragon\objects\catrefdata.pmlobj:263-292`（两张 elementTypes/longTypes 表）
  * `paragon\objects\catdtseelement.pmlobj:140,148,590`（`DATA`）、`catgetelement.pmlobj:240,339`（`TEXT`）
  * `common\functions\clock.pmlfnc:31,34`、`common\objects\clock.pmlobj:23-38`、
    `common\functions\dbchangesinit.pmlfnc:50,60-73`（日期文本）

与 `_recon/db_pdms_catalogue.md` §1.3 的一处不一致（以本机安装为准）
-------------------------------------------------------------------
该表把 `CATALOGUE` 对到代码 `CATE`；本机安装里 **`CATA` 才是 Catalogue**：
`paragon\forms\catcreate.pmlfrm:142` `elementTypes[5] = |CATA|` 对应 `:192` `longTypes[5] = |Catalogue|`，
且 `paragon\objects\cgeocataupgrade.pmlobj:282` `var !catas collect all CATA`、`:283` 后接
`NEW CATA`；`CATE` 的标签是 `:206` 的 `|Category|`。本函数按 `CATA` 取目录。

未实机验证（**必须先跑一遍再依赖**）
------------------------------------
1. `alpha file` / `output` 在 `define function` 里的可执行性（本机只有 .pmlobj/.pmlfrm 里的实例；
   函数里的实例是 `mds\common\functions\output.pmlfnc:35` 的 `output oldformat ce`）。
2. 产物行分隔符（未见 ALPHA FILE 产物的字节样本；契约只要求读方能吃 LF/CRLF）。
3. 在 Paragon 之外（如 Design）运行时 `collectAllFor` 的 `dbType` 范围 —— 若根数=0，函数会
   返回 `ERR|没有找到可导出的根…`，此时请进 PARAGON（`pdms.bat Paragon`，内部 `des.exe -module=81`）
   并打开 Catalogue 库后重跑。

替代路径（上面任一条不成立时）
------------------------------
1. **官方 GUI 途径（零代码）**：Paragon → 菜单 `Utilities → DB Listing...`
   （`PMLLIB\paragon\forms\appcatmain.pmlfrm:189` `'DB Listing...' … call !!displayOutput('Datal')`）
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

【R3 新增（契约 §o / 附录 F；S2 落点，**尚未实现**）】
  pkpmjwduniquename.pmlfnc   `define function !!pkpmjwdUniquename(!base is STRING) is STRING`
                             命名唯一化：候选 `原名 → 原名re → 原名re2 … 原名re99`（共 100 个），
                             占用判定 = `VAR !probe EXIST /$!cand` + `handle (2,109)`
                             （出处 abaarealib.pmlfrm:107-114；备选 NEW+handle(41,12)
                             abaarea.pmlfrm:523-528）；改名记录进全局 `!!pkpmjwdRenames`
                             （`TYPE|原名|实际名`，FAIL 条目以 `'FAIL|'` 开头）；候选耗尽返回
                             空串 ⇒ 宏内故障注入中止（§o.4/§o.5）。逐字夹具 = 契约附录 F.1/F.2。
  * 用户对用户的最终入口是 **pdms-net/ 的 .NET 窗体**（契约 §p，S8 落点）：PDMS 原生菜单
    「PKPM JWD」→ 窗体；本目录的 PML 窗体/宏保留为开发与无 .NET 环境的执行路径。
  * v1 的 install/（PML 菜单注入）自 §p.8 起为 legacy，文件保留不删。

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
（$M 加载 %PMLLIB% 下 .pmlfnc 的本机出处：admin\forms\adminapplic.pmlfrm:205）；
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
      assembly\functions\assybuildname.pmlfnc:47-50,64-65（VAR 后直接 .eq('FALSEA')，无 handle）、
      aba\Forms\abaarealib.pmlfrm:304-306（.eq('TRUEA') ⇒ "already exists"）、
      aba\Forms\abauserview.pmlfrm:859-860、TIANGONG\functions\tgautonum.pmlfnc:34-41；
  (b) 错误捕获：VAR 包在 handle (2,109)（Undefined name）——
      aba\Forms\abaarealib.pmlfrm:107-114（注释原文 -- Undefined name）。
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
`python test\check_uniquify_logic.py` —— 用 Python **复刻逻辑**做单元自测
（含任务指定场景：库里已有 NAME、NAMEre ⇒ 返回 NAMEre2；19 项断言）。
**这是逻辑等价复刻，不是 PML 实机**：本包全程未启动 PDMS、未部署
（§p.10：不运行 install/deploy、不改 D:/AVEVA、不写 G 盘）。
