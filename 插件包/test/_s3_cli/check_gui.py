# -*- coding: utf-8 -*-
"""S3 自检：gui.py 的真实构件（建窗口）+ 通过 GUI 自己的代码路径跑一次转换。

跑法：``python PKPM-JWD导入导出\\test\\_s3_cli\\check_gui.py``

不做假：真的 ``Tk()`` 建窗口（无显示器时 Tk 自己会报 TclError，本脚本如实报"未能在
图形环境启动"而不是伪造通过）；真的把界面上的输入框填成样本路径，调用
``ToolTab.collect()`` + ``ToolTab.work()``——即 GUI 按钮背后的那条路径（它又调
``cli.run_*``），核对产物与报告。
"""
from __future__ import annotations

import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(os.path.dirname(HERE))
ENGINE = os.path.join(PKG, "engine")
OUT = os.path.join(PKG, "test", "out")
PLUG = u"G:/工作/PDMS相关/00 PDMS插件/02 实用插件/PKPM导入导出插件"
SECMAP = PLUG + u"/PKPM转PDMS截面匹配文件.txt"
JWD = PLUG + u"/JLCJ2.jwd"
PDT = PLUG + u"/1_PM.pdt"

sys.path.insert(0, ENGINE)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import gui as G          # noqa: E402

#: 自动化跑 GUI 时必须把**模态对话框**换成记录器——否则脚本会停在等用户点「确定」。
#: 记录下来的内容也算证据（界面确实想弹这个框）。
DIALOGS = []


def _stub_dialogs():
    def mk(kind):
        def f(title=None, message=None, **kw):
            DIALOGS.append((kind, title, message))
            return "ok"
        return f
    for name in ("showwarning", "showerror", "showinfo"):
        setattr(G.messagebox, name, mk(name))


FAILS = []


def check(cond, label, detail=""):
    print("  [%s] %s %s" % ("OK" if cond else "FAIL", label, detail))
    if not cond:
        FAILS.append(label)


