# RENAME_MAP —— PKPM-JWD → PKPM2PDMS 改名映射（v2.1.0）

- 适用工作树：`D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/`（由 v2.0 交付树 `交付_PKPM-JWD插件/` **只复制**而来）
- 编制日期：2026-09-28
- 本文所有行号均为 **本工作树内文件** 的行号（内容与 v2.0 交付树逐字节相同，见 `验收/搭树自检.txt` §4）
- 上游依据：工作流 `D:/AI_Work/PKPM数据解析/workflow/pkpm2pdms_v210.ts`（`RENAME` 常量，:73-84；`REALTEST` 常量，:86-93）

---

## §0 一句话原则与两条铁律

**改的是「插件标识」，不是「PKPM 格式名」。**

1. **只替换标识符 token，不重写语义**：不做逻辑改动、不调格式、不改函数实现。除了 §2.7 里明确列出的「必须同步改」项，任何一处改动都必须能写成「某个 token → 另一个 token」。
2. **同一 token 的所有出现点必须一起改**：尤其是跨语言的三条链——C# 的 `Command Key` ↔ `pkpmjwd.uic` 的 `<Key>` ↔ `IAddin.Name` ↔ `DesignAddins.xml` 条目；PML 函数定义 ↔ 宏生成器调用；引擎的可执行文件名 ↔ `engine_path.txt` ↔ `EngineRunner` 查找路径。任何一条链断一处，实机就会失败（见 `TEST_PLAN.md` P3/P4）。

---

## §1 新名统一约定

| 场合 | 旧 | 新 |
|---|---|---|
| 标识符（全大写） | `PKPMJWD` | `PKPM2PDMS` |
| 标识符（全小写） | `pkpmjwd` | `pkpm2pdms` |
| 连字符形态 | `PKPM-JWD` | `PKPM2PDMS` |
| 连字符 + 中文 | `PKPM-JWD导入导出` | `PKPM2PDMS导入导出` |
| 显示名（菜单/标题/文档） | 「PKPM JWD」/「PKPM-JWD」 | 「PKPM2PDMS」 |
| SITE/容器名前缀 | `/PKPM_JWD` / `/PKPM_JWD_` | `/PKPM2PDMS` / `/PKPM2PDMS_` |
| 版本号（用户可见） | v2.0 / v1 | **v2.1.0** |
| 引擎 schema 版本常量 | `CONTRACT_VERSION = "1.0"` | **保持 `"1.0"` 不变** |

---

## §2 映射表（完整展开）

### §2.1 全大写标识符 `PKPMJWD` → `PKPM2PDMS`

出现形态共 5 类，逐类列出确切位置：

**(a) C# 类型名 / 命名空间 / 程序集 / IAddin 登记名**（B 包）

| 文件 | 行 | 旧 | 新 |
|---|---|---|---|
| `插件包/pdms-net/PKPMJWDAddin.cs` | 18 | `namespace PKPMJWD` | `namespace PKPM2PDMS` |
| 同上 | 20 | `class PKPMJWDAddin : IAddin` | `class PKPM2PDMSAddin : IAddin` |
| 同上 | 24 | `return "PKPMJWD";`（`IAddin.Name`） | `return "PKPM2PDMS";` |
| 同上 | 45 | `new OpenPKPMJWDCommand()` | `new OpenPKPM2PDMSCommand()` |
| 同上 | 86 | `class OpenPKPMJWDCommand : Command` | `class OpenPKPM2PDMSCommand : Command` |
| 同上 | 88 | `private static PKPMJWDForm _form;` | `PKPM2PDMSForm` |
| 同上 | 92 | `Key = "PKPMJWD.OpenTools";` | `Key = "PKPM2PDMS.OpenTools";` |
| 同上 | 111 | `MessageBox.Show("PKPMJWD error:\n" ...)` | `"PKPM2PDMS error:..."` |
| 同上 | 118 | `_form = new PKPMJWDForm();` | `PKPM2PDMSForm` |
| `插件包/pdms-net/PKPMJWDForm.cs` | 全文 | `PKPMJWDForm`、`PKPMJWD` 字样 | 同规则 |
| `插件包/pdms-net/PKLog.cs` | 全文 | 日志前缀 `PKPMJWD` | `PKPM2PDMS` |
| `插件包/pdms-net/PmlBridge.cs` | 全文 | `PKPMJWD` | `PKPM2PDMS` |
| `插件包/pdms-net/EngineRunner.cs` | 4,7,44,45,80,81 等 | 见 §2.6(a) | — |
| `插件包/pdms-net/build.cmd` | 2, 24, 32, 39 | `PKPMJWDAddin.cs`、`PKPMJWDForm.cs`、`out:...\PKPMJWD.dll`、`BUILD OK: ...\PKPMJWD.dll` | `PKPM2PDMS*`、`PKPM2PDMS.dll` |
| `插件包/pdms-net/README.txt` | 多处 | `PKPMJWD` 14 处 / `PKPMJWDForm` 1 处 | 同规则 |

**(b) `pkpmjwd.uic` 内的 Key / 工具名 / 菜单标题**（B 包）

文件：`插件包/pdms-net/pkpmjwd.uic`（UTF-8 **无 BOM** + **LF**，实测；改后保持同样形态）

| 行 | 旧 | 新 |
|---|---|---|
| 5 | `<ButtonTool Name="PKPMJWD.Open">` | `"PKPM2PDMS.Open"` |
| 8 | `<Key>PKPMJWD.OpenTools</Key>` | `<Key>PKPM2PDMS.OpenTools</Key>` |
| 12 | `<Caption>PKPM JWD 导入导出</Caption>` | `<Caption>PKPM2PDMS导入导出</Caption>` |
| 15 | `<MenuTool Name="PKPMJWD.Menu">` | `"PKPM2PDMS.Menu"` |
| 17 | `<Caption>PKPM JWD</Caption>` | `<Caption>PKPM2PDMS</Caption>` |
| 20,26,35 | `<Tool Name="PKPMJWD.Open" />` / `"PKPMJWD.Menu"` | `PKPM2PDMS.*` |
| **3** | **`<Version>1.0</Version>`** | **不要改！** 这是 AVEVA UIC 文件格式版本，不是插件版本（见 §3.3） |

同一文件在 `插件包/pdms-net/dist/pkpmjwd.uic` 还有一份副本，逐字同步。

**(c) DesignAddins / DesignCustomization 登记串**（B 包，`deploy` 脚本内）

| 文件 | 行 | 旧 | 新 |
|---|---|---|---|
| `插件包/pdms-net/deploy/deploy_pkpmjwd.py` | 14,134,135,138 | `>PKPMJWD<` / `<string>PKPMJWD</string>` | `>PKPM2PDMS<` / `<string>PKPM2PDMS</string>` |
| 同上 | 16,141,144 | `CustomizationFile Name="PKPMJWD" Path="pkpmjwd.uic"` | `Name="PKPM2PDMS" Path="pkpm2pdms.uic"` |
| 同上 | 110,112 | `<root>\PKPMJWD\pml\pkpmjwduniquename.pmlfnc`、`<root>\PKPMJWD\engine_path.txt` | `\PKPM2PDMS\...\pkpm2pdmsuniquename.pmlfnc` |
| 同上 | 147,148 | `root / "PKPMJWD.dll"`、`root / "pkpmjwd.uic"` | `PKPM2PDMS.dll`、`pkpm2pdms.uic` |
| 同上 | 46,69 | 动作常量 `K_BACKUP` 注释里的后缀 `.pkpmjwd-bak` | `.pkpm2pdms-bak` |
| 同上 | 68 | `p.suffix + ".pkpmjwd-bak"` | `".pkpm2pdms-bak"` |
| `插件包/pdms-net/deploy/undeploy_pkpmjwd.py` | 全文 | 同上 | 同上 |
| `PDMS原生插件/deploy/deploy_pkpmjwd.py`、`undeploy_pkpmjwd.py` | 全文 | 与 `插件包/pdms-net/deploy/` 两份一致（副本） | 同上 |

> ⚠ **注意**：`.pkpmjwd-bak` 是 v2.1.0 **新备份文件的后缀名**。改后缀后，卸载脚本**只能**识别新后缀的备份；v2.0 时代留下的 `.pkpmjwd-bak` 不会被自动还原。已记入 §8 待决项 ①。

