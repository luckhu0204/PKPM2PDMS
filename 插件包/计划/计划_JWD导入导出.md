# PKPM `.jwd` 导入/导出插件 —— 实施计划

> 编制日期：2026-09-23
> 目标：在现有《PKPM导入导出插件》基础上，**新增 `.jwd` 格式的导入（JWD→PDMS）与导出（PDMS→JWD）**
> 工作区：`D:\AI_Work\PKPM数据解析`
> 交付位置：`G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\PKPM-JWD导入导出\`（**新增子文件夹，不改动、不覆盖原有任何文件**）

---

## 0. 先说结论：**可行，而且 JWD 比 PDT 更值得做**

| 问题 | 结论 | 依据 |
|---|---|---|
| 能不能解析 `.jwd`？ | **能，而且不难**。`.jwd` 是**标准 SQLite3 单文件数据库**（头 16 字节 `SQLite format 3\0`），43 张 `pkpm*` 表，Python 标准库 `sqlite3` 直接读，零依赖、零授权风险 | 实测打开成功；表结构与 21 张非空表已全部 dump 并解码 |
| JWD 信息量相比 PDT？ | **更全**。JWD 含节点/轴网/柱段/梁段/支撑段/楼板(带洞口)/截面(带参数编码)/楼层标高/荷载；PDT 只有节点/网络/单元/墙板/荷载，且 `$STORY` 只覆盖 5/11 层、38 个节点 `FLOORID` 与几何不符 | `_recon/jwd_format.md` §2/§6 vs `_recon/pdt_format.md` §2/§9 |
| 能不能导入 PDMS？ | **能**。PDMS 的 Design/Structure 分支有成熟的 PML 建模命令链，且**本机 PDMS 安装里就有 AVEVA 官方与用户自写的同构范例**（`sctlcrelem.pmlfnc`、`StlGrating.pmlfrm`、`GRIDDESIGN.pmlfrm`），语法逐字可引 | `_recon/pdms_target.md` §6，全部带安装内文件行号出处 |
| 能不能导出回 JWD？ | **能**。PDMS 侧遍历 `STRU/FRMW/SBFR/SCTN/PANE` 取 `NAME/DESP/SPREF/POSS/POSE/JUSL/MEML/BANG`，Python 侧按 `pkpm*` 表结构写 SQLite；截面用匹配文件的**逆映射**还原 PKPM 截面名 | `pdms_target.md` §8.4 |
| 有没有硬阻塞？ | **没有**。唯一"不能做"的是逆向 SPAS（`CSpasDll` 封闭、本机无样本），而它**不在本需求路径上** | `pdms_target.md` §8.2 |

**一句话**：JWD 是 SQLite，比 PDT 更好解析；PDMS 侧有现成的、本机可引用的建模语法范例；导出回 JWD 也是写 SQLite。整条链子没有需要破解的二进制格式。

---

## 1. 现有插件现状（已查清，决定了"怎么加"）

**"现有插件"= `PKPM导入导出插件` 文件夹里的 P-TRANS 套件**，其 PDMS 侧主体是：

- `P-TRANS\PDMSxCA_Addin121.dll` —— **.NET Design Add-in**，被 **Dotfuscator 混淆**（中文资源串已加密，无法还原按钮文字）。
- 注册方式：`RegDllPDMS.exe` 写 `<PDMS根>\DesignAddins.xml` + `<PDMS根>\design.uic`（PDMS 根目录，**不是** `.mnu` 菜单）。
- 它**只认 `.pdt`**：DLL 内 C# 格式串 `ID= {0}, X= {1:F2}, Y= {2:F2}, Z= {3:F2}, FLOORID= {4}` 与 `1_PM.pdt` 第 71 行**逐字符一致**；13 个 `$` 段标记与文件完全对应。**这就是"只能解析 pdt"的根因。**
- 它在 PDMS 里建 **Design/Structure**：`STRUCTURE/FLOOR/FRMWORK/SBFRAMEWORK/SCTN/PANEL(PLOOP+PAVERT)/STWALL/WALL`，属性 `SPRE/DESP/POSS/POSE/JUSL/MEML/BANG/GTYPE`，命名模板 `/SITE/<工程>/MAINFRAME/STL_FRAME/EL<n>/{COLUMN|BEAM|HBRACE|VBRACE}`，并自动建 `ELEVIEW`/`PLANVIEW`。
- 截面换算两段式：内置 **2920 条** PKPM 截面编码表（如 `HN450X200 ↔ 39,450,200`）→ 再用 **`PKPM转PDMS截面匹配文件.txt`**（2836 条 `PKPM名, /规格/截面`）换成 `SPREF`。
- 反向已有 `KPM.PDMSxCA.PDMS2CA` 命令（但目标是 CA/STP 文本，**不是 `.jwd`**）。

### 由此得出的三条硬约束

1. **不能改现有 Add-in**——二进制混淆、无源码、重编译不合规也不现实。
2. **必须"旁路新增"**：新增独立包，与现有插件并存；用户原有菜单、原有 `.pdt` 流程**完全不受影响**。
3. **必须复用现有约定**，这样两套导入器产出可互换的模型：
   - 目录/规格：复用 `/PKPM_STSS`、`/PKPM_USER` 与 15 个 `/USER_*-SPEC/`（由 `PKPM（PDMS数据库）.txt` 建立）；
   - 截面匹配文件：复用 `PKPM转PDMS截面匹配文件.txt`（并补充其缺口，见 §4.2）；
   - PDMS 实体层级与命名：复用 Add-in 的 `/SITE/<工程>/MAINFRAME/STL_FRAME/EL<n>/…`。

---

## 2. 已完成的可行性侦察（本次工作区 `_recon\`）

| 产物 | 内容 |
|---|---|
| `pdt_format.md`（805 行）+ `parse_pdt.py` | PDT 13 段逐字段规范、实体关系图、ID 编码规律（**全局序号×100+类码**，序号 1…2841 密集无冲突）、`EXI/EXR` 续行语义、`LOADID` 负号跨表指代、单位（mm/MPa/kN·m）、几何一致性（0 悬挂引用、335 个面板回路全闭合） |
| `jwd_format.md`（9 章）+ `jwd_dump_all.py` + `canonical_model.json` | JWD 43 表逐一规范；**外键全部指向父表 `ID`**；线性构件表示法（梁=1 行 `pkpmBeamSeg`、柱=1 行 `pkpmColSeg`、支撑=1 行 `pkpmBraceSeg`；`(StdFlrID,GridID)` 恒为 1 行）；**`ShapeVal` 解码**（`Kind,参数…,材性,自身ID`，已解 Kind 1/2/3/26/303，其中 `HN` 族 8 条与 PDMS 库存 7 条精确吻合）；**Z 值必须由 `pkpmFloor.LevelB+Height` 推导，`pkpmStdFlr.Height` 全为 0 不可用**；22 张空表清单 |
| `pdms_target.md`（807 行）+ 全部字符串提取 | 现有插件技术栈与创建物（见 §1）、**截面匹配文件全解析**（2836 条 / 53 个规格前缀 / 10 大族，附录 A 逐行未删减）、**目录宏结构**（12 STSECTION / 57 STCATEGORY / 2920 SPCOMPONENT / 57 DTSET）、**PDMS 建模惯用法**（每条都带安装内文件+行号出处）、**编码纪律**（PML/宏=GBK 无 BOM；`.uic`=UTF-8 带 BOM；`.pdt`/匹配文件=GBK+CRLF） |

---

## 3. 交付形态

在现有插件文件夹内新增一个**自包含子包**（不触碰原有任何文件）：

```
PKPM导入导出插件\
├─ P-TRANS\                      ← 原有，不动
├─ 1_PM.pdt  JLCJ2.jwd  ...      ← 原有，不动
└─ PKPM-JWD导入导出\              ← ★ 本次新增
   ├─ engine\                     Python 引擎（标准库，零第三方依赖）
   │   ├─ jwd_read.py             .jwd(SQLite) → 规范模型(canonical)
   │   ├─ pdt_read.py             .pdt(文本)   → 规范模型（对照/回归用）
   │   ├─ canonical.py            规范模型数据类 + 校验器（唯一契约）
   │   ├─ secmap.py               截面匹配文件解析 + 解析器 + 逆映射
   │   ├─ macgen.py               规范模型 → PDMS 宏（GBK/CRLF，Structure 命令）
   │   ├─ jwd_write.py            规范模型 → .jwd(SQLite)
   │   ├─ pdms_dump.py            PDMS 导出文本 → 规范模型
   │   ├─ cli.py                  命令行入口（jwd2pdms / pdms2jwd / check）
   │   └─ secmap_extra.txt        匹配文件补充条目（HN 族等缺口，独立成文件不污染原件）
   ├─ pdms\                       PDMS 端 PML 包（GBK 无 BOM）
   │   ├─ pkpmjwd.pmlfrm          操作窗体（选文件 / 勾选构件类别 / 基点转角，复刻现有体验）
   │   ├─ pkpmjwd_export.pmlfnc   遍历 STRU/FRMW/SBFR/SCTN/PANE → 中性导出文本
   │   └─ pkpmjwd_run.mac         执行 Python 生成好的导入宏
   ├─ install\
   │   ├─ install.ps1             安装（复制 PML 到 PMLLIB + 注入 design.uic 菜单，**改前先 .bak**）
   │   └─ uninstall.ps1           卸载（同样先备份）
   ├─ docs\
   │   ├─ 使用说明.md             操作步骤、参数含义、菜单在哪
   │   ├─ 格式规范_JWD.md          JWD 表/字段/ShapeVal 解码（交付版，去侦察口气）
   │   ├─ 格式规范_PDT.md          PDT 规范（同上）
   │   ├─ 截面映射说明.md          匹配文件语法、缺口清单与补充办法
   │   └─ 交付清单.md              改了什么、装了什么、怎么回滚
   ├─ test\                       测试与证据（脚本 + 运行输出）
   └─ 计划\计划_JWD导入导出.md     本文件
