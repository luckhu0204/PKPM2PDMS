// EngineRunner.cs - Python engine invocation (out-of-process, frozen protocol).
// 契约 CONTRACT.md §p.5（冻结）：
//   入口解析顺序：
//     1) 环境变量 PKPM2PDMS_ENGINE（绝对路径）；
//     2) <PDMS根>\PKPM2PDMS\engine_path.txt（deploy 脚本写入，内容 = 引擎入口绝对路径，
//        UTF-8 无 BOM 单行）；
//     3) <DLL 所在目录>\..\..\engine\dist\pkpm2pdms_engine.exe（工作区直跑场景）；
//        exe 不存在时试同目录回退包装器 run_engine.cmd（§p.1）。
//   调用协议（冻结）：
//     <engine_entry> --cli --request <UTF-8 JSON 文件>
//     request = { "tool": "<子命令>", "args": { …该子命令的全部参数… } }
//     ★ --cli 是 R6 修复（问题①"多余窗口"）：冻结入口 pkpm2pdms_engine.exe 是
//       engine_launcher.py 打包的**双模** exe —— 无 --cli 时默认打开 tkinter 图形界面
//       （engine_launcher.py:99-105），那正是用户点「执行」后弹出的第二个窗口。
//       .NET 侧一律按"命令行"调用，绝不触发 GUI（回退包装器 run_engine.cmd 除外，见下）。
//   退出码 = §f.2（0 成功 / 1 异常 / 2 参数输入错 / 3 E- 项）；
//   stdout = 一行摘要 + 未解析清单（UTF-8；本类按 UTF-8 读字节）。
//   执行序列 = §p.5 btnRun ①-⑤（窗体侧 PKPM2PDMSForm.RunJob 实现，本类只做 ②③）。
// 边界（§p.4 混写红线）：.NET 不直接读写 .jwd/.pdt —— 一切格式转换由引擎进程完成；
//   引擎本体（engine/dist/）由实施包 S9 交付，本类只实现 .NET 侧调用。
// 【跨包对齐点】args 的键名采用 CLI 长选项名去前导 "--"（= argparse dest，如
//   "secmap"/"out"/"base"）；engine 侧 --request 解析须按同一约定实现（§m.1 R3 注）。
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;

namespace PKPM2PDMS
{
    public class EngineResult
    {
        public int ExitCode = -1;
        public string StdOut = "";
        public string StdErr = "";
        public string RequestFile = "";
        public bool TimedOut = false;
        public bool EntryMissing = false;
    }

    public static class EngineRunner
    {
        public const int TimeoutMs = 30 * 60 * 1000;    // 契约 §p.5 ③：同步等待，超时上限 30 分钟

        // ---- 入口解析（§p.5，顺序冻结；注释即顺序） ----
        public static string ResolveEntry()
        {
            // 1) 环境变量 PKPM2PDMS_ENGINE（绝对路径）
            string env = Environment.GetEnvironmentVariable("PKPM2PDMS_ENGINE");
            if (!string.IsNullOrEmpty(env) && File.Exists(env)) return env;

            // 2) <PDMS根>\PKPM2PDMS\engine_path.txt（UTF-8 无 BOM 单行）
            string flag = Path.Combine(PKLog.Dir(), "engine_path.txt");
            if (File.Exists(flag))
            {
                try
                {
                    string p = File.ReadAllText(flag, new UTF8Encoding(false)).Trim();
                    if (p.Length > 0 && File.Exists(p)) return p;
                }
                catch (Exception ex) { PKLog.Write("engine_path.txt read failed: " + ex.Message); }
            }

            // 3) <DLL 所在目录>\..\..\engine\dist\pkpm2pdms_engine.exe；回退 run_engine.cmd（§p.1）
            string here = AppDomain.CurrentDomain.BaseDirectory;
            string dist = Path.GetFullPath(Path.Combine(here, "..\\..\\engine\\dist"));
            string exe = Path.Combine(dist, "pkpm2pdms_engine.exe");
            if (File.Exists(exe)) return exe;
            string wrap = Path.Combine(dist, "run_engine.cmd");
            if (File.Exists(wrap)) return wrap;
            return null;
        }

