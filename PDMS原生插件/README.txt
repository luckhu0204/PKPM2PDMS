================================================================================
PKPM2PDMS导入导出 —— PDMS 原生插件（.NET Add-in + Python 引擎 + 少量 PML 工具）
目录：PKPM2PDMS_v2.1.0/插件包/pdms-net/
契约：spec/CONTRACT.md §(p)（实现条款）；★R7 命名方案（2026-09-28 用户定案，见第 5 节）
版本：v2.1.0（2026-09-28，R7 窗体改造：SITE 名探测 + 删除 PML 唯一化依赖）
================================================================================

0) 一句话与硬声明
--------------------------------------------------------------------------------
本包把 .NET WinForms 窗体挂进 PDMS 原生菜单/工具条（像 PKPM导入导出插件那样：
菜单点开一个窗体），文件格式转换交给 Python 引擎进程；PDMS 库内动作 = 「SITE 名探测
（只读查询）+ `$M` 执行引擎生成的建模型宏」。

              ★ 本轮（R7）本包【未部署】、未启动 PDMS ★
  R7 改造期间：没有执行过 deploy 脚本、没有启动/重启 PDMS、没有注册 DLL、没有
  **删除任何 PDMS 元素**、没有卸载插件、没有改写 D:\AVEVA 下任何文件（只读引用那里的
  Aveva 程序集与官方 XML 文档做签名核对）、没有写 G 盘。
  写操作只落在**工作区内**：编译产物（dist\）、_selftest 沙箱（_selftest\_sandbox）。
  需要用户在 PDMS 停机时按第 3 节自行安装。

R7 一句话：执行前由 .NET 侧**直查试出**可用的 SITE 名（静默、零弹窗）传给引擎；
引擎按该名建 SITE、中间层名 `<SITE名>_<段>`（生成期查重）、底层元素无名创建；
宏里**不再出现任何 PML 函数调用**，窗体用 `$M '<宏>'` 执行。

1) 目录与文件
--------------------------------------------------------------------------------
pdms-net/
  PKPM2PDMSAddin.cs   IAddin 入口（骨架照抄 TGTEXT\TGTextAddin.cs，每处 Aveva API
                    注释都标了参照文件与行号；〔R7〕启动时**不做任何 PML 预载**）
  PKPM2PDMSForm.cs    WinForms 窗体（控件清单 = 契约 §p.3 的 13 项，名字逐一对应；
                     〔R7〕执行链：探测 SITE 名 → 带 site_name 调引擎 → `$M '<宏>'`
                     → 读 report 命名结果 + SITE 复核；执行全程零新窗口）
  SiteProber.cs       ★R7 新增：SITE 名探测（DbElement 直查，静默；直查不可用时回退
                     `Q /候选名` 命令）。探测语义的出处与保守方向写在文件头注释里
  PmlBridge.cs      .NET↔PML 桥（RunPml / RunPmlWithResult / ImportDotnet，
                    契约 §p.4 三个冻结方法）
  EngineRunner.cs   引擎进程调用（入口三级解析 + `--cli --request` 协议，契约 §p.5；
                    启动器 exe 必须带 --cli，否则会开 tkinter 图形界面）
  PKLog.cs          日志（<PDMS根>\PKPM2PDMS\addin.log，ASCII + 时间戳，
                    照 TGSPECAddin.cs:52-63）
  build.cmd         编译命令（契约 §p.2 逐字 + 图标/版本开关；CRLF + 纯 ASCII；
                    〔R7〕源文件清单加了 SiteProber.cs）
  AssemblyInfo.cs   程序集版本：AssemblyVersion/FileVersion 2.1.0.0、
                    AssemblyInformationalVersion 2.1.0（插件版本 v2.1.0，未变）
  pkpm2pdms.uic       菜单/工具条定义（与 tgtext.uic 逐条同构，UTF-8 无 BOM + LF）
  dist\             产物：PKPM2PDMS.dll（编译生成）+ pkpm2pdms.uic（源文件的副本，
                    deploy 只认 dist 下这份）
  deploy\           deploy_pkpm2pdms.py / undeploy_pkpm2pdms.py（缺省 dry-run，只加不删、
                    幂等、可回滚；〔R7〕退役的 PML 族不再部署，清单见 RETIRED_PML 常量）
  _selftest\        自检脚本与沙箱：probe_dbelement.ps1（R7 新增，只读反射核对
                    DbElement 签名）、r7_stub_check.cs（R7 新增，不启动 PDMS 的自检桩：
                    候选序列 / args 的 site_name / report 解析 / 单引号拒绝 / 可选 e2e）、
                    sandbox_test.py（deploy/undeploy 清单）、verify_dll.ps1、audit_files.py、
                    read_gbk.py、write_static.py
  README.txt        本文件

