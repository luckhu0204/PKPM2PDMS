# -*- coding: utf-8 -*-
"""PKPM-JWD导入导出 —— tkinter 图形界面（契约 ``spec/CONTRACT.md`` §(f).3）。

三条纪律（§f.3 逐条）::

1. **三个标签页** 与 f.1 的三个子命令**逐项等价**（含 ``--base/--angle/--unit`` 等）；
   每个标签页上还有一个额外的「构件类别」勾选框组（§f.3 要求「勾选构件类别」）——
   它对应 ``cli.run_*`` 的 ``categories`` 参数（**不是**命令行选项，见交付说明）。
2. 逻辑**复用** ``cli.py`` 的同一个执行函数（:func:`cli.run_jwd2pdms` /
   :func:`cli.run_pdms2jwd` / :func:`cli.run_pdt2model`）——本文件**不复制**任何转换流程，
   也不做单位/编码的二次转换（§g）；所有读写都在被复用的函数里完成。
3. 执行在**后台线程**里跑（界面不冻结），结果显示：产物路径、构件计数、
   **未解析截面清单**、警告（``report.json`` 的摘要，与命令行 stdout 逐行相同）；
   「打开报告」用系统默认程序打开 ``report.json``。

只依赖标准库：``tkinter`` / ``threading`` / ``queue`` / ``os`` / ``sys``。
"""

from __future__ import annotations

import os
import queue
import sys
import threading
import traceback
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import cli as cli_mod                                    # noqa: E402

__all__ = ["App", "main"]

JWD_FILETYPES = [("PKPM 模型", "*.jwd"), ("所有文件", "*.*")]
PDT_FILETYPES = [("PKPM 中间模型", "*.pdt"), ("所有文件", "*.*")]
DUMP_FILETYPES = [("PDMS 导出文本", "*.txt"), ("所有文件", "*.*")]
MAP_FILETYPES = [("截面匹配文件", "*.txt"), ("所有文件", "*.*")]
MAC_FILETYPES = [("PDMS 宏", "*.mac"), ("所有文件", "*.*")]
JWD_OUT_FILETYPES = [("PKPM 模型", "*.jwd"), ("所有文件", "*.*")]
JSON_FILETYPES = [("JSON", "*.json"), ("所有文件", "*.*")]
#: 方向式标签页的输入/输出选择框（一个方向一个类型 ⇒ 用宽松的多模式列表，避免猜错）
IN_FILETYPES = [("PKPM/PKPM中间模型/目录宏/dump", "*.jwd *.pdt *.txt"),
                ("PKPM 模型", "*.jwd"), ("PKPM 中间模型", "*.pdt"),
                ("PDMS 目录宏 / dump 文本", "*.txt"), ("所有文件", "*.*")]
OUT_FILETYPES = [("PDMS 宏", "*.mac"), ("PKPM 模型", "*.jwd"),
                 ("PKPM 中间模型", "*.pdt"), ("转化表", "*.csv *.json"),
                 ("所有文件", "*.*")]

_HINT_REPORT = "留空 ⇒ 写在产物同目录、同基名的 .report.json（契约 §f.1）"
_HINT_SECMAP = u"留空 ⇒ 取与输入同目录的 %s（不存在则报错退出，码 2）" % cli_mod.DEFAULT_SECMAP_NAME
_HINT_EXTRA = "留空 ⇒ 自动加载 engine/secmap_extra.txt（若存在）；给定则只加载该文件（§f.1）"
_HINT_PROJECT = "留空 ⇒ 取 pkpmSysInfo.ID=2（如 JLCJ2），再取不到用 PKPM_PROJECT（§f.1）"
_HINT_UNIT = "只影响宏内数值缩放；须先把 PDMS 当前单位设成同一个值（契约 §d.4-1）"
_HINT_DUMP_UNIT = "只在 dump 缺 UNITS 行时生效；有 UNITS 行时以该行为准（§f.1/§c.1）"
_HINT_CATEGORIES = ("勾选要导出的构件类别（全部勾选 = 与命令行逐项等价）；"
                    "被取消的类别会逐类记入报告的 warnings/skipped，不静默丢弃")

#: ④ 数据库转化页签的方向（§m.1 的 5 条数据库命令）
DB_DIRECTIONS = ("jwd2db", "pdt2db", "db2jwd", "db2pdt", "dbsections")
DB_DIRECTION_CN = {
    "jwd2db": "jwd2db：.jwd 截面定义 → PDMS 目录+规格宏",
    "pdt2db": "pdt2db：.pdt 截面定义 → PDMS 目录+规格宏",
    "db2jwd": "db2jwd：PDMS 目录宏 → .jwd 截面定义（含闭环校验）",
    "db2pdt": "db2pdt：PDMS 目录宏 → .pdt 截面定义（含闭环校验）",
    "dbsections": "dbsections：目录宏/内置表 → 截面转化表（CSV/JSON）",
}
#: ⑤ 格式互转页签的方向（§m.1 的 4 条互转命令）
CONV_DIRECTIONS = ("pdt2pdms", "pdms2pdt", "jwd2pdt", "pdt2jwd")
CONV_DIRECTION_CN = {
    "pdt2pdms": "pdt2pdms：.pdt → PDMS 建模型宏（.mac）",
    "pdms2pdt": "pdms2pdt：PDMSDUMP 文本 → .pdt",
    "jwd2pdt": "jwd2pdt：.jwd → .pdt（走规范模型）",
    "pdt2jwd": "pdt2jwd：.pdt → .jwd（走规范模型）",
}
_HINT_DIRECTION = ("方向决定输入/输出类型与可用选项（与 §m.1 的命令矩阵逐项对应）；"
                   "不适用于当前方向的行会自动置灰/隐藏")