        // ---- ② 写 request JSON + ③ 进程调用（协议冻结 §p.5） ----
        // args：键 = CLI 长选项名去 "--"（argparse dest）；值 string / bool / string[]（--base 三元组）。
        // null / false / 空串 的键不写入（对应"缺省即省略"的 CLI 语义，§f.1/§m.1）。
        public static EngineResult Run(string tool, Dictionary<string, object> args)
        {
            EngineResult r = new EngineResult();
            string entry = ResolveEntry();
            if (entry == null)
            {
                r.EntryMissing = true;
                r.StdErr = "engine entry not found; looked at env PKPM2PDMS_ENGINE, "
                    + PKLog.Dir() + "\\engine_path.txt, <dll>\\..\\..\\engine\\dist\\pkpm2pdms_engine.exe";
                PKLog.Write("engine entry missing: " + r.StdErr);
                return r;
            }

            string dir = Path.Combine(Path.GetTempPath(), "PKPM2PDMS");
            Directory.CreateDirectory(dir);
            string req = Path.Combine(dir,
                tool + "-" + DateTime.Now.ToString("yyyyMMdd-HHmmss") + ".json");
            File.WriteAllText(req, BuildRequest(tool, args), new UTF8Encoding(false)); // §p.5 ②：UTF-8 无 BOM
            r.RequestFile = req;
            PKLog.Write("engine request: " + req + " entry=" + entry);

            ProcessStartInfo si = new ProcessStartInfo();
            si.FileName = entry;
            // R6 问题①（多余窗口）：给"启动器 exe"显式加 --cli，强制命令行模式；
            //   没有它，pkpm2pdms_engine.exe 会打开 tkinter 图形界面（engine_launcher.py:99-105）
            //   —— 就是用户看到的"要填源文件/匹配文件路径"的多余窗口。
            //   启动器自己会剥掉 --cli（engine_launcher.py:100），把 --request 交给 cli.py。
            //   回退包装器 run_engine.cmd（§p.1）**不能**加 --cli：它把参数原样转给 cli.py
            //   （run_engine.cmd 末行），而 cli.py 不认 --cli（会退出码 2）；它本身也无 GUI。
            si.Arguments = (IsShellWrapper(entry) ? "" : "--cli ") + "--request \"" + req + "\"";
            si.UseShellExecute = false;
            si.RedirectStandardOutput = true;
            si.RedirectStandardError = true;
            si.StandardOutputEncoding = Encoding.UTF8;      // §p.5：stdout 按 UTF-8 读
            si.StandardErrorEncoding = Encoding.UTF8;
            si.CreateNoWindow = true;

            try
            {
                using (Process proc = Process.Start(si))
                {
                    StringBuilder so = new StringBuilder();
                    StringBuilder se = new StringBuilder();
                    // 异步收流防止管道缓冲区写满导致死锁（摘要+未解析清单可能很长）
                    proc.OutputDataReceived += delegate(object s, DataReceivedEventArgs e)
                    { if (e.Data != null) so.AppendLine(e.Data); };
                    proc.ErrorDataReceived += delegate(object s, DataReceivedEventArgs e)
                    { if (e.Data != null) se.AppendLine(e.Data); };
                    proc.BeginOutputReadLine();
                    proc.BeginErrorReadLine();

                    if (!proc.WaitForExit(TimeoutMs))       // §p.5 ③：同步等待 + 超时 30 分钟
                    {
                        r.TimedOut = true;
                        try { proc.Kill(); } catch { }
                        PKLog.Write("engine TIMEOUT (30 min), killed");
                    }
                    proc.WaitForExit();                     // 确保异步流排空

                    r.ExitCode = proc.HasExited ? proc.ExitCode : -1;
                    r.StdOut = so.ToString();
                    r.StdErr = se.ToString();
                }
            }
            catch (Exception ex)
            {
                r.StdErr = "engine process failed: " + ex.Message;
                PKLog.Write("engine process failed: " + ex);
                return r;
            }
            PKLog.Write("engine exit=" + r.ExitCode + " req=" + req);
            return r;
        }

        // 回退入口 run_engine.cmd / *.bat 的判定（R6 问题①）：
        //   包装器把参数**原样**转给 engine/cli.py（dist\run_engine.cmd 末行），cli.py 不认 --cli；
        //   且包装器本身是纯命令行（无 tkinter），不需要 --cli。只有启动器 exe 才必须带。
        private static bool IsShellWrapper(string entry)
        {
            string ext = Path.GetExtension(entry);
            return string.Equals(ext, ".cmd", StringComparison.OrdinalIgnoreCase)
                || string.Equals(ext, ".bat", StringComparison.OrdinalIgnoreCase);
        }

        // request JSON 组装：{"tool": "...", "args": {...}}（§p.5 协议形状）
        private static string BuildRequest(string tool, Dictionary<string, object> args)
        {
            StringBuilder j = new StringBuilder();
            j.Append("{\"tool\": ").Append(JStr(tool)).Append(", \"args\": {");
            bool first = true;
            foreach (KeyValuePair<string, object> kv in args)
            {
                object v = kv.Value;
                if (v == null) continue;                    // 缺省参数：省略（CLI 语义）
                string s = v as string;
                if (s != null)
                {
                    if (s.Length == 0) continue;
                    AppendKV(j, ref first, kv.Key, JStr(s));
                    continue;
                }
                if (v is bool)
                {
                    if (!(bool)v) continue;                 // store_true：false 即不传
                    AppendKV(j, ref first, kv.Key, "true");
                    continue;
                }
                string[] arr = v as string[];
                if (arr != null)
                {
                    StringBuilder a = new StringBuilder("[");
                    for (int i = 0; i < arr.Length; i++)
                    {
                        if (i > 0) a.Append(", ");
                        a.Append(JStr(arr[i]));
                    }
                    a.Append("]");
                    AppendKV(j, ref first, kv.Key, a.ToString());
                    continue;
                }
                AppendKV(j, ref first, kv.Key, JStr(v.ToString()));
            }
            j.Append("}}");
            return j.ToString();
        }

        private static void AppendKV(StringBuilder j, ref bool first, string key, string jsonVal)
        {
            if (!first) j.Append(", ");
            first = false;
            j.Append(JStr(key)).Append(": ").Append(jsonVal);
        }

        // 最小 JSON 字符串转义（引号、反斜杠、控制字符；非 ASCII 原样 —— 文件本身 UTF-8）
        private static string JStr(string s)
        {
            StringBuilder o = new StringBuilder("\"");
            foreach (char ch in s)
            {
                if (ch == '\\' || ch == '"') { o.Append('\\'); o.Append(ch); }
                else if (ch < ' ') o.Append("\\u").Append(((int)ch).ToString("x4"));
                else o.Append(ch);
            }
            return o.Append('"').ToString();
        }
    }
}