2) 怎么编译（已真跑通过）
--------------------------------------------------------------------------------
前置：本机已有 C:\Windows\Microsoft.NET\Framework\v3.5\csc.exe（.NET 3.5/CLR 2.0）
      与 D:\AVEVA\Plant\PDMS12.1.SP4 下的 Aveva 程序集（只读引用，不改它们）。
      不需要 VS / dotnet SDK / 强名称 / GAC。

  cd /d D:\AI_Work\PKPM数据解析\PKPM2PDMS_v2.1.0\插件包\pdms-net
  build.cmd

〔R7 真跑（2026-09-28）〕实际输出（退出码 0）：
  ICON: D:\AI_Work\PKPM数据解析\PKPM2PDMS_v2.1.0\图标\pkpm2pdms.ico
  BUILD OK: D:\AI_Work\PKPM数据解析\PKPM2PDMS_v2.1.0\插件包\pdms-net\dist\PKPM2PDMS.dll
产物核对（_selftest\verify_dll.ps1，退出码 0）：
  DLL 765,952 字节（R6 为 761,856，增量 = SiteProber.cs + 窗体新代码）
  GetAssemblyName: Name=PKPM2PDMS Version=2.1.0.0 ProcessorArchitecture=X86
  FileVersion=2.1.0.0 / ProductVersion=2.1.0（AssemblyInformationalVersion）
  嵌入资源：pkpm2pdms.ico（/win32icon: 与 /resource: 都用，见 build.cmd）
  ImageRuntimeVersion = v2.0.50727（CLR 2.0）；PE machine = 0x14C（I386, x86）
  SHA256 = 025A1B872D8B7E19F0899081288A58E0F4B4B8B84E0760F10FA440D3BABF8F17
  同步到 PDMS原生插件\dist\ 与 PDMS原生插件\ 的两份**逐字节相同**（同上 SHA256）。
  —— 必须用 csc 3.5 + /platform:x86：PDMS 的 des.exe 自身是 CLR v2.0.50727，
     Aveva.Pdms.* 标了 Requires32Bit（_recon/net_addin_feasibility.md §1/§5.2）。

源码定位器（build.cmd 开头的 SRC 解析）：三种布局（就位 / %HERE%pdms-net\ /
  %HERE%PKPM2PDMS*\pdms-net\）都能找到源码并编到正确的 dist（R6 已用 _selftest\_rootsim\
  的暂存副本 + 目录联接复现过三种布局全部退出码 0；本 R7 未改动该定位器）。

编译期真实踩过的两个坑（都已在源码注释里留证）：
  a) Timer 二义（System.Threading.Timer vs System.Windows.Forms.Timer）
     → 窗体里全限定（TGTextAddin.cs:45 的同款处理）；
  b) Command.Error 的静态类型是 Aveva.Pdms.Utilities.Messaging.PdmsMessage
     而非 string（csc 报 CS0173 实测得出）→ PmlBridge.SafeError 经 object + ToString()
     取文本（SiteProber.SafeError 同法）。

3) 怎么安装（必须 PDMS 停机时）
--------------------------------------------------------------------------------
安装 = 纯文件注册（不改注册表、不进 GAC），共 5 步：
  ① 备份 <PDMS根>\DesignAddins.xml、DesignCustomization.xml（.pkpm2pdms-bak，只备一次）
  ② DesignAddins.xml 的 </ArrayOfString> 前插 <string>PKPM2PDMS</string>
  ③ DesignCustomization.xml 的 </UICustomizationFiles> 前插
     <CustomizationFile Name="PKPM2PDMS" Path="pkpm2pdms.uic" />   ← 最容易漏的一步
  ④ 复制 dist\PKPM2PDMS.dll、dist\pkpm2pdms.uic 到 <PDMS根>\
  ⑤ 写 <PDMS根>\PKPM2PDMS\engine_path.txt（引擎入口绝对路径，UTF-8 无 BOM 单行）；
     复制 插件包\pdms\ 下的可部署文件到 <PDMS根>\PMLLIB\pkpm2pdms\（逐字节原样，
     GBK 无 BOM + CRLF）。〔R7〕**不再**往 <PDMS根>\PKPM2PDMS\pml\ 复制任何 .pmlfnc。