_HINT_DB_PROJECT = ("--project 只记进报告的 options.project 与宏头注释"
                    "（目录宏没有 ZONE 概念；§m.1 的可选参数列里没有它）")
_HINT_SUFFIX = ("--suffix：4 个顶层容器名的唯一后缀；留空用 _YYYYMMDD。"
                "宏只操作本包自己的 /PKPM_JWD_* 容器（§l.1）")
_HINT_CLEAN = ("--clean：生成清场版（OLD … DELETE … MEM），只清本包自己的容器；"
               "CATE/SPWL 的 MEM 语义未直证（§12#16）")
_HINT_CATALOGUE = "必须是本包前缀（/PKPM_JWD_…）；填用户既有容器名会被安全闸拒绝（码 2）"
_HINT_SKELETON = ("full（13 段，缺省）| sections-only（只写首行+$VERSION+$DESIGNPARA+"
                  "$DEFFRAMESECTION+$END，§j.7.6）")
_HINT_FROM_BUILTIN = ("勾选 ⇒ 直接导出 engine/section_table.csv（§k.2 的冻结表），"
                      "此时输入文件可留空")
_HINT_FORMAT = "输出格式；留空按输出文件扩展名（.json → json，其余 csv）"


# --------------------------------------------------------------------------
# 后台执行：线程 + 队列（界面不冻结；结果回主线程显示）
# --------------------------------------------------------------------------


class _Job:
    """一次后台执行：``work()`` 在子线程里跑，结果经 ``queue`` 回主线程。"""

    def __init__(self, tab: "ToolTab", work: Callable[[], cli_mod.RunResult]) -> None:
        self.tab = tab
        self.work = work
        self.q: "queue.Queue[Tuple[str, Any]]" = queue.Queue()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self.tab._set_busy(True)
        self.tab._show_text("正在执行…（界面不冻结；请稍候）\n", clear=True)
        self.thread.start()
        self.tab.after(120, self._poll)

    def _run(self) -> None:
        try:
            res = self.work()
        except Exception:                       # 兜底：任何异常都要显示出来（§f.2 码 1）
            self.q.put(("exc", traceback.format_exc()))
        else:
            self.q.put(("ok", res))

    def _poll(self) -> None:
        try:
            kind, payload = self.q.get_nowait()
        except queue.Empty:
            self.tab.after(120, self._poll)
            return
        self.tab._set_busy(False)
        if kind == "exc":
            self.tab.show_traceback(payload)
        else:
            self.tab.show_result(payload)


# --------------------------------------------------------------------------
# 标签页
# --------------------------------------------------------------------------


