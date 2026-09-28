# -*- coding: utf-8 -*-
"""S3 自检：三个子命令 × 退出码 0/2/3 + pdms2jwd 端到端 + ``--report`` / ``--dump-unit``。

跑法（工作区根目录）：``python PKPM2PDMS导入导出\\test\\_s3_cli\\check_cli.py``

输入全部是**本脚本自己生成**的（§c.4 夹具转 GBK+CRLF、故意损坏的 .jwd）；
G: 下的样本原件只读。产物写在 ``PKPM2PDMS导入导出/test/out/``（本包的输出目录）。
"""
from __future__ import annotations

import io
import json
import math
import os
import sqlite3
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(os.path.dirname(HERE))
WS = os.path.dirname(PKG)                       # D:\AI_Work\PKPM数据解析
ENGINE = os.path.join(PKG, "engine")
CLI = os.path.join(ENGINE, "cli.py")
OUT = os.path.join(PKG, "test", "out")
PLUG = u"G:/工作/PDMS相关/00 PDMS插件/02 实用插件/PKPM导入导出插件"
SECMAP = PLUG + u"/PKPM转PDMS截面匹配文件.txt"
JWD = PLUG + u"/JLCJ2.jwd"
PDT = PLUG + u"/1_PM.pdt"

sys.path.insert(0, ENGINE)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import canonical as C          # noqa: E402
import jwd_read                # noqa: E402

FAILS = []


def check(cond, label, detail=""):
    print("  [%s] %s %s" % ("OK" if cond else "FAIL", label, detail))
    if not cond:
        FAILS.append(label)


def run(args, cwd=WS):
    """真实跑 cli.py 子进程，返回 (returncode, stdout, stderr)。"""
    cmd = [sys.executable, CLI] + [str(a) for a in args]
    print("  $ python PKPM2PDMS导入导出/engine/cli.py %s" % " ".join(
        ('"%s"' % a if " " in a else a) for a in args))
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return (p.returncode, p.stdout.decode("utf-8", "replace"),
            p.stderr.decode("utf-8", "replace"))


def gbk_write(path, text):
    data = text.replace("\r\n", "\n").replace("\n", "\r\n").encode("gbk")
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def jload(path):
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def rm_own(path):
    """删掉本脚本自己上一次跑出来的产物（只允许动 test/out/ 下、且由本脚本生成的名字）。"""
    p = os.path.abspath(path)
    assert p.startswith(os.path.abspath(OUT) + os.sep), p
    if os.path.isfile(p):
        os.remove(p)
        print("  （先清掉上一次的产物 %s，让「不留产物」的检查有意义）" % os.path.basename(p))


def fmt(v):
    """与 macgen._num 同口径的十进制格式化（独立写一遍，用于核对宏文本）。"""
    x = float(v)
    if abs(x) < 5e-7:
        x = 0.0
    s = "%.6f" % x
    return (s.rstrip("0").rstrip(".") if "." in s else s) or "0"