步骤（缺省 dry-run，先看清单再执行）：
  cd /d D:\AI_Work\PKPM数据解析\PKPM2PDMS_v2.1.0\插件包\pdms-net\deploy
  python deploy_pkpm2pdms.py                 ← 先 dry-run：打印"将要改变的全部对象"
  python deploy_pkpm2pdms.py --execute       ← 确认清单无误后再真执行（PDMS 停机！）
  然后启动 PDMS DESIGN，菜单栏出现「PKPM2PDMS」→ 点「PKPM2PDMS导入导出」。
  （装完重启 PDMS 生效；PML 侧要重启才会重新索引。）

可选项：
  --engine-entry <PATH>   显式指定引擎入口（写进 engine_path.txt）；
                          缺省自动找 engine\dist\pkpm2pdms_engine.exe / run_engine.cmd
  --pdms-root <DIR>       指向其它目录（仅测试用；正式安装不要带）

〔R7〕部署清单的构成（dry-run 会逐条打印，这里给口径）：
  = 2 备份 + 2 XML 插入 + 2 复制（DLL/uic）+ 1 写 engine_path.txt
    + 插件包\pdms\ 下**可部署**的 PML 文件（本机当前 = 21 个；另 5 个退役文件不部署）。
  退役族（deploy_pkpm2pdms.py 的 RETIRED_PML，逐条精确文件名、不用通配符）：
    唯一化主函数 / 改名计数×2 / 改名清单 / 运行入口函数 —— 这一族在 R7 整体退役
    （改名责任移交给 .NET 探测 + 引擎生成期查重），文件仍留在工作树里（不删）。

4) 怎么卸载（同样 PDMS 停机时）
--------------------------------------------------------------------------------
  cd /d D:\AI_Work\PKPM数据解析\PKPM2PDMS_v2.1.0\插件包\pdms-net\deploy
  python undeploy_pkpm2pdms.py               ← 先 dry-run
  python undeploy_pkpm2pdms.py --execute

卸载策略 = 恢复优先（比"删条目"更稳，符合"只加不删、可回滚"红线）：
  ① 两个 XML 从 .pkpm2pdms-bak 逐字节复原；
  ② 安装过的文件（DLL / uic / engine_path.txt / PMLLIB\pkpm2pdms\ 下本包部署的 PML）
     移动到 <PDMS根>\PKPM2PDMS\_uninstalled_<时间戳>\（不删除，原文件保留）；
  ③ .pkpm2pdms-bak 备份文件保留。

5) 用法（PDMS 内窗体）
--------------------------------------------------------------------------------
窗体一窗三向（下拉三项，显示中文；值 = 引擎子命令；R6 起固定，R7 未改）：

  ① PKPM导入PDMS      → auto2pdms  选 .jwd 或 .pdt 源文件（**按内容自动识别**）
  ② PDMS导出PDT文件   → pdms2pdt   先经 PML !!pkpm2pdmsexport 取 PDMSDUMP 文本再转
  ③ PDMS导出JWD文件   → pdms2jwd   同上