```

**为什么是 Python 引擎 + PML 前端**：JWD 是 SQLite，Python 标准库直接读写最稳；PDMS 内部取数/建模用 PML 才合规且能拿到全部属性。二者用**中性文本文件**交换，任何一端可单独替换。

---

## 4. 技术路线

### 4.1 三条管线（共用规范模型 = 唯一契约）

```
【导入】  .jwd(SQLite) ──jwd_read.py──► canonical ──macgen.py──► PDMS 宏(.mac, GBK) ──PDMS 里执行──► Design/Structure 模型
【导出】  PDMS 模型 ──pkpmjwd_export.pmlfnc──► 中性导出文本 ──pdms_dump.py──► canonical ──jwd_write.py──► .jwd(SQLite)
【对照】  .pdt(文本) ──pdt_read.py──► canonical ──┤ 用于交叉验证与回归（两格式同构件应得同几何）
```

### 4.2 关键技术决策

1. **规范模型（canonical）是唯一契约**：`Level / Joint / Member(梁|柱|支撑) / Panel(板含洞口) / Wall / SectionDef / MaterialDef / Load`。三读一写（JWD读、PDT读、PDMS读、宏生成、JWD写）全部只依赖它。契约文件 `engine/canonical.py` 先行冻结，后续所有实施包并行且互不重叠。
2. **Z 值推导**（JWD 侧最容易错）：`z_top = pkpmFloor.LevelB + pkpmFloor.Height`；梁/板在 `z_top(+HDiff)`；柱自 `LevelB+HDiffB` 到 `z_top`。已用 5 层 × 全构件自检（0 例外）。
3. **截面解析三段式**（与现有插件同构，保证互换）：
   `ShapeVal(GWD 编码) → PKPM 截面名 → 截面匹配文件 → /PDMS规格/截面`。
   - JWD 侧 `ShapeVal` 首字段即 PKPM 族码（已解 Kind 26→H 族 39、Kind 32→槽钢、Kind 303→薄壁 77 等），与现有插件内置表同源，可用作**独立校验**；
   - 匹配文件已有 `HN450X200`/`HN300X150` 等 → `/H_INTERNATIONAL-SPEC/`，本样本所需截面**大部分直接命中**；
   - 缺口用**独立补充文件** `secmap_extra.txt` 处理（如 `薄壁方钢管 → /RECT_SQUARE50018-SPEC/…`、`热轧无缝圆钢管 → /TUBE_TUBE-SPEC/…`），**不修改用户原件**；
   - 匹配文件已知 **257 条坏映射**（`DOUBLE_L_EQUAL_CROSS` 缺 `C` 等）→ 工具给出**可用性校验与自动纠正建议**，不擅自改原件。
4. **坐标系与单位**：统一 mm，Z 向上，右手系。基点 `E/N/U` 与转角 `ANG` 作为导入参数（复刻现有插件的 `txtBox_BasePoint`/`txtBox_ANG` 体验）。
5. **PDMS 建模语法只引用本机既有惯例**（`_recon/pdms_target.md` §6 每条带出处）：`NEW SITE/ZONE/STRU/FRMW/SBFR`、`NEW SCTN + SPREF + DESP + POSS/POSE + JUSL/MEML + BANG`、`NEW PANE + ORI + NEW PLOOP + HEIGHT + SJUS + NEW PAVERT POS`、墙用 `SPRE`、板用 `SPREF`。**不凭空造语法。**
6. **编码纪律（本机历史踩坑项）**：生成的宏与 PML = **GBK 无 BOM + CRLF**；`.uic` = UTF-8 带 BOM；`.jwd` = SQLite（文本列用 GBK 写入以与 PKPM 一致）。
7. **导出侧截面逆映射**：`SPREF /H_INTERNATIONAL-SPEC/HN450X200` → 匹配文件逆向 → PKPM 名 `HN450X200` → 反算 `ShapeVal`（族 39 + H/B）；参数化截面由 `DESP` 反推。无法逆映射的截面**明确列入报告**，不静默丢弃。
8. **不碰的东西**：不改 `PDMSxCA_Addin*.dll`、不改 `PKPM转PDMS截面匹配文件.txt`、不改 `PKPM（PDMS数据库）.txt`、不逆向 SPAS、不改 PDMS 安装内任何现有文件（安装器只**新增** `PMLLIB\<包名>\` 与在 `design.uic` 中**追加**一个菜单项，且改前备份 `design.uic.bak_<日期>`）。

### 4.3 与现有插件的一致性验收

同一栋结构分别用 `1_PM.pdt` 与 `JLCJ2.jwd` 导入，应得到**几何等价**的 PDMS 模型（层标高、构件数量、截面规格可逐项比对）。这是本项目最有说服力的正确性证据，工作流将产出该对比表。

---

## 5. 风险与待验证项（不隐瞒）

| # | 项 | 影响 | 处置 |
|---|---|---|---|
| R1 | `ShapeVal` 未解码族：Kind=3（单一尺寸族）、Kind=303 壁厚槽位含义、轻型槽钢厚度表 | 少量截面名称可能推算不准 | 已解族优先；未解族**不猜**，落"待确认清单"+ 按 `Name` 字段优先（`Name` 非空时直接用名） |
| R2 | `Ecc/EccX/EccY` 正负号约定未证实 | 偏心方向可能反向 | 默认按 0 / 可配置符号；生成报告列出所有非零偏构件供人工确认 |
| R3 | `pkpmJoint.HDiff` / `BraceSeg.HDiff2=6650` 单条异常 | 个别节点标高 | 按实测公式处理 + 异常单列报告 |
| R4 | 荷载数值字段语义未全证实 | 荷载仅作**参考信息**导出 | 明确标注"荷载为参考值，不参与几何" |
| R5 | `NEW SBFR` 是否必需父级；`POSS/POSE` vs `POSSTART/POSEND` 等价性 | 宏可能在实机报错 | 采用本机两种写法都出现的**最保守写法**（`SBFR` + `POSS/POSE`，与 Add-in 的 .NET 属性实例名一致），并做静态语法核对 |
| R6 | 无 PDMS 实机运行条件（本次） | **"未实机验证"必须如实标注** | 所有结论标注证据等级：静态核对 / 样本数据自检 / **未实机**。给出用户侧实机验证步骤清单 |

---

## 6. 验收标准（可检查、可复现）

1. `python engine\cli.py jwd2pdms JLCJ2.jwd -o out.mac` 在样本上**零报错**跑通，产出的 `.mac` 为 GBK+CRLF，含全部 598 梁 / 200 柱 / 13 支撑 / 222 板。
2. **截面解析覆盖率报告**：本样本用到的全部截面 100% 给出结论（命中映射 / 走参数化 / 明确列入待确认），不允许出现"静默跳过"。
3. **几何自检**：层标高、构件端点 Z、板顶点 Z 与 `pkpmFloor` 推导值逐一比对，0 例外。
4. **交叉验证**：`JLCJ2.jwd` 与 `1_PM.pdt` 走各自读取器得到的层标高/构件总数/包围盒对比表（两者为不同粒度模型，差异需**有解释**）。
5. **往返测试**：`JLCJ2.jwd → canonical → .jwd'`，两库非空表逐表行数与关键列比对；差异清单为空或全部有解释。
6. **导出链路静态测试**：用一份**由导入器生成的 PDMS 导出文本**（模拟 PDMS 取数结果）跑 `pdms_dump.py → jwd_write.py`，验证逆映射与表引用完整性（外键全部可解析）。
7. **独立复核**：由**独立于实现者**的复核角色，用**独立实现**（不复用引擎代码）从原始 JWD 直接算几何，与引擎结果比对。
8. **交付清单完整**：改了哪些文件、装了什么、如何卸载回滚，逐条列出。