class ToolTab(ttk.Frame):
    """一个子命令的界面：参数行 + 运行按钮 + 结果区（由子类填 :attr:`rows_hint`）。"""

    tool = ""
    title = ""
    run_button_text = "开始转换"

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, padding=8)
        self.vars: Dict[str, tk.Variable] = {}
        self._busy = False
        self._out_path = ""
        self._report_path = ""

        self.columnconfigure(0, weight=1)
        row = 0
        ttk.Label(self, text=self.title, font=("", 10, "bold")).grid(
            row=row, column=0, sticky="w", pady=(0, 6))
        row += 1
        self.form = ttk.Frame(self)
        self.form.grid(row=row, column=0, sticky="ew")
        self.form.columnconfigure(1, weight=1)
        row += 1
        self._row = 0
        self.build_form()
        self.build_result_area(row)

    # ---------------------------------------------------------------- 表单构件
    def _next(self) -> int:
        self._row += 1
        return self._row

    def var(self, key: str, value: Any = "") -> tk.Variable:
        v: tk.Variable
        if isinstance(value, bool):
            v = tk.BooleanVar(master=self, value=value)
        else:
            v = tk.StringVar(master=self, value=value)
        self.vars[key] = v
        return v

    def _hint(self, text: str) -> None:
        r = self._next()
        ttk.Label(self.form, text=text, foreground="#555555", wraplength=760,
                  justify="left").grid(row=r, column=1, sticky="w", pady=(0, 4))

    def file_row(self, key: str, label: str, *, save: bool = False,
                 filetypes: Sequence[Tuple[str, str]] = (), hint: str = "",
                 default: str = "") -> tk.Variable:
        r = self._next()
        ttk.Label(self.form, text=label).grid(row=r, column=0, sticky="w", padx=(0, 6))
        v = self.var(key, default)
        ent = ttk.Entry(self.form, textvariable=v)
        ent.grid(row=r, column=1, sticky="ew")
        ttk.Button(self.form, text="另存为…" if save else "选择…", width=10,
                   command=lambda: self._pick(key, save, filetypes)).grid(
            row=r, column=2, sticky="w", padx=(6, 0))
        if hint:
            self._hint(hint)
        return v

    def entry_row(self, key: str, label: str, default: str = "", hint: str = "",
                  width: int = 28) -> tk.Variable:
        r = self._next()
        ttk.Label(self.form, text=label).grid(row=r, column=0, sticky="w", padx=(0, 6))
        v = self.var(key, default)
        ttk.Entry(self.form, textvariable=v, width=width).grid(row=r, column=1, sticky="w")
        if hint:
            self._hint(hint)
        return v

    def combo_row(self, key: str, label: str, values: Sequence[str], default: str,
                  hint: str = "") -> tk.Variable:
        r = self._next()
        ttk.Label(self.form, text=label).grid(row=r, column=0, sticky="w", padx=(0, 6))
        v = self.var(key, default)
        ttk.Combobox(self.form, textvariable=v, values=list(values), width=8,
                     state="readonly").grid(row=r, column=1, sticky="w")
        if hint:
            self._hint(hint)
        return v

    def base_row(self, hint: str = "") -> None:
        """``--base E N U``：三个数值框。"""
        r = self._next()
        ttk.Label(self.form, text="基点 E / N / U").grid(row=r, column=0, sticky="w",
                                                       padx=(0, 6))
        box = ttk.Frame(self.form)
        box.grid(row=r, column=1, sticky="w")
        for i, nm in enumerate(("base_e", "base_n", "base_u")):
            v = self.var(nm, "0")
            ttk.Entry(box, textvariable=v, width=12).grid(row=0, column=i * 2, sticky="w")
            ttk.Label(box, text=("E", "N", "U")[i]).grid(row=0, column=i * 2 + 1,
                                                        padx=(2, 10))
        if hint:
            self._hint(hint)

    def categories_row(self) -> None:
        """构件类别勾选（§f.3；对应 ``cli.run_*`` 的 ``categories`` 参数）。"""
        r = self._next()
        ttk.Label(self.form, text="构件类别").grid(row=r, column=0, sticky="w", padx=(0, 6))
        box = ttk.Frame(self.form)
        box.grid(row=r, column=1, sticky="w")
        for i, key in enumerate(cli_mod.CATEGORIES):
            v = self.var("cat_" + key, True)
            ttk.Checkbutton(box, text=cli_mod.CATEGORY_CN[key], variable=v).grid(
                row=0, column=i, sticky="w", padx=(0, 10))
        self._hint(_HINT_CATEGORIES)

    def build_result_area(self, row: int) -> None:
        box = ttk.Frame(self, padding=(0, 8, 0, 0))
        box.grid(row=row, column=0, sticky="nsew")
        box.columnconfigure(0, weight=1)
        box.rowconfigure(1, weight=1)
        self.rowconfigure(row, weight=1)

        bar = ttk.Frame(box)
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self.btn_run = ttk.Button(bar, text=self.run_button_text, command=self.on_run)
        self.btn_run.grid(row=0, column=0, sticky="w")
        self.btn_report = ttk.Button(bar, text="打开报告", command=self.open_report,
                                     state="disabled")
        self.btn_report.grid(row=0, column=1, padx=(8, 0))
        self.btn_output = ttk.Button(bar, text="打开产物", command=self.open_output,
                                     state="disabled")
        self.btn_output.grid(row=0, column=2, padx=(8, 0))
        self.lbl_status = ttk.Label(bar, text="就绪")
        self.lbl_status.grid(row=0, column=3, padx=(12, 0))

        self.text = tk.Text(box, height=18, wrap="none", font=("Consolas", 9))
        self.text.grid(row=1, column=0, sticky="nsew")
        ysb = ttk.Scrollbar(box, orient="vertical", command=self.text.yview)
        ysb.grid(row=1, column=1, sticky="ns")
        xsb = ttk.Scrollbar(box, orient="horizontal", command=self.text.xview)
        xsb.grid(row=2, column=0, sticky="ew")
        self.text.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)

    # ---------------------------------------------------------------- 文件选择
    def _pick(self, key: str, save: bool, filetypes: Sequence[Tuple[str, str]]) -> None:
        cur = str(self.vars[key].get() or "")
        if save:
            path = filedialog.asksaveasfilename(filetypes=list(filetypes),
                                                initialfile=os.path.basename(cur) or None,
                                                initialdir=os.path.dirname(cur) or None)
        else:
            path = filedialog.askopenfilename(filetypes=list(filetypes),
                                              initialdir=os.path.dirname(cur) or None)
        if path:
            self.vars[key].set(os.path.normpath(path))

    # ---------------------------------------------------------------- 执行
    def _categories(self) -> Optional[List[str]]:
        """返回 ``None``（全选 = 与命令行等价）或勾中的类别列表。"""
        chosen: List[str] = []
        for c in cli_mod.CATEGORIES:
            v = self.vars.get("cat_" + c)
            if v is None or bool(v.get()):
                chosen.append(c)
        return None if len(chosen) == len(cli_mod.CATEGORIES) else chosen

    def collect(self) -> Dict[str, Any]:
        """收集界面参数（子类实现）；抛 ``ValueError`` 表示用户输入有问题。"""
        raise NotImplementedError

    def work(self, kwargs: Dict[str, Any]) -> cli_mod.RunResult:
        raise NotImplementedError

    def on_run(self) -> None:
        if self._busy:
            return
        try:
            kwargs = self.collect()
        except ValueError as exc:
            messagebox.showerror("参数有误", str(exc), parent=self)
            return
        self._out_path = str(kwargs.get("out") or "")
        if not self._out_path:
            messagebox.showerror("参数有误", "必须指定产物路径（--out）", parent=self)
            return
        _Job(self, lambda: self.work(kwargs)).start()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.btn_run.configure(state=("disabled" if busy else "normal"),
                               text=("正在执行…" if busy else self.run_button_text))
        self.lbl_status.configure(text=("正在执行…" if busy else "就绪"))

    def _show_text(self, s: str, clear: bool = False) -> None:
        self.text.configure(state="normal")
        if clear:
            self.text.delete("1.0", "end")
        self.text.insert("end", s)
        self.text.see("end")
        self.text.configure(state="disabled")

    def show_result(self, res: cli_mod.RunResult) -> None:
        """显示 ``report.json`` 的摘要（与命令行 stdout 逐行相同）+ 警告明细。"""
        self._out_path = res.output or self._out_path
        self._report_path = res.report_path or ""
        self._show_text("\n".join(res.lines) + "\n", clear=True)
        rep = res.report or {}
        warns = list(rep.get("warnings") or [])
        anoms = list(rep.get("geometry_anomalies") or [])
        if warns or anoms:
            self._show_text("\n【报告摘要补充】warnings %d 条 / geometry_anomalies %d 条"
                            "（全量见报告文件）\n" % (len(warns), len(anoms)))
            for w in warns[:20]:
                self._show_text("  W: %s\n" % (w,))
            if len(warns) > 20:
                self._show_text("  …（其余 %d 条见报告）\n" % (len(warns) - 20,))
            for a in anoms[:20]:
                self._show_text("  A: %s\n" % (a,))
            if len(anoms) > 20:
                self._show_text("  …（其余 %d 条见报告）\n" % (len(anoms) - 20,))
        self.lbl_status.configure(
            text={0: "完成", 2: "输入/参数错误（码 2）", 3: "模型有 E- 项（码 3）"}
            .get(res.exit_code, "失败（码 %s）" % res.exit_code))
        if res.ok:
            self.btn_report.configure(state=("normal" if self._report_path else "disabled"))
            self.btn_output.configure(state=("normal" if self._out_path else "disabled"))
        else:
            self.btn_report.configure(
                state=("normal" if self._report_path and os.path.isfile(self._report_path)
                       else "disabled"))
            self.btn_output.configure(state="disabled")
        if not res.ok:
            messagebox.showwarning("未完成（退出码 %s）" % res.exit_code,
                                   "\n".join(res.lines[:6]), parent=self)

    def show_traceback(self, tb: str) -> None:
        self._show_text("界面线程捕获到未预期异常（契约 §f.2 码 1 的情形）：\n" + tb,
                        clear=True)
        self.lbl_status.configure(text="异常")
        messagebox.showerror("未预期异常", tb.strip().splitlines()[-1], parent=self)

    # ---------------------------------------------------------------- 打开文件
    def open_report(self) -> None:
        self._open(self._report_path, "报告不存在")

    def open_output(self) -> None:
        self._open(self._out_path, "产物不存在")

    @staticmethod
    def _open(path: str, missing: str) -> None:
        if not path or not os.path.exists(path):
            messagebox.showerror("打不开", "%s：%s" % (missing, path or "(空)"))
            return
        try:
            if hasattr(os, "startfile"):                     # Windows：系统默认程序
                os.startfile(path)                           # type: ignore[attr-defined]
            else:                                            # 其它平台的可退化实现
                import subprocess
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path])
        except Exception as exc:
            messagebox.showerror("打不开", "%s\n%s" % (path, exc))


