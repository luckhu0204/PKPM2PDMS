// SiteProber.cs - 〔R7〕SITE 名探测：.NET 侧执行前"直查试名"，静默、零弹窗。
//
// 用户 2026-09-28 定案的命名方案（不得偏离）：
//   SITE 名由 .NET 侧在执行前直查试出：/PKPM2PDMS → /PKPM2PDMSre → /PKPM2PDMSre2 …
//   （上限 re99，共 100 个候选），试出第一个**可用**的传给引擎（--request 的 site_name 键）。
//   引擎不改名、不做 re 逻辑；中间层/ZONE/STRU/FRMW/SBFR 名 = <SITE名>_<段>（引擎侧查重）。
//
// ---- 探测语义的出处（本机实测证据，非记忆）----
//   * Aveva.Pdms.Database.DbElement.GetElement(System.String) 是 **static public**，
//     返回 Aveva.Pdms.Database.DbElement：反射实测
//     _selftest/probe_dbelement.ps1（本包新增，只读加载 D:\AVEVA\...\Aveva.Pdms.Database.dll）
//     → "Aveva.Pdms.Database.DbElement GetElement(System.String) [static public]"。
//   * 官方文档原文（D:\AVEVA\Plant\PDMS12.1.SP4\Aveva.Pdms.Database.xml:2832-2838）：
//       <member name="M:Aveva.Pdms.Database.DbElement.GetElement(System.String)">
//         "Get an Element instance using element name. **If the element name is not known,
//          a null Element is returned.** DEPRECATED. Use MDB.FindElement(string) ..."
//     ⇒ "查不到" 的正常形态 = 返回 **null Element**（不是抛异常）。
//   * 类文档（同文件 1998-2000）："Some methods return a 'null' DbElement to denote failure.
//     A 'null' DbElement can only be tested using the 'IsNull' method."
//     ⇒ 判定必须用 IsNull（不能拿 C# null 引用当唯一判据，两种都防）。
//   * 为什么不直接用 MDB.FindElement(string)：它的官方说明是"Return the first element where
//     name matches given string key, all DBs"（同文件 36476-36481）——**没有**写明"名字不存在
//     返回什么"，且 "all DBs / first match" 的语义与"这个顶层名是否已被占用"不完全等价；
//     故按用户方案用 DbElement.GetElement(string)，并在下面用"负控 + try/catch"兜底。
//
// ---- 判定与失败方向（保守，宁可跳过可用名，绝不误用已占用名）----
//   occupied（占用）= 返回的元素非空且 !IsNull；其余（null 引用 / IsNull / 抛异常）按用户方案
//   一律视为"可用"。**保守方向**：把"拿不准"判成占用（多跳一格名字），因为误判成"可用"
//   会让宏里 `NEW SITE /已存在名` 报错 —— 而宏头是 ONERROR CONTINUE，错误不会中止宏，
//   会静默带病继续（用户红线：绝不带病出宏）。反过来最多是本次改叫 /PKPM2PDMSre，无损失。
//
// ---- 静默纪律（用户要求"静默、零弹窗"）----
//   全部返回值/异常在本类内消化：不 $P、不弹对话框；探测结论只经 PKLog（ASCII）与窗体摘要区
//   对外表达。回退机制（Q 命令）同样只在 Code 内判 Run()/Error：
//   与该类同款写法的先例 = PmlBridge.cs:28-42（CreateCommand + Run + Error 进属性，不起窗口）。
//   ★ [待实机确认] Q 命令的"名字不存在 ⇒ Run() 返回 false 且 Error 有话"这一形态未实机验证；
//     本机 PMLLIB 全目录检索 "Q /" 只命中 PML 的 `eq /...` 比较（假阳性），没有 Q 命令的用例。
//     故回退路径只在"DbElement 直查不可用"时才走，且会在摘要区如实标出实际用的机制。
using System;
using System.Collections.Generic;
using Aveva.Pdms.Database;                                   // DbElement（官方 XML 文档 + 反射实测）
using PmlCommand = Aveva.Pdms.Utilities.CommandLine.Command;  // 回退探测：与 PmlBridge 同一接缝

