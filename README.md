# PKPM2PDMS v2.1.0（PKPM ↔ AVEVA PDMS 12.1 SP4 导入导出插件）

把国产结构设计软件 PKPM 的结构模型接入 AVEVA PDMS 12.1 SP4 的插件套件，三条能力线：

| 能力线 | 说明 |
|---|---|
| **几何建模双向** | `.jwd`（PKPM 结构模型，SQLite3）与 `.pdt`（PKPM 中间模型，GBK 文本）→ PDMS Design 结构模型（SITE/ZONE/STRU/FRMW/SBFR/SCTN/PANE/STWALL）；PDMS 模型 → `.jwd` / `.pdt` 导出；两种 PKPM 格式互相转换 |
| **截面库双向（数据库层）** | PKPM 截面定义（`*Sect` 表的 Kind/ShapeVal 编码、`$DEFFRAMESECTION`）→ PDMS Catalogue + Specification 宏（STSECTION/STCATEGORY/DTSET/PTSSET/SPRFILE/SPCOMPONENT）；PDMS 目录宏（DB Output 格式）→ 反算回 PKPM 截面定义；附截面转化表 |
| **PDMS 原生插件** | .NET Add-in（C# .NET 3.5 / x86，`IAddin` + WinForms 窗体）+ PML 混写：PDMS 菜单「PKPM2PDMS」点开原生窗体，导入/导出/建库都在这个窗体里完成 |

> **v2.1.0 = 标识改名 + 版本统一 + 4 处实机缺陷修复。**
> 标识：`PKPMJWD` / `pkpmjwd` / `PKPM-JWD` → `PKPM2PDMS` / `pkpm2pdms`；SITE 与容器前缀
> `/PKPM_JWD_*` → `/PKPM2PDMS_*`。版本：插件 v2.1.0，`PKPM2PDMS.dll` 的
> `AssemblyVersion` / `FileVersion` = 2.1.0.0（`插件包/pdms-net/AssemblyInfo.cs:10-12`）。
> **契约 schema 版本 `CONTRACT_VERSION = "1.0"` 与三种格式版本（PDMSDUMP 1.0 / .pdt $VERSION 4.2.0 /
> UIC `<Version>1.0`）一律不变。**

## 主用法：PDMS 内一键导入

PDMS DESIGN 菜单栏「**PKPM2PDMS**」→「**PKPM2PDMS导入导出**」打开原生窗体。
窗体上只有一个「操作类型」下拉，**只有三项**（源码：`插件包/pdms-net/PKPM2PDMSForm.cs:106-110`）：

| 下拉项 | 引擎动作 | 说明 |
|---|---|---|
| **PKPM导入PDMS** | `auto2pdms` | **一键导入**：按文件内容自动识别 `.jwd` / `.pdt`（无需选格式）。选文件 → 点「执行」→ 引擎在临时目录生成宏（留档）→ 立即在 PDMS 内 `$M` 执行 → 窗体回显 SITE 复核与构件计数摘要 |
| **PDMS导出PDT文件** | `pdms2pdt` | 先在 PDMS 里设好 CE，再导出 `.pdt` |
| **PDMS导出JWD文件** | `pdms2jwd` | 同上，导出 `.jwd` |

其余 7 个转换方向只在引擎 CLI 里保留，不上窗体（`PKPM2PDMSForm.cs:102-105` 注释）。

### 生成期命名方案（一句话）

**导入前由 .NET 侧用 `DbElement` 直查目标库，试出未被占用的 SITE 名（`/PKPM2PDMS` → `/PKPM2PDMSre`
→ `/PKPM2PDMSre2` …），引擎在「生成宏」时就把这个名字作为全树前缀写进每一层
（中间层与构件名 = `<SITE名>_<段>`），宏内不再依赖任何运行期 PML 函数。**

- 实测：同一模型连导两次 → 第 1 次 `/PKPM2PDMSre2`、第 2 次 `/PKPM2PDMSre3`（试名次数 3 → 4），
  全树前缀跟着变；生成的宏内 27 条带名 `NEW` 全部是 `/PKPM2PDMSre<n>_*`，重名 0；
  底层元素（SCTN / PANE / PLOOP / PAVERT）无名创建。
- 改名只影响名字：几何、属性、挂接与命名规则一概不变。
- 引擎侧契约（`cli.py --help` 原文）：建模型的三条子命令 `jwd2pdms` / `pdt2pdms` / `auto2pdms`
  **必须**给 `--site-name`——"SITE 名由 .NET 侧执行前用 DbElement 直查试出可用名后传入，
  引擎不默认、不改名"（`--request` 契约里是同名的 `site_name` 键）。

## PDMS 实机测试通过（2026-09-28，多层钢结构 / 导出反导 / 零错误）

已按 `计划/TEST_PLAN.md`（P0–P12）在本机 PDMS 12.1 SP4（Sample 项目 / DESIGN 模块 / `SYSTEM` 管理员账号）
实跑完整一轮，**结论 `passed`：12 项功能全部 pass，每一步 `errors=0`**
（逐条证据：`验收/real_test_result_R7.json`）。关键实测数据：

