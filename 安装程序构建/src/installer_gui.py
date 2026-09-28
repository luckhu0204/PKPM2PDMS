# -*- coding: utf-8 -*-
"""PKPM2PDMS导入导出 v1 —— 安装程序图形界面（tkinter，只用标准库）。

界面只做三件事：选 PDMS 根目录、选「预览 / 安装 / 卸载」、把过程中的每一行输出
原样显示出来（与包内 install.ps1 / uninstall.ps1 的输出等价，便于对照）。
真正的逻辑全在 :mod:`installer_core`，本文件不复制任何安装流程。
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import List, Optional

import installer_core as core

APP_TITLE = "PKPM2PDMS导入导出 v2.1.0 安装程序（PDMS 12.1 SP4）"
MODE_PREVIEW = "preview"
MODE_INSTALL = "install"
MODE_UNINSTALL = "uninstall"

INTRO = (
    "本程序只做 PDMS 侧的集成（与随包 install.ps1 / uninstall.ps1 等价）：\n"
    "  · 把 4 个 PML 文件装到 <PDMS根>\\PMLLIB\\pkpm2pdms\\\n"
    "  · 在 <PDMS根>\\design.uic 里追加一个「PKPM2PDMS PML」菜单项（改前先备份）\n"
    "不改 DesignAddins.xml，不删除任何文件，卸载默认是「整目录移动」而不是删除。\n"
    "转换引擎（.jwd/.pdt → PDMS 宏、PDMS → .jwd）在同目录的 PKPM2PDMS_引擎_v2.1.0.exe。"
)


class App(object):
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.q: "queue.Queue[Optional[object]]" = queue.Queue()
        self.busy = False
        self.last_code = 0

        root.title(APP_TITLE)
        root.geometry("880x680")
        root.minsize(760, 560)
        core.apply_window_icon(root)   # sys._MEIPASS 兼容（PyInstaller onefile）

        style = ttk.Style()
        try:
            style.theme_use("vista")
        except Exception:
            pass

        outer = ttk.Frame(root, padding=10)
        outer.pack(fill="both", expand=True)

        # ---- 说明
        intro = ttk.Label(outer, text=INTRO, justify="left", foreground="#333333")
        intro.pack(fill="x", pady=(0, 8))

        # ---- PDMS 根目录
        box1 = ttk.LabelFrame(outer, text=" 1) PDMS 安装根目录 ", padding=8)
        box1.pack(fill="x", pady=(0, 6))
        row = ttk.Frame(box1)
        row.pack(fill="x")
        self.var_root = tk.StringVar(value=core.DEFAULT_PDMS_ROOT)
        self.entry_root = ttk.Entry(row, textvariable=self.var_root)
        self.entry_root.pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="自动探测", width=10, command=self.on_detect).pack(side="left", padx=(6, 0))
        ttk.Button(row, text="浏览…", width=8, command=self.on_browse).pack(side="left", padx=(6, 0))
        self.lbl_scan = ttk.Label(box1, text="", foreground="#555555")
        self.lbl_scan.pack(fill="x", pady=(4, 0))

        # ---- 操作
        box2 = ttk.LabelFrame(outer, text=" 2) 要做什么 ", padding=8)
        box2.pack(fill="x", pady=(0, 6))
        self.var_mode = tk.StringVar(value=MODE_PREVIEW)
        ttk.Radiobutton(box2, text="仅预览（推荐先做一次：打印全部改动，不写任何文件）",
                        value=MODE_PREVIEW, variable=self.var_mode).grid(row=0, column=0, sticky="w", columnspan=2)
        ttk.Radiobutton(box2, text="安装（复制 PML 到 PMLLIB、备份并追加 design.uic 菜单项）",
                        value=MODE_INSTALL, variable=self.var_mode).grid(row=1, column=0, sticky="w", columnspan=2)
        ttk.Radiobutton(box2, text="卸载（移除本包菜单条目；包目录默认移动到 _removed_… 而不删除）",
                        value=MODE_UNINSTALL, variable=self.var_mode).grid(row=2, column=0, sticky="w", columnspan=2)

        self.var_restore = tk.BooleanVar(value=False)
        self.var_force = tk.BooleanVar(value=False)
        self.var_skipenc = tk.BooleanVar(value=False)
        ttk.Checkbutton(box2, text="卸载时改用「安装前备份」整份恢复 design.uic（默认是只移除本包条目）",
                        variable=self.var_restore).grid(row=3, column=0, sticky="w", columnspan=2, pady=(6, 0))
        ttk.Checkbutton(box2, text="跳过「PDMS 正在运行」检查（不推荐：PDMS 在跑时覆盖 PML 会读不到新代码）",
                        variable=self.var_force).grid(row=4, column=0, sticky="w", columnspan=2)
        ttk.Checkbutton(box2, text="跳过源包编码检查（不推荐）", variable=self.var_skipenc).grid(row=5, column=0, sticky="w", columnspan=2)

        # ---- 按钮
        box3 = ttk.Frame(outer)
        box3.pack(fill="x", pady=(2, 6))
        self.btn_run = ttk.Button(box3, text="执行", width=14, command=self.on_run)
        self.btn_run.pack(side="left")
        ttk.Button(box3, text="清空输出", width=10, command=self.clear_log).pack(side="left", padx=(6, 0))
        ttk.Button(box3, text="打开 PDMS 目录", width=16, command=self.on_open_root).pack(side="left", padx=(6, 0))
        ttk.Button(box3, text="退出", width=8, command=self.root.destroy).pack(side="right")

        # ---- 输出
        box4 = ttk.LabelFrame(outer, text=" 3) 输出 ", padding=6)
        box4.pack(fill="both", expand=True)
        self.log = ScrolledText(box4, wrap="none", height=22, font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)
        self.log.configure(state="disabled")

        self.status = ttk.Label(outer, text="就绪", foreground="#005500")
        self.status.pack(fill="x", pady=(4, 0))

        self.root.after(80, self._drain)
        self.say("PKPM2PDMS导入导出 安装程序 v%s" % core.VERSION)
        self.say("提示：先选「仅预览」看一遍完整改动清单，确认无误再选「安装」。")
        self.say("")
        self.on_detect(quiet=True)

    # ------------------------------------------------------------ 界面辅助

    def say(self, message: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def set_status(self, text: str, color: str = "#005500") -> None:
        self.status.configure(text=text, foreground=color)

    def _post(self, item: object) -> None:
        self.q.put(item)

    def _drain(self) -> None:
        try:
            while True:
                item = self.q.get_nowait()
                if item is None:
                    self.busy = False
                    self.btn_run.configure(state="normal")
                    continue
                if isinstance(item, tuple):
                    if item[0] == "status":
                        self.set_status(str(item[1]), str(item[2]) if len(item) > 2 else "#005500")
                    continue
                self.say(str(item))
        except queue.Empty:
            pass
        self.root.after(80, self._drain)

    # ------------------------------------------------------------ 事件

    def on_detect(self, quiet: bool = False) -> None:
        found = core.detect_pdms_roots()
        if found:
            self.var_root.set(found[0])
            text = "自动探测到 %d 个候选：%s" % (len(found), "；".join(found[:4]))
            if len(found) > 4:
                text += " …"
        else:
            text = "未自动探测到 PDMS 根目录（需要目录里有 design.uic）；请手动选择。"
        self.lbl_scan.configure(text=text)
        if not quiet:
            self.say("[探测] " + text)

    def on_browse(self) -> None:
        path = filedialog.askdirectory(title="选择 PDMS 安装根目录（目录里应有 design.uic）",
                                       initialdir=self.var_root.get() or core.DEFAULT_PDMS_ROOT)
        if path:
            self.var_root.set(os.path.normpath(path))

    def on_open_root(self) -> None:
        path = self.var_root.get().strip()
        if not os.path.isdir(path):
            messagebox.showwarning("目录不存在", "这个目录不存在：\n" + path)
            return
        try:
            os.startfile(path)  # noqa: S606  (Windows 专用)
        except Exception as exc:
            messagebox.showwarning("打不开", str(exc))

    def on_run(self) -> None:
        if self.busy:
            return
        mode = self.var_mode.get()
        root_path = self.var_root.get().strip()
        if not root_path:
            messagebox.showwarning("缺少参数", "请先选择 PDMS 安装根目录。")
            return
        if not os.path.isdir(root_path):
            messagebox.showwarning("目录不存在", "这个目录不存在：\n" + root_path)
            return
        uic = os.path.join(root_path, "design.uic")
        if mode != MODE_UNINSTALL and not os.path.isfile(uic):
            messagebox.showwarning("不像 PDMS 根目录",
                                   "该目录下没有 design.uic：\n" + uic + "\n\n请确认选的是 PDMS 安装根目录。")
            return
        if mode == MODE_INSTALL and not core.pdms_running():
            pass
        if mode == MODE_INSTALL and core.pdms_running() and not self.var_force.get():
            messagebox.showwarning("PDMS 正在运行",
                                   "检测到 PDMS 相关进程正在运行。\n请先完全退出 PDMS，或勾选「跳过 PDMS 正在运行检查」。")
            return
        if mode == MODE_INSTALL and not self.var_force.get():
            if not messagebox.askyesno("确认安装",
                                       "将向下面这个 PDMS 安装目录做改动：\n\n" + root_path +
                                       "\n\n· 复制 4 个 PML 到 PMLLIB\\pkpm2pdms\\\n"
                                       "· 备份并追加 design.uic 菜单项\n\n继续吗？"):
                return

        self.busy = True
        self.btn_run.configure(state="disabled")
        self.say("")
        self.say("#" * 62)
        self.say("# " + {MODE_PREVIEW: "仅预览", MODE_INSTALL: "安装", MODE_UNINSTALL: "卸载"}[mode]
                 + "  根目录 = " + root_path)
        self.say("#" * 62)
        self.set_status("正在执行…", "#884400")
        worker = threading.Thread(target=self._work, args=(mode, root_path), daemon=True)
        worker.start()

    # ------------------------------------------------------------ 后台执行

    def _work(self, mode: str, root_path: str) -> None:
        dry_run = (mode == MODE_PREVIEW)
        sink = self._post
        code = -1
        try:
            if mode == MODE_UNINSTALL:
                code = core.do_uninstall(pdms_root=root_path, dry_run=dry_run,
                                         restore_backup=self.var_restore.get(), report=sink)
            else:
                code = core.do_install(pdms_root=root_path, dry_run=dry_run,
                                       force=self.var_force.get(),
                                       skip_encoding_check=self.var_skipenc.get(),
                                       report=sink)
        except core.InstallError as exc:
            sink("")
            sink("FAIL: " + str(exc))
            sink("（退出码 %d：%s）" % (exc.code, _code_meaning(exc.code)))
            code = exc.code
        except Exception as exc:  # 兜底：不让界面线程炸掉
            import traceback
            sink(traceback.format_exc())
            sink("FAIL: 未预料的错误：" + str(exc))
            code = 1
        self.last_code = code
        sink("")
        sink("退出码 %d —— %s" % (code, _code_meaning(code)))
        if code == 0:
            if mode == MODE_PREVIEW:
                sink("预览通过。确认上面的清单没问题后，把「要做什么」改成安装再执行一次即可。")
                self._post(("status", "预览完成（未写入任何文件）", "#005500"))
            elif mode == MODE_INSTALL:
                sink("安装完成。请完全退出并重启 PDMS；进入 DESIGN 后菜单栏会出现「PKPM2PDMS PML」。")
                self._post(("status", "安装完成 —— 请重启 PDMS", "#005500"))
            else:
                sink("卸载完成。重启 PDMS 后生效。")
                self._post(("status", "卸载完成 —— 请重启 PDMS", "#005500"))
        else:
            if mode == MODE_PREVIEW:
                self._post(("status", "预览未通过（退出码 %d）" % code, "#990000"))
            else:
                self._post(("status", "失败（退出码 %d）：%s" % (code, _code_meaning(code)), "#990000"))
        self._post(None)


def _code_meaning(code: int) -> str:
    table = {
        0: "成功",
        1: "未预料的错误",
        2: "参数或路径不对（PDMS 根目录 / 源包缺失）",
        3: "检查未通过（design.uic 非合法 UTF-8 或 XML、源包编码不符）",
        4: "PDMS 正在运行（请先完全退出）",
        5: "写盘失败或校验失败（已尝试回滚，详见上方日志）",
    }
    return table.get(code, "未知")


def main(argv: Optional[List[str]] = None) -> int:
    _ = argv
    root = tk.Tk()
    try:
        root.call("tk", "scaling", 1.25)
    except Exception:
        pass
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