def _opt_text(var: Optional[tk.Variable]) -> Optional[str]:
    """可选文本：空串 ⇒ ``None``（让 cli 走 §f.1 的缺省规则）。"""
    s = str(var.get()).strip() if var is not None else ""
    return s or None


def _need_text(var: tk.Variable, what: str) -> str:
    s = str(var.get()).strip()
    if not s:
        raise ValueError("请先指定%s" % what)
    return s


def _float_text(var: tk.Variable, what: str, default: float = 0.0) -> float:
    s = str(var.get()).strip()
    if not s:
        return default
    try:
        return float(s)
    except ValueError:
        raise ValueError("%s 必须是数字，收到 %r" % (what, s))


def _bool(var: Optional[tk.Variable]) -> bool:
    return bool(var.get()) if var is not None else False


class _DirTab(ToolTab):
    """方向式标签页：一个"方向"下拉 + 共用表单，按方向显示/隐藏各选项行（§m.1 的命令矩阵）。

    实现方式：整行（标签/输入框/按钮/提示）记在 :attr:`groups` 里，切换方向时
    ``grid()`` / ``grid_remove()``——**不重建**控件，也不复制任何转换逻辑
    （收集到的参数原样交给 ``cli.run_*``，§f.3）。
    """

    run_button_text = "一键转换"
    directions: Sequence[str] = ()
    direction_cn: Dict[str, str] = {}

    def __init__(self, master: tk.Misc) -> None:
        self.groups: Dict[str, List[tk.Widget]] = {}
        self._group_of_dir: Dict[str, Tuple[str, ...]] = {}
        super().__init__(master)

    # ---------------------------------------------------------------- 分组
    def _capture(self, name: str, before: int) -> None:
        """把 ``before`` 之后新增的行（含 hint 行）记进 ``name`` 组。"""
        rows = set(range(before + 1, self._row + 1))
        for w in self.form.grid_slaves():
            try:
                r = int(w.grid_info().get("row", -1))
            except (TypeError, ValueError):
                continue
            if r in rows:
                self.groups.setdefault(name, []).append(w)

    def _apply_direction(self, *_a) -> None:
        d = str(self.vars["direction"].get())
        want = set(self._group_of_dir.get(d, ()))
        for name, ws in self.groups.items():
            for w in ws:
                if name == "always" or name in want:
                    w.grid()
                else:
                    w.grid_remove()
        if hasattr(self, "btn_run") and d in cli_mod.TOOLS:
            self.btn_run.configure(text="一键转换（%s）" % d)
        hint = self.hints.get(d)
        if hint and hasattr(self, "lbl_dir_hint"):
            self.lbl_dir_hint.configure(text=hint)

    def build_result_area(self, row: int) -> None:
        """先建结果区（按钮），再按当前方向应用一次显示/隐藏。"""
        super().build_result_area(row)
        self._apply_direction()

    # ---------------------------------------------------------------- 表单
    def build_form(self) -> None:
        self.hints: Dict[str, str] = {}
        b = self._row
        self.combo_row("direction", "转换方向", list(self.directions),
                       self.directions[0], _HINT_DIRECTION)
        self._capture("always", b)
        r = self._next()
        self.lbl_dir_hint = ttk.Label(self.form, text="", foreground="#004080",
                                      wraplength=760, justify="left")
        self.lbl_dir_hint.grid(row=r, column=0, columnspan=3, sticky="w", pady=(0, 4))
        self.groups.setdefault("always", []).append(self.lbl_dir_hint)
        self.build_direction_form()
        self.vars["direction"].trace_add("write", self._apply_direction)
        self._apply_direction()

    def build_direction_form(self) -> None:
        raise NotImplementedError

    # ---------------------------------------------------------------- 收集
    def collect(self) -> Dict[str, Any]:
        d = str(self.vars["direction"].get())
        if d not in self.directions:
            raise ValueError("未知方向 %r" % (d,))
        return self.collect_direction(d)

    def collect_direction(self, d: str) -> Dict[str, Any]:
        raise NotImplementedError

    def work(self, kwargs: Dict[str, Any]) -> cli_mod.RunResult:
        tool = str(kwargs.pop("tool"))
        fn = {"pdt2pdms": cli_mod.run_pdt2pdms, "pdms2pdt": cli_mod.run_pdms2pdt,
              "jwd2pdt": cli_mod.run_jwd2pdt, "pdt2jwd": cli_mod.run_pdt2jwd,
              "jwd2db": cli_mod.run_jwd2db, "pdt2db": cli_mod.run_pdt2db,
              "db2jwd": cli_mod.run_db2jwd, "db2pdt": cli_mod.run_db2pdt,
              "dbsections": cli_mod.run_dbsections}.get(tool)
        if fn is None:                       # pragma: no cover - collect() 已挡住
            raise ValueError("未实现的 GUI 方向：%r" % (tool,))
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        return fn(**kwargs)