| 步骤 | 实测结果 |
|---|---|
| 部署（两条路线，各自先 dry-run 后 execute） | 原生 28 项清单 → 24 项改动（21 PML + dll + uic + engine_path）；legacy 拷贝 21 个 PML；落盘逐字节核对 identical=21 / mismatch=0 |
| 菜单 | 菜单栏同现「PKPM2PDMS」（原生）与「PKPM2PDMS PML」（legacy） |
| 三项下拉 | 真实点击 + 键盘 DOWN/ENTER 切换，组合框读回三项文本全部验证通过 |
| 一键导入 `.jwd` | `JLCJ2.jwd` → `/PKPM2PDMSre2`：levels=5 joints=382 members=811（柱 200 / 梁 598 / 支撑 13）slabs=222 **errors=0** |
| **多层钢结构**导入 `.pdt` | `1_PM.pdt` → `/PKPM2PDMSre4`：levels=11 joints=617 members=1046（柱 121 / 梁 925）slabs=331 walls=4 loads=124 **errors=0** |
| **导出反导往返** | 导出 `export_test.pdt`（495,808 B，rows=7033）→ 反导 `/PKPM2PDMSre5`：members=1046 slabs=331 unresolved=0 **errors=0**；导出 `export_test.jwd`（860,160 B）→ 反导 `/PKPM2PDMSre6` unresolved=0 **errors=0** |
| 生成期唯一命名 | 连导两次 `re2`→`re3` 递增，宏内 27 条带名 `NEW` 全前缀化，重名 0（见上节） |
| 零窗口打扰 | 6 个窗口监视器覆盖导入/导出全程：无 tkinter / 引擎 GUI / 其它进程窗口 |

**错误面：`(47,*)` CP 语法错误 0 条、`Read only DB (2,25)` 0 条、引擎非零退出 0 次**（除一次已定位的
参数错误，见下节第 1 条）。命令窗中出现的 `(2,109) Undefined name` 是 Sample 库只装了钢规格库所致，
已逐条解释，不是宏语法或命名逻辑错误。

## 安装（两步 + 重启；务必 PDMS 完全停机）

**第一步：装原生插件（主路线，.NET）**

```bat
cd /d <本目录>\PDMS原生插件\deploy
python deploy_pkpm2pdms.py            :: 先 dry-run：打印"将要改变的全部对象"，不落盘
python deploy_pkpm2pdms.py --execute  :: 确认清单无误后真执行
```

**第二步（可选）：装 legacy PML** —— 原生窗体的「PDMS 文本导出」按钮依赖它装的 `!!pkpm2pdmsexport`；
不用导出功能可跳过这一步。

```bat
powershell -NoProfile -ExecutionPolicy Bypass -File 插件包\install\install.ps1 -DryRun
powershell -NoProfile -ExecutionPolicy Bypass -File 插件包\install\install.ps1
```

**然后：完全退出并重启 PDMS** → DESIGN 菜单栏出现上述两个菜单（名字不同，便于分辨哪条生效）。