---

## 7. 工作流编排（用动态工作流执行）

**阶段划分与并行度**（文件范围互不重叠，故可并行；每个实施包结束后由独立角色复核）：

| 阶段 | 角色 | 工作包（文件范围） | 并行 |
|---|---|---|---|
| S0 契约冻结 | 架构 | `engine\canonical.py` + `spec\CONTRACT.md`（接口/命名/编码/校验规则） | 单 |
| S1 实施（并行 4 包） | 实施 ×4 | ①`jwd_read.py` ②`pdt_read.py`+`secmap.py` ③`macgen.py` ④`jwd_write.py`+`pdms_dump.py` | 4 路 |
| S2 PDMS 端 | 实施 | `pdms\*.pmlfrm/.pmlfnc/.mac`（GBK） | 单 |
| S3 集成 CLI + 安装器 | 实施 | `engine\cli.py`、`install\install.ps1`、`uninstall.ps1` | 单 |
| S4 测试与证据 | 测试 | `test\*`：单元 + 几何自检 + 往返 + 覆盖率 + 导出链路 | 单（依赖 S1/S3） |
| S5 独立复核 | 复核 | 独立实现重算几何 + 逐条审查 S1–S3 产物 + 风险清单 | 单（与 S4 并行） |
| S6 文档与封装 | 文档 | `docs\*`、`交付清单.md` | 单（依赖 S1–S5） |
| S7 门禁 | 编排（脚本内 `world.run`） | 跑验收 8 条，失败则**带反馈回炉**（amend 重跑失败包） | — |

