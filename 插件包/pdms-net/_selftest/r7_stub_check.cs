// r7_stub_check.cs - 〔R7〕不启动 PDMS 的自检桩（反射驱动真的 dist\PKPM2PDMS.dll）。
//
// 目的：在**不允许启动 PDMS** 的前提下，把 R7 改造中"与 PDMS 无关"的部分真跑一遍：
//   * SiteProber.Candidates()            —— 候选序列 = 用户 2026-09-28 定案（/PKPM2PDMS → …re99）
//   * PKPM2PDMSForm.BuildEngineArgs(...) —— site_name 键只在建模型方向出现
//   * PKPM2PDMSForm.JsonIntAfter/JsonStrAfter —— report 命名结果的最小解析
//   * PKPM2PDMSForm.ExecMacro(...) 的单引号拒绝分支 —— 不猜、不半执行
// 只调用**方法体不引用 Aveva 类型**的成员，故不需要 PDMS 库、不需要起 PDMS。
// （R4/R6 的实机接缝由测试工程师流程验证；本桩是构建期的静态/逻辑自检。）
//
// 用法（本机实测）：
//   csc 3.5 x86 → %TEMP%\_r7_selftest\_r7_stub_check.exe
//   运行目录必须能解析 dist\PKPM2PDMS.dll（桩里用绝对路径 LoadFrom）。
using System;
using System.Collections.Generic;
using System.Reflection;
using System.Text;
using System.Windows.Forms;

namespace R7StubCheck
{
    public static class Program
    {
        private static int _pass, _fail;

        private static void Check(string name, bool ok, string detail)
        {
            if (ok) { _pass++; Console.WriteLine("  [PASS] " + name + "  " + detail); }
            else { _fail++; Console.WriteLine("  [FAIL] " + name + "  " + detail); }
        }