两条路线都是「只加不删、改前备份（`.pkpm2pdms-bak`）、幂等、可回滚」。卸载：
`python undeploy_pkpm2pdms.py`（先 dry-run；XML 从备份逐字节复原，安装文件移入 `_uninstalled_<时间>\`
而不是删除）或 legacy `install\uninstall.ps1`（先 `-DryRun`）。

## 其它入口

- **免 Python 环境**：见本仓库 **Release 附件**（引擎 exe、向导安装程序 exe）；源码树内也有一份
  引擎 exe 副本供 .NET 窗体调用（`插件包/engine/dist/`，按约定不入 git）。
- **命令行**（纯 Python 标准库，13 个子命令）：`python 插件包/engine/cli.py --help`
  —— `jwd2pdms` / `pdt2pdms` / `auto2pdms` / `pdms2jwd` / `pdms2pdt` / `jwd2pdt` / `pdt2jwd` /
  `jwd2db` / `pdt2db` / `db2jwd` / `db2pdt` / `pdt2model` / `dbsections`
- **图形界面**：`python 插件包/engine/gui.py`（tkinter）
- **截面匹配文件**：用你自己的《PKPM转PDMS截面匹配文件.txt》（按交付纪律不随包分发）；
  少量占位规格名在 `插件包/engine/secmap_extra.txt` 里按自己的等级库核对替换

## 目录结构

```
├─ 插件包/                 主交付包
│  ├─ engine/             转换引擎（纯 Python 标准库）：cli.py + gui.py + 读/写/宏/数据库模块
│  ├─ pdms/               PDMS 侧 PML（GBK 无 BOM + CRLF）
│  ├─ pdms-net/           .NET 原生插件源码（C# .NET 3.5 / x86）+ build.cmd + deploy 脚本
│  ├─ install/            legacy PML 路线安装/卸载（PowerShell）
│  ├─ spec/               接口契约 CONTRACT.md（唯一契约）
│  ├─ docs/               使用说明、格式规范（JWD/PDT）、数据库转化、截面映射、原生插件说明
│  └─ test/               验收测试与检查脚本
├─ PDMS原生插件/           上面 pdms-net 的发布副本（C# 源码 + deploy + _selftest）
├─ 图标/                  pkpm2pdms.ico（多尺寸；两个 exe 与 DLL 共用的图标源）
├─ 安装程序构建/            PyInstaller 打包源码与 spec
├─ 计划/                  RENAME_MAP.md（改名映射）+ TEST_PLAN.md（实机测试计划 P0–P12）
├─ docs/                  README_v2.1.0.md（本次改动 / 与 v2.0 差异 / 兼容性与迁移）
└─ 从这里开始.txt / 交付清单.txt / SHA256哈希清单.txt
```

## 未覆盖项（如实）

1. **混凝土板/墙规格**：导入宏的 `SPREF` 行引用 `/Concrete_Slab-SPEC/T120` 等，而 Sample 的 Paragon 只装了
   钢规格库 → 报 `(2,109) Undefined name`（宏头 `ONERROR CONTINUE` 使其继续执行）。**几何在、规格无**；
   `插件包/engine/secmap_extra.txt` 里 3 条占位规格名（`Concrete_Slab-SPEC` / `Concrete_Wall-SPEC` 等）
   请按自己的等级库核对替换，并按需导入混凝土库。
2. **荷载不参与转换**（按要求不做）：`.pdt` 写出时荷载段只写段头、体内为空。
3. **未实现的 PKPM 表**：`.jwd` 在本样本工程无数据的表（墙 / 楼梯 / 次梁 / 阻尼器 / 柱帽 / 施工段等）
   未实现对应转换。
4. **未解码截面族**按「不猜」原则列为待确认：族码 19、`TRAPEZOID` / `DOUBLE_C` / `RECT`、`Kind=2`、族码 32 槽序。
5. **往返保真差异（不属本轮判据）**：导出 `/PKPM2PDMSre4`（levels=10 / walls=4）→ 反导 `.pdt` 得
   levels=10 / walls=0，反导 `.jwd` 得 levels=9 / walls=0；板 331、构件 1046 保留，**墙在往返中丢失**。
6. **会话内新建元素属未提交状态**：实机测试的 `/PKPM2PDMSre2…re6` 全在同一 PDMS 会话内，
   要落盘须**正常退出** PDMS（强制结束进程会回滚）。
7. **legacy PML 路线**本轮只验证了「菜单存在 + 部署逐字节一致」；早期轮次曾发现 legacy 窗体控件布局
   出界的问题，本次未复测；窗体的「改名统计 / 改名清单」栏目属 R6 时代遗留（生成期命名方案已不再使用运行期改名）。
8. **v2.0 → v2.1.0 迁移（没有自动迁移工具）**：旧容器 `/PKPM_JWD_*`、旧 dump 首行 magic
   `#PKPM-JWD-PDMSDUMP`、旧备份后缀 `.pkpmjwd-bak`、旧 PMLLIB 目录 `pkpmjwd\` —— 新版**一律不识别**。
   请**先用 v2.0 的卸载脚本卸干净，再装 v2.1.0**（详见 `docs/README_v2.1.0.md` §4）。
9. **交付树冻结清单的时效**：`从这里开始.txt` / `交付清单.txt` / `docs/README_v2.1.0.md` 生成于
   2026-09-28 19:57，**早于同一天 20:42–21:10 的 R7 实机轮**；其中「实机结论」一处仍写着上一轮的
   failed 与「GitHub 未发布」。实际结论以 R7 轮为准（`验收/real_test_result_R7.json`）。
   源树未改动，以保持 `SHA256哈希清单.txt` 自洽。
10. **验收工作区不随本仓库分发**：`验收/`（实机截图 `R7截图/`、导出产物 `R7导出/`、日志 `R7日志/`、
    静态回归产物）按交付纪律**不属于交付内容**，是本地验收工作区。
11. **本仓库只放源码与文档**：`*.exe` / `*.dll` / `*.zip` 等编译产物按约定不入 git 树，走 Release 附件。
12. **首次安装前**：请先跑 dry-run 核对「将要改变的全部对象」清单，并**备份 PDMS 工程数据库**。

## 数据来源与致谢

截面转化表由用户提供的《PKPM转PDMS截面匹配文件.txt》、《PKPM（PDMS数据库）.txt》（PDMS DB Output 目录宏）
与 PKPM 官方 P-TRANS 内嵌截面编码表交叉对齐生成。PDMS 侧命令写法全部引自 AVEVA PDMS 12.1 SP4
本机安装内真实代码（`sctlcrelem.pmlfnc` 等），未凭空编造语法。

## 免责声明

本插件与 PKPM、AVEVA 无隶属关系；在 PDMS 中执行导入前请先备份工程数据库。按现状提供，不附带任何担保。
