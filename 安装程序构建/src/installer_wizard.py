# -*- coding: utf-8 -*-
"""PKPM2PDMS导入导出 v1 —— 向导式安装界面（Next / Next / Finish）。

像 Windows 常规软件安装包那样分步走：

  第 1 页  欢迎        —— 介绍装什么、往哪装；PDMS 根目录在这里选（自动探测）
  第 2 页  许可与选项  —— 展示要写入的菜单项；可选"先预览不改盘"
  第 3 页  安装        —— 进度条 + 逐行日志；实际动作在这页跑
  第 4 页  完成        —— 成功/失败结论 + 下一步指引（重启 PDMS 等）

安装与卸载共用同一套向导：第 3 页顶部是「安装」还是「卸载」的标签，
右下的主按钮在安装时叫「安装」，卸载时叫「卸载」。

逻辑全在 :mod:`installer_core`（与包内 install.ps1 / uninstall.ps1 等价），
本文件只负责界面与流程编排，不复制任何安装逻辑。
"""

from __future__ import annotations

import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import List, Optional

import installer_core as core

APP_TITLE = "安装 PKPM2PDMS导入导出 v2.1.0"
SUBTITLE = "PKPM ↔ AVEVA PDMS 12.1 SP4 导入导出插件（v2.1.0）"

PAGE_WELCOME = "welcome"
PAGE_OPTIONS = "options"
PAGE_PROGRESS = "progress"
PAGE_DONE = "done"

MODE_INSTALL = "install"
MODE_UNINSTALL = "uninstall"

PAGE_TITLES = {
    PAGE_WELCOME: "欢迎",
    PAGE_OPTIONS: "安装选项",
    PAGE_PROGRESS: "正在安装",
    PAGE_DONE: "完成",
}