        [STAThread]
        public static int Main(string[] argv)
        {
            Console.OutputEncoding = Encoding.UTF8;   // 控制台按 UTF-8 打印（本机 PowerShell/管道可读）
            string dll = argv.Length > 0 ? argv[0] : null;
            if (dll == null) { Console.WriteLine("usage: r7_stub_check.exe <PKPM2PDMS.dll>"); return 2; }

            Assembly asm = Assembly.LoadFrom(dll);
            Type sp = asm.GetType("PKPM2PDMS.SiteProber");
            Type fm = asm.GetType("PKPM2PDMS.PKPM2PDMSForm");
            Check("类型存在", sp != null && fm != null, "SiteProber=" + (sp != null) + " Form=" + (fm != null));
            if (sp == null || fm == null) return 2;

            // ---- ① 候选序列（SiteProber.Candidates） ----
            string[] cands = (string[])sp.GetMethod("Candidates").Invoke(null, null);
            Check("候选数 = 100", cands.Length == 100, "len=" + cands.Length);
            Check("候选首三个", cands[0] == "/PKPM2PDMS" && cands[1] == "/PKPM2PDMSre"
                && cands[2] == "/PKPM2PDMSre2", cands[0] + " / " + cands[1] + " / " + cands[2]);
            Check("候选末个 = /PKPM2PDMSre99", cands[99] == "/PKPM2PDMSre99", cands[99]);
            HashSet<string> set = new HashSet<string>(cands);
            Check("候选无重复", set.Count == cands.Length, "unique=" + set.Count);
            // 名字合法性（引擎侧 MacOptions 会拒：空白 / '~' / 内部 '/'）
            bool legal = true;
            foreach (string c in cands)
                if (c.IndexOf(' ') >= 0 || c.IndexOf('~') >= 0 || c.TrimStart('/').IndexOf('/') >= 0)
                    legal = false;
            Check("候选名无空白/~//（内部）", legal, "");

            // ---- ② 窗体实例（不碰 Aveva：只建 UI） ----
            object form = Activator.CreateInstance(fm);
            MethodInfo buildArgs = fm.GetMethod("BuildEngineArgs",
                BindingFlags.Instance | BindingFlags.NonPublic);
            FieldInfo fSite = fm.GetField("_siteName", BindingFlags.Instance | BindingFlags.NonPublic);
            FieldInfo fOut = fm.GetField("txtOut", BindingFlags.Instance | BindingFlags.NonPublic);
            FieldInfo fSrc = fm.GetField("txtSource", BindingFlags.Instance | BindingFlags.NonPublic);
            fSite.SetValue(form, "/PKPM2PDMSre");
            ((TextBox)fOut.GetValue(form)).Text = @"C:\Temp\PKPM2PDMS\import_x.mac";
            ((TextBox)fSrc.GetValue(form)).Text = @"C:\Temp\fake.jwd";

            Dictionary<string, object> a1 =
                (Dictionary<string, object>)buildArgs.Invoke(form, new object[] { "auto2pdms", "" });
            Check("auto2pdms 的 args 含 site_name", a1.ContainsKey("site_name")
                && (string)a1["site_name"] == "/PKPM2PDMSre",
                "site_name=" + (a1.ContainsKey("site_name") ? (string)a1["site_name"] : "(缺)"));
            Check("auto2pdms 的 args 含位置键 src", a1.ContainsKey("src"), "src=" + a1["src"]);
            Check("auto2pdms 的 args 含 base/angle/unit",
                a1.ContainsKey("base") && a1.ContainsKey("angle") && a1.ContainsKey("unit"),
                "base=" + string.Join(",", (string[])a1["base"]) + " unit=" + a1["unit"]);

            Dictionary<string, object> a2 =
                (Dictionary<string, object>)buildArgs.Invoke(form, new object[] { "pdms2jwd", @"C:\Temp\x.dump.txt" });
            Check("pdms2jwd 的 args **不含** site_name/base（导出方向不带建模型参数）",
                !a2.ContainsKey("site_name") && !a2.ContainsKey("base") && a2.ContainsKey("dump"),
                "keys=" + a2.Count);

            // ---- ③ report 命名结果的最小解析（JsonStrAfter / JsonIntAfter） ----
            string report =
                "{\n \"tool\": \"auto2pdms\",\n \"options\": {\n  \"project\": \"JLCJ2\",\n"
                + "  \"site_name\": \"/PKPM2PDMSre\",\n  \"base\": [0.0, 0.0, 0.0]\n },\n"
                + " \"stats\": {\n  \"used_names_count\": 37,\n  \"unnamed_count\": 512\n }\n}";
            MethodInfo ji = fm.GetMethod("JsonIntAfter", BindingFlags.Static | BindingFlags.NonPublic);
            MethodInfo js = fm.GetMethod("JsonStrAfter", BindingFlags.Static | BindingFlags.NonPublic);
            Check("JsonStrAfter(site_name)",
                (string)js.Invoke(null, new object[] { report, "site_name" }) == "/PKPM2PDMSre",
                (string)js.Invoke(null, new object[] { report, "site_name" }));
            Check("JsonIntAfter(used_names_count)",
                (string)ji.Invoke(null, new object[] { report, "used_names_count" }) == "37",
                (string)ji.Invoke(null, new object[] { report, "used_names_count" }));
            Check("JsonIntAfter(unnamed_count)",
                (string)ji.Invoke(null, new object[] { report, "unnamed_count" }) == "512", "");
            Check("Json*After 缺键返回 null",
                ji.Invoke(null, new object[] { report, "no_such_key" }) == null
                && js.Invoke(null, new object[] { report, "no_such_key" }) == null, "");

            // ---- ④ 宏路径含单引号：拒绝执行（不触 PML） ----
            MethodInfo exec = fm.GetMethod("ExecMacro", BindingFlags.Instance | BindingFlags.NonPublic);
            StringBuilder sum = new StringBuilder();
            exec.Invoke(form, new object[] { sum, @"C:\Temp\o'brien.mac" });
            string txt = sum.ToString();
            Check("含单引号的宏路径被拒绝", txt.IndexOf("单引号") >= 0 && txt.IndexOf("未执行") >= 0,
                txt.Replace("\r\n", " / ").Trim());

            // ---- ⑤ 可选 e2e：用**窗体自己**的 args 组装 + EngineRunner 真调引擎（不含 PDMS） ----
            if (argv.Length >= 4 && argv[1] == "--e2e")
                return E2E(asm, fm, form, argv[2], argv[3],
                    argv.Length >= 5 ? argv[4] : null);

            Console.WriteLine();
            Console.WriteLine("PASS=" + _pass + " FAIL=" + _fail);
            return _fail == 0 ? 0 : 1;
        }