**门禁（gate）**：S7 用真实命令跑 §6 的 1–6 条；**任何一条失败即不得进入文档定稿**，由编排脚本带着失败证据回到对应实施包重做（最多 2 轮）。第 7 条（实机）**按事实标注为"未实机验证"**，不伪造。

---

## 8. 明确不做（范围边界）

- ❌ 逆向或重编 `PDMSxCA_Addin*.dll`（.NET + Dotfuscator，无源码）
- ❌ 逆向 SPAS（`CSpasDll` 封闭、本机无样本、不在需求路径）
- ❌ 修改用户任何原件（`1_PM.pdt`、`JLCJ2.jwd`、`PKPM转PDMS截面匹配文件.txt`、`PKPM（PDMS数据库）.txt`、`P-TRANS\*`）
- ❌ 改 PDMS 安装内既有文件（安装器只**新增**文件 + 在 `design.uic` **追加**菜单项，且改前备份）
- ❌ 声称任何未经实机验证的结论（证据等级随交付物一起给出）

---

# 9. 修订记录 R2（2026-09-24 用户追加需求）

用户追加三项要求：**① PDT 格式也要完整的导入 + 导出**；**② 荷载不需要**；**③ 需要实现 PDMS 数据库层面的转化（用用户提供的"转化表"），pdt 和 jwd 都要**。

