# -*- coding: utf-8 -*-
"""R3 验收③：核对生成的**真实**宏里每个创建元素之前都有唯一化调用，并把计数对平。

跑法：``python PKPM2PDMS导入导出\\test\\_s3_cli\\check_r3_macro.py``

依据：契约 §o.4 的**逐字模板**（engine/macgen.py:581-608 的 ``emit_new`` 是生成侧唯一出处）::

    !pkpm2pdmsType = '<TYPE>'
    !n = !!pkpm2pdmsUniquename('<名>')
    if (!n eq '') then
      var !pkpm2pdmsFatal EXIST /$!n
    endif
    NEW <TYPE> $!n

审计对象：test/out/r3.mac（jwd2pdms）与 test/out/r3_pdt.mac（pdt2pdms）。
PLOOP/PAVERT 无名（§o.4 的 TYPE 清单里没有），不要求模板。
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), "test", "out")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

FAILS = []
NAMED_TYPES = ("SITE", "ZONE", "STRU", "FRMW", "SBFR", "SCTN", "PANE", "STWALL")
RE_NEW = re.compile(r"^(\s*)NEW (SITE|ZONE|STRU|FRMW|SBFR|SCTN|PANE|STWALL) (\S+)$")
RE_PLOOP = re.compile(r"^\s*NEW (PLOOP|PAVERT)\b")


def check(cond, label, detail=""):
    print("  [%s] %s %s" % ("OK" if cond else "FAIL", label, detail))
    if not cond:
        FAILS.append(label)


def audit(mac_name, report_name, expect):
    """审计一份宏；``expect`` = 按 TYPE 的期望创建数（None = 不核数）。"""
    print("=" * 78)
    print("审计 %s（期望 %s）" % (mac_name, expect))
    path = os.path.join(OUT, mac_name)
    raw = open(path, "rb").read()
    check(not raw.startswith(b"\xef\xbb\xbf") and b"\n" not in raw.replace(b"\r\n", b""),
          "%s 无 BOM 且只有 CRLF（§g）" % mac_name, "%d 字节" % len(raw))
    lines = raw.decode("gbk").split("\r\n")

    # ---- 头/尾（§o.5 + §o.4 前置） ----
    stripped = [l.strip() for l in lines]
    check(stripped[0].startswith("$S-"), "首行 $S-", stripped[0][:60])
    check("ONERROR GOLABEL /PKPM2PDMSERR" in stripped, "宏头 ONERROR GOLABEL /PKPM2PDMSERR（§o.5）")
    check("if (defined(!!pkpm2pdmsUniquename)) then" in stripped,
          "唯一化函数可用性检查（defined()，§o.4）")
    check("var !pkpm2pdmsFuncMissing EXIST /" in stripped,
          "函数缺失 ⇒ 故障注入行（§o.4 机制）")
    tail = [l for l in stripped if l in ("LABEL /PKPM2PDMSERR", "handle ANY", "$S+",
                                         "RETURN ERROR", "endhandle")]
    check(tail == ["LABEL /PKPM2PDMSERR", "handle ANY", "$S+", "RETURN ERROR", "endhandle"],
          "宏尾 LABEL/handle/$S+/RETURN ERROR/endhandle 依次齐全（§o.5）", str(tail))

    # ---- 每个 NEW 都有前置模板 ----
    counts = {t: 0 for t in NAMED_TYPES}
    nameless = 0
    uniq_calls = 0
    bad = []
    uniq_names = []
    for i, l in enumerate(lines):
        m = RE_NEW.match(l)
        if not m:
            if RE_PLOOP.match(l):
                nameless += 1
            continue
        ind, etype, nm = m.group(1), m.group(2), m.group(3)
        counts[etype] += 1
        if nm != "$!n":
            bad.append((i + 1, "NEW 名不是 $!n", l.strip()[:80]))
            continue
        tmpl = [
            ind + "!pkpm2pdmsType = '%s'" % etype,
            ind + "!n = !!pkpm2pdmsUniquename('",
            ind + "if (!n eq '') then",
            ind + "  var !pkpm2pdmsFatal EXIST /$!n",
            ind + "endif",
        ]
        if i < len(tmpl):
            bad.append((i + 1, "模板行不足", ""))
            continue
        block = lines[i - len(tmpl):i]
        for want, got in zip(tmpl, block):
            if not got.startswith(want):
                bad.append((i + 1, "模板行不匹配", "期望 %r / 实际 %r"
                            % (want.strip()[:60], got.strip()[:60])))
                break
        else:
            uniq_calls += 1
            uniq_names.append(block[1].split("!!pkpm2pdmsUniquename('", 1)[1].rsplit("')", 1)[0])
    check(not bad, "每个 NEW <TYPE> $!n 之前都是 §o.4 逐字模板（5 行）", bad[:3])
    check(all(n.startswith("/") for n in uniq_names),
          "传给 !!pkpm2pdmsUniquename 的名字都带前导 /（§o.1）",
          "" if all(n.startswith("/") for n in uniq_names)
          else [n for n in uniq_names if not n.startswith("/")][:3])

    total_new = sum(counts.values())
    check(uniq_calls == total_new,
          "唯一化调用数 == 创建元素总数（§o.4：全部走模板）",
          "%d vs %d" % (uniq_calls, total_new))
    check(counts == expect, "分类型创建数与期望一致（与 report.counts 对平）",
          "%s vs %s" % (counts, expect))
    print("     无名的 NEW（PLOOP/PAVERT，§o.4 清单外，不要求模板）：%d" % nameless)

    # ---- 与 report.json 对平 ----
    rep = json.load(io.open(os.path.join(OUT, report_name), encoding="utf-8"))
    c = rep["counts"]
    check("renames" in rep and rep["renames"] == [],
          "报告含 renames 键且生成方向为 []（§h v3/§o.7）", repr(rep.get("renames"))[:60])
    expect_counts = {
        "SCTN": c["members_total"],
        "PANE": c["slabs"],
        "STWALL": c["walls"],
        "FRMW": c["levels"] + 2,               # 每层 /STL_FRAME/EL<n> + /FLOOR&WALL + /GRID
        "SBFR": 4 * c["levels"] + 2,           # 每层 4 组 + /SLAB + /WALL
        "SITE": 1, "ZONE": 1, "STRU": 1,
    }
    check(counts == expect_counts,
          "宏内 NEW 分类 == report.counts 推出的期望（元素总数对平）",
          "%s" % ({k: (counts[k], expect_counts[k]) for k in counts
                   if counts[k] != expect_counts[k]} or "全部一致"))
    cmd = rep.get("stats", {}).get("commands") or {}
    check(cmd.get("唯一化调用") == total_new and cmd.get("NEW SCTN") == counts["SCTN"],
          "生成侧计数（stats.commands）与审计一致",
          "唯一化调用=%s NEW SCTN=%s" % (cmd.get("唯一化调用"), cmd.get("NEW SCTN")))
    check(rep["tool"] in ("jwd2pdms", "pdt2pdms"), "报告 tool", rep["tool"])
    return total_new


def main():
    n1 = audit("r3.mac", "r3.report.json",
               {"SITE": 1, "ZONE": 1, "STRU": 1, "FRMW": 7, "SBFR": 22,
                "SCTN": 811, "PANE": 222, "STWALL": 0})
    n2 = audit("r3_pdt.mac", "r3_pdt.report.json",
               {"SITE": 1, "ZONE": 1, "STRU": 1, "FRMW": 13, "SBFR": 46,
                "SCTN": 1046, "PANE": 331, "STWALL": 4})
    print("=" * 78)
    print("创建元素总数：r3.mac=%d、r3_pdt.mac=%d（每个都有前置唯一化调用）" % (n1, n2))
    print("FAIL 项：%d %s" % (len(FAILS), FAILS if FAILS else ""))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