def make_broken_jwd(path):
    """故意损坏的 .jwd：柱引用不存在的截面 ⇒ read_jwd 记 note、validate 报 E-MEM-SEC。"""
    if os.path.isfile(path):
        os.remove(path)              # 只删本脚本自己上一次跑出来的同名中间产物
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE pkpmStdFlr (ID INTEGER PRIMARY KEY, No_ INTEGER, Height REAL)")
    con.execute("CREATE TABLE pkpmFloor (ID INTEGER PRIMARY KEY, No_ INTEGER, Name TEXT,"
                " StdFlrID INTEGER, LevelB REAL, Height REAL)")
    con.execute("CREATE TABLE pkpmJoint (ID INTEGER PRIMARY KEY, No_ INTEGER, StdFlrID INTEGER,"
                " X REAL, Y REAL, HDiff REAL)")
    con.execute("CREATE TABLE pkpmColSect (ID INTEGER PRIMARY KEY, No_ INTEGER, Name TEXT,"
                " Mat INTEGER, Kind INTEGER, ShapeVal TEXT)")
    con.execute("CREATE TABLE pkpmColSeg (ID INTEGER PRIMARY KEY, No_ INTEGER, StdFlrID INTEGER,"
                " SectID INTEGER, JtID INTEGER, EccX REAL, EccY REAL, Rotation REAL,"
                " HDiffB REAL)")
    con.execute("INSERT INTO pkpmStdFlr VALUES (11, 1, 0)")
    con.execute("INSERT INTO pkpmFloor VALUES (101, 1, '', 11, 0.0, 3000.0)")
    con.execute("INSERT INTO pkpmJoint VALUES (201, 1, 11, 0.0, 0.0, 0.0)")
    con.execute("INSERT INTO pkpmColSect VALUES (301, 1, '', 6, 1, '1,400,400,6,301,')")
    con.execute("INSERT INTO pkpmColSeg VALUES (401, 1, 11, 999, 201, 0, 0, 0, 0)")  # SectID 不存在
    con.commit()
    con.close()
    return path


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    print("工作区 %s" % WS)

    # ---------------------------------------------------------- ① pdms2jwd
    print("\n=== ① pdms2jwd：契约 §c.4 最小夹具（GBK+CRLF）→ .jwd ===")
    with io.open(os.path.join(PKG, "test", "fixture_dump_min.txt"), "r", encoding="utf-8") as fh:
        fixture = fh.read()
    dump = gbk_write(os.path.join(OUT, "cli_fixture_dump_min.gbk.txt"), fixture)
    out_jwd = os.path.join(OUT, "cli_fixture.jwd")
    rc, out, err = run(["pdms2jwd", dump, "--out", out_jwd, "--secmap", SECMAP])
    check(rc == 0, "退出码 0", "rc=%d" % rc)
    check(os.path.isfile(out_jwd), "产物 .jwd 已生成：%s" % os.path.basename(out_jwd))
    rep_p = os.path.join(OUT, "cli_fixture.report.json")
    check(os.path.isfile(rep_p), "缺省报告 <--out 基名>.report.json 已生成")
    rep = jload(rep_p)
    n_un = len(rep["sections"]["unresolved"])
    check("unresolved: %d" % n_un in out,
          "stdout 打印未解析清单（unresolved: %d；%s）" % (n_un, "非空即逐条打印"))
    check(rep["counts"]["members"] == {"beam": 1, "column": 2, "brace": 0}
          and rep["counts"]["slabs"] == 1 and rep["counts"]["walls"] == 1,
          "报告构件计数 = §c.4 夹具的 2 柱/1 梁/1 板/1 墙", str(rep["counts"]))
    un_reasons = " | ".join(sorted(d["reason"] for d in rep["sections"]["unresolved"]))
    check(n_un == 2 and "B/H" in un_reasons and "T300" in un_reasons,
          "报告未解析清单 = RECT 族缺 H（夹具只给 1 个 DESP）+ 墙 T300 无条目",
          un_reasons)
    check(isinstance(rep["stats"].get("tables"), dict) and rep["stats"].get("rows"),
          "report.stats = write_jwd 的返回值（tables/rows；§b.3/§h）",
          "rows=%s" % rep["stats"].get("rows"))
    check(not rep["errors"], "errors 为空（契约附录 A 的联调建议）", str(rep["errors"]))
    con = sqlite3.connect("file:" + out_jwd.replace("\\", "/") + "?mode=ro", uri=True)
    got = (con.execute("SELECT COUNT(*) FROM pkpmColSeg").fetchone()[0],
           con.execute("SELECT COUNT(*) FROM pkpmBeamSeg").fetchone()[0],
           con.execute("PRAGMA encoding").fetchone()[0])
    con.close()
    check(got == (2, 1, "UTF-8"), ".jwd = 2 柱 / 1 梁、PRAGMA encoding=UTF-8", str(got))
    m_back = jwd_read.read_jwd(out_jwd)
    zs = sorted((round(m.start[2], 6), round(m.end[2], 6)) for m in m_back.members)
    check(zs == [(-2000.0, -1000.0), (-2000.0, -1000.0), (-1000.0, -1000.0)],
          "读回几何：2 根柱 (-2000→-1000) + 梁 (-1000→-1000)（§c.4 逐行读法）", str(zs))

    print("  --- stdout ---")
    print(out.rstrip())

    # ---------------------------------------------------------- ② --report / --base / --angle
    print("\n=== ② --report 显式路径 + --base/--angle 落进宏（§f.1）===")
    mac = os.path.join(OUT, "cli_sample.mac")
    rep2 = os.path.join(OUT, "cli_sample.report.json")
    rc, out, err = run(["jwd2pdms", JWD, "--out", mac, "--secmap", SECMAP,
                        "--project", "JLCJ2", "--report", rep2,
                        "--base", "100", "200", "300", "--angle", "90", "--unit", "mm"])
    check(rc == 0, "退出码 0", "rc=%d" % rc)
    check(os.path.isfile(rep2), "--report 指定的报告已生成")
    r2 = jload(rep2)
    check(r2["options"]["base"] == [100.0, 200.0, 300.0] and r2["options"]["angle"] == 90.0,
          "报告 options 记录 base/angle", json.dumps(r2["options"], ensure_ascii=False))
    txt = open(mac, "rb").read().decode("gbk")
    # R3 起（契约 §o.4，MacOptions.uniquify 缺省 True）宏内不再直写 "NEW ZONE /名"，
    # 而是先经唯一化函数探测再 "NEW ZONE $!n" ⇒ 断言改为 R3 形态。
    check("!!pkpm2pdmsUniquename('/JLCJ2')" in txt and "NEW ZONE $!n" in txt,
          "ZONE 名 = --project（R3 形态：先唯一化再 NEW ZONE $!n）")
    model = jwd_read.read_jwd(JWD)
    col = sorted([x for x in model.members if x.type == "column"],
                 key=lambda x: (x.no, x.id))[0]
    th = math.radians(90.0)
    cc, ss = math.cos(th), math.sin(th)
    want = "POSS E %s N %s U %s" % (fmt(100 + col.start[0] * cc - col.start[1] * ss),
                                    fmt(200 + col.start[0] * ss + col.start[1] * cc),
                                    fmt(300 + col.start[2]))
    check(want in txt,
          "按 §f.1 公式独立重算第一根柱（id=%s No=%s）的 POSS 行，宏内命中" % (col.id, col.no),
          want)
    print("     宏内命中行：%s" % want)

    # ---------------------------------------------------------- ③ 退出码 2
    print("\n=== ③ 退出码 2（参数/输入文件错误；契约 §f.2）===")
    for p in ("never.mac", "never3.jwd", "never4.mac", "never5.mac", "never6.jwd"):
        rm_own(os.path.join(OUT, p))
    rc, out, err = run(["jwd2pdms", os.path.join(OUT, "不存在的文件.jwd"),
                        "--out", os.path.join(OUT, "never.mac")])
    check(rc == 2, "输入文件不存在 ⇒ 2", "rc=%d" % rc)
    check(not os.path.isfile(os.path.join(OUT, "never.mac")), "码 2 时不留产物")
    rc, out, err = run(["jwd2pdms", JWD, "--out", os.path.join(OUT, "never5.mac"),
                        "--secmap", os.path.join(OUT, "没有这个匹配文件.txt")])
    check(rc == 2, "--secmap 指向不存在的文件 ⇒ 2", "rc=%d" % rc)
    rc, out, err = run(["pdms2jwd", dump, "--out", os.path.join(OUT, "never6.jwd")])
    check(rc == 2, "dump 同目录没有匹配文件且未给 --secmap ⇒ 2（§f.1 缺省规则）", "rc=%d" % rc)
    bad = gbk_write(os.path.join(OUT, "cli_bad_dump.txt"),
                    "#PKPM2PDMS-PDMSDUMP 1.0\nUNITS mm\n#SITE /S\n#END\n#FOO x\n")
    rc, out, err = run(["pdms2jwd", bad, "--out", os.path.join(OUT, "never3.jwd")])
    check(rc == 2, "dump 文法错误（#END 之后有内容）⇒ 2", "rc=%d" % rc)
    check(not os.path.isfile(os.path.join(OUT, "never3.jwd")), "码 2 时不留产物")
    fake = os.path.join(OUT, "cli_not_sqlite.jwd")
    with open(fake, "wb") as fh:
        fh.write(b"this is not sqlite\r\n")
    rc, out, err = run(["jwd2pdms", fake, "--out", os.path.join(OUT, "never4.mac"),
                        "--secmap", SECMAP])
    check(rc == 2, "不是 SQLite 的 .jwd ⇒ 2（不冒泡成码 1）", "rc=%d" % rc)

    # ---------------------------------------------------------- ④ 退出码 3
    print("\n=== ④ 退出码 3（validate 有 E-；不写产物）===")
    broken = make_broken_jwd(os.path.join(OUT, "cli_broken.jwd"))
    mac3 = os.path.join(OUT, "cli_broken.mac")
    rep3 = os.path.join(OUT, "cli_broken.report.json")
    rm_own(mac3)
    rc, out, err = run(["jwd2pdms", broken, "--out", mac3, "--secmap", SECMAP,
                        "--report", rep3])
    check(rc == 3, "E-MEM-SEC ⇒ 3", "rc=%d" % rc)
    check("E-MEM-SEC" in err, "E- 清单打到 stderr（§f.2 码 3）", err.strip().splitlines()[:1])
    check(not os.path.isfile(mac3), "码 3 时**不写产物**（§f.2）")
    r3 = jload(rep3)
    check(r3["errors"] and all(e.startswith("E-") for e in r3["errors"]),
          "码 3 时报告仍写出、errors 里是 E- 项", str(r3["errors"])[:150])
    print("  stderr：%s" % err.strip().splitlines()[:2])

    # ---------------------------------------------------------- ⑤ --extra / --dump-unit
    print("\n=== ⑤ --extra（§f.1）与 --dump-unit（§f.1/§c.1）===")
    extra = gbk_write(os.path.join(OUT, "cli_extra_probe.txt"),
                      "T20, /Concrete_Slab-SPEC/T20\n")
    rep5 = os.path.join(OUT, "cli_sample2.report.json")
    rc, out, err = run(["jwd2pdms", JWD, "--out", os.path.join(OUT, "cli_sample2.mac"),
                        "--secmap", SECMAP, "--extra", extra, "--report", rep5])
    r5 = jload(rep5)
    check(rc == 0 and r5["options"]["extra"] == os.path.abspath(extra),
          "--extra 给定时**只**加载该文件（options.extra 指向它）",
          str(r5["options"]["extra"]))
    names = [d["name"] for d in r5["sections"]["unresolved"]]
    check("T120" in names and "T20" not in names,
          "默认补充文件未加载 ⇒ T120 退回 unresolved、T20 因新条目解析成功", str(names))
    n_units_line = fixture.replace("UNITS mm\n", "").replace("UNITS mm\r\n", "")
    dump_no = gbk_write(os.path.join(OUT, "cli_dump_nounits.gbk.txt"), n_units_line)
    with open(dump_no, "rb") as fh:
        raw_no = fh.read()
    check(b"\r\n" in raw_no and b"UNITS" not in raw_no,
          "已生成「缺 UNITS 行」的夹具（%d 字节，首行 %r）"
          % (len(raw_no), raw_no.split(b"\r\n")[0]))
    j7 = os.path.join(OUT, "cli_fixture_m.jwd")
    rc, out, err = run(["pdms2jwd", dump_no, "--out", j7, "--dump-unit", "m",
                        "--secmap", SECMAP])
    r7 = jload(os.path.join(OUT, "cli_fixture_m.report.json"))
    check(rc == 0 and any("缺 UNITS 行" in w and "dump-unit=m" in w for w in r7["warnings"]),
          "--dump-unit 在 dump 缺 UNITS 行时生效并记 warnings",
          [w for w in r7["warnings"] if "UNITS" in w][:1])
    m7 = jwd_read.read_jwd(j7)
    z7 = sorted(round(x.start[2], 6) for x in m7.members)
    check(z7 == [-2000000.0, -2000000.0, -1000000.0],
          "UNITS m 生效：柱底 -2000 m → -2000000 mm、梁 -1000 m → -1000000 mm"
          "（§c.1 只有长度量换算）", str(z7))
    rc, out, err = run(["pdms2jwd", dump, "--out", os.path.join(OUT, "cli_fixture_mm.jwd"),
                        "--dump-unit", "m", "--secmap", SECMAP])
    r8 = jload(os.path.join(OUT, "cli_fixture_mm.report.json"))
    check(rc == 0 and any("不一致" in w and "以 UNITS 行为准" in w for w in r8["warnings"]),
          "dump 有 UNITS 行 ⇒ 以该行为准并记 warnings（--dump-unit 不生效）",
          [w for w in r8["warnings"] if "UNITS" in w][:1])

    print("\nFAIL 项：%d %s" % (len(FAILS), FAILS if FAILS else ""))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
