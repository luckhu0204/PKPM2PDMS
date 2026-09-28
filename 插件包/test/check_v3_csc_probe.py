# -*- coding: utf-8 -*-
r"""v3 工具链探针：证明契约 §p.2 的 csc 3.5 命令能编译出 CLR2/x86 的 DLL。

产物（全部留在 test/_v3_csc_check/，作为证据）：
  stub_pkpm2pdms.cs   最小 IAddin 桩（引用 AVEVA 5 件套）
  build.cmd         契约 §p.2 编译命令的原样实例
  stub_pkpm2pdms.dll  编译产物
  _csc_probe.txt    本次运行输出

只读 D:\AVEVA（/reference 只是读）；不写 G 盘、不启动 PDMS、不部署。
运行：python test\check_v3_csc_probe.py
"""
import io
import os
import shutil
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, '_v3_csc_check')
CSC = r'C:\Windows\Microsoft.NET\Framework\v3.5\csc.exe'
PDMS = r'D:\AVEVA\Plant\PDMS12.1.SP4'

STUB = r'''// stub_pkpm2pdms.cs - 契约 §p.2 编译命令的探针桩（不是交付的 Add-in 源码）
using System;
using Aveva.ApplicationFramework;
using Aveva.ApplicationFramework.Presentation;

namespace PKPM2PDMS
{
    public class StubAddin : IAddin
    {
        public string Name { get { return "PKPM2PDMS-stub"; } }
        public string Description { get { return "compile probe only"; } }
        public void Start(ServiceManager services)
        {
            CommandManager cm = (CommandManager)services.GetService(typeof(CommandManager));
            if (cm != null) cm.Commands.Add(new StubCommand());
        }
        public void Stop() { }
    }

    public class StubCommand : Command
    {
        public StubCommand()
        {
            Key = "PKPM2PDMS.StubProbe";
            Description = "probe";
        }
        public override bool IsValid { get { return true; } }
        public override void Execute() { }
    }
}
'''

BUILD = '''@echo off
rem compile probe for CONTRACT section p.2 (same shape as TGTEXT backup build.cmd)
setlocal
set CSC=C:\\Windows\\Microsoft.NET\\Framework\\v3.5\\csc.exe
set PDMS=D:\\AVEVA\\Plant\\PDMS12.1.SP4
set HERE=%~dp0

if not exist "%CSC%" set CSC=C:\\Windows\\Microsoft.NET\\Framework64\\v3.5\\csc.exe

"%CSC%" /nologo /target:library /platform:x86 /optimize+ /utf8output /codepage:65001 ^
 /warnaserror- /out:"%HERE%stub_pkpm2pdms.dll" ^
 /r:"%PDMS%\\Aveva.ApplicationFramework.dll" ^
 /r:"%PDMS%\\Aveva.ApplicationFramework.Presentation.dll" ^
 /r:"%PDMS%\\Aveva.Pdms.Database.dll" ^
 /r:"%PDMS%\\Aveva.Pdms.Utilities.dll" ^
 /r:"%PDMS%\\Aveva.Pdms.Geometry.dll" ^
 /r:System.dll /r:System.Core.dll /r:System.Drawing.dll ^
 /r:System.Windows.Forms.dll ^
 "%HERE%stub_pkpm2pdms.cs"

if errorlevel 1 (
  echo BUILD FAILED
  exit /b 1
)
echo BUILD OK: %HERE%stub_pkpm2pdms.dll
'''

PE_CLAMP = 0x4000  # PE 头在文件头；CLR 元数据根对大文件可能靠后 → 版本串全文件搜


def clr_version(path):
    """读 CLR 元数据根版本串（'v2.0.50727' / 'v4.0.30319'；全文件搜索，取最先出现）。"""
    b = open(path, 'rb').read()
    best = (None, -1)
    for tag in (b'v2.0.50727', b'v4.0.30319'):
        i = b.find(tag)
        if i >= 0 and (best[1] < 0 or i < best[1]):
            best = (tag.decode('ascii'), i)
    return best


