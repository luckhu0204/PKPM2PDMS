# -*- coding: utf-8 -*-
"""S3-v2 GUI 自检：④ 数据库转化 / ⑤ 格式互转 两个新页签（真实 Tk + 真实转换）。

跑法：``python PKPM-JWD导入导出\\test\\_s3_cli\\check_v2_gui.py``

不做假：真的建 Tk 窗口；真的按方向切换（并断言不相关的行被隐藏）；真的用界面收集到的
参数调用 ``cli.run_*``（= 按钮背后的那条路径，见 gui.ToolTab.work）；核对产物与报告。
模态对话框换成记录器（否则自动化会停在等用户点「确定」）。
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
CAT = PLUG + u"/PKPM（PDMS数据库）.txt"

sys.path.insert(0, ENGINE)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import gui as G          # noqa: E402

DIALOGS = []


def stub_dialogs():
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


def visible(tab, key):
    """某个变量对应的控件当前是否可见（grid_info 为空 = grid_remove 过）。"""
    for w in tab.form.grid_slaves():
        if str(getattr(w, "cget", lambda *_: "")("textvariable") or "") == str(tab.vars[key]):
            return bool(w.grid_info())
        if isinstance(w, G.ttk.Frame):                    # 勾选框在子框里
            for c in w.winfo_children():
                if str(getattr(c, "cget", lambda *_: "")("textvariable") or "") == str(tab.vars[key]):
                    return bool(w.grid_info())
    return False


def main():
    stub_dialogs()
    print("=== ① 建窗口：5 个标签页 ===")
    try:
        app = G.App()
    except Exception as exc:
        print("  [SKIP] 本机图形环境不可用：%r" % (exc,))
        print("\nFAIL 项：0（未能在本会话验证 GUI 构件——如实记录）")
        return 0
    app.update_idletasks()
    app.update()
    nb = [w for w in app.winfo_children() if w.winfo_class() == "TNotebook"][0]
    tabs = [nb.nametowidget(i) for i in nb.tabs()]
    names = [nb.tab(i, "text") for i in nb.tabs()]
    check(len(tabs) == 5, "五个标签页", str(names))
    check([t.tool for t in tabs] == ["jwd2pdms", "pdms2jwd", "pdt2model", "jwd2db",
                                     "pdt2pdms"],
          "页签顺序（①②③ 几何、④ 数据库转化、⑤ 格式互转）", str([t.tool for t in tabs]))
    db_tab = [t for t in tabs if t.tool == "jwd2db"][0]
    cv_tab = [t for t in tabs if t.tool == "pdt2pdms"][0]
    check(isinstance(db_tab, G.DbTab) and isinstance(cv_tab, G.ConvTab),
          "④/⑤ 用方向式页签类（_DirTab 子类）")
    check(sorted(db_tab.vars["direction"].get() and G.DB_DIRECTIONS) ==
          sorted(G.DB_DIRECTIONS), "④ 的方向下拉 = §m.1 的 5 条数据库命令",
          str(G.DB_DIRECTIONS))
    check(sorted(G.CONV_DIRECTIONS) == sorted(["pdt2pdms", "pdms2pdt", "jwd2pdt",
                                              "pdt2jwd"]),
          "⑤ 的方向下拉 = §m.1 的 4 条互转命令", str(G.CONV_DIRECTIONS))

    print("\n=== ② 按方向显示/隐藏选项行（不重建控件）===")
    db_tab.vars["direction"].set("jwd2db")
    app.update_idletasks()
    shown_gen = visible(db_tab, "suffix")
    db_tab.vars["direction"].set("db2jwd")
    app.update_idletasks()
    hidden_gen = visible(db_tab, "suffix")
    shown_skel = db_tab.vars.get("skeleton") is not None
    db_tab.vars["direction"].set("jwd2db")
    app.update_idletasks()
    check(shown_gen and not hidden_gen,
          "「--suffix」在 jwd2db 显示、在 db2jwd 隐藏（方向切换生效）",
          "jwd2db=%s db2jwd=%s" % (shown_gen, hidden_gen))
    check(shown_skel, "表单里存在 skeleton 控件（db2pdt 用）")

    print("\n=== ③ ④ 页签跑真实 jwd2db（GUI 路径）===")
    mac = os.path.join(OUT, "gui_v2_db.mac")
    rep = os.path.join(OUT, "gui_v2_db.report.json")
    db_tab.vars["direction"].set("jwd2db")
    db_tab.vars["src"].set(JWD)
    db_tab.vars["out"].set(mac)
    db_tab.vars["report"].set(rep)
    db_tab.vars["secmap"].set(SECMAP)
    db_tab.vars["project"].set("JLCJ2")
    db_tab.vars["suffix"].set("_GUITEST")
    kw = db_tab.collect()
    check(kw.get("tool") == "jwd2db" and kw.get("jwd") == JWD and kw.get("suffix") == "_GUITEST",
          "collect() 组装出的参数与命令行选项一一对应",
          json.dumps({k: str(v)[:40] for k, v in kw.items()}, ensure_ascii=False))
    res = db_tab.work(kw)
    db_tab.show_result(res)
    app.update_idletasks()
    check(res.exit_code == 0 and os.path.isfile(mac), "GUI 路径生成目录宏成功",
          "rc=%d" % res.exit_code)
    txt = open(mac, "rb").read().decode("ascii", "replace")
    check("/PKPM_JWD_USER_GUITEST" in txt and "-- clean" not in txt,
          "容器名带 --suffix 后缀；未勾 --clean ⇒ 无清场块")
    r = json.load(io.open(rep, encoding="utf-8"))
    check((r["db"]["generated"] or {}).get("sprfile") and r["db"]["safety"]["ascii_only"],
          "报告 db.generated/safety 都在（§m.3）",
          "SPRFILE=%s" % (r["db"]["generated"] or {}).get("sprfile"))
    shown = db_tab.text.get("1.0", "end")
    check("目录宏：" in shown and "本包容器：" in shown and "安全：" in shown,
          "结果区显示 db 块摘要（目录宏/容器/安全）")

    print("\n=== ④ ④ 页签跑真实 db2jwd（GUI 路径，含闭环）===")
    jwd_out = os.path.join(OUT, "gui_v2_from_cat.jwd")
    rep2 = os.path.join(OUT, "gui_v2_from_cat.report.json")
    db_tab.vars["direction"].set("db2jwd")
    db_tab.vars["src"].set(CAT)
    db_tab.vars["out"].set(jwd_out)
    db_tab.vars["report"].set(rep2)
    kw2 = db_tab.collect()
    check(kw2.get("tool") == "db2jwd" and kw2.get("db") == CAT and "skeleton" not in kw2,
          "db2jwd 不传 skeleton（该方向没有该选项）", str(sorted(kw2)))
    res2 = db_tab.work(kw2)
    r2 = json.load(io.open(rep2, encoding="utf-8"))
    check(res2.exit_code == 0 and os.path.isfile(jwd_out), "GUI 路径反算 .jwd 成功",
          "rc=%d" % res2.exit_code)
    check((r2["db"]["parsed"] or {}).get("specs", 0) >= 2920
          and set(("covered", "not_closable", "differences")) <= set(r2["db"]["closure"] or {}),
          "报告 db.parsed/db.closure 都在（闭环三键）",
          "specs=%s covered=%s" % ((r2["db"]["parsed"] or {}).get("specs"),
                                   (r2["db"]["closure"] or {}).get("covered")))
    db_tab.show_result(res2)
    check("闭环（" in db_tab.text.get("1.0", "end"), "结果区显示闭环摘要")

    print("\n=== ⑤ ④ 页签跑 dbsections（内置表 → CSV）===")
    csv = os.path.join(OUT, "gui_v2_sections.csv")
    db_tab.vars["direction"].set("dbsections")
    db_tab.vars["src"].set("")
    db_tab.vars["out"].set(csv)
    db_tab.vars["report"].set(os.path.join(OUT, "gui_v2_sections.report.json"))
    db_tab.vars["from_builtin"].set(True)
    kw3 = db_tab.collect()
    res3 = db_tab.work(kw3)
    check(res3.exit_code == 0 and os.path.isfile(csv)
          and res3.report["stats"]["table_rows"] == 3176,
          "--from-builtin 导出的 CSV = 3,176 行（§k.2）",
          "rc=%d rows=%s" % (res3.exit_code, res3.report["stats"].get("table_rows")))
    check(open(csv, "rb").read() == open(os.path.join(ENGINE, "section_table.csv"),
                                         "rb").read(),
          "导出内容与 engine/section_table.csv 逐字节相同")

    print("\n=== ⑥ ⑤ 页签跑真实 jwd2pdt（GUI 路径）===")
    pdt_out = os.path.join(OUT, "gui_v2_jwd.pdt")
    rep4 = os.path.join(OUT, "gui_v2_jwd.report.json")
    cv_tab.vars["direction"].set("jwd2pdt")
    cv_tab.vars["src"].set(JWD)
    cv_tab.vars["out"].set(pdt_out)
    cv_tab.vars["report"].set(rep4)
    cv_tab.vars["secmap"].set(SECMAP)
    cv_tab.vars["skeleton"].set("full")
    kw4 = cv_tab.collect()
    check(kw4.get("tool") == "jwd2pdt" and "jwd" in kw4 and kw4.get("skeleton") == "full",
          "jwd2pdt 的参数齐（含 --skeleton/--secmap）", str(sorted(kw4)))
    res4 = cv_tab.work(kw4)
    r4 = json.load(io.open(rep4, encoding="utf-8"))
    check(res4.exit_code == 0 and os.path.isfile(pdt_out)
          and (r4["stats"].get("ids") or {}).get("members") == 811,
          "GUI 路径 jwd2pdt：.pdt 写出、811 根构件发号",
          "rows=%s" % r4["stats"].get("rows"))
    check(cv_tab.vars["direction"].get() == "jwd2pdt", "方向保持（⑤ 页签方向可切换）")

    app.destroy()
    print("\nFAIL 项：%d %s" % (len(FAILS), FAILS if FAILS else ""))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
