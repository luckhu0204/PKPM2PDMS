# -*- coding: utf-8 -*-
"""临时检查（本会话自建）：抽看 smoke.mac 里推断截面的构件块。"""
import io, os, re, json

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAC = os.path.join(PKG, "test", "_acc_tmp", "smoke.mac")
REP = os.path.join(PKG, "test", "_acc_tmp", "smoke.report.json")

raw = open(MAC, "rb").read()
t = raw.decode("gbk")
lines = t.split("\r\n")
print("bytes", len(raw), "lone LF", raw.replace(b"\r\n", b"").count(b"\n"))
print("Circle_Profile 行数 =", sum(1 for l in lines if "Circle_Profile" in l))
print("推断截面注释行数 =", sum(1 for l in lines if "推断截面" in l))
desp = [l.strip() for l in lines if l.strip().startswith("DESP")]
print("DESP 行数 =", len(desp), "示例：", desp[:4])
idx = [i for i, l in enumerate(lines) if "Circle_Profile" in l]
print("---- 第一个推断块（前后 8 行）----")
i0 = idx[0]
for j in range(max(0, i0 - 6), min(len(lines), i0 + 6)):
    print("   ", j + 1, lines[j])
print("---- 第 12 个推断块 ----")
i1 = idx[-1]
for j in range(max(0, i1 - 6), min(len(lines), i1 + 6)):
    print("   ", j + 1, lines[j])

rep = json.load(open(REP, encoding="utf-8"))
sec = rep["sections"]
print("---- report.sections ----")
print("resolved=%s parametric=%s inferred=%s unresolved=%s total=%s"
      % (sec["resolved"], sec["parametric"], sec["inferred"],
         len(sec["unresolved"]), sec["total"]))
for d in sec["detail"]:
    if d["status"] != "resolved":
        print("  *", {k: d[k] for k in ("id", "table", "name", "kind", "status", "source",
                                        "pkpm_name", "spec_path", "desp_params")})
for d in sec["detail"]:
    if d["status"] == "inferred":
        print("  evidence:", d["evidence"][:200], "...")
        print("  reason:", d["reason"][:200], "...")
print("warnings 里提到 inferred 的：")
for w in rep["warnings"]:
    if "推断" in w:
        print("   -", w[:220])
print("assumptions：")
for a in rep["assumptions"]:
    print("   -", a[:220])
