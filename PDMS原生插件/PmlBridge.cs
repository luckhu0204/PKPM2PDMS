// PmlBridge.cs - .NET -> PML / PML -> .NET bridge for PKPMJWD.
// 混写边界（契约 CONTRACT.md §p.4，冻结三层职责）：.NET 只做 UI/参数/进程编排；
//   PDMS 库内一切取数与执行走 PML；本类是 .NET 调 PML 的唯一接缝。
//
// 本文件每一处 Aveva API 的出处（本机实测证据，非记忆）：
//   * 签名来源：D:\AI_Work\PKPM数据解析\_recon\net_addin_feasibility.md §3.4
//     —— Aveva.Pdms.Utilities.CommandLine.Command（抽象类）的反射实测成员：
//        static Command CreateCommand(string) / bool Run() / string Result /
//        string Error（原始证据 _recon\net\api_dump4.txt:2-27）。
//   * 用法来源：同报告 §3.5A —— .NET->PML：
//        Aveva.Pdms.Utilities.CommandLine.Command c = PmlCommand.CreateCommand("$M/...");
//        bool ok = c.Run();  string result = c.Result;
//     （recon §0.2/§3.4 另证：最小桩编译时同时 using Presentation 与 CommandLine 会报
//       error CS0104 "Command"二义 —— 故必须用 using 别名，见下方 using 行。）
//   * PML->.NET 方向（ImportDotnet 的 PML 文本）来源：同报告 §3.5B ——
//     D:\AVEVA\Plant\PDMS12.1.SP4\SolidSupport\pmllib\bopood.com\SolidSupport\mac\loadVariable
//     （213 字节，原文逐行）：import '<路径>' / handle any / endhandle /
//     using namespace '<NS>' / !!pmlValue = object PmlValue()。
using System;
using PmlCommand = Aveva.Pdms.Utilities.CommandLine.Command;   // recon §2.1：避免 CS0104 二义

namespace PKPMJWD
{
    public static class PmlBridge
    {
        // 契约 §p.4 冻结方法 1：bool RunPml(string pmlText)
        // 执行一段 PML/命令文本；成功返回 true，失败（含 PDMS 报错）返回 false。
        public static bool RunPml(string pmlText)
        {
            PmlCommand c = PmlCommand.CreateCommand(pmlText);      // recon §3.4：static 工厂
            if (c == null)
            {
                PKLog.Write("RunPml: CreateCommand returned null");
                return false;
            }
            bool ok = c.Run();                                     // recon §3.5A：bool ok = c.Run();
            if (!ok)
            {
                PKLog.Write("RunPml FAILED: [" + pmlText + "] err=" + SafeError(c));
            }
            return ok;
        }

        // 契约 §p.4 冻结方法 2：string RunPmlWithResult(string pmlText)
        // 执行并取回 Result（recon §3.5A：string result = c.Result;）；失败返回 null。
        public static string RunPmlWithResult(string pmlText)
        {
            PmlCommand c = PmlCommand.CreateCommand(pmlText);      // recon §3.4
            if (c == null)
            {
                PKLog.Write("RunPmlWithResult: CreateCommand returned null");
                return null;
            }
            if (!c.Run())                                          // recon §3.5A
            {
                PKLog.Write("RunPmlWithResult FAILED: [" + pmlText + "] err=" + SafeError(c));
                return null;
            }
            return c.Result;                                       // recon §3.5A：string result = c.Result
        }

        // 契约 §p.4 冻结方法 3：object ImportDotnet(string dllPathNoExt, string ns, string className)
        // PML->.NET 方向：把 .NET 程序集注入 PML 并实例化到 PML 全局 !!pkpmjwdImported，
        // 之后 PML 侧可直接调用该对象（recon §3.5B 的 SolidSupport 实战写法）。
        // 返回值：成功 = 所用的 PmlCommand 对象（可查 .Result）；失败 = null。
        public static object ImportDotnet(string dllPathNoExt, string ns, string className)
        {
            // 五行 PML 逐行对应 recon §3.5B 的 loadVariable 原文（import/handle/endhandle/using/object）
            string pml =
                "import '" + dllPathNoExt + "'\n" +
                "handle any\n" +
                "endhandle\n" +
                "using namespace '" + ns + "'\n" +
                "!!pkpmjwdImported = object " + className + "()";
            PmlCommand c = PmlCommand.CreateCommand(pml);          // recon §3.4
            if (c == null) return null;
            if (!c.Run())
            {
                PKLog.Write("ImportDotnet FAILED: dll=" + dllPathNoExt + " ns=" + ns
                    + " class=" + className + " err=" + SafeError(c));
                return null;
            }
            return c;
        }

        // Error 属性读取（recon §3.4：prop Error get [abstract virtual public]）；包一层防抛。
        // 编译实测补充：Error 的静态类型是 Aveva.Pdms.Utilities.Messaging.PdmsMessage
        //   （recon 的成员清单未标类型；csc 报 CS0173 得出），故经 object + ToString() 取文本。
        private static string SafeError(PmlCommand c)
        {
            try
            {
                object e = c.Error;
                return e == null ? "(no error text)" : e.ToString();
            }
            catch (Exception ex) { return "(error read failed: " + ex.Message + ")"; }
        }
    }
}