# --------------------------------------------------------------------------
# 三个标签页（逐项对应 f.1 的三个子命令）
# --------------------------------------------------------------------------


class Jwd2PdmsTab(ToolTab):
    tool = "jwd2pdms"
    title = "① .jwd → PDMS 宏（jwd2pdms）：生成 GBK+CRLF 的 .mac 与 report.json"

    def build_form(self) -> None:
        self.file_row("jwd", "PKPM 模型 .jwd", filetypes=JWD_FILETYPES)
        self.file_row("secmap", "--secmap 截面匹配文件", filetypes=MAP_FILETYPES,
                      hint=_HINT_SECMAP)
        self.file_row("extra", "--extra 补充映射文件", filetypes=MAP_FILETYPES,
                      hint=_HINT_EXTRA)
        self.file_row("out", "--out 输出宏 .mac", save=True, filetypes=MAC_FILETYPES)
        self.file_row("report", "--report 报告 json", save=True, filetypes=JSON_FILETYPES,
                      hint=_HINT_REPORT)
        self.entry_row("project", "--project 工程名（ZONE）", hint=_HINT_PROJECT)
        self.base_row("基点单位 = --unit（mm/cm/m）；缺省 0 0 0")
        self.entry_row("angle", "--angle 转角（度，+U 俯视逆时针）", default="0", width=10)
        self.combo_row("unit", "--unit 宏内单位", cli_mod.macgen.UNITS, "mm", _HINT_UNIT)
        self.categories_row()

    def collect(self) -> Dict[str, Any]:
        base = tuple(_float_text(self.vars["base_" + k], "基点 %s" % k.upper())
                     for k in ("e", "n", "u"))
        return {
            "jwd": _need_text(self.vars["jwd"], "输入 .jwd 文件"),
            "out": str(self.vars["out"].get()).strip(),
            "secmap": _opt_text(self.vars.get("secmap")),
            "extra": _opt_text(self.vars.get("extra")),
            "project": _opt_text(self.vars.get("project")),
            "base": base,
            "angle": _float_text(self.vars["angle"], "转角"),
            "unit": str(self.vars["unit"].get()),
            "report": _opt_text(self.vars.get("report")),
            "categories": self._categories(),
        }

    def work(self, kwargs: Dict[str, Any]) -> cli_mod.RunResult:
        return cli_mod.run_jwd2pdms(**kwargs)