第 ③ 项的解读：**"数据库层面"= PDMS 的 Catalogue（目录）+ Specification（等级/规格）**，即截面库本身，不是模型里的构件。用户说的"转化表"就是他自己给的那几份文件：

| 文件 | 规模 | 用途 |
|---|---|---|
| `PKPM（PDMS数据库）.txt` | 1,406,051 B / 70,301 行 | **一份真实的 PDMS 目录重建宏**（PDMS 自带 DB Output/DATAL 导出）：3 个 CATALOGUE、12 个 STSECTION、57 个 STCATEGORY、533 个参数名 TEXT、57 个 DTSET 参数化轮廓、2,920 个 SPRFILE、2,920 个 SPCOMPONENT |
| `P-TRANS\pkpm_section_DBOutput.txt` | 1,347,677 B | 2018 版同构宏，截面集合与上面完全相同 |
| `PKPM转PDMS截面匹配文件.txt` | 2,836 条 | `PKPM截面名, /规格/截面` 映射 |
| `P-TRANS\USERSTL.LIB` | 245,340 B | PKPM 钢材库 |
| `PDMSxCA_Addin*.dll` 内嵌表 | 2,326 名 / 1,131 码 | PKPM 截面名 ↔ 参数编码 |

## 9.1 本次新增的核心：双向四向截面转化

