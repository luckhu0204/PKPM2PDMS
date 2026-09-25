// EngineRunner.cs - Python engine invocation (out-of-process, frozen protocol).
// 契约 CONTRACT.md §p.5（冻结）：
//   入口解析顺序：
//     1) 环境变量 PKPMJWD_ENGINE（绝对路径）；
//     2) <PDMS根>\PKPMJWD\engine_path.txt（deploy 脚本写入，内容 = 引擎入口绝对路径，
//        UTF-8 无 BOM 单行）；
//     3) <DLL 所在目录>\..\..\engine\dist\pkpmjwd_engine.exe（工作区直跑场景）；
//        exe 不存在时试同目录回退包装器 run_engine.cmd（§p.1）。
//   调用协议（冻结）：
//     <engine_entry> --request <UTF-8 JSON 文件>
//     request = { "tool": "<子命令>", "args": { …该子命令的全部参数… } }
//   退出码 = §f.2（0 成功 / 1 异常 / 2 参数输入错 / 3 E- 项）；
//   stdout = 一行摘要 + 未解析清单（UTF-8；本类按 UTF-8 读字节）。
//   执行序列 = §p.5 btnRun ①-⑤（窗体侧 PKPMJWDForm.RunJob 实现，本类只做 ②③）。
// 边界（§p.4 混写红线）：.NET 不直接读写 .jwd/.pdt —— 一切格式转换由引擎进程完成；
//   引擎本体（engine/dist/）由实施包 S9 交付，本类只实现 .NET 侧调用。
// 【跨包对齐点】args 的键名采用 CLI 长选项名去前导 "--"（= argparse dest，如
//   "secmap"/"out"/"base"）；engine 侧 --request 解析须按同一约定实现（§m.1 R3 注）。
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;

namespace PKPMJWD
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
            // 1) 环境变量 PKPMJWD_ENGINE（绝对路径）
            string env = Environment.GetEnvironmentVariable("PKPMJWD_ENGINE");
            if (!string.IsNullOrEmpty(env) && File.Exists(env)) return env;

            // 2) <PDMS根>\PKPMJWD\engine_path.txt（UTF-8 无 BOM 单行）
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

            // 3) <DLL 所在目录>\..\..\engine\dist\pkpmjwd_engine.exe；回退 run_engine.cmd（§p.1）
            string here = AppDomain.CurrentDomain.BaseDirectory;
            string dist = Path.GetFullPath(Path.Combine(here, "..\\..\\engine\\dist"));
            string exe = Path.Combine(dist, "pkpmjwd_engine.exe");
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
                r.StdErr = "engine entry not found; looked at env PKPMJWD_ENGINE, "
                    + PKLog.Dir() + "\\engine_path.txt, <dll>\\..\\..\\engine\\dist\\pkpmjwd_engine.exe";
                PKLog.Write("engine entry missing: " + r.StdErr);
                return r;
            }

            string dir = Path.Combine(Path.GetTempPath(), "PKPMJWD");
            Directory.CreateDirectory(dir);
            string req = Path.Combine(dir,
                tool + "-" + DateTime.Now.ToString("yyyyMMdd-HHmmss") + ".json");
            File.WriteAllText(req, BuildRequest(tool, args), new UTF8Encoding(false)); // §p.5 ②：UTF-8 无 BOM
            r.RequestFile = req;
            PKLog.Write("engine request: " + req + " entry=" + entry);

            ProcessStartInfo si = new ProcessStartInfo();
            si.FileName = entry;
            si.Arguments = "--request \"" + req + "\"";     // §p.5 调用协议
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