def pe_machine_and_corflags(path):
    """PE 机器类型 + CorFlags 的 32BITREQUIRED 位（可选头 CLI 头 flags 不必解；这里给 machine + Is32Bit 判据）。"""
    b = open(path, 'rb').read(PE_CLAMP)
    if b[:2] != b'MZ':
        return None, None
    e_lfanew = int.from_bytes(b[0x3C:0x40], 'little')
    machine = int.from_bytes(b[e_lfanew + 4:e_lfanew + 6], 'little')
    return machine, None   # 0x014c = I386


def main():
    print('=== v3 csc 工具链探针 ===')
    os.makedirs(WORK, exist_ok=True)
    open(os.path.join(WORK, 'stub_pkpm2pdms.cs'), 'w', encoding='utf-8').write(STUB)
    # .cmd 必须 CRLF（LF-only 的批处理会被 cmd 误解析——本次实测教训，写进契约 §g）
    open(os.path.join(WORK, 'build.cmd'), 'w', encoding='ascii', newline='').write(
        BUILD.replace('\n', '\r\n'))

    fails = []

    def check(cond, label, detail=''):
        print('  [%s] %s %s' % ('OK' if cond else 'FAIL', label, detail))
        if not cond:
            fails.append(label)

    check(os.path.exists(CSC), 'csc 3.5 存在', CSC)
    refs = ['Aveva.ApplicationFramework.dll', 'Aveva.ApplicationFramework.Presentation.dll',
            'Aveva.Pdms.Database.dll', 'Aveva.Pdms.Utilities.dll', 'Aveva.Pdms.Geometry.dll']
    for r in refs:
        check(os.path.exists(os.path.join(PDMS, r)), '引用存在 ' + r)

    # 只读基准：编译前后 D:\AVEVA 的这 5 个 DLL + 注册文件不得变化
    watch = refs + ['DesignAddins.xml', 'DesignCustomization.xml', 'design.uic']

    def snap():
        out = {}
        for w in watch:
            p = os.path.join(PDMS, w)
            out[w] = (os.path.getsize(p), os.path.getmtime(p)) if os.path.exists(p) else None
        return out

    before = snap()
    p = subprocess.run([os.path.join(WORK, 'build.cmd')], capture_output=True,
                       cwd=WORK, shell=True)
    # csc/cmd 输出是本机代码页（GBK），按字节收再解
    out = (p.stdout or b'').decode('gbk', 'replace') + (p.stderr or b'').decode('gbk', 'replace')
    print('  --- build.cmd 输出 ---')
    for line in out.strip().splitlines():
        print('    ' + line)
    check(p.returncode == 0, 'csc 退出码 0', str(p.returncode))
    check('BUILD OK' in out, 'BUILD OK 出现')
    dll = os.path.join(WORK, 'stub_pkpm2pdms.dll')
    check(os.path.exists(dll), '产物存在 stub_pkpm2pdms.dll',
          '%d B' % os.path.getsize(dll) if os.path.exists(dll) else '')
    ver, off = clr_version(dll)
    check(ver == 'v2.0.50727', 'CLR 运行时版本 = v2.0.50727', '%s @0x%x' % (ver, off))
    machine, _ = pe_machine_and_corflags(dll)
    check(machine == 0x014c, 'PE machine = I386 (x86)', hex(machine or 0))
    after = snap()
    changed = [w for w in watch if before[w] != after[w]]
    check(not changed, 'D:\\AVEVA 被监视文件零变化（编译只读）', str(changed))

    # 顺带证明"可照抄样例"的产物也是 CLR2/x86（TGTEXT 备份里的 TGTEXT.dll）
    tg = r'D:\AI_Work\pmds三维文字程序-备份\TGTEXT\TGTEXT.dll'
    if os.path.exists(tg):
        v2, o2 = clr_version(tg)
        m2, _ = pe_machine_and_corflags(tg)
        print('  [info] TGTEXT.dll(备份) CLR=%s machine=%s size=%d' %
              (v2, hex(m2 or 0), os.path.getsize(tg)))
        check(v2 == 'v2.0.50727' and m2 == 0x014c,
              '样例 TGTEXT.dll 也是 CLR2/x86（旁证）')

    print('\nFAIL 项: %d %s' % (len(fails), fails if fails else ''))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
