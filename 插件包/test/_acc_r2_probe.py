# -*- coding: utf-8 -*-
"""临时探针 R2-1：跑齐 R2 命令并打印报告关键字段（验收测试编写用）。"""
import io
import json
import os
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = r"D:\AI_Work\PKPM数据解析"
CLI = os.path.join(ROOT, "PKPM2PDMS导入导出", "engine", "cli.py")
OUT = os.path.join(ROOT, "PKPM2PDMS导入导出", "test", "_acc_r2_out")
S = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
JWD = os.path.join(S, "JLCJ2.jwd")
PDT = os.path.join(S, "1_PM.pdt")
MAP = os.path.join(S, "PKPM转PDMS截面匹配文件.txt")
DB = os.path.join(S, "PKPM（PDMS数据库）.txt")
os.makedirs(OUT, exist_ok=True)


def run(args, tag):
    p = subprocess.run([sys.executable, CLI] + args, cwd=ROOT, capture_output=True)
    o = p.stdout.decode("utf-8", "replace")
    print("=== %s exit=%d" % (tag, p.returncode))
    if p.returncode:
        print(o[-2000:])
        print(p.stderr.decode("utf-8", "replace")[-2000:])
    return p.returncode


def rep(name):
    p = os.path.join(OUT, name)
    if not os.path.isfile(p):
        print("  (no report %s)" % name)
        return {}
    d = json.load(open(p, encoding="utf-8"))
    return d


def show(tag, d, keys=("counts", "stats")):
    print("--- %s" % tag)
    print("   tool=%s source_format=%s errors=%s" % (d.get("tool"), d.get("source_format"), d.get("errors")))
    for k in keys:
        v = d.get(k)
        if isinstance(v, dict):
            v = {kk: vv for kk, vv in v.items() if kk != "secmap"}
            print("   %s = %s" % (k, json.dumps(v, ensure_ascii=False)[:1500]))
        else:
            print("   %s = %s" % (k, v))
    db = d.get("db") or {}
    if db:
        print("   db.generated = %s" % json.dumps(db.get("generated"), ensure_ascii=False)[:1200])
        print("   db.parsed    = %s" % json.dumps(db.get("parsed"), ensure_ascii=False)[:600])
        print("   db.cross     = %s" % json.dumps(db.get("cross_check"), ensure_ascii=False)[:900])
        cl = db.get("closure") or {}
        print("   db.closure.covered=%s not_closable=%s differences=%s"
              % (cl.get("covered"), json.dumps(cl.get("not_closable"), ensure_ascii=False)[:600],
                 json.dumps(cl.get("differences"), ensure_ascii=False)[:600]))
        print("   db.safety    = %s" % json.dumps(db.get("safety"), ensure_ascii=False)[:400])
    print("   skipped=%d warnings=%d assumptions=%d" % (len(d.get("skipped") or []), len(d.get("warnings") or []), len(d.get("assumptions") or [])))


# 1) jwd2pdt
run(["jwd2pdt", JWD, "--out", os.path.join(OUT, "jwd2pdt.pdt"),
     "--report", os.path.join(OUT, "jwd2pdt.report.json")], "jwd2pdt")
# 2) pdt2pdms
run(["pdt2pdms", PDT, "--out", os.path.join(OUT, "pdt2pdms.mac"),
     "--report", os.path.join(OUT, "pdt2pdms.report.json")], "pdt2pdms")
# 3) jwd2pdms (for comparison, v1 command)
run(["jwd2pdms", JWD, "--out", os.path.join(OUT, "jwd2pdms.mac"),
     "--report", os.path.join(OUT, "jwd2pdms.report.json")], "jwd2pdms")
# 4) jwd2db / pdt2db
run(["jwd2db", JWD, "--out", os.path.join(OUT, "jwd2db.mac"),
     "--report", os.path.join(OUT, "jwd2db.report.json")], "jwd2db")
run(["pdt2db", PDT, "--out", os.path.join(OUT, "pdt2db.mac"),
     "--report", os.path.join(OUT, "pdt2db.report.json")], "pdt2db")
# 5) dbsections on the user macro
run(["dbsections", DB, "--out", os.path.join(OUT, "db_table.csv"),
     "--secmap", MAP, "--report", os.path.join(OUT, "dbsections.report.json")], "dbsections(user macro)")
# 6) db2jwd / db2pdt on the *package-generated* macro (closure step 1)
run(["db2jwd", os.path.join(OUT, "jwd2db.mac"), "--out", os.path.join(OUT, "db2jwd_from_jwd2db.jwd"),
     "--secmap", MAP, "--report", os.path.join(OUT, "db2jwd.report.json")], "db2jwd(pkg macro)")
run(["db2pdt", os.path.join(OUT, "pdt2db.mac"), "--out", os.path.join(OUT, "db2pdt_from_pdt2db.pdt"),
     "--secmap", MAP, "--report", os.path.join(OUT, "db2pdt.report.json")], "db2pdt(pkg macro)")
# 7) closure step 2: feed the reverse-engineered .jwd/.pdt back into jwd2db/pdt2db
run(["jwd2db", os.path.join(OUT, "db2jwd_from_jwd2db.jwd"),
     "--out", os.path.join(OUT, "closure2.mac"), "--secmap", MAP,
     "--report", os.path.join(OUT, "closure2.report.json")], "jwd2db(closure)")
print()
show("jwd2pdt", rep("jwd2pdt.report.json"), ("counts", "stats"))
show("pdt2pdms", rep("pdt2pdms.report.json"), ("counts", "stats"))
show("jwd2pdms", rep("jwd2pdms.report.json"), ("counts",))
show("jwd2db", rep("jwd2db.report.json"), ("stats",))
show("pdt2db", rep("pdt2db.report.json"), ("stats",))
show("dbsections", rep("dbsections.report.json"), ("stats",))
show("db2jwd", rep("db2jwd.report.json"), ("counts", "stats"))
show("db2pdt", rep("db2pdt.report.json"), ("counts", "stats"))
show("closure2", rep("closure2.report.json"), ("stats",))
