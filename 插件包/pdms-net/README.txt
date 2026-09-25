================================================================================
PKPM-JWD导入导出 —— PDMS 原生插件（.NET Add-in + PML 混写）
目录：PKPM-JWD导入导出/pdms-net/
契约：spec/CONTRACT.md §(p)（实现条款）与 §(o)（宏内重名唯一化）
版本：R3（2026-09-25，实施包 ⑬）
================================================================================

0) 一句话与硬声明
--------------------------------------------------------------------------------
本包把 .NET WinForms 窗体挂进 PDMS 原生菜单/工具条（像 PKPM导入导出插件那样：
菜单点开一个窗体），文件格式转换交给 Python 引擎进程，PDMS 库内动作交给 PML。

                    ★ 本包【未部署】★
  本轮从未执行 deploy 脚本、从未启动 PDMS、从未注册 DLL、从未改写
  D:\AVEVA 下任何文件、从未写 G 盘（有无接触基准核对佐证，见第 7 节）。
  需要用户在 PDMS 停机时按第 3 节自行安装；交付完也不会自动部署。

1) 目录与文件
--------------------------------------------------------------------------------
pdms-net/
  PKPMJWDAddin.cs   IAddin 入口（骨架照抄 TGTEXT\TGTextAddin.cs，每处 Aveva API
                    注释都标了参照文件与行号）
  PKPMJWDForm.cs    WinForms 窗体（控件清单 = 契约 §p.3 的 13 项，名字逐一对应）
  PmlBridge.cs      .NET↔PML 桥（RunPml / RunPmlWithResult / ImportDotnet，
                    契约 §p.4 三个冻结方法）
  EngineRunner.cs   引擎进程调用（入口三级解析 + --request 协议，契约 §p.5）
  PKLog.cs          日志（<PDMS根>\PKPMJWD\addin.log，ASCII + 时间戳，
                    照 TGSPECAddin.cs:52-63）
  build.cmd         编译命令（契约 §p.2 逐字；CRLF + 纯 ASCII 注释）
  pkpmjwd.uic       菜单/工具条定义（与 tgtext.uic 逐条同构，UTF-8 无 BOM + LF）
  dist\             产物：PKPMJWD.dll（编译生成）+ pkpmjwd.uic（源文件的副本，
                    deploy 只认 dist 下这份）
  deploy\           deploy_pkpmjwd.py / undeploy_pkpmjwd.py（缺省 dry-run，只加不删、
                    幂等、可回滚；本轮只交付、绝不执行）
  _selftest\        本轮自检脚本与沙箱（verify_dll.ps1 / sandbox_test.py 等，
                    全部为本轮新建，可复核可复跑）
  README.txt        本文件

2) 怎么编译（已真跑通过）
--------------------------------------------------------------------------------
前置：本机已有 C:\Windows\Microsoft.NET\Framework\v3.5\csc.exe（.NET 3.5/CLR 2.0）
      与 D:\AVEVA\Plant\PDMS12.1.SP4 下的 Aveva 程序集（只读引用，不改它们）。
      不需要 VS / dotnet SDK / 强名称 / GAC。

  cd /d D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\pdms-net
  build.cmd

实际输出（2026-09-25 实测）：
  BUILD OK: D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\pdms-net\dist\PKPMJWD.dll

源码定位器（build.cmd 开头的 SRC 解析，CSC 参数与契约 §p.2 完全一致）：
  build.cmd 会在三种布局下自动找到源码并编到正确的 dist：
    ① 就位运行（脚本在 pdms-net\ 内，SRC = 脚本目录）；
    ② 被复制/暂存到上级目录（SRC = %HERE%pdms-net\）；
    ③ 被复制/暂存到包含 PKPM-JWD*\ 目录的地方（SRC = %HERE%PKPM-JWD*\pdms-net\，
       通配为纯 ASCII，不写中文目录名进 .cmd）。
  起因（真实事故）：验收方曾把 build.cmd 复制到工作区根运行，%HERE% 指向根，
  csc 报 5 条 CS1504「源文件 d:\AI_Work\PKPM数据解析\EngineRunner.cs 未能打开」。
  本包已在 _selftest\_rootsim\ 里用暂存副本 + 目录联接复现并验证三种布局
  全部退出码 0（_rootsim\ 下的 PKPM-JWD-sim、pdms-net 是指向真实目录的
  联接，仅链接非实体；按"不删除"红线保留原位，由用户自行处置）。

