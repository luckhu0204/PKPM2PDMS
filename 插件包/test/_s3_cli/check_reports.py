# -*- coding: utf-8 -*-
"""S3 产物核对：报告结构 + 宏的字节纪律（GBK 无 BOM + CRLF）。

跑法：``python test\\_s3_cli\\check_reports.py <report.json> [<artifact> ...]``
只读产物；不做任何写入。
"""
from __future__ import annotations

import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEYS = ["contract_version", "tool", "source", "source_format", "output", "options",
        "assumptions", "counts", "sections", "geometry_anomalies", "skipped",
        "warnings", "errors", "stats"]


def main(argv):
    fails = []
    rep_path = argv[0]
    raw = open(rep_path, "rb").read()
    print("报告 %s：%d 字节，BOM=%s，CRLF 行数=%d"
          % (rep_path, len(raw), raw.startswith(b"\xef\xbb\xbf"), raw.count(b"\r\n")))
    if raw.startswith(b"\xef\xbb\xbf"):
        fails.append("报告带 BOM（§g 禁止）")
    rep = json.loads(raw.decode("utf-8"))
    missing = [k for k in KEYS if k not in rep]
    print("顶层键缺失：%s" % (missing or "无"))
    if missing:
        fails.append("报告缺键 %s" % missing)
    print("tool=%s source_format=%s" % (rep["tool"], rep["source_format"]))
    print("options=%s" % json.dumps(rep["options"], ensure_ascii=False))
    print("counts=%s" % json.dumps(rep["counts"], ensure_ascii=False))
    sec = rep["sections"]
    print("sections: resolved=%s parametric=%s unresolved_n=%d total=%s detail=%d"
          % (sec.get("resolved"), sec.get("parametric"), len(sec.get("unresolved") or []),
             sec.get("total"), len(sec.get("detail") or [])))
    for d in (sec.get("unresolved") or []):
        print("   unresolved: id=%s table=%s kind=%s name=%r used_by=%s candidate_keys=%s"
              % (d.get("id"), d.get("table"), d.get("kind"), d.get("name"),
                 d.get("used_by"), d.get("candidate_keys")))
        print("               reason=%s" % d.get("reason"))
    # §h：unresolved 必须是 detail 的子集
    det_ids = [(d.get("table"), d.get("id"), d.get("name"), d.get("status"))
               for d in (sec.get("detail") or [])]
    un_ids = [(d.get("table"), d.get("id"), d.get("name"), d.get("status"))
              for d in (sec.get("unresolved") or [])]
    sub = all(x in det_ids for x in un_ids)
    print("unresolved ⊂ detail：%s（detail 中 status=unresolved 的条数=%d）"
          % (sub, sum(1 for x in det_ids if x[3] == "unresolved")))
    if not sub or sum(1 for x in det_ids if x[3] == "unresolved") != len(un_ids):
        fails.append("unresolved 不是 detail 的严格子集")
    print("geometry_anomalies=%d（W- 分类：%s）" % (
        len(rep["geometry_anomalies"]),
        {p: sum(1 for x in rep["geometry_anomalies"] if x.startswith(p))
         for p in ("W-MEM-SHORT", "W-MEM-ZRANGE", "W-MEM-Z-END", "ECC:")}))
    print("skipped=%d：%s" % (len(rep["skipped"]),
                              [ (s.get("what"), s.get("count")) for s in rep["skipped"] ]))
    print("warnings=%d，误差核对：含 macgen 交叉核对 warning：%s"
          % (len(rep["warnings"]),
             any("MacroPlan.sections" in w for w in rep["warnings"])))
    for w in rep["warnings"][:6]:
        print("   - " + w[:150])
    print("assumptions=%d" % len(rep["assumptions"]))
    for a in rep["assumptions"]:
        print("   - " + a[:150])
    print("errors=%s" % (rep["errors"] or "无"))
    print("stats 键：%s" % sorted(rep["stats"]))

    for art in argv[1:]:
        b = open(art, "rb").read()
        ok = True
        if art.endswith(".mac"):
            txt = None
            try:
                txt = b.decode("gbk")
            except UnicodeDecodeError as exc:
                ok = False
                fails.append("%s 不是 GBK：%s" % (art, exc))
            if b.startswith(b"\xef\xbb\xbf"):
                ok = False
                fails.append("%s 带 BOM" % art)
            lone = b.replace(b"\r\n", b"").count(b"\n")
            if lone:
                ok = False
                fails.append("%s 有 %d 个孤立 LF" % (art, lone))
            n_lines = len(b.decode("gbk").splitlines())
            print("产物 %s：%d 字节 / %d 行(按 CRLF 计) / GBK 可解码=%s / 无 BOM=%s / "
                  "孤立 LF=%d / splitlines=%d 行"
                  % (art, len(b), b.count(b"\r\n"), ok,
                     not b.startswith(b"\xef\xbb\xbf"), lone, n_lines))
            txt = b.decode("gbk")
            print("   首行：%s" % txt.splitlines()[0])
            print("   末行：%s" % txt.splitlines()[-1])
            # 报告 ↔ 产物的交叉核对：未解析截面的构件数 = 宏内 -- UNRESOLVED SECTION 标记数
            n_sctn = sum(1 for l in txt.splitlines()
                         if l.strip().startswith("-- UNRESOLVED SECTION") and " SCTN" in l)
            n_pane = sum(1 for l in txt.splitlines()
                         if l.strip().startswith("-- UNRESOLVED SECTION") and " PANE" in l)
            want_sctn = sum(v for d in (sec.get("unresolved") or [])
                            if d.get("table") in ("beam", "col", "brace")
                            for v in (d.get("used_by") or {}).values())
            want_pane = sum(v for d in (sec.get("unresolved") or [])
                            if d.get("table") == "panel"
                            for v in (d.get("used_by") or {}).values())
            print("宏内 -- UNRESOLVED SECTION：SCTN %d / PANE %d；报告里未解析截面的构件数："
                  "SCTN %d / PANE %d" % (n_sctn, n_pane, want_sctn, want_pane))
            if (n_sctn, n_pane) != (want_sctn, want_pane):
                fails.append("报告与宏的未解析标记数不一致（报告 %s vs 宏 %s）"
                             % ((want_sctn, want_pane), (n_sctn, n_pane)))
        else:
            try:
                b.decode("utf-8")
            except UnicodeDecodeError as exc:
                ok = False
                fails.append("%s 不是 UTF-8：%s" % (art, exc))
            print("产物 %s：%d 字节 / UTF-8=%s / BOM=%s"
                  % (art, len(b), ok, b.startswith(b"\xef\xbb\xbf")))
    print("\nFAIL：%s" % (fails or "无"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