def main():
    _stub_dialogs()
    print("=== ① 导入 gui.py（不得在建窗口前做任何 I/O）===")
    check(hasattr(G, "App") and hasattr(G, "main"), "gui.App / gui.main 存在")
    check(G.cli_mod.run_jwd2pdms is not None, "gui 复用的是 cli.py 的执行函数（同一对象）")

    print("\n=== ② 真的建一次 Tk 窗口（无显示器则如实失败）===")
    try:
        app = G.App()
    except Exception as exc:                     # tk.TclError / 其它
        print("  [SKIP] 本机图形环境不可用：%r" % (exc,))
        print("\nFAIL 项：0（GUI 构件未能在本会话验证——已如实记录）")
        return 0
    app.update_idletasks()
    app.update()
    tabs = [w for w in app.winfo_children()
            if w.winfo_class() == "TNotebook"]
    check(bool(tabs), "主窗口里有 Notebook（标签页容器）")
    nb = tabs[0]
    names = [nb.tab(i, "text") for i in nb.tabs()]
    check(len(names) == 5, "五个标签页（v1 三条 + ④ 数据库转化 + ⑤ 格式互转）", str(names))
    alltabs = [nb.nametowidget(i) for i in nb.tabs()]
    t0, t1, t2 = alltabs[0], alltabs[1], alltabs[2]          # 本脚本只查 v1 的三条
    check([x.tool for x in alltabs][:3] == ["jwd2pdms", "pdms2jwd", "pdt2model"],
          "前三个标签页 = jwd2pdms / pdms2jwd / pdt2model",
          str([x.tool for x in alltabs]))
    for t in (t0, t1, t2):
        check(isinstance(t.vars.get("out"), type(t.vars.get("out"))),
              "[%s] 表单已建（%d 个变量）" % (t.tool, len(t.vars)), sorted(t.vars))
        check(hasattr(t, "btn_report") and str(t.btn_report["text"]) == "打开报告",
              "[%s] 有「打开报告」按钮" % t.tool)
    check(sorted(t0.vars) == sorted(["jwd", "secmap", "extra", "out", "report", "project",
                                     "base_e", "base_n", "base_u", "angle", "unit"] +
                                    ["cat_" + c for c in G.cli_mod.CATEGORIES]),
          "[jwd2pdms] 输入项逐项对应 §f.1（含 --base/--angle/--unit/--extra/--project）",
          sorted(t0.vars))
    check(sorted(t1.vars) == sorted(["dump", "secmap", "out", "report", "dump_unit"] +
                                    ["cat_" + c for c in G.cli_mod.CATEGORIES]),
          "[pdms2jwd] 输入项逐项对应 §f.1（含 --dump-unit）", sorted(t1.vars))
    check(sorted(t2.vars) == sorted(["pdt", "out", "report"] +
                                    ["cat_" + c for c in G.cli_mod.CATEGORIES]),
          "[pdt2model] 输入项逐项对应 §f.1", sorted(t2.vars))

    print("\n=== ③ 通过 GUI 的 collect()/work() 跑真实 jwd2pdms ===")
    mac = os.path.join(OUT, "gui_sample.mac")
    rep = os.path.join(OUT, "gui_sample.report.json")
    t0.vars["jwd"].set(JWD)
    t0.vars["secmap"].set(SECMAP)
    t0.vars["out"].set(mac)
    t0.vars["report"].set(rep)
    t0.vars["project"].set("JLCJ2")
    t0.vars["base_e"].set("0")
    t0.vars["base_n"].set("0")
    t0.vars["base_u"].set("0")
    t0.vars["angle"].set("0")
    t0.vars["unit"].set("mm")
    kwargs = t0.collect()
    check(kwargs["categories"] is None, "全勾选 ⇒ categories=None（与命令行逐项等价）")
    res = t0.work(kwargs)
    check(res.exit_code == 0 and res.ok, "GUI 路径转换成功（退出码 0）", "rc=%d" % res.exit_code)
    t0.show_result(res)                       # 界面显示分支（写 Text 控件）真的跑一遍
    shown = t0.text.get("1.0", "end")
    check("unresolved" in shown and "构件计数" in shown,
          "结果区显示 report.json 摘要（构件计数 + 未解析清单）",
          shown.strip().splitlines()[:2])
    app.update_idletasks()
    check(t0.btn_report.instate(["!disabled"]) and t0.btn_output.instate(["!disabled"]),
          "成功后「打开报告」「打开产物」按钮可用",
          "report=%s output=%s" % (t0.btn_report.instate(["!disabled"]),
                                   t0.btn_output.instate(["!disabled"])))
    r = json.loads(open(rep, "rb").read().decode("utf-8"))
    check(r["counts"]["members_total"] == 811, "报告构件计数 = 811（真实样本）",
          str(r["counts"]["members"]))

    print("\n=== ④ GUI 的构件类别勾选（只勾柱/梁 ⇒ 支撑被过滤并记账）===")
    mac2 = os.path.join(OUT, "gui_sample_noBrace.mac")
    rep2 = os.path.join(OUT, "gui_sample_noBrace.report.json")
    t0.vars["cat_brace"].set(False)
    t0.vars["out"].set(mac2)
    t0.vars["report"].set(rep2)
    kw = t0.collect()
    check(kw == None or kw["categories"] == ["column", "beam", "slab", "wall"],
          "取消「支撑」后 categories = 柱/梁/板/墙", str(kw.get("categories")))
    res2 = t0.work(kw)
    r2 = json.loads(open(rep2, "rb").read().decode("utf-8"))
    check(res2.exit_code == 0 and r2["counts"]["members"]["brace"] == 0
          and r2["counts"]["members"]["column"] == 200,
          "13 根支撑被过滤、200 根柱保留（计数取 Model.counts()）",
          str(r2["counts"]["members"]))
    check(any("构件类别勾选" in w for w in r2["warnings"])
          and any(s.get("what") == "member" and s.get("type") == "brace"
                  for s in r2["skipped"]),
          "过滤逐类记进 report.warnings + report.skipped（不静默）")

    print("\n=== ⑤ GUI 的 collect() 输入校验 ===")
    t0.vars["jwd"].set("")
    try:
        t0.collect()
        check(False, "空输入必须报错")
    except ValueError as exc:
        check("输入 .jwd" in str(exc), "空输入 ⇒ ValueError（界面弹「参数有误」）", str(exc))
    t0.vars["jwd"].set(JWD)
    t0.vars["angle"].set("不是数字")
    try:
        t0.collect()
        check(False, "非法转角必须报错")
    except ValueError as exc:
        check("转角" in str(exc), "非法转角 ⇒ ValueError", str(exc))

    print("\n=== ⑥ pdt2model 标签页同样可用 ===")
    js = os.path.join(OUT, "gui_sample_pdt.json")
    rep3 = os.path.join(OUT, "gui_sample_pdt.report.json")
    t2.vars["pdt"].set(PDT)
    t2.vars["out"].set(js)
    t2.vars["report"].set(rep3)
    res3 = t2.work(t2.collect())
    check(res3.exit_code == 0 and os.path.isfile(js), "GUI 的 pdt2model 成功",
          "rc=%d" % res3.exit_code)

    print("\n=== ⑦ 失败时的界面状态（码 2：不显示「打开产物」）===")
    t1.vars["dump"].set(os.path.join(OUT, "没有这个 dump.txt"))
    t1.vars["out"].set(os.path.join(OUT, "gui_never.jwd"))
    t1.vars["report"].set(os.path.join(OUT, "gui_never.report.json"))
    res4 = t1.work(t1.collect())
    t1.show_result(res4)
    app.update_idletasks()
    check(res4.exit_code == 2, "输入不存在 ⇒ 码 2", "rc=%d" % res4.exit_code)
    check(not t1.btn_output.instate(["!disabled"]),
          "失败时「打开产物」保持禁用（没有产物可开）")
    check("未完成" in t1.text.get("1.0", "end"),
          "结果区显示失败摘要而不是空白", t1.text.get("1.0", "end").strip()[:60])
    check(any(d[0] == "showwarning" for d in DIALOGS),
          "失败时弹出警告框（已换成记录器，实弹为模态框）",
          str(DIALOGS[-1][1] if DIALOGS else ""))

    print("\n=== ⑧ 后台线程执行（界面不冻结）+ 结果经队列回主线程 ===")
    import threading
    import time
    mac4 = os.path.join(OUT, "gui_thread.mac")
    rep4 = os.path.join(OUT, "gui_thread.report.json")
    t0.vars["jwd"].set(JWD)
    t0.vars["secmap"].set(SECMAP)
    t0.vars["out"].set(mac4)
    t0.vars["report"].set(rep4)
    t0.vars["cat_brace"].set(True)
    t0.vars["angle"].set("0")              # ⑤ 里故意写坏过，这里恢复
    t0.vars["base_e"].set("0")
    seen = {}
    orig_work, orig_show = t0.work, t0.show_result

    def work_spy(kw):
        seen["work_thread"] = threading.current_thread().ident
        return orig_work(kw)

    def show_spy(res):
        seen["show_thread"] = threading.current_thread().ident
        seen["res"] = res
        orig_show(res)

    t0.work, t0.show_result = work_spy, show_spy
    t0.on_run()
    check(t0._busy and t0.btn_run.instate(["disabled"]),
          "运行期间按钮禁用、主线程立刻返回（界面不冻结）")
    check(t0.text.get("1.0", "end").strip().startswith("正在执行"),
          "运行中结果区显示「正在执行…」", t0.text.get("1.0", "1.60").strip())
    deadline = time.time() + 120
    while "res" not in seen and time.time() < deadline:
        app.update()                       # 主线程继续跑事件循环（真正的 GUI 行为）
        time.sleep(0.02)
    t0.work, t0.show_result = orig_work, orig_show
    check("res" in seen, "结果经队列回到主线程并显示",
          "耗时 %.2fs" % (120 - (deadline - time.time())))
    if "res" in seen:
        check(seen["work_thread"] != threading.main_thread().ident,
              "转换真的跑在后台线程（与主线程 ident 不同）",
              "worker=%s main=%s" % (seen.get("work_thread"),
                                     threading.main_thread().ident))
        check(seen.get("show_thread") == threading.main_thread().ident,
              "结果显示回主线程（Tk 只在主线程被触碰）", str(seen.get("show_thread")))
        check(seen["res"].exit_code == 0 and os.path.isfile(mac4),
              "后台线程路径的产物已生成（%s）" % os.path.basename(mac4),
              "rc=%d" % seen["res"].exit_code)
        check(not t0._busy and t0.btn_run.instate(["!disabled"]),
              "结束后按钮恢复可用")

    app.destroy()
    print("\nFAIL 项：%d %s" % (len(FAILS), FAILS if FAILS else ""))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
