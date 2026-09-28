// PKPM2PDMSAddin.cs - PDMS addin entry (IAddin), CLR2/.NET3.5 x86.
// 骨架照抄（本机在用样例）：D:\AI_Work\PDMS三维文字程序\TGTEXT\TGTextAddin.cs
//   —— IAddin 恰 4 成员 Name/Description/Start(ServiceManager)/Stop()
//   （反射实测：D:\AI_Work\PKPM数据解析\_recon\net_addin_feasibility.md §3.4，
//   原始证据 _recon\net\api_dump.txt:38-48）。
// 注册链（契约 CONTRACT.md §p.1/§p.3，身份冻结）：
//   程序集 PKPM2PDMS.dll；命名空间 PKPM2PDMS；IAddin.Name = "PKPM2PDMS"
//   （= DesignAddins.xml <string>PKPM2PDMS</string> 的条目文本，recon §4.1：
//   条目 = 程序集路径去 .dll）；Command Key = "PKPM2PDMS.OpenTools"
//   （三处一致：pkpm2pdms.uic <Key> / 本文件构造器 / 菜单 Command）。
using System;
using System.Diagnostics;
using System.Windows.Forms;
using Aveva.ApplicationFramework;                 // IAddin / ServiceManager —— 参照 TGTextAddin.cs:8
using Aveva.ApplicationFramework.Presentation;    // Command / CommandManager —— 参照 TGTextAddin.cs:9

namespace PKPM2PDMS
{
    public class PKPM2PDMSAddin : IAddin                        // 参照 TGTextAddin.cs:13
    {
        public string Name                                    // 参照 TGTextAddin.cs:15-18
        {
            get { return "PKPM2PDMS"; }                         // 契约 §p.1：与 DesignAddins.xml 条目一致
        }

        public string Description                             // 参照 TGTextAddin.cs:20-23
        {
            get { return "PKPM2PDMS import/export tools"; }
        }

        public void Start(ServiceManager services)            // 参照 TGTextAddin.cs:25（签名 Start(ServiceManager)）
        {
            PKLog.Write("addin starting, pid=" + Process.GetCurrentProcess().Id);   // 参照 TGTextAddin.cs:27
            try
            {
                // 本机验证过的取 CommandManager 方式：从 ServiceManager 拿（同 TGTextAddin.cs:30-31）
                CommandManager cm = (CommandManager)services.GetService(
                    typeof(CommandManager));
                if (cm == null)                               // 参照 TGTextAddin.cs:32-36
                {
                    PKLog.Write("no CommandManager service");
                    return;
                }
                cm.Commands.Add(new OpenPKPM2PDMSCommand());    // 参照 TGTextAddin.cs:37
                PKLog.Write("command PKPM2PDMS.OpenTools registered");
                // 〔R7〕这里**不做任何 PML 预载**：唯一化 + 运行入口那一族 PML 函数已整体退役
                //   （不再部署、不再被任何代码引用，退役清单见 deploy_pkpm2pdms.py 的 RETIRED_PML）。
                //   R7 的职责分工：SITE 名由窗体的 SiteProber 执行前直查试出（静默）；
                //   中间层名字由引擎在生成期查重；宏里不再出现任何 !!pkpm2pdms* 调用。
                //   历史教训（留证备查）：本处曾发 `$M <…>.pmlfnc` 预载，在 PDMS 12.1 SP4 下
                //   每次启动都在 <PDMS根>\PKPM2PDMS\addin.log 留一条 "… FAILED"
                //   （(46,80) PML: Invalid syntax）—— .pmlfnc 只按「文件名（忽略大小写）= 函数名」
                //   由 PMLLIB 自动加载，$M 文件形式无效。现在没有预载，故也不会再留假失败。
                PKLog.Write("no PML preload at addin start (retired family; site name probed on run)");
            }
            catch (Exception ex)
            {
                PKLog.Write("start error: " + ex);            // 参照 TGTextAddin.cs:73-76
            }
        }

        public void Stop()                                    // 参照 TGTextAddin.cs:79-82
        {
            PKLog.Write("addin stopped");
        }
    }

    public class OpenPKPM2PDMSCommand : Command                 // 参照 TGTextAddin.cs:85
    {
        private static PKPM2PDMSForm _form;                     // 参照 TGTextAddin.cs:87（单例窗体）

        public OpenPKPM2PDMSCommand()
        {
            Key = "PKPM2PDMS.OpenTools";                        // 参照 TGTextAddin.cs:91；= pkpm2pdms.uic <Key>
            Description = "Open PKPM2PDMS import/export tools"; // 参照 TGTextAddin.cs:92
        }

        public override bool IsValid                          // 参照 TGTextAddin.cs:95-98
        {
            get { return true; }
        }

        public override void Execute()                        // 参照 TGTextAddin.cs:100-112
        {
            try
            {
                PKLog.Write("command execute");               // 参照 TGTextAddin.cs:104
                ShowForm();
            }
            catch (Exception ex)
            {
                PKLog.Write("execute error: " + ex);          // 参照 TGTextAddin.cs:109
                MessageBox.Show("PKPM2PDMS error:\n" + ex.Message);   // 参照 TGTextAddin.cs:110
            }
        }

        // 单例 + 以 PDMS 主窗为 Owner 的非模态显示（契约 §p.3-13）
        public static void ShowForm()                         // 参照 TGTextAddin.cs:114-127
        {
            if (_form == null || _form.IsDisposed) _form = new PKPM2PDMSForm();   // :116
            if (!_form.Visible)                               // :117
            {
                // 由 PDMS 主窗口"拥有"本窗体：始终浮在 PDMS 之上、点击正常置前（:119-122 注释同源）
                IntPtr h = Process.GetCurrentProcess().MainWindowHandle;   // :121
                if (h != IntPtr.Zero) _form.Show(new WindowWrapper(h));    // :122（非模态 Show，非 ShowDialog）
                else _form.Show();
            }
            _form.Activate();                                 // :125
            _form.BringToFront();                             // :126
        }
    }

    // minimal IWin32Window so a foreign (PDMS) window can own our form   // TGTextAddin.cs:130 原文注释
    internal class WindowWrapper : System.Windows.Forms.IWin32Window   // 参照 TGTextAddin.cs:131-136
    {
        private readonly IntPtr _handle;
        public WindowWrapper(IntPtr handle) { _handle = handle; }
        public IntPtr Handle { get { return _handle; } }
    }
}