        // e2e：<dll> --e2e <src .jwd/.pdt> <out .mac> [secmap]
        //   走窗体的 BuildEngineArgs（site_name 已设）+ EngineRunner.Run（--cli --request）
        //   + 窗体的 AppendEngineNames（读真 report 的三个键）。全程不开 PDMS、不起窗口。
        private static int E2E(Assembly asm, Type fm, object form, string src, string mac,
                               string secmap)
        {
            Console.WriteLine();
            Console.WriteLine("== e2e: 窗体 args -> EngineRunner -> 引擎 exe -> report 解析 ==");
            FieldInfo fSite = fm.GetField("_siteName", BindingFlags.Instance | BindingFlags.NonPublic);
            FieldInfo fOut = fm.GetField("txtOut", BindingFlags.Instance | BindingFlags.NonPublic);
            FieldInfo fSrc = fm.GetField("txtSource", BindingFlags.Instance | BindingFlags.NonPublic);
            FieldInfo fRep = fm.GetField("_reportPath", BindingFlags.Instance | BindingFlags.NonPublic);
            FieldInfo fErr = fm.GetField("_runError", BindingFlags.Instance | BindingFlags.NonPublic);
            string report = System.IO.Path.Combine(System.IO.Path.GetDirectoryName(mac),
                System.IO.Path.GetFileNameWithoutExtension(mac) + ".report.json");
            fSite.SetValue(form, "/PKPM2PDMSre");
            ((TextBox)fSrc.GetValue(form)).Text = src;
            ((TextBox)fOut.GetValue(form)).Text = mac;
            fRep.SetValue(form, report);
            if (!string.IsNullOrEmpty(secmap))
            {   // 源文件目录里没有"PKPM转PDMS截面匹配文件.txt"时，窗体预填的路径不存在
                // ⇒ 引擎按输入错误退出（码 2）。这里显式给一个存在的匹配文件，跑通全链路。
                FieldInfo fSec = fm.GetField("txtSecmap", BindingFlags.Instance | BindingFlags.NonPublic);
                ((TextBox)fSec.GetValue(form)).Text = secmap;
            }

            MethodInfo buildArgs = fm.GetMethod("BuildEngineArgs",
                BindingFlags.Instance | BindingFlags.NonPublic);
            Dictionary<string, object> args =
                (Dictionary<string, object>)buildArgs.Invoke(form, new object[] { "auto2pdms", "" });
            Console.WriteLine("  args keys = " + string.Join(", ", new List<string>(args.Keys).ToArray()));
            Console.WriteLine("  site_name = " + args["site_name"]);

            Type er = asm.GetType("PKPM2PDMS.EngineRunner");
            object res = er.GetMethod("Run").Invoke(null, new object[] { "auto2pdms", args });
            Type rt = res.GetType();
            int code = (int)rt.GetField("ExitCode").GetValue(res);
            string so = (string)rt.GetField("StdOut").GetValue(res);
            string se = (string)rt.GetField("StdErr").GetValue(res);
            string req = (string)rt.GetField("RequestFile").GetValue(res);
            Console.WriteLine("  exit=" + code + "  request=" + req);
            Console.WriteLine("  --- stdout ---");
            Console.WriteLine(so == null ? "(null)" : so.Trim());
            if (!string.IsNullOrEmpty(se)) { Console.WriteLine("  --- stderr ---"); Console.WriteLine(se.Trim()); }

            StringBuilder sum2 = new StringBuilder();
            fm.GetMethod("AppendEngineNames", BindingFlags.Instance | BindingFlags.NonPublic)
              .Invoke(form, new object[] { sum2 });
            Console.WriteLine("  --- 窗体 AppendEngineNames 输出 ---");
            Console.WriteLine(sum2.ToString().Trim());

            bool okReport = System.IO.File.Exists(report);
            Console.WriteLine("  report 存在 = " + okReport + " : " + report);
            Console.WriteLine();
            Console.WriteLine("E2E exit=" + code + " (期望 0)");
            return code == 0 ? 0 : 1;
        }
    }
}
