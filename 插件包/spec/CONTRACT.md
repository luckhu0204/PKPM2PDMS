# PKPM-JWD导入导出 —— 唯一接口契约（CONTRACT v3 = v1 + R2 + R3）

> 本文件是**全部实施包**唯一 的接口依据。任何模块间交互都必须通过本文件定义的
> 函数签名与数据结构；任何未在本文件出现的字段名、状态码、文件格式、
> PDMS 语法、命名规则都**不得**由实施者自行发明——需要新增时先改本文件（见 §0.3）。
>
> 契约版本：`CONTRACT_VERSION = "1.0"`（与 `engine/canonical.py` 的常量一致；
> **R2/R3 追加章节是增量、不推翻任何 v1 条款**，故机器可读常量保持不变，理由见 §0.4 末）
> 编制日期：2026-09-23；R2 修订：2026-09-24；R3 修订：2026-09-25
> 工作区：`D:\AI_Work\PKPM数据解析`；交付包：`PKPM-JWD导入导出\`
>
> **R3 新增章节索引**（两项追加需求：①重名唯一化（加 `re` 后缀）②PDMS 原生插件（.NET + PML 混写）；
> 四条硬边界：**不部署、不启动 PDMS、不写 G 盘、不改 `D:\AVEVA`**）：
> §(o) 命名唯一化 · §(p) PDMS 原生插件 · §(q) 验收标准 15–19 · §12 第 26–29 行 · 附录 F/G

---

## 0. 本契约的地位、证据与变更

### 0.1 三份侦察报告是**结论来源**，本文件是**可执行条款**

| 报告 | 本契约引用的章节 |
|---|---|
| `_recon/jwd_format.md` | §1（表级规范）、§2（外键与 ID 空间）、§3（ShapeVal 解码）、§4（单位与 Z 推导）、§5（标准层 vs 自然层）、§7（属性表）、§8（规范模型与公式）、§9（编码与未解项） |
| `_recon/pdt_format.md` | §0–§2（节/记录/字段词法）、§3（ID 编码）、§5（TYPE/SHAPE 词表）、§7（规范模型）、§9（异常清单） |
| `_recon/pdms_target.md` | §4（截面匹配文件全解析）、§5（目录宏结构）、§6（PDMS 建模惯用法，逐条带安装内文件行号）、§7（编码纪律）、§8（导出方案） |
| `_recon/db_pdms_catalogue.md` **〔R2〕** | §1（目录宏文法与头尾逐字来源）、§2（依赖顺序与两遍式）、§3（参数化链 6 环节）、§4（2,920 条 SPRFILE 的族/名/参数）、§5（逆向解析方案 + 24 条坑）、§6（生成方案与最小模板）、§6.4（重跑幂等性/清场范式） |
| `_recon/db_pkpm_sections.md` **〔R2〕** | §1（`USERSTL.LIB` 不可用作数据源）、§2（族码总表）、§3（`$DEFFRAMESECTION` 字段与 DLL 格式串）、§4（`.jwd` Kind/ShapeVal 反算）、§5（双向映射路径与信息损失）、§6（材料）、§7（缺口清单）、§8（分级清单） |
| `_recon/dbsect/pkpm_pdms_section_table.csv` / `.json` / `pkpm_pdms_section_conflicts.md` **〔R2〕** | 机器可读转化表（3,176 行 × 38 列）与冲突报告；本包内置表 `engine/section_table.csv` 的唯一来源 |
| `_recon/net_addin_feasibility.md` **〔R3〕** | §1（PDMS 可引用程序集清单）、§2（csc 3.5 编译器与最小桩实测）、§3（IAddin/Command 精确 API 签名、PML↔.NET 双向桥）、§4（注册三件套：DesignAddins.xml + **DesignCustomization.xml** + .uic；目标框架匹配）、§6（可照抄骨架：TGTEXT）、§7（证据目录与只读声明） |

**证据分级**（沿用侦察报告的标注，本契约全部沿用，不得在实施中把「推断」当「事实」）：

* **【事实】** 有文件/字节/SQL 级直证 —— 可直接编码。
* **【推断】** 由证据推得但机理未证实 —— 可编码，但必须在 `report.json` 的
  `assumptions` 里留痕，且**不得**写成对用户可见的确定性结论。
* **【未知】** 明确未解 —— **禁止猜测**：一律走「报出 + 落报告」的路径（§e 第 4 条）。

### 0.2 本文件自己跑过的核对（不是转述）

下列命令在本次会话中实际执行，输出见附录 C：

| # | 命令 | 用途 |
|---|---|---|
| C1 | `python test\probe_samples.py` | 截面匹配文件与 JWD 的字节级事实（编码/换行/行数/右值缺斜杠/表清单/层标高/中文字节） |
| C2 | `python test\probe_samples2.py` | 匹配文件左值唯一性（2836 条 0 重复）、规格前缀 53 个、JWD 46 张 `pkpm*` 表 |
| C3 | `python test\probe_kind26_keys.py` | Kind=26 的候选键命中（`Name` 7/8；`<子类型>-<Name>` 补齐 `[18a`） |
| C4 | `python test\test_contract_selfcheck.py` | `canonical.py` 的 JSON 往返、真实 JWD 上 `validate()` 无 `E-` 项、ShapeVal 解码与候选键规则 8/8、3/3 命中 |
| C5 | `python test\check_dump_grammar.py` | §c.4 夹具按 §c.3 规则解析（含 `desp` 可为 0 个 / 由尾部 10 token 反推 / PANE `~` 尾部 / STWALL 12 token 全部 OK） |
| C7 **〔R2〕** | `python test\probe_v2_shapes.py` | ① `1_PM.pdt` 逐段行式（repr，含缩进/小数位/EXI/EXR 形态）；② `PDMSxCA_Addin121.dll` 内 `.pdt` 格式串（按偏移取 UTF-16LE，逐字）；③ 侦察转化表规模/列/唯一性/取值域 |
| C8 **〔R2〕** | `python test\probe_v2_table_keys.py` | 转化表的键与重复分析（得出「非空 `pkpm_name` 唯一 + `pdms_spec_path` 唯一」⇒ `SectionRec.key` 规则） |
| C9 **〔R2〕** | `python test\probe_v2_exr_wrap.py` | `EXR`/`EXI`/`NETID`/`SLABID` 的行长与折行：EXR **每行最多 10 组**（首行缩进 7、续行缩进 8，最长 149 列）、`SLABID` **每行 20 个**（续行缩进 11，最长 169 列）、`$DEADLOAD` 分组头**紧随**其首个子段头 |
| C10 **〔R2〕** | `python test\build_section_table.py` | 从侦察转化表生成 `engine/section_table.csv`（3,176 行）+ `section_table.meta.json`（含 sha256）；抽查 `HN450X200` 的 dims 与 `.jwd` 样本逐项一致 |
| C11 **〔R2〕** | `python test\check_v2_contract.py` | v2 自检：内置表可加载/键唯一/与样本一致、`encode_shapeval` 回算与样本逐字一致、契约内宏模板 `NEW`:`END` 平衡与依赖顺序、`$DEADLOAD` 段头齐全 |
| C12 **〔R2〕** | `python test\probe_v2_kind303_slots.py` | `.jwd` 样本 3 条 `Kind=303` 的 ShapeVal 原文与槽位下标（标定 §k.3 的槽位算法：`18/20=d`、`27=库族码`、`30=mat`、`32`=形状码、`81=-1`、`82=ID`、`split_len=84`） |
| C13 **〔R3〕** | `python test\check_v3_csc_probe.py` | §p.2 编译命令的**实测**：csc 3.5 + `/platform:x86` 编译最小 IAddin 桩 ⇒ 退出码 0、产物 CLR=v2.0.50727、PE machine=I386；顺带旁证样例 `TGTEXT.dll`（备份副本）同为 CLR2/x86；并核对编译前后 `D:\AVEVA` 监视文件零变化 |
| C14 **〔R3〕** | `python test\check_v3_notouch.py snapshot / verify` | 无接触基准：`G:\…\PKPM导入导出插件`（递归 751 文件）与 `D:\AVEVA\Plant\PDMS12.1.SP4`（顶层 645 文件）的 size+mtime+sha256 清单；verify = 0 added / 0 removed / 0 changed |
| C15 **〔R3〕** | `python test\check_v3_contract.py` | v3 自检：附录 F 的 PML 函数/`.uic`/宏片段夹具静态断言（唯一化候选序列与上限、占用探测写法出处、`.uic` 与 tgtext.uic 逐条同构、`renames` 报告键）、CONTRACT.md 表格列数 |

> **与侦察报告的一处数字差异（以本次实测为准）**：`jwd_format.md` §0 记「43 张 `pkpm*` 表
> （21 非空 + 22 空）」。C2 实测 `sqlite_master` 中 `type='table'` 共 **46** 张、全部以 `pkpm` 开头
> （21 张非空、**25** 张空，非空表合计 6,480 行）。差异只影响「要建多少张表」这一个动作，
> 契约按**实测 46 张**执行（DDL 见 §b.3）。

### 0.3 变更规则

1. 实施过程中发现契约有误/有缺，**先在 `spec/` 下增补条文**（本文件是唯一入口），再改代码；
2. 实施者**不得**单方面扩展字段名、状态字符串、文件行标记、PDMS 命名或语法；
3. 新增的 PDMS 语法必须给出**本机安装内的文件+行号**出处（§d 的引用风格），否则视为自造，禁止使用。

### 0.4 契约变更记录（每次变更在此追加一条；含授权方与证据）

> 本节的每条都是**经项目编排方（工作流 owner）授权**的修订，不是实施者自拍板。授权原文与
> 证据一起存档在 `docs/推断项_Kind3圆形截面.md`。

| # | 日期 | 变更 | 授权 | 证据 | 影响面 |
|---|---|---|---|---|---|
| 1 | 2026-09-24 | 新增 `status='inferred'`（§e.1a/§e.3）：`Kind=3` 单尺寸截面按**证据**判为圆形族 `/USER_CIRCLE-SPEC/Circle_Profile` + `DESP <d>`；`Resolution` 增加 `evidence` 字段；§12#5 由「unresolved + 候选键」改为「inferred」 | 编排方明确授权（本工作流「集成修理工」轮的裁决） | ① `1_PM.pdt:2387-2388` `ID=1009, NAME=圆形4800, SHAPE=3` + `KIND=3, B1=4800`（B1=直径）；② 同一 JLCJ2 模型把「薄壁方钢管: B20」归 `Kind=303`（`pkpmBraceSect` ID=62965）⇒ 排除方管；③ 目录宏 `PKPM（PDMS数据库）.txt:2494,2502-2513,3026`：`/USER_CIRCLE` 的 DTSET 只有**一个**参数 `DKEY D / PTYP DIST / PPRO ( ATTRIB DESP[1] ) / DPRO ( 300 ) / NUMB 1`；④ 用户匹配文件 `PKPM转PDMS截面匹配文件.txt:27` `CIRCLE, /USER_CIRCLE-SPEC/Circle_Profile` | 样本 JLCJ2 的 12 根屋面水平支撑（`pkpmBraceSect` ID=32335）；不影响已 `resolved`/`parametric` 的截面 |
| 2 | 2026-09-24 | §d.4-3 的 `DESP` 写出条件改为「只要 `Resolution.desp_params` 非空就写出」（不再以 `status='parametric'` 为前提） | 同上（同一条裁决的第 4 点，编排方标注为**强制**） | `/USER_CIRCLE` 的 `DPRO ( 300 )`：不写 `DESP` 会按默认直径 300 建出来，几何直接错 | 同上；对 `desp_params=[]` 的 `resolved` 截面行为不变 |
| 3 | 2026-09-24 | §e.4 增加补充文件的**指令行** `@FAMILY <kind> = <族键\|none>`（唯一允许的非 `左值,右值` 行形式） | 同上（同一条裁决第 5 点：映射必须是**数据**、可一行改回 `unresolved`） | 契约自身 §e.3 对 `Kind=3` 的旧句「若 `secmap_extra.txt` 给出候选键则按其结果」已把该决定委托给补充文件 | `engine/secmap_extra.txt`；用户原件不含指令行（§g 禁止改原件） |
| 4 | 2026-09-24 | **R2 三项追加需求落地**：新增 §(j) `.pdt` 写出、§(k) 截面库核心 `sectionlib`、§(l) 目录/规格宏双向（`dbmacro`/`dbparse`）、§(m) 命令行 v2、§(n) 安全与范围；**荷载明确不做**（不导出/不映射/不新建，`.pdt` 只写段头）；§(g) 增两行编码；§12 增第 15–24 行；附录 D/E 新增；内置转化表落 `engine/section_table.csv` | 用户追加需求（本工作流 R2 轮） | 用户原文三项要求 + `计划_JWD导入导出.md` §9 R2（验收 9–14、风险 R7–R12）+ `_recon/db_pdms_catalogue.md` + `_recon/db_pkpm_sections.md` + `_recon/dbsect/*`（本次 C7–C11 逐条复核） | 新增 4 个模块（`pdt_write.py`/`sectionlib.py`/`dbmacro.py`/`dbparse.py`）+ 数据文件 `engine/section_table.csv`；`cli.py` 增 6 个子命令；`pdt_read.py` 需按 §j.4.5 增补 `TYPE=3 → 'brace'` |
| 5 | 2026-09-24 | `$SETELEMENT.TYPE=3` **冻结为「支撑（brace）」**，并要求 `pdt_read` 同步映射（水平/竖向由几何判定，同 §d.4-2 的 HBRACE/VBRACE 规则） | 编排方 R2 需求「PDT 要完整导入+导出」要求构件集合不丢 | 样本只有 `TYPE∈{1,2}`（`pdt_format.md` §5.1【事实】）。若把支撑写成 1/2 ⇒ 静默改类型；写成其它未映射值 ⇒ 现实现的 `pdt_read`（`engine/pdt_read.py:471` 「其余 TYPE 不进 members」）会**丢构件**。两端必须约定同一个码 | `engine/pdt_read.py`（映射 + notes 文案）、`pdt_write.py`；§12#15 留痕 |
| 6 | 2026-09-24 | 板/墙截面的 `.pdt` 表达冻结：`NAME=T<厚度%g>`、`TYPE=1`、`T2=0.00`、ID 由 §j.3 发号；`$DESIGNPARA` 只写**原样文本或全 0 占位**（不解释语义） | 编排方 R2 需求；与 v1 §e.1 候选键 3（`T<厚度>`）一致 | `pdt_format.md` §2.7【事实】`NAME=T600/T120/T100`、`T1=600.00`；§4 `$DESIGNPARA` 逐项含义【未确证】⇒ 禁止臆造 | `pdt_write.py`（`$DEFWASLABSECTION`）、报告 `assumptions`；§12#23 |
| 7 | 2026-09-24 | 目录宏生成器默认容器名冻结为 `/PKPM_JWD_USER`、`/PKPM_JWD_STSS`、`/PKPM_JWD_USER_SECTION`、`/PKPM_JWD_LIB`；生成的宏内**禁止**出现用户既有容器名 | 编排方 R2 需求（风险 R8：不得动用户既有目录/规格） | 用户既有容器：`/PKPM_USER`、`/PKPM_STSS`、`/PKPMDATA`（`PKPM（PDMS数据库）.txt` 的 `NEW CATALOGUE`，本次 C7 复核 `NEW SPRFILE`×2,920 / `NEW SPCOMPONENT`×2,920）、`/PKPM_USER_SECTION`、`/PKPM_LIB`（同文件 `NEW SPWLD`，db_pdms_catalogue §0/§2.1） | `dbmacro.py` 的安全闸（l.1）+ 报告 |
| 8 | 2026-09-25 | **R2 验收第 1 轮两处修复**：① §k.2 的 `extra_json` 派生列增加 `dll_siblings`（见 k.2 表），使 §l.5 的 759 对大小写/写法差异被完整归类；② §l.3.4 冻结不变量「同一父级内同名 NEW 只出现一次」的落地方式：`dbmacro` 对参数化族**按规格路径去重**（一条规格只建一次 STCATEGORY/SPRFILE/SELEC/SPCOMPONENT；PARA 取第一条，共用事实与 PARA 冲突写 `warnings`） | 编排方验收门禁的失败反馈（"按契约 v2 修正实现……修法：同一规格只建一次族/SPRFILE/SPCOMPONENT，或给重复条目加唯一后缀"——取**前者**，后者会造出假规格名并破坏 §l.3.4-1 的 `path == <family>-SPEC/<sprfile>` 不变量） | ① recon `_dll_pairs_full.json` 显式对：`L25x16x3 ↔ 33,2,25,16,3`、`L45x28x3 ↔ 33,2,45,28,3`、`L50x32x4/L56x36x3/4/5 ↔ 33,2,…`；`_dll_tokens.json` 码后相邻 token：`6-B100*4.00`、`7-B120*80*4.00` —— 即 DLL 确有这些拼写，而源表把热轧行的 `dll_table_entry` 标成了冷弯拼写（`_recon/dbsect/pkpm_pdms_section_table.csv` 行 `L25X16X3`/`L45X28X3`/`L50X32X4`/`L56X36X3/4/5`/`6-B100*4.00`/`7-B120*80*4.00` 的 `dll_table_entry` = `3-L25x16x3`/…/`8-B100*4.00`/`9-B120*80*4.00`）；实测引擎 751 vs recon 口径 759、差额恰这 8 键、反向 0。② 样本 JLCJ2：14 根 Kind=1 梁/柱全落 `/USER_RECT-SPEC/Rectangle_Profile`、2 根焊接 H 落 `/USER_H-SPEC/H_Profile` ⇒ 旧宏同父级重名 4 处（jwd2db）/2 处（pdt2db） | `engine/section_table.csv`+`meta`（重新生成，3,176 行/机械列不变）、`test/build_section_table.py`、`engine/dbparse.py`（`_variant_index` 读 `dll_siblings`）、`engine/dbmacro.py`（规格去重） |
| 9 | 2026-09-25 | **R3 复核·high/medium 修复（dbmacro 侧）**：① §l.3.3 第二遍引用**全部带父级限定链**（见 l.3.3 模板与 §12#25）；② §l.3.5/§l.4 重跑策略：ONERROR 先于清场段；uniquify 缺省后缀到**秒**；`--clean` 的重建容器带新运行戳、绝不复用刚清场的名字；③ DTSET 的 `PURP=PARA` 行 `PPRO ( ATTRIB PARA[n] )` 的 n 改用 **PARA 组内序号**（与 NUMB 同一编号空间；原件 PKPM（PDMS数据库）.txt:3159-3204 为证），不再用全族位置 | 编排方 R3 复核清单（发现·high 安全④、发现⑤ a/b/c、发现③潜伏 bug） | ① 用户原件 L46778 `OLD PTSSET 1 of STCATEGORY /USER_XI`、L46779 两级链、PMLLIB isometricadp `OLD RRULE 1 of RRST /…`；风险事实：供应商源名与用户库同名并存（§l.4），实测生成（合成表）含 `NEW STCATEGORY /C_COMMON`+裸名 `OLD SPRFILE /[5`，而 `scan_forbidden_names` 只查 5 个容器名 ⇒ 返回 []。② 旧代码清场段在 ONERROR 前（dbmacro 旧 982-991）、DELETE CATE MEM 自注 UNVERIFIED 且只清成员、同日两次 resolve_containers 输出完全相同。③ 实测构造混合族 /USER_FOO（L(DESP1),h,b(PARA)）生成 `PPRO ( ATTRIB PARA[2 ] ) + NUMB 1`（应为 PARA[1]）；内置表 3,176 行无混合族 ⇒ 休眠 bug | `engine/dbmacro.py`（引用链/重跑/PPRO）、`engine/dbparse.py`（§l.5-6/9 的链解析：`_split_old_target`/`_old_target_name`/`_REF_RE`/`_register_comp`）、§l.3.3/l.3.5/l.4/l.5、§12#25 |
| 10 | 2026-09-25 | **R3 复核·medium 修复（pdt 侧）**：① §j.3 的全局流水号 N 落地（旧实现按类别各自从 1 起号，跨类复用 N，与样本「N 填满 1..2841 跨类 0 复用」及本模块 docstring 均不符）；② `write_pdt_sections`（full 骨架）段序改回 SEGMENT_ORDER（`$DEFFRAMESECTION` 不再提前）；③ §a.2 的 ecc 表增加 `.pdt` 源 6 元组行：`pdt_read` 原始记录 (ECS1..ECE3)（仅记录、不并几何）、`write_pdt` 原样写回 ⇒ .pdt→.pdt 往返不丢偏心字段；旧申报「start/end 已含偏心」对 .pdt 源不成立的理由已修正；④ §12#17/§k.3 的 M 规则改为按 SHAPE（1/3→6、39→mat=5）；⑤ `write_pdt_sections` 按 (NAME,SHAPE) 去重（消除 db2pdt.pdt 的 857 组重复定义） | 编排方 R3 复核清单（发现①a/①b、④、⑧、⑨） | ① rev2 实测 pdt2pdt_roundtrip.pdt 各段 N 都从 1 起、跨类复用 1046；样本同口径唯一 N=2051（pdt_format.md §3.2【事实】）。② rev4c：db2pdt.pdt 25 个段头序列 `$VERSION,$DESIGNPARA,$DEFFRAMESECTION,$STORY,…`，与 SEGMENT_ORDER/样本相悖。③ rev3d 直扫样本：非零偏心 = 121 根梁（TYPE=2，ECS1=ECE1=225/250），柱全 0；rev3c 实测 Member.ecc=() ⇒ 信息丢失；pdt_read 注释早已指出与 pdt_format.md §2.9 相反。④ 1_PM.pdt:2370(M=6,SHAPE=1)/:2515(M=5,SHAPE=39)；rev4：db2pdt.pdt M 分布 {5:1845} 含 SHAPE=1/3。⑤ rev4c：1,845 条记录仅 988 个唯一 (NAME,SHAPE)、重复组 857（Kind=303 同落 col+brace 两表所致） | `engine/pdt_write.py`（发号/段序/ECS/去重）、`engine/pdt_read.py`（ecc 记录）、`engine/sectionlib.py`（M 规则 + loss_items）、§a.2/§j.3/§12#17 |
| 11 | 2026-09-25 | **R3 追加需求（v3 章节）**：① 新增 §(o) 命名唯一化——PDMS 侧运行期函数 `!!pkpmjwdUniquename`（`pdms/pkpmjwduniquename.pmlfnc`），候选序列 `原名 → 原名re → 原名re2 … 原名re99`（上限 99，共 100 个候选），占用判定用 `VAR !x EXIST /<名>` + `handle (2,109)`（出处 abaarealib.pmlfrm:107-114），改名记录进 `!!pkpmjwdRenames` 并入 `report.renames`；② 新增 §(p) PDMS 原生插件——`.NET Add-in + PML 混写`（源码 `pdms-net/`、产物 `pdms-net/dist/`、程序集 `PKPMJWD`、Command Key `PKPMJWD.OpenTools`、编译命令 = csc 3.5 + `/platform:x86` **本轮实测通过**、注册三件套 + 备份/幂等/卸载恢复的 deploy 脚本、引擎以独立可执行文件由 .NET 进程调用 `--request` 模式）；③ 新增 §(q) 验收 15–19；④ 四条硬边界入 §(p.10)：**不部署、不启动 PDMS、不写 G 盘、不改 D:\AVEVA**；⑤ §(g) 增 `.cs/.cmd/.uic` 编码行；§(h) 增 `renames` 键；§12 增 26–29 行；附录 F/G 新增 | 用户 R3 追加需求原文（重名加 re / 要 PDMS 内原生插件 / 成品放工作区 / 全程不动 PDMS、交付完也不部署） | `_recon/net_addin_feasibility.md`（全文，行号见附录 F）；可照抄样例实测：`D:\AI_Work\pmds三维文字程序-备份\TGTEXT\`（13 文件全齐；**任务给的 `D:\AI_Work\PKPM三维文字程序\TGTEXT` 已不存在**——该目录在 2026-09-21 清库事故中消失，本契约一律改引备份副本并在附录 F 注明）、`D:\AI_Work\PDMS Copilot\src\CopilotAddin.cs`、`D:\AI_Work\PDMS二次开发\PDMSSpecBuilder\dotnet\TGSPEC\TGSPECAddin.cs`；PMLLIB 占用判定与 NEW 冲突惯用法（abaarealib.pmlfrm:107-114、abaarea.pmlfrm:523-528、abacrhierarchy.pmlfrm:116-120）；本轮 C13（csc 实测）/C14（无接触基准）/C15（夹具自检） | 新增 `pdms/pkpmjwduniquename.pmlfnc`（S2 落点）、`pdms-net/` 全套（S8 落点）、`MacOptions.uniquify`/`pml_func_path`、`cli.py --request` 模式、report.renames 键、`D:\AI_Work\PKPM数据解析\交付_PKPM-JWD插件\` 交付落点（S6/交付包落点）；不改变 v1/v2 任何既有行为 |
| 12 | 2026-09-25 | **R3 复核三项修复（§o/宏/文档）**：① §o.2/§o.4 的 TYPE 通道改为**双 ! 全局** `!!pkpmjwdType`（§o.4 模板与 F.2 同步）：旧文写单 !，而函数读双 ! 全局（pmlfnc:96-97），且全包无任何调用方赋过双 ! ⇒ 运行期 `defined(!!pkpmjwdType)` 恒假、每条改名记录 TYPE 恒 '?'（可追溯性缺陷，§o.7）；PML 作用域语义：单 ! 只在定义它的宏/函数作用域内可见，跨作用域传须双 !（与 `!!CE` 同理）。② §o.3/§o.4/F.1 的占用探测形态由 `EXIST /$!cand`（base 自带前导 / ⇒ 实际探成 `//名`，**全库 0 例**的未证实形态）改为 `EXIST $!cand`——**带斜杠名字的既有惯用法就是 `EXIST $!x`**（本机 62 处，如 tgautonum.pmlfnc:33-41、abauserview.pmlfrm:859-860）；`EXIST /$!x` 的 6 处直证里插值变量**均不带斜杠**；(2,109) 双结局语义出处（abaarealib:107-114）不变；§o.4 的故障注入行同改（空名 ⇒ `EXIST` 无名参数 ⇒ 非法，§12#27 语义不变）。③ `pdms-net/README.txt` §6 补记导出方向的 PML 依赖（窗体调 `!!pkpmjwdexport`，该函数由 install\\install.ps1 安装并由 pkpmjwdrun.mac $M 载入，deploy 只装 uniquename） | 编排方 R3 复核清单（发现②、③、①） | ① macgen.py:602 旧赋 `!pkpmjwdType`（单 !）vs pmlfnc:96-97 读 `!!pkpmjwdType`；check_type_channel2.py 全包扫描：`!!pkpmjwdType` 仅命中 pmlfnc 自身与沙箱副本。② check_exist_forms.py：PMLLIB `EXIST /$!x` 6 处（变量均无斜杠）vs `EXIST $!x` 62 处（带斜杠名字）；tgvalrename.pmlfrm:181 注释明写「不带斜杠」。③ Form:519-521 调 `!!pkpmjwdexport` 且判 `OK\|`；deploy:109-110 只复制 uniquename；install.ps1:67,262,330 复制/载入 pkpmjwdexport | `engine/macgen.py`（TYPE 行 + 故障注入行）、`pdms/pkpmjwduniquename.pmlfnc`（探测行 + 头注释）、`pdms-net/README.txt` §6、`test/check_v3_contract.py`（夹具断言对齐）、`test/acceptance_r3.py`（check_15 冻结要素 + check_20 守卫形态） |

> **`CONTRACT_VERSION` 为何仍是 `"1.0"`**：R2 的四项新增**全部是增量章节**（没有任何 v1 条款被推翻），
> 而 `CONTRACT_VERSION` 已进入 v1 的产物契约——`report.json` 的 `contract_version` 字段、
> `test/acceptance.py` 与 `test/test_contract_selfcheck.py` 都按 `"1.0"` 断言。
> 按 §0.3「不推翻 v1 条款」的精神，R2 期间**保持常量不变**；待 R2 四个新模块全部落地并通过门禁后，
> 由编排方统一提升为 `"2.0"`（届时需同步改 `canonical.py`、报告样例与本文件 §h 的示例）。

---

## (a) 规范模型 API（`engine/canonical.py`）

### a.1 单位与坐标系（全项目统一，模块之间不得再换算）

* 长度 **mm**；角度 **度**；力 **kN**、线荷载 **kN/m**、面荷载 **kN/m²**；
* **X = E(east)、Y = N(north)、Z = U(up)**，右手系，Z 向上；
* 平面坐标 `(x, y)` 与 PDMS 的 `(E, N)` 一一对应；`z` 与 `U` 一一对应；
* `canonical.py` 只依赖标准库；**禁止**引入第三方包。

### a.2 数据类（字段名与 `jwd_format.md` §8 一致；单位 mm / 度）

`jwd_format.md` §8 给出 `Level / Joint / Section / Member / Slab / Load / Model`。
本契约**逐字段采用**，并做两处**已声明**的调整（其余字段全部保留）：

1. **引用方式**：`Joint.level / Member.level / Slab.level / Wall.level` 存
   `Level.stdflr_id`（`int`），不再内嵌 `Level` 对象；取对象用 `Model.level(key)`。
   理由：JSON 往返与 5 个包之间的比对需要一个稳定可排序的键（§8 内嵌对象在
   `n` 个自然层共用 1 个标准层时会复制出互相不等的对象，无法做字节级比对）。
2. **补充字段**：为**写回 .jwd** 与**报表**所必需、§8 未列的字段（如 `no`、`shapeval`、
   `grid_id`、`hdiff_start/hdiff_end`、`spec_path`…），全部带默认值，见下表。

| 数据类 | 字段（`=` 后为默认值） | 单位/取值 | 说明 |
|---|---|---|---|
| `Level` | `stdflr_id:int`, `floor_id:int`, `no:int`, `z_bot:float`, `z_top:float`, `height:float`, `name:str=""` | mm | **两种形态**见 a.3 |
| `Joint` | `id:int`, `level:int`, `x:float`, `y:float`, `z:float`, `no:int=0`, `hdiff:float=0.0` | mm | `z = level.z_top + hdiff` |
| `Section` | `id:int`, `kind:int`, `mat:int`, `name:str=""`, `dims:dict={}`, `table:str=""`, `no:int=0`, `shapeval:str=""`, `params:list=[]`, `note:str=""` | — | `mat`：5=钢 6=混凝土 0=未知；`table∈{'beam','col','brace','pdt','dump','panel'}`；`dims`/`params` 见 a.4 |
| `Member` | `id:int`, `type:str`, `level:int`, `section:int`, `start:(x,y,z)`, `end:(x,y,z)`, `rotation:float=0.0`, `ecc:tuple=()`, `no:int=0`, `grid_id:int\|None=None`, `node_id:int\|None=None`, `jydef:str=""`, `hdiff_start:float=0.0`, `hdiff_end:float=0.0`, `material:str=""`, `jusl:str=""`, `meml:str=""` | mm / 度 | `type∈{'beam','column','brace'}`；`start/end` 是**最终几何**（已并入偏心与高差） |
| `Slab` | `id:int`, `level:int`, `polygon:list[(x,y)]`, `z:float`, `thickness:float=0.0`, `is_hole:bool=False`, `dead:float=0.0`, `live:float=0.0`, `grid_edges:list[int]=[]`, `no:int=0`, `spec_path:str=""`, `ori:str="YNZU"`, `sjus:str="dbot"` | mm / kN/m² | `polygon` **不闭合**（首尾不重复） |
| `Wall` | `id:int`, `level:int`, `thickness:float=0.0`, `z_bot:float=0.0`, `z_top:float=0.0`, `loop:list[(x,y,z)]`, `section:int=-1`, `no:int=0`, `name:str=""`, `spec_path:str=""`, `sjus:str="na"` | mm | **本契约新增**（§8 未列；见 a.8） |
| `Load` | `id:int`, `kind:str`, `target_id:int`, `values:tuple[float\|None]`, `raw:list[str]=[]`, `load_sect_id:int=0`, `level:int=0` | kN / kN/m | `kind∈{'beam-line','joint-point'}`；`values` 与 `raw` **等长** |
| `Resolution` | `spec_path:str=""`, `desp_params:list[float]=[]`, `status:str="unresolved"`, `reason:str=""`, `pkpm_name:str=""`, `source:str=""`, `evidence:str=""` | — | `status∈{'resolved','parametric','inferred','unresolved'}`（`'inferred'` 见 §e.1a/§e.3、变更记录 §0.4-1）；`evidence` 只在 `status='inferred'` 时非空（证据链文本，见 §e.5a） |
| `Model` | `levels:list[Level]`, `joints:dict[int,Joint]`, `sections:dict[int,Section]`, `members:list[Member]`, `slabs:list[Slab]`, `loads:list[Load]`, `walls:list[Wall]=[]`, `source:str=""`, `source_format:str=""`, `units:str="mm"`, `contract_version:str="1.0"`, `notes:list[str]=[]` | — | `source_format∈{'jwd','pdt','pdmsdump','json'}` |

**`ecc` 的分量布局**（原始值，**仅记录**，供报表与写回；几何真值看 `start/end`）：

| `type` | `ecc` 长度 | 含义 | 出处 |
|---|---|---|---|
| `beam` | 1 | `(Ecc,)` 梁中线相对轴线的横向偏移 | `pkpmBeamSeg.Ecc` |
| `column` | 2 | `(EccX, EccY)` | `pkpmColSeg.EccX/EccY` |
| `brace` | 4 | `(EccX1, EccY1, EccX2, EccY2)` | `pkpmBraceSeg` |
| **`.pdt` 源（任意 type）** | 6 | `(ECS1, ECS2, ECS3, ECE1, ECE2, ECE3)` **原始值**（全 0 时空元组） | §0.4-10：`pdt_read` 从 `$SETELEMENT` 原样记录（**仅记录**，方向语义未证实 ⇒ 仍不并入 `start/end`，§12#6）；`write_pdt` 对 6 元组原样写回 ⇒ `.pdt→.pdt` 往返不丢偏心字段 |

> **偏心正负方向未证实**（`jwd_format.md` §9.3#6）：**不得**在代码里断言方向语义；
> 非零偏心的构件必须逐条列入报告（§h 的 `geometry_anomalies`）。

### a.3 `Level` 的两种形态（同一数据类，用 `height` 区分）

| 形态 | 来源 | `z_bot` | `z_top` | `height` | `stdflr_id`/`floor_id`/`no` |
|---|---|---|---|---|---|
| **楼层型** | `.jwd` | `pkpmFloor.LevelB` | `LevelB + Height` | `pkpmFloor.Height` | `pkpmStdFlr.ID` / `pkpmFloor.ID` / `pkpmFloor.No_` |
| **平面型** | `.pdt`、`.pdmsdump`（按节点 Z 分组推导） | `z` | `z` | `0` | 按 `z` 升序从 1 开始编号 / `0` / 同名序号 |

* 【事实】`.jwd` 的**标准层平面画在层顶**：`pkpmSlab.VertexZ` 恒等于 `pkpmFloor.Height`，
  且「柱自层底竖直贯穿本层」是唯一自洽解（`jwd_format.md` §4.2/§4.3）。
  ⇒ **禁止**用 `pkpmStdFlr.Height`（样本恒 0）。
* 【事实】`.pdt` 的节点 Z 不等于层顶：11 个标高只有 5 个是 `$STORY.TL`，38 个节点
  `FLOORID` 与几何不符（`pdt_format.md` §8.3）。
  ⇒ `.pdt`/`.pdmsdump` **必须按节点 Z 分组建平面型 Level**，不得用 `FLOORID` 或只用 `$STORY`。

### a.4 `Section.dims` / `Section.params` 的**唯一**解码规则

```
params = [t for t in ShapeVal.split(',')]        # 先去掉尾部空串
params = params[1:-2]                            # 去掉首字段(Kind) 与尾部 (Mat, 自身ID)
```
* 【事实】三张截面表 28/28 行满足「末字段 == 本行 ID」「倒数第二字段 == `Mat`（Kind=303 写 −1）」
  「首字段 == `Kind`」（`jwd_format.md` §3.1；本次 C4 也验证了 28/28 全部解出）。
* `dims` **只写有证据的键**；证据不足的字段名一律写进 `Section.note`，禁止把推断当事实。

**Kind → `dims` 键表（本契约冻结）**

| Kind | 族 | `params`（下标从 0） | `dims` 键 | 证据等级 |
|---|---|---|---|---|
| 1 | 混凝土矩形 | `[0]=B, [1]=H` | `{"B":float,"H":float}` | **B/H 先后为【推断-中】**（`jwd_format.md` §9.3#4）→ `note` 必须写明 |
| 2 | 焊接工字形（钢） | `[0]=Tw,[1]=H,[2]=B1,[3]=T1,[4]=B2,[5]=T2` | `{"Tw","H","B1","T1","B2","T2"}` | 值集合【推断-高】；**B/T 交错序【未知】**（§9.3#5）→ `note` 必须写明 |
| 3 | 单尺寸钢截面 | `[0]=d` | `{"d":float}` | 【未知】族别（圆钢/圆管/方管）（§9.3#1）→ `note` 必须写明 |
| 26 | 型钢库（轧制） | `[0]=族码,[1]=子类型,[2]=H,[3]=0,[4]=B,[5]=tf,[6]=tw,[7]=0` | `{"family":int,"subtype":int,"H","B","tf","tw"}` | H/B/tf/tw 【事实】（8 条中 7 条与 PDMS 截面库独立吻合，§3.2）；槽钢的 tf/tw 待 GB 轻型表核对 |
| 303 | 用户参数化截面 | 见下 | `{"family":int,"spec_str":str,"d":float,"b":float,"lib_family":int}` | 【事实】（四重印证，§3.2/§3.3） |

**Kind=303 的两条解码规则（都必须实现）**

1. 具名槽位（`params` 下标）：`[0]=族码(样本=77)`、`[17]=d(边长/直径)`、`[19]=b`、
   `[26]=冷弯库族码`、`[29]=Mat`、`[31]=未知码(16672/16640，语义未解，禁止使用)`。
2. 打包规格串：`params[1..6]` = 6 个 16 位整数，**每槽按「低字节在前」拼两个 ASCII 字符**，
   遇 `0x00` 截断：

   ```python
   buf = bytearray()
   for t in params[1:7]:
       v = int(float(t or 0)); buf.append(v & 0xFF); buf.append((v >> 8) & 0xFF)
   spec_str = bytes(buf).split(b"\x00")[0].decode("ascii")
   ```
   【事实】本次 C4 用样本 3 行复原出 `B250*10.00` / `B200*10.00` / `D194X8.0`，
   与 `jwd_format.md` §3.2 的表一致（该表由侦察脚本独立算出）。

### a.5 由来源表推导的精确公式（`read_*` 必须照此实现）

```
Level.z_top        = pkpmFloor.LevelB + pkpmFloor.Height       # 平面标高
Joint.z            = Level.z_top + pkpmJoint.HDiff
Beam.start/end     = (GridID→pkpmGrid.Jt1ID/Jt2ID→Joint.(x,y), Level.z_top + HDiff1 / + HDiff2)
Column.start/end   = ( Joint.x + EccX, Joint.y + EccY, Level.z_bot + HDiffB ) → ( 同水平位置, Level.z_top )
Brace.start/end    = ( Joint1.(x,y) + (EccX1,EccY1), Level.z_top + HDiff1 )
                     → ( Joint2.(x,y) + (EccX2,EccY2), Level.z_top + HDiff2 )
Slab.polygon       = zip(pkpmSlab.VertexX, pkpmSlab.VertexY)   # TEXT 逗号分隔 → float
Slab.z             = Level.z_top        # 等价于 Level.z_bot + pkpmSlab.VertexZ（实测 VertexZ == Height）
Opening            = pkpmSlab WHERE RoomIsHole = 1   （pkpmSlabHole 自身忽略，它只是索引记录）
Section            = §a.4
Load               = pkpmLoadSect.ElementKind 分流：12→'beam-line'，−1→'joint-point'；target = pkpmLoadSeg.ElementID
```
* `Member.level` **一律取 `start` 端所属 Level**（柱=下端所在层；梁/支撑=起点所在层）。
* `Member.hdiff_start/hdiff_end` 存原始 `HDiffB` / `HDiff1`,`HDiff2`；柱的 `hdiff_end = 0`。
* 【事实】每根构件都是"一行段表"、`(StdFlrID, GridID)` 恒 1 行；节点/网格线/房间**每层独立**
  （`jwd_format.md` §2.4）——**禁止**跨层按 ID 合并「同一物理构件」。

### a.6 `Model.to_json() / from_json()`

| 项目 | 规定 |
|---|---|
| 编码 | UTF-8 **无 BOM**（写文件用 `open(..., encoding='utf-8', newline='\n')`） |
| 规范形式 | `to_json(indent=None)`：`ensure_ascii=False`、`sort_keys=True`、紧凑分隔符 `(',',':')` ⇒ **同内容必得同字节**，用于跨模块比对 |
| 人工阅读 | `to_json(indent=1)` 允许，但**不得**用于比对 |
| 键类型 | `joints`/`sections` 的 JSON 键是字符串化整数；`from_json` 必须还原成 `int` 键 |
| 元组 | 序列化成 JSON 数组，`from_json` 还原成 `tuple`（`start/end/ecc/values`） |
| 数值 | 用 `json` 默认的 `float.__repr__`，禁止自行四舍五入 |
| 便捷方法 | `Model.save_json(path, indent=None) -> str`、`Model.load_json(path) -> Model` |

### a.7 `Model.validate() -> list[str]`

**返回值语义**：问题清单（空列表 = 通过）。前缀固定：

* `E-` **致命**：外键不可解析 / 建模所依据的等式不成立 ⇒ CLI **必须中止**（退出码 3），不写产物；
* `W-` **可疑**：可继续建模 ⇒ **必须全部**写入 `report.json` 的 `geometry_anomalies`。

**检查项（全表，实现不得增删语义）**

| 前缀 | 触发器 |
|---|---|
| `E-LEVEL-DUP` | `Level.stdflr_id` 重复 |
| `E-LEVEL-NEG` | `z_top < z_bot` |
| `W-LEVEL-H` | 楼层型 Level 的 `z_top-z_bot != height` |
| `E-JOINT-LEVEL` | `Joint.level` 不可解析 |
| `E-JOINT-Z` | `abs(joint.z - (level.z_top + joint.hdiff)) > 1e-6` |
| `W-SEC-MAT` | `Section.mat` 不在 `{0,5,6}` |
| `W-SEC-NOIDENT` | 截面既无 `name` 又无 `dims`、`params`（**截面不可解析**，必落 unresolved） |
| `W-SEC-DIMS` | Kind∈{1,2,3,26,303} 但 `dims` 为空 |
| `E-MEM-TYPE` | `type` 不在 `{'beam','column','brace'}` |
| `E-MEM-LEVEL` / `E-MEM-SEC` | `Member.level` / `Member.section` 不可解析（**外键可解析**检查） |
| `E-MEM-ZERO` | `start == end`（零长度杆件） |
| `W-MEM-SHORT` | 杆长 `< SHORT_MEMBER_MM = 300`（报告阈值） |
| `E-MEM-Z` | `start.z != base + hdiff_start`，`base = level.z_bot`（柱）/ `level.z_top`（梁、支撑） |
| `W-MEM-Z-END` | `end.z != level.z_top + hdiff_end`（柱越层、斜置构件会触发） |
| `W-MEM-ZRANGE` | 端点 Z 超出 `[z_bot, z_top]` 超过 `Z_SLACK_MM = 10` |
| `W-MEM-ECC` | `ecc` 分量数与 a.2 的布局不符 |
| `E-SLAB-LEVEL` / `E-SLAB-POLY` / `E-SLAB-THICK` / `E-SLAB-Z` | 层不可解析 / **多边形顶点数 < 3** / 厚度为负 / `z != level.z_top` |
| `W-SLAB-DUP` | 相邻顶点重复 |
| `E-WALL-LEVEL` / `E-WALL-LOOP` / `E-WALL-SEC` | 层不可解析 / 回路顶点 < 3 / 截面不可解析 |
| `W-WALL-Z` / `W-WALL-LOOPZ` | `z_top <= z_bot` / 回路顶点的 U 不在 `{z_bot, z_top}` |
| `E-LOAD-KIND` / `E-LOAD-TARGET` | `kind` 非法 / 目标（构件或节点）不可解析 |
| `W-LOAD-VALUES` | `len(values) != len(raw)` |

**本契约的验收基线**：用 `JLCJ2.jwd` 装配出的 Model，`validate()` 必须返回 **0 个 `E-`**，
且恰含 `W-MEM-SHORT × 5`、`W-MEM-ZRANGE × 1`（本次 C4 实测）。其中 `W-MEM-ZRANGE` 那 1 条
就是 `BraceSeg.HDiff2=6650` 的异常支撑（`jwd_format.md` §9.3#7），**必须**能被报告看见。

辅助方法（等价、便于调用）：`Model.errors()`、`Model.warnings()`、`Model.counts()`、
`Model.used_sections()`、`Model.panel_thicknesses()`、`Model.sorted_levels()`、`Model.level(key)`。

### a.8 `Wall` 为什么在契约里（与 §8 的差异声明）

1. 任务 (d)(e) 要求 PDMS 侧建 `STWALL`（墙用 `SPRE`），而 (b) 的 `read_pdt` 必须能吃下
   `.pdt` 里**真实存在**的 4 面墙（`pdt_format.md` §2.10，`$SETWALL` 4 条）；
   `.jwd` 也有 `pkpmWallSeg/pkpmWallSect`（样本为空，**语义未解码**）。
2. 因此 `Wall` 必须进契约，否则 `.pdt` 的墙无处安放。
3. **但 v1.0 明令**：`read_jwd` **禁止**从 `pkpmWallSeg` 臆造墙 —— 遇到非空行必须
   逐条记入 `report.skipped`（`what="pkpmWallSeg"`，附行数与 ID），并把
   `status=unresolved` 的结论写进报告（`jwd_format.md` §1.7 明确「转换器需另行逆向」）。

### a.9 `Model.notes` 的用途

读取期的非致命问题/假设（例如：某个空表非空且未解码、某个字段取值超出词表、
某条记录被跳过）。**CLI 必须把 `notes` 全量并入 `report.warnings`**。
`read_*` 的函数签名里没有 report 参数，`notes` 就是唯一的信息回流通道。

---

## (b) 各模块函数签名（实施包之间**只允许**通过这些交互）

### b.1 一览表

| 模块 | 函数 / 类 | 签名 | 副作用 |
|---|---|---|---|
| `engine/jwd_read.py` | `read_jwd` | `read_jwd(path: str) -> Model` | 只读输入；不写任何文件 |
| `engine/pdt_read.py` | `read_pdt` | `read_pdt(path: str) -> Model` | 只读 |
| `engine/jwd_write.py` | `write_jwd` | `write_jwd(model: Model, path: str) -> dict` | 新建/覆盖 `path`（SQLite） |
| `engine/secmap.py` | `SectionMap` | `SectionMap.load(path: str, extra_path: str \| None = None) -> SectionMap`（类方法）<br>`.resolve(section: Section, kind: str) -> Resolution`<br>`.reverse(spec_path: str) -> str \| None`<br>`.validate(catalogue_macro_path: str) -> list[str]` | 纯函数式；不写文件 |
| `engine/macgen.py` | `MacOptions` | 数据类，字段见 b.6 | — |
| | `generate_macro` | `generate_macro(model: Model, opts: MacOptions) -> str` | 纯函数 |
| | `write_macro` | `write_macro(path: str, text: str) -> str` | 写 GBK+CRLF 文件，返回 `path` |
| `engine/pdms_dump.py` | `parse_dump` | `parse_dump(text: str) -> Model` | 纯函数（**收 str，不收路径**） |
| `engine/cli.py` | — | 见 (f) | 读写命令行指定的文件 |
| `engine/gui.py` | — | 见 (f) | tkinter 图形操作，逻辑必须复用上述函数 |

**共同纪律**

1. **禁止**任何模块自行实现另外一份公式（例如 macgen 里再算一遍梁端点）。几何只由
   `jwd_read/pdt_read/parse_dump` 产出，`macgen/jwd_write` 只消费。
2. **禁止**静默跳过：任何被跳过的对象都要回流到 `Model.notes` 或 `write_jwd` 的返回值
   （见 b.5），由 CLI 汇总进 `report.skipped`。
3. 所有 `*_read` / `parse_dump` 必须在返回前把"未解码但非空"的表/节记入 `notes`。

### b.2 `read_jwd(path: str) -> Model`

* 打开方式：`sqlite3.connect('file:' + path.replace('\\','/') + '?mode=ro', uri=True)`
  —— **只读**，禁止对用户原件做任何写操作（含 `PRAGMA` 写入）。
* **文本列逐值解码（最容易踩的坑）**：`con.text_factory = dec`，其中

  ```python
  def dec(b):
      if not isinstance(b, bytes): return b
      for enc in ('ascii', 'utf-8'):
          try: return b.decode(enc)
          except Exception: pass
      return b.decode('gbk', 'replace')
  ```
  【事实】`pkpmColSect.Name`/`pkpmBraceSect.Name` 是 **GBK** 字节（`b1a1b1da…` = "薄壁…"），
  而 `pkpmLoadSect.Loadname` 是 **UTF-8** 字节（`e697a0` = "无"）（`jwd_format.md` §9.1）；
  本次 C1 在该文件上复现了这一对事实。
  **禁止**整体 `text_factory=gbk`（会得到 `鏃�`），也**禁止**整体 UTF-8。
* 装配步骤严格按 §a.5；表不存在或为空 ⇒ 视为空，**不报错**（`.jwd` 表数实测 46，见 §0.2）。
* 非空但未解码的表（`pkpmWallSeg`、`pkpmStairSeg`、`pkpmSubBeam`、`pkpmCrane*`、`pkpm*Damper*`、
  `pkpmCantiSlab*`、`pkpmColcapSect`、`pkpmMidBeamSeg`、`pkpmMidSlab`、`pkpmPetroDevice*` 等）
  ⇒ 写 `notes`，行数 > 0 时**必须**留下"未转换"痕迹；不得猜字段含义。
* 可选充实（**只做加法，不影响几何**）：
  * `pkpmProperty` 中 `Name='HNTDJ'`（混凝土强度等级，样本 `ShapeVal='30.00'`）
    ⇒ `Member.material = 'C' + str(int(值))`（`30.00` → `'C30'`）；`Name='GANGH'` 同理 → `'Q'+str(int(值))`；
    **值 ≤ 0（未指定）时不填**（样本 GANGH 全 0）。
  * `pkpmSysInfo.ID=2` 的字符串（样本 `"JLCJ2"`）→ 作为工程名候选（CLI 的 `--project` 缺省值）。

### b.3 `write_jwd(model: Model, path: str) -> dict`

**建表（DDL 的唯一出处）**：把 `_recon\jwd_dump\00_schema.txt` 里的
**46 条 `CREATE TABLE`** 与索引语句**原样**嵌入实现（本次 C2/命令行已确认该文件含
`CREATE TABLE count=46`，且每条 DDL 与样本一致）。建库后 `PRAGMA encoding` 应为 `UTF-8`。

**写入顺序：父表先于子表**（外键虽不具约束力，仍必须满足父子顺序，便于任何工具校验）：

```
1  pkpmStdFlr      → 2  pkpmFloor       → 3  pkpmJoint      → 4  pkpmAxis
5  pkpmGrid        → 6  pkpmBeamSect    → 7  pkpmColSect    → 8  pkpmBraceSect
9  pkpmColSeg      → 10 pkpmBeamSeg     → 11 pkpmBraceSeg   → 12 pkpmSlab
13 pkpmSlabHole    → 14 pkpmLoadSect    → 15 pkpmLoadSeg    → 16 pkpmProperty
17 pkpmSysInfo     → 18 pkpmStdFlrPara  → 其余 28 张表只建表不插行
```

**由规范模型合成缺失的父表（不丢失几何）**

| 目标表 | 合成规则 |
|---|---|
| `pkpmStdFlr`/`pkpmFloor` | 每个 Level 各一行：`StdFlr(ID=stdflr_id, No_=no)`、`Floor(ID=floor_id, No_=no, StdFlrID=stdflr_id, LevelB=z_bot, Height=height)`。**平面型 Level 先归并成楼层**：把模型里出现过的全部 Z 升序去重 `z[0..m-1]`，对每对相邻 `(z[i], z[i+1])` 建一层 `z_bot=z[i], height=z[i+1]-z[i]`；最高面 `z[m-1]` 不再单独成层。 |
| `pkpmJoint` | 每个 `(stdflr, x, y)` 唯一 → 一行；`No_` 按层内 `(y, x)` 升序 1..n |
| `pkpmGrid`/`pkpmAxis` | 每根 `beam` 一行 `pkpmGrid(Jt1ID/Jt2ID = 该梁两端节点)`，并给它一行 `pkpmAxis`（同两端点，`Name=''`）。**允许**简化：轴网分组编号与原 JWD 可能不同（报告须注明），几何不受影响。 |
| `pkpmProperty` | 有 `Member.material` 时写 `Name='HNTDJ'`、`Type=5`、`ShapeVal='<等级数字>.00'`（如 C30 → `30.00`） |

**文本列写字节规则**（`jwd_format.md` §9.1 的混合编码，写回必须按列区分）：

| 列 | 字节编码 |
|---|---|
| `pkpm*Sect.Name` | **GBK**（含中文时） |
| `pkpmLoadSect.Loadname` | **UTF-8** |
| 其余文本列（`ShapeVal`、`JYDef`、`GridsID`、`VertexX/Y/Z`、`strParas*`、`Loadname` 之外） | **ASCII**；含非 ASCII 时用 **GBK** |

> 全部 ASCII 时三种编码等价，无风险；**禁止**写 BOM。

**返回值**（`dict`，键固定，供 CLI 直接并入 `report.json`）：

```python
{
  "tables": {"pkpmStdFlr": 5, "pkpmFloor": 5, ...},   # 表名 -> 实际插入行数
  "rows": 5017,                                       # 插入总行数
  "members": {"beam": 598, "column": 200, "brace": 13},
  "slabs": 222, "walls": 0, "loads": 121,
  "skipped": [ {"what": "wall", "id": 7, "why": "pkpmWallSeg 语义未解码（jwd_format.md §1.7）"} ],
  "warnings": ["轴网编号为合成结果，与原 JWD 的轴线分组可能不同"]
}
```

### b.4 `read_pdt(path: str) -> Model`

* 编码 **GBK、CRLF**；`;` 开头为注释；`$` 开头为节头；**缩进即语法**：
  ≤4 空格 = 新记录，>4 = 续行；续行以裸值开头时**追加到上一条物理行的最后一个字段**
  （跨行记忆 `last_key`）——`EXR` 与 `$RIGID.SLABID` 都有折行，踩坑实证见 `pdt_format.md` §1.2。
* 只解析几何相关节：`$VERSION/$STORY/$NODECOOR/$NET/$DEFFRAMESECTION/$DEFWASLABSECTION/`
  `$DEFMATERIAL/$SETELEMENT/$SETWALL/$SETSLAB/`（荷载节**可选**解析，塞不进 `Model` 的语义
  一律进 `notes`）。
* Level：按 §a.3 的**平面型**规则按节点 Z 分组建，禁止用 `FLOORID`（`pdt_format.md` §8.3）。
* `Member.level` = start 端所在平面；柱的 `start` 在下端、`end` 在上端（`$SETELEMENT.TYPE=1`）。
* 构件类型：`TYPE=1`→`column`、`2`→`beam`、其余值（含墙板 5/6）不进 `members`；
  `$SETSLAB`→`Slab`（`polygon` 由 `NETID` 有序闭合环拼出，`pdt_format.md` §2.10）；
  `$SETWALL`→`Wall`（`loop` 为环的 3D 顶点，`z_bot/z_top` 为环上 U 的极值）。
* `Section`：`$DEFFRAMESECTION` → `Section(table='pdt', kind=KIND, dims={'B1','B2','B3','H1','H2','H3','T1'…})`，
  `name` 取 `NAME`/`NAME1`；`$DEFWASLABSECTION` → 不建 `Section`，墙板厚度直接落在 `Slab.thickness`/`Wall.thickness`。
* 【事实】型钢板厚在本格式里**恒为 0**，只能靠名称映射（`pdt_format.md` §2.6）→ 进 `notes`。

### b.5 模块间"不许互相 import"的边界

* `canonical.py` **不得** import 任何其他引擎模块（它是叶子）。
* `secmap.py` 只 import `canonical`；`macgen.py` 可 import `canonical`+`secmap`；
  `jwd_write.py` 只 import `canonical`；`*_read.py` 只 import `canonical`；
  `cli.py`/`gui.py` import 全部。
* 禁止环状依赖；禁止在 `canonical.py` 里写 I/O 与 PDMS 语法。

### b.6 `MacOptions` 字段（`macgen.generate_macro(model, opts)` 的 `opts`）

| 字段 | 类型 | 缺省 | 说明 |
|---|---|---|---|
| `project` | `str` | `"PKPM_PROJECT"` | PDMS ZONE 名（CLI 的 `--project`） |
| `base_e` / `base_n` / `base_u` | `float` | `0.0` | 基点，单位 = `unit`（§f.1 的坐标公式） |
| `angle_deg` | `float` | `0.0` | 平面转角（度，+U 俯视逆时针） |
| `unit` | `str` | `"mm"` | **必须** ∈ `{'mm','cm','m'}`；决定宏观内数值缩放（d.4-1） |
| `secmap` | `SectionMap \| None` | `None` | 截面解析器。**`None` ⇒ `generate_macro` 抛 `ValueError`**：禁止静默产出"无规格宏"；CLI 必须注入（`SectionMap.load(...)` 的结果） |
| `header_note` | `str` | `""` | 附在宏头部注释里的额外说明（可留空） |
| `time_text` | `str` | `""` | 头注释里的时间戳文本；留空则由实现取当前时间 |
| `uniquify` | `bool` | `True` **〔R3〕** | True ⇒ 每个创建元素前 emit §o.4 的唯一化模板（`!!pkpmjwdUniquename` + 空名故障注入 + `ONERROR/LABEL` 尾）；False ⇒ v1 行为（直接 `NEW <TYPE> /名`），仅测试用 |
| `pml_func_path` | `str` | `""` **〔R3〕** | `pkpmjwduniquename.pmlfnc` 的路径；非空时宏头 emit `$M <$!pkpmjwdFuncPath>`（§o.4）；空 ⇒ 只发注释提醒"函数须已加载" |

* 板/墙的规格**不设独立字段**：一律由 `secmap.resolve(Section.for_panel('slab'|'wall', 厚度), kind)` 得到
  （契约 §e.6），保持"截面解析只有一条路"。
* `MacOptions` 定义在 `macgen.py` 内（不放 `canonical.py`，因为它是宏生成专有参数）。

---

## (c) PDMS 导出文本格式 `#PKPM-JWD-PDMSDUMP 1.0`

**用途**：PDMS 侧（PML 导出函数）写、Python 侧（`pdms_dump.parse_dump`）读的中性交换文本。
**两端必须严格一致**：写方按本节的生成规则，读方按本节的解析规则；任何一端改动都先改本文件。

### c.1 编码、换行、缺省单位（先说清）

| 项目 | 规定 |
|---|---|
| 编码 | **GBK，无 BOM**。只含 ASCII 时按 GBK 解码与按 UTF-8 解码等价；读方**必须**用 GBK 解码（`open(path, encoding='gbk')`），解码失败即报错退出（**禁止** `errors='replace'`） |
| 换行 | **CRLF**（`\r\n`）；读方按 `splitlines()` 处理，行尾 `\r` 必须去掉 |
| 缺省单位 | `UNITS` 行缺失 ⇒ 视为 **`mm`**，并在报告 `warnings` 里记一条 |
| 单位换算 | `mm`=×1、`cm`=×10、`m`=×1000。**只有长度量随单位变化**：E/N/U 坐标、`#PANE` 的 `height`、`#STWALL` 的 `height` 与厚度尾部、`#SCTN` 的 `desp` 参数。角度（`bangle`）恒为**度**，不随单位变化 |
| 名称 | 一律不含空白字符；**不得**含 `~`（`~` 是可选尾部的分隔符） |
| 数值 | 必须是 `float()` 可解析的十进制（允许 `1e+04`、`-0.5`）；**禁止**千分位逗号、单位后缀、`NaN/Inf` |
| 行数 | 每条记录恰好一行；除首行/`UNITS` 行外，**空行一律忽略**（不报错） |

### c.2 文法（EBNF，`SP`=空格，`CRLF`=`\r\n`）

```
file      = header , units , { record } , end ;
header    = "#PKPM-JWD-PDMSDUMP" , SP , "1.0" , CRLF ;
units     = "UNITS" , SP , ( "mm" | "cm" | "m" ) , CRLF ;
record    = site | zone | stru | frmw | sbfr | sctn | pane | stwall ;
site      = "#SITE"   , SP , name , CRLF ;
zone      = "#ZONE"   , SP , name , CRLF ;
stru      = "#STRU"   , SP , name , CRLF ;
frmw      = "#FRMW"   , SP , name , CRLF ;
sbfr      = "#SBFR"   , SP , name , CRLF ;
sctn      = "#SCTN" , SP , name , SP , ctype , SP , spref ,
            { SP , num } ,                                  (* desp: 0..n 个 *)
            SP , num , SP , num , SP , num ,                (* e1 n1 u1 *)
            SP , num , SP , num , SP , num ,                (* e2 n2 u2 *)
            SP , orient , SP , card , SP , card , SP , num , CRLF ;   (* ori jusl meml bangle *)
pane      = "#PANE" , SP , name , SP , num ,                (* height = 板厚 *)
            SP , vertex , { SP , vertex } ,                  (* ≥3 个顶点 *)
            [ SP , "~" , SP , spref , SP , orient2 , SP , card ] , CRLF ;
stwall    = "#STWALL" , SP , name , SP , spref , SP , num ,  (* height = 墙高 *)
            SP , vertex2 , SP , vertex2 ,                    (* 底边起/终点，U = 底标高 *)
            [ SP , "~" , SP , num ] , CRLF ;                  (* 可选：墙厚 *)
end       = "#END" , CRLF ;
vertex    = num , SP , num , SP , num ;                      (* e n u *)
vertex2   = num , SP , num , SP , num ;                      (* e n u，与 vertex 同构 *)
name      = 1*NAMECHAR ;   NAMECHAR = 可见 ASCII(%x21-7E) 但排除 "~"
spref     = name | "-" ;   card = name | "-" ;
ctype     = "COLUMN" | "BEAM" | "HBRACE" | "VBRACE" ;
orient    = "E" | "N" | "U" | "S" ;
orient2   = "YNZU" ;
num       = [ "-" ] , 1*DIGIT , [ "." , 1*DIGIT ] , [ ("e"|"E") , [ "+" | "-" ] , 1*DIGIT ] ;
```

### c.3 解析规则（读方**必须**按此实现，且有歧义处已在此定死）

1. **层级**：`#SBFR` 的父是**最近一条** `#FRMW`；`#FRMW` 的父是最近 `#STRU`；
   `#STRU` 的父是最近 `#ZONE`；`#ZONE` 的父是最近 `#SITE`；
   `#SCTN`/`#PANE`/`#STWALL` 的父是最近 `#SBFR`。缺失父级 ⇒ 记 `E-PARSE` 并终止。
2. **`#SCTN` 的 `desp` 可为 0 个 —— 用"从尾部定位"法解析**（这是本节定死的规则）：
   `tokens = line.split()`；`len(tokens) >= 14`；
   `name=tokens[1]`、`ctype=tokens[2]`、`spref=tokens[3]`、
   **`desp = tokens[4 : len(tokens)-10]`**、`e1,n1,u1,e2,n2,u2 = tokens[-10:-4]`、
   `ori,jusl,meml,bangle = tokens[-4:]`。
   ⇒ 因为尾部固定 10 个 token，`desp` 的长度不需要额外字段，也不会与几何混淆。
3. **`#PANE` 的可选尾部**：先按 token 找**第一个** `~`；`~` 之前是
   `[标记, name, height, v1e, v1n, v1u, v2e, …]`，`~` 之后恰为 3 个 token
   `spref ori sjus`。要求 `(len(left)-3) % 3 == 0` 且顶点数 ≥ 3，否则 `E-PARSE`。
   无 `~` ⇒ `spec_path=''`（记 `W-DUMP-NOSPEC`）、`ori='YNZU'`、`sjus='dbot'`。
4. **`#STWALL`**：token 数 ∈ {10, 12}；`name=t[1]`、`spre=t[2]`、`height=t[3]`、
   底边起 `(t[4],t[5],t[6])`、底边终 `(t[7],t[8],t[9])`；有尾部时 `t[10]=='~'`、`t[11]=厚度`。
   `spre == '-'` ⇒ `spec_path=''` 并记 `W-DUMP-NOSPEC`。
5. **`-` 哨兵**：`spref/spre == '-'` 表示"无规格"，**不是**名字叫 `-` 的规格。
   读方必须记入 `report.sections.unresolved` + `report.skipped`（禁止静默丢弃该构件）。
6. **`type` 与 `ori` 是冗余自校验位**：几何才是真值来源。
   * `Member.type`：由 `ctype` 决定；`HBRACE`/`VBRACE` 都映射成 `'brace'`。
     与几何分类不一致（`COLUMN` 却水平 / `BEAM` 却不水平）⇒ 记 `W-DUMP-TYPE`，**仍按 `ctype` 归类**。
   * `ori`：由端点差算出（`|ΔU|>tol` 且 `√(ΔE²+ΔN²)≤tol` → `U`；`|ΔN|≤tol<|ΔE|` → `E`；
     `|ΔE|≤tol<|ΔN|` → `N`；否则 `S`）。不一致 ⇒ 记 `W-DUMP-ORI`，不改变几何。
   * `bangle` → `Member.rotation`（度）；`jusl/meml` → `Member.jusl/meml`（`-` → `''`）。
7. **`#PANE` → `Slab`**：`polygon = [(E,N)]`、`z = U`（所有顶点的 U 必须一致，误差 ≤ 1e-6，
   否则 `E-PARSE`）、`thickness = height`、`is_hole=False`、`level` 由 §a.3 平面型规则定。
8. **`#STWALL` → `Wall`**：`loop = [起(z), 终(z), 终(z+height), 起(z+height)]`（4 点闭合回路）、
   `z_bot = min(U)`、`z_top = z_bot + height`、`thickness` 取尾部值（缺省 0 并记 `W-DUMP-NOTHICK`）。
9. **`#FRMW /GRID` 下的 `#SCTN`**：轴网线**不是**结构构件 —— 一律**忽略**并把条数记入 `notes`。
   `jwd2pdms` 生成的 dump 不写轴网（轴网由宏直接生成，见 (d)）。
10. **`#END`**：必须存在；其后只允许空行。缺失 ⇒ `E-PARSE`。
11. **层归并**：读完后按 §a.3 平面型规则把出现过的 Z 建成 Level；随后若交给 `jwd_write`，
    由 `jwd_write` 按 b.3 归并成楼层。

### c.4 最小示例（**可直接用作两端联调夹具**）

```
#PKPM-JWD-PDMSDUMP 1.0
UNITS mm
#SITE /PKPM_JWD
#ZONE /JLCJ2
#STRU /MAINFRAME
#FRMW /STL_FRAME/EL1
#SBFR /COLUMN
#SCTN /STL_COL_1 COLUMN /H_INTERNATIONAL-SPEC/HN450X200 400 400 -2000 400 400 -1000 U rboc rboc 0
#SCTN /STL_COL_2 COLUMN /USER_RECT-SPEC/Rectangle_Profile 600 600 600 -2000 600 600 -1000 U rboc rboc 0
#SBFR /BEAM
#SCTN /BM_1 BEAM /H_INTERNATIONAL-SPEC/HN300X150 400 400 -1000 6400 400 -1000 E lbos lbos 0
#SBFR /HBRACE
#SBFR /VBRACE
#FRMW /FLOOR&WALL
#SBFR /SLAB
#PANE /SLAB_1 120 400 400 -1000 6400 400 -1000 6400 4400 -1000 400 4400 -1000 ~ /USER_RECT-SPEC/Rectangle_Profile YNZU dbot
#SBFR /WALL
#STWALL /W_1 /Concrete_Wall-SPEC/WALL-300 3000 0 0 -2000 6000 0 -2000 ~ 300
#FRMW /GRID
#END
```

**逐行读法（同时验证 §c.3 的规则）**

| 行 | 解析结果 |
|---|---|
| `#SCTN /STL_COL_1 …` | 15 个 token：name=`/STL_COL_1`、ctype=`COLUMN`、spref=`/H_INTERNATIONAL-SPEC/HN450X200`、`desp=tokens[4:5]=[]`、POSS=(400,400,−2000)、POSE=(400,400,−1000)、ori=`U`、jusl/meml=`rboc`、bangle=0 |
| `#SCTN /STL_COL_2 …` | 15 个 token：`desp = tokens[4:15-10] = tokens[4:5] = ['600']`（矩形截面的第 1 个 DESP 参数）、几何 `tokens[-10:-4] = (600,600,−2000)→(600,600,−1000)` |
| `#PANE /SLAB_1 …` | `height=120`（板厚）、4 个顶点、尾部 `~ /USER_RECT-SPEC/Rectangle_Profile YNZU dbot` ⇒ `Slab(thickness=120, z=−1000, ori='YNZU', sjus='dbot')` |
| `#STWALL /W_1 …` | 12 个 token：`spre=/Concrete_Wall-SPEC/WALL-300`、`height=3000`、底边 (0,0,−2000)→(6000,0,−2000)、尾部厚度 300 ⇒ `Wall(z_bot=−2000, z_top=1000, thickness=300)` |

### c.5 写方（PML 侧）生成规则（与 §c.3 一一对应）

| 记录 | 生成规则 |
|---|---|
| `#SCTN` | `ctype` 按几何/构件类型取 `COLUMN`/`BEAM`/`HBRACE`/`VBRACE`（支撑：`\|ΔU\|≤tol` → `HBRACE`，否则 `VBRACE`）；`spref = !!CE.SPREF`（无 → `-`）；`desp = !!CE.DESP` 原样；坐标 `= !!CE.POSS/POSE` 的 `.East/.North/.Up`；`jusl/meml = !!CE.JUSL/MEML`（无 → `-`）；`bangle = !!CE.BANG` |
| `#PANE` | `height = !!CE.HEIGHT`（PLOOP 挤出高度 = 板厚）；顶点 = PLOOP 的 PAVERT 顺序 `.East/.North/.Up`；尾部 `spref = !!CE.SPREF`（无 → 省略整个尾部）、`ori = YNZU`、`sjus = !!CE.SJUS`（无 → `dbot`） |
| `#STWALL` | `spre = !!CE.SPRE`；`height = !!CE.HEIG`；底边 = `!!CE.POSS/POSE`；尾部厚度 = 墙截面厚度（取不到则省略尾部） |
| 层级行 | `#SITE/#ZONE/#STRU/#FRMW/#SBFR` 各写当前元素 `NAME`（含 `/` 的路径名照写，见 (d)） |

> 单位：写方若所在 Design 数据库不是 mm，必须**按 §c.1 换算后写数值**，并把 `UNITS` 行写成
> 数据库当前单位；缺省写 `mm`。

---

## (d) PDMS 实体层级与命名（与现有插件同构）

### d.1 树形（**必须**照此实现，两套导入器的结果才能互换）

```
SITE  /PKPM_JWD
└ ZONE  /<工程名>                                  ← --project，缺省取 pkpmSysInfo.ID=2（样本 "JLCJ2"）
  └ STRU  /MAINFRAME
    ├ FRMW  /STL_FRAME/EL<n>      n = pkpmFloor.No_（平面型模型：按 Level.no）
    │   ├ SBFR /COLUMN   → SCTN /STL_COL_<No_>
    │   ├ SBFR /BEAM     → SCTN /BM_<No_>
    │   ├ SBFR /HBRACE   → SCTN /HB_<No_>
    │   └ SBFR /VBRACE   → SCTN /VB_<No_>
    ├ FRMW  /FLOOR&WALL
    │   ├ SBFR /SLAB     → PANE  /SLAB_<No_>
    │   └ SBFR /WALL     → STWALL /W_<No_>
    └ FRMW  /GRID        承载轴网（本契约 v1.0 只建 FRMW，不写轴网构件；轴网由宏另行生成）
```
* 命名来源（**事实**，`pdms_target.md` §3.3，取自 `PDMSxCA_Addin121.dll` 字符串）：
  `/SITE`、`/MAINFRAME`、`/STL_FRAME/EL`、`/S_EL`、`/FLOOR&WALL`、
  `/COLUMN`、`/BEAM`、`/HBRACE`、`/VBRACE`、`/STL_COL_`、`/BM_`、`/HB_`、`/VB_`。
* 板/墙分组在 `FRMW /FLOOR&WALL` 下（同源字符串 `/FLOOR&WALL`）；板厚写在 PANE 的 `HEIGHT`。
* `bis` 不在契约内：**不**建 `ELEVIEW`/`PLANVIEW` 视图（Add-in 会建这些视图，但那是它的 UI 行为，
  没有证据表明导入所必需；为避免多造对象，v1.0 不建。若实机证明确有必要，走 §0.3 的契约变更）。

### d.2 构件命名（**契约冻结**）

| 构件 | 名称 | `<No_>` 取值 |
|---|---|---|
| 柱 | `/STL_COL_<No_>` | `pkpmColSeg.No_`（层内编号）；平面型模型用 1..n 的批内序号 |
| 梁 | `/BM_<No_>` | `pkpmBeamSeg.No_` |
| 水平支撑 | `/HB_<No_>` | `pkpmBraceSeg.No_`（`\|ΔU\| ≤ 1e-6` 的支撑） |
| 竖向支撑 | `/VB_<No_>` | `pkpmBraceSeg.No_`（其余支撑） |
| 板 | `/SLAB_<No_>` | `pkpmSlab.No_` |
| 墙 | `/W_<No_>` | `pkpmWallSeg.No_`（**v1.0 不产出**，留给后续） |

* `No_` 是**层内**编号，跨层会重复 ⇒ 名称只在一个 FRMW/EL 内唯一，符合 PDMS 同级唯一性要求。
* 名称里**不含**空格；`/` 允许（证据：本机 `GRIDDESIGN.pmlfrm:975/994/1016` 用
  `!!CE.NAME = name OF OWNER + '/ALLX' + …` 给 SBFR 起含 `/` 的名字，是能正常运行的宏）。

### d.3 宏里允许出现的 PDMS 语法（**逐条带本机出处**，禁止自造）

> 取证方式：直接读取本机 PDMS 安装内的 PML 源码（只读）。下表每一行都可在
> `D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB\` 下按"文件:行号"复核。

| 用途 | 语法 | 出处（本机文件:行） |
|---|---|---|
| 五级骨架 | `NEW SITE /X`、`!!CE = !Site`、`NEW ZONE /X`、`!!CE = !Zone`、`NEW STRU /X`、`NEW FRMW /X` | `Building_Design\pmllib\concrete_design\ANCHOR\nucdesoanchier.pmlobj:90-106` |
| 层级下钻 | `NEW STRU` / `NEW FRMW` / `NEW SBFR`（依次建在最近父级下） | `mypml\forms\GRIDDESIGN.pmlfrm:964-979` |
| 回退游标 | 裸写类型名 `STRU` / `FRMW` / `SBFR` / `SCTN` / `PANE` / `WALL` | `mypml\forms\StlGrating.pmlfrm:105`（`STRU`）、`mypml\forms\GRIDDESIGN.pmlfrm:1458`（`FRMW`）、`design\functions\aslspecinit.pmlfnc:79,81`（`SBFR`,`FRMW`）、`design\forms\aslhandrail.pmlfrm:158`、`MYTOOLS\test\Tekla2PDMS\sdnf\functions\sdnfinver3.pmlfnc:373` |
| 命名 | `!!CE.NAME = …` | `mypml\forms\GRIDDESIGN.pmlfrm:970,975` |
| 钢构件 + 规格 | `NEW SCTN` / `SPREF <spec>` / `DESP <v…>` / `JUSL <card>` / `MEML <card>` / `POSS E .. N .. U ..` / `POSE E .. N .. U ..` / `BANG <deg>` | `mypml\forms\StlGrating.pmlfrm:92-97`；`MYTOOLS\test\Tekla2PDMS\sdnf\functions\sdnfinver3.pmlfnc:117,140,142,158,163,187,188,192`；`design\functions\sctlcrelem.pmlfnc:169-181,267-292,332-349` |
| 卡点枚举 | `JUSL/MEML` 取值形如 `rbos,bos,lbos,naro,na,nalo,ltos,tos,rtos,na`（对称截面）/ `lboc,boc,…`（C/U）/ `toay,toax,rtta,…`（L） | `sdnfinver3.pmlfnc:128,132,136` |
| 板 | `NEW PANE` / `ORI Y IS N AND Z IS U` / `NEW PLOOP` / `HEIGHT <t> SJUS dbot` / `NEW PAVERT` + `POS E .. N .. U ..` | `mypml\forms\StlGrating.pmlfrm:45-56`；`design\functions\sctlcrelem.pmlfnc:229-256` |
| 墙 | `NEW STWALL` / `SPRE <spec>` / `DESP <v…>` / `JUSL <card>` / `POSS …` | `design\functions\sctlcrelem.pmlfnc:201-202,156-167,313-330`；`Building_Design\pmllib\concrete_design\TRADUCTEUR\nucdesogwall.pmlobj:180-196` |
| 轴网线 | `NEW SCTN` + `POSSTART E .. N .. U ..` / `POSEND E .. N .. U ..` | `mypml\forms\GRIDDESIGN.pmlfrm:979-985,1019-1026` |
| 注释 | `--` 行注释；`$*` 亦可 | `mypml\forms\scale-STRU.mac`（`--`）；`PMLLIB\SBSPEC\sb_snap.mac`（`$*`） |
| 同义词开关 | 首行 `$S-  -- Synonym translation OFF`、末行 `$S+  -- Synonym translation ON` | 用户原件 `G:\…\PKPM（PDMS数据库）.txt` 第 1 行与末行（本次实测，见附录 C） |

**属性归属（AVEVA 官方实现直证）**：`SCTN`/`PANE(板)` 用 **`SPREF`**，
`WALL`/`STWALL` 用 **`SPRE`**（`design\functions\sctlcrelem.pmlfnc:201-202,229-232,267-292`）。

> ⚠ **同一安装内的反例**（必须让实施者知道）：`nucdesogwall.pmlobj:188` 对 `NEW STWALL`
> 用的是 `spref /SPEC-GC-WALL-SIMPLE-SPCO`。本契约**按任务要求与 sctlcrelem 的官方归属**取
> **墙用 `SPRE`**；实机若报错，先按 §12 的"待实机确认项"回报，不得擅自两处都写。

### d.4 `macgen.generate_macro` 的输出骨架（`MacOptions.unit` 决定数值缩放）

```
$S-                                  -- 关闭同义词翻译（源自目录宏首行惯例）
-- PKPM-JWD导入导出 自动生成：<源文件>  <时间>  契约 v1.0
-- 单位：<mm|cm|m>；基点 E/N/U = …；转角 = … 度
NEW SITE /PKPM_JWD
NEW ZONE /<工程名>
NEW STRU /MAINFRAME
NEW FRMW /STL_FRAME/EL1
  NEW SBFR /COLUMN
    NEW SCTN /STL_COL_1
      SPREF /H_INTERNATIONAL-SPEC/HN450X200        -- 未解析时整行省略，并写 -- UNRESOLVED SECTION 注释
      POSS E 400 N 400 U -2000
      POSE E 400 N 400 U -1000
      JUSL rboc
      MEML rboc
      BANG 0
  FRMW                                               -- 回退到本层 FRMW（裸类型名，见 d.3）
  NEW SBFR /BEAM
    …
  STRU                                               -- 回退到 STRU，准备下一层
NEW FRMW /FLOOR&WALL
  NEW SBFR /SLAB
    NEW PANE /SLAB_1
      SPREF /USER_RECT-SPEC/Rectangle_Profile        -- 未解析时省略本行
      ORI Y IS N AND Z IS U
      NEW PLOOP
        HEIGHT 120 SJUS dbot
        NEW PAVERT
        POS E 400 N 400 U -1000
        …（每个顶点一条 PAVERT）
    PANE
  STRU
NEW FRMW /GRID
STRU
$S+
```

**宏生成纪律**

1. 单位：`MacOptions.unit ∈ {'mm','cm','m'}`；所有长度量按 `mm→unit` 缩放输出
   （mm=×1、cm=÷10、m=÷1000）。**v1.0 不在宏里发出任何单位设置语句**
   （本机可引的单位惯用法是 PML 里的 `Var !Units units` + `mm distance`，见
   `Building_Design\pmllib\room_manager\functions\nucroommcreation.pmlfnc`；这是 PML 代码
   而非宏命令，故不采用）⇒ 调用方必须把 PDMS 当前单位设成与 `--unit` 相同，
   该假设写入 `report.assumptions`。
2. 未解析截面（`status='unresolved'`）：**仍生成构件几何**（`SCTN`/`PANE`/`STWALL` 照建），
   但省略 `SPREF`/`SPRE` 行，并在其上方写 `-- UNRESOLVED SECTION <id> <name> <reason>`。
   依据：`sctlcrelem.pmlfnc:229-256` 表明无规格的 PANE 依然合法（`SPREF` 失败后直接
   `NEW PLOO`），SCTN 亦然（`:290-292` 的 `else NEW SPINE`）。**禁止静默丢弃构件**。
2b. 推断截面（`status='inferred'`，§e.1a）：**既写 `SPREF`/`SPRE` 也写 `DESP`**（数值见第 3 条），
   并在构件块**上方**写一行 GBK 注释
   `-- 推断截面：<证据摘要>；若实为别的族请改 engine/secmap_extra.txt 的 @FAMILY 行`。
   推断结论必须在 `report.sections.detail[].status='inferred'` 与 `evidence` 里机器可见（§h）。
3. `DESP` **只要 `Resolution.desp_params` 非空就写出**（不再以 `status='parametric'` 为条件；
   见变更记录 §0.4-2）：数值随 `unit` 缩放。`desp_params=[]` 的 `resolved` 截面行为不变。
4. `JUSL`/`MEML`：`Member.jusl/meml` 为空时**不写**该行（不要写 `na`，避免自造语义）。
5. 每个 SBFR 组结束后用裸类型名回退（`FRMW` 或 `STRU`），确保下一条 `NEW` 落在正确父级。

---

## (e) 截面解析优先级（**三个方向共用，必须唯一**）

### e.1 四级优先级（严格按序，命中即止）

```
1) Section.Name 非空 且 在匹配文件（原件或补充文件）中命中           → status='resolved'   source='name'
2) 否则按 §a.4 解码 ShapeVal 得到候选键，逐个查匹配文件               → status='resolved'   source='shapeval'
3) 否则走用户参数化族（§e.3 的映射表 → /USER_*-SPEC/… + DESP 参数）  → status='parametric' source='family'
3b) 否则按 §e.3 的**推断族**（数据驱动，见 §e.1a）                     → status='inferred'   source='family'
4) 全都失败                                                          → status='unresolved' source='none'
```

**第 3b 级（推断）与第 1/2 级同时命中时的优先级**：第 1/2 级优先——只要
`Section.Name` 或候选键在匹配文件里命中，就是 `resolved`，推断**不参与**。

### e.1a 推断族（`status='inferred'`，变更记录 §0.4-1）

* **定义**：`Kind` 的族别在数据里**没有直接字段**，但有**独立证据**足以判定"是哪一族、参数怎么传"时，
  按 §e.3 的**推断表**给出规格 → `status='inferred'`、`source='family'`、`desp_params` 按该族参数序给出。
* 与 `resolved`/`parametric` 的差别**只在认识论上**：`inferred` 是"有证据的判定"而非"原件里写明的映射"，
  因此它必须（a）在 `report.sections.detail` 里 `status='inferred'` 且 `evidence` 非空、
  （b）在宏里带 `-- 推断截面：…` 注释（§d.4-2b）、（c）可以被数据**一行改回** `unresolved`（§e.4 指令行）。
* **数据驱动**：启用/停用推断**只**由补充文件的指令行决定（§e.4）；`secmap.py` 里**不得**写
  `if section.kind == 3: …` 之类的硬编码分支——`Kind` 号与族键的对应关系属于数据。
* `ok`/`use_desp` 语义：`inferred` 视为"有规格"（`Resolution.ok` 为真），且按其 `desp_params` 出 `DESP`。

**候选键生成器（按序尝试，命中即止）**

| 序 | 候选键 | 适用 | 证据 |
|---|---|---|---|
| 0 | `Section.name`（原样，含中文、含 `[`、含空格后的内容） | 全部，非空时 | §3.4：型钢库截面靠名称映射 |
| 1 | `<subtype>-<name>`（Kind=26） | Kind=26 且有子类型（族码 31/32/33/66…） | 插件 DLL 键表 `1-[18a ↔ 32,1,[18a`、`2-I18a ↔ 31,2,I18a`；本次 C3 实测：`Name` 命中 7/8，补上此键后 **8/8**（`[18a → 2-[18a → /C_LIGHT-SPEC/CL18a`） |
| 2 | `<lib_family>-<spec_str>`（Kind=303） | Kind=303 | DLL 键表 `6-B20*1.20 ↔ 77,6`；§3.2 四重印证；本次 C4 实测 **3/3 命中** |
| 3 | `T<厚度>`（`%g` 格式，如 `T120`） | 板/墙（由 `Section.for_panel` 合成，`kind='slab'/'wall'`） | 【事实】`.pdt` 的 `$DEFWASLABSECTION.NAME` 就是 `T600/T120/T100`（pdt_format.md §2.7） |
| 4 | `矩<B>X<H>`（Kind=1） | Kind=1 | `.pdt` 里混凝土矩形叫 `矩750X750/矩300X600`；**注意**原件里没有 `矩*` 条目（§4.3），此键主要用于补充文件 |
| 5 | `<Kind>#<params 用逗号连接>`（如 `1#300,600`、`3#20`、`26#39,1,450,0,200,14,9,0`） | 全部（兜底键） | 本契约规定，供 `secmap_extra.txt` 手工补齐**任何**截面；键可复现（只需 ShapeVal 原文） |

### e.2 匹配文件的解析容错（用户原件实测，C1 输出）

| 事实 | 要求 |
|---|---|
| GBK、CRLF、无 BOM、3,023 物理行 | 按 GBK 解码、按行处理 |
| 注释**只有** `//` 一种（`///`、`// DESC '…'`、`//+`、`//short` 都是注释）；另有整行 `/` 的分隔线 | 以 `strip()` 后 `startswith('//')` 判注释；`strip()` 后仅由 `/` 组成的行也当注释 |
| 数据行 `<PKPM 名>,<空白><PDMS 路径>`；**逗号两侧空白随意**；右值可能**缺前导 `/`** | `l, r = line.split(',', 1)`；`l=l.strip()`；`r=' '.join(r.split())`（合并内部空白）；`if not r.startswith('/'): r = '/' + r` |
| 右值缺前导 `/` 的实测 4 条 | 第 2979–2982 行：`组卷L40X15X2.0, DOUBLE_THIN_L_COIL_EQUAL-SPEC/DLTC40X15X2.0` 等 ⇒ 必须补齐 |
| 左值唯一 | 2,836 条数据行 **0 个重复左值**（C2） ⇒ 冲突处理：后加载者覆盖并记 `warnings` |
| 大小写 | **严格区分**（原件同时存在 `L25X3` 与 `3-L25x16x3`）⇒ 比较前**只**做空白归一化与前导 `/` 补齐，**不改大小写** |
| 规格前缀 | 共 53 个（C2）⇒ 只做信息统计，不参与判断逻辑 |

### e.3 用户参数化族映射表（第 3 级；**只列有证据的**）

| 输入（Kind + dims） | 族键 | `spec_path` | `desp_params` 顺序 | 证据 |
|---|---|---|---|---|
| Kind=1（`B,H`） | `RECT` | `/USER_RECT-SPEC/Rectangle_Profile` | `[B, H]` | 原件第 29 行 `RECT, /USER_RECT-SPEC/Rectangle_Profile`；目录宏 `/USER_RECT` 的 DTSET：`DKEY B→ATTRIB DESP[1]`、`DKEY H→ATTRIB DESP[2]`（pdms_target.md §5.2） |
| Kind=2（`Tw,H,B1,T1,B2,T2`）**且** `B1==B2 且 T1==T2` | `H` | `/USER_H-SPEC/H_Profile` | `[B1, B2, H, Tw, T1, T2]` | 原件 `H → /USER_H-SPEC/H_Profile`；目录宏 `/USER_H` 参数序 `B1 B2 H Tw T1 T2`（§5.2） |
| Kind=2 **且** `B1≠B2 或 T1≠T2` | — | — | — | **unresolved**：B/T 交错序未证实（`jwd_format.md` §9.3#5） |
| Kind=3（`d`）→ **推断族**（§e.1a） | `CIRCLE` | `/USER_CIRCLE-SPEC/Circle_Profile` | `[d]`（单参数=直径） | ① `1_PM.pdt:2387-2388` `ID=1009, NAME=圆形4800, SHAPE=3` + `KIND=3, B1=4800`（B1=直径）⇒ `Shape/Kind=3` 是圆形；② 同一 JLCJ2 模型把「薄壁方钢管: B20」归 `Kind=303`（`pkpmBraceSect` ID=62965）⇒ 排除方管；③ 目录宏 `PKPM（PDMS数据库）.txt:2502-2513`：`/USER_CIRCLE` 的 DTSET 唯一参数 `DKEY D / PTYP DIST / PPRO ( ATTRIB DESP[1] ) / NUMB 1`（故 `desp_params=[d]`）；④ 原件第 27 行 `CIRCLE, /USER_CIRCLE-SPEC/Circle_Profile`。**启用与否由 §e.4 的指令行决定**（默认在 `engine/secmap_extra.txt` 里 `@FAMILY 3 = CIRCLE`） |
| Kind=26 / Kind=303 | — | — | — | **不走参数化族**（族属性无法由 H/B 反推 HN/HW；303 的规格串本身就是键） |
| 板 `/T<t>` / 墙 `/T<t>` | — | — | — | 原件无板/墙规格条目 ⇒ 需在 `secmap_extra.txt` 里显式给出（**不改用户原件**） |

> 除 `RECT`/`H`/`CIRCLE` 外，其余 `USER_*` 族（`XI/C/TUBE/PIPE/T/Z/CROSS/…`）在 v1.0
> **不自动启用**：JWD 数据里没有足够证据判定该用哪一族（§e.3 只列证据充分的）。

**`Kind=3` 的残余风险（必须随交付物一起给出，不得当作事实）**：`d=20` 的**单位**与"实心圆钢
还是别的圆形"没有 100% 排除；影响面仅样本 JLCJ2 的 12 根屋面水平支撑。改动办法见 §e.4 指令行。

### e.4 补充映射文件 `engine/secmap_extra.txt`（**独立文件，禁止改用户原件**）

* 语法**与用户原件完全相同**（同一解析器），GBK 无 BOM + CRLF；
* 加载顺序：**原件 → 补充文件**；同名左值以**补充文件**为准，并记 `warnings`；
* 典型内容（示例，实施者按需增删）：

```
///截面匹配补充（本文件属于 PKPM-JWD导入导出，不改动用户原件）
// 板厚：T<厚度mm>，见 pdt_format.md §2.7
T120, /Concrete_Slab-SPEC/T120
T100, /Concrete_Slab-SPEC/T100
// 墙：STWALL 用 SPRE 指向墙体规格
T300, /Concrete_Wall-SPEC/WALL-300
// 兜底键：任何截面都可用 <Kind>#<ShapeVal 参数体> 点名
3#20, /TUBE_TUBE-SPEC/D20X2.0
```

* `--extra F` 指定其它补充文件时，**默认补充文件不再加载**（避免隐性叠加）。

#### e.4a 指令行 `@FAMILY <kind> = <族键|none>`（变更记录 §0.4-3）

* **唯一允许**的非 `左值,右值` 行形式（其余非注释行仍须含逗号，否则按"无法解析"记 `warnings`）；
* 语义：声明"`Kind=<kind>` 的单尺寸截面按 **推断族** `<族键>` 解析"（§e.1a/§e.3）；
  `= none` 表示**强制回 `unresolved`**（停用该推断）；
* 作用域与优先级：按 `原件 → 补充文件` 的顺序收集，**后加载者覆盖**（与左值映射同规则）；
  默认生效的一条在 `engine/secmap_extra.txt`（用户原件按 §g 不改、也就不含指令行）；
* 已知族键：`CIRCLE`（`/USER_CIRCLE-SPEC/Circle_Profile`，`desp_params=[d]`）。
  未知族键 ⇒ 记 `warnings` 并**不启用**（不许猜）；
* 一个 `Kind` 只允许一条生效规则；同一 `Kind` 重复声明时后一条覆盖并记 `warnings`。

### e.5 `Resolution.reason` 的写法（未解析必须可解释）

`status='unresolved'` 时 `reason` 必须包含"缺什么证据"，例如：

```
"Name 为空且 candidate keys ['26#39,1,450,0,200,14,9,0'] 不在匹配文件；Kind=26 建议在 secmap_extra.txt 补条目"
"Kind=2 的 B1/T1 交错序未证实（jwd_format.md §9.3#5），无法确定 DESP 顺序"
"Kind=3 的推断族已被 @FAMILY 3 = none 停用（engine/secmap_extra.txt），无候选键命中"
"板厚 T20 无匹配条目，需在 secmap_extra.txt 给出 T20 → 板规格"
```

### e.5a `Resolution.evidence`（`status='inferred'` 必填）

`evidence` 是**证据链文本**（分号分隔，每条带 `文件:行` 或"数据事实"），例如 §e.3 的 `Kind=3` 行：

```
"1_PM.pdt:2387-2388 SHAPE=3/KIND=3 B1=4800 NAME=圆形4800（B1=直径）；
 同模型 薄壁方钢管 归 Kind=303（pkpmBraceSect 62965）；
 PKPM（PDMS数据库）.txt:2502-2513 /USER_CIRCLE DTSET DKEY D→ATTRIB DESP[1]；
 PKPM转PDMS截面匹配文件.txt:27 CIRCLE→/USER_CIRCLE-SPEC/Circle_Profile；
 启用规则 engine/secmap_extra.txt @FAMILY 3 = CIRCLE"
```

`reason` 在 `inferred` 时写**残余风险与改法**（不是"缺什么证据"）。

### e.6 `SectionMap` 的三个方法

* `.resolve(section: Section, kind: str) -> Resolution`
  `kind ∈ {'beam','col','brace','slab','wall'}`：决定"构件类别"相关的家族选择；
  `slab`/`wall` 传 `Section.for_panel(kind, 厚度)` 合成的 Section。
  纯函数：同一 (section, kind) 必得同一结果（`SectionMap` 内部不得有状态变更）。
* `.reverse(spec_path: str) -> str | None`
  归一化后查**逆映射**（右值 → 左值）；多条左值映射到同一右值时返回**加载顺序中第一条**
  （原件优先，其次补充文件；各自按行序）。找不到返回 `None`（调用方必须记入报告）。
* `.validate(catalogue_macro_path: str) -> list[str]`
  以 `encoding='utf-8-sig'`（原文带 BOM）读目录宏（`PKPM（PDMS数据库）.txt`，本次实测：
  BOM=`EF BB BF`、70,301 行、`NEW SPRFILE`×2920、`NEW SPCOMPONENT`×2920），逐条检查：
  1. 右值是否出现在 `NEW SPCOMPONENT <path>` 集合中；缺失 → `"specmap L<行号> <左值> -> <右值> : SPCOMPONENT 不存在"`
  2. 右值的 `-SPEC` 属主名是否∈属主集合；缺失 → `"… : 属主 <X>-SPEC 不存在"`
  返回问题清单（空 = 通过）。**已知原件有 257 条坏映射**（`DOUBLE_L_EQUAL_CROSS` 缺 `C` 等，
  `pdms_target.md` §4.4）⇒ 该清单**不阻断**流程，只进报告；**禁止**自动改原件。

---

## (f) 命令行与图形界面签名

### f.1 三个子命令（**签名冻结**；§m.1〔R2〕是完整命令矩阵，本节三条不变）

```
python PKPM-JWD导入导出/engine/cli.py jwd2pdms <jwd> --out <macro.mac>
        [--secmap F] [--extra F] [--project N] [--base E N U] [--angle D] [--unit mm] [--report R.json]

python PKPM-JWD导入导出/engine/cli.py pdms2jwd <dump.txt> --out <out.jwd>
        [--secmap F] [--dump-unit mm] [--report R.json]

python PKPM-JWD导入导出/engine/cli.py pdt2model <pdt> --out <model.json>
```

| 参数 | 缺省行为 |
|---|---|
| `--secmap F` | 省略 ⇒ 取**与主输入文件同目录**的 `PKPM转PDMS截面匹配文件.txt`；不存在 ⇒ 报错退出（码 2），提示用 `--secmap` 指定（仅对接受 `--secmap` 的子命令适用） |
| `--extra F` | 省略 ⇒ 自动加载 `engine/secmap_extra.txt`（若存在）；给定时**只**加载给定文件 |
| `--project N` | 省略 ⇒ `pkpmSysInfo.ID=2`（样本 `JLCJ2`）；取不到 ⇒ `PKPM_PROJECT`，并记 `assumptions` |
| `--base E N U` | 省略 ⇒ `0 0 0`；单位 = `--unit` |
| `--angle D` | 省略 ⇒ `0`；单位度 |
| `--unit {mm,cm,m}` | 省略 ⇒ `mm`；只影响宏内数值缩放（见 d.4-1） |
| `--dump-unit {mm,cm,m}` | 省略 ⇒ `mm`；**仅当 dump 无 `UNITS` 行时生效**；两者不一致时以 `UNITS` 行为准并记 `warnings` |
| `--report R.json` | 省略 ⇒ 写在 `<--out 同目录>\<--out 基名>.report.json`（如 `out.mac` → `out.report.json`） |

**参数语义**

* 基点与转角（`jwd2pdms`）：`θ = angle_deg`（度，从 +U 俯视逆时针），
  `E = base_e + (x·cosθ − y·sinθ)`、`N = base_n + (x·sinθ + y·cosθ)`、`U = base_u + z`；
  `base_*` 先按 `--unit` 换算成 mm 参与计算，输出前再缩放回 `unit`。
* `pdms2jwd` 的 `--dump-unit` 与 §c.1 一致；`.jwd` 内部恒为 **mm**。
* `pdt2model` 只做 `read_pdt` → `Model.save_json`，并写报告（缺省 `--report` 同上规则）。

### f.2 退出码（**冻结**）

| 码 | 含义 |
|---|---|
| `0` | 成功（**允许**存在 `unresolved` 截面与 `W-` 警告；但必须在 stdout 打印未解析清单，并写进报告） |
| `1` | 未捕获异常（打印 traceback） |
| `2` | 参数/输入文件错误（文件不存在、编码解码失败、dump 文法错误、匹配文件缺失） |
| `3` | `Model.validate()` 出现 **`E-`** 项 ⇒ **不写产物**，把问题清单打到 stderr 并写入报告 |

### f.3 `engine/gui.py`（tkinter，仅标准库）

* 三个标签页对应 f.1 三个子命令，**逐项等价**于命令行参数（含 `--base/--angle/--unit` 等）；
* 逻辑必须**复用** `cli.py` 里的同一个执行函数（GUI 不得复制一份流程）；
* 运行在后台线程，界面不冻结；执行完显示：产物路径、构件计数、**未解析截面清单**、警告；
* 「打开报告」按钮用系统默认程序打开 `report.json`；
* 界面文字用中文；文件选择框按 §g 的编码规则读写，禁止在 GUI 里做单位/编码的二次转换。

---

## (g) 编码与产物纪律

| 产物 | 编码 | 换行 | BOM | 备注 |
|---|---|---|---|---|
| Python 源码（`*.py`、`secmap_extra.txt` 除外） | UTF-8 | 不限（LF/CRLF 均可） | **无** | 首行可写 `# -*- coding: utf-8 -*-` |
| `README.txt`、`docs/*.md` 等纯文本说明 | **UTF-8** | 不限 | **无** | 与 Python 源码一致，便于 git diff 与跨包读写 |
| PDMS 侧产物 `*.mac` / `*.pmlfrm` / `*.pmlfnc` / `*.pmlobj` | **GBK** | **CRLF** | **无** | 必须用 `open(path,'w',encoding='gbk',newline='')` 并自行拼 `\r\n`；写完必须回读校验（`bytes` 里不得有 `\n` 单行） |
| `engine/secmap_extra.txt` | **GBK** | CRLF | 无 | 与原件同构 |
| `#PKPM-JWD-PDMSDUMP` 文本 | **GBK** | CRLF | 无 | 见 §c.1 |
| `engine/section_table.csv` **〔R2〕** | **UTF-8** | CRLF | **带 BOM**（例外，见纪律 2） | 数据文件；与源转化表一致，Excel 可直开；`from_csv` 必须用 `utf-8-sig` 读 |
| 目录/规格宏 `*.mac`（`dbmacro` 产物）**〔R2〕** | **纯 ASCII**（写成 UTF-8 即可） | CRLF | 无 | 写前断言 `text.isascii()`；见 §l.4 |
| `engine/section_table.meta.json` **〔R2〕** | UTF-8 | LF | 无 | 见 §k.2 |
| `*.json`（`Model`/`report`） | UTF-8 | LF | 无 | 见 §a.6 |
| `.jwd`（SQLite） | 见 b.3 的文本列规则 | — | — | `PRAGMA encoding='UTF-8'` |
| `.pdt`、截面匹配文件（**只读**） | GBK | CRLF | 无 | — |
| `pdms-net/*.cs`、`*.py`（deploy 脚本）、`build.cmd` **〔R3〕** | UTF-8（.cs 由 `/codepage:65001` 读） | `.cmd` **必须 CRLF** | 无 | 见 §p.2 与纪律 6；`build.cmd` 注释用 **ASCII**（实测非 ASCII/非 CRLF 的 .cmd 会被 cmd 误解析） |
| `pdms-net/dist/pkpmjwd.uic`（Add-in 菜单注册）**〔R3〕** | **UTF-8** | **LF** | **无** | 与可照抄样例 `tgtext.uic` 逐字节同构（实测：3C 3F 78 开头无 BOM、41 LF/0 CRLF，本次 C16） |
| `<PDMS根>\DesignAddins.xml` / `DesignCustomization.xml`（deploy 改动时）**〔R3〕** | UTF-8 | CRLF | **带 BOM**（实测 EF BB BF） | 读写用 `utf-8-sig`、写回保留 BOM+CRLF；改前 `.pkpmjwd-bak`（§p.6） |
| PDMS 安装内 `.uic` / `DesignAddins.xml`（安装器追加菜单时） | UTF-8 | CRLF | **带 BOM**（惯例） | 改前必须 `.bak`（属 S3 安装包职责，本契约只规定纪律） |

**硬性纪律**

1. **禁止**用 `errors='replace'`/`ignore'` 静默吞掉解码失败；编码失败一律按 f.2 的码 2 退出。
2. **禁止**在任何产物里写 BOM —— 例外**仅**三处：`<PDMS根>\design.uic` / `DesignAddins.xml` /
   `DesignCustomization.xml`（实测带 BOM，属安装器/deploy 职责）与 `engine/section_table.csv`〔R2〕
   （数据文件，与源转化表一致，见 §k.2）。`pdms-net/dist/pkpmjwd.uic` **不带 BOM**（§g 表）。
3. 写 GBK 文件时，**先编码再写**（`text.encode('gbk')`，失败即报错），不要依赖平台默认编码。
4. 所有"用户原件"（`JLCJ2.jwd`、`1_PM.pdt`、`PKPM转PDMS截面匹配文件.txt`、`PKPM（PDMS数据库）.txt`、
   `P-TRANS\*`）**只读**；本包**不得**写入、改名、移动其中任何文件。
5. 所有"用户原件"统一按 §i 的路径清单访问；实施者**不得**把绝对路径硬编码进 `engine/*.py`
   （只有 `test/*` 允许，因为测试要跑样本）；引擎的输入路径一律由参数传入。
6. **〔R3〕`.cmd` 批处理 = ASCII 注释 + CRLF**：本次实测（C13 第一轮）LF-only 或含中文/§ 的
   `rem` 行会被 cmd 误解析成命令；写 `.cmd` 一律 `encoding='ascii'` + 显式 `\r\n`。
7. **〔R3〕不得写入 G 盘**（`G:\工作\…\PKPM导入导出插件\` 及其子目录只读）；交付落点见 §q-19。

---

## (h) 报告策略（`report.json`）

**每次转换必须写一份报告**（`--report` 指定或缺省同名文件）。缺省写入失败 ⇒ 按码 2 退出。
**不许静默跳过任何对象**：所有"没转/没解析/可疑"的东西都必须能在这份报告里查到。

```jsonc
{
  "contract_version": "1.0",
  "tool": "jwd2pdms",                       // jwd2pdms | pdms2jwd | pdt2model
  "source": "G:\\...\\JLCJ2.jwd",
  "source_format": "jwd",                   // jwd | pdt | pdmsdump
  "output": "D:\\...\\out.mac",
  "options": { "secmap": "...", "extra": "...", "project": "JLCJ2",
               "base": [0,0,0], "angle": 0, "unit": "mm" },
  "assumptions": [ "宏内不发出单位设置语句，需 PDMS 当前单位为 mm（契约 d.4-1）" ],
  "counts": { "levels":5, "joints":382,
              "members": {"beam":598,"column":200,"brace":13}, "members_total":811,
              "slabs":222, "slabs_holes":29, "slabs_with_thickness":80, "walls":0,
              "loads": {"beam-line":77,"joint-point":44}, "loads_total":121,
              "sections":28 },              // 直接来自 Model.counts()
  "sections": {
    "resolved": 23, "parametric": 5, "inferred": 1, "unresolved": 0, "total": 28,
    "detail": [ { "id":3985, "table":"col", "name":"薄壁方钢管: B25", "kind":303,
                  "status":"resolved", "source":"shapeval",
                  "pkpm_name":"6-B250*10.00",
                  "spec_path":"/RECT_SQUARE6728_2002-SPEC/B250*10.00",
                  "desp_params": [], "reason":"", "evidence":"",
                  "used_by": {"column": 2} },
                { "id":32335, "table":"brace", "name":"", "kind":3,
                  "status":"inferred", "source":"family", "pkpm_name":"CIRCLE",
                  "spec_path":"/USER_CIRCLE-SPEC/Circle_Profile",
                  "desp_params": [20.0],
                  "reason":"Kind=3 的族别按证据判为圆形（实心圆钢）；残余风险见 CONTRACT §e.3",
                  "evidence":"1_PM.pdt:2387-2388 SHAPE=3/KIND=3 B1=4800 NAME=圆形4800；…",
                  "used_by": {"brace": 12} } ],
    "unresolved": [ { "id":..., "name":"...", "kind":3, "status":"unresolved",
                      "candidate_keys":[...], "reason":"...",
                      "used_by": {"brace": 12} } ]
  },
  "geometry_anomalies": [ "W-MEM-ZRANGE: Member 63116(brace): end.z=13250 超出层区间 [-1000, 6600] 超过 10 mm" ],
  "skipped": [ { "what":"pkpmSlabHole", "count":29,
                 "why":"板洞几何已在 RoomIsHole=1 的 pkpmSlab 行里，避免重复建洞（jwd_format.md §1.4）" } ],
  "warnings": [ "板厚 T20 无匹配条目，需在 secmap_extra.txt 给出" ],
  "errors": [],
  "stats": { "tables": {...}, "rows": 5017 }     // write_jwd 的返回值（导出方向）
}
```

* `counts` **必须**直接取 `Model.counts()`（唯一出处，禁止各包各算一份）。
* `sections.detail` **必须覆盖每一个被用到的截面**（含板/墙厚度合成的）；`unresolved`
  是 `detail` 中 `status='unresolved'` 的子集，便于直接展示。
  顶层计数 `resolved/parametric/inferred/unresolved` 四类**都要给出**（§e.1a：`inferred` 不得
  混进 `resolved`——不确定性必须机器可见）；`inferred` 条目 `evidence` **必须非空**。
* `geometry_anomalies` **必须**包含 `Model.validate()` 的全部 `W-` 项（原文照抄），
  另可追加业务级异常（非零偏心统计、`HDiff` 异常值等）。
* `skipped` **必须**覆盖：未解码的非空表、被跳过的构件类型、`-` 规格的对象、被忽略的轴网 SCTN。
* `stdout` 必须打印一行摘要 + **未解析清单**（即使为空也要打印 `unresolved: 0`）。
* **〔R2〕数据库类子命令**（`jwd2db`/`pdt2db`/`db2jwd`/`db2pdt`/`dbsections`）在本结构上**追加** `db` 键
  （`macro_source`/`generated`/`parsed`/`cross_check`/`closure`/`losses`/`safety`），
  结构见 §m.3；v1 的键位与语义**不变**。
* **〔R3〕`renames` 键**（§o.7）：建模方向（`*2pdms`）经 PDMS 执行后**必须**并入；
  纯生成方向（引擎单独跑、未经 PDMS）写 `"renames": []`（键仍存在）。
  条目结构 `{"type","original","final","reason"}`；`type='FAIL'` ⇒ 上层（.NET/CLI）按错误处理（§o.6）。

---

## (i) 范围边界（**明令不做**）

1. **不改** `PDMSxCA_Addin.dll` / `PDMSxCA_Addin121.dll`（.NET + Dotfuscator，无源码），
   也不改 `P-TRANS\` 下任何文件；本包与现有插件**并存**，用户原有的 `.pdt` 流程不受影响。
2. **不改任何样本原件**：`JLCJ2.jwd`、`1_PM.pdt`、`PKPM转PDMS截面匹配文件.txt`、
   `PKPM（PDMS数据库）.txt`、`Pm[SPAS]转PDMS的信息提示.WRN`、`安装使用方法.txt`。
   缺口一律用 `engine/secmap_extra.txt` 补。
3. **不逆向 SPAS**（`CSpasDll` 封闭、本机无 `.spas` 样本，`pdms_target.md` §8.2）。
4. **不改 PDMS 安装内既有文件**；安装器只**新增** `PMLLIB\<包名>\` 并在
   `<PDMS根>\design.uic`、`<PDMS根>\DesignAddins.xml` 里**追加**条目，且改前备份
   （`.bak_<日期>`；这两个文件本就带 BOM，写回时必须保留 UTF-8+BOM+CRLF）。
5. **不删任何文件**（含本包自己的产物：改用覆盖写或 .new 后缀）。
6. 工作区外只允许写：`--out`/`--report` 指定的路径、安装器目标（PDMS 安装目录内的新增/追加项）。

---

## (j) `.pdt` 写出契约（`engine/pdt_write.py`）〔R2 §0.4-4/5/6〕

> 需求原文：「PDT 要完整导入 + 导出」「荷载不做」「生成的段名与行式必须与现有
> `PDMSxCA_Addin*.dll` 内的格式串**逐字一致**，否则现有插件读不了」。
> 本节的**唯一权威**是样本 `1_PM.pdt` 的逐字行式（本次 C7 实测）+ DLL 格式串（本次 C7 实测），
> 两者冲突处见 **j.8**，裁定为「**KEY 名/顺序**以 DLL 为准、**数值格式与空白**以样本为准」。

### j.1 签名与选项（**冻结**）

```python
@dataclass
class PdtOptions:                      # 定义在 engine/pdt_write.py
    file_note: str = ""                # 首行 ;File <file_note> saved <time> 的路径文本；缺省 = 输出文件绝对路径
    time_text: str = ""                # 时间文本；缺省 = 当前时间，格式 "M/D/YYYY H:M:S"（无前导零）
    designpara: list = None            # 50×20 的**原始文本**（行=list[str]）；None ⇒ 50 行 × 20 个 "0.000"
    materials: dict = None             # {材料名: {"type":int,"es":float,"pr":float,"exc":float,"ds":float}}
    skeleton: str = "full"             # "full"（13 段）| "sections-only"（§k 的 db2pdt 用）
    brace_type: str = "3"              # 支撑的 $SETELEMENT.TYPE（§j.4.5，冻结为 3）
    rigid: bool = True                 # 是否写 $RIGID（False ⇒ 段头仍写、体内为空）
    floor_index_base: int = 1          # 层号起始（$STORY.ID / FLOORID 的编号基准）

def write_pdt(model: Model, path: str, opts: PdtOptions | None = None) -> dict
def write_pdt_sections(sections: dict, path: str,
                       opts: PdtOptions | None = None) -> dict
```

* `sections = {"beam": [Section, …], "col": […], "brace": […]}`（canonical `Section`，
  `kind`/`mat`/`name`/`dims`/`shapeval` 已由 `sectionlib` 填好）→ **`db2pdt` 的唯一入口**。
* 返回（键固定，供 CLI 直接并入 `report.json`）：

```python
{ "segments": {"$VERSION": 2, "$DESIGNPARA": 51, "$STORY": 11, "$NODECOOR": 1235, …},
  "rows": 9678, "ids": {"materials": 5, "sections": 32, "joints": 617, "members": 1046, "panels": 331},
  "skipped": [ {"what": "section-shapeval", "id": 4080, "why": "Kind=2 不可回算，写占位块"} ],
  "warnings": [], "assumptions": ["荷载段只写段头（R2 §9.3）", "EXR 只写最小自洽集（§j.5）"] }
```

* **不写**任何文件以外的副作用；`opts=None` ⇒ 全部取缺省。

### j.2 文件级纪律（**冻结**，全部以样本为据）

1. **编码 GBK 无 BOM + CRLF**（§g）；写后必须回读校验：GBK 严格可解码、**不存在单 `\n`**（每个 `\n` 前必须是 `\r`）。
2. **段序 13 段**（逐字顺序，不得增删）：
   `$VERSION` → `$DESIGNPARA` → `$STORY` → `$NODECOOR` → `$NET` → `$DEFFRAMESECTION` →
   `$DEFWASLABSECTION` → `$DEFMATERIAL` → `$SETELEMENT` → `$SETWALL` → `$SETSLAB` → `$RIGID` →
   荷载分组头（`$DEADLOAD` / `$LIVELOAD`，见 j.6）→ `$END`。
3. 第 1 行 = `;File <file_note> saved <time_text>`（样本 L1）；第 2 行空行；第 3 行 `$VERSION`。
4. **每段 = 段头行 + 数据行 + 1 个空行**；`$DEADLOAD`/`$LIVELOAD` 是**分组头**，其后**紧随**其第一个子段头
   （样本 L8104→L8105、L8933→L8934，本次 C9 实测），分组头自身不带数据与空行。
5. **缩进即语法**（`pdt_format.md` §1.2【事实】）：记录行 **4 空格**；记录续行/普通续行 **7 空格**；
   `EXR` 续行 **8 空格**；`$RIGID.SLABID` 续行 **11 空格**。`>4` 一律按续行解析 ⇒ 精确到空格数。
6. 文件末：`$END` 前 **2 个空行**（样本 L9675/L9676）、`$END` 后 **1 个空行**（L9678）；
   即文件以 `$END\r\n\r\n` 结尾。
7. `$VERSION` 段体：`   4.2.0`（**3 空格**，样本 L4）。
8. **行尾空白不写**（§j.5 末条）：模板比对一律 `rstrip()`。

### j.3 全局 ID 编码（**冻结**）

**【事实】**（`pdt_format.md` §3.2）：`ID = N × 100 + CC`；本文件 2,841 个带 ID 对象的 `N` 恰填满 1..2,841、
无缺号、无跨类别复用。

`N` 从 **1** 开始，按**下列创建顺序**连续发号（每阶段内按给定序）：

| CC | 对象 | 发号顺序（v1+R2 无荷载 ⇒ 不为其留号） |
|---|---|---|
| 10 | 材料 | `opts.materials` 的键（或模型材料名集合）**升序** |
| 09 | 框架截面 | `Section.id` 升序 |
| 07 | 节点 | 合成节点按 `(z, y, x)` 升序 |
| 08 | 线段/构件 | 按 `(level.no, TYPE, id)` 升序 |
| 11 | 墙板截面 | 按厚度升序（每个不同厚度一行，§j.4.7） |
| 05 | 墙 | `Wall.id` 升序 |
| 06 | 板 | `Slab.id` 升序 |
| (12/13/14) | 荷载 | **不写**（R2 §9.3：荷载不做） |

* `$NET.ID == $SETELEMENT.ID`（同一构件共用 08 类码的**同一个 N**）【事实】1046/1046。
* `$STORY.ID`、`$RIGID.ID` 是**不带类码**的小整数（1..k）。
* **节点合成**（canonical 的 `Member` 只有端点坐标，没有节点）：每个唯一坐标 → 一个节点，
  唯一性按 `round(v, 6)` 归一后比较；节点 `FLOORID` = 该 Z 所属 Level 的 `no`。
* **禁止**用 ID 数字反推结构关系（`pdt_format.md` §3.2 结论）。

### j.4 逐段写出规范（模板逐字；`\u2420` 表示**不写行尾空白**）

> 下表「行式模板」是从样本逐字抄下来的（本次 C7），`<…>` 为变量；`%.2f`/`%G` 等是数值格式。

| # | 段 | 行式模板（逐字） | 数据来源 | 证据 |
|---|---|---|---|---|
| j.4.1 | 首行 | `;File <note> saved <M/D/YYYY H:M:S>` | `opts.file_note` / `opts.time_text` | 样本 L1 `;File I:\…\1_PM.pdt saved 3/19/2025 8:4:27` |
| j.4.2 | `$VERSION` | `$VERSION` / `   4.2.0` / 空行 | 常量 | 样本 L3–L5 |
| j.4.3 | `$DESIGNPARA` | `$DESIGNPARA` / 50 行，每行 `    ` + 20 个值以 `, ` 连接 / 空行 | `opts.designpara`（原样）；None ⇒ `0.000`×20×50 | 样本 L6–L57（L7 首行 `    0.000, 0.000, 3.000, …`） |
| j.4.4 | `$STORY` | 每条 2 行：`    ID=<n>, NUB=1` / `       NO=1, HI=<int>, BL=<int>, TL=<int>, WID=<%.2f>, LEN=<%.2f>, HEI=<%.2f>` | `Level`（`BL=z_bot`、`TL=z_top`、`HI=height`、`WID/LEN`= 该层节点 X/Y 极差、`HEI`= 该层构件最大竖向跨度，样本 §8.3） | 样本 L58–L68；DLL 0x033E3D |
| j.4.5 | `$NODECOOR` | 每节点 2 行：`    ID= <id>, X= <%.2f>, Y= <%.2f>, Z= <%.2f>, FLOORID= <n>` / `       EXR= <k> ,<10005>, <fl> ,<10012>, <fl>e+06` | 合成节点（j.3）；`EXR` 见 j.5 | 样本 L71–L76（`FLOORID= 2` 带空格、坐标 2 位小数） |
| j.4.6 | `$NET` | `    ID=<id>, NODES=<jid>, NODEE=<jid>` | 构件两端节点 ID（j.3） | 样本 L1306+；DLL 0x0203DC |
| j.4.7 | `$DEFFRAMESECTION` | 每条 5 行：`    ID=<id>, NAME=<name>, SHAPE=<shape>` / `       KIND=<k>, B1=<b1>, B2=0, H1=<h1>, H2=0, B3=0, H3=0` / `       T1=0, T2=0, T3=0, T4=0, T5=0, T6=0` / `       M=<m>, RI=0.000, RJ=0.000, UA=0.000, NAME1=<name1>` / `       EXI=1, 10011, <id>` | `sectionlib.encode_defframesection`（§k.3） | 样本 L2367–L2371；DLL 0x033B1C/0x033B81/0x033C05/0x033C75/0x0202DB |
| j.4.8 | `$DEFWASLABSECTION` | `    ID=<id>, NAME=T<厚度%g>, TYPE=1, T1=<%.2f>, T2=0.00` | 模型里每个**不同**板/墙厚度一行 | 样本 L2529–L2532；DLL 0x033E3D 第二串 |
| j.4.9 | `$DEFMATERIAL` | `    ID=<id>, NAME=<n>, TYPE=<261\|262>, ES=<%G2>, PR=<%G2>, EXC=<%G5>, DS=<%G5>` | `opts.materials`，缺省 = j.9 内置表 | 样本 L2535–L2539；DLL 0x020344 |
| j.4.10 | `$SETELEMENT` | `    ID=<id>, TYPE=<1\|2\|3>, NETID=<id>, SECTID=<sid>, MATID1=<mid>, MATID2=-9999, ECS1=0.000, ECS2=0.000, ECS3=0.000, ECE1=0.000, ECE2=0.000, ECE3=0.000, ANG=<%.3f>` + `EXI`(j.5) + `EXR`(j.5) | 构件（TYPE：1=柱、2=梁、**3=支撑**见下）；`ECS/ECE` **一律 0.000**（§j.7.2）；`MATID2=-9999`= 无次材料 | 样本 L2542–L2545；DLL 0x020183/0x020154 |
| j.4.11 | `$SETWALL` | `    ID=<id>, TYPE=5, SECTID=<sid>, MATID=<mid>, MATID2=0, HOLEID=-9999, EC=0.0` / `       NUB=<n>, NETID= <id>, <id>, …` + `EXI` + `EXR` | `Wall`（`NETID` = 该墙回路的边，v1 模型里回路由 `loop` 合成） | 样本 L6729–L6733；DLL 0x033D24 |
| j.4.12 | `$SETSLAB` | 同 j.4.11 但 `TYPE=6` | `Slab`（`is_hole=True` 的板**不写**，见 j.7.3） | 样本 L6751–L6754 |
| j.4.13 | `$RIGID` | `    ID=<n>, FLOORID=<n>, NUB=<n>` / `       SLABID= <id>, …`（**每行 20 个**，续行 **11 空格**） | 每层一个组，`SLABID` = 该层板 ID 升序 | 样本 L8077–L8102；本次 C9（每行恒 20 个、缩进 11） |
| j.4.14 | 荷载段头 | 见 j.6（**只写段头**） | — | 样本 L8104–L9676（25 个段头，本次 C9 实测） |
| j.4.15 | `$END` | `$END` | — | 样本 L9677 |

**j.4.5 之补充（`TYPE` 词表与支撑）**：`1`=柱、`2`=梁【事实】；**`3`=支撑**〔R2 冻结，§0.4-5〕。
依据：样本无支撑（`pdt_format.md` §5.1「本文件无斜撑」）⇒ 无直证；但写 1/2 会静默改类型，
写其它未映射值会被读端丢弃构件（`engine/pdt_read.py:471`）⇒ 两端必须以同一码约定。
`pdt_read` 必须同步：`TYPE=3 → Member.type='brace'`（水平/竖向由 `|ΔZ| ≤ 1e-6` 判，同 §d.4-2），
并把「TYPE ∉ {1,2,3} 不进 members」的 notes 文案改成只覆盖真正的未知值。**待实机确认**（§12#15）。

### j.5 `EXI` / `EXR` 的精确构造（计数自洽，**冻结**）

**`EXI` 行**（每条记录最多 1 行，不折行）：

| 记录 | 模板 | 组数 k |
|---|---|---|
| 截面（`$DEFFRAMESECTION`） | `       EXI=1, 10011, <自身ID>` | 1 |
| 构件/墙/板 | `       EXI=3, 10011, <自身ID>, 10013, <混凝土等级>, 10014, <钢牌号>` | 3 |
| 节点 | **不写**（样本无 `EXI`，见 L71–L76） | — |

`10013/10014` 由材料名解析（冻结）：`C##` → `(##, 0)`；`Q###` → `(0, ###)`；**无材料名或认不出 → `(30, 0)`**
（样本 1040/1046 条为 `30, 0`）——该兜底必须写进报告的 `assumptions`。

**`EXR` 行**（**每行最多 10 组**，续行 **8 空格**；`k` = 该记录实际组数，必须自洽）：

| 记录 | 模板（首行） | 键集（最小自洽集） |
|---|---|---|
| 节点 | `       EXR= <k> ,<id>, <val> ,<id>, <val>`（注意 `= ` 后有空格、每组前是「空格+逗号」） | `10005,<楼层> ,<10012>,<楼层×1e6>`（样本 `EXR= 2 ,10005, 2 ,10012, 2e+06`） |
| 构件（`$SETELEMENT`） | `       EXR=<k>, <id>, <val>, <id>, <val>`（`=` 后**无空格**） | `-41,<TYPE>, -40,<楼层>, 10005,<楼层>, 10012,<楼层×1e6+层内序号>` ⇒ k=4 |
| 墙/板 | 同构件 | `-41,<TYPE>, -40,<楼层>, 10005,<楼层>, 10012,<楼层×1e6>` ⇒ k=4 |

* **不写**的 EXR 键（样本有、语义未证；逐条列入报告 `assumptions`）：
  `-1004..-1001`、`-119`、`-90..-86`、`-84`、`-82`、`-73`、`-71`、`-67`、`-64`、`-63`、`-59`、`-58`、
  `-57`、`-44`、`-43`、`-42`、`10001..10003`、`10217`（来源：`pdt_format.md` §6 的未确证清单）。
* **行尾空白不写**：样本同类行不一致（`       EXI=1, 10011, 609` 无尾空格、`       EXI=3, …, 10014, 0 ` 有）
  ⇒ 判定为**非语义**；本契约要求不写，验收比对一律 `rstrip()`。
* 折行不变量：**任何行 ≤ 10 组**、续行缩进精确 8 空格；`$STORY`/`$FORMAT` 之外的行不折行（样本实测
  `EXR` 最长 149 列、续行最长 138 列，本次 C9）。

### j.6 荷载：**只写段头，体内为空**〔R2 §9.3〕

```
$DEADLOAD
$DEFNODELOAD

$SETNODELOAD

$DEFLINELOAD

$SETLINELOAD

$DEFSLABLOAD

$SETSLABLOAD

$LIVELOAD
$DEFLINELOAD

$SETLINELOAD

$DEFSLABLOAD

$SETSLABLOAD

```
* 与样本**同构**：`$DEADLOAD` 组含 6 个子段头、`$LIVELOAD` 组含 4 个（样本的活载组没有
  `$DEFNODELOAD`/`$SETNODELOAD`，本次 C9 实测 L8933–L8934、L9010、L9343）；
* 分组头**紧随**其首个子段头（j.2-4）；每个空子段头后写 **1 个空行**（保持"段末空行"规则一致）；
* 报告必须写明：`assumptions: ["荷载不导出（R2 §9.3）"]`，且 `counts.loads` 照常统计（canonical 仍解析荷载）。

### j.7 无法表达的对象：**占位 + 报告，绝不丢构件**

1. **截面不可回算**（`encode_defframesection` 抛 `unencodable`，例如 `Kind=2`、`Kind=303`、
   `Kind=26` 且族码 ≠ 39）⇒ 写**占位块**（5 行，数值全 0、`M=<mat 或 5>`、
   `NAME=<Section.name 或 "<kind>#<params 原文>">`、`SHAPE=<kind>`），并在 `skipped` 记
   `{"what":"section-shapeval","id":…,"why":…}`；引用它的构件**照写**。
2. **偏心**：canonical 的 `start/end` **已含偏心**（v1 §a.5）⇒ `ECS1..ECE3` 一律写 `0.000`，
   **不得**把 `Member.ecc` 再写进去（否则二次施加）。原始 `ecc` 只进报告。该决定写进 `assumptions`。
3. **板洞**：`Slab.is_hole=True` 的板**不写** `$SETSLAB`（`.pdt` 里板洞由 `HOLEID` 表达，语义未证 ⇒ 不猜），
   逐条进 `skipped`（`what="slab-hole"`）；`is_hole=False` 且 `thickness<=0` 的"房间"也**不写**并记 `skipped`。
4. **墙**：`Wall.loop` 非 4 点或非竖直平面 ⇒ 按 `NETID` 环顺序写出全部边（`NUB=len(NETID)`），
   点不足 3 个 ⇒ `skipped`。
5. **材料缺表**：材料名不在 `opts.materials` 也不在内置表（j.9）⇒ 用 `(262, 3e4, 0.2, 1e-5, 25)` 兜底
   并记 `warnings`（**不得**猜钢号）。
6. `skeleton="sections-only"` ⇒ 只写 首行 + `$VERSION` + `$DESIGNPARA` + `$DEFFRAMESECTION` + `$END`；
   `skeleton="full"`（**缺省**，也是 `db2pdt` 的缺省）⇒ 写全 13 段，其中 `$DEFFRAMESECTION` 由 `sections` 填、
   其余几何段**只有段头与空行**（0 条记录）；`$SETWALL`/`$SETSLAB`/`$SETELEMENT` 为空段是**合法**的
   （Add-in 按 KEY 解析，空段不产生构件）——若实机证明空段会报错，走契约变更，**不得**擅自补造数据。

### j.8 与 DLL 格式串的**已知差异**（必须知道，不得"改正"）

| 位置 | DLL 格式串（偏移，本次 C7 实测） | 样本实测 | 冻结裁定 |
|---|---|---|---|
| `$STORY` | 0x033E3D `WID={4:G2}, LEN={5:G2}, HEI={6:G2}` | `WID=15200.00, LEN=49400.00, HEI=12000.00`（**2 位小数**） | **以样本为准**（`%.2f`） |
| `$NODECOOR` | 0x02041E `ID= {0}, X= {1:F2}, …` | 一致 ✓ | 用 DLL |
| 节点 `EXR` | 0x02029F `       EXR= {0} ` + 0x0202C1 `,{0}, {1} ` | `       EXR= 2 ,10005, 2 ,10012, 2e+06`（数值是 `2e+06` 的 G 形式） | 用 DLL 的**空白布局** + G 形式数值 |
| 元素 `EXR` | 同上（会得到 `EXR= 19 ,-1004, …`） | `       EXR=19, -1004, 0.000, …`（`=` 后无空格） | **以样本为准**（两种形态并存 ⇒ 见下） |
| `EXI` | 0x0202DB `       EXI= {0} ` + `,{0}, {1} ` | `       EXI=1, 10011, 609` / `EXI=3, …, 10014, 0 ` | **以样本为准** |
| `$DEFMATERIAL` | 0x020344 `{3:G2}/{4:G2}/{5:G5}/{6:G5}` | `3e+04 / 0.2 / 1e-05 / 26`（**e 小写**；`G` 默认是大写 `E`） | 格式规则见 j.9（`%G` 后 `E→e`） |
| `ECS/ECE/ANG` | 0x020154 `    {0:F3},` | `0.000` ✓ | 用 DLL |
| 墙/板 `EC` | 0x033D24 `EC={6:F1}` | `EC=0.0` ✓ | 用 DLL |
| `$RIGID` | 0x033D24 区 `    ID={0}, NUB={1}` + `SLABID=` | `    ID=1, FLOORID=1, NUB=101` + 每行 20 个 | **以样本为准**（含 `FLOORID`；每行 20 个） |

**裁定原则（写进实现注释与报告）**：段名、`KEY` 名与**其顺序**以 DLL 格式串为准（这是 Add-in
按名解析的硬要求）；**数值格式、小数位、空白布局**以样本为准（样本是 Add-in 自己写出、也读得回去的
现成往返证据）。两处不一致是**同一程序两版/两条代码路径**的痕迹，实现**不得**自行"统一"。

### j.9 材料内置表（`opts.materials` 缺省值）

取自样本 `$DEFMATERIAL`（`1_PM.pdt:2535-2539`，本次 C7 逐字复核）——**同名多定义时取被构件引用的那条**：

| 名称 | `TYPE` | `ES` | `PR` | `EXC` | `DS` | 说明 |
|---|---|---|---|---|---|---|
| `C30` | 262 | 3e+04 | 0.2 | 1e-05 | **25** | 样本里 `C30` 有 `DS=26`(ID 110) 与 `DS=25`(ID 310) 两条；构件实际引用 **310**（`MATID1=310`）⇒ 取 `25` |
| `Q235` | 261 | 2.1e+05 | 0.3 | 1e-05 | 78 | ID 210（样本里另一条 410 用 `EXC=1.2e-4/DS=78.5`，6 根钢梁用它） |
| `Q345` | 261 | 2.1e+05 | 0.3 | 0.00012 | 78.5 | ID 510 |

数值格式（**冻结**）：`%.2G`/`%.5G` 后把 `E` 替换为 `e`；整数值不带小数点 ⇒
`3e+04`、`2.1e+05`、`1e-05`、`0.00012`、`26`、`78.5`、`0.2`；`TYPE` 写整型；其余字段如 `$STORY` 用 `%.2f`。
【推断-高】`261`=钢、`262`=混凝土（由 `NAME`/`ES`/`DS` 交叉验证，`pdt_format.md` §2.8）。

### j.10 往返验收（可执行，对应计划 §9.4-9）

1. **行式静态一致**：逐行 `rstrip()` 后必须匹配 j.4 的模板；段名集合 = j.2 的 13 段；缩进符合 j.2-5。
2. **计数自洽**：每个 `EXI/EXR` 行的 `k` = 该行实际组数；`NUB` = 列表长度；`NEW`-`END`（本段无）；
3. **往返等价**：`Model --write_pdt--> .pdt' --read_pdt--> Model'` 满足：
   `levels` 的 `(z_bot,z_top,height)` 多重集相同、`members` 的 `(type, 端点四舍五入到 0.01 mm)` 多重集相同、
   `slabs/walls` 的顶点集合相同、包围盒相同、`Model'.errors()` 为空。
4. **不要求**与样本 `1_PM.pdt` 逐字节相同（ID 发号顺序与 EXR 键集不同，j.3/j.5）；比对一律 `rstrip()`。
5. 报告必须含：段行数、ID 分配表、未复刻的 EXR 键、占位截面、材料兜底、`assumptions`。

---

## (k) 截面转化核心（`engine/sectionlib.py`）〔R2 §0.4-4〕

> 这是 R2 的**新核心**：其它新模块（`pdt_write`/`dbmacro`/`dbparse`/CLI）都依赖它。
> 它把「PKPM 侧截面定义（`.jwd` 的 Kind/ShapeVal、`.pdt` 的 `$DEFFRAMESECTION`）」与
> 「PDMS 侧截面库（Catalogue/Specification 的 SPRFILE/SPCOMPONENT）」双向互算，
> 并**逐项申报信息损失**。

### k.1 数据类（**冻结**）

```python
@dataclass
class ParamDef:
    name: str            # 参数名原样（含单位括号，如 'h(mm)'、'B1'、'Parameter 1'）
    desp_index: int      # is_parametric=True ⇒ 1..N（= DESP[n] 的下标）；否则 0
    default: str         # 默认值原文（来自 SPRFILE.PARA / DTSET.DPRO）；无 ⇒ ''

@dataclass
class SectionRec:
    key: str             # 唯一键：pkpm_name 非空则用它，否则用 pdms_spec_path（实测 3,176/3,176 唯一）
    pkpm_name: str       # PKPM 侧截面名（可为空：目录里存在但匹配文件没有的条目）
    family_code: int     # PKPM 族码（0 = 未知）
    family_name_cn: str  # 族的中文名（原样，含 ' | ' 分隔的英文描述）
    kind: int            # .jwd/.pdt 的 Kind/Shape（0 = 未知；仅样本观测到值）
    shapeval: str        # PKPM 侧编码串（.jwd 的 ShapeVal 或 DLL 编码串；原样）
    dims: dict           # 尺寸（键空间同 §a.4；空 = 未知）
    mat: int             # 5=钢 6=混凝土（内置表默认 5；见 k.2）
    pdms_spec_path: str  # PDMS 规格路径（SPCOMPONENT 全名，形如 /C_COMMON-SPEC/[5）
    pdms_catalogue: str  # 所属 CATALOGUE（/PKPM_STSS、/PKPM_USER，可空）
    is_parametric: bool  # True = 参数化族（DESP 驱动）
    params: list         # list[ParamDef]
    confidence: str      # 'high' | 'medium' | 'low' | 'unknown'
    source: str          # 溯源串（原样，如 'macro+match+dll_explicit'）
    extra: dict = {}     # 其余溯源信息（无损保留；见 k.2）

    def to_dict(self) -> dict: ...        # JSON 友好；键序固定
    @classmethod
    def from_dict(cls, d) -> "SectionRec": ...

class SectionTable:
    recs: list[SectionRec]
    def get(self, key=None, pkpm_name=None, pdms_spec_path=None) -> SectionRec | None
    def by_family(self, family_code: int) -> list[SectionRec]
    def to_csv(self) -> str ; @classmethod def from_csv(cls, text_or_path) -> "SectionTable"
    def to_json(self) -> str ; @classmethod def from_json(cls, text_or_path) -> "SectionTable"
    def validate(self) -> list[str]
    def to_jwd_sections(self) -> dict      # {"beam":[Section,...],"col":[...],"brace":[...]}（canonical 对象）
    def loss_report(self, direction: str) -> list[dict]

def load_builtin_table() -> SectionTable    # 读 engine/section_table.csv
def table_from_jwd(model: Model) -> SectionTable
def table_from_pdt(model: Model) -> SectionTable
```

* `confidence` 词表**冻结**为 `{high, medium, low, unknown}`；未知一律 `unknown` 且 `extra['reason']` 必填。
* `key` 唯一性是**实测**（本次 C8）：`pkpm_name` 非空 2,835 条且互不重复；`pdms_spec_path` 3,176 条互不重复；
  两者取值域不相交（名字不以 `/` 开头）⇒ `key` 规则无碰撞。
* `SectionTable.get()` 的匹配规则：空白归一化、**不改大小写**（同 §e.2）；`pdms_spec_path` 查询时补前导 `/`。

### k.2 内置转化表 `engine/section_table.csv`（**冻结的数据文件**）

* **性质**：数据文件（不是代码），由 `test/build_section_table.py` 从
  `_recon/dbsect/pkpm_pdms_section_table.csv`（3,176 行 × 38 列）**机械投影**而来；
  `sectionlib` **只读**，不得改写。重跑生成器必须**字节一致**（幂等）。
* **编码**：UTF-8 **带 BOM** + CRLF（§g 的例外行；与源表一致，Excel 可直接打开）；
  `from_csv` 必须用 `utf-8-sig` 读，兼容无 BOM。
* **规模（本次 C8/C10 实测）**：3,176 行；键唯一 3,176；`pkpm_name` 非空 2,835 且唯一；
  `pdms_spec_path` 唯一 3,176（全部形如 `/X/Y`，57 个规格属主）；`shapeval` 非空 2,335；
  `family_code` 已知 2,335；`is_parametric=true` 15 条；`confidence` = high 1,146 / medium 1,433 / low 597；
  文件 **4,815,297 B**（含 BOM；体积集中在 `params_json` 1.75 MB 与 `extra_json` 1.90 MB ——
  前者是具名参数表，后者是溯源列，**都是审计/交叉核对所需**，不得为了"减肥"删列）。
* **列序（15 列，冻结，不得增删改序）**：

```
key, pkpm_name, family_code, family_name_cn, kind, shapeval, dims_json, mat,
pdms_spec_path, pdms_catalogue, is_parametric, params_json, confidence, source, extra_json
```

* **投影规则（逐条对应生成器）**：

| 列 | 来源 | 规则 |
|---|---|---|
| `key` | 派生 | `pkpm_name` 非空 → 用它；否则 `pdms_spec_path` |
| `pkpm_name` / `pdms_spec_path` / `pdms_catalogue` | 同名源列 | 原样（去首尾空白） |
| `family_code` | 源列 | `int`；空 → `0` |
| `family_name_cn` | 源列 `family_cn` | 原样 |
| `kind` | 源列 `jwd_kind` → `pdt_kind` | 取第一个非空；都空 → `0` |
| `shapeval` | 源列 `shapeval_encoding` | 原样（DLL 编码串；空 ⇒ `''`） |
| `dims_json` | 派生 | ① 按 `family_code` 的**位置规则**（k.3 表）解 `shapeval`；② 再用该行 `stcategory_params`（或 `param_names`）的**具名参数**补齐**尺寸类**键（`h→H, b→B, tw, tf, t, d, r`）；③ 两者都有且不等 ⇒ `extra['param_check']='mismatch: …'`（**不修改**任一侧） |
| `mat` | 常量 | **5（钢）**：内置表的条目全部来自 PDMS 钢结构目录（`PURP STL`）；`.jwd`/`.pdt` 给出的真实 `Mat` 优先（调用方覆盖） |
| `is_parametric` | 源列 | `'true'` → `True`（Python）/ 冻结文字 `true\|false`（CSV） |
| `params_json` | 源列 `param_names` × `para_values` | 按 `\|`/空白对位；`desp_index = i+1` **仅当** `is_parametric=true`，否则 `0` |
| `confidence` / `source` | 同名源列 | 原样 |
| `extra_json` | 其余源列 + 派生 | 未进上表的 24 列原样保留；另加 `params_named`（**全部**具名参数，无损）、必要时 `param_check` / `param_len_mismatch`；以及 `dll_siblings`（变更记录 §0.4-8：recon §2.6 的 **DLL 名集**里、归一键（norm_pkpm2）与该行相同而该行 `dll_table_entry`/`name_variants` 未记录的拼写，`;` 连接）——源表把"冷弯/热轧同名异族"两行标成同一个 DLL 拼写，不派生此列则 §l.5 的 759 对大小写/写法差异只归得出 751 对。只补 DLL 里真实存在的拼写，**不得**引入表外字符串（口径不得放大） |

* **JSON 列格式**：`json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',',':'))`（确定性）；
  `from_csv` 用 `json.loads` 还原。**禁止**用 `eval`。
* **元数据**：`engine/section_table.meta.json`（UTF-8 无 BOM）记录源文件路径、源 sha256、源行数、
  产物行数/列序/sha256、以及 k.2 的统计数字 —— 验收（计划 §9.4-14）比对的就是这两份文件。
* **缺口现状（必须照实报告，不得"修表"）**：256 条右值在目录宏里不存在（Double-L 三族的缩写不一致，
  `conflicts.md` §2.2）、4 条右值原本缺前导 `/`（已在源表里补齐，本次 C8 确认补后命中宏）。

### k.3 编解码四件套（**冻结**）

```python
def decode_shapeval(kind: int, shapeval: str) -> dict        # §a.4 的唯一实现（不得另写一份）
def encode_shapeval(rec: SectionRec, sec_id: int = 0,
                    mat: int | None = None) -> str            # 回算 .jwd 的 ShapeVal
def decode_defframesection(block: list[str]) -> dict          # 5 行 → 字段字典
def encode_defframesection(rec: SectionRec, sec_id: int = 0,
                           mat: int | None = None) -> list[str]  # 字段字典 → 5 行（j.4.7 模板）
```

**`encode_shapeval` 规则（Kind → 输出；`id` = `sec_id` 或 `rec.extra['jwd_id']`）**

| Kind | 输出模板 | 前置条件 | 证据 |
|---|---|---|---|
| 1 | `1,<B>,<H>,<mat>,<id>,` | `dims` 有 `B`/`H` | 样本 `1,300,600,6,1380,` |
| 3 | `3,<d>,<mat>,<id>,` | `dims` 有 `d` | 样本 `3,20,5,32335,`；§12#5 的 `CIRCLE` 推断 |
| 26 | `26,<family>,<subtype>,<H>,0,<B>,<tf>,<tw>,0,<mat>,<id>,` | **仅 `family==39`** | 样本 `26,39,1,450,0,200,14,9,0,5,4484,`；本次 C10 用目录宏 `PARA`（`h,b,tw,tf`=450,200,9,14）复现出同一串 ⇒ 闭环成立 |
| 303 | `303,77,<打包串槽 6 个>,…,<d>,0,<d>,0,…<槽27>…,<mat>,…,<槽32>…,-1,<id>,` | `dims` 有 `spec_str`/`d`/`lib_family` | 槽位（**split 下标**，本次 C12 实测 3/3 条样本）：`0=303`、`1=77`、`2..7`=打包串（每槽 2 字符、低字节在前、遇 0 结束）、**`18`=d、`20`=d**、`27`=库族码、`30`=mat、`32`=形状码（方矩 `16672`/圆 `16640`）、`81=-1`、`82`=自身ID，其余 0；末尾还有一个空字段 ⇒ `split_len=84`。**矩形管**（`B<a>*<b>*<t>`）的槽 20 应为另一边长 —— **未观测** ⇒ 记 `unknown` 并沿用 `d` |
| 其它 | **抛 `ValueError("unencodable")`** | — | 不得降级成空串；调用方必须记报告 |

* 数值格式：整数写整数、小数用 `repr(float)`（如 `6.5`）；**末字段后必须保留 `,`**（样本如此）。
* 打包串编码（Kind=303）是 §a.4 解码的逆：ASCII 规格串按 2 字符切、每槽 `lo | (hi<<8)`（首字符在低字节），不足补 0。
* **已实测的闭环**（本次 C11 自动断言）：① `Kind=26`（族码 39）由内置表 `HN450X200` 的 `dims`
  回算出 `26,39,1,450,0,200,14,9,0,5,4484,` —— 与 `.jwd` 样本**逐字相同**；
  ② `Kind=303` 由内置表的 `spec_str`/`lib_family`/`d` 回算 3 条（ID 3985 / 62965 / 12729）——
  与 `.jwd` 样本**逐字段相同**（各 84 字段）。

**`encode_defframesection` 规则（→ j.4.7 的 5 行）**

| rec | `SHAPE`/`KIND` | `B1` / `H1` | `T1..T6` | `M` | `NAME1` |
|---|---|---|---|---|---|
| `Kind=1` | `1` | `B` / `H` | 全 0 | `mat` | `''` |
| `Kind=3` | `3` | `d` / `0` | 全 0 | `mat` | `''` |
| `Kind=26` 且 `family=39` | `39` | `B` / `H` | 全 0（**样本如此**：厚度靠 `NAME1` 查库） | `mat` | `pkpm_name` |
| 其它 | `<kind>` | `0` / `0` | 全 0 | `mat` 或 `5` | `pkpm_name`（**占位块**，报告留痕） |

* `M` 的规则（§0.4-10 修订，R3 复核发现⑧）：**按 SHAPE 取**——`SHAPE=1/3 → M=6`、
  `SHAPE=39 → M=mat`（目录宏记录 mat=5 ⇒ 5）；`mat ∉ {5,6}` ⇒ 记 `unknown` 并写 `5`。
  依据：样本全部 3 个观测点（29 条 SHAPE=1 与 1 条 SHAPE=3 全部 `M=6`（如 1_PM.pdt:2370）、
  2 条 SHAPE=39 全部 `M=5`（如 :2515））——旧冻结 `M=mat` 会让目录宏模板的 SHAPE=1/3 行写 5，
  与样本**全部**观测相悖（实测 db2pdt.pdt 的 M 分布 {5: 1845}，其中含 SHAPE=1/3）。
* `decode_defframesection` 必须容忍 `RI/RJ/UA` 的 3 位小数、`T1..T6` 为 0、`NAME1` 为空。

### k.4 PDMS 侧：`to_pdms` / `from_pdms`（**优先级唯一**）

```python
def to_pdms(rec: SectionRec, secmap=None) -> dict
    # {"spec_path": str, "desp_params": list[float], "status": "resolved|parametric|unresolved",
    #  "source": "builtin|secmap|family|none", "reason": str}
def from_pdms(spec_path: str, secmap=None) -> SectionRec | None
```

* `to_pdms` 的**唯一优先级**（与 §e 的语义一致，不得另立一套）：
  1. `rec.pdms_spec_path` 非空 ⇒ `status='resolved'`、`source='builtin'`；`desp_params` =
     `rec.is_parametric` 时取 `params[i].default`（数值化）否则 `[]`；
  2. 否则 `secmap` 给定时调 `secmap.SectionMap.resolve(...)`（**复用 §e 的四级优先级**，含 `inferred`），
     `source='secmap'`；
  3. 否则按 §e.3 的**用户参数化族模板**（`status='parametric'`，`source='family'`）；
  4. 全失败 ⇒ `status='unresolved'`、`source='none'`、`reason` 必填（写法同 §e.5）。
* `from_pdms`：归一化（去空白、补前导 `/`、**不改大小写**）后依次查
  ① 内置表 `pdms_spec_path` → ② `secmap.reverse()` 得 PKPM 名再查内置表 `pkpm_name` → ③ 都没有 ⇒ `None`
  （**禁止**猜：不返回 fabricated 记录）。

### k.5 信息损失申报（`loss_report(direction)`）

`direction ∈ {'jwd2db','db2jwd','pdt2db','db2pdt'}`；返回 `list[dict]`，每项
`{"field":…, "severity":"loss|partial|unknown", "reason":…, "evidence":…}`。**冻结清单**：

| direction | 项 | severity | 说明与证据 |
|---|---|---|---|
| `jwd2db` | 工程自定义截面（Kind=1/2/3 的具体尺寸）只能落参数化模板 | `partial` | 尺寸变 DESP 参数；`db_pkpm_sections.md` §7.1（`.pdt` 30 个 `矩*` 均落 `/USER_RECT-SPEC/Rectangle_Profile`） |
| `jwd2db` | `.jwd` 无力学量（A/g/Ix/Wx…） | `loss` | PARA 只有目录里有；样本 `$DEFFRAMESECTION` 只有 6 尺寸 + 6 厚度 |
| `jwd2db` | `Kind=1` 的 `B/H` 先后为【推断-中】 | `unknown` | v1 §12#3 |
| `db2jwd` | 族码 `19`/`TRAPEZOID`/`DOUBLE_C`/`RECT` 的族码值未解 | `unknown` | `db_pkpm_sections.md` §2.3/§8.3；conflicts §4.3 |
| `db2jwd` | `Kind=26` 的族码 ≠ 39 时 6 尺寸槽顺序未知 ⇒ **不可生成** | `unknown` | §4.2（仅族码 39 能靠名反推）；§12#19 |
| `db2jwd` | `Kind=2` 字段语义未知 ⇒ **不可生成** | `unknown` | `jwd_format.md` §9.3#5；conflicts §3 |
| `db2jwd` | `Kind=303` 的槽 27/32 只能按规则推（27=名前缀、32=方/圆） | `partial` | 3 条样本 + 本次 C10；§12#20 |
| `db2jwd` | 目录宏 `PARA` 的数值精度高于 PKPM 自己的取整（`HN300X150` 的 `tw`：PARA 6.5 vs `.jwd` 6） | `partial` | 本次 C10 实测（`jwd_format.md` §3.2 的「PKPM 取整」） |
| `db2pdt` | `PARA` 的 13–27 项（力学量/截面特性）在 `.pdt` 无字段 | `loss` | `pdt_format.md` §2.6；`db_pkpm_sections.md` §5.1 边 C |
| `db2pdt` | 型钢 `tf/tw` 不进 `T1..T6`（样本恒 0） | `loss` | 样本 32/32 条 `T1..T6=0`；§3.3 |
| `db2pdt` | `M` 只有 3 个观测点 | `unknown` | §3.3；§12#17 |
| `db2pdt` | `RI/RJ/UA` 全 0、语义未证 | `unknown` | §3.3 |
| `db2pdt` | `EXI` 第 2 数 `10011` 语义未证（照抄） | `unknown` | §3.3 |
| `pdt2db` | 型钢 `tf/tw` 缺失 ⇒ PARA 的 `tw/tf` 只能取自目录宏 | `partial` | 同上一行；§7.1 |
| `pdt2db` | `$DESIGNPARA`/`EXR` 语义未证 ⇒ 不进数据库 | `loss` | `pdt_format.md` §4/§6 |

---

## (l) PDMS 目录/规格宏：生成与解析（`engine/dbmacro.py` / `engine/dbparse.py`）〔R2 §0.4-4/7〕

### l.1 安全约束（**硬，实现必须自校验**）

1. 生成的宏**只允许**创建/修改**本包自己的 4 个容器**：`opts.catalogue_user`、`opts.catalogue_stss`、
   `opts.spec_world_user`、`opts.spec_world_lib`（缺省见 l.2，全部带 `/PKPM_JWD_` 前缀）。
2. **禁止**：宏内出现 `NEW`/`OLD`/`DELETE` + 用户既有容器名
   （`/PKPM_USER`、`/PKPM_STSS`、`/PKPMDATA`、`/PKPM_USER_SECTION`、`/PKPM_LIB`）。
   实现必须做一次**字符串扫描自检**，命中即 `ValueError`（不得"警告后继续"）。
3. `clean_first=True` 时，清场语句的目标**必须 ∈ 上述 4 个容器**（含 `suffix` 后的实际名），
   否则 `ValueError`；清场只允许出现在**本包容器**上。
4. `USERSTL.LIB` **不作数据源**（私有二进制、16 个 f32 载荷与目录宏 `PARA` 无一能对上：
   `db_pkpm_sections.md` §1.4）；几何/参数一律取目录宏的 `SPRFILE PARA` + `DTSET` 具名参数。
5. 生成的宏**必须纯 ASCII**（写前断言）；中文只允许出现在报告/文档里。
6. 用户原件（`PKPM（PDMS数据库）.txt`、`pkpm_section_DBOutput.txt`、匹配文件、`JLCJ2.jwd`、`1_PM.pdt`）**只读**。

### l.2 `DbOptions`（**冻结**字段）

| 字段 | 类型 | 缺省 | 说明 |
|---|---|---|---|
| `catalogue_user` | str | `"/PKPM_JWD_USER"` | 参数化族目录（`STSECTION /USER_SECTION` 的父） |
| `catalogue_stss` | str | `"/PKPM_JWD_STSS"` | 型钢库目录（11 个 `STSECTION` 的父） |
| `spec_world_user` | str | `"/PKPM_JWD_USER_SECTION"` | 用户参数化族的 `SPWLD` |
| `spec_world_lib` | str | `"/PKPM_JWD_LIB"` | 型钢库的 `SPWLD` |
| `uniquify` | bool | `True` | 给 4 个顶层容器名追加 `suffix`（**SPRFILE/SPCOMPONENT 名保持不变**，见 l.4） |
| `suffix` | str | `""` | 唯一名后缀；`uniquify=True` 且为空 ⇒ 用 `_YYYYMMDD` |
| `clean_first` | bool | `False` | 生成清场版（l.3.5） |
| `onerror_label` | str | `"/PKPKERR"` | `ONERROR GOLABEL` 与 `LABEL` 的标号（**不得**硬编码 `/ERROR3`：样本里标号随导出次数变化，db_pdms_catalogue §5.3-2） |
| `date_text` | str | `""` | 头注释的日期文本；空 ⇒ 当前日期 |

### l.3 生成结构（**冻结骨架**）

**l.3.1 头尾逐字**（来源：样本 L1–L6/L70290–L70295，db_pdms_catalogue §1.1/§6.1）：

```
$S-  -- Synonym translation OFF
-- ------------------------------------------------------------------     ← 70 个 '-'，与样本 L2 同
-- PKPM-JWD导入导出  dbmacro: <table 来源>  <date_text>
ONERROR GOLABEL <onerror_label>

… 正文（l.3.2/l.3.3）…

LABEL <onerror_label>
handle ANY
$S+
RETURN ERROR
endhandle
```

* **不写** `INPUT BEGIN/END/FINISH`（那是 DB Listing 输出器的包装；`db_pdms_catalogue.md` §6.1 结论）。
* 缩进：每层 +2 空格（与样本同风格）；**缩进不参与语义**，`dbparse` 必须忽略。

**l.3.2 第一遍：`NEW…END`**（依赖顺序**冻结**，`db_pdms_catalogue.md` §2.1【事实】）：

```
NEW CATALOGUE <catalogue_user>
PURP STL
  NEW STSECTION /USER_SECTION
  PURP STL
    NEW STCATEGORY /<族名>
    PURP STL
      NEW TEXT /<族名>-PA<n>        PURP PARA      STEX '<参数名>'
      NEW DTSET
        NEW DATA  DKEY <DKEY>  [PTYP DIST]  PPRO ( ATTRIB DESP[n] | ATTRIB PARA[n] | WPAR[n] )
                  DPRO ( <默认值> )  PURP DESP|PARA  NUMB <n>  DTIT '<标题>'
      NEW PTSSET
        NEW PLINE  PKEY <卡点>  PX <表达式>  PY <表达式>  DX <v>  DY <v>  [PLAX <轴>]
                   CLFL true  TUFL true  PURP CLEW  CCON ANY
      NEW GMSSET
        <SRECTANGLE … | SANNULUS … | SPROFILE + NEW SPVERT …>
      NEW SPRFILE /<轮廓名>   GTYP BEAM   PARA <值…>
…  （型钢库：NEW CATALOGUE <catalogue_stss> + 11 个 STSECTION + 族 + 各自的 SPRFILE）
NEW SPWLD <spec_world_user>
DESC 'Structural Steel'
PURP STL
  NEW SPECIFICATION <spec 名>
  DESC '<英文描述>'   LNTP unset   QUES GTYP   PURP STL
    NEW SELEC   DESC '<族 DESC 英文原文>'   TANS 'BEAM'
      NEW SPCOMPONENT /<族名>-SPEC/<轮廓名>
```

**l.3.3 第二遍：`OLD…`（无 `END`，**必须**）**（【事实】2,920+2,920+50 条，样本 L46778+）。

**引用必须带父级限定链（§0.4-9，R3 复核发现·high）**：供应商源名按 §l.4 保留 ⇒ 目标库若已装
供应商 PKPM 库，同类型同名元素在不同父下合法并存，裸名 `OLD` 的解析归属取决于 PDMS 运行时
顺序——一旦解析到**用户**元素，随后的 `PSTR/GSTR/DTRE/CATR` 会改写用户目录元素。
因此本包生成侧把每个第二遍引用都从**本包唯一顶层容器**向下限定。语法证据（同一文法）：
样本 L46778 `OLD PTSSET 1 of STCATEGORY /USER_XI`（OLD + 一级 of 链）、L46779
`NARE PLINE 9 of PTSSET 1 of STCATEGORY /USER_XI`（两级 of 链）、PMLLIB
`isometricadp\data\*.dat` 的 `OLD RRULE 1 of RRST /…`；**链深**（STSECTION/CATALOGUE/
SPECIFICATION/SELEC 段）为同一文法的外推 ⇒ §12#25 待实机确认。解析侧按 §l.5-6/9
取"链头本体名"（第一个 ` of ` 之前的首名/宿主名）：

```
OLD PTSSET 1 of STCATEGORY /<族名> of STSECTION /<STSECTION> of CATALOGUE <catalogue>
NARE PLINE <条数> of PTSSET 1 of STCATEGORY /<族名> of STSECTION /<…> of CATALOGUE <…>

OLD SPRFILE /<轮廓名> of STCATEGORY /<族名> of STSECTION /<…> of CATALOGUE <…>
PSTR PTSSET 1 of STCATEGORY /<族名> of STSECTION /<…> of CATALOGUE <…>
GSTR GMSSET 1 of STCATEGORY /<族名> of STSECTION /<…> of CATALOGUE <…>
DTRE DTSET 1 of STCATEGORY /<族名> of STSECTION /<…> of CATALOGUE <…>

OLD SPCOMPONENT /<族名>-SPEC/<轮廓名> of SELEC <n> of SPECIFICATION <spec 名> of SPWLD <spec_world>
CATR SPRFILE /<轮廓名> of STCATEGORY /<族名> of STSECTION /<…> of CATALOGUE <…>
```

（`<n>` = 该 SPECIFICATION 下 SELEC 的创建序号，与第一遍一致；SPCOMPONENT 的直属父 SELEC
无名，故用序号链——与 `OLD PTSSET 1` 同型。）

**l.3.4 不变量（生成时必须成立，验收逐条查）**

| # | 不变量 | 依据 |
|---|---|---|
| 1 | `SPCOMPONENT 名 == /<STCATEGORY 名>-SPEC/<SPRFILE 名>` | 样本 2,920/2,920 成立（§2.2） |
| 2 | `NEW` 与 `END` 严格 1:1；`OLD` **一律不写 `END`** | 样本 8,325:8,325、`OLD` 5,890 全无 `END`（§1.1） |
| 3 | 全部引用型属性（`PSTR/GSTR/DTRE/CATR/NARE`）**只在第二遍**出现 | 样本无一条 `NEW` 带引用属性（§2.3） |
| 4 | `NARE` 的 `n` = 该 PTSSET 内 `PLINE` 条数 | 样本 `/USER_RECT` 9（§6.2-说明） |
| 5 | `len(SPRFILE.PARA) == count(DATA with PURP=PARA)` | 40/42 族成立，例外（`/H_AMERICA`、`/H_EUROPE` 的 25/26）**必须记 warning**（§4.4-1、§3.7） |
| 6 | 参数化族的 `TEXT` 条数 == `count(DATA with PURP=PARA)`；`PURP=DESP` 的 `DATA` 带 `PTYP DIST` | §1.3、§3.7（`PTYP` 只出现在 DESP 行） |
| 7 | `SELEC` 全 `TANS 'BEAM'`；`SPECIFICATION` 全 `QUES GTYP` + `LNTP unset` + `PURP STL` | §7.1-15 |
| 8 | `PARA` 值向量按 `DTSET.NUMB` 顺序，**word 型参数可含空格**（1–2 token） | §4.4-1（`S RSA`） |

**l.3.5 清场版（可选）**：`clean_first=True` 时**先 `ONERROR GOLABEL`、再清场段**
（§0.4-9：空库首跑时 `OLD <本包容器>` 会失败，未 armed 的 ONERROR 会让宏直接中止；
**按任务给定的 `OLD … DELETE … MEM` 范式**）：

```
ONERROR GOLABEL <label>
-- clean（可选）：只清本包自己的容器；类型缩写见 CONTRACT §12#16
OLD CATALOGUE <catalogue_user + clean 后缀>
DELETE CATE MEM
OLD CATALOGUE <catalogue_stss + clean 后缀>
DELETE CATE MEM
OLD SPWLD <spec_world_user + clean 后缀>
DELETE SPWL MEM
OLD SPWLD <spec_world_lib + clean 后缀>
DELETE SPWL MEM
```

* 清场目标名 = 基名 + **清场后缀**（显式 `--suffix` 原样；缺省 = 当日日期戳）；
  **重建容器** = 基名 + 运行戳（`_YYYYMMDD_HHMMSS`，§l.4）——**绝不复用刚清场的名字**：
  `DELETE … MEM` 只清成员不清容器本身、且语义未直证（下条），同名重建必然撞名
  （PDMS 无 OVERRIDE，§12#22）。
* 【**未直证**】官方样例只证明了 `DELETE PTSE MEM` / `DELETE GMSE MEM`
  （`pdmsdata\MDS-UPDATE-PTSE-AT29A-GMSE-AT29A.pmldat:5-6,113-114`）；`CATE`/`SPWL` 的 `MEM` 语义
  **无直证** ⇒ 必须写进报告 `warnings` 与 `assumptions`（§12#16）；**默认仍是唯一名路线**（R7）。

**l.3.6 缺口的补建**（正确验收 §9.4-12 要求"覆盖缺口"）：
`/Concrete_Slab-SPEC/T100|T120|T600`、`/Concrete_Wall-SPEC/WALL-<厚度>` 在用户目录宏里**不存在**
（`db_pkpm_sections.md` §7.3【事实】），由本包宏在自己的 SPWLD 下**新建**（`SPRFILE` 用
`T<厚度>`/`WALL-<厚度>` 名，`PARA` 给厚度值），`SELEC` 取 `DESC 'Slab'`/`'Wall'` + `TANS 'BEAM'`。

### l.4 编码与唯一名（**冻结**）

* 产物编码：**纯 ASCII、UTF-8 无 BOM、CRLF**（用户两份原件均无 BOM、纯 ASCII 正文：
  `PKPM（PDMS数据库）.txt` 只有 BOM 而无非 ASCII 正文，本次 C7 复核 2,920/2,920）；
  `write_db_macro(path, text)` 写前必须断言 `text.isascii()`。
* `uniquify=True` 只改 4 个**顶层容器名**（加 `suffix`；**缺省后缀 = `_YYYYMMDD_HHMMSS` 到秒**
  —— 旧版只到日 ⇒ 同日重跑必撞名，§0.4-9）；`STSECTION/STCATEGORY/SPRFILE/SPCOMPONENT`
  等**保持源名**（这样 `SPREF` 的 `/<族>-SPEC/<轮廓>` 路径与既有约定完全一致，用户已有的
  `PKPM转PDMS截面匹配文件.txt` 右值可直接用）。理由：PDMS 名字在**属主内**唯一，新容器内不会与
  用户冲突。**引用侧**（第二遍）一律带父级限定链（§l.3.3/§0.4-9）——属主内唯一保创建不撞名，
  限定链保引用不落到用户元素上，两者合起来才完整。
* `db2jwd`/`db2pdt` 的缺省容器名同上（写进 `.jwd`/`.pdt` 的截面名时用 `pkpm_name`，不用容器名）。

### l.5 `parse_db_macro(text) -> SectionTable` / `parse_db_macro_file(path) -> SectionTable`

**必须实现的 12 条规则**（每条证据见 `db_pdms_catalogue.md` §5.3 的 24 条坑表）：

1. **编码自动判定**：`utf-8-sig` → `utf-8` → `gbk`（顺序尝试，**禁止** `errors='replace'` 静默吞）；
   行尾 CRLF/LF 都接受。
2. 丢弃注释行（`--…`）与 `$S±`；空行忽略。
3. **合并 `$` 续行**成逻辑行；续行**允许是无关键字的纯值行**（挂在"上一个字段"上）。
4. 按 `INPUT BEGIN … INPUT END … INPUT FINISH` 切段（段数 1..n 可变）；**无 INPUT 包裹时**（手工宏）整文件为一段。
5. **栈式块解析**：`NEW <TYPE> [name]` 入栈、`END` 出栈；`END` **可省**（段尾自动收栈）。
6. **`OLD <TYPE> <target>` 无 `END`**：遇到下一个 `NEW`/`OLD`/段尾/`LABEL`/`handle` 即结束
   （否则会把 `LABEL /ERROR3` 误挂成最后一个元素的属性）。**目标可带父级限定链**
   （§l.3.3/§0.4-9）：`<名字>`、`<N> of <TYPE> <名字>` 之后可接任意多个
   `of <TYPE> <名字|序号>` 链节；解析取**链头本体名**——"序号+宿主"形态取宿主名、
   其余取首 token（`OLD PTSSET 1 of STCATEGORY /X of STSECTION /S of CATALOGUE /C`
   的本体 = `/X`；`OLD SPRFILE /Y of STCATEGORY /Z of …` 的本体 = `/Y`）。
7. **`OLD` 的类型名可省**（`OLD /XI_Profile` 与 `OLD SPRFILE /XI_Profile` 两种都要支持）。
8. 遇到 `LABEL`/`handle`/`endhandle`/`RETURN` ⇒ 立即关闭一切开放语句并**丢弃**它们。
9. token 化：`'…'` 整体、`( … )` **成对递归**整体（表达式可三层嵌套）、名字整体取到行尾
   （**可含 `/`**）；名字/引用值以 **` of ` 为界**——` of <TYPE> <token>` 是父级限定链
   （§l.3.3/§0.4-9），**不是**名字的一部分（引用型属性的值同理：`CATR SPRFILE /X of …`
   的本体 = `/X`）。
10. 类型名**同义词归一化**：`PLINE/PLIN`、`SPRFILE/SPRF`、`SPCOMPONENT/SPCO`、`SELEC/SELE`、
    `SPECIFICATION/SPEC`、`SPWLD/SPWL`、`PTSSET/PTSE/PTSET`、`GMSSET/GMSE/GMSET`、`CATALOGUE/CATE`、`DTSET/DTSE`。
11. 属性解析：允许**只有 key 没有值**（`LOCK`）；`KEY value` 与 `KEY=value` 两种写法都接受。
12. **`PARA` 逐项解析**：以 `DTSET` 的 `NUMB`/`DTIT` 为准逐个消化 token；**word 型参数允许 1–2 token**；
    长度与 `count(PURP=PARA)` 不一致 ⇒ `warnings`（`/H_AMERICA`、`/H_EUROPE` 的 25/26 必须被报出而不是崩）。

**输出**：每条 `SPCOMPONENT` → 一个 `SectionRec`，字段取值：
`pdms_spec_path` = SPCOMPONENT 全名；`pdms_catalogue` = 其 `SPRFILE` 的 CATALOGUE/SPWLD；
`family_code` = 由 `SPRFILE` 的父 `STCATEGORY` 反查（内置表的 `pdms_stcategory`→`family_code` 映射；查不到 ⇒ `0`）；
`pkpm_name` = 匹配文件逆查（`secmap.reverse`）；`dims` = `PARA` 按 `DTSET` 具名参数对位（尺寸类进 dims，
力学量进 `extra['params_named']`）；`shapeval` = 按 k.3 回算（族码已知且可算时，否则 `''`）；
`params` = `ParamDef` 列表（`is_parametric` 由族的 `PURP=DESP` 是否非空决定）。

**验收阈值**（计划 §9.4-11）：对 `PKPM（PDMS数据库）.txt` 必须解析出 **≥ 2,920 条规格**，
并与匹配文件做交叉一致率报告，**必须归类**下列已知差异（数字来自侦察报告，本次 C8 复核了 256 与 4）：

| 类别 | 期望数 | 来源 |
|---|---|---|
| 匹配文件数据行 | 2,836 | `pdms_target.md` §4.1（本次 v1 C2 复核） |
| 命中宏（右值存在同名 SPCOMPONENT） | 2,576（= 2,836 − 256 − 4） | §4.4 |
| **右值失效**（Double-L 三族缩写不一致） | 256 | conflicts §2.1/§2.2；本次 C8 复核（`in_pdms_macro=''` 恰 256） |
| 右值原本缺前导 `/` | 4（第 2979–2982 行，归一时补齐） | conflicts §2.3；本次 C8 复核（补后命中宏） |
| 大小写/写法差异（同名不同拼写） | 759 对 | conflicts §2.6 |
| 宏有、匹配文件没有的 SPRFILE | 344 | conflicts §2.4 |

### l.6 反向：`db2jwd` / `db2pdt`（落点与闭环）

**落点（函数冻结）**：

```python
# engine/jwd_write.py（新增，v1 的 write_jwd 不动）
def write_jwd_sections(sections: dict, path: str, opts: dict | None = None) -> dict
# engine/pdt_write.py（§j.1 已给）
def write_pdt_sections(sections: dict, path: str, opts: PdtOptions | None = None) -> dict
```

**由 `SectionTable` 生成 `sections`**：`sectionlib.SectionTable.to_jwd_sections()`（k.1）。

* `write_jwd_sections`：建**全部 46 张表**（DDL 同 §b.3），只填 `pkpmBeamSect`/`pkpmColSect`/`pkpmBraceSect`
  三张（`Kind`/`ShapeVal`/`Name`/`Mat` 由 `sectionlib.encode_shapeval` 回算），其余表**建而空**
  （可选写 `pkpmSysInfo.ID=2` 工程名）；返回值结构同 §b.3，并在 `warnings` 注明
  「这是截面定义文件，不含几何」。产出必须是**合法 SQLite**（`PRAGMA encoding='UTF-8'`、文本列按 §b.3 的字节规则）。
* `write_pdt_sections`：见 §j.1/§j.7.6（缺省 `skeleton="full"`）。

**覆盖范围（冻结，**不得**扩大也不得静默缩小）**：

| 源（目录宏里的族） | 可否反算 | 产出 | 依据 |
|---|---|---|---|
| 族码 `39`（`/H_INTERNATIONAL`） | ✅ | `Kind=26`：`H`,`B`,`tf`,`tw` 取自 `PARA` 的 `h,b,tf,tw`；`subtype=1` | 本次 C10 实测：`HN450X200` 的 `PARA`(450,200,9,14) → `26,39,1,450,0,200,14,9,0,5,<id>,` **与样本逐字一致** |
| 族 `77`（`/RECT_*`、`/TUBE_*`） | ✅ | `Kind=303`：`spec_str` = 规格名去 `<N>-` 前缀；`d/b` 取自 `PARA`；槽 27 = 名首数字；槽 32 按方/圆 | §a.4 + §3.2 + 本次 C10（`6-B250*10.00` 命中内置表） |
| `RECT` 族 | ✅（仅模板） | `Kind=1`，`B/H` 取 DTSET `DPRO` 默认值（`500/500`），并标 `confidence='unknown'` | §e.3 的 `RECT` 行（`PARA 0` 是占位） |
| `CIRCLE` 族 | ✅（仅模板） | `Kind=3`，`d` 取 `DPRO`（300） | §12#5（`inferred`） |
| 族码 `31/32/33/36/37/38/40/66/71/72/73` | ❌ | **跳过 + 报告**（`unencodable`） | 6 尺寸槽顺序未知（§12#19） |
| `Kind=2`（焊接 H） | ❌ | 同上 | §12#18 |
| 族码 `19`/`TRAPEZOID`/`DOUBLE_C` | ❌ | 同上 | conflicts §4.2/§4.3 |

**闭环判据**（计划 §9.4-13，**可执行**）：`db2jwd`/`db2pdt` 的反算结果再喂回 `jwd2db`/`pdt2db`，
必须回到**同一批规格名**：

1. 对 ✅ 覆盖的规格：反算出的 PKPM 名/编码串 → `jwd2db`/`pdt2db` → `SectionTable` 的
   `pdms_spec_path` 集合必须**逐个相等**（集合级相等，不是顺序相等）；
2. 允许的差异必须逐条列入 `report.db.closure.differences`（例：`HN300X150` 的 `tw`
   目录宏 6.5 vs `.jwd` 取整 6 —— 两者都映射到同一规格名 ⇒ 记为「数值取整差异」，**不算失败**）；
3. 覆盖不到的规格必须逐条列入 `report.db.closure.not_closable`（含族名与理由）；
4. `report.db.closure.covered / not_closable / differences` 三个键**必须存在**。

---

## (m) 命令行（v2 最终形态；v3 增 `--request`）〔R2 §0.4-4 / R3 §0.4-11〕

### m.1 子命令矩阵（v1 的三条见 §f.1，**不变**；下面是 v2 全量）

| # | 子命令 | 作用 | 必需参数 | 可选参数 |
|---|---|---|---|---|
| 1 | `jwd2pdms` | `.jwd` → PDMS 建模型宏 | `<jwd> --out <macro.mac>` | v1 §f.1 全部 |
| 2 | `pdt2pdms` | `.pdt` → PDMS 建模型宏 | `<pdt> --out <macro.mac>` | v1 §f.1 全部（`pdt` 代替 `jwd`） |
| 3 | `pdms2jwd` | PDMSDUMP → `.jwd` | `<dump> --out <out.jwd>` | v1 §f.1 |
| 4 | `pdms2pdt` | PDMSDUMP → `.pdt` | `<dump> --out <out.pdt>` | `[--dump-unit mm] [--report R.json] [--skeleton full\|sections-only]` |
| 5 | `jwd2db` | `.jwd` 截面定义 → PDMS 目录+规格宏 | `<jwd> --out <db.mac>` | `[--secmap F] [--extra F] [--report R.json] [--suffix S] [--clean] [--catalogue-user N] [--catalogue-stss N]` |
| 6 | `pdt2db` | `.pdt` 截面定义 → PDMS 目录+规格宏 | `<pdt> --out <db.mac>` | 同 5 |
| 7 | `db2jwd` | 目录宏 → `.jwd` 截面定义 | `<db.macro> --out <out.jwd>` | `[--secmap F] [--report R.json]` |
| 8 | `db2pdt` | 目录宏 → `.pdt` 截面定义 | `<db.macro> --out <out.pdt>` | `[--secmap F] [--report R.json] [--skeleton full\|sections-only]` |
| 9 | `jwd2pdt` | `.jwd` → `.pdt`（走规范模型） | `<jwd> --out <out.pdt>` | `[--secmap F] [--extra F] [--report R.json] [--skeleton full]` |
| 10 | `pdt2jwd` | `.pdt` → `.jwd`（走规范模型） | `<pdt> --out <out.jwd>` | `[--secmap F] [--report R.json]` |
| 11 | `dbsections` | 列出/导出截面字典与转化表 | `<db.macro\|--from-builtin> --out <F.csv\|F.json>` | `[--format csv\|json] [--report R.json] [--secmap F]` |

* 参数**风格与缺省**沿用 §f.1（`--secmap` 缺省取输入同目录的匹配文件、`--extra` 缺省取
  `engine/secmap_extra.txt`、`--report` 缺省写 `<--out 基名>.report.json`）。
* `--suffix S` / `--clean` / `--catalogue-user` / `--catalogue-stss` 只作用于 `jwd2db`/`pdt2db`，
  语义见 §l.2；`--clean` 即 `clean_first=True`。
* `dbsections` 的 `--from-builtin`：直接导出 `engine/section_table.csv` 的内容（转 `--format json` 时用 §k.1 的 `to_json`）。
* **荷载相关参数一律不存在**（R2 §9.3）；`jwd2pdt`/`pdms2pdt` 仍会**统计**荷载（canonical 解析不变）但**不写**。
* **〔R3〕`--request FILE`（全局选项）**：给**任意**子命令时，从 UTF-8 JSON 文件读
  `{"tool": "<子命令名>", "args": {…}}`，其余行为与命令行完全一致（同一执行函数）；
  这是 §p.5 的引擎调用协议，**对用户不暴露**（用户只见 PDMS 窗体）。退出码/report 与 §m.2/§h 一致。

### m.2 退出码

**沿用 §f.2，不新增码**：(0 成功 / 1 未捕获异常 / 2 参数与输入错误 / 3 `Model.validate()` 有 `E-` 项)。
`db2jwd`/`db2pdt` 的"不可闭环节点/不可反算族"**不是**错误 ⇒ 退出 0 + 报告列出（§l.6）。

### m.3 报告扩展（在 §h 的结构上**追加** `db` 键，v1 键位不变）

```jsonc
"db": {
  "macro_source": "G:\\…\\PKPM（PDMS数据库）.txt",   // 或 jwd/pdt 来源
  "generated": { "catalogue": ["/PKPM_JWD_USER","/PKPM_JWD_STSS"],
                 "spec_world": ["/PKPM_JWD_USER_SECTION","/PKPM_JWD_LIB"],
                 "stsection": 12, "stcategory": 57, "sprfile": 2920, "spcomponent": 2920,
                 "text": 533, "dtset": 57, "data": 578, "ptsset": 57, "pline": 430,
                 "gmsset": 57, "profile": 59, "specification": 12, "selec": 57,
                 "pass2": {"PSTR": 2920, "GSTR": 2920, "DTRE": 2920, "CATR": 2920, "NARE": 50} },
  "parsed":    { "specs": 2920, "sprfile": 2920, "spcomponent": 2920, "families": 57,
                 "warnings": ["/H_AMERICA 有 6 条 PARA 长 26（其余 25）…"] },
  "cross_check": { "matching_file_rows": 2836, "matched": 2576, "broken_rhs": 256,
                   "missing_leading_slash": 4, "case_variants": 759, "macro_only": 344 },
  "closure":   { "covered": 0, "not_closable": [ {"family": "/I_COMMON", "n": 45, "why": "…"} ],
                 "differences": [ {"key":"HN300X150", "why":"tw: PARA 6.5 vs .jwd 6"} ] },
  "losses":    [ {"direction":"db2pdt", "field":"A/g/Ix/Wx…", "severity":"loss", "reason":"…"} ],
  "safety":    { "forbidden_names_scanned": true, "clean_targets": [], "ascii_only": true }
}
```

* `safety` 三键必须存在（§l.1 的硬约束要机器可见）；`generated`/`parsed` 两键在**生成**方向填，
  `parsed`/`cross_check` 在**解析**方向填，缺席的键写 `null`（**不得**省略键）。

---

## (n) R2 安全约束与范围增补（§i 的追加，不改 v1 条款）

1. **目录/规格宏只允许操作本包自己的容器**（§l.1）；宏由用户自行执行，本包**不代跑 PDMS**。
2. **不改用户的 PDMS 既有目录/规格**：不 OLD/DELETE 用户的 CATALOGUE/SPWLD/SPECIFICATION；
   不写入任何 PDMS 数据库文件。
3. **`USERSTL.LIB` 不作数据源**（§l.1-4）；它是私有二进制，参数与目录宏 `PARA` 不重合。
4. **荷载不做**：不导出、不映射、不新建工作；`.pdt` 只写段头（§j.6）；canonical 的荷载解析保留（v1 不动）。
5. **匹配文件的 256 条失效右值与 759 处大小写差异**：只做报告归类与纠正建议，
   **不改用户原件**；纠正项只允许写进 `engine/secmap_extra.txt`（§e.4）。
6. **不改 `PDMSxCA_Addin*.dll`**、不反编译它（`M`/`EXI`/`EXR` 的残留疑点按 §12 留痕，不靠反编译解决）。
7. 新增产物一律落在 `PKPM-JWD导入导出\` 内（`engine/section_table.csv`、`section_table.meta.json`
   属**数据文件**，由 `test/build_section_table.py` 可复现生成）。
8. R2 落地后 `docs/` 必须同步（`交付清单.md`、`使用说明.md` 的命令表、`格式规范_PDT.md` 的**写出**章节、
   新增 `格式规范_PDMSDB.md` 的目录宏章节）；文档结论的证据分级仍按 §0.1（**未实机**不得写成"已验证"）。

---

## (o) 命名唯一化（重名加 `re`）〔R3 §0.4-11〕

> 需求原文：「宏里的名字不能重名：所有层次与元件，若与 PDMS 库中已有模型重名，
> 就在名字后面加后缀 `re`（还冲突就继续 `re2`、`re3`…）」。
> 判定**必须**发生在 PDMS 运行期（生成宏时不知道库里已有什么）⇒ 逻辑落在 PML，宏/窗体调用它。

### o.1 候选序列与上限（**冻结**）

```
候选(base) = [ base ] + [ base & 're' ] + [ base & 're%d' for d in 2..99 ]
           ⇒ 共 100 个候选；base 含前导 '/'（§d.2 的名字）。
```
* 取**第一个未被占用**的候选；全部占用 ⇒ 失败（§o.6）。
* 后缀**直接拼接**，无分隔符：`/STL_COL_1` → `/STL_COL_1re` → `/STL_COL_1re2` → …
* **只影响名字**：几何、属性、挂接、命名规则（§d）一概不变；`re` 后缀后的名字仍是"同级唯一"的普通名字。
* 本机制与 §l.2/§l.4 的数据库侧唯一名**互不替代**：§l 管 CATALOGUE/SPWLD/SPRFILE（生成期后缀 + 清场），
  §o 管 **Design 模型树元素**（运行期探测）。两者不叠加：DB 宏不走 §o。

### o.2 PML 函数（**冻结**签名与落点）

```pml
-- 落点：PKPM-JWD导入导出/pdms/pkpmjwduniquename.pmlfnc（GBK 无 BOM + CRLF，§g）
define function !!pkpmjwdUniquename(!base is STRING) is STRING
```

* **算法**（附录 F.1 是逐字夹具，`test/check_v3_contract.py` 静态断言）：
  1. `if (defined(!!pkpmjwdRenames)) then … else … endif`（`defined()` 出处：`nucdesogwall.pmlobj:206`；
     数组建立用 `!!pkpmjwdRenames = object ARRAY()`（`object ARRAY()` 出处：`nucroommcreation.pmlfnc`））。
  2. 依 §o.1 的序列逐个探测：占用判定见 §o.3。
  3. 命中可用名 `!final` 后：`if (!final ne !base) then !!pkpmjwdRenames.append('SCTN|<base>|<final>') endif`
     —— 记录格式**冻结**为 `'TYPE|原名|实际名'` 三段竖线串（TYPE 由调用方在 **`!!pkpmjwdType`
     双 ! 全局变量**里传入——单 ! 变量只在定义它的宏/函数作用域内可见，跨作用域传须双 !，
     与 `!!CE` 同理；见 §o.4；`.append()` 出处：`GRIDDESIGN.pmlfrm:986` `!this.SCTNLIST.APPEND(!!CE)`）。
  4. 返回 `!final`；**候选耗尽** ⇒ `!!pkpmjwdRenames.append('FAIL|<base>|<base>re99')` 并返回 `''`。
* **只允许**用 §o.3 的两种已证实写法之一做探测；不得自造第三种。

### o.3 占用判定的两种已证实写法（**出处强制**）

| # | 写法 | 语义 | 出处（本机安装内） |
|---|---|---|---|
| 1 | `VAR !probe EXIST $!cand` 包在 `handle (2,109)` 里；**VAR 成功（'TRUEA'）⇒ 已占用**、正常返回 'FALSEA' 或落到 `(2,109)` ⇒ **可用** | `!cand` 自带前导 `/`（§o.1）⇒ 插值后就是 `/名`；**带斜杠名字的既有惯用法就是 `EXIST $!x`**（本机 62 处；如 `TIANGONG\functions\tgautonum.pmlfnc:33-41` `!cand = '/' & !pre & …` 后 `exist $!cand` 循环探测、`aba\Forms\abauserview.pmlfrm:859-860`）。`EXIST /$!cand`（⇒ `//名`）形态全库 **0 例** ⇒ R3 复核发现⑬后禁用（旧写法 `EXIST /$!x` 的 6 处直证里插值变量**均不带斜杠**，如 `aba\Forms\abaarealib.pmlfrm:107-114`） | `aba\Forms\abaarealib.pmlfrm:107-114`（`VAR !exist EXIST /$!!abaDefaults.task.val` + `handle (2,109)`，注释原文 `-- Undefined name`——(2,109) 双结局语义的出处，与本表行的 `$!x` 形态并用） |
| 2 | `NEW <TYPE> <名>` 包在 `handle (41,12)` 里；落到 `(41,12)` ⇒ 重名（先 `delete` 再补救或换名） | 建了才知道 | `PMLLIB\aba\Forms\abaarea.pmlfrm:523-528`（`NEW IDLI $!this.name.val` + `handle(41,12)` + `!!alert.error('An element of this name already exists.…')`）；`PMLLIB\aba\Forms\abacrhierarchy.pmlfrm:116-120`（`NEW LIBY …` + `handle (41,12)` + `delete DLLB` + `!!ce = ….dbref()`） |

**裁定**：`!!pkpmjwdUniquename` 用**写法 1**（无副作用）；写法 2 是"创建即冲突"的兜底——宏的
`ONERROR` 尾（§o.5）会把任何漏网的 `(41,12)` 变成整宏中止（§12#26 标注 (2,109) 语义待实机确认）。

### o.4 宏里的确切用法（**冻结模板**）

**前置**：宏头（`$S-` 之后）加载函数文件；`MacOptions.pml_func_path`（§b.6 v3 新增）非空时 emit：

```pml
$M <$!pkpmjwdFuncPath>
```
（`$M <路径>` 出处：`nucdesogwall.pmlobj:204` `$M/%PDMSUI%/DES/STLWRK/LPNODE $<AT $!PosString$>`——
用 PDMS 环境变量路径带参数执行宏文件；**绝对路径直跑 .pmlfnc** 的同源证据是注释形态
`nucdesmanchor.mac:9-11` `$m/V:/PML/gcplus/…mac /DEV /floor450 …` ⇒ 标【推断】待实机，见 §12#28。
`.NET` 路径下由 Add-in 在 `Start()` 里 `$M` 一次，路径取 §p.5 的 engine_path 机制旁的
`<PDMS根>\PKPMJWD\pml\`。）

**每个创建元素前**（TYPE 传给函数用；`eq` 运算符出处：`sdnfinver3.pmlfnc:113` `!errflag eq 1`）：

```pml
!!pkpmjwdType = 'SCTN'
!n = !!pkpmjwdUniquename('/STL_COL_1')
if (!n eq '') then
  var !pkpmjwdFatal EXIST $!n
endif
NEW SCTN $!n
  SPREF …
  POSS …
  …
```

* `!!pkpmjwdType` 是**双 ! 全局**（跨作用域传给函数；单 ! 在函数内不可见，§o.2 步骤 3）。
* `if (!n eq '') then var !pkpmjwdFatal EXIST $!n endif` 是**故障注入**：`!n` 为空串时该行变成
  `VAR … EXIST`（无名参数）⇒ 非法 ⇒ 触发宏头的 `ONERROR GOLABEL` ⇒ 整宏中止（§12#27 标注该
  行为为【推断-高】）；`!n` 非空时该行重探一次刚验证过的名字（`EXIST /名`，§o.3 的已证实形态），无副作用。
* 骨架层（SITE/ZONE/STRU/FRMW/SBFR）与元件层（SCTN/PANE/STWALL）**全部**走该模板；
  `TYPE` 依次为 `'SITE' 'ZONE' 'STRU' 'FRMW' 'SBFR' 'SCTN' 'PANE' 'STWALL'`。
* `MacOptions.uniquify`（§b.6 v3 新增，**缺省 True**）：True ⇒ emit 上述模板；False ⇒ 沿用 v1 行为
  （直接 `NEW SCTN /名`），仅测试用——**交付产物必须 True**，并在报告 `assumptions` 记录。

### o.5 宏的 ONERROR 尾（**冻结**；全部逐字有出处）

```pml
$S-  -- Synonym translation OFF
ONERROR GOLABEL /PKPMJWDERR
…（§o.4 的创建块 …）…
LABEL /PKPMJWDERR
handle ANY
$S+
RETURN ERROR
endhandle
```
出处：DB Listing 头尾（`PKPM（PDMS数据库）.txt` L5 `ONERROR GOLABEL /ERROR3`、L70291–70295
`LABEL /ERROR3 / handle ANY / $S+ / RETURN ERROR / endhandle`；生成器来源
`rptoutput.pmlfrm:728` 与 `:3586-3591`，db_pdms_catalogue §1.1/§6.1）。语义：任何错误（含 §o.4 的
故障注入与漏网 `(41,12)`）⇒ 跳到 LABEL ⇒ 恢复同义词 ⇒ `RETURN ERROR` 上抛 ⇒
**执行者（Add-in 的 `Command.Run()` 或手动跑宏的操作者）看到失败**。

### o.6 失败行为（**冻结**；不许静默跳过）

1. 候选耗尽（含 `re99` 也被占用）：函数返回 `''` + `!!pkpmjwdRenames` 追加 `'FAIL|<base>|<base>re99'`；
2. 宏经 §o.4/§o.5 中止 ⇒ 后续元素**不再创建**（部分建成模型 + 报错，**不是**回滚）；
3. .NET 路径：`Command.Run()` 返回假 / `Result` 含错误（recon §3.5A：`bool ok = c.Run(); string result = c.Result;`）
   ⇒ 窗体弹错 + `addin.log` + 把 `!!pkpmjwdRenames` 取回并入 `report.renames`；
4. **绝不**改用"跳过该元素继续"或"覆盖既有元素"。

### o.7 可追溯（**冻结**）

* `report.renames`（§h v3 新增键）：
```jsonc
"renames": [ {"type":"SCTN","original":"/STL_COL_1","final":"/STL_COL_1re","reason":"name in use"},
             {"type":"FAIL","original":"/STL_COL_2","final":"/STL_COL_2re99","reason":"candidates exhausted"} ]
```
* **改名只发生在 PDMS 侧**：`.mac`/`.dump`/`.jwd`/`.pdt` 等生成文件里**仍是原名**（生成期不知道库内容，
  也不应把运行期结果回写进文件）；`report.renames` 是唯一真相。
* 首次运行的"全部原名可用"情形 ⇒ `renames: []`（键仍必须存在）。

---

## (p) PDMS 原生插件（.NET Add-in + PML 混写）〔R3 §0.4-11〕

> 需求原文：「要做 PDMS 内插件，不要外置的：界面必须是 PDMS 原生界面（像参考的
> `PKPM导入导出插件` 那样：PDMS 菜单/工具条点开后面一个窗体），PML 与 .NET 可以混写」；
> 「成品放工作区，不要把新东西写到 G 盘」「全程不要动 PDMS……交付完也不要部署」。

### p.1 交付形态与目录（**冻结**）

```
PKPM-JWD导入导出/
├─ pdms-net/                        ← C# 源码 + 构建脚本（S8 落点）
│  ├─ PKPMJWDAddin.cs               IAddin 入口（照 TGTextAddin.cs 骨架）
│  ├─ PKPMJWDForm.cs                WinForms 窗体（控件清单见 p.3）
│  ├─ PmlBridge.cs                  .NET→PML / PML→.NET 桥（p.4）
│  ├─ EngineRunner.cs               引擎进程调用（p.5）
│  ├─ PKLog.cs                      日志（照 TGSPECAddin.cs 的 Log()）
│  ├─ build.cmd                     编译命令（p.2，原样可跑）
│  ├─ pkpmjwd.uic                   菜单/工具条注册（p.3）
│  ├─ dist/                         产物：PKPMJWD.dll + pkpmjwd.uic
│  └─ deploy/                       安装/卸载脚本（p.6；本轮只交付、不执行）
│     ├─ deploy_pkpmjwd.py
│     └─ undeploy_pkpmjwd.py
├─ engine/dist/                     引擎独立可执行入口（p.5；S9 落点）
│  ├─ pkpmjwd_engine.exe            构建期用 PyInstaller --onefile 打包 engine/cli.py（若可用）
│  └─ run_engine.cmd                回退包装器（exe 不存在时用）
└─ pdms/pkpmjwduniquename.pmlfnc    §o.2 的唯一化函数（S2 落点）
```

* **身份冻结**：程序集名 `PKPMJWD`；命名空间 `PKPMJWD`；Add-in 类 `PKPMJWDAddin : IAddin`
  （`IAddin` 4 成员签名见 recon §3.4：`Name / Description / Start(ServiceManager) / Stop()`）；
  Command 类 `OpenPKPMJWDCommand : Command`；**Command Key = `"PKPMJWD.OpenTools"`**；
  `IAddin.Name` 返回 `"PKPMJWD"`（该串同时是 `DesignAddins.xml` 的条目文本）。
* 样例对照（**可照抄**，逐条行号见附录 F.4）：`TGTextAddin.cs:13-137`（IAddin + Command + WindowWrapper）、
  `TGSPECAddin.cs:14-109`（IAddin + Log 模式）、`TextForm.cs`（35,588 B WinForms 窗体实例）。
  **任务给的 `D:\AI_Work\PKPM三维文字程序\TGTEXT` 已不存在**（2026-09-21 清库事故）；
  实际可用的完整副本 = `D:\AI_Work\pmds三维文字程序-备份\TGTEXT\`（TGTextAddin.cs/TextForm.cs/
  build.cmd/tgtext.uic/deploy_tgtext.py 全齐）与 `C:\TEMP\tgtext_tty\recovered2\`。本契约一律引备份副本。

### p.2 编译命令（**冻结**；本轮已实测，C13）

`pdms-net/build.cmd` 的正文（逐字；探针实例 `test/_v3_csc_check/build.cmd` 已原样跑通）：

```bat
@echo off
rem build PKPMJWD.dll (x86, CLR2/.NET3.5, C#3) against local PDMS 12.1.SP4 assemblies
setlocal
set CSC=C:\Windows\Microsoft.NET\Framework\v3.5\csc.exe
set PDMS=D:\AVEVA\Plant\PDMS12.1.SP4
set HERE=%~dp0

if not exist "%CSC%" set CSC=C:\Windows\Microsoft.NET\Framework64\v3.5\csc.exe

"%CSC%" /nologo /target:library /platform:x86 /optimize+ /utf8output /codepage:65001 ^
 /warnaserror- /out:"%HERE%dist\PKPMJWD.dll" ^
 /r:"%PDMS%\Aveva.ApplicationFramework.dll" ^
 /r:"%PDMS%\Aveva.ApplicationFramework.Presentation.dll" ^
 /r:"%PDMS%\Aveva.Pdms.Database.dll" ^
 /r:"%PDMS%\Aveva.Pdms.Utilities.dll" ^
 /r:"%PDMS%\Aveva.Pdms.Geometry.dll" ^
 /r:System.dll /r:System.Core.dll /r:System.Drawing.dll ^
 /r:System.Windows.Forms.dll ^
 "%HERE%PKPMJWDAddin.cs" "%HERE%PKPMJWDForm.cs" "%HERE%PmlBridge.cs" ^
 "%HERE%EngineRunner.cs" "%HERE%PKLog.cs"

if errorlevel 1 (
  echo BUILD FAILED
  exit /b 1
)
echo BUILD OK: %HERE%dist\PKPMJWD.dll
```

* **引用清单（冻结，最小集）**：系统 `System.dll`、`System.Core.dll`、`System.Drawing.dll`、
  `System.Windows.Forms.dll`；AVEVA 5 件套 = `Aveva.ApplicationFramework.dll`、
  `Aveva.ApplicationFramework.Presentation.dll`、`Aveva.Pdms.Database.dll`、
  `Aveva.Pdms.Utilities.dll`、`Aveva.Pdms.Geometry.dll`（全部位于 `D:\AVEVA\Plant\PDMS12.1.SP4\` 根，
  recon §1.1）。**不引用** `Aveva.Pdms.Shared.dll`（TGTEXT 的 build.cmd:17 引了它，但 C13 实测
  最小桩不需要 ⇒ 保持最小集；实施中确需时走契约变更）。不需强名称、不进 GAC（recon §5.1）。
* **实测结论（C13，附录 G）**：退出码 0；产物 4096 B；CLR 运行时版本 **v2.0.50727**；
  PE machine **I386**；旁证：备份 `TGTEXT.dll`（77,824 B）同为 `v2.0.50727`/`I386`。
  ⚠ 本次实测教训：`.cmd` 必须 **CRLF + ASCII 注释**（LF-only 或非 ASCII 注释会被 cmd 误解析——
  已计入 §g 纪律 6）。
* `/codepage:65001` + `/utf8output`：源码按 UTF-8 读（与 §g 的 Python 源码纪律一致）；
  含中文的窗体字符串用 `\uXXXX` 或源码 UTF-8 均可，但**产物内中文最终显示依赖 PDMS 进程**，
  实施时 Caption 优先用 `.uic` 里已验证可行的中文（tgtext.uic:12 `Caption>三维文字<` 即中文直排）。

### p.3 界面（**冻结**；"原生界面"的核心）

**菜单/工具条注册**（`pdms-net/dist/pkpmjwd.uic`，UTF-8 无 BOM + LF——与 `tgtext.uic` 逐条同构，
对照表见附录 F.3）：

```xml
<ButtonTool Name="PKPMJWD.Open">
  <Command><Type>Instance</Type><Key>PKPMJWD.OpenTools</Key><Arguments /></Command>
  <Image />
  <Caption>PKPM JWD 导入导出</Caption>
  <DisplayStyle>Default</DisplayStyle>
</ButtonTool>
<MenuTool Name="PKPMJWD.Menu">
  <Image />
  <Caption>PKPM JWD</Caption>
  <DisplayStyle>Default</DisplayStyle>
  <Tools><Tool Name="PKPMJWD.Open" /></Tools>
</MenuTool>
```
外加 `<MenuBar><Tool Name="PKPMJWD.Menu" /></MenuBar>` 与 `<QATTools><Tool Name="PKPMJWD.Open" /></QATTools>`
（同 tgtext.uic:25-36）。**注册链 = 三件套**（recon §4.1/§4.2【事实】）：
① `DesignAddins.xml` 的 `<ArrayOfString>` 加 `<string>PKPMJWD</string>`；
② **`DesignCustomization.xml` 的 `<UICustomizationFiles>` 加
`<CustomizationFile Name="PKPMJWD" Path="pkpmjwd.uic" />`**（最易漏的一步）；
③ `pkpmjwd.uic` 复制到 `<PDMS根>\`。

**窗体 `PKPMJWDForm`（WinForms，控件清单冻结）**——一窗三向，控件自上而下：

| # | 控件 | 类型 | 说明 |
|---|---|---|---|
| 1 | `cmbOp` | ComboBox（DropDownList） | 操作：`jwd2pdms` / `pdt2pdms` / `pdms2jwd` / `pdms2pdt` / `jwd2db` / `pdt2db` / `db2jwd` / `db2pdt` / `jwd2pdt` / `pdt2jwd`（§m.1 子集；`dbsections` 不进窗体）。缺省 `jwd2pdms` |
| 2 | `txtSource` + `btnBrowseSource` | TextBox + Button | 源文件（`.jwd`/`.pdt`/目录宏 `.txt`/PDMSDUMP `.txt`）；类型按扩展名判定（`.jwd`⇒SQLite、`.pdt`⇒文本、`dump`⇒PDMSDUMP），**不设格式下拉** |
| 3 | `txtSecmap` + `btnBrowseSecmap` | TextBox + Button | 截面匹配文件；缺省 = 源文件同目录 `PKPM转PDMS截面匹配文件.txt`（§f.1 同规则） |
| 4 | `chkUseExtra` + `txtExtra` | CheckBox + TextBox | 补充映射；缺省勾选 = `engine/secmap_extra.txt`（§e.4 同规则） |
| 5 | `numBaseE/numBaseN/numBaseU` | NumericUpDown ×3（3 位小数） | 基点 E/N/U（§f.1 语义）；仅建模方向（`*2pdms`）启用 |
| 6 | `numAngle` | NumericUpDown（2 位小数） | 转角（度）；同上 |
| 7 | `cmbUnit` | ComboBox | `mm/cm/m`，缺省 `mm`（§d.4-1：只缩放宏内数值） |
| 8 | 构件类别勾选 | CheckBox ×8 | `chkColumn/chkBeam/chkHBrace/chkVBrace/chkSlab/chkWall/chkGrid/chkHole`——与现有 Add-in 的 `Chk_Column/Chk_Beam/Chk_Brace/Chk_Slab/Chk_Wall/Chk_Grid/Chk_Hole` 同名同义（`pdms_target.md` §3.2 控件名直证；本包拆 HBrace/VBrace 两个）；仅建模方向启用 |
| 9 | `txtOut` + `btnBrowseOut` | TextBox + Button | 输出文件（`.mac/.jwd/.pdt/.csv/.json`）；缺省 = `%TEMP%\PKPMJWD\<源基名>.<ext>` |
| 10 | `btnRun` | Button「执行」 | 见 p.5 的执行序列 |
| 11 | `progressBar1` + `txtSummary` | ProgressBar + multiline TextBox(ReadOnly) | 进度与摘要（引擎 report.json 的 `counts`/`sections` 计数 + `renames` + 未解析清单） |
| 12 | `btnOpenReport` | Button「打开报告」 | 用系统默认程序打开 report.json（`Process.Start`） |
| 13 | 全窗体 | — | 非模态（`Show()` 不 `ShowDialog()`，照 `TGSPECAddin.cs:86-88`）；Owner 设为 PDMS 主窗（照 `TGTextAddin.cs:114-127` 的 `WindowWrapper`）；窗体标题 `PKPM JWD 导入导出`；**不暴露命令行**——所有引擎参数由窗体收集 |

### p.4 混写边界（**冻结**；三层职责）

| 层 | 职责 | 机制（出处） |
|---|---|---|
| **.NET**（`PKPMJWD.dll`） | 菜单/窗体呈现、文件选择、参数收集、进度显示、结果写状态/弹窗、日志 | `IAddin/Command/CommandManager`（recon §3.4）；Owner+非模态（TGTextAddin.cs:114-127） |
| **PML** | **PDMS 库内**一切取数与执行：遍历 `STRU/FRMW/SBFR/SCTN/PANE/STWALL` 写 PDMSDUMP（§c.5）、名字唯一化（§o）、`$M` 执行导入宏 | `.NET→PML`：`Aveva.Pdms.Utilities.CommandLine.Command.CreateCommand(s)` + `Run()`/`Result`（recon §3.4/§3.5A）；`PML→.NET`：`import '<dll 绝对路径去 .dll>'` + `using namespace '<NS>'` + `!!o = object Class()`（recon §3.5B，SolidSupport `mac/loadVariable` 原文） |
| **Python 引擎**（已验证，**本轮不重写**） | 文件格式转换：`.jwd/.pdt` ↔ 规范模型 ↔ PDMS 宏/PDMSDUMP ↔ 目录宏（§j/k/l/m 的全部子命令） | 独立可执行入口，由 .NET 进程调用（p.5） |

* **混写红线**：.NET **不直接**读写 `.jwd/.pdt`（那是引擎的事）；PML **不做**文件格式解析
  （除了 PDMS 库取数）；引擎 **不碰** PDMS 进程/数据库。
* `PmlBridge` 的三个冻结方法：`bool RunPml(string pmlText)`、`string RunPmlWithResult(string pmlText)`、
  `object ImportDotnet(string dllPathNoExt, string ns, string className)`——分别对应 recon §3.5A/§3.5B。

### p.5 引擎调用（**冻结**；"独立可执行文件 + 进程调用"）

**入口解析顺序**（`EngineRunner`）：
1. 环境变量 `PKPMJWD_ENGINE`（绝对路径）；
2. `<PDMS根>\PKPMJWD\engine_path.txt`（deploy 脚本写入，内容 = 引擎入口绝对路径，UTF-8 无 BOM 单行）；
3. `<DLL 所在目录>\..\..\engine\dist\pkpmjwd_engine.exe`（工作区直跑场景）。

**调用协议（冻结）**：

```
<engine_entry> --request <UTF-8 JSON 文件>
request = { "tool": "jwd2pdms",                     // §m.1 的 10 个窗体子命令之一
            "args": { …该子命令在 §m.1/§f.1 的全部参数，键名与 CLI 完全一致… } }
```

* 引擎行为：与命令行**同一执行函数**（`cli.py` 的实现不许分叉）；`--request FILE` 是 §m 的
  **v3 新增全局选项**（§0.4-11）；执行完把 report.json 写到 `args.report`，退出码用 §f.2；
  stdout 输出**一行摘要 + 未解析清单**（UTF-8；.NET 按 UTF-8 读字节）。
* .NET 执行序列（`btnRun`）：① 校验输入存在/扩展名合法 → ② 写 request JSON 到
  `%TEMP%\PKPMJWD\<op>-<timestamp>.json` → ③ `Process.Start(engine_entry, "--request …")` 等待退出
  （**同步等待 + 窗体进度条滚动**，超时上限 30 分钟）→ ④ 退出码 ≠0 ⇒ 弹错 + 日志；=0 ⇒
  **建模方向**继续：`PmlBridge.RunPml("$M <生成的 .mac>")`（宏由引擎生成到 `txtOut`，内含 §o 唯一化），
  再取回 `!!pkpmjwdRenames` 并入 report → ⑤ 摘要上窗 + `btnOpenReport` 可用。
* **导出方向**（`pdms2jwd/pdms2pdt`）：先 `PmlBridge` 执行 §c.5 的 PML 导出函数得到 PDMSDUMP 到
  `txtOut` 同目录的 `<源基名>.dump.txt`（GBK+CRLF，§c.1），再以该 dump 为 `--request` 的输入调引擎。

### p.6 注册脚本（**冻结**；本轮**只交付、绝不执行**）

`pdms-net/deploy/deploy_pkpmjwd.py` / `undeploy_pkpmjwd.py`（骨架照 `deploy_tgtext.py`，逐行出处见附录 F.5）：

| 步骤 | 行为 | 出处（deploy_tgtext.py） |
|---|---|---|
| 0 | **缺省 dry-run**：只打印"将要改变的全部对象"完整清单（逐条绝对路径），**不落盘**；带 `--execute` 才真正修改（v3 硬化，对应红线 6「先打印完整清单再执行」） | TGTEXT 无此步（v3 新增） |
| 1 | 备份 `DesignAddins.xml`/`DesignCustomization.xml` 各一次，后缀 `.pkpmjwd-bak` | :21-26 `backup_once()` |
| 2 | `DesignAddins.xml` 的 `</ArrayOfString>` 前插 `  <string>PKPMJWD</string>\n`；幂等（已有则跳过） | :28-38 |
| 3 | `DesignCustomization.xml` 的 `</UICustomizationFiles>` 前插 `  <CustomizationFile Name="PKPMJWD" Path="pkpmjwd.uic" />\n`；幂等 | :41-51 |
| 4 | 复制 `dist\PKPMJWD.dll`、`dist\pkpmjwd.uic` 到 `<PDMS根>\` | :54-58 |
| 5 | 写 `<PDMS根>\PKPMJWD\engine_path.txt`（引擎入口绝对路径）与 `<PDMS根>\PKPMJWD\pml\pkpmjwduniquename.pmlfnc`（§o.2 函数，GBK+CRLF 原样复制） | v3 新增 |
| 卸载 | **恢复优先**：从 `.pkpmjwd-bak` 复原两个 XML；把安装的 4 个文件（DLL/uic/engine_path.txt/pmlfnc）**移动**到 `<PDMS根>\PKPMJWD\_uninstalled_<时间戳>\`（不删除） | TGTEXT :61-84 是"删条目+unlink"；v3 改为恢复+移动（更符合红线 3） |

* 两个 XML 的读写必须 `utf-8-sig`（实测两者均 **UTF-8 带 BOM + CRLF**：DesignAddins.xml 1,140 B/26 CRLF、
  DesignCustomization.xml 688 B/11 CRLF，本次 C16 实测）——写回必须保留 BOM 与 CRLF。
* **PDMS 安装目录以外**不落任何文件；引擎本体**不复制**进 PDMS 目录（用 engine_path.txt 指回工作区/交付目录）。

### p.7 日志与状态（**冻结**）

* 日志：`<PDMS根>\PKPMJWD\addin.log`（ASCII、追加、带时间戳）——照 `TGSPECAddin.cs:52-63` 的 `Log()`；
  `TGLog.cs`（952 B）是可直接照抄的实现。
* 用户可见反馈：窗体 `txtSummary`（主）+ `MessageBox`（错误，照 `TGTextAddin.cs:110`）+
  `report.json`（完整）。不要求写 PDMS 命令窗。

### p.8 与既有包的关系

* `engine/gui.py`（tkinter）保留为**开发/测试**工具；对用户只暴露 PDMS 内窗体（§p.3）。
* `install/`（v1 的 PML 菜单注入方案）**被 §p 取代**：S8 交付后 `install/install.ps1` 标记为
  legacy（文件保留不删，`docs/交付清单.md` 注明以 `pdms-net/deploy/` 为准）。

### p.9 验收（编号见 §q；本轮只做静态部分）

### p.10 安全边界（R3 硬边界，**违反任何一条即验收失败**）

1. **不部署**：不执行 deploy 脚本；`D:\AVEVA` 的注册三件套与 DLL 在整轮前后零变化（C14 基准）。
2. **不启动 PDMS**：不运行 `des.exe`/`pdms.bat`/任何 PDMS 模块；验收只做静态与文件级检查。
3. **不写 G 盘**：交付物只出现在 `PKPM-JWD导入导出\` 与 `D:\AI_Work\PKPM数据解析\交付_PKPM-JWD插件\`；
   G 盘清单零变化（C14 基准）。
4. **不改 `D:\AVEVA`**：只允许**读**（csc `/reference`、静态取证）；C14 基准核对。
5. 交付声明：`docs/交付清单.md` 与 `docs/使用说明.md` 必须写明
   **「本包未部署，需要用户自己在 PDMS 停机时按 docs/使用说明.md 安装」**；不得写"已安装/已生效"。

---

## (q) 验收标准 15–19〔R3 §0.4-11；v1 的 1–8 与 R2 的 9–14 不变〕

| # | 标准 | 怎么验（可执行口径） |
|---|---|---|
| 15 | **重名唯一化** | ① 静态：附录 F.1 夹具与 `pdms/pkpmjwduniquename.pmlfnc` 逐字对照（签名、探测写法、上限 99、FAIL 记录、append/defined 出处注释齐全）——`test/check_v3_contract.py`；② **逻辑对照**：用 Python 参考实现（同一算法）对构造的"占用表"跑出候选序列，断言 `原名→re→re2…`、第 100 个候选耗尽即 FAIL——同脚本；③ 改名记录：模拟结果必须能产出 §o.7 的 `renames` 条目；④ 耗尽行为 = 报错中止（§o.6），代码评审确认无"跳过/覆盖"分支。**PDMS 实机行为标注"未实机"**（§12#26/27） |
| 16 | **.NET 插件真编译通过** | 跑 `pdms-net/build.cmd`（§p.2 原样）：退出码 0；产物 `dist\PKPMJWD.dll` 存在；CLR 版本 = **v2.0.50727**、PE machine = **I386**（`test/check_v3_csc_probe.py` 的 PE 检查逻辑复用，C13 已对探针桩实测通过）；D:\AVEVA 零变化 |
| 17 | **注册脚本静态检查** | ① 对 deploy 脚本跑**dry-run**（缺省即 dry-run）：打印的清单 = 备份 2 + 追加 2 + 复制 2 + 写 2（§p.6 表）；② 幂等：对临时目录副本连跑两次（脚本支持 `--pdms-root <dir>` 指向沙箱副本），第二次无新增条目；③ 卸载恢复：uninstall 后两个 XML 与 `.pkpmjwd-bak` **逐字节相等**、4 个安装文件被移入 `_uninstalled_*`；④ 只加不删：dry-run 清单里不得出现"删除"字样；⑤ **未被执行过**：C14 verify（真实 `D:\AVEVA` 与 G 盘零变化） |
| 18 | **界面清单完整** | ① `pkpmjwd.uic` 与 tgtext.uic 逐条同构对照（附录 F.3 表：结构/键名/命令形态一致，仅 Name/Caption/Key 不同）——`test/check_v3_contract.py`；② `PKPMJWDForm.cs` 含 §p.3 表的全部 13 项控件（控件名静态检索）；③ 编译通过（=标准 16）⇒ 菜单→Command→窗体链成立（Key 三处一致：.uic / Addin / Command 构造器）；④ 实机可见性标注"未实机" |
| 19 | **交付落点** | ① 成品只存在于 `PKPM-JWD导入导出\` 与 `D:\AI_Work\PKPM数据解析\交付_PKPM-JWD插件\`（后者含：整包副本 + `交付清单.md` + 哈希清单）；② C14 verify：G 盘 751 文件与 `D:\AVEVA` 顶层 645 文件在整轮前后 size+mtime+sha256 零变化；③ `docs/交付清单.md` 含 §p.10-5 的未部署声明 |

---

> 例外：本表第 5 行已经 §0.4-1 的**授权变更**改写；其余各行仍按原裁定执行。
> **第 15–24 行是 R2 新增**（§0.4-4 授权）；**第 26–29 行是 R3 新增**（§0.4-11 授权）。

| # | 歧义点 | 本契约的裁定 | 处置 |
|---|---|---|---|
| 1 | `FRMW /STL_FRAME/EL<n>` 是"名字含 `/` 的单个 FRMW"还是"`/STL_FRAME` 下挂 `EL<n>`" | **按任务要求冻结为**：每层一个 FRMW，名称字面 `STL_FRAME/EL<n>`；宏里写 `NEW FRMW /STL_FRAME/EL<n>` | 依据：Add-in 字符串 `/STL_FRAME/EL`；本机 `GRIDDESIGN.pmlfrm:975` 证明 NAME 含 `/` 可运行。**待实机确认**；若报错，回报后走契约变更 |
| 2 | 墙用 `SPRE` 还是 `SPREF` | **冻结：`SPRE`** | 依据：`sctlcrelem.pmlfnc:201-202`（AVEVA 官方）。反例 `nucdesogwall.pmlobj:188` 用 `spref`；实机以 SPRE 为准 |
| 3 | `Kind=1` 的 `B/H` 先后 | 冻结为 `B` 前 `H` 后，并在 `Section.note` 标注【推断-中】 | 依据：`jwd_format.md` §3.2（PDMS `/USER_XI` 参数名序 `B,H,Tw,T1,T2`）。**待实机确认** |
| 4 | `Kind=2` 的 `B/T` 交错序 | 对称（`B1==B2` 且 `T1==T2`）时按 `[B1,B2,H,Tw,T1,T2]` 出 DESP；不对称 ⇒ unresolved | 依据 §9.3#5；**不得**猜 |
| 5 | `Kind=3` 族别 | **`inferred`：圆形（实心圆钢，`dim=直径`）→ `/USER_CIRCLE-SPEC/Circle_Profile` + `DESP <d>`**（变更记录 §0.4-1，编排方授权） | 证据与残余风险见 §e.3 的 `Kind=3` 行；启用/停用见 §e.4a（`@FAMILY 3 = CIRCLE` / `= none`）。**不得**再按旧句"unresolved + 候选键"处理 |
| 6 | `Ecc/EccX/EccY` 正负方向 | 只记录不过滤（几何里照加），非零偏心逐条进报告 | §9.3#6；建议实机抽验一根已知偏心梁 |
| 7 | `BraceSeg.HDiff2=6650` | 忠实带入几何，由 `W-MEM-ZRANGE` 报出 | §9.3#7 |
| 8 | 荷载数值语义（类型码 1/2/3、kN vs kN/m） | 只做"原样搬运 + 计数"，**不参与几何**；报告注明未证实 | §1.6 / §9.3#8 |
| 9 | `Rotation` 单位与基准轴 | 冻结为**度**、绕构件自身轴（对齐 PDMS `BANG`） | §4.1【推断】+ `sdnfinver3.pmlfnc:192` 的 `BANG` 用法 |
| 10 | 宏内是否需要显式设单位 | v1.0 **不发**单位语句；`--unit` 只缩放数值 | 见 d.4-1；若实机需要，用 `Var !Units units` + `mm distance`（PML 惯用法）补 |
| 11 | `pdms2jwd` 是否需要 `--extra` | 不提供（保持任务给定签名）；使用默认 `secmap_extra.txt` | 若需要，走契约变更 |
| 12 | `#SCTN` 的 `ori` 码、`#PANE` 的 `orient2` | 冻结为冗余自校验位（`E/N/U/S` 与 `YNZU`） | 本契约定义（§c.2/c.3.6） |
| 13 | 轴网能否往返 | v1.0：`jwd2pdms` **不写**轴网到 dump；`jwd_write` 用合成轴网 | b.3；报告须注明"轴网编号为合成结果" |
| 14 | `pkpmWallSeg`/`pkpmStairSeg`/`pkpmSubBeam` 等空表族的语义 | **不解码**；非空 ⇒ 记报告 | §1.7；`Wall` 数据类只服务 `.pdt` |
| 15 **〔R2〕** | `.pdt` 的 `$SETELEMENT.TYPE=3` 是不是"支撑" | **冻结为支撑**（§j.4.5，§0.4-5）；`pdt_read` 同步映射 `3→'brace'`；`1=柱`/`2=梁` 不变 | 样本无支撑（`pdt_format.md` §5.1【事实】）⇒ 无直证。写 1/2 会静默改类型、写别的值会丢构件（`engine/pdt_read.py:471`）⇒ 两端必须同码。**待实机确认** |
| 16 **〔R2〕** | 清场版 `DELETE CATE MEM` / `DELETE SPWL MEM` 是否合法 | 清场版按任务给定的 `OLD … DELETE … MEM` 范式生成，但**类型缩写标【未直证】**；默认走唯一名路线（R7） | 官方样例只证 `DELETE PTSE MEM`/`DELETE GMSE MEM`（`pdmsdata\MDS-UPDATE-PTSE-AT29A-GMSE-AT29A.pmldat:5-6,113-114`；db_pdms_catalogue §6.4） |
| 17 **〔R2〕** | `.pdt` 的 `M` 字段规则 | **§0.4-10 修订：按 SHAPE 取（`1/3→6`、`39→mat=5`）**；`mat ∉ {5,6}` ⇒ 报告 `unknown` 并写 5 | 样本全部 3 个观测点（`SHAPE=1/3→6`、`39→5`）；旧冻结 `M=mat` 与 SHAPE=1/3 的观测**全部**相悖（R3 复核发现⑧：实测 db2pdt.pdt 的 M 分布 {5:1845} 含 SHAPE=1/3） |
| 18 **〔R2〕** | 族码 `19` / `TRAPEZOID` / `DOUBLE_C` / `RECT` 的族码值 | **不解**：`db2jwd`/`db2pdt` 遇到即**跳过 + 报告**（`not_closable`） | conflicts §4.2/§4.3；`RECT` 另按 §k.3 的 `Kind=1` 模板处理（仅模板，非具体尺寸） |
| 19 **〔R2〕** | `Kind=26` 的族码 ≠ 39 时 6 个尺寸槽的顺序 | **不可生成**：`db2jwd` 只支持族码 `39`；其它（31/32/33/36/37/38/40/66/71/72/73）⇒ 跳过 + 报告 | `db_pkpm_sections.md` §4.2（只有族码 39 能靠名反推 H/B）；§12#4 同源的"不许猜"原则 |
| 20 **〔R2〕** | `Kind=303` 槽 27 / 槽 32 的取值规则 | 槽 27 = 规格名首数字前缀（`6-B250*10.00`→6，**由 §3.2/§3.3 的族码表印证**）；槽 32 = 方矩 `16672` / 圆 `16640`（**【推断-中】**，仅 3 条样本）；两者都必须进报告留痕 | `jwd_format.md` §3.2；本次 C10 复核（3 条样本的编码/解码双向一致） |
| 21 **〔R2〕** | 能不能用 `USERSTL.LIB` 当 PKPM 截面库数据源 | **不能**：不作数据源，几何/参数一律取目录宏 `SPRFILE PARA` + `DTSET` 具名参数 | `db_pkpm_sections.md` §1.4（16 个 f32 载荷与宏 `PARA` **无一能对上**）、§1.5（文件内不含任何 PDMS 规格名） |
| 22 **〔R2〕** | 目录宏重跑 | 生成侧默认给 4 个顶层容器加唯一后缀；清场版可选（§l.3.5） | 宏内 `OVERRIDE` **0 次**、`DELETE` **0 次**（db_pdms_catalogue §6.4【事实】）⇒ 重名 `NEW` 必失败（`ONERROR GOLABEL` 整体中止） |
| 23 **〔R2〕** | `.pdt` 的 `EXR` 键集与 `$DESIGNPARA` 语义 | `EXR` **只写最小自洽集**（§j.5），未复刻键逐条列报告；`$DESIGNPARA` **只写原样文本或全 0 占位**，不解释语义 | `pdt_format.md` §6 的未确证清单、§4（50×20 无字段名） |
| 24 **〔R2〕** | 匹配文件的 256 条失效右值 / 759 处大小写差异 / 344 条宏独有 | 只做**归类报告 + 纠正建议**，**不改用户原件**；纠正项只允许写进 `engine/secmap_extra.txt` | conflicts §2.1–§2.6；本次 C8 复核（`in_pdms_macro=''` 恰 256） |
| 25 **〔R3〕** | 第二遍父级限定链的**链深**（`of STSECTION` / `of CATALOGUE` / `of SPECIFICATION` / `of SELEC <n>` 段） | **待实机确认**：样本只直证一级 `OLD PTSSET 1 of STCATEGORY /X` 与两级属性链（`NARE PLINE n of PTSSET 1 of …`）；更深链节是同一文法的外推（§l.3.3/§0.4-9）。实机若报错 ⇒ 回报后改为"OLD 唯一容器 + 相对 OLD"方案（走 §0.3 契约变更） | 语法证据：`PKPM（PDMS数据库）.txt:46778/46779`、PMLLIB `isometricadp\data\*.dat` 的 `OLD RRULE 1 of RRST /…`；风险事实：供应商源名与用户库同名并存（§l.4），裸名 OLD 的归属取决于 PDMS 运行时解析顺序，无法静态验证（R3 复核发现·high） |
| 26 **〔R3〕** | `VAR !probe EXIST /<名>` + `handle (2,109)` 的语义：**VAR 成功 = 已占用；(2,109) = 名字未定义（可用）** | **冻结该语义**（§o.3 写法 1）；备选（同样已证实）= `NEW` + `handle (41,12)`（abaarea.pmlfrm:523-528）。**待实机确认**：错误号语义只能静态引证，无法在本轮验证 | 依据：`abaarealib.pmlfrm:107-114`（`VAR !exist EXIST /$!!abaDefaults.task.val` + `handle (2,109)`，注释原文 `-- Undefined name` / `-- Does not exist`） |
| 27 **〔R3〕** | 宏内空名故障注入 `var !pkpmjwdFatal EXIST $!n`（`!n = ''` ⇒ 该行变成无名参数的 `EXIST` ⇒ 非法 ⇒ 触发 `ONERROR GOLABEL` ⇒ 整宏中止） | **冻结该机制**（§o.4/§o.5）；【推断-高】：无名参数的 `EXIST` 必然报错——但具体错误号未证。实机若发现空名被"容忍"，改用 §o.3 写法 2 的 handle 内 return（走 §0.3 变更）。**§0.4-12 修订**：探测/重探的形态统一为 `EXIST $!n`（`!n` 自带前导 `/`）——旧形 `EXIST /$!n` 对非空名会探成 `//名`（全库 0 例的未证实形态，R3 复核发现⑬） | `ONERROR GOLABEL`/`LABEL`/`handle ANY`/`RETURN ERROR`/`endhandle` 全部有出处（`PKPM（PDMS数据库）.txt` L5/L70291-70295；`rptoutput.pmlfrm:728,3586-3591`）；`eq` 运算符出处 `sdnfinver3.pmlfnc:113` |
| 28 **〔R3〕** | 宏内 `$M <绝对路径>` 直跑 `.pmlfnc`（加载 `!!pkpmjwdUniquename`） | **待实机确认**：同源证据是①环境变量路径形态 `nucdesogwall.pmlobj:204`、②注释里的盘符绝对路径形态 `nucdesmanchor.mac:9-11`。若实机拒绝 ⇒ 备选（已冻结）：Add-in 在 `Start()` 里用 `Command.CreateCommand("$M <绝对路径>")` 预载（Add-in 侧字符串拼接无宏解析限制）；或把函数文件随 DLL 部署进 `<PDMS根>\PKPMJWD\pml\`（§p.6 步骤 5 已安排） | recon §3.5A（.NET→PML 用 CreateCommand）；§p.6 步骤 5 |
| 29 **〔R3〕** | 引擎独立可执行文件的**构建方式** | 调用**接口**已冻结（§p.5：`--request` 协议、入口解析顺序、退出码）；构建方式在构建期决定——首选 PyInstaller `--onefile` 打包 `engine/cli.py`；不可用则交付 `engine\dist\run_engine.cmd` 回退（内容：定位 Python 3.12 后 `"…python.exe" "%~dp0..\cli.py" %*`）。实施者**不得**改调用接口，也不得让 .NET 直接 import Python | 任务原文「引擎的调用方式定为：打包好的独立可执行文件，由 .NET 以进程方式调用」；本机 Python 3.12.10（C13 会话实测 `py -V` 场景） |

---

## 附录 A：最小示例（dump / 宏 / report.json）

* dump 最小示例与逐行读法：见 §c.4（夹具已用 `test/check_dump_grammar.py` 按 §c.3 规则跑通）。
* 宏最小示例：见 §d.4。
* `report.json` 最小示例：见 §h。
* 联调建议：`test/` 里放一份 §c.4 的 dump 文本（GBK+CRLF），
  跑 `cli.py pdms2jwd` 应得到含 2 柱 + 1 梁 + 1 板 + 1 墙 的 `.jwd`，且报告 `errors` 为空。

## 附录 B：本契约引用的证据（文件:行）

### B.1 本机 PDMS 安装（`D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB\`，本次亲自读取）

| 文件:行 | 内容 | 本契约用途 |
|---|---|---|
| `mypml\forms\StlGrating.pmlfrm:42-48` | `new stru/new frmw/new sbfr/NEW PANE/ORI Y IS N AND Z IS U/NEW PLOOP/HEIGHT $!PW SJUS dbot` | §d.3 板语法、c.5 生成规则 |
| `mypml\forms\StlGrating.pmlfrm:49-56` | `NEW PAVERT` + `POS E … N … U …`（4 条围成矩形） | §c.3.3、d.3 |
| `mypml\forms\StlGrating.pmlfrm:92-97` | `NEW SCTN/SPREF $!SPEC/DESP …/JUS GG/POSS/POSE` | §d.3 钢构件、§d.4 骨架 |
| `mypml\forms\StlGrating.pmlfrm:105` | `STRU`（回退） | §d.3 回退游标 |
| `design\functions\sctlcrelem.pmlfnc:156-167,169-181` | 墙 `DESP`；`SCTN/GENSEC` 的 `DESP` | §d.3 |
| `design\functions\sctlcrelem.pmlfnc:201-202` | `WALL/STWALL → SPRE` | §d.3 属性归属（墙用 SPRE） |
| `design\functions\sctlcrelem.pmlfnc:229-256` | `PANE → SPREF`（失败则 `NEW PLOO` + `HEIGHT`） | §e 未解析仍可建、d.4-2 |
| `design\functions\sctlcrelem.pmlfnc:267-292` | `SCTN/GENSEC → SPREF` + `GTYPE`；无规格 `else NEW SPINE` | §d.3、d.4-2 |
| `design\functions\sctlcrelem.pmlfnc:313-349` | 墙/构件的 `JUSL/MEML` | §d.3 |
| `mypml\forms\GRIDDESIGN.pmlfrm:964-985` | `NEW STRU`/`NEW FRMW`/`!!CE.NAME = name OF OWNER + …`/`NEW SBFR`/`NEW SCTN`/`POSSTART/POSEND` | §d.1、d.2（名称可含 `/`）、d.3 |
| `mypml\forms\GRIDDESIGN.pmlfrm:1458` | 裸 `FRMW` 回退 | §d.3 回退游标 |
| `design\functions\aslspecinit.pmlfnc:79,81` | 裸 `SBFR`、`FRMW` 回退 | §d.3 |
| `MYTOOLS\test\Tekla2PDMS\sdnf\functions\sdnfinver3.pmlfnc:117,140,142,158,163,187,188,192` | `new sctn/spref/desp/pose/poss/jusl/meml/bangle` | §d.3、§12#9 |
| `MYTOOLS\…\sdnfinver3.pmlfnc:128,132,136` | 卡点枚举串 | §d.3 |
| `Building_Design\pmllib\concrete_design\ANCHOR\nucdesoanchier.pmlobj:90-106` | `!!CE = /*`、`NEW SITE/ZONE/STRU/FRMW` | §d.1 五级骨架 |
| `Building_Design\pmllib\concrete_design\TRADUCTEUR\nucdesogwall.pmlobj:180-196` | `NEW STWALL` + `desp`/`spref`/`jusl`/`poss` | §d.3、§12#2 反例 |
| `Building_Design\pmllib\room_manager\functions\nucroommcreation.pmlfnc` | `Var !Units units` + `mm distance` | §12#10（不采用） |

### B.2 用户原件（`G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\`，本次只读实测）

| 文件 | 事实 | 用途 |
|---|---|---|
| `PKPM转PDMS截面匹配文件.txt` | GBK/CRLF/无 BOM、3,023 行、数据 2,836 条、`//` 注释 78、空行 109、无法解析 0、右值缺前导 `/` **4 条**（L2979–2982）、左值 **0** 重复、53 个规格前缀；L29 `RECT, /USER_RECT-SPEC/Rectangle_Profile`；L643 `HN450X200 ,/H_INTERNATIONAL-SPEC/HN450X200`；L281 `1-[18a  , /C_COMMON-SPEC/[18a` | §e.1/e.2 |
| `JLCJ2.jwd` | SQLite3、`PRAGMA encoding=UTF-8`、`user_version=0`、**46** 张 `pkpm*` 表（21 非空 6,480 行）、层标高 −2000/−1000/6600/11600/16600/22060、`pkpmColSect.Name` 为 GBK 字节、`pkpmLoadSect.Loadname` 为 UTF-8 字节 | §0.2、a.3、a.4、b.2、b.3 |
| `PKPM（PDMS数据库）.txt` | UTF-8 **带 BOM**（EF BB BF）、1,406,051 B、70,301 行、首行 `$S-  -- Synonym translation OFF`、末行 `$S+  -- Synonym translation ON`、`NEW SPRFILE`×2920、`NEW SPCOMPONENT`×2920 | §d.3、e.6 |
| `1_PM.pdt` | GBK/CRLF、9,677 行、`$VERSION 4.2.0` | b.4 |

## 附录 C：本次会话实际执行的核对（可复现）

```
cd /d D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出
python test\probe_samples.py          # C1
python test\probe_samples2.py         # C2
python test\probe_kind26_keys.py      # C3
python test\test_contract_selfcheck.py  # C4
python test\check_dump_grammar.py       # C5
```

**C4 的关键输出（本次实测，逐字）**

```
counts = {'levels': 5, 'joints': 382, 'sections': 28,
          'members': {'beam': 598, 'column': 200, 'brace': 13}, 'members_total': 811,
          'slabs': 222, 'slabs_holes': 29, 'slabs_with_thickness': 80, 'walls': 0,
          'loads': {'beam-line': 77, 'joint-point': 44}, 'loads_total': 121}
validate: E-0  W-6
   W-MEM-SHORT x 5
   W-MEM-ZRANGE x 1
Kind=303: 6-B250*10.00 -> /RECT_SQUARE6728_2002-SPEC/B250*10.00
          1-D194X8.0   -> /TUBE_TUBE-SPEC/D194X8.0
          6-B200*10.00 -> /RECT_SQUARE6728_2002-SPEC/B200*10.00
Kind=26 : 只按 Name 命中 7 个（未中 ['[18a']）；叠加 <子类型>-<Name> 后未中 0 个
FAIL 项: 0
```

**未做的验证（不得当作已通过）**

* **未在 PDMS 实机运行**任何宏 / PML：本会话只在文件层面读取安装内的 PML 源码与原件，
  因此 §d 的所有语法、§12#1#2#10 的裁定都标注为「待实机确认」，不声称已验证。
* **未跑** `jwd_read/pdt_read/macgen/jwd_write/pdms_dump/cli/gui`——它们属于 S1/S3 实施包；
  本契约只提供签名、规则与自检夹具。

---

## 附录 D：R2 证据（逐字表 + 夹具）

### D.1 `PDMSxCA_Addin121.dll` 内 `.pdt` 的格式串（本次 C7 实测：按偏移取 UTF-16LE、NUL 截断）

| 偏移 | 格式串原文（逐字） | 用于段 |
|---|---|---|
| `0x033B1C` | `    ID={0}, NAME={1}, SHAPE={2}` | `$DEFFRAMESECTION` 行1 |
| `0x033B81` | `       KIND={0}, B1={1}, B2={2}, H1={3}, H2={4}, B3={5}, H3={6}` | 行2 |
| `0x033C05` | `       T1={0}, T2={1}, T3={2}, T4={3}, T5={4}, T6={5}` | 行3 |
| `0x033C75` | `       M={0}, RI={1}, RJ={2}, UA={3}, NAME1={4}` | 行4 |
| `0x0202DB` | `       EXI= {0} ` | `EXI` 前缀 |
| `0x0202C1` | `,{0}, {1} ` | `EXI/EXR` 的每对 |
| `0x02029F` | `       EXR= {0} ` | `EXR` 前缀 |
| `0x020154` | `    {0:F3},` | `ECS/ECE/ANG` 等 3 位小数 |
| `0x020344` | `    ID={0}, NAME={1}, TYPE={2}, ES={3:G2}, PR={4:G2}, EXC={5:G5}, DS={6:G5}` | `$DEFMATERIAL` |
| `0x0203DC` | `    ID={0}, NODES={1}, NODEE={2}` | `$NET` |
| `0x02041E` | `    ID= {0}, X= {1:F2}, Y= {2:F2}, Z= {3:F2}, FLOORID= {4}` | `$NODECOOR` |
| `0x020183` | `    ID={0}, TYPE={1}, NETID={2}, SECTID={3}, MATID1={4}, MATID2={5}, ECS1={6}, ECS2={7}, ECS3={8}, ECE1={9}, ECE2={10}, ECE3={11}, ANG={12}` | `$SETELEMENT` |
| `0x033D24` | `    ID={0}, TYPE={1}, SECTID={2}, MATID={3}, MATID2={4}, HOLEID={5}, EC={6:F1}` | `$SETWALL`/`$SETSLAB` |
| `0x033D24` 区 | `       NUB={0}, NETID=` 与 `    ID={0}, NUB={1}` | 墙板环 / `$RIGID` |
| `0x033E3D` | `       NO={0}, HI={1}, BL={2}, TL={3}, WID={4:G2}, LEN={5:G2}, HEI={6:G2}` | `$STORY` |
| `0x033E3D` 区 | `    ID={0}, NAME={1}, TYPE={2}, T1={3:F2}, T2={4:F2}` | `$DEFWASLABSECTION` |
| `0x02007E` | `SPCOMPONENT 3 OF SELEC 1 OF SPECIFICATION /Concrete_Wall-SPEC` | Add-in 找的墙规格（§7.3） |

> **注意（§j.8）**：上表里 `{…:G2}` 等与样本实测的数值形态有出入（如 `$STORY.WID=15200.00`）。
> 实现按「KEY 名/顺序以 DLL 为准、数值格式以样本为准」执行。

### D.2 样本 `1_PM.pdt` 的逐段行式（本次 C7 实测；`|` 后为样本行号）

```
L1     ;File I:\氯化因局部设备变动20250227\PDMS\1_PM.pdt saved 3/19/2025 8:4:27
L3-4   $VERSION / 3 空格 + 4.2.0
L6     $DESIGNPARA（50 行 × 20 值，4 空格缩进 + ', ' 分隔；L7 '    0.000, 0.000, 3.000, …'）
L58    $STORY
L59    '    ID=1, NUB=1'
L60    '       NO=1, HI=8300, BL=-1300, TL=7000, WID=15200.00, LEN=49400.00, HEI=12000.00'
L70    $NODECOOR
L71    '    ID= 3807, X= 1580.00, Y= 15200.00, Z= 11700.00, FLOORID= 2'
L72    '       EXR= 2 ,10005, 2 ,10012, 2e+06'
L1306  $NET        '    ID=65908, NODES=53207, NODEE=10207'
L2366  $DEFFRAMESECTION
L2367  '    ID=609, NAME=矩750X750, SHAPE=1'
L2368  '       KIND=1, B1=750, B2=0, H1=750, H2=0, B3=0, H3=0'
L2369  '       T1=0, T2=0, T3=0, T4=0, T5=0, T6=0'
L2370  '       M=6, RI=0.000, RJ=0.000, UA=0.000, NAME1='
L2371  '       EXI=1, 10011, 609'
L2528  $DEFWASLABSECTION  '    ID=183711, NAME=T600, TYPE=1, T1=600.00, T2=0.00'
L2534  $DEFMATERIAL       '    ID=110, NAME=C30, TYPE=262, ES=3e+04, PR=0.2, EXC=1e-05, DS=26'
L2541  $SETELEMENT
L2542  '    ID=65908, TYPE=2, NETID=65908, SECTID=1509, MATID1=310, MATID2=-9999, ECS1=0.000, …, ANG=0.000'
L2543  '       EXI=3, 10011, 65908, 10013, 30, 10014, 0 '      ← 行尾有空格（本契约不写）
L2544  '       EXR=19, -1004, 0.000, … , -44, 1.000'          ← 首行 10 对
L2545  '        -43, 80302.000, … , 10012, 3000441.000 '      ← 续行缩进 8，9 对
L6728  $SETWALL
L6729  '    ID=183805, TYPE=5, SECTID=183711, MATID=310, MATID2=0, HOLEID=-9999, EC=0.0'
L6730  '       NUB=4, NETID= 73308, 153408, 66908, 102208 '
L6750  $SETSLAB          '    ID=184706, TYPE=6, SECTID=184611, …'
L8076  $RIGID
L8077  '    ID=1, FLOORID=1, NUB=101'
L8078  '       SLABID= 188106, …（20 个）'
L8079  '           214906, …（20 个；缩进 11）'
L8104  $DEADLOAD
L8105  $DEFNODELOAD      ← 分组头后**紧随**子段头（无空行）
L8933  $LIVELOAD
L8934  $DEFLINELOAD
L9675-9676  （两个空行）
L9677  $END
L9678  （空行；文件以 $END + CRLF + CRLF 结尾）
```

### D.3 内置转化表（本次 C10 实测输出）

```
源表：3176 行 × 38 列  sha256=fc19f317be9cf9d0（前 16 位）
写出 engine/section_table.csv（3176 行）+ engine/section_table.meta.json
stats={"keys_unique":3176,"pkpm_name_nonempty":2835,"pkpm_name_unique":2835,
       "pdms_spec_path_unique":3176,"shapeval_nonempty":2335,"is_parametric_true":15,
       "family_code_known":2335,"kind_known":7,
       "confidence":{"high":1146,"medium":1433,"low":597}}
抽查：HN450X200 fam=39 dims={"B":200,"H":450,"family":39,"r":13,"tf":14,"tw":9}
                spec=/H_INTERNATIONAL-SPEC/HN450X200
      2-[18a    fam=32 dims={"B":74,"H":180,"family":32,"name":"[18a","subtype":2,…}
                spec=/C_LIGHT-SPEC/CL18a
      6-B250*10.00 fam=77 dims={"d":250,"family":77,"lib_family":6,"t":10}
                spec=/RECT_SQUARE6728_2002-SPEC/B250*10.00
```
⇒ `HN450X200` 的 `dims`（H=450/B=200/tf=14/tw=9）与 `.jwd` 样本的 `26,39,1,450,0,200,14,9,0,5,4484,`
**逐项一致** ⇒ §k.3 的 `Kind=26`（族码 39）闭环成立。

### D.4 目录宏最小示例（`dbmacro` 的产物形状 / `dbparse` 的夹具）

> 这是**本契约定义的**最小可解析夹具（含参数化族全链 + 两遍式 + 头尾）；
> `test/check_v2_contract.py` 会从本文件里抽出这个代码块做静态自检
> （`NEW`:`END` 平衡、`OLD` 无 `END`、必需链、纯 ASCII）。

```dbm
$S-  -- Synonym translation OFF
-- ----------------------------------------------------------------------
-- PKPM-JWD dbmacro: CONTRACT appendix D.4 minimal fixture (ASCII only)
ONERROR GOLABEL /PKPKERR

NEW CATALOGUE /PKPM_JWD_USER
PURP STL

NEW STSECTION /USER_SECTION
PURP STL

NEW STCATEGORY /USER_RECT
PURP STL

NEW TEXT /USER_RECT-PA1
PURP PARA
STEX 'B'

END
NEW TEXT /USER_RECT-PA2
PURP PARA
STEX 'H'

END

NEW DTSET

NEW DATA
DKEY APAR
PTYP DIST
PPRO ( ATTRIB DESP[1 ] )
DPRO ( 500 )
PURP DESP
NUMB 1
DTIT 'B '

END
NEW DATA
DKEY BPAR
PTYP DIST
PPRO ( ATTRIB DESP[2 ] )
DPRO ( 500 )
PURP DESP
NUMB 2
DTIT 'H '

END
END

NEW PTSSET

NEW PLINE
PKEY NA
PX 0
PY 0
CLFL true
TUFL true
PURP CLEW
CCON ANY

END
END

NEW GMSSET

NEW SRECTANGLE
PX 0
PY 0
PXLE ( ATTRIB DESP[1 ] )
PYLE ( ATTRIB DESP[2 ] )
DX 0
DY 0
DXL 0
DYL 0
TUFL true

END
END

NEW SPRFILE /Rectangle_Profile
GTYP BEAM
PARA 0

END
END
END
END

NEW SPWLD /PKPM_JWD_USER_SECTION
DESC 'Structural Steel'
PURP STL

NEW SPECIFICATION /PKPM_JWD_SECTION_USER
DESC 'PKPM_User_Section'
LNTP unset
QUES GTYP
PURP STL

NEW SELEC
DESC 'Rectangle_Profile'
TANS 'BEAM'

NEW SPCOMPONENT /USER_RECT-SPEC/Rectangle_Profile

END
END
END
END

-- pass 2: cross references

OLD PTSSET 1 of STCATEGORY /USER_RECT
NARE PLINE 2 of PTSSET 1 of STCATEGORY /USER_RECT

OLD SPRFILE /Rectangle_Profile
PSTR PTSSET 1 of STCATEGORY /USER_RECT
GSTR GMSSET 1 of STCATEGORY /USER_RECT
DTRE DTSET 1 of STCATEGORY /USER_RECT

OLD SPCOMPONENT /USER_RECT-SPEC/Rectangle_Profile
CATR SPRFILE /Rectangle_Profile

LABEL /PKPKERR
handle ANY
$S+
RETURN ERROR
endhandle
```

### D.5 R2 侦察报告的章节索引（实施者的阅读顺序）

| 要写哪个模块 | 先读哪些章节 |
|---|---|
| `pdt_write.py` | `pdt_format.md` §0–§2（词法/缩进）、§3（ID 编码）、§5（TYPE/SHAPE 词表）、§9（异常）；本契约 §j；D.1/D.2 |
| `sectionlib.py` | `db_pkpm_sections.md` §2（族码表）、§3（`$DEFFRAMESECTION`）、§4（`.jwd` 编码）、§5（映射与损失）；本契约 §a.4/§k；D.3 |
| `dbmacro.py` | `db_pdms_catalogue.md` §1（文法）、§2（顺序/两遍式）、§3（参数化链）、§6（生成方案与模板）、§6.4（幂等）；本契约 §l、D.4 |
| `dbparse.py` | `db_pdms_catalogue.md` §1.4（词法细节）、§2（外键）、§4（族/名/参数）、§5.2/§5.3（解析流程 + 24 条坑）、§7（分级清单）；本契约 §l.5 |
| 全部 | `pkpm_pdms_section_conflicts.md`（260/256/4/759/344 的归类）、`dbsect/pkpm_pdms_section_table.csv`（数据源） |

## 附录 E：R2 自检命令与输出（可复现）

```
cd /d D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出
python test\probe_v2_shapes.py        # C7  .pdt 行式 + DLL 格式串 + 转化表规模
python test\probe_v2_table_keys.py    # C8  转化表键/重复分析（256 条 in_pdms_macro=''）
python test\probe_v2_exr_wrap.py      # C9  EXR 每行 ≤10 组、SLABID 每行 20 个、缩进 8/11
python test\build_section_table.py    # C10 生成 engine/section_table.csv + meta
python test\check_v2_contract.py      # C11 v2 契约静态自检（见下）
python test\probe_v2_kind303_slots.py # C12 Kind=303 槽位原文（标定 §k.3）
```

**C11 检查项**（全部必须通过；实现按 `test/check_v2_contract.py`）：

1. `engine/section_table.csv` 可被 `utf-8-sig` 读、行数 = 3,176 + 表头、列序 = §k.2 的 15 列；
2. `SectionRec.key` 唯一、`pdms_spec_path` 唯一、`params_json` 可 `json.loads`；
3. `HN450X200` 的 `dims` 与 `.jwd` 样本 `26,39,1,450,0,200,14,9,0,5,4484,` 逐项一致；
4. 附录 D.4 的宏夹具：`NEW` 数 == `END` 数、`OLD` 均无 `END`、
   含 `PSTR/GSTR/DTRE/CATR/NARE` 五个引用链、`SPCOMPONENT 名 == /<STCATEGORY>-SPEC/<SPRFILE 名>`、
   **纯 ASCII**、容器名全部以 `/PKPM_JWD_` 开头、不含用户既有容器名；
5. 本文件（`spec/CONTRACT.md`）的 Markdown 表格列数自检（`test/check_markdown_tables.py`）。

**未做的验证（R2 同样不得当作已通过）**

* **未在 PDMS 实机运行**：R2 新写的目录宏、清场语句（§12#16）、`TYPE=3`（§12#15）均**未实机**；
* **未实现** R2 的四个新模块（`pdt_write`/`sectionlib`/`dbmacro`/`dbparse`）与 6 个新子命令——
  本契约只冻结签名、规则与夹具；实现与验收由后续实施包完成。

---

## 附录 F：R3 证据与夹具（唯一化 + 原生插件）

### F.1 `!!pkpmjwdUniquename` 的逐字夹具（`pdms/pkpmjwduniquename.pmlfnc` 的**产物形状**）

> `test/check_v3_contract.py` 从本代码块抽取并静态断言：签名、探测写法（EXIST + `(2,109)`）、
> 候选序列（`re`、`re2..re99`、上限）、`defined()` 守卫、`append` 记录、FAIL 返回空串。
> 每一行写法的出处以行尾 `-- ↑` 注释标明（实施时**保留**这些出处注释）。

```pml
-- PKPM-JWD导入导出 -- §o.2 命名唯一化（CONTRACT 附录 F.1 夹具）
-- 依赖：本文件被 $M 加载后，!!pkpmjwdUniquename 对所有调用方可用（§o.4）。
define function !!pkpmjwdUniquename(!base is STRING) is STRING
  if (defined(!!pkpmjwdRenames)) then           -- ↑ defined()：nucdesogwall.pmlobj:206
  else
    !!pkpmjwdRenames = object ARRAY()           -- ↑ object ARRAY()：nucroommcreation.pmlfnc
  endif
  if (!base eq '') then                         -- 空基名 = 编码错误，按失败处理（eq 出处：sdnfinver3:113）
    !!pkpmjwdRenames.append('FAIL||')           -- ↑ .append()：GRIDDESIGN.pmlfrm:986
    return ''
  endif
  -- 候选序列：base, base&'re', base&'re2' .. base&'re99'（§o.1，共 100 个；& 连接：nucdesogwall:185）
  do !idx from 0 to 99
    if (!idx eq 0) then
      !cand = !base
    elseif (!idx eq 1) then
      !cand = !base & 're'
    else
      !cand = !base & 're' & !idx.string()      -- ↑ .string()：GRIDDESIGN.pmlfrm:975
    endif
    var !probe EXIST $!cand                     -- ↑ 占用探测写法①（EXIST $!x，base 自带 /）：tgautonum.pmlfnc:33-41、abauserview.pmlfrm:859-860；(2,109) 双结局语义：abaarealib.pmlfrm:107-114
      handle (2,109)                            --   (2,109) = Undefined name ⇒ 可用
        if (!cand eq !base) then
          return !cand                          --   handle 内 return：abaarea.pmlfrm:527 同形态
        else
          !!pkpmjwdRenames.append(!pkpmjwdType & '|' & !base & '|' & !cand)
          return !cand
        endif
      endhandle
  enddo
  -- 全部 100 个候选都被占用 ⇒ 失败（§o.6）：留痕并返回空串，由宏的故障注入中止（§o.4）
  !!pkpmjwdRenames.append('FAIL|' & !base & '|' & !base & 're99')
  return ''
endfunction
```
> ⚠ 实施注意（**必须如实处理，不得假装上面逐字可跑**）：上面的夹具表达的是**算法与写法**的冻结契约；
> `return` 出现在 `do`/`handle` 块内、`elseif` 链等属于**实机语法层**——`return` 在 handle 块内已有
> 同形态直证（`abaarea.pmlfrm:527`），`do` 块内的 `return` 未单独取证。实施 S2 时要以能被 PDMS
> 接受的形式落地（必要时把 `do` 循环展开成显式 100 分支或逐个 `if` 链——**语义不变**），并把差异写进
> 交付说明；不得改变：候选序列、探测写法（EXIST + `(2,109)`）、记录格式（`!pkpmjwdType|原名|实际名`）、
> FAIL 语义（返回空串 + `'FAIL|…'` 留痕）。

### F.2 宏片段夹具（§o.4 模板的产物形状）

```pml
$S-  -- Synonym translation OFF
ONERROR GOLABEL /PKPMJWDERR
$M <$!pkpmjwdFuncPath>
!!pkpmjwdType = 'SITE'
!n = !!pkpmjwdUniquename('/PKPM_JWD')
if (!n eq '') then
  var !pkpmjwdFatal EXIST $!n
endif
NEW SITE $!n
!!pkpmjwdType = 'SCTN'
!n = !!pkpmjwdUniquename('/STL_COL_1')
if (!n eq '') then
  var !pkpmjwdFatal EXIST $!n
endif
NEW SCTN $!n
  SPREF /H_INTERNATIONAL-SPEC/HN450X200
  POSS E 400 N 400 U -2000
  POSE E 400 N 400 U -1000
LABEL /PKPMJWDERR
handle ANY
$S+
RETURN ERROR
endhandle
```
（骨架完整版见 §d.4；本片段只展示唯一化模板的接入点。）

### F.3 `pkpmjwd.uic` 与 `tgtext.uic` 的同构对照（验收 18-①）

| 结构项 | tgtext.uic（备份副本，行号） | pkpmjwd.uic（本包） |
|---|---|---|
| 根元素与命名空间 | `:2` `<UserInterfaceCustomization xmlns="www.aveva.com">` | 相同 |
| ButtonTool + Command | `:5-14` `<ButtonTool Name="TGTEXT.Open">` → `<Type>Instance</Type>` + `<Key>TGTEXT.OpenTools</Key>` | `Name="PKPMJWD.Open"` + `<Key>PKPMJWD.OpenTools</Key>` + `<Caption>PKPM JWD 导入导出</Caption>` |
| MenuTool 容器 | `:15-22` `<MenuTool Name="TGTEXT.Menu">` → `<Tools><Tool Name="TGTEXT.Open" /></Tools>` | `Name="PKPMJWD.Menu"` + `<Caption>PKPM JWD</Caption>` |
| 挂载点 | `:25-27` `<MenuBar><Tool Name="TGTEXT.Menu" /></MenuBar>` | 相同 |
| QAT | `:34-36` `<QATTools><Tool Name="TGTEXT.Open" /></QATTools>` | 相同 |
| 中文 Caption | `:12` `<Caption>三维文字</Caption>`（中文直排可行） | `PKPM JWD 导入导出` |
| 编码 | **UTF-8 无 BOM + LF**（实测 3C 3F 78、41 LF / 0 CRLF） | 相同 |

### F.4 可照抄样例的实测清单（本次亲自读取；路径为**实际存在**的副本）

| 文件 | 关键内容（行号） | 用途 |
|---|---|---|
| `D:\AI_Work\pmds三维文字程序-备份\TGTEXT\TGTextAddin.cs` | `:13` `class TGTextAddin : IAddin`；`:15-23` Name/Description；`:25-77` `Start(ServiceManager)` 取 `CommandManager` 并 `cm.Commands.Add(...)`；`:85-93` `OpenTextCommand : Command` 构造器设 `Key`；`:95-98` `IsValid`；`:100-112` `Execute()` + 错误弹窗；`:114-127` 单例窗体 + `WindowWrapper` Owner；`:131-136` `IWin32Window` 实现 | §p.1 的 Add-in/Command/窗体骨架 |
| 同目录 `TextForm.cs` | 35,588 B 的完整 WinForms 窗体（控件布局实例） | §p.3 的窗体写法 |
| 同目录 `build.cmd` | `:4` `set CSC=...v3.5\csc.exe`；`:10-23` `/target:library /platform:x86 /optimize+ /utf8output /codepage:65001` + 引用清单 + 源文件列表 | §p.2 编译命令的母本 |
| 同目录 `tgtext.uic` | 全文 41 行（F.3 对照表） | §p.3 的 .uic 母本 |
| 同目录 `deploy_tgtext.py` | `:21-26` 备份一次；`:28-38` DesignAddins.xml 幂等追加；`:41-51` DesignCustomization.xml 幂等追加；`:54-58` 复制 DLL/uic；`:61-84` 卸载 | §p.6 的脚本母本 |
| `D:\AI_Work\PDMS二次开发\PDMSSpecBuilder\dotnet\TGSPEC\TGSPECAddin.cs` | `:52-63` `Log()` 写 `<PDMS根>\TGSPEC\addin.log`（ASCII、时间戳） | §p.7 日志模式 |
| `D:\AI_Work\PDMS Copilot\src\CopilotAddin.cs` | 10,370 B；第 4 个 IAddin 实现旁证 | 旁证 |
| `D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB\aba\Forms\abaarealib.pmlfrm` | `:107-114` `VAR !exist EXIST /$!!…` + `handle (2,109)`（`-- Undefined name`） | §o.3 写法 1 |
| `D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB\aba\Forms\abaarea.pmlfrm` | `:523-528` `NEW IDLI` + `handle(41,12)` + `!!alert.error('An element of this name already exists.…')`；`:527` handle 内 `return` | §o.3 写法 2、F.1 注意 |
| `D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB\aba\Forms\abacrhierarchy.pmlfrm` | `:116-120` `NEW LIBY` + `handle (41,12)` + `delete DLLB` + `.dbref()` | §o.3 写法 2 变体 |
| `D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB\Building_Design\pmllib\concrete_design\TRADUCTEUR\nucdesogwall.pmlobj` | `:204` `$M/%PDMSUI%/DES/STLWRK/LPNODE $<AT $!PosString$>`；`:206` `if(defined(!!CDPNRTN))` | §o.4 的 `$M`、F.1 的 `defined()` |
| `D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB\mypml\forms\GRIDDESIGN.pmlfrm` | `:986` `!this.SCTNLIST.APPEND(!!CE)` | §o.2 的 `.append()` |
| `D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB\Building_Design\pmllib\room_manager\functions\nucroommcreation.pmlfnc` | `object ARRAY()` 建数组 | F.1 的数组建立 |
| `D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB\Building_Design\pmllib\concrete_design\ANCHOR\nucdesmanchor.mac` | `:9-11` 注释里的 `$m/V:/PML/…mac /DEV /floor450 …`（绝对路径带参形态） | §12#28 |

### F.5 本轮实测的注册文件事实（C16，只读）

| 文件 | 大小 | BOM | 换行 | 关键内容 |
|---|---|---|---|---|
| `D:\AVEVA\…\DesignAddins.xml` | 1,140 B | EF BB BF | CRLF×26 | `<string>TGTEXT</string>`、`<string>PDCOPILOT</string>` 已在（recon §4.1 全文） |
| `D:\AVEVA\…\DesignCustomization.xml` | 688 B | EF BB BF | CRLF×11 | `<CustomizationFile Name="TGTEXT" Path="tgtext.uic" />` 已在（recon §4.2 全文） |
| 备份 `tgtext.uic` | 1,081 B | 无（3C 3F 78） | LF×41 | F.3 对照表左列 |

### F.6 任务给定路径与实际路径的差异（**必须知道**）

| 任务原文 | 实测 | 处置 |
|---|---|---|
| `D:/AI_Work/PDMS三维文字程序/TGTEXT` | **不存在**（该目录在 2026-09-21 清库事故中被清空——见工作区根 AGENTS.md 的事故记录） | 改用实测完好的副本：`D:\AI_Work\pmds三维文字程序-备份\TGTEXT\`（13 文件全齐）与 `C:\TEMP\tgtext_tty\recovered2\`（20 文件，含 `TGTEXT__*` 前缀）；`D:\AI_Work\PDMS Copilot\` 与 `D:\AI_Work\PDMS二次开发\PDMSSpecBuilder\dotnet\TGSPEC\` **存在**，与任务清单一致 |

## 附录 G：R3 自检命令与输出（可复现）

```
cd /d D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出
python test\check_v3_csc_probe.py        # C13 csc 3.5 工具链实测（产物 CLR2/x86）
python test\check_v3_notouch.py snapshot # C14 建立无接触基准（G 盘 751 文件 + D:\AVEVA 顶层 645 文件）
python test\check_v3_notouch.py verify   # C14 核对（0 added / 0 removed / 0 changed）
python test\check_v3_contract.py         # C15 v3 夹具自检（F.1/F.2/F.3 + renames 键 + 表格列数）
```

**C13 关键输出（本次实测，逐字）**

```
=== v3 csc 工具链探针 ===
  [OK] csc 3.5 存在 C:\Windows\Microsoft.NET\Framework\v3.5\csc.exe
  [OK] 引用存在 Aveva.ApplicationFramework.dll / .Presentation.dll / Aveva.Pdms.Database.dll
       / Aveva.Pdms.Utilities.dll / Aveva.Pdms.Geometry.dll
  --- build.cmd 输出 ---
    BUILD OK: …\test\_v3_csc_check\stub_pkpmjwd.dll
  [OK] csc 退出码 0
  [OK] 产物存在 stub_pkpmjwd.dll 4096 B
  [OK] CLR 运行时版本 = v2.0.50727 @0x2d4
  [OK] PE machine = I386 (x86) 0x14c
  [OK] D:\AVEVA 被监视文件零变化（编译只读）
  [info] TGTEXT.dll(备份) CLR=v2.0.50727 machine=0x14c size=77824
  [OK] 样例 TGTEXT.dll 也是 CLR2/x86（旁证）
FAIL 项: 0
```

**C14 关键输出（本次实测）**

```
snapshot: D:\AVEVA\Plant\PDMS12.1.SP4  645 个文件
snapshot: G:\…\PKPM导入导出插件  751 个文件
verify:   0 added / 0 removed / 0 changed（两个区域）
```

**C15 检查项**：① F.1 夹具含 `define function !!pkpmjwdUniquename`、`EXIST /$!cand`、
`handle (2,109)`、`'re'` 与 `re99` 上限、`defined(`、`.append(`、`FAIL|`、`return ''`；
② F.2 夹含 `ONERROR GOLABEL /PKPMJWDERR`、`if (!n eq '') then`、`LABEL /PKPMJWDERR`；
③ §p.3 的 13 项控件名在 §p.3 表内可检索（文本级）；④ `report.renames` 键在 §h 出现；
⑤ CONTRACT.md 表格列数自检；⑥ `engine/README.txt`/`test/README.txt`/`pdms/README.txt`
包含 R3 条目（落地指引）。

**未做的验证（R3 不得当作已通过）**

* **未在 PDMS 实机运行**任何东西（含 `$M`、`VAR EXIST`、`!!pkpmjwdUniquename`、Add-in 加载）——
  §o/§p 的运行期行为全部标注"待实机确认"（§12#26/27/28）；
* **未部署**：deploy 脚本只交付（§p.10-1），C14 基准证明 `D:\AVEVA` 与 G 盘零变化；
* **未实现** §o/§p 的交付物（`pdms/pkpmjwduniquename.pmlfnc`、`pdms-net/*`、`engine/dist/*`）
  —— 本契约只冻结签名、命令、控件清单、协议与夹具；实现与验收 15–19 的完整执行由后续实施包完成。