〔R7〕一键导入的完整执行链（点「执行」之后，除窗体自身刷新外**零新窗口**）：
  ① 校验输入（源文件存在、输出非空且不同于源）；
  ② **SITE 名探测**（SiteProber，UI 线程内、静默）：候选序列
     `/PKPM2PDMS` → `/PKPM2PDMSre` → `/PKPM2PDMSre2` … `/PKPM2PDMSre99`（共 100 个），
     取第一个可用名。判定用 `Aveva.Pdms.Database.DbElement.GetElement("/候选名")`：
     官方文档（D:\AVEVA\...\Aveva.Pdms.Database.xml:2832-2838）写明"名字未知 ⇒ 返回
     null Element"，类文档（同文件 2000）写明"要用 IsNull 判空"；本包两种都防
     （null 引用 / IsNull / 抛异常）。**保守方向**：拿不准判"占用"（宁可换下一个名字），
     因为误判"可用"会让宏里 `NEW SITE /已存在名` 失败，而宏头是 ONERROR CONTINUE，
     错误不会中止宏 —— 那正是"带病出宏"。
     探测前先用一个"必定不存在"的负控名自检机制（直查对未知名必须回"未占用"）；
     直查不可用（异常/语义不符）时回退 `Q /候选名` 命令（Run()/Error 判定，同样静默），
     回退也过一次同样的负控；直查把 100 个候选全判占用时，用回退机制交叉验证一次。
     100 个全占用 / 两种机制都不可用 ⇒ 摘要区明确报错，**不执行导入**。
  ③ 组装 `--request`（新增键 `site_name`）+ 调引擎（`--cli --request`，同步等待 ≤30 min）；
  ④ 引擎生成宏（`%TEMP%\PKPM2PDMS\import_<yyyyMMdd-HHmmss>.mac`，每次一份供审计）：
     SITE = 传入的 site_name（引擎不改名、不做 re 逻辑）；中间层 = `<SITE名>_<段>`
     （ZONE `_<工程名>` / STRU `_MF` / FRMW `_EL1..ELn`、`_FW`、`_GR` /
     SBFR `_EL<k>_COLUMN|BEAM|HBRACE|VBRACE|SLAB|WALL`，含层号 ⇒ 全宏唯一，生成期查重，
     重复即生成失败）；底层 SCTN/PANE/STWALL **无名创建**（PDMS 分配系统名）；
     宏头 `ONERROR CONTINUE`；宏里**不含任何** `!!pkpm2pdms*` 调用。
  ⑤ 窗体执行 `$M '<宏全路径>'`（.mac 的 $M 合法，官方先例 = PMLLIB 的
     common\forms\*macro*.pmlfrm:76-86）；
  ⑥ 结果 + 命名结果上摘要区：读 report 的 `options.site_name` /
     `stats.used_names_count` / `stats.unnamed_count`（**不解析 stdout**），
     再用 SiteProber 复核该 SITE 名现在是否真的存在（宏真建了/没建，都如实写）。

R7 交互纪律（与 R6 一致）：**「执行」全程不弹第二个窗口** ——
  * 引擎调用带 --cli（见 EngineRunner.cs），启动器 exe 不再开 tkinter 图形界面；
  * 输入校验不过 / 探测失败 / 引擎失败 / 宏失败 一律落摘要区 + addin.log，不弹 MessageBox；
  * 探测本身也是静默的：不 $P、不进命令窗（先走 DbElement 直查；只有直查不可用才回退
    Q 命令，见第 6 节的 [待实机确认] 条目）；
  * 保留的对话框只有文件选择（打开/保存）与「打开报告」按钮的提示，属正常交互。
  * 10 个英文子命令里其余 7 个（jwd2pdms/pdt2pdms/jwd2db/pdt2db/db2jwd/db2pdt/
    jwd2pdt/pdt2jwd）仍在引擎 CLI 中可用，只是不在窗体下拉里。

〔R7〕改名/唯一化责任分工（用户 2026-09-28 定案，本包不偏离）：
  * SITE 名 → .NET 侧直查试名（SiteProber），唯一责任方；
  * 中间层/底层名 → 引擎生成期维护已用名字集合 + 落盘前全量自查（重复即失败）；
  * 运行期 PML 唯一化函数 → 整体退役（不再部署、不再被任何代码引用）。

6) 现状与依赖（如实声明）
--------------------------------------------------------------------------------
* 引擎独立可执行（engine\dist\pkpm2pdms_engine.exe + run_engine.cmd 回退）由实施包
  S9 交付；engine 侧 --request 解析（{"tool","args"}，键 = CLI 长选项名去 "--"）与本包
  EngineRunner.cs 同一约定；〔R7〕建模型方向新增 `site_name` 键（缺 ⇒ 引擎退出码 2，
  错误信息写明"由 .NET 侧直查试出"）。
* 导出方向（pdms2pdt/pdms2jwd）的 PML 依赖：窗体调 `!!pkpm2pdmsexport(!!CE,'<path>')`
  （pdms\pkpm2pdmsexport.pmlfnc）—— 该函数随 deploy 装到 <PDMS根>\PMLLIB\pkpm2pdms\；
  导出成功的判据 = dump 文件真的写出来且非空（`.Result` 对 PML 表达式命令取不到值，
  R6 实机两次证据）。
* 〔R7〕**退役族不再部署，但两个 legacy 入口仍随包部署**（用户指定的清单如此）：
  `pdms\pkpm2pdms.pmlfrm`（legacy PML 窗体）与 `pdms\pkpm2pdmsrun.mac`（宏运行入口）
  内部仍调用退役族函数，故它们**装上去也按不了那两颗按钮**（会报 "PML: Function not
  found"）。这两个文件属 `插件包\pdms\**`，不在 R7 窗体改造的文件范围内，需其归属方
  同步改写（要么删掉对退役函数的调用，要么改成 `$M` 直跑 + 读报告）。
