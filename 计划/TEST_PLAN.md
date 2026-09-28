# TEST_PLAN —— PKPM2PDMS v2.1.0 实机测试计划（P0–P12）

- 被测对象：`PKPM2PDMS v2.1.0`，工作树 `D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/`
- 编制日期：2026-09-28
- 本计划分两段执行：**第 1 段 = P0–P4**（前置 → 部署 → 启动 → 菜单 → 原生窗体）；**第 2 段 = P5–P12**（端到端 → 重名 re → 清理 → 卸载 → 恢复校验 → 汇总）。第 2 段**接着第 1 段的同一个 PDMS 会话**做，中途不重启。
- 配套文档：`计划/RENAME_MAP.md`（改名映射与实施划分）

---

## §0 纪律（与 RENAME_MAP §6.1 同源，每一步都适用）

1. **只新增或覆盖文件，不删除任何文件。唯一例外**：P10 里删除**本次实机测试自己创建在 PDMS 数据库里的测试元素**，且只能用**确切名字逐个**删除；删不动就保留并如实记录，**不要**尝试通配或强制手段。
2. **不使用通配符/循环删除**，任何不可逆操作前先把「将要改变的全部对象」逐条打印出来核对。
3. **G 盘只读**：`G:/工作/PDMS相关/00 PDMS插件/02 实用插件/PKPM导入导出插件` 下任何文件不改动（样本只读；引擎只**读**它）。
4. **结论必须有证据**：截图/日志/导出文本的路径必须真实存在；失败就写失败，不许把没做的写成做了。
5. **动手前先读** `C:/Users/Administrator/.zcode/skills/pdms-plugin-gui-test/SKILL.md` **全文**（DPI 虚拟化陷阱、点击/输入方式、截图方式、模态框堵队列等）。坐标**不要照抄**文档里的旧数字，按当前屏幕实测定位。

---

## §1 实机测试环境事实（**逐字抄录**，来源：`D:/AI_Work/PKPM数据解析/workflow/pkpm2pdms_v210.ts:86-93`，变量已按其定义 `PDMSROOT`、`GUISCR` 展开）

**实机测试环境事实**：
- PDMS 根：`D:/AVEVA/Plant/PDMS12.1.SP4`（可写，管理员）；测试项目 **Sample**（`D:/AVEVA/Plant/Projects12.1.SP4/Sample`），登录 SAMPLE/SAMPLE，MDB /SAMPLE，模块 Design。
- 启动批处理（一行式）：`D:/AVEVA/Plant/PDMS12.1.SP4/pdms.bat Sample SAMPLE/SAMPLE /SAMPLE Design`；放到 `C:/TEMP/p2p_tty/start_sample.bat` 后分离启动。
- GUI 脚本目录：`C:/Users/Administrator/.zcode/skills/pdms-plugin-gui-test/scripts`（`find_cmdedit.ps1` 找命令窗输入框、`con_bridge2.ps1` 注入命令、`find_float.ps1` 找/置前悬浮窗、`capture_wins.ps1`/`cap_dialog.ps1` 截图、`dismiss_error.ps1` 点掉 (2,779) 模态框）。
- **动手前必须先读** `C:/Users/Administrator/.zcode/skills/pdms-plugin-gui-test/SKILL.md` 全文（DPI 虚拟化陷阱、点击/输入方式、截图方式、模态框堵队列等）。坐标不要照抄文档里的旧数字，按当前屏幕实测定位。
- PDMS 启动约 90~120 秒才登录完，耐心轮询。

---

## §2 环境事实的实测核对（2026-09-28 本机只读核查 —— 与上面那段的差异在这里）

> 本节是**本会话实测**结果，目的是让执行员不要照着不存在的脚本走。凡与 §1 冲突处，以本节为准。

| 事实 | §1 的说法 | 实测结果 | 处理 |
|---|---|---|---|
| PDMS 根三件配置 | — | `D:/AVEVA/Plant/PDMS12.1.SP4/` 下 **存在** `DesignAddins.xml`（1,140 B）、`DesignCustomization.xml`（688 B）、`design.uic`（6,008 B）、`pdms.bat`（6,390 B） | P0 备份对象确认可用 |
| 命令窗桥 `con_bridge2.ps1` | 在 `.../pdms-plugin-gui-test/scripts` | **该目录下不存在此文件**。目录实测只有 7 项：`capture_wins.ps1`、`cap_dialog.ps1`、`dismiss_error.ps1`、`find_cmdedit.ps1`、`find_float.ps1`、`start_sample_design.bat`、`start_tty.bat`。但 `SKILL.md` 的工具表（:28）**确实把它列为 `scripts/` 下的脚本** | **P6 前必须先把 `find_cmdedit.ps1` 拿到句柄，然后按 `SKILL.md:52-54` 的“建立命令通道”做法注入**；若现场缺注入器，就按 `SKILL.md:76` 的提示（`EM_SETSEL`+`WM_CLEAR` 清空 + 重发）就地写一个最小注入脚本，落盘到 `验收/实机日志/`，并在 `real_test_result.json` 里注明“注入器为现场自建” |
| `stop-pdms.ps1` / `start-pdms.ps1` | §1 未提；`SKILL.md:33` 说在另一个 skill | **存在**于 `C:/Users/Administrator/.zcode/skills/pdms-install-restart-refresh/scripts/`（`stop-pdms.ps1`、`start-pdms.ps1`、`install-toolkit.ps1`、`verify-install.ps1`） | P0/P11 用这个路径 |
| `C:/TEMP/p2p_tty/` | 用来放 `start_sample.bat` | **尚不存在**（`C:/TEMP/rv_tty/` 也不存在） | P2 先 `New-Item -ItemType Directory` 建目录，再放 bat |
| 桌面同款启动批处理 | — | `.../pdms-plugin-gui-test/scripts/start_sample_design.bat` **存在**，内容就是 §1 那条一行式 | 可对照复制 |
| 屏幕与窗口尺寸 | §1 未提 | `SKILL.md:95` 记录本机屏幕 **3840×2160**，固定布局：**PDMS 主窗 `(0,0) 2400×1400`；插件窗 `(2400,20) 705×1440`**（2026-09-22 实测可用）；`SKILL.md:50` 另有一套较早的 `1640×1380` | P2/P3/P4 按 **2400×1400** 缩窗，**坐标仍现场实测** |
| 启动等待 | §1 说 90~120 s | `SKILL.md:49` 流程写 `sleep 85s` | 同量级，耐心轮询到登录完成再截屏 |
| PDMS 主安装盘 | §1 未提 | `SKILL.md:44`：主安装盘是 **D:**；`C:/AVEVA` 是空壳，勿用 | 引擎与 deploy 脚本的 `DEFAULT_ROOT` 都是 `D:\AVEVA\Plant\PDMS12.1.SP4`，一致 |
| 管理员打包/`--onefile` 图标 | — | 两个 exe 由 C 包带 `--icon` 构建 | P5 用文件名确认版本 |

**被测产物（P1/P5 要用，构建阶段产出的确切路径）**