```
                      ┌── .jwd  pkpm{Col,Beam,Brace}Sect (Kind / ShapeVal 编码)
PKPM 截面定义 ─────────┤
                      └── .pdt  $DEFFRAMESECTION / $DEFWASLABSECTION / $DEFMATERIAL
        ⇅  （族码表 + 尺寸参数，双向互算；信息损失逐项列清）
PDMS 数据库   ─────────  Catalogue：STSECTION / STCATEGORY / SPRFILE / DTSET / PTSSET / GMSSET
                        Specification：SPECIFICATION / SELEC / SPCOMPONENT
```

四个方向都要实现，叠加已有的几何链路，命令行最终为：

```
jwd2pdms / pdt2pdms     几何：PKPM → PDMS 建模型宏
pdms2jwd / pdms2pdt     几何：PDMS 模型 → .jwd / .pdt
jwd2db   / pdt2db       数据库：PKPM 截面定义 → PDMS 目录 + 规格宏
db2jwd   / db2pdt       数据库：PDMS 目录 + 规格 → PKPM 截面定义
jwd2pdt  / pdt2jwd      格式互转（走规范模型）
dbsections              列出 / 导出截面字典与转化表
```

## 9.2 已完成的侦察结论（实施按此，不再重新摸索）

**PDMS 目录宏文法**（`_recon/db_pdms_catalogue.md`，1,123 行，每条带行号）：该 .txt 就是 PDMS 自带 `DB Listing`（PML `rptoutput.pmlfrm`）的产物，头尾 10 行逐字来自其 `:724-729` 与 `:3586-3596`。

