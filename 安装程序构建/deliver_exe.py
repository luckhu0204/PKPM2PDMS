# -*- coding: utf-8 -*-
"""把 exe 版安装程序归集到 v2.1.0 的交付目录（只新增，不删除；目标已存在则报告而不覆盖）。

改动说明（C 包）
----------------
【历史·刻意保留的旧称】v1 版本把产物直接写到 G 盘样本区下的
``PKPM-JWD导入导出_v1_安装程序``（G 盘是**只读样本区**，本项目硬红线），
所以本版改为写进 v2.1.0 工作树自己的 ``<NEW>\\安装程序\\exe版交付\\``；
v1 的两份验证证据（``_exe_result.txt`` / ``_sandbox_result.txt``）已随 C 包复制到
``_历史调试\\``，作为历史留档，不再随本脚本交付。
（上面这处旧名是**历史说明**，不是漏改；全树残留扫描请照 RENAME_MAP §7 例外 5 处理。）
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))          # <NEW>\安装程序构建
NEW_ROOT = os.path.dirname(HERE)                            # <NEW>
BUILD_DIST = os.path.join(NEW_ROOT, '安装程序')              # build_exe.py 的 DIST
TARGET = os.path.join(BUILD_DIST, 'exe版交付')

ITEMS = [
    (os.path.join(BUILD_DIST, 'PKPM2PDMS_安装程序_v2.1.0.exe'), 'PKPM2PDMS_安装程序_v2.1.0.exe'),
    (os.path.join(BUILD_DIST, 'PKPM2PDMS_引擎_v2.1.0.exe'), 'PKPM2PDMS_引擎_v2.1.0.exe'),
    (os.path.join(HERE, '安装说明.txt'), '安装说明.txt'),
    (os.path.join(HERE, 'src', 'installer_core.py'), os.path.join('源码', 'installer_core.py')),
    (os.path.join(HERE, 'src', 'installer_gui.py'), os.path.join('源码', 'installer_gui.py')),
    (os.path.join(HERE, 'src', 'installer_wizard.py'), os.path.join('源码', 'installer_wizard.py')),
    (os.path.join(HERE, 'src', 'installer_main.py'), os.path.join('源码', 'installer_main.py')),
    (os.path.join(HERE, 'src', 'engine_launcher.py'), os.path.join('源码', 'engine_launcher.py')),
    (os.path.join(HERE, 'build_exe.py'), os.path.join('源码', 'build_exe.py')),
    (os.path.join(HERE, 'test_sandbox.py'), os.path.join('源码', 'test_sandbox.py')),
    (os.path.join(HERE, 'test_exe.py'), os.path.join('源码', 'test_exe.py')),
]


def sha(path):
    with open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main():
    print('=' * 70)
    print('交付 exe 版安装程序（PKPM2PDMS v2.1.0）')
    print('=' * 70)
    print('目标目录：' + TARGET)

    missing = [src for src, _ in ITEMS if not os.path.isfile(src)]
    if missing:
        print('')
        print('[中止] 以下要交付的文件还没生成（先跑 build_exe.py）：')
        for m in missing:
            print('   ' + m)
        return 3

    if os.path.isdir(TARGET):
        existing = []
        for root, _dirs, files in os.walk(TARGET):
            for name in files:
                existing.append(os.path.relpath(os.path.join(root, name), TARGET))
        if existing:
            print('')
            print('[中止] 目标目录已存在且非空（%d 个文件），不覆盖，请人工判断：' % len(existing))
            for name in sorted(existing)[:40]:
                print('   ' + name)
            return 2
    else:
        os.makedirs(TARGET)
        print('已创建目录 ' + TARGET)

    print('')
    ok = True
    for src, rel in ITEMS:
        dst = os.path.join(TARGET, rel)
        parent = os.path.dirname(dst)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        shutil.copy2(src, dst)
        same = (sha(src) == sha(dst))
        ok = ok and same
        print('  %-6s %-46s %10d 字节  sha %s' % ('OK' if same else '不符', rel,
                                                  os.path.getsize(dst), sha(dst)[:16]))
    print('')
    print('逐文件 SHA256 校验：%s' % ('全部一致' if ok else '有不一致，请检查'))
    total = sum(os.path.getsize(os.path.join(TARGET, rel)) for _src, rel in ITEMS)
    print('交付目录合计 %d 个文件，%d 字节' % (len(ITEMS), total))
    print('交付位置：' + TARGET)
    return 0 if ok else 4


if __name__ == '__main__':
    sys.exit(main())
