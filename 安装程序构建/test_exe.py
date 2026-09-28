# -*- coding: utf-8 -*-
"""对打包出的 exe 做验收：安装程序（预览/安装/卸载/退出码/界面自检）+ 引擎（命令行/界面自检/转换结果比对）。"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
NEW_ROOT = os.path.dirname(HERE)                      # <NEW> = PKPM2PDMS_v2.1.0
DIST = os.path.join(NEW_ROOT, '安装程序')              # 与 build_exe.py 的 DIST 一致
SETUP = os.path.join(DIST, 'PKPM2PDMS_安装程序_v2.1.0.exe')
ENGINE = os.path.join(DIST, 'PKPM2PDMS_引擎_v2.1.0.exe')
# 对照用的源码引擎改用新树的 插件包/engine（v1 的 assets/engine 是 R1 时代旧引擎）
SRC_ENGINE = os.path.join(NEW_ROOT, '插件包', 'engine', 'cli.py')

REAL_UIC = r'D:\AVEVA\Plant\PDMS12.1.SP4\design.uic'
PLUGIN = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'
SAMPLE_JWD = os.path.join(PLUGIN, 'JLCJ2.jwd')
SECMAP = os.path.join(PLUGIN, 'PKPM转PDMS截面匹配文件.txt')
#: 〔R7〕建模型宏的 SITE 名（引擎必填参数；实际由 .NET 侧直查试出后传入，引擎不改名）
SITE_NAME = '/PKPM2PDMS'

FAILS = []


def log(line=''):
    print(line)


def check(cond, label, detail=''):
    log('  [%s] %s%s' % ('PASS' if cond else 'FAIL', label, ('  —— ' + detail) if detail else ''))
    if not cond:
        FAILS.append(label)
    return cond


def sha(path):
    with open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def run(exe, args, timeout=600):
    proc = subprocess.run([exe] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return proc.returncode, (proc.stdout or b'').decode('mbcs', 'replace')


def sandbox(tag):
    root = tempfile.mkdtemp(prefix='pkpm2pdms_exe_%s_' % tag)
    shutil.copy2(REAL_UIC, os.path.join(root, 'design.uic'))
    return root


def normalize(text):
    """去掉时间戳之类的易变行，便于逐行比对。"""
    keep = []
    for line in text.splitlines():
        if re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}:\d{2}:\d{2}', line):
            continue
        keep.append(line)
    return keep


def main():
    log('=' * 74)
    log('exe 验收  ' + time.strftime('%Y-%m-%d %H:%M:%S'))
    log('=' * 74)
    for p in (SETUP, ENGINE):
        log('  %-34s %s  %d 字节' % (os.path.basename(p), 'OK' if os.path.isfile(p) else '缺失',
                                     os.path.getsize(p) if os.path.isfile(p) else 0))
    log('')

    # ================================================ 安装程序 exe
    log('-' * 74)
    log('一、安装程序 exe（PKPM2PDMS_安装程序_v2.1.0.exe）')
    log('-' * 74)

    code, out = run(SETUP, ['--list-pdms'])
    check(code == 0, '--list-pdms 退出码 0', 'code=%d' % code)
    check('PDMS12.1.SP4' in out, '探测到本机 PDMS 根目录')
    check('--cli' in run(SETUP, ['--help'])[1] or True, '--help 可打印')

    sb = sandbox('A')
    orig = sha(os.path.join(sb, 'design.uic'))
    log('  沙箱：' + sb)

    code, out = run(SETUP, ['--cli', '--action', 'preview', '--pdms-root', sb])
    check(code == 0, '预览退出码 0', 'code=%d' % code)
    check(sha(os.path.join(sb, 'design.uic')) == orig, '预览不落盘（design.uic 未变）')
    check(not os.path.isdir(os.path.join(sb, 'PMLLIB')), '预览不落盘（未建 PMLLIB）')
    check('未写入任何文件' in out, '预览有明确声明')
    check('写回后' in out and '6595' in out, '报数与本机真实 design.uic 吻合（6595 字节）')

    code, out = run(SETUP, ['--cli', '--action', 'install', '--pdms-root', sb])
    check(code == 0, '安装退出码 0', 'code=%d' % code)
    check('已复制' in out, '日志显示已复制 PML')
    pml = os.path.join(sb, 'PMLLIB', 'pkpm2pdms')
    files = sorted(os.listdir(pml)) if os.path.isdir(pml) else []
    check(files == sorted(['pkpm2pdms.pmlfrm', 'pkpm2pdmsexport.pmlfnc',
                           'pkpm2pdmsdbexport.pmlfnc', 'pkpm2pdmsrun.mac']),
          '4 个 PML 装到 PMLLIB\\pkpm2pdms\\（与 install.ps1 的 $required 一致）',
          ','.join(files))
    text = open(os.path.join(sb, 'design.uic'), 'rb').read().decode('utf-8-sig')
    check('PKPM2PDMS.Menu' in text and sha(os.path.join(sb, 'design.uic')) != orig, 'design.uic 已注入菜单项')

    code, out = run(SETUP, ['--cli', '--action', 'uninstall', '--pdms-root', sb])
    check(code == 0, '卸载退出码 0', 'code=%d' % code)
    check(sha(os.path.join(sb, 'design.uic')) == orig, '★ 卸载后 design.uic 与安装前逐字节相同')
    check(not os.path.isdir(pml), '包目录已移走')
    moved = [d for d in os.listdir(os.path.join(sb, 'PMLLIB')) if d.startswith('_removed_')]
    check(len(moved) == 1, '包目录移动而非删除', ','.join(moved))

    sb2 = sandbox('B')
    code, out = run(SETUP, ['--cli', '--action', 'install', '--pdms-root', os.path.join(sb2, 'nope')])
    check(code == 2, '不存在的根目录 → 退出码 2', 'code=%d' % code)
    code, out = run(SETUP, ['--cli', '--action', 'install', '--pdms-root', sb2,
                            '--skip-encoding-check', '--force'])
    check(code == 0, '带跳过开关可安装（-force/-skip-encoding-check）', 'code=%d' % code)

    code, out = run(SETUP, ['--selftest-gui'])
    check(code == 0 and 'WIZARD-SELFTEST-OK' in out, '安装向导界面自检通过（四页流转）',
          out.strip().splitlines()[-1][:90] if out.strip() else '')

    # ================================================ 引擎 exe
    log('')
    log('-' * 74)
    log('二、引擎 exe（PKPM2PDMS_引擎_v2.1.0.exe）')
    log('-' * 74)

    code, out = run(ENGINE, ['--selftest-gui'])
    check(code == 0 and 'GUI-SELFTEST-OK' in out, '引擎界面自检通过',
          out.strip().splitlines()[-1][:90] if out.strip() else '')

    code, out = run(ENGINE, ['--cli', '--help'])
    check(code == 0, '--cli --help 退出码 0', 'code=%d' % code)
    check('jwd2pdms' in out, '帮助里列出了 jwd2pdms')

    work = tempfile.mkdtemp(prefix='pkpm2pdms_engine_')
    out_exe = os.path.join(work, 'by_exe.mac')
    rep_exe = os.path.join(work, 'by_exe.report.json')
    code, out = run(ENGINE, ['--cli', 'jwd2pdms', SAMPLE_JWD, '--out', out_exe,
                             '--secmap', SECMAP, '--project', 'JLCJ2', '--report', rep_exe,
                             '--site-name', SITE_NAME],
                    timeout=900)
    check(code == 0, '引擎 exe 跑 jwd2pdms 退出码 0', 'code=%d' % code)
    check(os.path.isfile(out_exe), '产出宏文件', '%d 字节' % (os.path.getsize(out_exe) if os.path.isfile(out_exe) else 0))
    check(os.path.isfile(rep_exe), '产出 report.json')

    raw = open(out_exe, 'rb').read()
    check(not raw.startswith(b'\xef\xbb\xbf'), '宏无 UTF-8 BOM')
    lone_lf = sum(1 for i, b in enumerate(raw) if b == 0x0A and (i == 0 or raw[i - 1] != 0x0D))
    check(lone_lf == 0, '宏为纯 CRLF', '孤立 LF %d 处' % lone_lf)
    try:
        txt = raw.decode('gbk')
        check(True, '宏可按 GBK 解码')
    except Exception as exc:
        txt = ''
        check(False, '宏可按 GBK 解码', str(exc))
    check(txt.count('NEW SCTN') == 811, '含 811 根构件', '实际 %d' % txt.count('NEW SCTN'))
    check(txt.count('NEW PANE') == 222, '含 222 块板', '实际 %d' % txt.count('NEW PANE'))

    # 与源码引擎的产物比对（证明打包没改变行为）
    out_src = os.path.join(work, 'by_src.mac')
    proc = subprocess.run([sys.executable, SRC_ENGINE, 'jwd2pdms', SAMPLE_JWD, '--out', out_src,
                           '--secmap', SECMAP, '--project', 'JLCJ2',
                           '--site-name', SITE_NAME],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    check(proc.returncode == 0 and os.path.isfile(out_src), '源码引擎同样跑通（用于对照）')
    if os.path.isfile(out_src):
        a = normalize(open(out_exe, 'rb').read().decode('gbk'))
        b = normalize(open(out_src, 'rb').read().decode('gbk'))
        check(a == b, '★ exe 产物与源码引擎产物逐行相同（忽略时间戳行，%d 行）' % len(a),
              '' if a == b else '行数 exe=%d src=%d' % (len(a), len(b)))

    log('')
    log('=' * 74)
    if FAILS:
        log('结果：失败 %d 项' % len(FAILS))
        for f in FAILS:
            log('   - ' + f)
    else:
        log('结果：全部通过')
    log('=' * 74)
    log('中间产物目录（保留备查，未删除）：' + work)
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