- 命令集：`$S±`、`ONERROR GOLABEL`、`INPUT BEGIN/END/FINISH`、`NEW…END`、`OLD…`（**无 END**）、`LABEL / handle ANY / RETURN ERROR / endhandle`
- **依赖顺序**：CATALOGUE > STSECTION > STCATEGORY > {TEXT, DTSET>DATA, PTSSET>PLINE, GMSSET>SPROFILE>SPVERT/SRECTANGLE/SANNULUS, SPRFILE} → SPWLD > SPECIFICATION > SELEC > SPCOMPONENT → **第二遍全部 `OLD` 补引用**（PSTR/GSTR/DTRE/CATR/NARE）
- 参数化链：`TEXT(-PAn)`=参数名 → `DTSET DATA(NUMB/DKEY/DTIT/PPRO/DPRO/PURP)` → `PLINE` 表达式用 `ATTRIB DESP[n]` 画轮廓 → `SPRFILE(GTYP,PARA)` → `PSTR/GSTR/DTRE` → `SPCOMPONENT`（名=`/<族>-SPEC/<轮廓>`，2,920/2,920 成立）
- **重跑无 OVERRIDE，必失败** → 生成侧需唯一名，或按官方 `OLD … DELETE … MEM` 范式
- 逆向坑：`OLD` 无 END 且类型可省、`NEW` 的 END 可省、全名/缩写并存、`$` 续行 + 裸值行、括号嵌套表达式、负号两种写法、**词值含空格**（`S RSA`）会致 `/H_AMERICA`、`/H_EUROPE` 的 25/26 个值摆动

**PKPM 截面侧**（`_recon/db_pkpm_sections.md`，879 行 + 机器可读转化表）：

- `USERSTL.LIB` 是**私有二进制**（头 `39 0F 03 00` + 80 字节 `PKPM Steel Library Win`，熵 5.91），含 2,925 个 16 字节名槽但 16 个 f32 载荷与目录宏 `PARA` **无一能对上** → **不能**当几何参数源。权威源改用 **目录宏的 `SPRFILE PARA` + `STCATEGORY` 具名参数**
- **族码表已建成 24 个族码**并经"显式编码对 × 规格属主"互证：31/32/33/36/37/38/39/40/66/71/72/73/77 + TUBE15/H16/PIPE17/TEE18/Z20/C21/CROSS22/CROSS_I23/ANGEL24/XI2/CIRCLE3；`19` 推断；`TRAPEZOID/DOUBLE_C/RECT` 未知
- **`.pdt` 可反算**：DLL 里逐字存在全部 5 行格式串（`0x033B1C/0x033B81/0x033C05/0x033C75/0x0202DB`），字段语义已定；仅 `M`、`EXI` 第 2 数（10011）未定
- **`.jwd` 反算**：Kind=1/3 可；Kind=26 族码 39 可（tf/tw 齐）；Kind=303 打包串可完整还原（`12866,12341,…` → `B250*10.00`）；族码 32 尺寸槽序与 Kind=2 未知
- **信息损失**：`.pdt` 无力学量字段、型钢 `T1..T6` 恒 0 → `.pdt` ↔ `.jwd` 对型钢厚度非无损。故两条链路各自直连 PDMS，**不做绕道互转**
- 匹配文件 **260 行右值失效**（256 行 `DLE*` vs 宏里 `DLEC*/DLU*/DLUS*`，4 行缺前导 `/`），另有 759 处大小写差异
- 样本缺口：`/Concrete_Slab-SPEC`、`/Concrete_Wall-SPEC` 及 `T100/T120/T600` 只存在于 `.pdt`，PDMS 宏里没有 → **正好由本次"生成目录+规格宏"能力补上**
- 交付物：`pkpm_pdms_section_table.csv`（3,176 行 × 38 列）+ `.json` + `pkpm_pdms_section_conflicts.md`

## 9.3 荷载：明确不做（用户确认）