namespace PKPM2PDMS
{
    // 探测结论（窗体只读这个对象，不再自己扫库）
    public sealed class SiteProbeResult
    {
        public string SiteName = "";      // 试出的可用 SITE 名（含前导 '/'）；失败 = ""
        public bool Found = false;
        public string Mode = "none";      // "dbelement"（主）/ "command"（回退）/ "none"
        public string Detail = "";        // 人类可读说明（落摘要区 + addin.log）
        public int Tried = 0;             // 实际试了几个候选
        public List<string> Taken = new List<string>();    // 判为占用的候选（诊断用，不落库）
        public List<string> Notes = new List<string>();    // 过程中值得记一笔的事（如实上窗）
    }

    public static class SiteProber
    {
        // 用户定案的顶层名（无前导 '/'）与后缀上限：/PKPM2PDMS、/PKPM2PDMSre、… /PKPM2PDMSre99
        public const string BaseToken = "PKPM2PDMS";
        public const int MaxSuffix = 99;

        // 候选序列（共 100 个；顺序 = 用户方案，不得改）
        public static string[] Candidates()
        {
            List<string> l = new List<string>();
            l.Add("/" + BaseToken);
            l.Add("/" + BaseToken + "re");
            for (int i = 2; i <= MaxSuffix; i++) l.Add("/" + BaseToken + "re" + i.ToString());
            return l.ToArray();
        }

        // 主入口：试出第一个可用的 SITE 名。全程 UI 线程内完成（与窗体其它 PDMS 库动作一致）。
        public static SiteProbeResult ProbeFirstFree()
        {
            SiteProbeResult r = new SiteProbeResult();
            // 负控名：本次必然不存在（时间戳 + GUID 片段），只用于验证探测机制本身
            string ctrl = "/" + BaseToken + "_PROBE_" + CtrlToken();
            string err;
            bool occ;

            // ---- ① 主机制（DbElement 直查）的能力自检：对"必定不存在"的名字必须回"未占用" ----
            if (!DirectQuery(ctrl, out occ, out err))
            {
                r.Notes.Add("DbElement 直查不可用（" + err + "），改用回退机制");
            }
            else if (occ)
            {
                r.Notes.Add("DbElement 直查对未知名回'已占用'（与官方文档不符），改用回退机制");
            }
            else
            {
                r.Mode = "dbelement";
            }

            // ---- ② 回退机制（Q 命令）同样先过能力自检 ----
            if (r.Mode != "dbelement")
            {
                r.Mode = "command";
                if (!CommandQuery(ctrl, out occ, out err))
                {
                    return Fail(r, "两种探测都不可用：DbElement 直查失败，回退的 Q 命令也失败（"
                        + err + "）");
                }
                if (occ)
                {
                    return Fail(r, "回退探测（Q 命令）对未知名回'已占用'，无法判定名字是否可用");
                }
            }

            // ---- ③ 逐个试名 ----
            string stopErr;
            if (!Scan(r, out stopErr)) return Fail(r, stopErr);

            // ---- ④ 直查把 100 个候选全判"占用"时交叉验证一次 ----
            //     （可能是直查 API 在说谎，例如恒返回"占用"；用回退机制验最后一个候选）
            if (!r.Found && r.Mode == "dbelement")
            {
                string[] cands = Candidates();
                string last = cands[cands.Length - 1];
                if (CommandQuery(last, out occ, out err) && !occ)
                {
                    r.Notes.Add("直查判满 100 个候选，但回退机制判 " + last + " 可用 ⇒ 改用回退机制重扫");
                    r.Taken.Clear();
                    r.Tried = 0;
                    r.Mode = "command";
                    if (!Scan(r, out stopErr)) return Fail(r, stopErr);
                }
            }

            if (!r.Found)
            {
                return Fail(r, "候选名 100 个（/" + BaseToken + "…/" + BaseToken + "re"
                    + MaxSuffix.ToString() + "）全部已被占用，请在 PDMS 里为本次导入腾出一个顶层名。");
            }

            r.Detail = "可用 SITE 名 = " + r.SiteName + "（试了 " + r.Tried.ToString()
                + " 个候选，机制 = " + ModeText(r.Mode) + "）";
            return r;
        }

