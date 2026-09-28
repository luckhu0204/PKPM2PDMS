# PKPM2PDMS v2.1.0 交付说明（相对 v2.0 的改动与迁移）

> 交付树：`D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0`（2026-09-28 定稿）
> 入口文档：`从这里开始.txt`（安装/卸载）· `交付清单.txt`（构建产物与口径）· `SHA256哈希清单.txt`（全树逐文件哈希）
> 本文回答三个问题：**这次改了什么、和 v2.0 差在哪、装过 v2.0 的机器怎么迁**。

---

## 1. 本次改动清单（v2.0 → v2.1.0）

### 1.1 标识改名（主项）

改的是「插件标识」，不是「PKPM 格式名」。token 级映射摘要（完整展开见 `计划/RENAME_MAP.md` §1–§2）：

| 场合 | 旧名 | 新名 |
|---|---|---|
| 标识符（全大写） | `PKPMJWD` | `PKPM2PDMS` |
| 标识符（全小写） | `pkpmjwd` | `pkpm2pdms` |
| 连字符形态 | `PKPM-JWD` / `PKPM-JWD导入导出` | `PKPM2PDMS` / `PKPM2PDMS导入导出` |
| SITE/容器名前缀 | `/PKPM_JWD`、`/PKPM_JWD_` | `/PKPM2PDMS`、`/PKPM2PDMS_`（含 `_USER`/`_STSS`/`_USER_SECTION`/`_LIB`/`_SPEC`） |
| PML 函数/全局量 | `!!pkpmjwd*`（23 个 extern 函数 + 2 个全局数组） | `!!pkpm2pdms*` |
| 引擎环境变量 | `PKPMJWD_ENGINE` | `PKPM2PDMS_ENGINE` |
| 文件名 | `pkpmjwd.pmlfrm`、`pkpmjwdexport.pmlfnc`、`pkpmjwddbexport.pmlfnc`、`pkpmjwduniquename.pmlfnc`、`pkpmjwdrun.mac`、`PKPMJWDAddin.cs`、`PKPMJWDForm.cs`、`pkpmjwd.uic`、`deploy/undeploy_pkpmjwd.py`、`pkpmjwd_engine.exe` | 全部改为 `pkpm2pdms` 形态 |
| 备份后缀 / PMLLIB 子目录 | `.pkpmjwd-bak`、`pkpmjwd\` | `.pkpm2pdms-bak`、`pkpm2pdms\` |

改名前基线规模（RENAME_MAP §2.3 实测）：`PKPMJWD` 1 466 处/67 文件、`PKPM-JWD` 1 481 处/186 文件、`pkpmjwd` 1 729 处/100 文件、`PKPM_JWD` 16 298 处/42 文件（其中真正的应改目标为排除运行产物后的 224 处/39 文件）。

**明确不改的**（RENAME_MAP §3）：PKPM 自有数据容器名与字段名；命令名/模块名/格式名（PDMSDUMP、.pdt）；UIC `<Version>1.0`（AVEVA 格式版本）；契约 schema 常量 `CONTRACT_VERSION = "1.0"`；内部轮次号 R1/R2/R3。

### 1.2 图标

新增 `图标/pkpm2pdms.ico`（多尺寸）+ `pkpm2pdms_256.png` + `小尺寸预览.png`；两个 exe（PyInstaller `--icon`）与 .NET DLL（csc `/win32icon` + `/resource`）共用同一图标源。静态检查证明 ico 的 7 个条目逐字节出现在两个 exe（各 1 次）与 DLL（各 2 次）（`验收/static_result.json` icon 段 notes）。

### 1.3 版本号统一

插件版本 v2.0 / v1 → **v2.1.0**：DLL 新增 `AssemblyInfo.cs`（AssemblyVersion / FileVersion 2.1.0.0），exe 文件名带 `_v2.1.0`，GUI 标题与文档同步。版本号的三层含义（插件版本 / 契约 schema 1.0 / 格式版本）见 `从这里开始.txt` 第 6 条。

### 1.4 实机测试发现的缺陷修复（v2.0 带病，本次修复）

> 因此「v2.1.0 相对 v2.0 只改名片、逻辑一行未改」这句旧口径**不再成立**，准确说法是：
> **以标识改名与版本统一为主题，另含下列 4 处缺陷修复**（明细与证据：`验收/real_test_result.json` fixes[0..4]）。

1. **宏生成器守卫行非法语法**（`插件包/engine/macgen.py`）：旧写法 `var !pkpm2pdmsFuncMissing EXIST /` 是解析期 CP 语法错，宏整份加载失败；改为 `!pkpm2pdmsFuncMissing = !!pkpm2pdmsUniquenameMissing()`（运行期报错、由宏头 ONERROR 承接，语义不变）。修复后重打包两个引擎 exe。
2. **两条安装路线 Tool Key 撞名**（`插件包/install/install.ps1`、`uninstall.ps1`、`安装程序构建/src/installer_core.py`）：legacy 注入 design.uic 的 Key 原与原生 uic 完全同名（PDMS 整份拒载）；legacy 一律加 `.PML.` 前缀 → `PKPM2PDMS.PML.Menu` / `PKPM2PDMS.PML.Open`。原生路线的 Key（`PKPM2PDMS.Menu`/`PKPM2PDMS.Open`）由契约 §p 逐字冻结，不动。
3. **legacy 窗体 10 处 para 缺 text 关键字**（`插件包/pdms/pkpm2pdms.pmlfrm` 第 35、47、60、76、78、80、82、84、86、88 行）→ 补齐；窗体从「CP 语法错打不开」变为可以打开。
4. **交付脚本旧标识残留 15 处**（`插件包/deliver/collect_r3.py`、`collect_to_workspace.py`）→ 按 RENAME_MAP §3 token 表清零；静态门禁 residue 由 FAIL 转 PASS。

---

## 2. 实机测试结果（2026-09-28，如实）

**结论：failed（未整体通过）。** 证据：`验收/real_test_result.json`（status=failed；2026-09-28 11:48–12:05 按 `计划/TEST_PLAN.md` P0–P12 在本机 PDMS 12.1 SP4、Sample/DESIGN 项目实跑一轮）。

**实测通过的段落**：

- P0 前置（进程清场 + 三个 PDMS 配置文件与基线 SHA256 逐字节核对）；
- P1 两条路线部署（原生 `deploy_pkpm2pdms.py` 与 legacy `install.ps1`，各自先 dry-run 后 execute，清单一一对应）；
- P2 启动（本轮不再弹 Customization file error 模态框——缺陷 2 修复的直接效果）；
- P3 菜单栏同时出现「PKPM2PDMS」（原生）与「PKPM2PDMS PML」（legacy）（截图 `验收/实机截图/P3_menubar_r2.png`）；
- P5 新引擎 exe 用只读样本出宏/出报告（811 构件：柱 200/梁 598/支撑 13，板 222；G 盘前后只读核对一致；宏 GBK 无 BOM 纯 CRLF、SITE=/PKPM2PDMS、不含旧名）；
- P10 本次未创建任何元素，无删除对象（全程未执行 DELETE）；
- P11 卸载并把 PDMS 配置逐字节复原（before/after SHA256 全等），legacy 交付版 uninstall.ps1 直接跑通。

**未通过 / 未执行，及原因**：

- **P4/P9（原生窗体）**：点菜单后 addin.log 已记 `command execute` + `form opened`（命令链已通、窗体对象已构造），但窗体顶层窗口在 des.exe 里枚举不到——**未定位**，不排除本会话 .NET 显示问题。
- **P6（宏建树）**：宏在守卫行按设计中止——本机 PDMS Design 会话**加载不了任何 PML 全局函数**（连 AVEVA 自带 `!!comUnitsConvert` 也 `Variable not defined`，直证 `验收/实机日志/P2_probe_env_r2.txt` 等）。属环境阻塞，不是本包代码能就地绕过的（契约 §o 冻结这条链路）。未创建任何元素。
- **P7（导出对账）**：导出函数在本环境不可用，导出没发生，未产出导出文本（不伪造产物）。
- **P9（legacy 窗体）**：缺陷 3 修复后窗体能打开，但**控件被布局到窗体窗口之外**（子控件 x≈1054…5850，窗体仅 736 宽），按钮点不到——新发现，未修。
- **P8（重名 re）**：没有第一棵树，无从执行（不是「re 没生效」的结论）。

**含义**：转换引擎（P5）与安装/卸载（P1/P11）已实测可用；「在 PDMS 里一键建树/导出」的端到端在本机尚未走通，需先解决 PML 全局函数加载的环境问题（blockers[0]），legacy 窗体布局与原生窗体窗口两处待查（blockers[1][2]）。

静态门禁：`验收/静态回归.py` 汇总 PASSED、8/8、exit 0（`验收/static_result.json`，2026-09-28 12:05:13）——静态检查 ≠ 实机通过。

---

## 3. 与 v2.0 的差异（除改名外）

| 项 | v2.0 | v2.1.0 | 影响 |
|---|---|---|---|
| PDMSDUMP 首行 magic | `#PKPM-JWD-PDMSDUMP` | `#PKPM2PDMS-PDMSDUMP`（其后格式版本 1.0 不变） | 引擎对首行硬校验：**v2.0 生成的旧 dump 文本被 v2.1.0 引擎拒收**（迁移见 §4.1） |
| 备份后缀 | `.pkpmjwd-bak` | `.pkpm2pdms-bak` | 新版卸载脚本只认新后缀，不自动还原 v2.0 旧备份 |
| PMLLIB 子目录 / PDMS 根自有目录 | `pkpmjwd\` | `pkpm2pdms\` | 旧安装不被新版识别、清理 |
| 菜单 | 「PKPM JWD」（原生 uic Caption） | 原生「PKPM2PDMS」+ legacy「PKPM2PDMS PML」两个菜单 | 两条路线 Key 集合不相交（本次修复后），便于分辨哪条生效 |
| 安装脚本 | `deploy/undeploy_pkpmjwd.py` | `deploy/undeploy_pkpm2pdms.py` | 命令随名改 |
| 引擎环境变量 | `PKPMJWD_ENGINE` | `PKPM2PDMS_ENGINE` | 指定引擎路径的入口名变了 |
| 版本号 | v2.0 / v1 | v2.1.0 / 2.1.0.0 | 见 §1.3 |
| 转换逻辑 | — | 除 §1.4-1 宏守卫行外**未动** | 读/写/截面映射/数据库导出行为与 v2.0 一致（`验收/static_result.json` behavior_regression 段，修复已登记判据） |

---

## 4. 兼容性与迁移

### 4.1 数据 / 模型层

- **旧容器**：v2.0 建的 `/PKPM_JWD`、`/PKPM_JWD_USER`、`/PKPM_JWD_STSS` 等容器，v2.1.0 不再引用（新名 `/PKPM2PDMS*`）。本版**没有**自动迁移/改名工具；已用 v2.0 建过模型的数据库，旧容器保持原样，要归到新名下需手工处理或用新引擎重导。
- **旧 dump 文本**：v2.0 生成的 PDMSDUMP 文本首行是 `#PKPM-JWD-PDMSDUMP`，v2.1.0 引擎拒收。迁移二选一：① 用 v2.0 引擎重出；② 手工把首行改成 `#PKPM2PDMS-PDMSDUMP`（其余行不动）。本版不加自动兼容分支。
- **截面匹配文件**：《PKPM转PDMS截面匹配文件.txt》格式不变，直接沿用（仍按交付纪律不随包分发，用你自己的）。

