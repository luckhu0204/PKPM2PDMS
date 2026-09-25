// PKLog.cs - PKPMJWD logging (ASCII, millisecond timestamps).
// Log 模式照抄：D:\AI_Work\PDMS二次开发\PDMSSpecBuilder\dotnet\TGSPEC\TGSPECAddin.cs:52-63
//   （ASCII 编码、yyyy-MM-dd HH:mm:ss.fff 时间戳、追加写入、异常吞掉不抛）。
// 结构（lock + Dir/FilePath/Write）参照：D:\AI_Work\PDMS三维文字程序\TGTEXT\TGLog.cs:7-36。
// 日志落点（契约 CONTRACT.md §p.7，冻结）：<PDMS根>\PKPMJWD\addin.log。
//   <PDMS根> 取 AppDomain.CurrentDomain.BaseDirectory —— 部署后 DLL 位于 PDMS 安装根，
//   与 TGSPECAddin.cs:56（BaseDirectory\TGSPEC）与 TGLog.cs:13-14 的取法一致。
// 注意：本文件写入的是 ASCII 日志，msg 请保持 ASCII（非 ASCII 字符会被 ASCII 编码替换）。
using System;
using System.IO;

namespace PKPMJWD
{
    public static class PKLog
    {
        private static readonly object _lock = new object();   // 参照 TGLog.cs:9

        public static string Dir()
        {
            // <PDMS根>\PKPMJWD —— 参照 TGLog.cs:13-14（BaseDirectory\TGTEXT\log 的同构取法）
            return Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "PKPMJWD");
        }

        public static string FilePath()
        {
            return Path.Combine(Dir(), "addin.log");           // 契约 §p.7 冻结文件名
        }

        public static void Write(string msg)
        {
            try
            {
                lock (_lock)                                    // 参照 TGLog.cs:26
                {
                    Directory.CreateDirectory(Dir());           // 参照 TGSPECAddin.cs:57
                    File.AppendAllText(FilePath(),              // 参照 TGSPECAddin.cs:58-60
                        DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff ") + msg + "\r\n",
                        System.Text.Encoding.ASCII);
                }
            }
            catch { }                                           // 参照 TGSPECAddin.cs:62（吞异常）
        }
    }
}