class Pdms2JwdTab(ToolTab):
    tool = "pdms2jwd"
    title = "② PDMS 导出文本 → .jwd（pdms2jwd）：PDMSDUMP 1.0（GBK）→ SQLite"

    def build_form(self) -> None:
        self.file_row("dump", "PDMS 导出文本（dump.txt）", filetypes=DUMP_FILETYPES)
        self.file_row("secmap", "--secmap 截面匹配文件", filetypes=MAP_FILETYPES,
                      hint=_HINT_SECMAP)
        self.file_row("out", "--out 输出 .jwd", save=True, filetypes=JWD_OUT_FILETYPES)
        self.file_row("report", "--report 报告 json", save=True, filetypes=JSON_FILETYPES,
                      hint=_HINT_REPORT)
        self.combo_row("dump_unit", "--dump-unit dump 缺省单位", cli_mod.macgen.UNITS, "mm",
                       _HINT_DUMP_UNIT)
        self.categories_row()

    def collect(self) -> Dict[str, Any]:
        return {
            "dump": _need_text(self.vars["dump"], "输入 dump 文本"),
            "out": str(self.vars["out"].get()).strip(),
            "secmap": _opt_text(self.vars.get("secmap")),
            "dump_unit": str(self.vars["dump_unit"].get()),
            "report": _opt_text(self.vars.get("report")),
            "categories": self._categories(),
        }

    def work(self, kwargs: Dict[str, Any]) -> cli_mod.RunResult:
        return cli_mod.run_pdms2jwd(**kwargs)


class Pdt2ModelTab(ToolTab):
    tool = "pdt2model"
    title = "③ .pdt → 规范模型 JSON（pdt2model）：只读 .pdt，写 model.json"

    def build_form(self) -> None:
        self.file_row("pdt", "PKPM 中间模型 .pdt", filetypes=PDT_FILETYPES)
        self.file_row("out", "--out 输出 model.json", save=True, filetypes=JSON_FILETYPES)
        self.file_row("report", "--report 报告 json", save=True, filetypes=JSON_FILETYPES,
                      hint=_HINT_REPORT)
        self.categories_row()

    def collect(self) -> Dict[str, Any]:
        return {
            "pdt": _need_text(self.vars["pdt"], "输入 .pdt 文件"),
            "out": str(self.vars["out"].get()).strip(),
            "report": _opt_text(self.vars.get("report")),
            "categories": self._categories(),
        }

    def work(self, kwargs: Dict[str, Any]) -> cli_mod.RunResult:
        return cli_mod.run_pdt2model(**kwargs)


# --------------------------------------------------------------------------
# 主窗口
# --------------------------------------------------------------------------