* 窗体摘要里的命名结果显示依赖 report 的三个键（见第 5 节⑥）；引擎若还未按 R7 产出
  这三个键，摘要会少这几行（不报错、不猜）。
* 窗体的 8 个构件类别勾选（chkColumn…chkHole）按契约 §p.3-8 冻结保留；§m.1 冻结的 CLI
  暂无对应的类别过滤参数，故勾选状态暂不传给引擎（等契约增补后再接线）。
* 【待实机确认】清单（本轮**未**在 PDMS 实机验证过，本轮也绝不允许启动 PDMS）：
  1) `DbElement.GetElement(string)` 在真实会话里对"不存在名字"是否如文档返回 null
     Element（而不是抛异常）—— 本包两种都防（try/catch + IsNull），但"抛异常 ⇒ 走回退"
     这条分支的真伪要靠实机确认；
  2) 回退探测的 `Q /候选名` 命令形态：**本机 PMLLIB 全目录检索 "Q /" 只命中 PML 的
     `eq /...` 比较（假阳性）**，没有 Q 命令的先例可引；"名字不存在 ⇒ Run() 返回 false
     且 Error 有文本"这一形态未验证。回退只在第 1 条不成立时才走，且摘要区会标出本次
     实际用的机制；
  3) `$M '<宏全路径>'` 在 PDMS 12.1 SP4 里对 `.mac` 的行为（官方 PMLLIB 有先例，但本包
     未实机跑过）；`$M` 返回 true 而宏内某行失败（ONERROR CONTINUE 不中止）时，只有
     命令窗输出与第 5 节⑥ 的 SITE 复核能发现 —— 实机验收请以这两处为准；
  4) 引擎宏在真实 PDMS 库里创建 SITE/ZONE/STRU/FRMW/SBFR 的形态与名字合法性。
* 一致性依赖：`插件包\engine\**` 由 B 包维护（本包不动）；本包只保证 request 的形状与
  键名与其一致（`site_name` / `src` / `out` / `report` / `secmap` / `extra` / `base` /
  `angle` / `unit`）。

7) 本轮（R7）实际跑过的验收（真实命令与结论）
--------------------------------------------------------------------------------
* 只读证据（为探测方法找签名，不启动 PDMS）：
  `powershell -NoProfile -ExecutionPolicy Bypass -File _selftest\probe_dbelement.ps1`
  → 反射实测 `Aveva.Pdms.Database.DbElement GetElement(System.String) [static public]`、
  属性 `IsNull` / `IsValid` / `IsDeleted` 存在；官方文档
  `D:\AVEVA\Plant\PDMS12.1.SP4\Aveva.Pdms.Database.xml:2832-2838` 写明"名字未知 ⇒
  返回 null Element"、"用 IsNull 判空"（同文件 2000、4099）。
* 编译：`插件包\pdms-net\build.cmd` → 退出码 0、BUILD OK（输出见第 2 节）；
  编译成功本身即证 SiteProber.cs 里 `DbElement.GetElement(string)` / `IsNull` 对真
  Aveva.Pdms.Database.dll 可解析（未加任何新的 using 欺骗）。
* 产物：`_selftest\verify_dll.ps1` → RESULT OK（CLR v2.0.50727 + I386 + Name=PKPM2PDMS
  + Version=2.1.0.0）；嵌入资源 pkpm2pdms.ico；SHA256 见第 2 节。