**(d) 部署脚本里的「PDMS 根下自有目录名」`PKPMJWD\`**（B 包）

`deploy_pkpmjwd.py:110,112`、`PKPMJWDAddin.cs:69-70`（`Path.Combine(PKLog.Dir(), "pml")` 的上级由 `PKLog.Dir()` 决定）、`PKLog.cs`（`PKLog.Dir()` 实现）→ 统一 `/PKPM2PDMS/`。

**(e) 测试与自检脚本内的标识符**（B 包）

`插件包/pdms-net/_selftest/audit_files.py`（13 处）、`write_static.py`（16 处）、`sandbox_test.py`（12 处）、`verify_dll.ps1`（4 处）；`PDMS原生插件/_selftest/` 同名 4 个文件。

> `write_static.py` / `verify_dll.ps1` **生成或校验** `build.cmd` 的内容，必须与 §2.1(a) 的 `build.cmd` 保持同一份字符串（`write_static.py:15,25,29` 逐行照抄 `build.cmd:5,15,18`）。

---

### §2.2 全小写标识符 `pkpmjwd` → `pkpm2pdms`

**(a) 文件名与目录名** —— 见 §2.5 完整清单。

**(b) `PKPMJWD_ENGINE` 环境变量 → `PKPM2PDMS_ENGINE`（B 包，任务书未列，必须同步改）**

实测出现点（共 20 处）：

| 文件 | 行 |
|---|---|
| `插件包/pdms-net/EngineRunner.cs` | 4, 7, 44, 45, 80（`GetEnvironmentVariable("PKPMJWD_ENGINE")`） |
| `插件包/pdms-net/PKPMJWDForm.cs` | 672（用户可见错误文案） |
| `插件包/pdms-net/README.txt` | 128 |
| `插件包/pdms-net/ENGINE_IO.md` | 36 |
| `插件包/pdms-net/deploy/deploy_pkpmjwd.py` | 201（用户可见提示） |
| `插件包/docs/原生插件说明.md` | 155 |
| `插件包/spec/CONTRACT.md` | 2024 |
| `插件包/test/_s3_cli/check_r3_engine.py` | 147（检查锚点，改 A 包侧时须与 B 包同步） |
| `PDMS原生插件/` 对应 4 个文件 | 同上 |

**(c) `%TEMP%\pkpmjwd_py312.txt`（回退包装器临时文件）**

`插件包/engine/dist/run_engine.cmd:9`：`set "PYTMP=%TEMP%\pkpmjwd_py312.txt"` → `pkpm2pdms_py312.txt`。同一文件 :16 的 `echo pkpmjwd_engine: Python not found` 也改。

**(d) `%PDMSUSER%` 缺省输出文件名**（B 包，用户可见）

| 文件 | 行 | 旧 | 新 |
|---|---|---|---|
| `插件包/pdms/pkpmjwd.pmlfrm` | 55 | `%PDMSUSER%\pkpmjwd_dump.txt` | `pkpm2pdms_dump.txt` |
| 同上 | 63 | `%PDMSUSER%/pkpmjwd_dboutput.txt` | `pkpm2pdms_dboutput.txt` |
| 同上 | 78 | 提示文字里的 `pkpmjwd_dump.txt` | 同上 |
| `插件包/docs/使用说明.md` | 105 | `%PDMSUSER%\pkpmjwd_dump.txt` | 同上 |

**(e) 引擎可执行文件名 `pkpmjwd_engine.exe` → `pkpm2pdms_engine.exe`**

出现点（A 包与 B 包交界，见 §5.D）：

| 位置 | 角色 |
|---|---|
| `插件包/engine/dist/pkpmjwd_engine.exe` | 文件本体（构建产物，改名/重建） |
| `插件包/engine/dist/run_engine.cmd` | 3,16 文案 |
| `插件包/pdms-net/EngineRunner.cs` | 63（`Path.Combine(dist, "pkpmjwd_engine.exe")`）、80-81 |
| `插件包/pdms-net/ENGINE_IO.md` | 19,47,56 |
| `插件包/pdms-net/deploy/deploy_pkpmjwd.py` | 60,92 |
| `插件包/docs/原生插件说明.md`、`插件包/docs/使用说明.md`、`插件包/docs/交付清单.md`、`插件包/engine/README.txt`、`插件包/spec/CONTRACT.md:1902,2026`、`插件包/README.txt` | 文档与说明 |
| `插件包/test/acceptance_r3.py` | 399,687-688（检查锚点） |
| `PDMS原生插件/` 对应文件 | 副本 |

**(f) 其它小写出现形态**

| 形态 | 旧 | 新 | 位置举例 |
|---|---|---|---|
| 窗体名 | `setup form !!pkpmjwd` | `!!pkpm2pdms` | `插件包/pdms/pkpmjwd.pmlfrm:30`；`pkpmjwdrun.mac:29`（`show !!pkpmjwd`） |
| 宏菜单命令 | `<Macro>show !!pkpmjwd</Macro>` | `show !!pkpm2pdms` | `插件包/install/install.ps1:142`；`安装程序构建/src/installer_core.py:47` |
| PMLLIB 子目录名 | `PMLLIB\pkpmjwd\` | `PMLLIB\pkpm2pdms\` | `install.ps1:37`（`-PackageName` 缺省）、`:74`；`uninstall.ps1:33`；`安装程序构建/src/installer_wizard.py:130` |
| 备份后缀 | `.bak_pkpmjwd_<ts>` | `.bak_pkpm2pdms_<ts>` | `install.ps1:201`；`uninstall.ps1:67,68`；`安装程序构建/src/installer_core.py:382,565,570,635` |
| 卸载后保留目录 | `PMLLIB\_removed_pkpmjwd_<ts>\` | `_removed_pkpm2pdms_<ts>` | `uninstall.ps1:116`；`安装程序构建/src/installer_wizard.py:137,434` |
| 归档/交付目录名 | `PKPM-JWD导入导出\` | `PKPM2PDMS\`（交付根即 `PKPM2PDMS_v2.1.0`） | 见 §2.3(c) |
| 临时沙箱目录 | `%TEMP%\pkpmjwd_sandbox` | 不改（一次性自测脚本，B 包可选） | `_selftest/sandbox_test.py:5` |

---

### §2.3 中文/连字符形态与 SITE 前缀

**(a) `PKPM-JWD` / `PKPM-JWD导入导出` → `PKPM2PDMS` / `PKPM2PDMS导入导出`**

共 2 253 处，集中在：文档标题与正文（`插件包/docs/*.md`、`插件包/README.txt`、`插件包/pdms/README.txt`、`插件包/engine/README.txt`）、模块 docstring（`engine/canonical.py:2`、`cli.py:2,6,8,10,2072`、`gui.py:2`、`jwd_write.py:2`、`macgen.py:2`、`pdms_dump.py:2`、`pdt_read.py:2`、`pdt_write.py:2`、`secmap.py:2`、`sectionlib.py:2`、`secmap_extra.txt:1`）、`.NET` 注释与 `build.cmd`、安装脚本与安装程序源码、顶层三清单。

> **同时改的 3 处「用户可见字符串」**（不属于格式名，属于插件标识）：
> - `engine/dbmacro.py:1031`：头注释 `A("-- PKPM-JWD dbmacro: %s  %s" % ...)` → `-- PKPM2PDMS dbmacro:`
> - `engine/macgen.py:455`：宏头注释 `-- PKPM-JWD导入导出 自动生成：...` → `PKPM2PDMS导入导出`
> - `插件包/pdms/pkpmjwduniquename.pmlfnc:207`：`$P PKPM-JWD 改名 $!i： ...` → `$P PKPM2PDMS 改名 ...`

**(b) SITE / 容器名前缀 `/PKPM_JWD` → `/PKPM2PDMS`，`/PKPM_JWD_` → `/PKPM2PDMS_`**

任务书只点了 3 个名字（`/PKPM_JWD`、`/PKPM_JWD_USER`、`/PKPM_JWD_STSS`），但**规则是前缀**，实测共 5 个插件自有容器名 + 1 个 SITE + 1 个 SPEC 缺省名，全部按前缀改：

| 文件 | 行 | 旧 | 新 | 说明 |
|---|---|---|---|---|
| `插件包/engine/macgen.py` | 76 | `SITE_NAME = "/PKPM_JWD"` | `"/PKPM2PDMS"` | 导入宏建的顶层 SITE。**P8「重名 re」验收对象就是它** |
| `插件包/engine/dbmacro.py` | 69 | `CONTRACT_PKG_PREFIX = "/PKPM_JWD_"` | `"/PKPM2PDMS_"` | 包自有前缀（安全闸判据） |
| 同上 | 93 | `catalogue_user: str = "/PKPM_JWD_USER"` | `"/PKPM2PDMS_USER"` | |
| 同上 | 94 | `catalogue_stss: str = "/PKPM_JWD_STSS"` | `"/PKPM2PDMS_STSS"` | |
| 同上 | 95 | `spec_world_user: str = "/PKPM_JWD_USER_SECTION"` | `"/PKPM2PDMS_USER_SECTION"` | |
| 同上 | 96 | `spec_world_lib: str = "/PKPM_JWD_LIB"` | `"/PKPM2PDMS_LIB"` | |
| 同上 | 700 | docstring `('/PKPM_JWD_LIB', '/SECTION_C')` | `('/PKPM2PDMS_LIB', ...)` | 仅消息用 |
| 同上 | 814 | `"/PKPM_JWD_SPEC"` | `"/PKPM2PDMS_SPEC"` | SPEC 缺省名 |
| 同上 | 27 | `本包自己的 4 个容器（``/PKPM_JWD_`` 前缀）` | `/PKPM2PDMS_` | docstring |
| `插件包/engine/cli.py` | 2063 | help「缺省 /PKPM_JWD_USER；必须带 /PKPM_JWD_ 前缀」 | `/PKPM2PDMS_USER`、`/PKPM2PDMS_` | 命令行可见 |
| 同上 | 2065 | help「缺省 /PKPM_JWD_STSS；…」 | 同上 | |
| `插件包/engine/gui.py` | 85,88,824 | 提示文案里的 `/PKPM_JWD_*` | `/PKPM2PDMS_*` | GUI 可见 |
| `插件包/spec/CONTRACT.md` | 21 处 | `/PKPM_JWD*` | `/PKPM2PDMS*` | 契约同步 |
| `插件包/docs/*.md` | 多处 | 同上 | 同上 | |
| `插件包/test/**` 脚本与夹具 | 多处 | 同上 | 同上 | A 包 |
| `插件包/test/_acc_r2_out/**`、`test/_acc_r3_out/**`、`test/_acceptance*_out/**`、`test/_rt_out/**`、`test/_s*_probes*/**`、`test/out/**` | — | 同上 | **已不在新树内**（搭树时按任务书整目录排除，共 9 个目录 / 479 文件） |
| `插件包/test/_db_out/**`（5 文件） | — | 17 | **在新树内**（未匹配任务书的排除模式，按"保留脚本与夹具"留下）。是运行产物，**扫描时排除**，见 §7 例外 6 |

**实测计数（本工作树的「改名前基线」，脚本 `baseline.py`；扫描 377 个文本文件 —— 已排除二进制扩展名，并排除 `计划\`（本步新增的文档）与 `验收\`）**

| token | 出现处数 | 涉及文件数 |
|---|---|---|
| `PKPMJWD` | 1 466 | 67 |
| `PKPM-JWD` | 1 481 | 186 |
| `pkpmjwd` | 1 729 | 100 |
| `PKPM_JWD`（含 `/PKPM_JWD` 前缀） | 16 298 | 42 |

其中 `/PKPM_JWD` 前缀共 **16 297 处 / 42 文件**，分布（前几名）：
`插件包/test/_db_out/selftest_db.mac` 16 005（**运行产物，扫描时应整目录排除**）、
`插件包/test/_db_out/from_jwd.mac` 51、`插件包/spec/CONTRACT.md` 21、
`插件包/test/_db_out/closure.json` 17、`插件包/test/_r*_*.txt` 各 13~14、
`插件包/engine/dbmacro.py` 10、`插件包/docs/数据库转化说明.md` 10、
`插件包/docs/交付报告.md` 7、`插件包/test/acceptance_r2.py` 6、
`插件包/engine/cli.py` 4、`插件包/engine/gui.py` 3、`插件包/docs/使用说明.md` 3、
`插件包/engine/macgen.py` 1 …（完整清单见该脚本输出）

> 排除 `插件包/test/_db_out/**` 这 3 个运行产物文件后，`/PKPM_JWD` 基线为 **224 处 / 39 文件** —— 这才是「应改成 0」的真实目标量。
> 改名后上表四行**都应为 0**（例外见 §7）。
> 注意 `PKPMJWD`、`pkpmjwd`、`PKPMJWD_ENGINE` 是**大小写敏感的多个 token**，都要各自扫。

**(c) 目录名 `PKPM-JWD导入导出`（工作区/交付目录）**

- 工作区里 `D:/AI_Work/PKPM数据解析/PKPM-JWD导入导出/` 是 **v2.0 的源工作目录**，不属于本次改名范围（不动）。
- 交付根目录名新树固定为 `PKPM2PDMS_v2.1.0`。
- `engine/README.txt:37,48`、`插件包/pdms-net/README.txt:3,45,89,102`、`PDMS原生插件/README.txt:3,45,89,102`、`插件包/pdms-net/ENGINE_IO.md:58-61,187-191`、`插件包/engine/dist/run_engine.cmd` 里出现的 `PKPM-JWD导入导出\...` 路径示例 → 改为 `PKPM2PDMS\...`（**示例路径**，不是真实约束）。

---

### §2.4 PML 函数与全局变量（A 包定义名 ↔ B 包定义体，必须同批改）

`!!pkpmjwd...` → `!!pkpm2pdms...`。**函数名是契约的一部分**：`spec/CONTRACT.md` 与 `engine/macgen.py` 会按名调用，漏一个就运行时报「未定义函数」——`.pmlfrm:178` 已有这条错误分支。

| 定义所在文件（B 包） | 行 | 函数/全局 | 新名 |
|---|---|---|---|
| `插件包/pdms/pkpmjwduniquename.pmlfnc` | 77 | `!!pkpmjwdUniquename(!base is STRING) is STRING` | `!!pkpm2pdmsUniquename` |
| 同上 | 161 | `!!pkpmjwdRenamesCount() is REAL` | `!!pkpm2pdmsRenamesCount` |
| 同上 | 175 | `!!pkpmjwdRenamesFailCount() is REAL` | `!!pkpm2pdmsRenamesFailCount` |
| 同上 | 195 | `!!pkpmjwdRenamesShow()` | `!!pkpm2pdmsRenamesShow` |
| 同上 | 80,83,88,92,140,151,163,166,177,181,182,197,201,206,207 | 全局数组 `!!pkpmjwdRenames` | `!!pkpm2pdmsRenames` |
| 同上 | 98,99 | 全局 `!!pkpmjwdType` | `!!pkpm2pdmsType` |
| `插件包/pdms/pkpmjwdexport.pmlfnc` | 53 | `!!pkpmjwdname(!value is STRING)` | `!!pkpm2pdmsname` |
| 同上 | 69 | `!!pkpmjwdnum(!value is REAL, !toMm is BOOLEAN)` | `!!pkpm2pdmsnum` |
| 同上 | 84 | `!!pkpmjwddesp(!element is DBREF, !toMm is BOOLEAN)` | `!!pkpm2pdmsdesp` |
| 同上 | 104 | `!!pkpmjwdgroup(!value is STRING, !token is STRING)` | `!!pkpm2pdmsgroup` |
| 同上 | 126 | `!!pkpmjwdctype(!sbname, !dE, !dN, !dU)` | `!!pkpm2pdmsctype` |
| 同上 | 169 | `!!pkpmjwdori(!dE, !dN, !dU)` | `!!pkpm2pdmsori` |
| 同上 | 205 | `!!pkpmjwdgroupof(!el is DBREF)` | `!!pkpm2pdmsgroupof` |
| 同上 | 224 | `!!pkpmjwdsctn(!el, !sbname, !toMm)` | `!!pkpm2pdmssctn` |
| 同上 | 275 | `!!pkpmjwdpane(!el, !toMm)` | `!!pkpm2pdmspane` |
| 同上 | 329 | `!!pkpmjwdstwall(!el, !toMm)` | `!!pkpm2pdmsstwall` |
| 同上 | 373 | `!!pkpmjwdexport(!scope, !outFile)` ← **文档里公开的入口** | `!!pkpm2pdmsexport` |
| 同上 | 552 | `!!pkpmjwdexportce(!outFile)` | `!!pkpm2pdmsexportce` |
| `插件包/pdms/pkpmjwddbexport.pmlfnc` | 73 | `!!pkpmjwddbdate()` | `!!pkpm2pdmsdbdate` |
| 同上 | 86 | `!!pkpmjwddbcounts(!container)` | `!!pkpm2pdmsdbcounts` |
| 同上 | 121 | `!!pkpmjwddbroots()` | `!!pkpm2pdmsdbroots()`（**只替换 `pkpmjwd`→`pkpm2pdms`，`dbroots` 的拼写不要动**） |
| 同上 | 142 | `!!pkpmjwddbinventory()` | `!!pkpm2pdmsdbinventory` |
| 同上 | 169 | `!!pkpmjwddbexportWith(!outFile, !itemsText, !options)` | `!!pkpm2pdmsdbexportWith` |
| 同上 | 274 | `!!pkpmjwddbexport(!outFile)` | `!!pkpm2pdmsdbexport` |

**任务书只点名了 3 个函数**（`!!pkpmjwdUniqueName`≡`!!pkpmjwdUniquename`、`!!pkpmjwdExport`、`!!pkpmjwdRenames`）。上表是**全部 23 个 extern 函数 + 2 个全局**——只改点名的 3 个会让窗体/宏大面积报错。

**调用点（同一批一起改）**：
- `插件包/pdms/pkpmjwd.pmlfrm`：126,127,143,144,174,178（Renames 系列）、206（export）、233（dbexport）
- `插件包/pdms/pkpmjwdrun.mac`：29（`show !!pkpmjwd`）
- `插件包/engine/macgen.py`：宏里调用 `!!pkpm2pdmsUniquename` 与 `!!pkpm2pdmsRenames*`（A 包）
- `插件包/pdms-net/PKPMJWDForm.cs`（B 包）：窗体按钮文案与调用复核
- `插件包/docs/*.md`、`插件包/pdms/README.txt`、`spec/CONTRACT.md`（文档）

**交叉核对要求**（照工作流 `pkpm4` 要求）：B 包改完必须把「函数定义名」清单交回，A 包用同一清单核对 `macgen.py` 的调用名——两边名单**逐字相同**才算过。

---

### §2.5 文件名 / 目录名改名清单（本工作树内）

| 旧路径 | 新路径 | 包 |
|---|---|---|
| `插件包/pdms/pkpmjwd.pmlfrm` | `pkpm2pdms.pmlfrm` | B |
| `插件包/pdms/pkpmjwdexport.pmlfnc` | `pkpm2pdmsexport.pmlfnc` | B |
| `插件包/pdms/pkpmjwddbexport.pmlfnc` | `pkpm2pdmsdbexport.pmlfnc` | B |
| `插件包/pdms/pkpmjwduniquename.pmlfnc` | `pkpm2pdmsuniquename.pmlfnc` | B |
| `插件包/pdms/pkpmjwdrun.mac` | `pkpm2pdmsrun.mac` | B |
| `插件包/pdms-net/PKPMJWDAddin.cs` | `PKPM2PDMSAddin.cs` | B |
| `插件包/pdms-net/PKPMJWDForm.cs` | `PKPM2PDMSForm.cs` | B |
| `插件包/pdms-net/pkpmjwd.uic` | `pkpm2pdms.uic` | B |
| `插件包/pdms-net/dist/pkpmjwd.uic` | `dist/pkpm2pdms.uic` | B |
| `插件包/pdms-net/deploy/deploy_pkpmjwd.py` | `deploy_pkpm2pdms.py` | B |
| `插件包/pdms-net/deploy/undeploy_pkpmjwd.py` | `undeploy_pkpm2pdms.py` | B |
| `插件包/pdms-net/_selftest/_sandbox_src/pkpmjwduniquename.pmlfnc` | `pkpm2pdmsuniquename.pmlfnc` | B |
| `插件包/engine/dist/pkpmjwd_engine.exe` | `pkpm2pdms_engine.exe`（重建产物） | A |
| `插件包/engine/dist/run_engine.cmd` | 文件名不改（内容改） | A |
| `插件包/test/_v3_csc_check/stub_pkpmjwd.cs` | `stub_pkpm2pdms.cs` | A |
| `插件包/test/_v3_csc_check/stub_pkpmjwd.dll` | `stub_pkpm2pdms.dll` | A |
| `PDMS原生插件/*.cs`（2 个）、`pkpmjwd.uic`、`dist/pkpmjwd.uic`、`deploy/deploy_pkpmjwd.py`、`deploy/undeploy_pkpmjwd.py`、`_selftest/_sandbox_src/pkpmjwduniquename.pmlfnc` | 同规则（B 包副本） | B |
| `插件包/engine/dist/pkpmjwd_engine.exe` 之外 | — | — |
| `安装程序构建/build_spec/PKPM-JWD_安装程序_v1.spec` | `PKPM2PDMS_安装程序_v2.1.0.spec` | C |
| `安装程序构建/build_spec/PKPM-JWD_引擎_v1.spec` | `PKPM2PDMS_引擎_v2.1.0.spec` | C |
| `PDMS原生插件/dist/PKPMJWD.dll` | **保留旧名不删**；新增 `PKPM2PDMS.dll` | B |
| `插件包/pdms-net/dist/PKPMJWD.dll` | 同上 | B |

> **故意保留的旧名**：两处 `dist/PKPMJWD.dll`（v2.0 编译产物）。用途：静态回归里做「新版 vs 旧版」对照，以及证明「旧名 DLL 确实存在过」。构建阶段产出 `PKPM2PDMS.dll` 后，**两个都要在**（不要覆盖、不要删除）。这是残留扫描里唯一允许的合法 `PKPMJWD` 命中源之一（见 §7）。

---

### §2.6 任务书未列、但必须同步改的项（本表补入——漏改会直接导致实机失败）

**(a) `PKPMJWD_ENGINE` 环境变量** → `PKPM2PDMS_ENGINE`（§2.2(b)）

`EngineRunner.cs:45` 是引擎查找链的第 1 优先级。测试脚本 `TEST_PLAN.md` P0/P5 可能用这个变量覆盖引擎入口；两边必须同名。

**(b) PDMSDUMP 文本首行 magic `#PKPM-JWD-PDMSDUMP`** → `#PKPM2PDMS-PDMSDUMP`

| 角色 | 位置 |
|---|---|
| 常量定义 | `插件包/engine/pdms_dump.py:46`（`HEADER`），格式版本 `:47 FORMAT_VERSION = '1.0'`（**不改**） |
| 写出（PML 侧） | `插件包/pdms/pkpmjwdexport.pmlfnc:431`：`!lines[!n] = '#PKPM-JWD-PDMSDUMP 1.0'` |
| 严格校验 | `插件包/engine/pdms_dump.py:408,410,412`；`插件包/engine/cli.py:916-917` 与 `1635-1636`（**硬校验，首行不符直接 InputError**） |
| 文档 | `插件包/docs/使用说明.md`、`pdms/README.txt:8`、`pkpmjwd.pmlfrm:6,47`、`cli.py:885,2091,2108`、`spec/CONTRACT.md §c` |

**为什么必须改**：它是**插件自有**的交换格式，名字里就是插件标识；读写两侧都在本交付物内，可同步改。不改则 §7 残留扫描必然命中 `PKPM-JWD`。
**兼容性代价（必须写进文档）**：v2.0 生成的旧 dump 文本新引擎会拒绝。迁移办法：用旧引擎，或把首行 `#PKPM-JWD-PDMSDUMP` 手工替换为 `#PKPM2PDMS-PDMSDUMP`（其余行不变）。**不要**为了兼容去放宽 `cli.py:916` 的校验——那属于行为改动，超出「只改名」的范围（见 §8 待决项 ②）。

**(c) `PKPM-JWD-sim`**：出现在 `PDMS原生插件/README.txt:60`、`插件包/pdms-net/README.txt:60`、`插件包/deliver/collect_r3.py:172`、`交付清单.txt:86,93`。它是 `_rootsim\` 下的**目录联接名**（v2.0 作者工作区独有）。
**实测**：本工作树 `插件包/pdms-net/_selftest/_rootsim/` 与 `PDMS原生插件/_selftest/_rootsim/` 都**只有 `build.cmd` 一个文件，无任何链接**（脚本 `links.py`，链接数 0）。→ 只需改文档里的字样，无实体要改名。

**(d) `build.cmd` 的目录匹配通配**：`build.cmd:15`、`:18`、`:5` 用 `%HERE%PKPM-JWD*` 找 `pdms-net`。改名为 `PKPM2PDMS*` 后，**只有**在目录名真的是 `PKPM2PDMS*` 时才命中。`_selftest/_rootsim/build.cmd` 是同一份内容的副本（`write_static.py` 生成），三处一起改。**风险**：如果实现者把工作树目录名换成别的（不是 `PKPM2PDMS*`），这条回退链会失效 —— 见 §8 待决项 ③。

**(e) `插件包/deliver/**`（4 个文件）与顶层三清单**：任务书的 A/B/C 三包范围**都没包含**它们，但里面确实有旧标识（`deliver/collect_r3.py`：`PKPMJWD`×5 / `PKPM-JWD`×9 / `pkpmjwd`×30；`collect_to_workspace.py`：×4 / ×12 / ×22）。本表把它们**补入 A 包**（§5.A）与「构建/文档阶段」（§5.D），避免漏改。见 §8 待决项 ④。

**(f) `插件包/install/install.ps1` 与原生插件菜单标题要区分**（照工作流 `pkpm4` 要求）

- 原生 `.NET` 菜单标题 = **`PKPM2PDMS`**（`pkpm2pdms.uic:15,17`；PDMS 菜单栏出现的就是它）
- legacy PML 菜单标题 = **`PKPM2PDMS PML`**（`install.ps1:132` 的 `<Caption>PKPM-JWD</Caption>`、`:146` 的 `<Caption>PKPM-JWD 导入导出</Caption>`）
  这是**两处不同**的新串，不能都写成 `PKPM2PDMS`，否则 `TEST_PLAN` P3 无法区分两条安装路线是否都生效。

---

## §3 不要改的（逐条 + 证据 + 为什么）

### §3.1 PKPM 自有的数据容器名与字段名（绝对不改）

| 串 | 实测出现量 | 证据 | 为什么不能改 |
|---|---|---|---|
| `PKPM_USER`、`PKPM_STSS`、`/PKPMDATA`、`PKPM_USER_SECTION`、`/PKPM_LIB` | `PKPM_STSS` **2 925 处 / 13 文件**（本工作树；其中 `engine/section_table.csv` 2 905 处、`spec/CONTRACT.md` 3、`docs/数据库转化说明.md` 3、`engine/dbmacro.py` 2） | `engine/dbmacro.py:71-74`：`FORBIDDEN_NAMES`＝「**用户既有容器名**（契约 §l.1-2）。生成物里出现即违规。」 | 这 5 个是**用户 PDMS 库里已存在的容器**，插件的安全闸专门禁止生成它们。把它们改名＝把安全闸判据一起改掉，会合成到用户数据上 |
| `/PKPM_SECTION_USER` | 1 处 | `engine/dbmacro.py:814`（user 侧 SPEC 缺省名） | 不带 `/PKPM_JWD_` 前缀，按前缀规则不属插件自有 |
| `pkpmFloor`、`pkpmSlab`、`pkpmGrid`、`pkpmJoint`、`pkpmBeamSect`、`pkpmColSeg`、`pkpmWallSeg`、`pkpmStairSeg`、`pkpmCantiSlab`、`pkpmSatTower` … 共 **86 个 `pkpm*` 表名** | `pkpm_name` **364 处 / 59 文件**（本工作树；`engine/sectionlib.py` 76、`spec/CONTRACT.md` 19、`engine/cli.py` 18、`engine/dbparse.py` 15 …）；`pkpmFloor`、`pkpmSlab`、`pkpmStdFlr`、`pkpmAxis` 各 200~380 处（v2.0 全树口径） | `插件包/docs/格式规范_JWD.md`、`engine/canonical.py`、`jwd_read.py`、`jwd_write.py`、`engine/section_table.csv` | 这些是 **PKPM 软件自己的数据表名**（导入 `.jwd` 里就长这样），改了就读不懂 PKPM 的输出、写不回 `.jwd` |
| `pkpmAxis_StdFlrID`、`pkpmBeamSeg_SectID` … 等外键列名 | 各 2 处 | `engine/jwd_write.py`（DDL 生成）与 `test/_s2_probes_20260924/_ddl_block.py` | 同上，是表结构的一部分 |
| `pkpm_sections`、`pkpm_section_DBOutput`、`pkpm_pdms_section_table`、`pkpm_pdms_section_conflicts`、`pkpm_name_known`、`pkpm_name_unique`、`pkpm_name_nonempty`、`pkpm2` | 106 / 10 / 31 / 5 / 21 / 21 / 21 / 23 处 | `engine/section_table.csv`、`section_table.meta.json`、`spec/CONTRACT.md`、`docs/转化表说明.md` | 随包转化表的**列名/文件名/版本键**，属数据结构 |

> 一句话判据：**`pkpm` + 表名/列名 ⇒ 不改；`pkpmjwd` / `PKPMJWD` / `PKPM-JWD` / `/PKPM_JWD` ⇒ 改。** 两者首 4 字母相同，纯大小写不敏感替换会误伤 —— 见 §6.2。

### §3.2 命令名、模块名、格式名（不改）

| 串 | 证据 | 为什么 |
|---|---|---|
| `.jwd` | `engine/jwd_read.py:2`、`jwd_write.py:2`；样本 `JLCJ2.jwd` | 是 PKPM 导出的**文件格式名**，与插件无关（任务书 §2.7 明确） |
| `.pdt` | `engine/pdt_read.py:2`、`pdt_write.py:2` | PKPM 中间模型格式名 |
| `jwd2pdms`、`pdt2pdms`、`jwd2db`、`pdt2db`、`db2jwd`、`db2pdt`、`pdms2jwd`、`pdt2model`、`dbsections`（共 12 个子命令） | `engine/cli.py`（`jwd2pdms` 16 处、`pdt2pdms` 16 处）；`PKPMJWDForm.cs`（各 9 / 7 处） | 子命令名描述的是**转换方向**（jwd→pdms），不是插件名。改名＝改 CLI 接口，会破坏批处理脚本与窗体↔引擎协议 |
| `jwd_read.py`、`jwd_write.py`、`pdt_read.py`、`pdt_write.py`、`pdms_dump.py` | `插件包/engine/` 目录 | 模块名描述格式，不是插件 |
| `$VERSION`、`$DESIGNPARA`、`$STORY` … 13 个 `.pdt` 段名；`engine/pdt_write.py:52` `SEGMENT_ORDER` | `pdt_write.py:17-20,52` | PKPM `.pdt` 文法的段名 |
| `VERSION_BODY = "   4.2.0"`（3 空格） | `engine/pdt_write.py:57` | PKPM `.pdt` 的版本**段体值**，不是插件版本（见 §4.4） |
| `FORMAT_VERSION = '1.0'` | `engine/pdms_dump.py:47` | PDMSDUMP 格式版本，不是插件版本 |
| 样本文件名 `JLCJ2.jwd`、`JLCJ2.pdt`、`PKPM转PDMS截面匹配文件.txt` | `G:/工作/PDMS相关/00 PDMS插件/02 实用插件/PKPM导入导出插件/`（只读） | 用户样本原件 |
| `PKPM_SECTION_USER`（无 JWD） | `engine/dbmacro.py:814` | 见 §3.1 |

### §3.3 版本号里「看起来像版本但不是插件版本」的 4 处（改了会坏）

| 位置 | 值 | 真实含义 | 处理 |
|---|---|---|---|
| `插件包/pdms-net/pkpmjwd.uic:3` | `<Version>1.0</Version>` | AVEVA UIC 文件格式版本 | **不改** |
| `插件包/engine/pdms_dump.py:47` | `FORMAT_VERSION = '1.0'` | PDMSDUMP 文本格式版本 | **不改** |
| `插件包/engine/pdt_write.py:57` | `VERSION_BODY = "   4.2.0"` | PKPM `.pdt` 的 `$VERSION` 段体 | **不改** |
| `插件包/engine/canonical.py:33` | `CONTRACT_VERSION = "1.0"` | 规范模型 schema 版本（被 `spec/CONTRACT.md` 与多个测试引用） | **不改**（任务书明确）。文档里加一句话：**「`CONTRACT_VERSION` 是规范模型 schema 版本，与插件版本 v2.1.0 是两回事，本版不动。」** |

### §3.4 内部轮次名 `R1 / R2 / R3` 与契约版本 `v1.0 / v3`

`v2.0` 是**插件版本**（要改成 v2.1.0），而 `R1/R2/R3` 是**实施轮次代号**、`契约 v3 = v1.0 + R2 + R3` 是**契约修订历史**。按工作流要求：历史性叙述可保留，但**首次出现处要注明旧称**，例如：

> 交付报告 v2.1.0（本文历史上以「PKPM-JWD导入导出 v2.0」交付，内部轮次 R1/R2/R3；契约 `spec/CONTRACT.md` v3，`CONTRACT_VERSION` 常量恒为 `"1.0"`）

需要加的「首次出现说明」位置（至少）：`插件包/docs/交付报告.md:1`、`docs/交付清单.md:1`、`docs/使用说明.md:3`、`docs/数据库转化说明.md:3`、`从这里开始.txt:2`、`插件包/README.txt:1`。

---

## §4 版本号统一清单（v2.1.0 / 2.1.0.0）

### §4.1 A 包（引擎与文档）

| 文件 | 行 | 旧串 | 新串 |
|---|---|---|---|
| `插件包/engine/cli.py` | 2072 | `description="PKPM-JWD导入导出：... （契约 v%s）" % C.CONTRACT_VERSION` | 名字改 `PKPM2PDMS导入导出`；**版本仍印 `CONTRACT_VERSION`（"1.0"）**，额外加 `--version` 或描述里补 `插件版本 2.1.0` —— 见 §8 待决项 ⑤ |
| `插件包/engine/gui.py` | 811 | `self.title("PKPM-JWD导入导出 —— 图形界面（契约 v%s）")` | `PKPM2PDMS导入导出 v2.1.0 —— 图形界面（契约 v1.0）` |
| `插件包/docs/交付报告.md` | 1 | `# 交付报告 —— PKPM-JWD导入导出 v2.0（v1.0 + R2 + R3）` | `# 交付报告 —— PKPM2PDMS导入导出 v2.1.0（…）` |
| `插件包/docs/交付清单.md` | 1 | `# 交付清单 —— PKPM-JWD导入导出 v2.0` | `… v2.1.0` |
| `插件包/docs/使用说明.md` | 3 | `> 版本：v2.0（契约 …）` | `> 版本：v2.1.0（契约 …）` |
| `插件包/README.txt` | 1 附近 | 包说明版本 | v2.1.0 |
| `插件包/test/**` 里印版本的检查脚本 | `acceptance*.py`、`check_v3_contract.py` 等 | 若断言里含 `v2.0` 需按实际改 | 逐处确认 |
| 顶层 | `从这里开始.txt:2` | `PKPM-JWD导入导出 v2.0` | `PKPM2PDMS导入导出 v2.1.0` |
| 顶层 | `从这里开始.txt:19` | `两个 v1 图形入口 exe` | `PKPM2PDMS_安装程序_v2.1.0.exe` / `PKPM2PDMS_引擎_v2.1.0.exe` |
| 顶层 | `交付清单.txt`、`SHA256哈希清单.txt` | 全树重算 + 版本改 v2.1.0 | 由构建/文档阶段重生成 |

### §4.2 B 包（C# / PML / 安装脚本）

| 文件 | 行 | 旧串 | 新串 |
|---|---|---|---|
| `插件包/pdms-net/build.cmd` | 24 | `/out:"%SRC%dist\PKPMJWD.dll"` | `/out:"%SRC%dist\PKPM2PDMS.dll"` |
| 同上 | **新增** | — | 加 `/win32icon:"<NEW>\图标\pkpm2pdms.ico"`，并在源文件列表加 `"%SRC%AssemblyInfo.cs"` |
| `插件包/pdms-net/AssemblyInfo.cs` | **新增文件** | — | `[assembly: AssemblyVersion("2.1.0.0")]`、`AssemblyFileVersion("2.1.0.0")`、`AssemblyInformationalVersion("2.1.0")`（**当前源码里没有任何版本特性**，实测 `PKPMJWDAddin.cs` 全文无 `AssemblyVersion`） |
| `插件包/pdms-net/PKPMJWDForm.cs` | 窗体标题处 | `PKPM JWD` 之类标题 | `PKPM2PDMS v2.1.0`；并加 `this.Icon = new Icon(<嵌入 ico 流>)` |
| `PDMS原生插件/` 对应 4 项 | 同上 | 同上 | 同上（副本一致） |
| `插件包/pdms-net/README.txt` | 5 附近 | `版本：R3（2026-09-25，实施包 ⑬）` | `版本：v2.1.0（2026-09-28）` |

### §4.3 C 包（图标与安装程序构建）

| 文件 | 行 | 旧串 | 新串 |
|---|---|---|---|
| `安装程序构建/src/installer_core.py` | 38 | `VERSION = "1.0"` | `VERSION = "2.1.0"` |
| 同上 | 385, 555 | `PKPM-JWD导入导出 安装程序 v%s` / `卸载程序 v%s` | `PKPM2PDMS导入导出 …` |
| `安装程序构建/src/installer_gui.py` | 23 | `APP_TITLE = "PKPM-JWD导入导出 v1 安装程序（PDMS 12.1 SP4）"` | `"PKPM2PDMS导入导出 v2.1.0 安装程序（PDMS 12.1 SP4）"` |
| 同上 | 30,31,33,114,211,259 | `PMLLIB\pkpmjwd\`、「PKPM-JWD」、`PKPM-JWD_引擎_v1.exe` | 新名 |
| `安装程序构建/src/installer_wizard.py` | 31 | `APP_TITLE = "安装 PKPM-JWD导入导出 v1"` | `"安装 PKPM2PDMS导入导出 v2.1.0"` |
| 同上 | 32 | `SUBTITLE = "PKPM ↔ AVEVA PDMS 12.1 SP4 导入导出插件"` | 保留（不含旧名）＋版本 |
| 同上 | 87, 123, 124 | `PKPM-JWD导入导出 v1`、欢迎页 | 新名 + 2.1.0 |
| 同上 | 130-132, 137, 427, 428, 434 | PMLLIB 子目录、菜单项、备份名、`$m .../pkpmjwd/pkpmjwdrun.mac` | 新名 |
| `安装程序构建/src/installer_main.py` | 2, 7, 8, 9, 22, 23 | `PKPM-JWD_安装程序_v1.exe`、`prog="PKPM-JWD_安装程序"` | 新名 + v2.1.0 |
| `安装程序构建/src/engine_launcher.py` | 2, 7, 8 | `PKPM-JWD_引擎_v1.exe` | `PKPM2PDMS_引擎_v2.1.0.exe` |
| 同上 | **新增** | — | `root.iconbitmap(...)` 加 `sys._MEIPASS` 兼容（PyInstaller onefile） |
| `安装程序构建/build_exe.py` | 21 | `INSTALLER_NAME = 'PKPM-JWD_安装程序_v1'` | `'PKPM2PDMS_安装程序_v2.1.0'` |
| 同上 | 22 | `ENGINE_NAME = 'PKPM-JWD_引擎_v1'` | `'PKPM2PDMS_引擎_v2.1.0'` |
| 同上 | 38-39 | `PyInstaller` 参数无 `--icon` | 两个 exe 都加 `'--icon', <NEW>/图标/pkpm2pdms.ico` |
| 同上 | 56-57 | `--add-data <源>assets/pdms`、`assets/docs` | 改为指向 `<NEW>/插件包/pdms`、`<NEW>/插件包/docs`（照工作流 `pkpm6`） |
| `安装程序构建/build_spec/*.spec` | 25, 48 | `name='PKPM-JWD_安装程序_v1'` / `'PKPM-JWD_引擎_v1'` | 新名（`.spec` 由 PyInstaller 重生成，手改只用于对照） |
| `安装程序构建/prepare_assets.py` | 6 | `V1 = G:\...\PKPM-JWD导入导出_v1_已验收_20260924` | 改为 `<NEW>/插件包/...`，**不要写 G 盘** |
| `安装程序构建/安装说明.txt` | 全文 | `v1`、`PKPM-JWD_*_v1.exe`、「未在真实 PDMS 装过」 | 新名 + v2.1.0；「未部署」说明改写为「实机测试由工作流完成，安装步骤见下」 |
| `安装程序构建/dist/**`、`build/**` | — | v1 产物与 PyInstaller 中间件 | **不复制**（见 §5.C） |

### §4.4 版本号的三层含义（写文档时必须统一口径）

| 名称 | 值 | 载体 | 是否改 |
|---|---|---|---|
| 插件版本 | **2.1.0** | exe 文件名、GUI/欢迎页标题、README、交付清单、Release tag、DLL AssemblyVersion `2.1.0.0` | 改 |
| 规范模型 schema 版本 | `CONTRACT_VERSION = "1.0"` | `engine/canonical.py:33`，出现在 `.jwd`/report.json 的 `contract_version` 字段 | **不改** |
| 格式版本 | PDMSDUMP `1.0`、`.pdt` `$VERSION 4.2.0`、UIC `<Version>1.0</Version>` | 格式文件内部 | **不改** |

---

## §5 三个实施包的文件范围划分（互不重叠）

**实测规模**（本工作树，`验收/搭树自检.txt` §3）：复制进来 385 个文件；`插件包` 353 + `PDMS原生插件` 29 + 顶层清单 3。

```
A 包 = 315 个文件   插件包/{engine,test,docs,spec,deliver}/** + 插件包/README.txt + 插件包/计划/**
B 包 =  67 个文件   插件包/{pdms-net,pdms,install}/** + PDMS原生插件/**
C 包 =   0 个文件   图标/**（空） + 安装程序构建/**（空）   ← 本步按任务书"另建空目录"留空，内容由 C 包自己从 安装包程序\ 复制
不可分割（不属三包） 顶层 从这里开始.txt / 交付清单.txt / SHA256哈希清单.txt  →  构建与文档阶段负责
```

### §5.A A 包：引擎 Python + 测试 + 文档 + 契约

**范围（只动这些，共 315 个文件）**

| 子树 | 文件数 | 字节 | 包含 |
|---|---|---|---|
| `插件包/engine/**` | 19 | 14,458,987 | `cli.py` `gui.py` `canonical.py` `jwd_read.py` `jwd_write.py` `pdt_read.py` `pdt_write.py` `pdms_dump.py` `macgen.py` `dbmacro.py` `dbparse.py` `secmap.py` `sectionlib.py` `secmap_extra.txt` `section_table.csv` `section_table.meta.json` `README.txt` `dist/run_engine.cmd` `dist/pkpmjwd_engine.exe` |
| `插件包/test/**` | 275 | 5,549,153 | 全部保留的脚本与夹具（`acceptance*.py`、`check_*.py`、`probe_*.py`、`pdt_*_selfcheck.py`、`fixtures`、`_db_out/`、`_s3_cli/`、`_v3_csc_check/` …） |
| `插件包/docs/**` | 12 | 297,579 | `交付报告.md` `交付清单.md` `使用说明.md` `原生插件说明.md` `截面映射说明.md` `数据库转化说明.md` `格式规范_JWD.md` `格式规范_PDT.md` `转化表说明.md` `重名处理说明.md` `推断项_Kind3圆形截面.md` `README.txt` |
| `插件包/spec/**` | 3 | 208,806 | `CONTRACT.md`（2659 行，21 处 `/PKPM_JWD`）、`README.txt`、`out/README.txt` |
| `插件包/README.txt` | 1 | 2,692 | 包总说明 |
| `插件包/计划/**` | 1 | 25,099 | `计划_JWD导入导出.md` |
| **`插件包/deliver/**`（任务书未列，本表补入）** | **4** | **116,200** | `README.txt`、`collect_r3.py`、`collect_to_workspace.py`、`copy_to_plugin.py` |

**A 包的专属职责**

1. `engine/**` 全部标识替换（§2.1 docstring、§2.2(e) 引擎名、§2.3(a)(b) SITE 前缀、§2.6(b) DUMP magic、§4.1 版本）。
2. `macgen.py` 里生成的宏对 `!!pkpm2pdmsUniquename` / `!!pkpm2pdmsRenames*` 的调用名 —— 必须与 B 包交回的函数清单**逐字一致**（§2.4）。
3. `spec/CONTRACT.md` 同步（它是接口契约，改了实现不改契约 = 文档与代码不符）。
4. `test/**` 全部脚本与夹具。
5. `engine/dist/pkpmjwd_engine.exe` 的重命名/重建：新引擎 exe 由构建阶段产出为 `pkpm2pdms_engine.exe`（见 §5.D）。
6. **不做**：`pdms/**`、`pdms-net/**`、`install/**`、`PDMS原生插件/**`（B 包）；图标与安装程序（C 包）。

### §5.B B 包：C# / PML / 安装脚本 / 原生插件副本

**范围（只动这些，共 67 个文件）**

| 子树 | 文件数 | 字节 | 包含 |
|---|---|---|---|
| `插件包/pdms-net/**` | 29 | 202,794 | `PKPMJWDAddin.cs` `PKPMJWDForm.cs` `PKLog.cs` `PmlBridge.cs` `EngineRunner.cs` `pkpmjwd.uic` `build.cmd` `README.txt` `ENGINE_IO.md` `deploy/{deploy,undeploy}_pkpmjwd.py` `dist/{PKPMJWD.dll,pkpmjwd.uic}` `_selftest/{audit_files.py,read_gbk.py,sandbox_test.py,verify_dll.ps1,write_static.py,_rootsim/build.cmd,_sandbox/**,_sandbox_src/**}` |
| `插件包/pdms/**` | 6 | 67,923 | `pkpmjwd.pmlfrm` `pkpmjwdexport.pmlfnc` `pkpmjwddbexport.pmlfnc` `pkpmjwduniquename.pmlfnc` `pkpmjwdrun.mac` `README.txt` |
| `插件包/install/**` | 3 | 26,034 | `install.ps1` `uninstall.ps1` `README.txt` |
| `PDMS原生插件/**` | 29 | 202,794 | `插件包/pdms-net/**` 的发布副本（同名同内容）+ `build.cmd` `dist/**` `deploy/**` `_selftest/**` |
| **合计** | **67** | | |

**B 包的专属职责**

1. §2.1(a)(b)(c)(e) 全部 C# 与 `.uic` 改名；§2.2(b) 环境变量；§2.4 全部 PML 函数与全局。
2. 文件名改名（§2.5 里 B 包那 13 项）。
3. `build.cmd`：输出名 → `PKPM2PDMS.dll`、加 `/win32icon:`、加 `AssemblyInfo.cs`（含 `AssemblyVersion("2.1.0.0")`）。
   **先不要图标先编一次**，确认改名后可编过；图标路径先写好，等 C 包产出 `.ico` 后由构建阶段统一编译。
4. legacy PML 菜单标题 = `PKPM2PDMS PML`（`install.ps1:132,146`），与原生 `.NET` 菜单 `PKPM2PDMS` 区分开（§2.6(f)）。
5. `PDMS原生插件/` 与 `插件包/pdms-net/` 两份**必须一致**；`PDMS原生插件/dist/PKPMJWD.dll` 旧名**保留不删**，新 `PKPM2PDMS.dll` 由构建阶段放进来。
6. **编码纪律（硬）**：`pdms/**` 的 `.pmlfrm/.pmlfnc/.mac` 与 `install/*.ps1` 是 **GBK 无 BOM + CRLF**（实测，见 `验收/搭树自检.txt` 脚注与 `RENAME_MAP §6.3`）。改完必须复测：GBK 严格解码通过、无 BOM、孤立 LF = 0。`pdms-net/*.uic` 是 **UTF-8 无 BOM + LF**，改完保持。
7. **不做**：`engine/**`、`test/**`、`docs/**`、`spec/**`（A 包）；图标与安装程序（C 包）。

### §5.C C 包：图标 + 安装程序构建工具

**起点**：`图标/`、`安装程序构建/` 在工作树里**都是空目录**（按任务书"另建空目录"，实测 0 文件）。

**要做的事**

1. **图标**：写**可复现**的 `图标/make_icon.py`（Pillow 12.3.0 已装），产出
   - `图标/pkpm2pdms.ico`（多尺寸 16/24/32/48/64/128/256）
   - `图标/pkpm2pdms_256.png`、`图标/小尺寸预览.png`（16/24/32/48/64 并排放大）
   设计：深蓝渐变底 + 白色门式刚架 + 白色右箭头；线宽 ≥ 图标边长 8%，保证 16px 可辨。
2. **安装程序构建**：从 `D:/AI_Work/PKPM数据解析/安装包程序/` **复制到** `安装程序构建/`（**不动原目录**），只复制源码与工具，**不复制**：
   - `build/**`（PyInstaller 中间件，≈28 MB，含 `*.toc`/`*.pkg`/`*.pyc`）
   - `dist/**`（v1 exe 与 4 个 `.备份_*`，≈79 MB）
   - `**/__pycache__/**`、`*.pyc`
   - `_build_log.txt`、`_dbg_*.py`、`_exe_result.txt`、`_sandbox_result.txt`（一次性调试产物 —— 若要留作历史，放进 `安装程序构建/_历史调试/`，不散在根）
   要复制的：`src/**`（5 个 .py）、`build_exe.py`、`deliver_exe.py`、`prepare_assets.py`、`test_exe.py`、`test_sandbox.py`、`安装说明.txt`、`build_spec/**`（2 个 `.spec`）。
   > 源目录 83 文件 / 122,434,788 字节；按上面规则应复制 ≈14 个文件 / ≈150 KB。
3. 在副本内改造：§4.3 全部版本与名称；`build_exe.py` 加 `--icon`、改 `--add-data` 指向新树；`engine_launcher.py` 引擎名；`installer_*` 的标题/欢迎页/完成页；`root.iconbitmap` 的 `sys._MEIPASS` 兼容。
4. 产出（由构建阶段执行）：`安装程序/PKPM2PDMS_安装程序_v2.1.0.exe`、`安装程序/PKPM2PDMS_引擎_v2.1.0.exe`。
5. **不做**：`插件包/**`、`PDMS原生插件/**`。

### §5.D 交界处与三包之外的归属（最容易漏的地方）

| 事项 | 归属 | 理由 |
|---|---|---|
| `插件包/engine/dist/pkpm2pdms_engine.exe` 的**产出** | 构建阶段（A 包只改 `run_engine.cmd` 与文档里的名字） | exe 是 PyInstaller 产物，必须在新名源码上重建 |
| `插件包/pdms-net/dist/PKPM2PDMS.dll`、`PDMS原生插件/dist/PKPM2PDMS.dll` 的**产出** | 构建阶段（B 包负责 `build.cmd` 配方） | 同上 |
| `插件包/pdms-net/build.cmd` 的 `/win32icon:` 路径 | B 包写路径，C 包产出图标 | 顺序：C 产出 ico → B/构建 编译 |
| `engine/` 与 `pdms/` 的**函数名一致性** | A 包（调用方）与 B 包（定义方）**交叉核对** | §2.4 末段 |
| `test/_s3_cli/check_r3_engine.py:147` 里的锚点 `PKPMJWD_ENGINE` / `pkpmjwd_engine.exe` | A 包（在 `test/**` 内），但必须等于 B 包改后的串 | 交叉核对 |
| 顶层 `从这里开始.txt`、`交付清单.txt`、`SHA256哈希清单.txt` | **构建 + 文档阶段**（不属 A/B/C） | 三清单要重算全树 SHA256、写新版本与 GitHub 链接 |
| `插件包/docs/交付清单.md` 与顶层 `交付清单.txt` 的一致性 | A 包改 md；文档阶段改 txt | 两者内容需对齐，改完互查 |
| `图标/**`、`验收/**`、`计划/**` | 不入 A/B/C 的改名范围（`计划/**` 是本次新写的两份文档） | — |

---

## §6 操作纪律与推荐做法

### §6.1 三条硬红线（用户 2026-09-21 永久红线）

1. **只新增或覆盖文件，不删除任何文件**（唯一例外：实机测试里按**确切名字**删 PDMS 内本次创建的测试元素）。
2. **禁止任何形式的批量删除**：不用通配符/循环决定删除对象；确需删除时先"移动"到明确命名的备份目录并报告。
3. **G 盘只读**：`G:/工作/PDMS相关/00 PDMS插件/02 实用插件/PKPM导入导出插件` 下任何文件都不改（样本只读）。

### §6.2 替换手法（**推荐：显式 token 列表 + 大小写敏感**）

不要用「大小写不敏感的 `pkpmjwd` → `pkpm2pdms`」一把梭——因为 `PKPMJWD` 与 `PKPM2PDMS` 都是大写、而 `pkpmFloor`/`pkpmSlab` 与 `pkpmjwd` 前缀相同（§3.1）。**按最长的 token 先替换**，顺序如下（每个都大小写敏感）：

```
1. PKPMJWDAddin        → PKPM2PDMSAddin
2. PKPMJWDForm         → PKPM2PDMSForm
3. PKPMJWD_ENGINE      → PKPM2PDMS_ENGINE
4. PKPM-JWD导入导出     → PKPM2PDMS导入导出
5. PKPM-JWD-PDMSDUMP   → PKPM2PDMS-PDMSDUMP
6. PKPM-JWD            → PKPM2PDMS
7. PKPMJWD             → PKPM2PDMS
8. /PKPM_JWD           → /PKPM2PDMS          （含 /PKPM_JWD_ → /PKPM2PDMS_）
9. pkpmjwd             → pkpm2pdms
```

> `PKPMJWD`（7）必须在 `pkpmjwd`（9）**之前**执行，否则第 9 步会把已改好的大写串再匹配一次（`PKPM2PDMS` 里不含 `pkpmjwd`，其实安全；但反过来，先做 9 会把 `PKPMJWD` 的大小写变体混掉）。用大小写敏感替换时 7/9 互不影响，顺序只为可复现。

**替换前必须**：
- `git`/文件级备份：本项目**不是 git 仓库**；覆盖前对将改文件先复制成 `<同名>.bak_v20_20260928`（同目录或 `验收/改名前快照/`），
- 打印「将要改变的全部对象」完整清单（逐条绝对路径），核对后再执行。

**逐文件确认编码**（本机实测，供改完回验）：

| 目录 | 编码 / 换行 |
|---|---|
| `插件包/engine/**`（`.py`） | UTF-8 无 BOM + LF |
| `插件包/engine/secmap_extra.txt` | **GBK** 无 BOM + CRLF |
| `插件包/engine/section_table.csv` | UTF-8 **带 BOM** + CRLF |
| `插件包/pdms/**`（`.pmlfrm/.pmlfnc/.mac`） | **GBK** 无 BOM + CRLF |
| `插件包/install/*.ps1` | **GBK** 无 BOM + CRLF |
| `插件包/pdms-net/*.uic`、`dist/*.uic` | UTF-8 无 BOM + LF |
| `插件包/pdms-net/*.cs`、`build.cmd`、`deploy/*.py`、`_selftest/*` | UTF-8（`build.cmd` 为 CRLF；`.cs`/`.py` 为 LF） |
| `PDMS原生插件/**` | 同上（4 个文件是 UTF-8 **带 BOM** + CRLF：`_selftest/_sandbox/DesignAddins.xml`、`DesignCustomization.xml` 及其 `.pkpmjwd-bak`） |
| 顶层三清单 | UTF-8 **带 BOM** + CRLF |
| `插件包/test/build_section_table.py` | UTF-8 **带 BOM** + LF |

> 判据（照 `install.ps1:76-104` 的既有实现）：**PDMS 侧产物**改完必须 `GBK 严格往返一致 + 无 BOM + 孤立 LF = 0`。`.uic`/`.xml` **保持原形态**：本来带 BOM 的仍带 BOM，本来不带的仍不带。

### §6.3 改名后必须跑的确定性检查（每包自查 + 构建阶段统一）

```bash
# 1) 语法/编译
python -m py_compile <全部改过的 .py>                      # 逐个列出，不用通配删除
C:/Windows/Microsoft.NET/Framework/v3.5/csc.exe /nologo /target:library /platform:x86 \
  /out:<NEW>/验收/_ren_PKPM2PDMS.dll <build.cmd 里的同一批引用与源文件>   # 退出码 0

# 2) 编码
python <检查脚本>：对 插件包/pdms/** 与 插件包/install/** 断言 GBK 严格解码 + 无 BOM + 孤立 LF=0

# 3) 残留扫描（只读，逐文件列出，不做任何删除）
#    对 <NEW> 全树扫描 PKPMJWD / pkpmjwd / PKPM-JWD / /PKPM_JWD
#    期望命中 = 0；例外只有 §7 列出的那些
```

---

## §7 残留扫描与允许的例外

**做成 0 命中的判据**：`<NEW>` 全树（排除二进制：`*.exe`/`*.dll`/`*.ico`/`*.png`/`.jwd`/`.pdt`；**并排除** `插件包/test/_db_out/**` 这一类运行产物目录）扫描 `PKPMJWD|pkpmjwd|PKPM-JWD|PKPM_JWD` → **0 命中**。

**扫描范围声明（先写清再扫，否则数字没有可比性）**

- 改名前基线（§2.3(b) 表）：扫 380 个文本文件，四类 token 合计 21 294 处。
- **必须排除**：`插件包/test/_db_out/**`（`selftest_db.mac` 一个文件就有 16 005 处 `/PKPM_JWD`，是 v2.0 的生成产物，不是要改的源码/文档）。
- 排除后基线 ≈ **322 处 `/PKPM_JWD` / 43 个文件**（其余三类 token 的排除量很小）。
- 若把 `_db_out/` 也算进去，扫描**永远不可能到 0**，会掩盖真实漏改。

**允许且必须逐条解释的例外**（预期只有这些）：

| # | 位置 | 命中内容 | 为什么允许 |
|---|---|---|---|
| 1 | `插件包/pdms-net/dist/PKPMJWD.dll`、`PDMS原生插件/dist/PKPMJWD.dll` | 文件名 + 文件**内**嵌入的 `PKPMJWD`/`PKPMJWDAddin`/`PKPMJWDForm` 元数据（实测二进制里各 5/1/1 处） | v2.0 编译产物，**故意保留**（回归对照 + 证明旧名存在过）。属二进制，不参与文本扫描 |
| 2 | `插件包/test/_v3_csc_check/_baseline/g_plugin.json` | `PKPM-JWD` 713 处、`pkpmjwd` 48 处 | 这是 **G 盘插件目录的只读基线快照**（扫描 `G:\工作\...\PKPM导入导出插件` 的 751 个条目），记录的是 G 盘**现状**（含 R1 时代旧副本）。改了就不再是基线，会与本次"G 盘零变化"核对冲突 |
| 3 | `插件包/test/_v3_csc_check/_baseline/aveva_root.json` | 若含旧名同理 | 同上（AVEVA 根目录基线） |
| 4 | `插件包/test/_s2_probes_20260924/_sandbox/**` | 大量旧名（沙箱里的 `pkpmjwd.pmlfrm` 等） | **已不在新树内**（搭树时整目录排除）。若实现者另建沙箱，同样排除在外 |
| 5 | 文档里的**历史性叙述** | 「历史上以 PKPM-JWD导入导出 v2.0 交付」「v2.0 时代的 `/PKPM_JWD` SITE」 | §3.4 要求保留并注明旧称；这类命中要在扫描报告里逐条列出，说明是"刻意保留的历史说明" |
| 6 | `插件包/test/_db_out/**`（5 文件） | 16 073 处 `/PKPM_JWD`（`selftest_db.mac` 16 005 + `from_jwd.mac` 51 + `closure.json` 17） | **v2.0 的运行产物**（数据库宏/闭包报告），不是交付源码或文档。**扫描时应整目录排除**；是否改属产品决定（`RENAME_MAP §8 待决项 ⑨` 已记录） |

> 若出现上表以外的命中，就是**漏改**，必须补改，不得当作例外。

**扫描建议命令**（只读；逐文件打印，不用通配删除）：

```bash
python <扫描脚本> "<NEW>" PKPMJWD pkpmjwd PKPM-JWD PKPM_JWD
# 输出形如：<相对路径>:<行号>:[<编码>] <该行内容>
```

---

## §8 需人工确认的点（逐条：位置 / 风险 / 建议）

**① 旧备份后缀 `.pkpmjwd-bak` 与旧 PMLLIB 目录 `pkpmjwd` 的迁移**
位置：`deploy_pkpmjwd.py:68`（备份后缀）、`PKPMJWDAddin.cs:69`（`<PDMS根>\PKPMJWD\pml\...`）、`install.ps1:37,116`。
风险：改了后缀后，**v2.0 时代已装在 PDMS 里的 `.pkpmjwd-bak` 备份、`PKPMJWD\` 目录、`PMLLIB\pkpmjwd\` 目录不会被新版识别**。若用户机器上已装 v2.0，会同时存在新旧两套 → 菜单出现两份、卸载只清新的。
建议（推荐）：**先卸旧再装新**，并在 `docs/README_v2.1.0.md` 与 `从这里开始.txt` 里写清迁移步骤：先用 v2.0 的 `undeploy_pkpmjwd.py` / `uninstall.ps1` 卸载（它们认得旧后缀），再装 v2.1.0。**不在代码里为旧后缀加兼容分支**（那属于行为改动）。本次实机环境（Sample 项目）**从未装过 v2.0**（v2.0 交付报告自述"本包未部署、未启动过 PDMS"），所以实机测试不受影响。

**② PDMSDUMP 首行 magic 的向后兼容**
位置：`engine/pdms_dump.py:46,410`、`engine/cli.py:916,1635`。
风险：v2.0 生成的 dump 文本新引擎**拒绝读取**（硬校验）。
建议（推荐）：**按 §2.6(b) 改**，并在文档写明兼容影响与手工迁移办法。若要求"能读旧 dump"，那是**功能增量**（放宽校验为接受两个 magic），超出"只改名"，需要产品决定后单独做——本表不排入。

**③ `build.cmd` 的 `PKPM-JWD*` 目录通配**
位置：`build.cmd:5,15,18`（及 `_rootsim/build.cmd`、`write_static.py:15,25,29` 的副本）。
风险：它靠「目录名以 `PKPM-JWD` 开头」在暂存区里找回 `pdms-net`。改成 `PKPM2PDMS*` 后，只有目录名确实以 `PKPM2PDMS` 开头才命中。
建议（推荐）：改成 `PKPM2PDMS*`；同时**把工作树目录名保持为 `PKPM2PDMS_v2.1.0`**（以 `PKPM2PDMS` 开头）→ 通配仍然命中。若你打算把交付根改成别的名字，请在此处同步调整。

**④ `插件包/deliver/**` 与顶层三清单的归属**
位置：`插件包/deliver/collect_r3.py`、`collect_to_workspace.py`、`copy_to_plugin.py`、`deliver/README.txt`；顶层 `从这里开始.txt`/`交付清单.txt`/`SHA256哈希清单.txt`。
风险：任务书的 A/B/C 三包**都没包含**它们；不改则残留扫描不达 0。
建议（推荐）：`deliver/**` **补入 A 包**（本表已补，见 §5.A）；顶层三清单归**构建/文档阶段**（要重算 SHA256、写 v2.1.0 与 GitHub 链接，改名包做不了）。**若三包实现者都严格只动自己范围内的文件，请把这条显式传达给构建阶段。**

**⑤ 引擎的「插件版本」怎么在 CLI/GUI 暴露**
位置：`engine/cli.py:2072`、`engine/gui.py:811`。
风险：现在两者印的是 `CONTRACT_VERSION`（"1.0"）。按任务书它必须保持不变，那么运行时就看不到 2.1.0。
建议（推荐）：`cli.py` 的描述里追加一段固定文本「插件版本 2.1.0」，或加 `--version` 参数印 `PKPM2PDMS v2.1.0（契约模型版本 1.0）`；`gui.py` 标题改为 `PKPM2PDMS导入导出 v2.1.0 —— 图形界面（契约 v1.0）`。**不要**把 `CONTRACT_VERSION` 本身改成 2.1.0。

**⑥ `install.ps1` 的两个 `<Caption>` 与 `.NET` 菜单是否为"同一份菜单"**
位置：`install.ps1:132,146`（legacy PML）、`pkpm2pdms.uic:12,17`（原生 .NET）。
说明：两条安装路线各自注入一个菜单项，是**两个**菜单。按工作流要求：原生 = `PKPM2PDMS`，legacy = `PKPM2PDMS PML`。
建议（推荐）：照此改；`TEST_PLAN` P3 的判据就是「两个菜单名都出现」。

**⑦ `插件包/engine/dist/run_engine.cmd` 的文件名**
说明：任务书只点了 `pkpmjwd_engine.exe`→`pkpm2pdms_engine.exe`，没点 `run_engine.cmd`。
建议（推荐）：**文件名不改**（改名会让 `EngineRunner.cs` 的回退查找、`deploy` 脚本的 `resolve_engine_entry`、多个测试锚点同时要改，收益为零）；只改其**内容**里的引擎名与临时文件名（§2.2(c)）。

**⑧ `插件包/test/_acc_*` 等历史日志是否改写**
说明：搭树时**整目录**排除的 9 个运行产物目录（`out/`、`_acc_r2_out/`、`_acc_r3_out/`、`_acceptance_out/`、`_acceptance_r2_out/`、`_rt_out/`、`_s2_probes_20260924/`、`_s10_probes/`、`_s12_probes/`，共 479 文件 / 144,467,666 字节）已不在新树。但 `插件包/test/` **根下**仍有大量 `_acc_*.txt`、`_r2_*`、`_r3_*`、`_r4_*`、`_r5_*`、`_dbg_*`、`_nav*`、`_v2_*` 等**历史运行日志**（未匹配任务书的排除模式，故保留）。
风险：改写它们会让「v2.0 时代的原始输出」不再是原始记录。
建议（推荐）：**照工作流 A 包的要求一律替换**（A 包范围写明「.py/.md/.txt/.json/.cmd/.mac 等」全替换，残留扫描要求 0 命中）；若你更看重"历史日志逐字节可溯"，则改成冻结它们并在扫描里列为例外——**两者只能选一**，请产品决定。本表按工作流默认取「一律替换」。

**⑨ 未匹配排除模式但仍保留的运行产物目录**
位置：`插件包/test/_db_out/`（5 文件 / 2,948,757 字节，含 2.8 MB 的 `selftest_db.mac` 与夹具 `fixture_gbk.txt`）、`_s3_cli/`（13 文件 / 95,666 字节，脚本）、`_v3_csc_check/`（6 文件 / 255,606 字节，含 `_baseline/*.json` 夹具）、`spec/out/`（1 文件 README）。
说明：任务书的排除模式只覆盖 9 个目录名，这些不在内。
建议（推荐）：**保留**（按"保留 test 下的脚本与夹具"），但要知悉：`_db_out/` 里的 `/PKPM_JWD` 有 **16 073 处**（`selftest_db.mac` 16 005 + `from_jwd.mac` 51 + `closure.json` 17），会让残留扫描多出上万处命中 —— 它是**运行产物**，扫描时应整目录排除（§7 例外 6）。若希望新树更干净，可把 `_db_out/` 也排除（那属于**再复制一次**的操作，不能在目标树里删）。

**⑩ 交付根目录名 vs 顶层文档里的路径示例**
说明：多处文档示例写 `PKPM-JWD导入导出\engine\cli.py`。改名后这些示例会指向不存在的路径。
建议（推荐）：统一改为 `PKPM2PDMS_v2.1.0\...`（**用实际工作树名**），而不是笼统的 `PKPM2PDMS\`，免得读者照抄时找不到。§2.3(c) 列了出现点。

---

## §9 附：本文引用到的核查脚本（本会话临时目录，可复跑）

| 脚本 | 作用 |
|---|---|
| `C:/Users/Administrator/AppData/Local/Temp/pkpm_tools/build_tree.py` | 搭树（`--dry` 只打印 COPY 计划；只新增/覆盖，不删除） |
| `.../selfcheck.py` | 生成 `验收/搭树自检.txt`（统计、排除清单、两层目录树、逐文件 SHA256 比对、抽查） |
| `.../census.py` | 全树 `pkpm*` token 普查（用于 §2.3 与 §3.1 的计数） |
| `.../baseline.py` | 改名前基线：四类旧名 token 的处数/文件数，以及 `/PKPM_JWD` 的逐文件分布（§2.3(b) 与 §7 的数字来源） |
| `.../cnt1.py` | 单个 token 的逐文件计数（`PKPM_STSS`、`pkpm_name`） |
| `.../g.py` | 递归 regex 打印 `相对路径:行号:[编码] 行内容`（本文多数行号证据的来源） |
| `.../scan_tokens.py` | 每文件 token 计数 + 编码/换行统计（§6.2 编码表的来源） |
| `.../bom.py` | 列出带 UTF-8 BOM 的文件 |
| `.../links.py` | 检查链接/联接与 `_rootsim` 内容 |
| `.../reconcile.py` | 复制数量核对（`832 − 479 = 353` 等） |