        // 宏执行后的**复核**（同一套直查，静默）：SITE 名现在是否真的存在。
        // 这正是"主探测机制能看见已存在元素"的一次正向对照 —— 顺带验证宏真的建了 SITE。
        public static string VerifySiteExists(string siteName)
        {
            if (string.IsNullOrEmpty(siteName)) return "未探测（未传 SITE 名）";
            bool occ;
            string err;
            if (DirectQuery(siteName, out occ, out err))
                return occ ? "存在（DbElement 直查复核命中）" : "不存在（DbElement 直查复核未命中）";
            if (CommandQuery(siteName, out occ, out err))
                return occ ? "存在（回退 Q 命令复核命中）" : "不存在（回退 Q 命令复核未命中）";
            return "无法判定（两种探测都不可用：" + err + "）";
        }

        // ---------------- 以下为内部实现 ----------------

        // 主探测：DbElement 直查。返回 false = 这次调用本身没拿到结论（异常），调用方须换机制。
        private static bool DirectQuery(string path, out bool occupied, out string err)
        {
            occupied = false;
            err = "";
            try
            {
                DbElement e = DbElement.GetElement(path);   // 官方文档：名字未知 ⇒ null Element
                occupied = (e != null) && !e.IsNull;        // IsNull 是官方指定的判空方式
                return true;
            }
            catch (Exception ex)
            {
                // 官方文档说"名字未知返回 null Element"，若实机抛异常（例如库没打开），
                // 这里也不猜 —— 如实报出，由调用方决定换机制。★[待实机确认]
                err = ex.GetType().Name + ": " + ex.Message;
                return false;
            }
        }

        // 回退探测：Q 命令（用户方案指定）。ok(Run) = 命中；Run 失败 = 名字未占用。
        // ★[待实机确认]："名字不存在 ⇒ Run() 返回 false"这一形态未实机验证（见文件头）。
        private static bool CommandQuery(string path, out bool occupied, out string err)
        {
            occupied = false;
            err = "";
            try
            {
                PmlCommand c = PmlCommand.CreateCommand("Q " + path);   // 同 PmlBridge.cs:30 的工厂
                if (c == null) { err = "CreateCommand 返回 null"; return false; }
                bool ok = c.Run();                                     // 同 PmlBridge.cs:36
                if (ok) { occupied = true; return true; }
                err = SafeError(c);                                    // 同 PmlBridge.cs:89-97
                return true;
            }
            catch (Exception ex)
            {
                err = ex.GetType().Name + ": " + ex.Message;
                return false;
            }
        }

        // 用当前机制扫一遍候选表；r.Found=true 即命中。返回 false = 中途拿不到结论（stopErr 有因）。
        private static bool Scan(SiteProbeResult r, out string stopErr)
        {
            stopErr = "";
            string[] cands = Candidates();
            for (int i = 0; i < cands.Length; i++)
            {
                bool occ;
                string err;
                r.Tried = i + 1;
                bool ok = (r.Mode == "dbelement")
                    ? DirectQuery(cands[i], out occ, out err)
                    : CommandQuery(cands[i], out occ, out err);
                if (!ok) { stopErr = "探测中断于 " + cands[i] + "：" + err; return false; }
                if (!occ)
                {
                    r.SiteName = cands[i];
                    r.Found = true;
                    return true;
                }
                r.Taken.Add(cands[i]);
            }
            return true;    // 扫完仍无可用（r.Found 保持 false）
        }

        private static SiteProbeResult Fail(SiteProbeResult r, string detail)
        {
            r.Found = false;
            r.SiteName = "";
            r.Detail = detail;
            return r;
        }

        private static string CtrlToken()
        {
            // 只用 [0-9A-F]：名字里不含空白/特殊字符，且每次运行都不同（不会撞上历史残渣）
            return DateTime.Now.ToString("HHmmss") + "_"
                + Guid.NewGuid().ToString("N").Substring(0, 4);
        }

        private static string ModeText(string mode)
        {
            if (mode == "dbelement") return "DbElement 直查";
            if (mode == "command") return "回退 Q 命令";
            return "无";
        }

        // Error 属性读取（对照 PmlBridge.SafeError：静态类型是 PdmsMessage，经 object+ToString 取文本）
        private static string SafeError(PmlCommand c)
        {
            try
            {
                object e = c.Error;
                return e == null ? "(无错误文本)" : e.ToString();
            }
            catch (Exception ex) { return "(错误文本读取失败: " + ex.Message + ")"; }
        }
    }
}