class DbTab(_DirTab):
    """④ 数据库转化页签：PDMS 目录/规格宏 ⇄ PKPM 截面定义 ⇄ 截面转化表（§m.1 的 5 条）。

    与命令行逐项等价：输入/输出/--secmap/--extra/--report/--project/--suffix/--clean/
    --catalogue-user/--catalogue-stss/--skeleton/--from-builtin/--format 全部有对应控件。
    """

    tool = "jwd2db"
    title = "④ 数据库转化：PKPM 截面定义 ⇄ PDMS 目录+规格宏（Catalogue + Specification）"
    directions = DB_DIRECTIONS
    direction_cn = DB_DIRECTION_CN

    def build_direction_form(self) -> None:
        self.hints = {d: DB_DIRECTION_CN[d] for d in self.directions}
        b = self._row
        self.file_row("src", "输入文件", filetypes=IN_FILETYPES,
                      hint="jwd2db/pdt2db：.jwd / .pdt；db2jwd/db2pdt/dbsections：PDMS 目录宏；"
                           "dbsections 也可勾下面的「用内置表」而留空")
        self.file_row("out", "输出文件", save=True, filetypes=OUT_FILETYPES)
        self.file_row("report", "--report 报告 json", save=True, filetypes=JSON_FILETYPES,
                      hint=_HINT_REPORT)
        self.file_row("secmap", "--secmap 截面匹配文件", filetypes=MAP_FILETYPES,
                      hint=_HINT_SECMAP)
        self._capture("always", b)

        b = self._row
        self.file_row("extra", "--extra 补充映射文件", filetypes=MAP_FILETYPES,
                      hint=_HINT_EXTRA)
        self.categories_row()
        self._capture("gen", b)

        b = self._row
        self.entry_row("project", "--project 工程名标签", hint=_HINT_DB_PROJECT)
        self.entry_row("suffix", "--suffix 容器后缀", hint=_HINT_SUFFIX)
        r = self._next()
        ttk.Label(self.form, text="--clean 清场版").grid(row=r, column=0, sticky="w",
                                                       padx=(0, 6))
        ttk.Checkbutton(self.form, text="生成清场版（只清本包容器）",
                        variable=self.var("clean", False)).grid(row=r, column=1,
                                                              sticky="w")
        self._hint(_HINT_CLEAN)
        self.entry_row("catalogue_user", "--catalogue-user", hint=_HINT_CATALOGUE)
        self.entry_row("catalogue_stss", "--catalogue-stss", hint=_HINT_CATALOGUE)
        self._capture("gen", b)

        b = self._row
        self.combo_row("skeleton", "--skeleton 写出骨架", cli_mod.SKELETONS, "full",
                       _HINT_SKELETON)
        self._capture("parse", b)

        b = self._row
        r = self._next()
        ttk.Label(self.form, text="内置表").grid(row=r, column=0, sticky="w", padx=(0, 6))
        ttk.Checkbutton(self.form, text="用内置转化表（--from-builtin）",
                        variable=self.var("from_builtin", False)).grid(row=r, column=1,
                                                                      sticky="w")
        self._hint(_HINT_FROM_BUILTIN)
        self.combo_row("format", "--format 转化表格式", ("", "csv", "json"), "",
                       _HINT_FORMAT)
        self._capture("builtin", b)

        self._group_of_dir = {
            "jwd2db": ("gen",), "pdt2db": ("gen",),
            "db2jwd": (), "db2pdt": ("parse",),
            "dbsections": ("builtin",),
        }

    def collect_direction(self, d: str) -> Dict[str, Any]:
        common = {"out": _need_text(self.vars["out"], "输出文件"),
                  "secmap": _opt_text(self.vars.get("secmap")),
                  "report": _opt_text(self.vars.get("report"))}
        if d in ("jwd2db", "pdt2db"):
            args = dict(common)
            args.update({
                "extra": _opt_text(self.vars.get("extra")),
                "project": _opt_text(self.vars.get("project")),
                "suffix": _opt_text(self.vars.get("suffix")),
                "clean": _bool(self.vars.get("clean")),
                "catalogue_user": _opt_text(self.vars.get("catalogue_user")),
                "catalogue_stss": _opt_text(self.vars.get("catalogue_stss")),
                "categories": self._categories(),
            })
            if d == "jwd2db":
                args["jwd"] = _need_text(self.vars["src"], "输入 .jwd 文件")
                args["tool"] = "jwd2db"
            else:
                args["pdt"] = _need_text(self.vars["src"], "输入 .pdt 文件")
                args["tool"] = "pdt2db"
            return args
        if d in ("db2jwd", "db2pdt"):
            args = dict(common)
            args["db"] = _need_text(self.vars["src"], "输入目录宏文件")
            if d == "db2pdt":
                args["skeleton"] = str(self.vars["skeleton"].get())
            args["tool"] = d
            return args
        args = dict(common)
        args["db"] = _opt_text(self.vars.get("src"))
        args["from_builtin"] = _bool(self.vars.get("from_builtin"))
        args["fmt"] = _opt_text(self.vars.get("format"))
        if not args["from_builtin"] and not args["db"]:
            raise ValueError("请选择输入目录宏，或勾选「用内置转化表」")
        args["tool"] = "dbsections"
        return args