产物核对（_selftest\verify_dll.ps1 实测）：
  DLL 40,960 字节；GetAssemblyName: Name=PKPMJWD, ProcessorArchitecture=X86,
  PublicKeyToken=null；ImageRuntimeVersion = v2.0.50727（CLR 2.0）；
  PE machine = 0x14C（I386, x86）。
  —— 必须用 csc 3.5 + /platform:x86：PDMS 的 des.exe 自身是 CLR v2.0.50727，
  Aveva.Pdms.* 标了 Requires32Bit（_recon/net_addin_feasibility.md §1/§5.2）。

编译期真实踩过的两个坑（都已在源码注释里留证）：
  a) Timer 二义（System.Threading.Timer vs System.Windows.Forms.Timer）
     → 窗体里全限定（TGTextAddin.cs:45 的同款处理）；
  b) Command.Error 的静态类型是 Aveva.Pdms.Utilities.Messaging.PdmsMessage
     而非 string（侦察清单未标类型，csc 报 CS0173 实测得出）
     → PmlBridge.SafeError 经 object + ToString() 取文本。

3) 怎么安装（必须 PDMS 停机时）
--------------------------------------------------------------------------------
安装 = 纯文件注册（不改注册表、不进 GAC），共 5 步（契约 §p.6）：
  ① 备份 <PDMS根>\DesignAddins.xml、DesignCustomization.xml（.pkpmjwd-bak，只备一次）
  ② DesignAddins.xml 的 </ArrayOfString> 前插 <string>PKPMJWD</string>
  ③ DesignCustomization.xml 的 </UICustomizationFiles> 前插
     <CustomizationFile Name="PKPMJWD" Path="pkpmjwd.uic" />   ← 最容易漏的一步
  ④ 复制 dist\PKPMJWD.dll、dist\pkpmjwd.uic 到 <PDMS根>\
  ⑤ 写 <PDMS根>\PKPMJWD\engine_path.txt（引擎入口绝对路径）；
     复制 pdms\pkpmjwduniquename.pmlfnc 到 <PDMS根>\PKPMJWD\pml\

步骤（缺省 dry-run，先看清单再执行）：
  cd /d D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\pdms-net\deploy
  python deploy_pkpmjwd.py                 ← 先 dry-run：打印"将要改变的全部对象"
  python deploy_pkpmjwd.py --execute       ← 确认清单无误后再真执行（PDMS 停机！）
  然后启动 PDMS DESIGN，菜单栏出现「PKPM JWD」→ 点「PKPM JWD 导入导出」。
  （PDMS 已停机再执行；装完重启 PDMS 生效。）

可选项：
  --engine-entry <PATH>   显式指定引擎入口（写进 engine_path.txt）；
                          缺省自动找 engine\dist\pkpmjwd_engine.exe / run_engine.cmd
  --pdms-root <DIR>       指向其它目录（仅测试用；正式安装不要带）

4) 怎么卸载（同样 PDMS 停机时）
--------------------------------------------------------------------------------
  cd /d D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\pdms-net\deploy
  python undeploy_pkpmjwd.py               ← 先 dry-run
  python undeploy_pkpmjwd.py --execute

卸载策略 = 恢复优先（比"删条目"更稳，符合"只加不删、可回滚"红线）：
  ① 两个 XML 从 .pkpmjwd-bak 逐字节复原；
  ② 安装过的 4 个文件（DLL/uic/engine_path.txt/pmlfnc）移动到
     <PDMS根>\PKPMJWD\_uninstalled_<时间戳>\（不删除，原文件保留）；
  ③ .pkpmjwd-bak 备份文件保留。

5) 用法（PDMS 内窗体）
--------------------------------------------------------------------------------
窗体一窗三向：转换（jwd2pdt/pdt2jwd 等）、建 PDMS 模型（jwd2pdms/pdt2pdms，宏由
引擎生成后自动 $M 执行，宏内含 §o 重名唯一化）、截面库（jwd2db/pdt2db 生成目录/
规格宏，确认后手动执行）、导出（pdms2jwd/pdms2pdt 先经 PML !!pkpmjwdexport 取
PDMSDUMP 文本再转）。10 个操作下拉对应契约 §m.1 的窗体子命令子集；执行完摘要区
显示引擎 stdout（含未解析截面清单），「打开报告」用系统默认程序打开 report.json。
重名唯一化：PDMS 侧运行期函数 !!pkpmjwdUniquename（pdms/pkpmjwduniquename.pmlfnc，
S2 交付）—— 已占用的名字自动加后缀 re / re2 / … / re99，全占满则报错中止整宏，
改名记录落 report.renames（契约 §o）。