* 静态自查（在本包根下跑；「退役族关键词」= 退役族两个文件的英文名去掉公共前缀后
  的那两个词，逐字列在 deploy\deploy_pkpm2pdms.py 的 RETIRED_PML 常量里）：
  `findstr /I /S "<退役族关键词1> <退役族关键词2>" *.cs` → **0 命中**（连注释里都没有）；
  `findstr /I /S "site_name" *.cs` → 命中（窗体与 SiteProber，request 新键）；
  `findstr /I "<退役族关键词1>" deploy\*.py` → 只在 RETIRED_PML 常量里；
  deploy / undeploy 的 **dry-run 输出**（即"清单"）里这两个关键词 **0 命中**
  （幂等、只加不删；清单里另打印"另有 5 个退役文件不部署"）。
  注：`_selftest\_sandbox\PKPM2PDMS\_uninstalled_*\` 里躺着的是**历次沙箱测试被 undeploy
  移走的历史副本**（按红线只移不删），对全树做关键词 grep 会命中它们 —— 它们从不部署、
  不在交付清单里。
* 注册脚本：`python _selftest\sandbox_test.py`（沙箱 = 工作区内副本，绝不碰真 D:\AVEVA）
  → **FAILS: 0**。对照项含：dry-run 清单里退役族 0 命中、退役族未被部署到 PMLLIB、
  PML 21 个文件逐字节到位、幂等（连跑两次 XML 字节不变）、undeploy 后 XML 与备份
  逐字节相等、24 个已装文件移入最新 _uninstalled_*、备份保留、全部清单无删除动作。
* 逻辑自检桩（**不启动 PDMS**）：`_selftest\r7_stub_check.cs` 用 csc 3.5 x86 编成
  `%TEMP%\_r7_selftest\_r7_stub_check.exe`，反射驱动真的 `dist\PKPM2PDMS.dll`：
    - 候选序列 = 100 个、首三个 `/PKPM2PDMS` `/PKPM2PDMSre` `/PKPM2PDMSre2`、
      末个 `/PKPM2PDMSre99`、无重复、无空白/`~`/内部 `/`  → PASS；
    - `BuildEngineArgs`：auto2pdms 的 args 含 `site_name=/PKPM2PDMSre`（+ src/base/angle/unit），
      pdms2jwd 的 args **不含** site_name/base → PASS；
    - `Json*After` 解析真形状的 report 片段（site_name / used_names_count / unnamed_count、
      缺键返回 null）→ PASS；含单引号的宏路径被拒绝执行 → PASS。合计 **PASS=15 FAIL=0**。
* 编码/版本审计：`python _selftest\audit_files.py` → FAILS: 0（含 SiteProber.cs 的
  UTF-8 无 BOM；build.cmd 纯 ASCII + CRLF；uic 三份字节相同；版本特性 2.1.0.0 / 2.1.0）。
* .NET → 引擎 端到端（**不开 PDMS**，用同一自检桩的 `--e2e`）：窗体的 BuildEngineArgs
  → `EngineRunner.Run`（`--cli --request`）→ `engine\dist\pkpm2pdms_engine.exe`：
  `auto2pdms` 退出码 0、耗时 0.01 s、产出宏 + report；窗体 `AppendEngineNames` 从真 report
  里读出 `SITE 名 = /PKPM2PDMSre`、`带名创建 11 个`、`无名创建 5 个`。
  该宏逐条核对：`NEW SITE /PKPM2PDMSre` / ZONE `_PKPM_PROJECT` / STRU `_MF` /
  FRMW `_EL1,_EL2,_FW,_GR` / SBFR `_EL1_COLUMN|BEAM|HBRACE|SLAB`；宏头 `ONERROR CONTINUE`；
  `NEW SCTN`×4、`NEW PANE`×1 = 无名创建；全文 `!!` **0 处**、`LABEL`/`handle`/`$M` **0 处**。
  （样本：只读用工作区内 `插件包\test\_acceptance_out\acc_fixture.jwd` + 显式匹配文件
  `插件包\test\fixture_secmap_dup.txt`；产物只落 `%TEMP%\PKPM2PDMS\`。）
* 未跑：PDMS 实机链路（窗体 → 探测 → 引擎 → `$M` → 复核）与任何会改 PDMS 库的动作。

8) 编码纪律（本包落盘形态）
--------------------------------------------------------------------------------
*.cs / *.py / README.txt / ENGINE_IO.md：UTF-8 无 BOM；build.cmd：纯 ASCII + CRLF
（LF-only 的 .cmd 会被 cmd 误解析，契约 §p.2 实测教训）；pkpm2pdms.uic：UTF-8 无 BOM + LF
（与在用的 tgtext.uic 逐字节同构）。deploy 复制的 PML 文件按 GBK+CRLF 原样字节复制，
不做转码；本包不生成、不改写 PDMS 侧文件。

9) 版本沿革（一句话各）
--------------------------------------------------------------------------------
R1-R5 侦察/契约/格式转换与 PML 工具集（详见验收\实机日志_R4 与 spec\CONTRACT.md）。
R6  实机反馈三项修复：多余窗口（--cli）、一键导入、下拉收敛为三项；宏本体改为标准
    "DB Output 宏"结构（去掉错误块）。
R7  窗体改造（本版）：.NET 侧 SITE 名直查探测（SiteProber）+ `--request` 新增 site_name
    + 窗体 `$M '<宏>'` 执行 + 删净对 PML 唯一化函数族的一切依赖（部署清单同步移除）。

—— 本包未部署，需要用户自己在 PDMS 停机时按第 3 节安装。——
================================================================================
