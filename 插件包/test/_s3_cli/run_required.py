# -*- coding: utf-8 -*-
"""S3-v2 证据：把本轮任务要求的 6 组命令**逐条真跑**并留档。

跑法：``python PKPM2PDMS导入导出\\test\\_s3_cli\\run_required.py``
输出：``test/out/_v2_required_commands.txt``（命令 + 退出码 + stdout/stderr 原文）

任务原文里用 ``…`` 省略输入的两条（pdms2pdt / jwd2pdt / dbsections）用下面注明的输入补齐，
每条都打印"实际用的命令"。样本原件只读。
"""
from __future__ import annotations

import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(os.path.dirname(HERE))
WS = os.path.dirname(PKG)                      # D:\AI_Work\PKPM数据解析
CLI = os.path.join(PKG, "engine", "cli.py")
OUT = os.path.join(PKG, "test", "out")
PLUG = u"G:/工作/PDMS相关/00 PDMS插件/02 实用插件/PKPM导入导出插件"
JWD = PLUG + u"/JLCJ2.jwd"
PDT = PLUG + u"/1_PM.pdt"
SECMAP = PLUG + u"/PKPM转PDMS截面匹配文件.txt"
CAT = PLUG + u"/PKPM（PDMS数据库）.txt"
DUMP = os.path.join(OUT, "cli_fixture_dump_min.gbk.txt")      # §c.4 夹具（GBK+CRLF）

JOBS = [
    ("1) pdt2pdms（任务原文）",
     ["pdt2pdms", PDT, "--out", "PKPM2PDMS导入导出/test/out/sample_pdt.mac",
      "--secmap", SECMAP, "--project", "JLCJ2"]),
    ("2) jwd2db（任务原文）",
     ["jwd2db", JWD, "--out", "PKPM2PDMS导入导出/test/out/sample_db.mac",
      "--project", "JLCJ2"]),
    ("3) pdt2db（任务原文）",
     ["pdt2db", PDT, "--out", "PKPM2PDMS导入导出/test/out/sample_pdt_db.mac"]),
    ("4) db2jwd（任务原文）",
     ["db2jwd", CAT, "--out", "PKPM2PDMS导入导出/test/out/from_cat.jwd"]),
    ("5a) pdms2pdt（任务用 … 省略输入 ⇒ 用契约 §c.4 夹具，GBK+CRLF）",
     ["pdms2pdt", DUMP, "--out", "PKPM2PDMS导入导出/test/out/from_dump.pdt",
      "--secmap", SECMAP]),
    ("5b) jwd2pdt（任务用 … 省略参数 ⇒ 给 --secmap，其余取缺省）",
     ["jwd2pdt", JWD, "--out", "PKPM2PDMS导入导出/test/out/sample_jwd.pdt",
      "--secmap", SECMAP]),
    ("6a) dbsections --from-builtin（内置表 → CSV）",
     ["dbsections", "--from-builtin", "--out",
      "PKPM2PDMS导入导出/test/out/sections_builtin.csv"]),
    ("6b) dbsections（目录宏 → JSON，行数在摘要里）",
     ["dbsections", CAT, "--out", "PKPM2PDMS导入导出/test/out/sections_from_macro.json",
      "--format", "json"]),
    ("附加）pdt2jwd（§m.1 第 10 行，任务清单里有）",
     ["pdt2jwd", PDT, "--out", "PKPM2PDMS导入导出/test/out/sample_pdt_to.jwd",
      "--secmap", SECMAP]),
    ("附加）db2pdt（§m.1 第 8 行，任务清单里有；含闭环）",
     ["db2pdt", CAT, "--out", "PKPM2PDMS导入导出/test/out/from_cat.pdt",
      "--secmap", SECMAP]),
]


def main():
    log = io.StringIO()
    fails = []
    for title, args in JOBS:
        cmd = [sys.executable, "PKPM2PDMS导入导出/engine/cli.py"] + list(args)
        shown = " ".join(('"%s"' % a if (" " in a or "（" in a) else a) for a in cmd[2:])
        print("=" * 78)
        print(title)
        print("  $ python %s" % shown)
        log.write("=" * 78 + "\n%s\n$ python PKPM2PDMS导入导出/engine/cli.py %s\n"
                  % (title, shown))
        p = subprocess.run(cmd, cwd=WS, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = p.stdout.decode("utf-8", "replace")
        err = p.stderr.decode("utf-8", "replace")
        print("  退出码 = %d" % p.returncode)
        print(out.rstrip())
        if err.strip():
            print("  --- stderr ---")
            print(err.rstrip())
        log.write("退出码 = %d\n%s%s\n" % (p.returncode, out, err))
        if p.returncode != 0:
            fails.append(title)
    print("\n失败（非 0 退出码）的组：%s" % (fails if fails else "无"))
    log.write("\n失败（非 0 退出码）的组：%s\n" % (fails if fails else "无"))
    path = os.path.join(OUT, "_v2_required_commands.txt")
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(log.getvalue())
    print("证据已写入 %s（%d 字节）" % (path, len(log.getvalue())))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
