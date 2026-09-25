// PKPMJWDAddin.cs - PDMS addin entry (IAddin), CLR2/.NET3.5 x86.
// 骨架照抄（本机在用样例）：D:\AI_Work\PDMS三维文字程序\TGTEXT\TGTextAddin.cs
//   —— IAddin 恰 4 成员 Name/Description/Start(ServiceManager)/Stop()
//   （反射实测：D:\AI_Work\PKPM数据解析\_recon\net_addin_feasibility.md §3.4，
//   原始证据 _recon\net\api_dump.txt:38-48）。
// 注册链（契约 CONTRACT.md §p.1/§p.3，身份冻结）：
//   程序集 PKPMJWD.dll；命名空间 PKPMJWD；IAddin.Name = "PKPMJWD"
//   （= DesignAddins.xml <string>PKPMJWD</string> 的条目文本，recon §4.1：
//   条目 = 程序集路径去 .dll）；Command Key = "PKPMJWD.OpenTools"
//   （三处一致：pkpmjwd.uic <Key> / 本文件构造器 / 菜单 Command）。
using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;
using Aveva.ApplicationFramework;                 // IAddin / ServiceManager —— 参照 TGTextAddin.cs:8
using Aveva.ApplicationFramework.Presentation;    // Command / CommandManager —— 参照 TGTextAddin.cs:9

namespace PKPMJWD
{
    public class PKPMJWDAddin : IAddin                        // 参照 TGTextAddin.cs:13
    {
        public string Name                                    // 参照 TGTextAddin.cs:15-18
        {
            get { return "PKPMJWD"; }                         // 契约 §p.1：与 DesignAddins.xml 条目一致
        }

        public string Description                             // 参照 TGTextAddin.cs:20-23
        {
            get { return "PKPM JWD import/export tools"; }
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
                cm.Commands.Add(new OpenPKPMJWDCommand());    // 参照 TGTextAddin.cs:37
                PKLog.Write("command PKPMJWD.OpenTools registered");
                PreloadPmlFunctions();
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

        // 契约 §o.4：.NET 路径下由 Add-in 在 Start() 里 $M 一次
        //   <PDMS根>\PKPMJWD\pml\pkpmjwduniquename.pmlfnc（deploy 步骤 5 安装，§p.6 表），
        // 使 !!pkpmjwdUniquename 对随后 $M 的导入宏可用（§o.2/§o.4）。
        // 【待实机确认】$M 绝对路径直跑 .pmlfnc（CONTRACT §12#28：同源证据为
        //   nucdesogwall.pmlobj:204 与 nucdesmanchor.mac:9-11）。失败仅记日志，不阻断启动。
        private static void PreloadPmlFunctions()
        {
            try
            {
                string fnc = Path.Combine(Path.Combine(PKLog.Dir(), "pml"),
                    "pkpmjwduniquename.pmlfnc");
                if (!File.Exists(fnc))
                {
                    PKLog.Write("pml function not installed, skip preload: " + fnc);
                    return;
                }
                bool ok = PmlBridge.RunPml("$M " + fnc);      // .NET->PML：recon §3.5A
                PKLog.Write("preload pkpmjwduniquename.pmlfnc: " + (ok ? "ok" : "FAILED"));
            }
            catch (Exception ex)
            {
                PKLog.Write("preload error: " + ex.Message);
            }
        }
    }

    public class OpenPKPMJWDCommand : Command                 // 参照 TGTextAddin.cs:85
    {
        private static PKPMJWDForm _form;                     // 参照 TGTextAddin.cs:87（单例窗体）

        public OpenPKPMJWDCommand()
        {
            Key = "PKPMJWD.OpenTools";                        // 参照 TGTextAddin.cs:91；= pkpmjwd.uic <Key>
            Description = "Open PKPM JWD import/export tools"; // 参照 TGTextAddin.cs:92
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
                MessageBox.Show("PKPMJWD error:\n" + ex.Message);   // 参照 TGTextAddin.cs:110
            }
        }

        // 单例 + 以 PDMS 主窗为 Owner 的非模态显示（契约 §p.3-13）
        public static void ShowForm()                         // 参照 TGTextAddin.cs:114-127
        {
            if (_form == null || _form.IsDisposed) _form = new PKPMJWDForm();   // :116
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
