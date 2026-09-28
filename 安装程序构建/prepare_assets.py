# -*- coding: utf-8 -*-
"""把 v2.1.0 工作树里的 PML / 引擎 / 文档镜像一份到本目录的 assets\\ （只复制，不删除）。

**本脚本现在是可选的对照工具，不是构建的必经步骤。**
``build_exe.py`` 已经直接内嵌 ``<NEW>\\插件包\\{pdms,docs,engine}``（唯一真源），
不再读本目录的 ``assets\\``；跑本脚本只是为了在构建目录里留一份便于离线核对的镜像。

改动说明（C 包）：【历史·刻意保留的旧称】v1 版本的源是 G 盘上的旧交付树
``PKPM-JWD导入导出_v1_已验收_20260924``（G 盘是**只读样本区**，本项目硬红线），
本版改为读 v2.1.0 工作树自己的 ``插件包\\``。
（这处旧名是**历史说明**，不是漏改；全树残留扫描请照 RENAME_MAP §7 例外 5 处理。）
"""

from __future__ import annotations

import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))          # <NEW>\安装程序构建
NEW_ROOT = os.path.dirname(HERE)                            # <NEW>
PKG = os.path.join(NEW_ROOT, '插件包')

PDMS_DST = os.path.join(HERE, 'assets', 'pdms')
ENGINE_DST = os.path.join(HERE, 'assets', 'engine')
DOC_DST = os.path.join(HERE, 'assets', 'docs')

PDMS_NAMES = ('pkpm2pdms.pmlfrm', 'pkpm2pdmsexport.pmlfnc', 'pkpm2pdmsdbexport.pmlfnc',
              'pkpm2pdmsrun.mac', 'pkpm2pdmsuniquename.pmlfnc', 'README.txt')
DOC_NAMES = ('使用说明.md', '格式规范_JWD.md', '截面映射说明.md', '交付清单.md', '交付报告.md')


def copy_file(src, dst, label):
    shutil.copy2(src, dst)
    print('  %-10s %-30s %9d 字节 -> %s'
          % (label, os.path.basename(dst), os.path.getsize(dst), dst))


def main() -> int:
    for d in (PDMS_DST, ENGINE_DST, DOC_DST):
        os.makedirs(d, exist_ok=True)

    print('镜像源：%s' % PKG)
    print('pdms\\ :')
    for name in PDMS_NAMES:
        src = os.path.join(PKG, 'pdms', name)
        if os.path.isfile(src):
            copy_file(src, os.path.join(PDMS_DST, name), 'pdms')
        else:
            print('  [缺] %s' % src)

    # 引擎 exe 用：整个 engine 目录（纯 Python，PyInstaller 会打成 exe）
    print('engine\\ :')
    engine_src = os.path.join(PKG, 'engine')
    for name in sorted(os.listdir(engine_src)):
        src = os.path.join(engine_src, name)
        if os.path.isfile(src):
            copy_file(src, os.path.join(ENGINE_DST, name), 'engine')

    print('docs\\ :')
    for name in DOC_NAMES:
        src = os.path.join(PKG, 'docs', name)
        if os.path.isfile(src):
            copy_file(src, os.path.join(DOC_DST, name), 'docs')
        else:
            print('  [缺] %s' % src)

    print('')
    print('镜像完成：%s' % HERE)
    print('注意：build_exe.py 不读 assets\\；内嵌的是 插件包\\ 下的原件。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