| 产物 | 路径 | 本计划里的用途 |
|---|---|---|
| 原生插件部署脚本 | `插件包/pdms-net/deploy/deploy_pkpm2pdms.py` / `undeploy_pkpm2pdms.py` | P1 / P11 |
| 原生插件窗体源码 | `插件包/pdms-net/PKPM2PDMSForm.cs` | P4 控件核对 |
| legacy 安装脚本 | `插件包/install/install.ps1` / `uninstall.ps1` | P1 / P11 |
| legacy PML 包 | `插件包/pdms/pkpm2pdms.pmlfrm`、`pkpm2pdmsexport.pmlfnc`、`pkpm2pdmsdbexport.pmlfnc`、`pkpm2pdmsrun.mac` | P1 复制内容 / P7 导出 |
| 引擎 exe | `安装程序/PKPM2PDMS_引擎_v2.1.0.exe` | P5 出宏 |
| 引擎（源码/独立 exe 副本） | `插件包/engine/dist/pkpm2pdms_engine.exe` | P1 的 `engine_path.txt` 指向它 |
| 安装程序 exe | `安装程序/PKPM2PDMS_安装程序_v2.1.0.exe` | 可选路线（本次以 `install.ps1` 为准） |
| 只读样本 | `G:/工作/PDMS相关/00 PDMS插件/02 实用插件/PKPM导入导出插件/JLCJ2.jwd`、`.../PKPM转PDMS截面匹配文件.txt` | P5 |

---

## §3 证据目录规范（先建目录，后面每步往里放）

```
验收/
├─ 备份_PDMS配置/     P0 的三个 XML/uic 原件副本 + SHA256_before.txt
├─ 实机截图/          P2/P3/P4/P6/P7/P9 的屏幕与窗口截图（PNG）
├─ 实机日志/          P1/P2/P5/P6/P7/P9/P11 的命令输出与 PDMS 回显
├─ rt_phase1.json     P0–P4 结果
├─ rt_model.mac       P5 生成的导入宏
├─ rt_model.report.json  P5 的报告（构件计数）
├─ rt_export_1.txt    P7 第一次导出（PDMS 中性导出文本）
├─ rt_export_2.txt    P8 第二次导出
├─ real_test_result.json  P12 汇总
└─ 搭树自检.txt       搭树阶段产物（不在本计划范围内）
```

**证据要求**：截图必须是**真的拍到了**对应场景（读图可辨识，不看文件大小）；日志必须是**命令的原始回显**（不要手抄）；每次失败也要留证据（出错文本 + 出错位置）。

---

## §4 逐步计划

> 每步格式：**目的 → 命令/操作 → 通过判据 → 失败排障 → 证据**。

---

### P0 前置（进程清理 + 配置备份 + 基线 SHA256）

**目的**：确保 PDMS 未在运行（部署 PML 前必须停机）；把将被部署脚本改动的三个文件留成可逐字节复原的基线。

**命令/操作**

1. 查进程：
   ```
   tasklist | findstr /i "des.exe PDMSConsole mon.exe"
   ```
   若有输出 → 用 `C:/Users/Administrator/.zcode/skills/pdms-install-restart-refresh/scripts/stop-pdms.ps1` 关闭，然后**再查一遍**确认三进程都退出。
2. 建目录 `验收/备份_PDMS配置/`、`验收/实机截图/`、`验收/实机日志/`。
3. 备份**三个**文件（逐条确切路径，不用通配）到 `验收/备份_PDMS配置/`：
   - `D:/AVEVA/Plant/PDMS12.1.SP4/DesignAddins.xml`
   - `D:/AVEVA/Plant/PDMS12.1.SP4/DesignCustomization.xml`
   - `D:/AVEVA/Plant/PDMS12.1.SP4/design.uic`
4. 记录三者的 SHA256（含字节数）到 `验收/备份_PDMS配置/SHA256_before.txt`，格式：
   ```
   <sha256>  <字节数>  <绝对路径>
   ```

**通过判据**

- `tasklist` 的输出里**不含** `des.exe` / `PDMSConsole.exe` / `mon.exe`（三进程全部退出）。
- `验收/备份_PDMS配置/SHA256_before.txt` 恰有 **3 行**，每行的文件存在且 SHA256 与当前文件一致（自己重算一遍核对）。

**失败排障**

- `stop-pdms.ps1` 关不掉：`tasklist` 看是否有残留 `des.exe`；用任务管理器视角确认；**不要**用 `taskkill /f` 之类批量强杀，先看是不是有模态框在等点击（用 `dismiss_error.ps1`）。
- 备份失败（权限/占用）：确认以管理员身份运行；确认文件没被 PDMS 打开。

**证据**：`验收/实机日志/P0_tasklist.txt`、`验收/实机日志/P0_stop.txt`、`验收/备份_PDMS配置/SHA256_before.txt`。

---

### P1 部署（两条路线都装，各自先 dry-run）

**目的**：把 v2.1.0 的两个菜单入口装上：原生 `.NET` 窗体（`deploy_pkpm2pdms.py` 路线）+ legacy PML 菜单（`install.ps1` 路线）。两条路线**都装**，因为 P3 要核对两个菜单名，P7 的导出功能依赖 legacy 路线装的 `!!pkpm2pdmsexport`。

**命令/操作**

1. **原生路线 —— 先 dry-run，核对清单**：
   ```
   python "D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/插件包/pdms-net/deploy/deploy_pkpm2pdms.py" --pdms-root "D:/AVEVA/Plant/PDMS12.1.SP4"
   ```
   逐条读它打印的「将要改变的全部对象」。核对这几条**必须是新名**：
   - `DesignAddins.xml` 插入行含 `<string>PKPM2PDMS</string>`
   - `DesignCustomization.xml` 插入行含 `Name="PKPM2PDMS" Path="pkpm2pdms.uic"`
   - 复制目标 `...\PKPM2PDMS.dll`、`...\pkpm2pdms.uic`
   - 写入 `...\PKPM2PDMS\engine_path.txt`
   - 复制 `...\PKPM2PDMS\pml\pkpm2pdmsuniquename.pmlfnc`
   - 备份后缀为 `.pkpm2pdms-bak`

   清单无误后再执行：
   ```
   python ".../deploy_pkpm2pdms.py" --pdms-root "D:/AVEVA/Plant/PDMS12.1.SP4" --execute
   ```
