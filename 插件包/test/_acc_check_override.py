# -*- coding: utf-8 -*-
"""临时验证（本会话自建）：@FAMILY 3 = none 能否把该截面强制回 unresolved（契约 §e.4a）。

用自己的补充文件（只含指令行 + 板厚条目）跑 --extra，检查：
  * 报告里 32335 status=unresolved，且宏里没有 SPREF /USER_CIRCLE-SPEC/...
  * 未解析清单里出现该截面、reason 提到 @FAMILY 3 = none
  * 未知族键（@FAMILY 3 = XYZ）记 warning 且不启用
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
ROOT = os.path.dirname(PKG)
CLI = os.path.join(PKG, "engine", "cli.py")
SAMPLE = (r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\JLCJ2.jwd")
MAP = (r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\PKPM转PDMS截面匹配文件.txt")
TMP = os.path.join(HERE, "_acc_tmp")


def write_gbk(path, lines):
    with open(path, "wb") as fh:
        fh.write(("".join(l + "\r\n" for l in lines)).encode("gbk"))


def run(tag, rule_lines):
    extra = os.path.join(TMP, "extra_%s.txt" % tag)
    out = os.path.join(TMP, "override_%s.mac" % tag)
    rep = os.path.join(TMP, "override_%s.report.json" % tag)
    body = ["// 覆盖测试（本会话自建，不属于交付物）", "T120, /Concrete_Slab-SPEC/T120",
            "T100, /Concrete_Slab-SPEC/T100", "T0, /Concrete_Slab-SPEC/DEFAULT"]
    body += rule_lines
    write_gbk(extra, body)
    p = subprocess.run([sys.executable, CLI, "jwd2pdms", SAMPLE, "--out", out,
                        "--secmap", MAP, "--extra", extra, "--report", rep],
                       capture_output=True, cwd=ROOT)
    print("== %s: 退出码 %d" % (tag, p.returncode))
    r = json.load(open(rep, encoding="utf-8"))
    sec = r["sections"]
    print("   resolved=%s parametric=%s inferred=%s unresolved=%s"
          % (sec["resolved"], sec["parametric"], sec["inferred"], len(sec["unresolved"])))
    for d in sec["detail"]:
        if d["id"] == 32335:
            print("   32335: status=%s source=%s spec=%r desp=%s"
                  % (d["status"], d["source"], d["spec_path"], d["desp_params"]))
    for d in sec["unresolved"]:
        if d["id"] == 32335:
            print("   unresolved reason:", d["reason"][:160])
    for w in r["warnings"]:
        if "@FAMILY" in w:
            print("   warning:", w[:160])
    mac = open(out, "rb").read().decode("gbk")
    print("   宏里 Circle_Profile 出现次数 =", mac.count("/USER_CIRCLE-SPEC/Circle_Profile"))
    print("   宏里 -- UNRESOLVED SECTION 32335 =", "-- UNRESOLVED SECTION 32335" in mac)


run("none", ["@FAMILY 3 = none"])
run("unknown", ["@FAMILY 3 = XYZ"])
run("on", ["@FAMILY 3 = CIRCLE"])