class ConvTab(_DirTab):
    """⑤ 格式互转页签：pdt2pdms / pdms2pdt / jwd2pdt / pdt2jwd（§m.1 第 2/4/9/10 行）。"""

    tool = "pdt2pdms"
    title = "⑤ 格式互转：.pdt↔.jwd↔PDMS 文本 ↔ PDMS 建模型宏"
    directions = CONV_DIRECTIONS
    direction_cn = CONV_DIRECTION_CN

    def build_direction_form(self) -> None:
        self.hints = {d: CONV_DIRECTION_CN[d] for d in self.directions}
        b = self._row
        self.file_row("src", "输入文件", filetypes=IN_FILETYPES,
                      hint="pdt2pdms/pdt2jwd：.pdt；jwd2pdt：.jwd；pdms2pdt：dump 文本")
        self.file_row("out", "输出文件", save=True, filetypes=OUT_FILETYPES)
        self.file_row("report", "--report 报告 json", save=True, filetypes=JSON_FILETYPES,
                      hint=_HINT_REPORT)
        self.file_row("secmap", "--secmap 截面匹配文件", filetypes=MAP_FILETYPES,
                      hint=_HINT_SECMAP)
        self._capture("always", b)

        b = self._row
        self.file_row("extra", "--extra 补充映射文件", filetypes=MAP_FILETYPES,
                      hint=_HINT_EXTRA)
        self.categories_row()
        self._capture("gen", b)

        b = self._row
        self.combo_row("dump_unit", "--dump-unit dump 缺省单位", cli_mod.macgen.UNITS,
                       "mm", _HINT_DUMP_UNIT)
        self._capture("dump", b)

        b = self._row
        self.combo_row("skeleton", "--skeleton 写出骨架", cli_mod.SKELETONS, "full",
                       _HINT_SKELETON)
        self._capture("pdt", b)

        b = self._row
        self.entry_row("project", "--project 工程名（ZONE）", hint=_HINT_PROJECT)
        self.base_row("基点单位 = --unit（mm/cm/m）；缺省 0 0 0")
        self.entry_row("angle", "--angle 转角（度，+U 俯视逆时针）", default="0", width=10)
        self.combo_row("unit", "--unit 宏内单位", cli_mod.macgen.UNITS, "mm", _HINT_UNIT)
        self._capture("macro", b)

        self._group_of_dir = {
            "pdt2pdms": ("gen", "macro"), "pdms2pdt": ("dump", "pdt"),
            "jwd2pdt": ("gen", "pdt"), "pdt2jwd": ("gen",),
        }

    def collect_direction(self, d: str) -> Dict[str, Any]:
        args: Dict[str, Any] = {
            "out": _need_text(self.vars["out"], "输出文件"),
            "secmap": _opt_text(self.vars.get("secmap")),
            "report": _opt_text(self.vars.get("report")),
            "tool": d,
        }
        if d == "pdt2pdms":
            base = tuple(_float_text(self.vars["base_" + k], "基点 %s" % k.upper())
                         for k in ("e", "n", "u"))
            args.update({"pdt": _need_text(self.vars["src"], "输入 .pdt 文件"),
                         "extra": _opt_text(self.vars.get("extra")),
                         "project": _opt_text(self.vars.get("project")),
                         "base": base,
                         "angle": _float_text(self.vars["angle"], "转角"),
                         "unit": str(self.vars["unit"].get()),
                         "categories": self._categories()})
            return args
        if d == "pdms2pdt":
            args.update({"dump": _need_text(self.vars["src"], "输入 dump 文本"),
                         "dump_unit": str(self.vars["dump_unit"].get()),
                         "skeleton": str(self.vars["skeleton"].get())})
            return args
        if d == "jwd2pdt":
            args.update({"jwd": _need_text(self.vars["src"], "输入 .jwd 文件"),
                         "extra": _opt_text(self.vars.get("extra")),
                         "skeleton": str(self.vars["skeleton"].get()),
                         "categories": self._categories()})
            return args
        args.update({"pdt": _need_text(self.vars["src"], "输入 .pdt 文件"),
                     "categories": self._categories()})
        return args


class App(tk.Tk):
    """主窗口：三个标签页 + 顶部说明。界面文字全部中文（§f.3）。"""

    def __init__(self) -> None:
        super().__init__()
        self.title("PKPM-JWD导入导出 —— 图形界面（契约 v%s）" % cli_mod.C.CONTRACT_VERSION)
        self.geometry("1000x760")
        self.minsize(880, 640)

        head = ttk.Frame(self, padding=(10, 8, 10, 0))
        head.pack(fill="x")
        ttk.Label(head, justify="left", wraplength=960, text=(
            "五个标签页与命令行逐项对应（契约 §f.1 的三条 + §m.1 的九条）：①②③ 是几何链路，"
            "④ 数据库转化（目录宏/规格宏/截面转化表），⑤ 格式互转。"
            "执行逻辑复用 cli.py 的同一函数；结果区显示 report.json 的摘要：产物路径、"
            "构件计数、未解析截面清单、db 块（目录宏/解析/交叉核对/闭环/安全）与警告。\n"
            "PDMS 侧产物（.mac/.pdt/目录宏）为 GBK 或纯 ASCII + CRLF、无 BOM；"
            "Python/JSON 产物为 UTF-8 无 BOM。转换只读用户原件，绝不改写输入文件；"
            "目录宏只新建/清理本包自己的 /PKPM_JWD_* 容器（§l.1）。"
        )).pack(anchor="w")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=8)
        for cls in (Jwd2PdmsTab, Pdms2JwdTab, Pdt2ModelTab, DbTab, ConvTab):
            tab = cls(nb)
            nb.add(tab, text={"jwd2pdms": "① .jwd → PDMS 宏",
                              "pdms2jwd": "② PDMS 文本 → .jwd",
                              "pdt2model": "③ .pdt → model.json",
                              "jwd2db": "④ 数据库转化",
                              "pdt2pdms": "⑤ 格式互转"}[cls.tool])


def main(argv: Optional[Sequence[str]] = None) -> int:
    """启动 GUI（``python engine/gui.py``）。无显示器/无 Tk 时打印说明并返回 1。"""
    try:
        app = App()
    except tk.TclError as exc:                     # 无窗口系统（如纯无头会话）
        print("无法初始化 tkinter 窗口：%s" % (exc,), file=sys.stderr)
        print("本机若无图形环境，请改用命令行：python engine/cli.py --help", file=sys.stderr)
        return 1
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
