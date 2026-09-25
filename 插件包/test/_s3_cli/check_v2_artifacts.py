# -*- coding: utf-8 -*-
"""S3-v2 产物字节纪律自检（契约 §g / §j.2 / §l.1-5 / §l.4）。

跑法：``python PKPM-JWD导入导出\\test\\_s3_cli\\check_v2_artifacts.py``

只读 ``test/out/`` 下的产物；不写任何文件。检查项：
  * PDMS 侧（.mac 建模型宏 / 目录宏）：GBK 可解码、无 BOM、只有 CRLF；目录宏另外要求纯 ASCII。
  * .pdt（§j.2）：无 BOM、只有 CRLF、GBK 可解码。
  * CSV / JSON（转化表 / 报告）：UTF-8 无 BOM。
  * .jwd：SQLite 头部 + PRAGMA encoding。
"""
from __future__ import annotations

import io
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(PKG, "test", "out")
ENGINE = os.path.join(PKG, "engine")

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
FAILS = []

#: (文件名, 类别) —— 类别决定检查口径
FILES = [
    ("sample_pdt.mac", "macro"),
    ("sample_db.mac", "dbmacro"),
    ("sample_pdt_db.mac", "dbmacro"),
    ("sample_jwd.pdt", "pdt"),
    ("from_cat.pdt", "pdt"),
    ("from_dump.pdt", "pdt"),
    ("sample_jwd_sections.pdt", "pdt"),
    ("sections_builtin.csv", "csv"),
    ("sections_from_macro.json", "utf8"),
    ("sample_pdt.report.json", "utf8"),
    ("sample_db.report.json", "utf8"),
    ("sample_pdt_db.report.json", "utf8"),
    ("from_cat.report.json", "utf8"),
    ("from_cat_db2pdt.report.json", "utf8"),
    ("sample_jwd.report.json", "utf8"),
    ("sample_pdt2jwd.report.json", "utf8"),
    ("sections_builtin.report.json", "utf8"),
    ("sections_from_macro.report.json", "utf8"),
]


def check(cond, label, detail=""):
    print("  [%s] %s %s" % ("OK" if cond else "FAIL", label, detail))
    if not cond:
        FAILS.append(label)


def main():
    print("=== 产物字节纪律（%d 个文件）===" % len(FILES))
    for name, kind in FILES:
        p = os.path.join(OUT, name)
        if not os.path.isfile(p):
            check(False, "%s 存在" % name, "缺文件")
            continue
        b = open(p, "rb").read()
        bom = b.startswith(b"\xef\xbb\xbf")
        lone = b.replace(b"\r\n", b"").count(b"\n")
        try:
            b.decode("gbk")
            gbk_ok = isinstance(b.decode("gbk"), str)
        except UnicodeDecodeError:
            gbk_ok = False
        ascii_only = all(c < 128 for c in b)
        if kind == "csv":
            # §k.2 第 1277 行：转化表 CSV 是 **UTF-8 带 BOM + CRLF**（§g 的例外行，与源表一致）
            try:
                b.decode("utf-8-sig")
                u8 = True
            except UnicodeDecodeError:
                u8 = False
            check(u8 and bom and lone == 0,
                  "%s（csv）UTF-8+BOM + CRLF（§k.2 的例外行）" % name,
                  "%d 字节，bom=%s，孤立 LF=%d" % (len(b), bom, lone))
        elif kind in ("macro", "dbmacro", "pdt"):
            ok = (not bom) and lone == 0 and gbk_ok
            if kind == "dbmacro":
                ok = ok and ascii_only
            check(ok, "%s（%s）无 BOM / 只有 CRLF / GBK 可解码%s"
                  % (name, kind, " / 纯 ASCII" if kind == "dbmacro" else ""),
                  "%d 字节，bom=%s，孤立 LF=%d，ascii=%s" % (len(b), bom, lone, ascii_only))
        else:
            try:
                b.decode("utf-8")
                u8 = True
            except UnicodeDecodeError:
                u8 = False
            check(u8 and not bom, "%s（UTF-8）无 BOM 且可解码" % name,
                  "%d 字节，bom=%s" % (len(b), bom))

    print("\n=== 内置转化表逐字节相同（§k.2）===")
    a = open(os.path.join(OUT, "sections_builtin.csv"), "rb").read()
    e = open(os.path.join(ENGINE, "section_table.csv"), "rb").read()
    check(a == e, "dbsections --from-builtin 的 CSV == engine/section_table.csv",
          "%d vs %d 字节（sha 相同=%s）" % (len(a), len(e), a == e))

    print("\n=== 目录宏安全约束（§l.1）===")
    txt = open(os.path.join(OUT, "sample_db.mac"), "rb").read().decode("ascii")
    forbidden = ["/AVEVA", "/CATALOGUE", "/SPWLD", "/SPECIFICATION", "OVERRIDE"]
    for f in forbidden:
        check(f not in txt, "sample_db.mac 内不出现 %r" % f)
    for f in ("/PKPM_JWD_USER", "/PKPM_JWD_STSS", "/PKPM_JWD_USER_SECTION", "/PKPM_JWD_LIB"):
        check(f in txt, "sample_db.mac 只建本包容器 %s" % f)
    news = sum(1 for l in txt.splitlines() if l.strip().startswith("NEW "))
    ends = sum(1 for l in txt.splitlines() if l.strip() == "END")
    check(news == ends, "NEW 与 END 1:1（§l.3.4-2）", "%d : %d" % (news, ends))

    print("\n=== .jwd 产物（db2jwd / pdt2jwd）===")
    for name in ("from_cat.jwd", "sample_pdt2jwd.jwd"):
        p = os.path.join(OUT, name)
        if not os.path.isfile(p):
            check(False, "%s 存在" % name)
            continue
        con = sqlite3.connect("file:" + p.replace("\\", "/") + "?mode=ro", uri=True)
        t = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        enc = con.execute("PRAGMA encoding").fetchone()[0]
        con.close()
        check(t == 46 and enc == "UTF-8", "%s：46 表 / PRAGMA encoding=UTF-8" % name,
              "%d 表 / %s" % (t, enc))

    print("\nFAIL 项：%d %s" % (len(FAILS), FAILS if FAILS else ""))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