### 4.2 安装层（已装 v2.0 的机器：先卸旧、再装新）

1. **PDMS 完全停机**（des.exe / PDMSConsole.exe / mon.exe 全退出）。
2. **用 v2.0 自带的卸载脚本卸干净**：原生 `undeploy_pkpmjwd.py`、legacy `install\uninstall.ps1`（v2.0 版）。v2.1.0 的安装/卸载脚本**识别不到**旧名安装物——`PKPMJWD.dll`、`pkpmjwd.uic`、`PMLLIB\pkpmjwd\`、`.pkpmjwd-bak`、DesignAddins.xml 里的 `<string>PKPMJWD</string>` 都不在新版的清单与移除正则里。
3. 重启 PDMS 确认菜单栏不再出现旧名菜单（v2.0 原生为「PKPM JWD」）；若两个 XML 还有残留，手工清理前先另存备份。
4. 再按 `从这里开始.txt` 第 3 条装 v2.1.0（两条路线，各自先 dry-run 看「将要改变的全部对象」再 execute），装完完全重启 PDMS。
5. **为什么不建议新旧并存**：新旧是两套 addin + 两套 PML 目录（旧名 `pkpmjwd\` 与新名 `pkpm2pdms\`），互不识别、互不清理；本交付未测试并存形态，排障时无法区分哪套生效。支持的路径只有「先卸旧、再装新」。

### 4.3 GitHub 状态（截至 2026-09-28，如实）

**v2.1.0 未发布到 GitHub。** `github.com/luckhu0204/PKPM-JWD-PDMS-Plugin`（旧名仓库）仍停在 v2.0.0（Latest release v2.0.0，2026-09-25；最后提交 f37a889d，2026-09-25——`gh release list` / `gh api repos/...` 查证）。**本目录是 v2.1.0 的唯一交付源。**

---

## 5. 文档入口

| 要看什么 | 去哪 |
|---|---|
| 安装两步 / 卸载 / 引擎 exe 位置 | `从这里开始.txt` |
| 构建产物、扫描口径、迁移要点 | `交付清单.txt` |
| 全树逐文件 SHA256 | `SHA256哈希清单.txt` |
| 三种用法谁是主、已知限制 | `插件包\docs\使用说明.md` |
| 原生 .NET 插件细节 | `PDMS原生插件\README.txt`、`插件包\docs\原生插件说明.md` |
| 改名映射完整展开 / 实机测试计划 | `计划\RENAME_MAP.md` / `计划\TEST_PLAN.md` |
| 实机结论与全部证据路径 | `验收\real_test_result.json`（static：`验收\static_result.json`） |