class Wizard(object):
    def __init__(self, root: tk.Tk, mode: str = MODE_INSTALL) -> None:
        self.root = root
        self.mode = mode
        self.q: "queue.Queue[object]" = queue.Queue()
        self.page = PAGE_WELCOME
        self.busy = False
        self.result_code = -1
        self.cancelled = False
        self.pdms_root = ""
        self.dry_run = False

        root.title(APP_TITLE)
        root.geometry("700x540")
        root.minsize(660, 520)
        core.apply_window_icon(root)   # sys._MEIPASS 兼容（PyInstaller onefile）
        try:
            root.call("tk", "scaling", 1.2)
        except Exception:
            pass
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except Exception:
            pass

        self._build()
        self._goto(PAGE_WELCOME)
        self.root.after(80, self._drain)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------------------------------------------------------------- 界面骨架

    def _build(self) -> None:
        # 顶部标题条
        head = tk.Frame(self.root, bg="#0a3d62", height=64)
        head.pack(fill="x")
        head.pack_propagate(False)
        tk.Label(head, text="PKPM2PDMS导入导出 v2.1.0", bg="#0a3d62", fg="white",
                 font=("Microsoft YaHei UI", 13, "bold")).pack(anchor="w", padx=18, pady=(10, 0))
        tk.Label(head, text=SUBTITLE, bg="#0a3d62", fg="#b8d4e8",
                 font=("Microsoft YaHei UI", 9)).pack(anchor="w", padx=18)

        body = ttk.Frame(self.root, padding=(16, 12, 16, 0))
        body.pack(fill="both", expand=True)
        self.pages: dict = {}
        for key in (PAGE_WELCOME, PAGE_OPTIONS, PAGE_PROGRESS, PAGE_DONE):
            frame = ttk.Frame(body)
            frame.pack(fill="both", expand=True)
            self.pages[key] = frame
        self._build_welcome()
        self._build_options()
        self._build_progress()
        self._build_done()

        # 底部按钮条
        foot = ttk.Frame(self.root, padding=(16, 8, 16, 12))
        foot.pack(fill="x")
        self.btn_back = ttk.Button(foot, text="上一步", width=10, command=self._on_back)
        self.btn_back.pack(side="left")
        self.btn_next = ttk.Button(foot, text="下一步", width=12, command=self._on_next)
        self.btn_next.pack(side="right")
        self.btn_cancel = ttk.Button(foot, text="取消", width=10, command=self._on_cancel)
        self.btn_cancel.pack(side="right", padx=(0, 8))

    def _page_title(self, parent, text, sub=""):
        ttk.Label(parent, text=text, font=("Microsoft YaHei UI", 15, "bold")).pack(anchor="w")
        if sub:
            ttk.Label(parent, text=sub, foreground="#555555",
                      font=("Microsoft YaHei UI", 9)).pack(anchor="w", pady=(2, 10))

    def _build_welcome(self) -> None:
        f = self.pages[PAGE_WELCOME]
        verb = "安装" if self.mode == MODE_INSTALL else "卸载"
        self._page_title(f, "欢迎使用 PKPM2PDMS导入导出 v2.1.0 %s程序" % verb,
                         "本程序只处理 PDMS 侧集成，转换引擎另有 PKPM2PDMS_引擎_v2.1.0.exe。")

        box = ttk.LabelFrame(f, text=" 本程序会做什么 ", padding=10)
        box.pack(fill="x", pady=(0, 10))
        if self.mode == MODE_INSTALL:
            lines = [
                "·  把 4 个 PML 文件复制到  <PDMS根>\\PMLLIB\\pkpm2pdms\\",
                "·  先备份 design.uic，再往里追加一个「PKPM2PDMS PML」菜单项",
                "备份文件名形如 design.uic.bak_pkpm2pdms_<日期时间>，随时可回滚。",
            ]
        else:
            lines = [
                "·  只移除本程序追加的三处菜单条目（design.uic 恢复到与安装前逐字节相同）",
                "·  PML 包目录整体「移动」到 PMLLIB\\_removed_pkpm2pdms_<时间>，不删除文件",
            ]
        for i, line in enumerate(lines):
            ttk.Label(box, text=line, font=("Microsoft YaHei UI", 9),
                      justify="left").grid(row=i, column=0, sticky="w", pady=1)

        warn = ttk.Label(f, text="不删除任何文件；不改 DesignAddins.xml；不动 pml.index；不动任何样本原件。",
                         foreground="#1a5fb4", font=("Microsoft YaHei UI", 9))
        warn.pack(anchor="w", pady=(0, 12))

        box2 = ttk.LabelFrame(f, text=" PDMS 安装位置 ", padding=10)
        box2.pack(fill="x")
        row = ttk.Frame(box2)
        row.pack(fill="x")
        self.var_root = tk.StringVar(value=core.DEFAULT_PDMS_ROOT)
        ttk.Entry(row, textvariable=self.var_root).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="自动探测", width=10, command=self._on_detect).pack(side="left", padx=(6, 0))
        ttk.Button(row, text="浏览…", width=8, command=self._on_browse).pack(side="left", padx=(6, 0))
        self.lbl_detect = ttk.Label(box2, text="", foreground="#555555", font=("Microsoft YaHei UI", 8))
        self.lbl_detect.pack(anchor="w", pady=(5, 0))
        ttk.Label(box2, text="判断标准：该目录下有 design.uic。", foreground="#777777",
                  font=("Microsoft YaHei UI", 8)).pack(anchor="w")

    def _build_options(self) -> None:
        f = self.pages[PAGE_OPTIONS]
        if self.mode == MODE_INSTALL:
            self._page_title(f, "安装选项", "确认要写入的内容；默认建议先做一次「仅预览」。")
        else:
            self._page_title(f, "卸载选项", "确认要移除的内容。")

        box = ttk.LabelFrame(f, text=" 将要写入的内容 ", padding=10)
        box.pack(fill="both", expand=True)
        self.txt_plan = ScrolledText(box, wrap="word", height=9, font=("Consolas", 9),
                                     background="#fbfbfb", relief="flat")
        self.txt_plan.pack(fill="both", expand=True)
        self.txt_plan.configure(state="disabled")

        if self.mode == MODE_INSTALL:
            self.var_dry = tk.BooleanVar(value=True)
            ttk.Checkbutton(f, text="仅预览（打印全部改动，不写入任何文件）—— 建议第一次先勾这个",
                            variable=self.var_dry).pack(anchor="w", pady=(10, 0))
            self.var_restore = tk.BooleanVar(value=False)
            ttk.Checkbutton(f, text="卸载时用「安装前备份」整份恢复 design.uic（默认是只移除本程序追加的条目）",
                            variable=self.var_restore).pack(anchor="w")
            self.var_force = tk.BooleanVar(value=False)
            ttk.Checkbutton(f, text="跳过「PDMS 正在运行」检查（不推荐）",
                            variable=self.var_force).pack(anchor="w")
        else:
            self.var_dry = tk.BooleanVar(value=True)
            ttk.Checkbutton(f, text="仅预览（打印全部改动，不写入任何文件）",
                            variable=self.var_dry).pack(anchor="w", pady=(10, 0))
            self.var_restore = tk.BooleanVar(value=False)
            ttk.Checkbutton(f, text="用「安装前备份」整份恢复 design.uic",
                            variable=self.var_restore).pack(anchor="w")
            self.var_force = tk.BooleanVar(value=False)

    def _build_progress(self) -> None:
        f = self.pages[PAGE_PROGRESS]
        self.lbl_stage = ttk.Label(f, text="正在准备…", font=("Microsoft YaHei UI", 11, "bold"))
        self.lbl_stage.pack(anchor="w")
        self.prog = ttk.Progressbar(f, mode="indeterminate", length=660)
        self.prog.pack(fill="x", pady=(8, 8))
        self.lbl_status = ttk.Label(f, text="", foreground="#555555", font=("Microsoft YaHei UI", 9))
        self.lbl_status.pack(anchor="w", pady=(0, 8))
        self.txt_log = ScrolledText(f, wrap="none", height=14, font=("Consolas", 9))
        self.txt_log.pack(fill="both", expand=True)
        self.txt_log.configure(state="disabled")

    def _build_done(self) -> None:
        f = self.pages[PAGE_DONE]
        self.lbl_done_title = ttk.Label(f, text="", font=("Microsoft YaHei UI", 15, "bold"))
        self.lbl_done_title.pack(anchor="w")
        self.lbl_done_sub = ttk.Label(f, text="", foreground="#555555",
                                      font=("Microsoft YaHei UI", 9), wraplength=640, justify="left")
        self.lbl_done_sub.pack(anchor="w", pady=(6, 12))
        box = ttk.LabelFrame(f, text=" 日志 ", padding=6)
        box.pack(fill="both", expand=True)
        self.txt_done = ScrolledText(box, wrap="word", height=13, font=("Consolas", 8))
        self.txt_done.pack(fill="both", expand=True)
        self.txt_done.configure(state="disabled")

    # ---------------------------------------------------------------- 页面切换

    def _goto(self, page: str) -> None:
        self.page = page
        for key, frame in self.pages.items():
            if key == page:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

        verb = "安装" if self.mode == MODE_INSTALL else "卸载"
        is_last = (page == PAGE_DONE)
        if page == PAGE_WELCOME:
            self.btn_back.configure(state="disabled")
            self.btn_next.configure(state="normal", text="下一步")
            self.btn_cancel.configure(state="normal", text="退出")
            self._on_detect(quiet=True)
        elif page == PAGE_OPTIONS:
            self.btn_back.configure(state="normal")
            self.btn_next.configure(
                state="normal",
                text=("完成" if (self.mode == MODE_UNINSTALL and self.var_dry.get())
                      else ("下一步" if self.var_dry.get() else verb)))
            self.btn_cancel.configure(state="normal", text="上一步")
            self._refresh_plan()
        elif page == PAGE_PROGRESS:
            self.btn_back.configure(state="disabled")
            self.btn_next.configure(state="disabled")
            self.btn_cancel.configure(state="normal", text="取消")
            self.lbl_stage.configure(text="正在%s…" % verb)
            self.prog.start(12)
        else:
            self.btn_back.configure(state="disabled")
            self.btn_next.configure(state="normal", text="完成")
            self.btn_cancel.configure(state="normal", text="关闭")

    def _on_next(self) -> None:
        if self.page == PAGE_WELCOME:
            root = self.var_root.get().strip()
            if not root or not os.path.isdir(root):
                messagebox.showwarning("请选择安装位置", "这个目录不存在：\n" + (root or "(空)"))
                return
            if not os.path.isfile(os.path.join(root, "design.uic")):
                if not messagebox.askyesno("不像 PDMS 根目录",
                                           "该目录下没有 design.uic：\n%s\n\n仍要继续吗？" % root):
                    return
            self.pdms_root = root
            self._goto(PAGE_OPTIONS)
            return

        if self.page == PAGE_OPTIONS:
            self.dry_run = self.var_dry.get()
            if not self.dry_run and self.mode == MODE_INSTALL:
                running = core.pdms_running()
                if running and not self.var_force.get():
                    messagebox.showwarning("PDMS 正在运行",
                                           "检测到 PDMS 相关进程正在运行：\n%s\n\n"
                                           "请先完全退出 PDMS 再安装。" % ", ".join(running))
                    return
                if not messagebox.askyesno("确认%s" % verb_text(self.mode),
                                           "即将向下面这个 PDMS 安装目录写入：\n\n%s\n\n继续吗？" % self.pdms_root):
                    return
            self._goto(PAGE_PROGRESS)
            self._log("")
            self._log("#" * 60)
            self._log("# %s  目标 = %s%s" % (verb_text(self.mode), self.pdms_root,
                                            "（仅预览）" if self.dry_run else ""))
            self._log("#" * 60)
            self._start()
            return

        if self.page == PAGE_DONE:
            self.root.destroy()

    def _on_back(self) -> None:
        if self.page == PAGE_OPTIONS:
            self._goto(PAGE_WELCOME)
        elif self.page == PAGE_PROGRESS:
            pass  # 安装中不允许回退
        elif self.page == PAGE_DONE:
            pass

    def _on_cancel(self) -> None:
        if self.page == PAGE_PROGRESS and self.busy:
            if messagebox.askyesno("取消", "正在%s，确定要取消吗？" % verb_text(self.mode)):
                self.cancelled = True
            return
        if self.page == PAGE_DONE:
            self.root.destroy()
            return
        if self.page == PAGE_OPTIONS:
            self._goto(PAGE_WELCOME)
            return
        if self.page == PAGE_WELCOME:
            if messagebox.askyesno("退出", "确定要退出安装程序吗？"):
                self.root.destroy()

    def _on_close(self) -> None:
        if self.busy:
            if not messagebox.askyesno("正在安装", "正在%s，确定要退出吗？" % verb_text(self.mode)):
                return
            self.cancelled = True
            return
        self.root.destroy()

    # ---------------------------------------------------------------- 探测与清单

    def _on_detect(self, quiet: bool = False) -> None:
        found = core.detect_pdms_roots()
        if found:
            self.var_root.set(found[0])
            text = "自动探测到 %d 个：%s" % (len(found), "；".join(found[:3]))
            if len(found) > 3:
                text += " …"
        else:
            text = "未自动探测到（需要目录里有 design.uic），请手动选择。"
        self.lbl_detect.configure(text=text)
        _ = quiet

    def _on_browse(self) -> None:
        path = filedialog.askdirectory(title="选择 PDMS 安装根目录（目录里应有 design.uic）",
                                       initialdir=self.var_root.get() or core.DEFAULT_PDMS_ROOT)
        if path:
            self.var_root.set(os.path.normpath(path))

    def _refresh_plan(self) -> None:
        """在第 2 页把「将要写入什么」列出来（真跑一遍 dry-run，拿到真实清单）。"""
        lines: List[str] = []
        try:
            if self.mode == MODE_INSTALL:
                code, log = _capture(core.do_install, pdms_root=self.pdms_root, dry_run=True)
            else:
                code, log = _capture(core.do_uninstall, pdms_root=self.pdms_root, dry_run=True)
            lines = [x.rstrip() for x in log if x.strip() and not x.startswith("=")]
        except Exception as exc:
            lines = ["（无法生成清单：%s）" % exc]
        self.txt_plan.configure(state="normal")
        self.txt_plan.delete("1.0", "end")
        self.txt_plan.insert("1.0", "\n".join(lines))
        self.txt_plan.configure(state="disabled")

    # ---------------------------------------------------------------- 执行

    def _start(self) -> None:
        self.busy = True
        self.cancelled = False
        threading.Thread(target=self._work, daemon=True).start()

    def _work(self) -> None:
        code = -1
        try:
            if self.mode == MODE_INSTALL:
                code = core.do_install(pdms_root=self.pdms_root, dry_run=self.dry_run,
                                       force=self.var_force.get(), report=self._log)
            else:
                code = core.do_uninstall(pdms_root=self.pdms_root, dry_run=self.dry_run,
                                         restore_backup=self.var_restore.get(), report=self._log)
        except core.InstallError as exc:
            self._log("")
            self._log("失败：" + str(exc))
            code = exc.code
        except Exception as exc:  # noqa: BLE001
            import traceback
            self._log(traceback.format_exc())
            self._log("未预料的错误：" + str(exc))
            code = 1
        self.result_code = code
        self.q.put(("done", code))

    def _log(self, line: str) -> None:
        self.q.put(("line", line))

    def _drain(self) -> None:
        try:
            while True:
                item = self.q.get_nowait()
                if isinstance(item, tuple) and item[0] == "line":
                    for view in (getattr(self, "txt_log", None), getattr(self, "txt_done", None)):
                        if view is not None:
                            view.configure(state="normal")
                            view.insert("end", str(item[1]) + "\n")
                            view.see("end")
                elif isinstance(item, tuple) and item[0] == "done":
                    self._finish(item[1])
        except queue.Empty:
            pass
        self.root.after(80, self._drain)

    def _finish(self, code: int) -> None:
        self.busy = False
        self.prog.stop()
        verb = verb_text(self.mode)
        if code == 0:
            if self.dry_run:
                self.lbl_done_title.configure(text="%s预览完成" % verb, foreground="#1a5fb4")
                if self.mode == MODE_INSTALL:
                    self.lbl_done_sub.configure(
                        text="以上就是将要发生的全部改动，**目前没有写入任何文件**。\n"
                             "确认没问题后，回到「上一步」取消勾选「仅预览」，再「下一步」执行真正的%s。" % verb)
                else:
                    self.lbl_done_sub.configure(
                        text="以上就是将要发生的全部改动，**目前没有写入任何文件**。\n"
                             "确认没问题后，回到「上一步」取消勾选「仅预览」，再「下一步」执行真正的%s。" % verb)
            else:
                self.lbl_done_title.configure(text="%s完成" % verb, foreground="#1a5fb4")
                if self.mode == MODE_INSTALL:
                    self.lbl_done_sub.configure(
                        text="插件已装好。\n\n"
                             "· 请把 PDMS 完全退出后重新打开（新 PML 文件需要重启后才会被索引）\n"
                             "· 进入 DESIGN 模块后，菜单栏会出现「PKPM2PDMS PML」\n"
                             "· 也可以在 PDMS 命令行执行：  $m \"%%PMLLIB%%/pkpm2pdms/pkpm2pdmsrun.mac\"\n"
                             "· 要撤销就用同一个程序选择「卸载」")
                else:
                    self.lbl_done_sub.configure(
                        text="插件已移除，请重启 PDMS 生效。\n\n"
                             "design.uic 已恢复到与安装前逐字节相同；PML 包目录被移动到了 "
                             "PMLLIB\\_removed_pkpm2pdms_<时间>，文件未删除。")
        else:
            self.lbl_done_title.configure(text="%s失败（退出码 %d）" % (verb, code), foreground="#c01c28")
            self.lbl_done_sub.configure(
                text="没有改动任何文件，或已自动回滚。\n"
                     "常见原因：%s\n详见左侧日志。" % code_hint(code))
        self._goto(PAGE_DONE)


def verb_text(mode: str) -> str:
    return "安装" if mode == MODE_INSTALL else "卸载"


def code_hint(code: int) -> str:
    return {
        0: "成功",
        1: "未预料的错误",
        2: "路径不对（PDMS 根目录 / design.uic 找不到）",
        3: "检查未通过（design.uic 不是合法 UTF-8 或 XML）",
        4: "PDMS 正在运行，请先完全退出",
        5: "写盘或写后校验失败（已尝试回滚）",
    }.get(code, "未知")


def _capture(fn, **kw):
    lines: List[str] = []
    code = fn(report=lines.append, **kw)
    return code, lines


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    mode = MODE_UNINSTALL if "--uninstall" in argv else MODE_INSTALL
    root = tk.Tk()
    Wizard(root, mode=mode)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
