# -*- coding: utf-8 -*-
"""PKPM2PDMS 转换引擎 —— exe 入口（PKPM2PDMS v2.1.0）。

双击运行 = 图形界面（与 ``python engine/gui.py`` 相同）。
带 ``--cli`` = 命令行模式，参数原样透传给 ``engine/cli.py``::

    PKPM2PDMS_引擎_v2.1.0.exe --cli jwd2pdms "xxx.jwd" --out "xxx.mac" --secmap "截面匹配文件.txt"
    PKPM2PDMS_引擎_v2.1.0.exe --cli --help

带 ``--selftest-gui`` = 无人工干预的界面自检（建窗体、跑几轮事件循环、关掉）。

〔R6 问题① 双保险的 B 半〕**带 ``--request`` 也进 CLI 模式**（不需要 ``--cli``）：
``--request <UTF-8 JSON>`` 是 .NET 原生窗体（``EngineRunner.cs``）与其它调用方的
进程调用形状，它天然是"命令行调用"，绝不能因此弹窗。少了这条兜底，只要调用方漏传
``--cli``，本启动器就会落到 ``import gui`` 分支，弹出「要填源文件路径/匹配文件路径」的
图形窗口 —— 那正是用户实机反馈的"点执行后多出来的窗口"。A 半（``EngineRunner.cs``
每次都显式加 ``--cli``）与本半互为保险，两处都有才不会再出现第二个窗口。

两个名字的关系
--------------
* 交付给用户的安装目录里叫 ``PKPM2PDMS_引擎_v2.1.0.exe``（``build_exe.py`` 的 ``ENGINE_NAME``）；
* 构建阶段会**另拷一份**到 ``插件包/engine/dist/pkpm2pdms_engine.exe``（见 ``ENGINE_EXE_NAME``），
  .NET 原生窗体的 ``engine_path.txt`` 指向的就是这个名字。
两者是同一个 exe，只是文件名不同。
"""

from __future__ import annotations

import os
import sys

#: 交付给用户的引擎 exe 名（``build_exe.py`` 的 ``ENGINE_NAME``，产物落在 <NEW>/安装程序/）
ENGINE_EXE_DELIVERED = "PKPM2PDMS_引擎_v2.1.0.exe"

#: 构建阶段会另拷一份到 插件包/engine/dist/ 的部署名
#: —— .NET 原生窗体的 engine_path.txt 指向的就是这个名字
ENGINE_EXE_NAME = "pkpm2pdms_engine.exe"

if getattr(sys, "frozen", False):
    _BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
else:
    # 源码模式：先找本目录的 assets/engine 镜像，再找新树的 插件包/engine
    _HERE = os.path.dirname(os.path.abspath(__file__))
    _CANDIDATES = [os.path.join(_HERE, "assets", "engine")]
    _P = _HERE
    for _ in range(3):
        _P = os.path.dirname(_P)
        _CANDIDATES.append(os.path.join(_P, "assets", "engine"))
        _CANDIDATES.append(os.path.join(_P, "插件包", "engine"))
    _BASE = next((c for c in _CANDIDATES if os.path.isdir(c)), _CANDIDATES[0])
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)


def selftest_gui() -> int:
    try:
        import gui
        _install_default_window_icon()
        app = gui.App()          # App 本身就是 tk.Tk
        for _ in range(8):
            app.update()
        tabs = len(app.winfo_children())
        title = app.title()
        app.destroy()
        print("GUI-SELFTEST-OK：引擎窗体建立成功，顶层子控件 %d 个，标题=%s" % (tabs, title))
        return 0
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print("GUI-SELFTEST-FAIL：" + str(exc))
        return 1


def _install_default_window_icon() -> None:
    """让引擎窗体也带上插件图标。

    引擎窗体的类是 engine/gui.py 里的 App(tk.Tk)；那个文件属 A 包范围，本启动器不改它，
    改为在 App() 实例化**之前**给 tkinter.Tk 包一层"建好就设图标"：
    gui.App.__init__ 里的 super().__init__() 会走到包装后的实现（gui.py:810）。
    任何异常都吞掉 —— 图标是装饰，不能挡住转换。
    """
    try:
        import tkinter as tk
        import installer_core as core
        path = core.icon_path()
        if not path:
            return
        original = tk.Tk.__init__

        def _patched(self, *a, **kw):
            original(self, *a, **kw)
            try:
                self.iconbitmap(path)
            except Exception:
                pass

        tk.Tk.__init__ = _patched
    except Exception:
        pass


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest-gui" in argv:
        return selftest_gui()
    # 〔R6 问题①·B 半〕CLI 模式判定 = 显式 ``--cli`` **或**出现 ``--request``。
    #   ``--request <json>`` 只有 cli.py 认（cli.py:2512 ``if raw and raw[0] == "--request"``），
    #   是纯命令行调用形状；把它判成图形模式就等于"调用方少写一个 --cli 就弹窗"。
    #   只剥 ``--cli``、``--request`` 原样透传（cli.py 自己解析它）。
    if "--cli" in argv or "--request" in argv:
        argv = [a for a in argv if a != "--cli"]
        import cli
        return cli.main(argv)
    import gui
    _install_default_window_icon()      # 必须在 gui.App() 实例化之前
    return gui.main(argv)


if __name__ == "__main__":
    sys.exit(main())