2. **legacy 路线 —— 先 -DryRun**：
   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File "D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/插件包/install/install.ps1" -PdmsRoot "D:/AVEVA/Plant/PDMS12.1.SP4" -DryRun
   ```
   核对：目标包目录 `...\PMLLIB\pkpm2pdms\`；`design.uic` 追加的菜单项含 `PKPM2PDMS.Menu` / `PKPM2PDMS.Open`，且**按钮标题是 `PKPM2PDMS PML`**（与原生路线区分开，见 `RENAME_MAP §2.6(f)`）；备份名形如 `design.uic.bak_pkpm2pdms_<时间>`；源包编码检查通过。
   然后按上面命令去掉 `-DryRun` 真装。
3. 核对安装结果：
   ```
   dir "D:/AVEVA/Plant/PDMS12.1.SP4\PKPM2PDMS" "D:/AVEVA/Plant/PDMS12.1.SP4\PKPM2PDMS\pml" "D:/AVEVA/Plant/PDMS12.1.SP4\PMLLIB\pkpm2pdms"
   type "D:/AVEVA/Plant/PDMS12.1.SP4\PKPM2PDMS\engine_path.txt"
   ```
   并检查 `DesignAddins.xml` / `DesignCustomization.xml` / `design.uic` 三个文件的内容确实含新名。

**通过判据**（逐条可判定）

1. 两个 dry-run 各自的**清单与随后 `--execute` / 真装的报告一一对应**（不多不少）。
2. `D:/AVEVA/Plant/PDMS12.1.SP4/` 下存在 `PKPM2PDMS.dll` 与 `pkpm2pdms.uic`。
3. `D:/AVEVA/Plant/PDMS12.1.SP4/PKPM2PDMS/engine_path.txt` **存在**，内容指向的引擎文件**确实存在**（`Test-Path` 返回 True），且文件名是 `pkpm2pdms_engine.exe`（新引擎），**不是** `pkpmjwd_engine.exe`。
4. `D:/AVEVA/Plant/PDMS12.1.SP4/PKPM2PDMS/pml/pkpm2pdmsuniquename.pmlfnc` 存在。
5. `DesignAddins.xml` 含子串 `>PKPM2PDMS<`；`DesignCustomization.xml` 含 `Path="pkpm2pdms.uic"`。
6. `D:/AVEVA/Plant/PDMS12.1.SP4/PMLLIB/pkpm2pdms/` 下有 legacy 路线的 PML 文件（至少 `pkpm2pdms.pmlfrm`、`pkpm2pdmsexport.pmlfnc`、`pkpm2pdmsrun.mac`）。
7. 出现备份文件：`DesignAddins.xml.pkpm2pdms-bak`、`DesignCustomization.xml.pkpm2pdms-bak`、`design.uic.bak_pkpm2pdms_*`。
8. **阴性判据**：`D:/AVEVA/Plant/PDMS12.1.SP4/` 下**不应**出现 `PKPMJWD.dll`、`pkpmjwd.uic`、`PKPMJWD\` 目录（若出现说明装到了旧名，属失败）。

**失败排障**

- dry-run 就报 `缺构建产物 ...\PKPM2PDMS.dll` → 构建阶段没产出，先回去跑 `插件包/pdms-net/build.cmd`；把构建日志附到证据里。
- dry-run 报「目标不是 PDMS 安装根？」→ 传 `--pdms-root` 时要指向**有 `design.uic` 的那层**。
- `install.ps1` 退出码 **3**（编码检查未通过）→ 说明 `插件包/pdms/` 里的 PML 不是 GBK 无 BOM + CRLF（改名时被编辑器改坏了）。用 `-SkipEncodingCheck` **不要**作为解决方案；要回去修编码。
- `install.ps1` 退出码 **4**（PDMS 正在运行）→ 回 P0 关干净再装。
- `install.ps1` 退出码 **2**（参数/源包缺失）→ 看它报的缺哪个文件。

**证据**：`验收/实机日志/P1_deploy_dryrun.txt`、`P1_deploy_execute.txt`、`P1_install_dryrun.txt`、`P1_install_execute.txt`、`P1_verify_dir.txt`、`P1_engine_path.txt`、`P1_config_grep.txt`。

---

### P2 启动 PDMS（Sample / Design，分离启动）

**目的**：把装了新插件的 DESIGN 会话拉起来，为 P3/P4 提供现场。

**命令/操作**

1. 建目录并写启动批处理：
   ```
   New-Item -ItemType Directory -Force -Path 'C:/TEMP/p2p_tty'
   ```
   写 `C:/TEMP/p2p_tty/start_sample.bat`，内容**一行**（对应 §1 的一行式）：
   ```
   D:\AVEVA\Plant\PDMS12.1.SP4\pdms.bat Sample SAMPLE/SAMPLE /SAMPLE Design
   ```
   （可对照复制 `.../pdms-plugin-gui-test/scripts/start_sample_design.bat`）
2. **分离启动**（**不要 `-Wait`**）：
   ```
   Start-Process cmd -ArgumentList '/c','C:/TEMP/p2p_tty/start_sample.bat'
   ```
3. 轮询 `des.exe` 出现并等登录完成（约 **90~120 秒**；`SKILL.md` 的流程用 85 s，两者都在同量级，**耐心轮询到登录完成**再截屏）：
   ```
   tasklist | findstr /i des.exe
   ```
4. 登录完成后缩窗布局（DPI-aware，物理坐标，现场实测）。两处参考尺寸均来自 SKILL.md，**取较新的那套**：
   - `SKILL.md:95`（2026-09-22 实测可用，**本文采用**）：屏幕 3840×2160；**PDMS 主窗 `(0,0) 2400×1400`；插件窗 `(2400,20) 705×1440`**
   - `SKILL.md:50`（较早写法）：`MoveWindow(des主窗, 0, 0, 1640, 1380)` 并最小化 PDMSConsole
   两者都在同量级；**以现场屏幕实测为准**，并最小化 PDMSConsole 控制台窗。
5. **首屏截图**（用 `capture_wins.ps1` 或 `SKILL.md §看模型` 的 `fgshot`/`winshot`），存 `验收/实机截图/P2_design_started.png`。**读图**确认是 DESIGN 主窗。

**通过判据**

- `tasklist` 里 `des.exe` 存在。
- `验收/实机截图/P2_design_started.png` **读图**能看到 PDMS DESIGN 主窗口（菜单栏 + 图形区/多窗口可见），不是黑图、不是别的程序。
- 截图里 PDMS 主窗尺寸约为 2400×1400（或至少整窗可见、未被遮挡）。

**失败排障**

- 90~120 s 后仍无 `des.exe` → 看 `PDMSConsole` 窗口里的报错；常见是 license/项目锁。截图留着。
- 起来但报错框 → `dismiss_error.ps1 -DesPid <pid>` 点掉，再截屏。
- 截图全黑/被遮 → 按 `SKILL.md:103` 的“截图全黑先怀疑遮挡”，把 PDMS 置前后再截（`fgshot` 已内置置前）。
- 窗口没起来但进程在 → 用 `capture_wins.ps1 -DesPid <pid>` 抓全部窗口。

**证据**：`验收/实机日志/P2_start.txt`（含 `tasklist` 输出与启动命令）、`验收/实机截图/P2_design_started.png`。

---

### P3 菜单验证（**两个**菜单名都要出现）

**目的**：证明两条安装路线都真的生效（这是 P1「两条路线都装」的可观测结果）。

**命令/操作**

1. 截**主窗菜单栏宽图**：`capture_wins.ps1` 截 PDMS 主窗（尺寸 ≥ 2400 宽），或 `fgshot` 只截顶部条，存 `验收/实机截图/P3_menubar.png`。
2. **读图**，在菜单栏里找两个串：**`PKPM2PDMS`**（原生 .NET 路线）与 **`PKPM2PDMS PML`**（legacy PML 路线）。
3. 若看不到，逐个查（**不改判据，只排查**）：
   ```
   type "D:/AVEVA/Plant/PDMS12.1.SP4\DesignAddins.xml"
   type "D:/AVEVA/Plant/PDMS12.1.SP4\DesignCustomization.xml"
   powershell -NoProfile -Command "Select-String -LiteralPath 'D:/AVEVA/Plant/PDMS12.1.SP4/design.uic' -Pattern 'PKPM2PDMS'"
   dir "D:/AVEVA/Plant/PDMS12.1.SP4\PKPM2PDMS.dll" "D:/AVEVA/Plant/PDMS12.1.SP4\pkpm2pdms.uic"
   ```
   （`design.uic` 是 UTF-8 带 BOM，用 `Select-String` 或 python `io.open(..., encoding='utf-8-sig')` 读；**不要**用会改文件的编辑器打开它。）
   并确认 PDMS 是**在 P1 之后**才启动的（改 PML / 换 DLL 后**必须完全重启**，会话内 `PML REHASH ALL` 不重载；见 `SKILL.md:13`）。

**通过判据**

- `P3_menubar.png` **读图可辨认**：
  - 菜单栏**存在**名为 `PKPM2PDMS` 的菜单项；
  - 菜单栏**存在**名为 `PKPM2PDMS PML` 的菜单项。
- 两条都出现 = PASS；只有一条 = 记 FAIL 并说明哪条没生效；两条都无 = FAIL。

**失败排障**

- 原生菜单没出现：查 `DesignAddins.xml` 里的条目文本是否**精确等于** `PKPM2PDMS`（`IAddin.Name` 必须与之一致，`PKPM2PDMSAddin.cs:24`）；查 `DesignCustomization.xml` 的 `Path="pkpm2pdms.uic"` 是否与实际落盘文件名一致；查 `PKPM2PDMS.dll` 是否真在 PDMS 根（不在 `PKPM2PDMS\` 子目录）。
- legacy 菜单没出现：查 `design.uic` 是否含 `PKPM2PDMS.Menu`；查 `PMLLIB\pkpm2pdms\` 下 PML 文件是否齐（`install.ps1` 只校验 4 个文件名）。
- 两个都不出现：先怀疑 **PDMS 不是 P1 之后重启的**，或 PDMS 启动时把 `DesignAddins.xml` 里找不到的 DLL 静默跳过。**不要手工运行 `pmlscan.exe`、不要改 `PMLLIB\pml.index`**（`install.ps1:328` 明确禁止）。

**证据**：`验收/实机截图/P3_menubar.png`、`验收/实机日志/P3_config_dump.txt`。

---

### P4 打开原生窗体（真实点击 + 控件核对）

**目的**：证明原生 `.NET` 窗体真的能打开、且在 v2.1.0 名字/标题下工作。

**命令/操作**

1. **真实菜单路径**（PDMS 命令行**不认识** .NET 插件命令，`SKILL.md:15`：输入 `PKPM2PDMS.OpenTools` 会报 `CP: Syntax error`；只能点菜单）：
   - 同一 powershell 进程内完成：置前主窗 → `SetCursorPos(菜单x, y)` → `mouse_event` 点击 `PKPM2PDMS` 菜单 → 等菜单展开 → 点击里面的「导入导出」项。
   - 菜单 x 坐标按当前窗口尺寸**现场定位**（菜单重排，别抄旧数字）。
2. `find_float.ps1` 确认悬浮窗出现并置前（输出 `floating: hwnd=... at (x,y) size w x h`）。
3. 截图 `验收/实机截图/P4_form.png`（整窗），必要时再截细节图。
4. **读图**核对标题与主要控件，并把窗体标题、按钮/输入框文字**逐个记录下来**（写进 P12 的证据）。
5. 与源码 `插件包/pdms-net/PKPM2PDMSForm.cs` 对照：标题与按钮文字必须一致，且标题含 **`PKPM2PDMS`** 与版本 **`v2.1.0`**。

**通过判据**

- 窗体出现且被 `find_float.ps1` 找到（有 `hwnd`）。
- `P4_form.png` 读图：窗体标题含 `PKPM2PDMS`；能辨认出文件选择、截面匹配、基点/转角、构件类别勾选、执行按钮等主要控件。
- 记录下来的控件文字与 `PKPM2PDMSForm.cs` **逐条一致**（列出差异即为 FAIL）。
- **阴性判据**：窗体标题/控件里**不得**出现 `PKPMJWD`/`PKPM JWD`（残留旧名 = 漏改）。

**失败排障**

- 点了没反应：99% 是模态错误框堵队列 → `dismiss_error.ps1 -DesPid <pid>`；或输入行有残留 → 清空重发（`SKILL.md:76`）。
- 点到别处：查 DPI。统一 `SetProcessDPIAware()` + 物理坐标；`PrintWindow` 截图即物理像素可直接量（`SKILL.md:18,77`）。
- 窗体出来又被盖：`find_float.ps1` 会置前；若仍被盖，先最小化 PDMSConsole 与资源管理器。
- 窗体一次性崩溃：看 `PKLog` 的日志目录（`PKLog.Dir()` 指向 `<PDMS根>\PKPM2PDMS\`），把日志附上。

**证据**：`验收/实机截图/P4_form.png`、`验收/实机截图/P4_form_detail.png`、`验收/实机日志/P4_findfloat.txt`、`验收/实机日志/P4_controls.txt`（控件文字逐条记录）。

---

### P5 引擎生成导入宏（用 v2.1.0 引擎 exe，样本只读）

**目的**：用**交付的引擎 exe**（不是源码）把只读样本转成 PDMS 导入宏，并拿到构件计数作为 P7 对账基准。

**命令/操作**

1. 先看参数（确认新 exe 能跑）：
   ```
   "D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/安装程序/PKPM2PDMS_引擎_v2.1.0.exe" --cli --help
   ```
2. 生成宏与报告（**样本只读，只读不写**）：
   ```
   "D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/安装程序/PKPM2PDMS_引擎_v2.1.0.exe" --cli jwd2pdms \
     "G:/工作/PDMS相关/00 PDMS插件/02 实用插件/PKPM导入导出插件/JLCJ2.jwd" \
     --out   "D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/验收/rt_model.mac" \
     --secmap "G:/工作/PDMS相关/00 PDMS插件/02 实用插件/PKPM导入导出插件/PKPM转PDMS截面匹配文件.txt" \
     --project JLCJ2 \
     --report "D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/验收/rt_model.report.json"
   ```
   （参数名以第 1 步 `--help` 的实际输出为准；若 `--report` 名字不同，按实际写并在日志里记下。）
3. 从 `rt_model.mac` 里确认宏的**名字相关锚点**（只读）：
   - 出现 `!!pkpm2pdmsUniquename(`（唯一化调用）而**不是** `!!pkpmjwdUniquename(`
   - 出现 `NEW SITE /PKPM2PDMS`（或 `emit_new("", "SITE", SITE_NAME)` 的等价输出）
4. 打开 `rt_model.report.json`，记下构件计数（**参考值：811 构件 / 222 板** —— 这是量级参照，**不是判据**；判据是 P7 的自洽对账）。

**通过判据**

- 第 1 步退出码 **0**，`--help` 正常列出子命令。
- `验收/rt_model.mac` 与 `验收/rt_model.report.json` 都存在且非空。
- `rt_model.mac` 里含 `!!pkpm2pdmsUniquename(`，**不含** `!!pkpmjwd`。
- `rt_model.mac` 里 SITE 名是 `/PKPM2PDMS`（含 `re` 候选逻辑），**不含** `/PKPM_JWD`。
- G 盘样本的 mtime/size **未变化**（自己前后各记一次，证明只读）。

**失败排障**

- exe 起不来 / 报缺 DLL → PyInstaller 产物问题，回构建阶段；先用源码 `python 插件包/engine/cli.py ...` 跑一次，把两边差异记下来。
- 报 `首行不是 #PKPM2PDMS-PDMSDUMP`（在 `pdms2jwd` 方向才会遇到）→ 见 `RENAME_MAP §8 待决项 ②`（旧 dump 的兼容说明）。
- 报截面匹配文件读不了 → 确认 `--secmap` 指到 G 盘那个只读文件（含中文名，**加引号**）。
- 宏里出现 `!!pkpmjwd`（旧名）→ A 包/B 包改名漏了 `macgen.py` 或 PML 定义，属**改名缺陷**，回 `RENAME_MAP §2.4` 交叉核对，不要现场改判据。

**证据**：`验收/实机日志/P5_engine_help.txt`、`P5_engine_run.txt`、`验收/rt_model.mac`、`验收/rt_model.report.json`、`验收/实机日志/P5_gdrive_stat.txt`。

---

### P6 在 PDMS 里执行宏（命令窗注入）

**目的**：让 PDMS 真的按宏建模，这是「端到端」的核心一步。

**命令/操作**

1. 先拿命令窗输入框句柄：
   ```
   powershell -File ".../pdms-plugin-gui-test/scripts/find_cmdedit.ps1" -TargetPid2 <des pid>
   ```
   期望输出 `EDIT hwnd=<n>`。
2. 注入执行宏的命令（宏全路径；用 `$m`）。注入方式按 `SKILL.md:52-54` 的“建立命令通道”做法。可先注入 `Q PROJECT` 验证通道通（响应出现在历史窗）。
   > ⚠ `con_bridge2.ps1` 在脚本目录里**实测不存在**（见 §2）。用你现场确认可用的注入方式；若需自写，落盘到 `验收/实机日志/` 并记入 P12。
3. 清空输入行残留（`EM_SETSEL` + `WM_CLEAR`）后再发，避免 `^^` 类语法错误（`SKILL.md:76`）。
4. 若弹出 `(2,779) Error` 模态框 → `dismiss_error.ps1 -DesPid <pid>` 点掉，**再**继续（模态框会堵死命令队列，`SKILL.md:17`）。
5. 收集命令窗回显，存 `验收/实机日志/P6_cmdlog.txt`；截屏 `验收/实机截图/P6_after_macro.png`。

**通过判据**

- 命令窗回显显示宏**执行完成**（无 `ONERROR` 中止、无 `^^` 指向的错误行）。
- 回显里**没有**未处理的 `(2,779) Error`。
- `P6_after_macro.png` 读图能看到 PDMS 里有新建的结构（3D 视图出现构件，或至少结构树/多窗口有内容变化）。
- 回显里**不得**出现「未定义函数 `!!pkpmjwdUniquename`」之类旧名报错。

**失败排障**

- 命令发了没反应 → `SKILL.md:76`：99% 是模态错误框堵队列（`dismiss_error.ps1`），或输入行有残留（清空重发）。
- 报 `!!pkpm2pdmsUniquename` 未定义 → 唯一化函数没预载。查：`<PDMS根>\PKPM2PDMS\pml\pkpm2pdmsuniquename.pmlfnc` 是否存在；`PKPM2PDMSAddin.cs` 的 `PreloadPmlFunctions()` 是否成功（看 `PKLog` 日志里 `preload pkpm2pdmsuniquename.pmlfnc: ok`）。宏里已有软失败分支（`macgen.py:499` 用 `defined(...)` 判断），若走到那条分支，说明预载失败。
- 宏报 `NEW ... 已存在` → 与 P8 相关，见 P8 排障。
- 报语法错 → 命令窗历史里的 `^^` 标出出错位置（那不是乱码）。把该行连同上下文抄进日志。

**证据**：`验收/实机日志/P6_cmdlog.txt`（原始回显）、`验收/实机截图/P6_after_macro.png`、`验收/实机日志/P6_injector.txt`（注入了什么命令、用什么工具）。

---

### P7 验证建模（用插件自己的导出函数对账）

**目的**：用**被测插件自己**的 PDMS→文本导出能力，把刚建出来的模型读出来，与 P5 的 `report.json` 对账。这样对账链两端都来自被交付物。

**命令/操作**

1. 先读源码确认签名（别猜）：
   ```
   读 "D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/插件包/pdms/pkpm2pdmsexport.pmlfnc"
   ```
   入口签名（v2.0 实测）：`define function !!pkpmjwdexport(!scope is DBREF, !outFile is STRING) is STRING`（:373）；改名后为 `!!pkpm2pdmsexport(!scope, !outFile)`；便捷入口 `!!pkpm2pdmsexportce(!outFile)`（:552，以 `!!CE` 为范围）。
2. 在命令窗里调用（把宏建的 SITE 作为 scope；从 P6 回显或结构树里取**确切元素名**）：
   ```
   !!pkpm2pdmsexport(/PKPM2PDMS, 'D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/验收/rt_export_1.txt')
   ```
   （若返回字符串以 `ERR` 开头，把返回值原样记进日志。）
3. 解析 `rt_export_1.txt`：统计构件数（`#SCTN`/`#PANE`/`#STWALL` 记录数）与层级框架名（`#SITE`/`#ZONE`/`#STRU`/`#FRMW`/`#SBFR` 的名字）。
4. 与 `rt_model.report.json` 的构件计数对账。

**通过判据**

- 调用返回值**不以 `ERR` 开头**（成功）。
- `验收/rt_export_1.txt` 存在，首行是 `#PKPM2PDMS-PDMSDUMP 1.0`（**新 magic**；若是 `#PKPM-JWD-PDMSDUMP`，说明 PML 侧漏改，记 FAIL）。
- 自己写解析脚本统计出的构件数与 `rt_model.report.json` 的计数**一致**；不一致必须给出**解释**（并记为 FAIL 或带解释的 PASS，由 P12 判定）。
- `rt_export_1.txt` 里的层级名与 `rt_model.mac` 里生成的名字一致。

**失败排障**

- 返回 `ERR|打不开输出文件（ALPHA FILE）` → 路径/权限问题：用绝对路径、确认目录存在、**加引号**。
- 返回 `ERR|...` 其它 → 抄下完整返回值；`pkpm2pdmsexport.pmlfnc` 的错误分支不少，按返回文本定位。
- 导出文件是 GBK、但你的解析脚本按 UTF-8 读会失败 → 按 **GBK** 读（`engine/pdms_dump.py` 的 `open(..., encoding='gbk')` 是既有约定）。
- 计数不一致 → 先查是不是**选错了 scope**（导出范围不同，计数自然不同）；把 scope 全名记进日志。scope 必须与 P6 建的 SITE 一致。

**证据**：`验收/rt_export_1.txt`、`验收/实机日志/P7_export_call.txt`（调用命令与返回值）、`验收/实机日志/P7_reconcile.txt`（自己算的计数 vs report.json）。

---

### P8 重名 re 验证（**本次关键验收项**）

**目的**：验证改名后的唯一化链路（`!!pkpm2pdmsUniquename` + 宏侧调用）在**同一棵树已存在**时，第二次执行会生成带 `re` 后缀的新名，而不是报错或覆盖。

**命令/操作**

1. **再执行一次同一个宏**（P6 的方式，同一份 `验收/rt_model.mac`）。
2. 再次导出：
   ```
   !!pkpm2pdmsexport(/PKPM2PDMS, '.../验收/rt_export_2.txt')
   ```
   （若第二棵树已叫 `/PKPM2PDMSre`，scope 仍指向原来的 `/PKPM2PDMS` 即可导出第一棵；**关键是从两次导出文本里比对名字**。）
3. **解析两次导出文本**，比较 `#SITE`/`#ZONE`/`#STRU` 的名字集合：
   - 统计出现 `re` 后缀的名字条数（`re`、`re2`、… `re99`）。
   - 列出前 10 条 `原名 → 实际名` 对照。
4. 若在 PDMS 里直接查更直观，可列结构：
   ```
   (命令窗) LIST SITE          # 或按现场可用语法列出 SITE
   ```

**通过判据**

- 第二次执行**没有**导致「名字已用」硬错误、**没有**覆盖第一棵树（判据：第一棵树仍在，名字仍为 `/PKPM2PDMS`）。
- `rt_export_2.txt` 里**确有名带 `re` 后缀的元素**（至少 SITE 层，例如 `/PKPM2PDMSre`）；`re` 名字条数 **> 0**。
- 若两次导出的差异条数与 `rt_model.mac` 里元素总数相当（即整棵树被唯一化），更佳；条数为 0 或出现覆盖 = **FAIL**。
- FAIL 时必须保留证据（命令窗回显 + 两次导出文本 + 截图）。

**失败排障**

- 没有 re 名字、且报「名字已用」→ 唯一化函数没生效。查：`defined(!!pkpm2pdmsUniquename)` 是否为真（在命令窗直接问）；查预载日志；查宏里调用的是不是**新名字**（`!!pkpm2pdmsUniquename` 而不是 `!!pkpmjwdUniquename`）。**这是改名遗留缺陷，回 `RENAME_MAP §2.4` 交叉核对，不要现场改判据。**
- 第二棵树把第一棵覆盖了 → 说明 `EXIST` 探测失效（`macgen.py` 的 `EXIST $!cand` 逻辑），是**严重缺陷**，记 FAIL 并保留证据。
- re 名字出现在 ZONE/STRU 层但不在 SITE 层 → 如实记录层次，并按「至少 SITE 层未出现」判 FAIL。

**证据**：`验收/rt_export_2.txt`、`验收/实机日志/P8_rerun.txt`（第二次执行的命令窗回显）、`验收/实机日志/P8_rename_list.txt`（`原名 → 实际名` 对照 + 计数）、`验收/实机截图/P8_after_rerun.png`。

---

### P9 原生窗体端到端（尽力而为）

**目的**：走一遍「窗体」这条主用户路径（不只是命令窗），证明窗体→引擎→建模整链可用。

**命令/操作**

1. 打开原生窗体（P4 的方式）。
2. 在窗体上把同一份 `.jwd` 再转一次：
   - **优先**：直接在窗体的路径输入框里填路径（比走文件对话框稳）。
   - 必须走文件对话框时：点文件名框 → `Set-Clipboard <路径>` + `Ctrl+V`（WPF/ElementHost 输入框会吞 `SendInput` 字符，必须用剪贴板粘贴，`SKILL.md:19`）→ 回车。
3. 点「执行」，观察摘要/状态栏；截屏。
4. 若窗体走的是「生成宏」而不是直接建模，则按 P6 方式在命令窗执行，再按 P7 的方式导出对账。

**通过判据**

- **成功情形**：窗体报告执行成功（摘要里构件数与 P5 参考值同量级），且 PDMS 内确实多出一棵树（截图或导出可证）。
- **失败情形**：如实记录失败步骤、错误文本、截图；在 `real_test_result.json` 里记为 `fail`（若是环境/交互工具所限而非产品缺陷，记 `skip` 并写明原因——**不许把做不到的写成做到了**）。

**失败排障**

- 输入框填不进：用剪贴板（`SKILL.md:19`）。
- 点按钮没反应：查模态框（`dismiss_error.ps1`）；查窗体是否被置前（`find_float.ps1`）。
- 窗体报「找不到引擎入口」→ 查三层引擎查找链（`RENAME_MAP §2.2(e)`）：① 环境变量 `PKPM2PDMS_ENGINE` → ② `<PDMS根>\PKPM2PDMS\engine_path.txt` → ③ `<DLL目录>\..\..\engine\dist\pkpm2pdms_engine.exe`。哪一层命中要记进日志。

**证据**：`验收/实机截图/P9_form_e2e.png`、`验收/实机日志/P9_form_e2e.txt`。

---

### P10 清理数据库测试元素（**只用确切名字**）

**目的**：把本次实机测试在 Sample 项目里创建的元素删掉，让测试环境回到干净状态。

**命令/操作**

1. **先从 P7/P8 的导出文本里读出本次创建的确切元素名**（不要凭记忆，不要用通配符）。预期至少：
   - `/PKPM2PDMS`（第一棵树，`macgen.py:76` 的 `SITE_NAME`）
   - `/PKPM2PDMSre`（第二棵树，P8 的唯一化结果）
   把它俩的**完整路径**逐条打印出来，核对无误。
2. 在命令窗里**用确切名字逐个**删除。例如（语法以现场可执行为准）：
   ```
   DELETE SITE /PKPM2PDMSre
   DELETE SITE /PKPM2PDMS
   ```
   > PDMS 的删除语法请以现场实测为准（本机**没有**现成的可引用证据确认 `DELETE SITE <全名>` 一条即删；必要时分两步：先 `/<名字>` 设定当前元素，再删）。
3. 删后**查询确认不存在**：
   ```
   (命令窗) LIST SITE      # 或 Q SITE 之类现场可用查询，确认列表里不再有这两个名字
   ```
4. 若删不动（被引用/锁定/语法不对）→ **保留并如实记录**，不要尝试通配、`/ALL`、强制手段。

**通过判据**

- 删除前：逐条打印出的确切完整路径**不少于** 2 条，且都来自 P7/P8 的导出文本（不是猜的）。
- 删除后：查询结果里**不再存在**这些确切名字。
- 若某项删不掉：`real_test_result.json` 里记 `skip`（或 `fail`）并写清是哪一条、什么现象、留下了什么。

**失败排障**

- `DELETE` 报语法错 → 查现场可用语法（可 `Q SITE`/`LIST` 先看层级），**不要**试通配。
- 报「元素被引用」→ 先删子层（FRMW/SBFR/SCTN/PANE/STWALL）还是整 SITE 级联，按 PDMS 实际行为来；若必须逐层删，逐条列出确切名字后逐个删。
- **绝对不做**：`DELETE SITE /PKPM*`、`DELETE ... ALL`、循环删除、任何通配形式的删除。

**证据**：`验收/实机日志/P10_delete_targets.txt`（删除前的确切名字清单）、`P10_delete_run.txt`（每一条的删除回显）、`P10_after_query.txt`（删除后的查询结果）。

---

### P11 关闭并卸载 + **恢复校验**

**目的**：把插件完整卸掉，并证明 PDMS 的三个配置文件**逐字节回到 P0 的状态**。

**命令/操作**

1. 关闭 PDMS：
   ```
   powershell -File "C:/Users/Administrator/.zcode/skills/pdms-install-restart-refresh/scripts/stop-pdms.ps1"
   tasklist | findstr /i "des.exe PDMSConsole mon.exe"      # 期望无输出
   ```
2. 卸载**两条路线**，各自先 dry-run：
   ```
   python ".../插件包/pdms-net/deploy/undeploy_pkpm2pdms.py" --pdms-root "D:/AVEVA/Plant/PDMS12.1.SP4"          # dry-run
   python ".../undeploy_pkpm2pdms.py" --pdms-root "D:/AVEVA/Plant/PDMS12.1.SP4" --execute
   powershell -NoProfile -ExecutionPolicy Bypass -File ".../插件包/install/uninstall.ps1" -PdmsRoot "D:/AVEVA/Plant/PDMS12.1.SP4" -DryRun
   powershell ... -File ".../uninstall.ps1" -PdmsRoot "D:/AVEVA/Plant/PDMS12.1.SP4"
   ```
3. **恢复校验**：重算三个文件的 SHA256，写入 `验收/备份_PDMS配置/SHA256_after.txt`，再与 `SHA256_before.txt` 逐行比对：
   ```
   python -c "import hashlib,io,sys; [print(hashlib.sha256(open(p,'rb').read()).hexdigest(), p) for p in [r'D:/AVEVA/Plant/PDMS12.1.SP4/DesignAddins.xml', r'D:/AVEVA/Plant/PDMS12.1.SP4/DesignCustomization.xml', r'D:/AVEVA/Plant/PDMS12.1.SP4/design.uic']]"
   ```
   （把输出存 `验收/备份_PDMS配置/SHA256_after.txt`；与 `SHA256_before.txt` 用 `fc /b` 或逐行对照，结论写进 `验收/实机日志/P11_sha_compare.txt`。）
   > 注意：`SHA256_before.txt` 每行含**字节数**，所以「SHA256 一致」同时意味着字节数一致；这也是"逐字节一致"的判据。
4. 另查安装残留（**列出但不删**）：
   ```
   dir "D:/AVEVA/Plant/PDMS12.1.SP4\PKPM2PDMS" 
   dir "D:/AVEVA/Plant/PDMS12.1.SP4\PMLLIB"
   ```
   `PKPM2PDMS.dll` / `pkpm2pdms.uic` 是否按设计被移走或按设计保留；`PMLLIB\pkpm2pdms\` 是否被移动成 `_removed_pkpm2pdms_<时间>\`（**移动而非删除**）。

**通过判据**（这是最硬的判据）

1. `tasklist` 无 `des.exe`/`PDMSConsole.exe`/`mon.exe`。
2. **恢复后三个文件的 SHA256 与 P0 备份逐字节一致**：`DesignAddins.xml`、`DesignCustomization.xml`、`design.uic` 的 SHA256 **分别等于** `SHA256_before.txt` 里记录的对应值（自己重算，不看脚本自报）。**任一条不一致 = FAIL，并在 P12 里重点标注**。
3. 卸载 dry-run 的清单与真跑报告一一对应。
4. 卸载对既有条目**零影响**：`DesignAddins.xml` 里 TGTEXT / PDCOPILOT / Bopood 等非本包条目原样保留（由判据 2 的逐字节一致隐含保证）。
5. 包目录是**移动**（`_removed_pkpm2pdms_<时间>\`）而不是删除（默认模式）。

**失败排障**

- SHA256 不一致 → **先别动手改文件**。按顺序查：(a) 是不是卸载只跑了一条路线（另一条遗留）；(b) 是不是 `design.uic` 被 legacy 路线改过而原生路线没碰它；(c) 是不是 PDMS 启动时自己重写过 `design.uic`（PDMS 会写这个文件）—— 若是 PDMS 自身行为，要在 `real_test_result.json` 里写清「差异来自 PDMS 自身写回，非插件遗留」，并给出具体差异（用 `fc /b` 或 `Compare-Object` 逐字节对比）。
- 删除/移走失败的残留 → 逐条列出并保留，**不删**。
- 卸载报「XML 校验失败已回滚」→ 按脚本提示用备份恢复，并把脚本输出留证。

**证据**：`验收/实机日志/P11_stop.txt`、`P11_undeploy_dryrun.txt`、`P11_undeploy_execute.txt`、`P11_uninstall_dryrun.txt`、`P11_uninstall_execute.txt`、`验收/备份_PDMS配置/SHA256_after.txt`（新算的三行）、`验收/实机日志/P11_sha_compare.txt`（逐行对比结论）。

---

### P12 汇总与判定

**目的**：把 P0–P11 的结论落成一个机器可读、可被复核员独立复算的结果文件。

**命令/操作**

写 `验收/real_test_result.json`：

```json
{
  "status": "passed | failed | blocked",
  "checks": [
    {"name": "P0 前置",              "result": "pass|fail|skip", "evidence": "验收/实机日志/P0_tasklist.txt"},
    {"name": "P1 部署（两条路线）",   "result": "...", "evidence": "..."},
    {"name": "P2 启动 PDMS",         "result": "...", "evidence": "验收/实机截图/P2_design_started.png"},
    {"name": "P3 菜单（两个名字）",   "result": "...", "evidence": "验收/实机截图/P3_menubar.png"},
    {"name": "P4 原生窗体",          "result": "...", "evidence": "验收/实机截图/P4_form.png"},
    {"name": "P5 引擎生成宏",        "result": "...", "evidence": "验收/rt_model.mac + rt_model.report.json"},
    {"name": "P6 执行宏",            "result": "...", "evidence": "验收/实机日志/P6_cmdlog.txt"},
    {"name": "P7 导出对账",          "result": "...", "evidence": "验收/rt_export_1.txt + 实机日志/P7_reconcile.txt"},
    {"name": "P8 重名 re",           "result": "...", "evidence": "验收/rt_export_2.txt + 实机日志/P8_rename_list.txt"},
    {"name": "P9 窗体端到端（尽力）", "result": "...", "evidence": "..."},
    {"name": "P10 清理测试元素",      "result": "...", "evidence": "验收/实机日志/P10_after_query.txt"},
    {"name": "P11 卸载+恢复校验",    "result": "...", "evidence": "验收/实机日志/P11_sha_compare.txt"},
    {"name": "P12 汇总",             "result": "...", "evidence": "验收/real_test_result.json"}
  ],
  "blockers": [],
  "env": {"pdms_started": true, "screen": "3840x2160"}
}
```

**通过判据 / 状态判定规则（照工作流 `pkpm12`）**

**`passed`（全部满足）**
1. **P3**：两个菜单名（`PKPM2PDMS` 与 `PKPM2PDMS PML`）都出现；
2. **P4**：原生窗体成功打开；
3. **P6 + P7**：宏执行成功，且导出对账的构件计数与 `report.json` 一致（差异有解释并被接受）；
4. **P8**：重名 `re` 生效（`rt_export_2.txt` 里确实出现带 `re` 的名字）；
5. **P11**：三个配置文件的 SHA256 与 P0 备份**逐字节一致**。

**`failed`**：上面任一项**关键项失败**（尤其 P3 只有一条菜单、P8 无 `re`、P11 哈希不一致）。

**`blocked`**：环境原因导致无法完成 —— PDMS 起不来、license 不可用、屏幕/交互工具不可用、样本不可读等。`blockers` 里逐条写清。

**其它要求**

- `checks[].result` 只填 `pass`/`fail`/`skip`；`skip` 必须配 `blockers` 里的一条原因。
- 每个 `evidence` 必须是**本机真实存在的路径**（复核员会去读它）。
- 汇总报告里要有：**做了哪些**、**哪些没做到**、**每个结论的证据路径**、**屏幕分辨率**、**PDMS 是否真的启动过**。

**证据**：`验收/real_test_result.json`、`验收/实机日志/P12_summary.txt`。

---

## §5 判据速查表（执行时对照，别自己放松）

| 步 | 一句话判据 | 关键证据 |
|---|---|---|
| P0 | 三进程不在；3 个配置已备份且记录 SHA256 | `备份_PDMS配置/SHA256_before.txt` |
| P1 | 两条路线装成功；`engine_path.txt` 指向**存在**的新引擎；**不出现**任何 `PKPMJWD*` 落盘 | `P1_*.txt` |
| P2 | `des.exe` 在；截图是 DESIGN 主窗 | `P2_design_started.png` |
| P3 | 菜单栏同时有 `PKPM2PDMS` 与 `PKPM2PDMS PML` | `P3_menubar.png`（读图） |
| P4 | 窗体出现、标题含 `PKPM2PDMS`+`v2.1.0`、控件与源码一致、无 `PKPMJWD` 残留 | `P4_form.png` + `P4_controls.txt` |
| P5 | 引擎 `--help` 退出码 0；宏含 `!!pkpm2pdmsUniquename`、SITE=`/PKPM2PDMS`、无旧名；G 盘未变 | `rt_model.mac`、`P5_gdrive_stat.txt` |
| P6 | 宏执行完成、无未处理模态框、PDMS 里出现新结构 | `P6_cmdlog.txt`、`P6_after_macro.png` |
| P7 | 导出成功；首行 `#PKPM2PDMS-PDMSDUMP 1.0`；构件计数与 report.json 对账 | `rt_export_1.txt` |
| P8 | 第二次执行产生 `re` 名字且未覆盖第一棵；`re` 条数 > 0 | `rt_export_2.txt` + `P8_rename_list.txt` |
| P9 | 成功则记录成功；失败如实记 `fail`/`skip` | `P9_*.png/txt` |
| P10 | 只用**确切名字**删；删后查询不存在；删不动就保留并记录 | `P10_*.txt` |
| P11 | 三文件 SHA256 与 P0 **逐字节一致**；包目录是移动不是删 | `SHA256_after.txt`、`P11_sha_compare.txt` |
| P12 | 5 条 passed 判据全满足才 `passed` | `real_test_result.json` |

---

## §6 已知风险与预置对策（执行前先看一遍）

| # | 风险 | 预置对策 |
|---|---|---|
| 1 | `con_bridge2.ps1` 实测不存在（§2） | P6 前先确认注入手段；必要时现场自建注入器并落盘 `验收/实机日志/`，在结果里注明 |
| 2 | PDMS 会在自己启动/退出时**写回** `design.uic` | P11 若哈希不一致，先区分「PDMS 自身写回」与「插件遗留」，用逐字节对比给出证据 |
| 3 | Sample 项目里可能**已有**同名的 `/PKPM2PDMS` 元素 | P5/P6 前先在命令窗查一次 `SITE` 列表；若已存在，**先记录**（这会改变 P8 的预期：第一次执行就可能触发 `re`），并把该事实写进结果 |
| 4 | 用户机器上可能残留 v2.0 的旧名安装（`PKPMJWD.dll` / `PMLLIB\pkpmjwd\`） | P1 前的**阴性判据**已含此项；若发现旧残留，**不要删**，记录后在报告里提示用户用 v2.0 的卸载脚本处理（见 `RENAME_MAP §8 待决项 ①`） |
| 5 | 屏幕不是 3840×2160 / DPI 不是 125% | 所有坐标**现场实测**；缩窗尺寸按实际屏幕调整，截图里记下分辨率 |
| 6 | `(2,779)` 模态错误框堵死命令队列 | 每发一条命令后检查是否有模态框；用 `dismiss_error.ps1` 点掉再继续 |
| 7 | 引擎 exe 或 DLL 尚未产出 | P1/P5 会立刻暴露（缺文件）；此时应回到构建阶段，**不要**用源码版冒名顶替后当成"实机通过" |
| 8 | 中文路径与空格 | 所有命令行里的路径**一律加引号**（工作树路径含中文，样本路径也含中文） |
| 9 | G 盘只读被破坏 | P5 前后各记一次样本的 size/mtime；若变化 → 立即停手并在报告里标注 |

---

## §7 本文与其它文档的关系

| 文档 | 关系 |
|---|---|
| `计划/RENAME_MAP.md` | 提供改名映射与各包文件范围；P1/P4/P5/P7/P8 的判据里用到它的具体行号 |
| `验收/搭树自检.txt` | 证明工作树内容与 v2.0 逐字节一致、以及哪些运行产物被排除 |
| `验收/静态回归.py`（构建阶段产出） | 静态门禁；本计划是它的实机对应物。**静态回归 exit 0 不等于实机通过**，两者都要有 |
| `验收/real_test_result.json` | 本计划的唯一权威结论文件 |
| `C:/Users/Administrator/.zcode/skills/pdms-plugin-gui-test/SKILL.md` | 交互与截图的**操作手册**；本计划的每一步都要求先读它 |
