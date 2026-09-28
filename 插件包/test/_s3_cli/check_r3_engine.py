# -*- coding: utf-8 -*-
"""R3 引擎侧自检：``--request`` 协议（§p.5/§m R3）+ ``renames`` 键（§h v3）+ 引擎入口三形态。

跑法：``python PKPM2PDMS导入导出\\test\\_s3_cli\\check_r3_engine.py``

覆盖：
  A. ``_request_to_argv`` 的键还原（连字符选项、位置参数、bool/列表/省略、未知键、缺参、未知 tool）
  B. ``main(["--request", …])`` 端到端（dbsections 内置表 ⇒ 0；缺文件/坏 JSON/未知 tool ⇒ 2）
  C. ``report.renames`` 键存在（生成方向恒 []）
  D. 引擎入口三形态：python cli.py / dist\\run_engine.cmd / dist\\pkpm2pdms_engine.exe（--request）
  E. pdms-net/ENGINE_IO.md 存在且含冻结锚点
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(os.path.dirname(HERE))
WS = os.path.dirname(PKG)
ENGINE = os.path.join(PKG, "engine")
OUT = os.path.join(PKG, "test", "out")
sys.path.insert(0, ENGINE)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import cli as cli_mod   # noqa: E402

FAILS = []


def check(cond, label, detail=""):
    print("  [%s] %s %s" % ("OK" if cond else "FAIL", label, detail))
    if not cond:
        FAILS.append(label)


def run_main(argv):
    """直接调 cli.main()（进程内）；捕获 stdout/stderr 并返回退出码。"""
    import contextlib
    buf_out, buf_err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
        rc = cli_mod.main(argv)
    return rc, buf_out.getvalue(), buf_err.getvalue()


def main():
    parser = cli_mod.build_parser()

    print("=== A. _request_to_argv 的键还原（与 EngineRunner.BuildRequest 对齐）===")
    a1 = cli_mod._request_to_argv(parser, "jwd2pdms", {
        "jwd": "a.jwd", "out": "o.mac", "base": [1.0, 2.0, 3.0], "angle": 90,
        "secmap": None, "extra": "", "project": "JLCJ2", "unit": "mm"})
    check(a1 == ["jwd2pdms", "a.jwd", "--out", "o.mac", "--base", "1.0", "2.0", "3.0",
                 "--angle", "90", "--project", "JLCJ2", "--unit", "mm"],
          "jwd2pdms：位置参数 + 连字符/列表/数值/省略", str(a1))
    a2 = cli_mod._request_to_argv(parser, "dbsections",
                                  {"from_builtin": True, "out": "x.csv", "format": "csv"})
    check(a2 == ["dbsections", "--from-builtin", "--out", "x.csv", "--format", "csv"],
          "dbsections：from_builtin ⇒ 真实选项串 --from-builtin（连字符不被拼错）", str(a2))
    a3 = cli_mod._request_to_argv(parser, "pdms2pdt",
                                  {"dump": "d.txt", "out": "o.pdt", "dump_unit": "cm"})
    check(a3 == ["pdms2pdt", "d.txt", "--out", "o.pdt", "--dump-unit", "cm"],
          "pdms2pdt：dump_unit ⇒ --dump-unit（真实注册的选项串）", str(a3))
    try:
        cli_mod._request_to_argv(parser, "db2pdt",
                                 {"db": "m.txt", "out": "o.pdt", "dump_unit": "cm"})
        check(False, "db2pdt 没有 --dump-unit，传了必须报错")
    except cli_mod.InputError as exc:
        check(True, "db2pdt 没有 --dump-unit，传了 ⇒ InputError（不发明选项）", str(exc)[:70])
    a4 = cli_mod._request_to_argv(parser, "jwd2db",
                                  {"jwd": "a.jwd", "out": "o.mac", "clean": True,
                                   "catalogue_user": "/PKPM2PDMS_USER_X"})
    check(a4 == ["jwd2db", "a.jwd", "--out", "o.mac", "--clean",
                 "--catalogue-user", "/PKPM2PDMS_USER_X"],
          "jwd2db：store_true 与连字符长选项", str(a4))
    for tool, bad in (("jwd2pdms", {"jwd": "a", "out": "b", "nope": 1}),
                      ("pdms2pdt", {"out": "b", "skeleton": "full"}),
                      ("nope", {"out": "b"})):
        try:
            cli_mod._request_to_argv(parser, tool, bad)
            check(False, "非法 request 必须报错：%s" % tool)
        except cli_mod.InputError as exc:
            check(True, "非法 request ⇒ InputError（%s）" % tool, str(exc)[:70])

    print("\n=== B. main(--request) 端到端 ===")
    req = os.path.join(OUT, "_req_probe_engine.json")
    with io.open(req, "w", encoding="utf-8", newline="\n") as fh:   # §p.5：UTF-8 无 BOM
        fh.write(json.dumps({"tool": "dbsections",
                             "args": {"from_builtin": True,
                                      "out": os.path.join(OUT, "_req_probe_engine.csv"),
                                      "format": "csv"}}, ensure_ascii=False))
    rc, out, err = run_main(["--request", req])
    check(rc == 0 and "3176 行 × 15 列" in out, "--request 端到端（dbsections 内置表）RC=0",
          "rc=%d" % rc)
    check("unresolved: 不适用" in out, "DB 方向成功摘要含『不适用』行", out.splitlines()[-4][:60]
          if out else "")
    rc, out, err = run_main(["--request", os.path.join(OUT, "_missing_req.json")])
    check(rc == 2, "request 文件不存在 ⇒ 2", "rc=%d" % rc)
    bad = os.path.join(OUT, "_req_bad_engine.json")
    with io.open(bad, "w", encoding="ascii", newline="\n") as fh:
        fh.write("{bad json")
    rc, out, err = run_main(["--request", bad])
    check(rc == 2, "坏 JSON ⇒ 2", "rc=%d" % rc)
    with io.open(bad, "w", encoding="ascii", newline="\n") as fh:
        fh.write('{"tool": "nope", "args": {}}')
    rc, out, err = run_main(["--request", bad])
    check(rc == 2, "未知 tool ⇒ 2", "rc=%d" % rc)
    with io.open(bad, "w", encoding="ascii", newline="\n") as fh:
        fh.write('{"tool": "jwd2pdms", "args": {"jwd": "a.jwd", "out": "b.mac", "nope": 1}}')
    rc, out, err = run_main(["--request", bad])
    check(rc == 2, "未知键 ⇒ 2（每个操作只传该子命令实际存在的参数）", "rc=%d" % rc)

    print("\n=== C. report.renames 键（§h v3/§o.7）===")
    rep = json.load(io.open(os.path.join(OUT, "r3.report.json"), encoding="utf-8"))
    check(rep.get("renames") == [], "r3.report.json 的 renames == []", repr(rep.get("renames")))
    check(cli_mod._new_report("t", "s", "jwd", "o", {}).get("renames") == [],
          "_new_report 恒含 renames 键")

    print("\n=== D. 引擎入口三形态 ===")
    exe = os.path.join(ENGINE, "dist", "pkpm2pdms_engine.exe")
    wrap = os.path.join(ENGINE, "dist", "run_engine.cmd")
    check(os.path.isfile(exe), "dist\\pkpm2pdms_engine.exe 存在（PyInstaller --onefile）",
          "%d B" % (os.path.getsize(exe) if os.path.isfile(exe) else -1))
    check(os.path.isfile(wrap), "dist\\run_engine.cmd 存在（§p.1 回退）")
    wb = open(wrap, "rb").read()
    check(b"\r\n" in wb and all(c < 128 for c in wb),
          "run_engine.cmd 为 ASCII + CRLF（§g 纪律 6）", "%d B" % len(wb))
    req2 = os.path.join(OUT, "_req_r3_jwd2pdms.json")
    p = subprocess.run([exe, "--request", req2], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    out_txt = p.stdout.decode("utf-8")          # §p.5：引擎管道 stdout = UTF-8
    check(p.returncode == 0 and "[jwd2pdms] 成功" in out_txt and "构件计数" in out_txt,
          "exe --request 端到端（jwd2pdms 全样本）RC=0 且 UTF-8 可解码", "rc=%d" % p.returncode)
    check(os.path.isfile(os.path.join(OUT, "r3.mac")) and os.path.getsize(
        os.path.join(OUT, "r3.mac")) > 300000, "exe 产物 r3.mac 在位")
    rep2 = json.load(io.open(os.path.join(OUT, "r3.report.json"), encoding="utf-8"))
    check(rep2["tool"] == "jwd2pdms" and rep2["renames"] == [],
          "exe 路径的报告同样带 renames=[]")

    print("\n=== E. ENGINE_IO.md ===")
    doc = os.path.join(PKG, "pdms-net", "ENGINE_IO.md")
    check(os.path.isfile(doc), "pdms-net/ENGINE_IO.md 存在")
    t = io.open(doc, encoding="utf-8").read() if os.path.isfile(doc) else ""
    for anchor in ("--request", "engine_path.txt", "PKPM2PDMS_ENGINE", "pkpm2pdms_engine.exe",
                   "run_engine.cmd", "renames", "退出码", "30 分钟", "UTF-8"):
        check(anchor in t, "ENGINE_IO.md 含锚点 %r" % anchor)

    print("\nFAIL 项：%d %s" % (len(FAILS), FAILS if FAILS else ""))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