6) 现状与依赖（如实声明）
--------------------------------------------------------------------------------
* 引擎独立可执行（engine\dist\pkpmjwd_engine.exe + run_engine.cmd 回退）由实施包
  S9 交付；engine 侧的 --request 解析（读 {"tool","args"} JSON，键 = CLI 长选项名
  去 "--"）须与本包 EngineRunner.cs 的同一约定对齐（契约 §p.5 注）。在它交付前，
  窗体执行会报"找不到引擎入口"（可先设环境变量 PKPMJWD_ENGINE 指向 cli.py 的
  包装器，等 S9 落地）。
* pdms\pkpmjwduniquename.pmlfnc（§o.2 唯一化函数）由实施包 S2 交付；当前缺失时
  deploy 会如实打印"跳过"而不是静默失败。
* 〔R3 复核补记〕导出方向的 PML 依赖：窗体「PDMS 文本导出」调
  !!pkpmjwdexport(!!CE,'<path>')（pdms\pkpmjwdexport.pmlfnc:373，返回 'OK|…'）——
  该函数**不由 deploy 安装**（deploy_pkpmjwd.py 只复制 pkpmjwduniquename.pmlfnc），
  而是随 install\install.ps1 复制到 <PDMS根>\PMLLIB\pkpmjwd\（install.ps1:67,262）
  并经 pkpmjwdrun.mac $M 载入（install.ps1:330）。⇒ 要用窗体的导出功能，需先按
  install.ps1 装 PML（或在 PDMS 命令行手动 $M <包>\pdms\pkpmjwdexport.pmlfnc），
  否则该按钮报"找不到 PML 函数"（r==null ⇒ MessageBox+日志，PmlBridge 失败路径
  干净：不会半截写文件）。
* 窗体的 8 个构件类别勾选（chkColumn…chkHole）按契约 §p.3-8 冻结保留；§m.1 冻结
  的 CLI 暂无对应的类别过滤参数，故勾选状态暂不传给引擎（等契约增补后再接线）。
* 运行期行为（$M 绝对路径直跑、VAR EXIST + handle(2,109) 的占用判定、Result 取回
  !!pkpmjwdRenames 的形态）均标注【待实机确认】（契约 §12#26/27/28），本轮未在
  PDMS 实机上验证过 —— 本轮也绝不允许启动 PDMS。

7) 本轮实际跑过的验收（真实命令与结论）
--------------------------------------------------------------------------------
* 编译：pdms-net 下 build.cmd → 退出码 0，BUILD OK（输出见第 2 节）。
* 产物：_selftest\verify_dll.ps1 → CLR v2.0.50727 + PE I386 + Name=PKPMJWD，RESULT OK。
* 注册脚本：_selftest\sandbox_test.py（--pdms-root 指向工作区内的沙箱副本，绝不碰
  真 D:\AVEVA）→ FAILS: 0：dry-run 打印 8 项完整清单且零写入；execute 后条目各 1 处、
  BOM 保留、CRLF 恰各加 1 行（addins 26→27、cust 11→12）；连跑两次幂等（XML 字节
  不变）；undeploy 后 XML 与备份逐字节相等、4 文件移入 _uninstalled_*、备份保留；
  全部清单无任何删除动作。
* 无接触基准：test\check_v3_notouch.py snapshot（开工前）/ verify（收尾）→
  D:\AVEVA 顶层 645 文件与 G:\…\PKPM导入导出插件 751 文件零变化。

8) 编码纪律（本包落盘形态）
--------------------------------------------------------------------------------
*.cs / *.py / README.txt：UTF-8 无 BOM；build.cmd：纯 ASCII + CRLF（LF-only 的 .cmd
会被 cmd 误解析，契约 §p.2 实测教训）；pkpmjwd.uic：UTF-8 无 BOM + LF（与在用的
tgtext.uic 逐字节同构：首字节 3C 3F 78、41 个 LF，本机实测——契约附录 F.3；
注意：与"UTF-8 带 BOM"的一般惯例不同，这里以实测可用的参考件为准）。
deploy 复制的 .pmlfnc 按 GBK+CRLF 原样字节复制，不做转码。

—— 本包未部署，需要用户自己在 PDMS 停机时按第 3 节安装。——
================================================================================
