# -*- coding: utf-8 -*-
"""用 PyInstaller 把安装程序与引擎打包成单文件 exe（PKPM2PDMS v2.1.0）。

产物（``--onefile``）
--------------------
* ``<NEW>\\安装程序\\PKPM2PDMS_安装程序_v2.1.0.exe``
* ``<NEW>\\安装程序\\PKPM2PDMS_引擎_v2.1.0.exe``

内嵌资源：**不再用本目录下的 assets\\ 旧副本**，直接指向 v2.1.0 工作树（唯一真源）
----------------------------------------------------------------------------
=====================================================  ===========================  =============================
来源                                                    PyInstaller 参数              解包后位置（运行时）
=====================================================  ===========================  =============================
``<NEW>\\插件包\\pdms\\``（改名后的 PML）                 ``--add-data ...;pdms``      ``<_MEIPASS>\\pdms\\``
``<NEW>\\插件包\\docs\\``（文档）                         ``--add-data ...;docs``      ``<_MEIPASS>\\docs\\``
``<NEW>\\插件包\\engine\\*.py``                           ``--paths``                  import 路径
``<NEW>\\插件包\\engine\\secmap_extra.txt``                ``--add-data ...;.``         ``<_MEIPASS>\\secmap_extra.txt``
``<NEW>\\插件包\\engine\\section_table.csv``               ``--add-data ...;.``         ``<_MEIPASS>\\section_table.csv``
``<NEW>\\插件包\\engine\\section_table.meta.json``         ``--add-data ...;.``         ``<_MEIPASS>\\...meta.json``
``<NEW>\\图标\\pkpm2pdms.ico``                            ``--icon``                   两个 exe 的图标
=====================================================  ===========================  =============================

为什么转化表要放进解包目录**根部**：``sectionlib.py:112-114`` 用
``os.path.dirname(os.path.abspath(__file__))``（冻结后即 ``_MEIPASS``）拼出
``section_table.csv`` / ``section_table.meta.json``，所以 ``--add-data`` 的目的目录必须是 ``.``。
v1 的 ``assets\\engine`` 是 R1 时代的旧引擎（既没有 ``sectionlib.py``、也没有这两份表），
而现引擎 ``cli.py:98`` 会 ``import sectionlib`` 并调 ``load_builtin_table()``——
不内嵌就会在运行时找不到转化表。

用法
----
::

    python build_exe.py                # 真打包（会先后调用 PyInstaller 两次）
    python build_exe.py --print-cmd    # 只打印"待执行命令"与预检结果，不跑 PyInstaller

原则：只新增文件；若同名产物已存在，先"移动"成 ``.备份_<时间>`` 再生成，绝不直接删除。
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))        # <NEW>\安装程序构建
NEW_ROOT = os.path.dirname(HERE)                          # <NEW> = PKPM2PDMS_v2.1.0
PY = sys.executable

DIST = os.path.join(NEW_ROOT, '安装程序')                  # 最终 exe 落在这里
BUILD = os.path.join(HERE, 'build')                       # PyInstaller workpath
SPEC = os.path.join(HERE, 'build_spec')                   # PyInstaller specpath

# ---- 内嵌资源来源（v2.1.0 工作树里的唯一真源）
PKG = os.path.join(NEW_ROOT, '插件包')
PDMS_SRC = os.path.join(PKG, 'pdms')
DOCS_SRC = os.path.join(PKG, 'docs')
ENGINE_SRC = os.path.join(PKG, 'engine')
ICON = os.path.join(NEW_ROOT, '图标', 'pkpm2pdms.ico')

INSTALLER_NAME = 'PKPM2PDMS_安装程序_v2.1.0'
ENGINE_NAME = 'PKPM2PDMS_引擎_v2.1.0'

#: 安装程序必须内嵌、且安装时要复制进 PMLLIB 的 4 个 PML。
#: 与 ``插件包/install/install.ps1:67`` 的 ``$required`` 逐字一致 ——
#: 两条安装路线（exe 与 .ps1）装的文件清单必须相同。
REQUIRED_PML = (
    'pkpm2pdms.pmlfrm',
    'pkpm2pdmsexport.pmlfnc',
    'pkpm2pdmsdbexport.pmlfnc',
    'pkpm2pdmsrun.mac',
)

#: 引擎 exe 必须内嵌到解包目录根部的数据文件
ENGINE_DATAS = ('secmap_extra.txt', 'section_table.csv', 'section_table.meta.json')


# ---------------------------------------------------------------- 预检

def preflight():
    """返回问题清单（空 = 可以直接打包）。只读，不做任何修改。"""
    problems = []

    def need_file(path, what):
        if not os.path.isfile(path):
            problems.append('%s 不存在：%s' % (what, path))
        elif os.path.getsize(path) == 0:
            problems.append('%s 是空文件：%s' % (what, path))

    def need_dir(path, what):
        if not os.path.isdir(path):
            problems.append('%s 不是目录：%s' % (what, path))

    need_file(ICON, '图标文件')
    for d, what in ((PDMS_SRC, 'PML 源目录'), (DOCS_SRC, '文档源目录'), (ENGINE_SRC, '引擎源目录')):
        need_dir(d, what)
    for name in REQUIRED_PML:
        need_file(os.path.join(PDMS_SRC, name), '改名后的 PML')
    for name in ENGINE_DATAS:
        need_file(os.path.join(ENGINE_SRC, name), '引擎数据文件')
    for name in ('cli.py', 'gui.py', 'sectionlib.py'):
        need_file(os.path.join(ENGINE_SRC, name), '引擎模块')
    for name in ('installer_main.py', 'engine_launcher.py'):
        need_file(os.path.join(HERE, 'src', name), '本目录入口源码')
    return problems


def report_preflight(problems):
    print('预检（只读，不改任何文件）：')
    for label, path in (('图标      ', ICON), ('PML 源    ', PDMS_SRC), ('文档源    ', DOCS_SRC),
                        ('引擎源    ', ENGINE_SRC), ('输出目录  ', DIST)):
        kind = '文件' if os.path.isfile(path) else ('目录' if os.path.isdir(path) else '缺失')
        size = ''
        if kind == '文件':
            size = '  %d 字节' % os.path.getsize(path)
        elif kind == '目录':
            try:
                size = '  %d 个条目' % len(os.listdir(path))
            except OSError:
                size = ''
        print('  %s %-4s %s%s' % (label, kind, path, size))
    for title, names, base in (('待内嵌的 PML（%d 个）' % len(REQUIRED_PML), REQUIRED_PML, PDMS_SRC),
                               ('待内嵌的引擎数据（%d 个）' % len(ENGINE_DATAS), ENGINE_DATAS, ENGINE_SRC)):
        print('  ' + title + '：')
        for name in names:
            p = os.path.join(base, name)
            ok = os.path.isfile(p)
            print('     [%s] %-30s %s' % ('有' if ok else '缺', name,
                                          ('%d 字节' % os.path.getsize(p)) if ok else ''))
    print('')
    if problems:
        print('预检不通过（%d 项）—— 真打包会拒绝执行：' % len(problems))
        for item in problems:
            print('   [X] ' + item)
        print('   提示：``插件包\\pdms\\`` 的改名由 B 包负责；B 包没改完之前这一步必然挡住。')
    else:
        print('预检通过：图标、PML、文档、引擎源码与转化表都在位。')
    print('')
    return problems


# ---------------------------------------------------------------- 打包

def move_aside(path):
    """目标已存在时先改名备份（不删除）。"""
    if os.path.exists(path):
        bak = path + '.备份_' + time.strftime('%Y%m%d_%H%M%S')
        os.rename(path, bak)
        print('  已有同名产物，先改名为：%s' % os.path.basename(bak))


def cmd_one_line(cmd):
    def q(c):
        if c and (' ' in c or '\t' in c or '"' in c):
            return '"%s"' % c
        return c
    return ' '.join(q(c) for c in cmd)


def print_cmd(cmd, label):
    print('  ' + label)
    print('  单行（可直接复制进 cmd）：')
    print('    ' + cmd_one_line(cmd))
    print('  分行（便于逐项核对）：')
    print('    ' + cmd[0])
    for c in cmd[1:]:
        print('      ' + ('"%s"' % c if ' ' in c else c))
    print('')


def pyinstaller_cmd(cmd_tail):
    return [PY, '-m', 'PyInstaller', '--noconfirm', '--onefile', '--console',
            '--distpath', DIST, '--workpath', BUILD, '--specpath', SPEC] + cmd_tail


def installer_cmd_tail():
    return [
        '--name', INSTALLER_NAME,
        '--icon', ICON,                    # exe 的 PE 图标（资源管理器/任务栏）
        '--add-data', ICON + ';ico',       # 同一份 .ico 作为数据打进包 —— root.iconbitmap 要用
        '--add-data', PDMS_SRC + ';pdms',
        '--add-data', DOCS_SRC + ';docs',
        '--paths', os.path.join(HERE, 'src'),
        os.path.join(HERE, 'src', 'installer_main.py'),
    ]


def engine_cmd_tail():
    tail = ['--name', ENGINE_NAME,
            '--icon', ICON,                # exe 的 PE 图标
            '--add-data', ICON + ';ico']   # 同上：引擎窗体的 iconbitmap 要用
    for name in ENGINE_DATAS:
        tail += ['--add-data', os.path.join(ENGINE_SRC, name) + ';.']
    tail += [
        '--paths', ENGINE_SRC,
        '--paths', os.path.join(HERE, 'src'),
        os.path.join(HERE, 'src', 'engine_launcher.py'),
    ]
    return tail


def build(cmd_tail, label):
    cmd = pyinstaller_cmd(cmd_tail)
    print('')
    print('=' * 74)
    print('打包：%s' % label)
    print('=' * 74)
    print_cmd(cmd, '要执行的命令：')
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=HERE)  # 继承 stdout，方便看进度
    print('用时 %.1f 秒，退出码 %d' % (time.time() - t0, proc.returncode))
    return proc.returncode


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog='build_exe.py',
        description='PKPM2PDMS v2.1.0 —— 用 PyInstaller 打包安装程序与引擎（单文件 exe）')
    ap.add_argument('--print-cmd', '--dry-run', dest='print_cmd', action='store_true',
                    help='只打印"待执行命令"与预检结果，不运行 PyInstaller')
    args = ap.parse_args(argv)

    print('=' * 74)
    print('PKPM2PDMS v2.1.0 打包脚本')
    print('=' * 74)
    print('工作树   : ' + NEW_ROOT)
    print('构建目录 : ' + HERE)
    print('输出目录 : ' + DIST)
    print('Python   : ' + PY)
    print('')

    problems = report_preflight(preflight())

    print('待执行的两条 PyInstaller 命令：')
    print('')
    print_cmd(pyinstaller_cmd(installer_cmd_tail()),
              '[1] 安装程序（内嵌 PML + 文档 + 图标）')
    print_cmd(pyinstaller_cmd(engine_cmd_tail()),
              '[2] 引擎（内嵌引擎源码 + secmap_extra + 转化表 + 图标）')

    if args.print_cmd:
        print('（--print-cmd：只打印，未运行 PyInstaller，未写出任何 exe。）')
        if problems:
            print('注意：上面列出了 %d 项预检问题；真打包（不带 --print-cmd）会被拒绝。' % len(problems))
        return 0

    if problems:
        print('预检不通过，拒绝打包（退出码 2）。先解决上面列出的问题。')
        return 2

    for d in (DIST, BUILD, SPEC):
        os.makedirs(d, exist_ok=True)

    # ---- 1) 安装程序 exe
    target = os.path.join(DIST, INSTALLER_NAME + '.exe')
    move_aside(target)
    rc = build(installer_cmd_tail(), '安装程序（含内嵌 PML 与文档）')
    if rc != 0:
        return rc
    print('产物：%s  (%d 字节)' % (target, os.path.getsize(target)))

    # ---- 2) 引擎 exe
    target2 = os.path.join(DIST, ENGINE_NAME + '.exe')
    move_aside(target2)
    rc = build(engine_cmd_tail(), '转换引擎（tkinter 界面 + --cli 命令行）')
    if rc != 0:
        return rc
    print('产物：%s  (%d 字节)' % (target2, os.path.getsize(target2)))

    print('')
    print('全部打包完成，产物在：%s' % DIST)
    for name in sorted(os.listdir(DIST)):
        p = os.path.join(DIST, name)
        if os.path.isfile(p):
            print('   %-44s %10d 字节' % (name, os.path.getsize(p)))

    print('')
    print('后续步骤（交给构建阶段，逐条命令）：')
    print('  1) 引擎 exe 另拷一份给 .NET 原生窗体用（engine_path.txt 指向这个名字）：')
    print('       copy /y "%s" "%s"'
          % (target2, os.path.join(PKG, 'engine', 'dist', 'pkpm2pdms_engine.exe')))
    print('  2) 验收两个 exe：')
    print('       python "%s"' % os.path.join(HERE, 'test_exe.py'))
    print('  3) 与 install.ps1 的等价性沙箱自测（需要 B 包的 install.ps1 已改名）：')
    print('       python "%s"' % os.path.join(HERE, 'test_sandbox.py'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