- 不导出荷载、不做荷载映射、不新增荷载相关工作
- `.pdt` 写出时荷载段只写段头、体内为空（`$DEADLOAD` / `$LIVELOAD` 两组，其下 4 个子段为空），保证现有 Add-in 解析不炸
- canonical 里保留荷载解析（已有实现与测试覆盖，不动），报告与文档明确标注"荷载不参与转换"

## 9.4 R2 新增验收标准

9. **PDT 往返**：`JLCJ2.jwd → canonical → .pdt'` → 再读回，层标高/构件数/包围盒等价；生成的 `.pdt` 段名与行式与现有 Add-in 里的格式串**逐字静态一致**
10. **PDT 导入链路**：`pdt2pdms` 对 `1_PM.pdt` 产出宏，其层标高与 `jwd2pdms` 对 `JLCJ2.jwd` 的产出一致（同工程两格式互证），差异有解释
11. **数据库导出**：从 `PKPM（PDMS数据库）.txt` 解析出规格字典（≥2,920 条），与匹配文件交叉一致率报告（含已知 260 条失效与 759 处大小写差异的归类）
12. **数据库导入**：`jwd2db` 与 `pdt2db` 为两个样本实际用到的**全部**截面生成 PDMS 目录+规格宏，并覆盖缺口（`/Concrete_Slab-SPEC/T100|T120`、`/Concrete_Wall-SPEC/WALL-600`）。生成的宏必须满足：两遍结构（第一遍 NEW、第二遍 OLD 补引用）、参数化族带 TEXT/DTSET/PTSSET、SPCOMPONENT 挂在 `SELEC … TANS 'BEAM'` 下、重跑有唯一名或 `OLD+DELETE` 策略
13. **数据库反向闭环**：`db2jwd` / `db2pdt` 从目录宏 + 匹配文件反算出 `.jwd` 的 `*Sect`（Kind/ShapeVal）与 `.pdt` 的 `$DEFFRAMESECTION` 段；**用反算结果再跑一次 `jwd2db`/`pdt2db` 能回到同一批规格名**（闭环校验），信息损失列清单
14. **转化表交付**：CSV/JSON 转化表在包内，行数与校验和可复现

## 9.5 R2 新增风险

| # | 项 | 影响 | 处置 |
|---|---|---|---|
| R7 | PDMS 目录宏**无 OVERRIDE**，重跑必失败 | 重复导入报错 | 生成侧默认给唯一前缀名；同时生成可选的 `OLD … DELETE … MEM` 清场版本 |
| R8 | CATALOGUE 级操作会动用户的 PDMS 目录库 | 误操作影响面大 | 生成宏默认建**本包自己的 CATALOGUE**（`/PKPM_JWD_*`）并只对该目录做 OLD/DELETE，**不改用户既有目录**；文档写明 |
| R9 | `USERSTL.LIB` 解析不动（私有二进制） | 不能从 PKPM 库直出几何参数 | 权威源用目录宏 `PARA` + 派生族码表；文档说明该文件不作为数据源 |
| R10 | `.pdt` ↔ `.jwd` 对型钢厚度非无损 | 互转有信息损失 | 两条链路各自直连 PDMS，不做绕道互转；损失列清单 |
| R11 | 匹配文件 260 条失效 + 759 处大小写差异 | 部分规格解析不到 | 报告归类并给纠正建议；**不改用户原件**，纠正项写进本包补充文件 |
| R12 | 族码 19、TRAPEZOID/DOUBLE_C/RECT 未解；Kind=2 与族码 32 槽序未知 | 极少数截面无法自动生成 | 列入"待确认"清单，生成时跳过并报告，**不猜** |

## 9.6 范围边界（R2 补充）

- ❌ 荷载的导入 / 导出 / 映射
- ❌ 逆向 `CA2PDMS` / `PDMS2CA` 两个 .NET 类（已知可解 `M`/`EXI` 等残留疑点，但不在需求内）
- ❌ 修改用户的 PDMS 既有目录 / 规格库（只生成宏，由用户自行执行；且只针对本包自己的目录）
