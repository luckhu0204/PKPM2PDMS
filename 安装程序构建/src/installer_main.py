# -*- coding: utf-8 -*-
"""PKPM2PDMS导入导出 v2.1.0 —— 安装程序入口。

双击运行 = 图形界面（:mod:`installer_gui`）。
带 ``--cli`` = 无界面模式，便于脚本化 / 自检::

    PKPM2PDMS_安装程序_v2.1.0.exe --cli --action preview --pdms-root "D:\\AVEVA\\Plant\\PDMS12.1.SP4"
    PKPM2PDMS_安装程序_v2.1.0.exe --cli --action install  --pdms-root "..." [--force] [--skip-encoding-check]
    PKPM2PDMS_安装程序_v2.1.0.exe --cli --action uninstall --pdms-root "..." [--restore-backup]
"""

from __future__ import annotations

import argparse
import sys

import installer_core as core


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="PKPM2PDMS_安装程序",
        description="PKPM2PDMS导入导出 v%s —— PDMS 侧安装/卸载（默认双击是图形界面）" % core.VERSION,
    )
    p.add_argument("--cli", action="store_true", help="无界面模式（本参数出现即进入命令行）")
    p.add_argument("--action", choices=("preview", "install", "uninstall"), default="preview",
                   help="preview=只打印改动不落盘；install=安装；uninstall=卸载（缺省 preview）")
    p.add_argument("--pdms-root", default=core.DEFAULT_PDMS_ROOT,
                   help="PDMS 安装根目录（缺省 %s）" % core.DEFAULT_PDMS_ROOT)
    p.add_argument("--source-dir", default=None,
                   help="PML 源包目录；省略则用程序内嵌的副本")
    p.add_argument("--package-name", default=core.PACKAGE_NAME_DEFAULT,
                   help="装到 PMLLIB 下的子目录名（缺省 %s）" % core.PACKAGE_NAME_DEFAULT)
    p.add_argument("--force", action="store_true", help="跳过『PDMS 正在运行』检查（不推荐）")
    p.add_argument("--skip-encoding-check", action="store_true", help="跳过源包 GBK/CRLF 校验（不推荐）")
    p.add_argument("--restore-backup", action="store_true",
                   help="卸载时用最新的 design.uic.bak_pkpm2pdms_* 整份恢复")
    p.add_argument("--list-pdms", action="store_true", help="只列出探测到的 PDMS 根目录后退出")
    return p


def run_cli(argv) -> int:
    args = _build_parser().parse_args(argv)
    say = core.make_printer()

    if args.list_pdms:
        found = core.detect_pdms_roots()
        say("探测到的 PDMS 根目录（含 design.uic）共 %d 个：" % len(found))
        for path in found:
            say("  " + path)
        if not found:
            say("  （无）—— 请用 --pdms-root 手动指定")
        return core.ExitCode.OK

    try:
        if args.action == "uninstall":
            return core.do_uninstall(pdms_root=args.pdms_root,
                                     package_name=args.package_name,
                                     dry_run=False,
                                     restore_backup=args.restore_backup,
                                     report=say)
        return core.do_install(pdms_root=args.pdms_root,
                               source_dir=args.source_dir,
                               package_name=args.package_name,
                               dry_run=(args.action == "preview"),
                               force=args.force,
                               skip_encoding_check=args.skip_encoding_check,
                               report=say)
    except core.InstallError as exc:
        say("")
        say("FAIL: " + str(exc))
        say("（退出码 %d）" % exc.code)
        return exc.code
    except Exception as exc:  # noqa: BLE001
        import traceback
        say(traceback.format_exc())
        say("FAIL: 未预料的错误：" + str(exc))
        return 1


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest-gui" in argv:
        return selftest_gui()
    # 命令行专用开关：出现任何一个都走无界面模式（否则会误开向导窗口等人点）
    cli_only = {"--cli", "--list-pdms", "--action", "--pdms-root", "--source-dir",
                "--package-name", "--force", "--skip-encoding-check", "--restore-backup"}
    if any(a in cli_only for a in argv):
        if "--cli" not in argv:
            argv = ["--cli"] + argv
        return run_cli(argv)
    if any(a in ("-h", "--help", "/?") for a in argv):
        _build_parser().print_help()
        return core.ExitCode.OK
    import installer_wizard
    return installer_wizard.main(argv)


def selftest_gui() -> int:
    """无人工干预的向导界面自检：建窗体、走一遍四个页面（不执行安装），再关掉。"""
    import tkinter as tk
    import installer_wizard
    say = core.make_printer()
    try:
        root = tk.Tk()
        core.apply_window_icon(root)   # 自检也走一遍图标设置（冻结后验证 _MEIPASS 路径）
        for mode in (installer_wizard.MODE_INSTALL, installer_wizard.MODE_UNINSTALL):
            root.destroy()
            root = tk.Tk()
            wiz = installer_wizard.Wizard(root, mode=mode)
            seen = []
            # 第 1 页 → 第 2 页
            wiz.var_root.set(wiz.pdms_root or core.DEFAULT_PDMS_ROOT)
            wiz.pdms_root = wiz.var_root.get().strip()
            wiz._goto(installer_wizard.PAGE_OPTIONS)
            wiz.root.update()
            seen.append(wiz.page)
            wiz._refresh_plan()
            wiz.root.update()
            plan_len = len(wiz.txt_plan.get("1.0", "end").strip())
            # 第 3 页（不启动线程，只看界面能建起来）
            wiz._goto(installer_wizard.PAGE_PROGRESS)
            wiz.root.update()
            seen.append(wiz.page)
            wiz.prog.stop()
            # 第 4 页
            wiz._log("（自检注入的一行日志）")
            wiz._finish(0)
            wiz.root.update()
            seen.append(wiz.page)
            say("WIZARD-SELFTEST mode=%s 页面流转 %s  第2页清单 %d 字符  完成页标题=%r"
                % (mode, "→".join(seen), plan_len, wiz.lbl_done_title.cget("text")))
            if plan_len <= 0:
                say("WIZARD-SELFTEST-FAIL：第 2 页清单为空（%s）" % mode)
                return 1
        root.destroy()
        say("WIZARD-SELFTEST-OK：安装/卸载两套向导的四页均能正常建立与流转")
        return core.ExitCode.OK
    except Exception as exc:
        import traceback
        say(traceback.format_exc())
        say("WIZARD-SELFTEST-FAIL：" + str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
