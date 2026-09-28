# -*- coding: utf-8 -*-
r"""引擎自检：宏结构 + 命名方案 + auto2pdms（〔R7〕2026-09-28 用户确认的命名方案）。

> 文件名沿用 R6 的名字（脚本名已被多处日志引用）；**内容按 R7 更新**：
> R6 的"唯一化模板/`!!pkpm2pdmsUniquename`"一节整体作废 —— 宏内不再有任何 PML 函数调用。

覆盖（全部为**本脚本独立重算**，不读被测代码的中间变量）：

A. 宏结构 + 命名（macgen，R7）
   A1 头部 5 行形态：`$S-  -- Synonym translation OFF` / `-- `+64 个 `-` 的分隔线 /
      `-- <用途>  Date: <时间>` / 一行 `-- 元素：…` / `ONERROR CONTINUE`
   A2 尾部 3 行形态：`-- End <用途>  Date: …` / `$S+  -- Synonym translation ON` / 分隔线
      ⇒ 头尾的"用途"串与 Date 串必须一致
   A3 宏本体**零运行期函数依赖**：`!!pkpm2pdms` / `$M ` / `FuncPath` /
      `pkpm2pdmsFuncMissing` / `pkpm2pdmsType` 全部 0 处；旧错误块
      （`LABEL /PKPM2PDMSERR` / `handle ANY` / `RETURN ERROR` / `endhandle`）也 0 处
   A4 名字查重（硬保证）：重解析全部 `NEW <TYPE> /名字` —— 无重名；STRU/FRMW/SBFR 的
      名字形如 `/<SITE名>_<段>`
   A5 底层 unnamed：`NEW SCTN` / `NEW PANE` / `NEW STWALL` 全部不带名字
   A6 头部 `-- 元素：…` 的逐类计数 == 宏内同类型 `NEW` 的实际条数（注释不许说谎）
   A7 字节纪律：GBK 可解、无 BOM、无孤立 LF

B. 自动识别子命令 auto2pdms（cli）
   B1 登记：`TOOLS` 含 auto2pdms；argparse 子命令存在，且**选项集与 jwd2pdms 逐项相同**
      （`--out/--site-name/--secmap/--extra/--project/--base/--angle/--unit/--report`，
      位置参数 dest=src）
   B2 jwd 分支：样本 JLCJ2.jwd → 退出码 0 + 报告 `options.auto_detected='jwd'` + `tool='auto2pdms'`
   B3 pdt 分支：样本 1_PM.pdt → 退出码 0 + `auto_detected='pdt'`
   B4 认不出 ⇒ 退出码 2（本脚本临时造的无特征二进制）；**不猜**
   B5 `--request`（.NET 路径，§p.5）四种键都能跑：`{"src":…,"site_name":…}` /
      `{"jwd":…}` / `{"pdt":…}` / 连字符 `site-name`，并核对 "--request 跑的宏" 与
      "命令行跑的宏" 除 Date 行外**逐字节一致**（同一执行函数）
   B6 判据只看**文件头**：把 JLCJ2.jwd 的字节装进 `.pdt` 扩展名的文件 ⇒ 仍判 jwd
   B7 〔R7〕缺 `--site-name` ⇒ 退出码 2（引擎不默认、不改名）

用法（工作目录任意）::

    python test\check_r6_macro_structure.py                 # 全跑（样本在 G 盘，只读）
    python test\check_r6_macro_structure.py --mac a.mac b.mac   # 只核对既有宏（跳过 B）
    python test\check_r6_macro_structure.py --skip-sample       # 只做 B1/B4 等不需样本的部分

退出码：0 = 全部通过；1 = 有 FAIL（逐条打印）。产物写在 ``test/_r6_out/``（覆盖写，不删任何文件）。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
ENGINE = os.path.join(PKG, "engine")
CLI = os.path.join(ENGINE, "cli.py")
OUT = os.path.join(HERE, "_r6_out")
PY = sys.executable

SAMPLE_DIR = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
SAMPLE_JWD = os.path.join(SAMPLE_DIR, "JLCJ2.jwd")
SAMPLE_PDT = os.path.join(SAMPLE_DIR, "1_PM.pdt")
SAMPLE_MAP = os.path.join(SAMPLE_DIR, "PKPM转PDMS截面匹配文件.txt")

#: 〔R7〕SITE 名由命令行/--request 传入（= .NET 侧直查试出的可用名）
SITE_NAME = "/PKPM2PDMS"

#: 头/尾的标准形态（与用户原件 …\P-TRANS\pkpm_section_DBOutput.txt 逐行同形）
SEP = "-- " + "-" * 64
FIRST_LINE = "$S-  -- Synonym translation OFF"
ONERROR = "ONERROR CONTINUE"
TAIL_ON = "$S+  -- Synonym translation ON"
ELEMENT_LINE_RE = re.compile(r"^-- 元素：(.*)$")
DATE_LINE_RE = re.compile(r"^-- (End )?.*  Date: .+$")
ELEM_TYPES = ("SITE", "ZONE", "STRU", "FRMW", "SBFR", "SCTN", "PANE", "STWALL")
UNNAMED_TYPES = ("SCTN", "PANE", "STWALL")
#: 〔R7〕中间层名字：/<SITE名>_<段>
NAME_RE = re.compile(r"^/<SITE>_(MF|FW|GR|EL\d+|EL\d+_(COLUMN|BEAM|HBRACE|VBRACE|SLAB|WALL))$"
                     .replace("<SITE>", re.escape(SITE_NAME.lstrip("/"))))

#: "插入的其他代码"的禁项（R6 问题②要删掉的 + R7 改 ONERROR CONTINUE 后不该再有的错误块）
FORBIDDEN = ("!!pkpm2pdms", "$M ", "FuncPath", "pkpm2pdmsFuncMissing", "pkpm2pdmsType",
             "LABEL /PKPM2PDMSERR", "handle ANY", "RETURN ERROR", "endhandle")

FAILS = []
N = [0]


def check(cond, label, detail=""):
    N[0] += 1
    print("  %-4s %s%s" % ("PASS" if cond else "FAIL", label,
                           ("   [%s]" % detail) if detail else ""))
    if not cond:
        FAILS.append(label)
    return bool(cond)


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def run_cli(args, cwd=None):
    p = subprocess.run([PY, CLI] + args, cwd=cwd or PKG,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return (p.returncode,
            p.stdout.decode("utf-8", "replace"),
            p.stderr.decode("utf-8", "replace"))


def mask_dates(text):
    """去掉带时间戳的两行（头部 `-- <用途>  Date: …`、尾部 `-- End …  Date: …`）。"""
    return "\r\n".join(l for l in text.split("\r\n") if not DATE_LINE_RE.match(l))


# --------------------------------------------------------------------------
# A. 宏结构 + 命名
# --------------------------------------------------------------------------
def check_macro(path):
    """核对一个宏文件的结构/命名/计数；返回是否本文件全部 PASS。"""
    print("\n=== A. 宏结构 + 命名：%s ===" % os.path.basename(path))
    before = len(FAILS)
    raw = read_bytes(path)
    try:
        text = raw.decode("gbk")
        check(True, "GBK 严格解码", "%d 字节" % len(raw))
    except UnicodeDecodeError as exc:
        check(False, "GBK 严格解码", str(exc))
        return False
    check(not raw.startswith(b"\xef\xbb\xbf"), "无 BOM")
    check(b"\n" not in raw.replace(b"\r\n", b""), "无孤立 LF（全部 CRLF）")

    lines = text.split("\r\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]                      # 末行 CRLF 之后的空串不算一行

    # ---- A1 头部 ----
    check(len(lines) >= 15, "宏至少 15 行", "%d 行" % len(lines))
    check(lines[0] == FIRST_LINE, "第 1 行 = %r" % FIRST_LINE, repr(lines[0]))
    check(lines[1] == SEP, "第 2 行 = `-- ` + 64 个 - 的分隔线（与 DB Output 宏同形）",
          "%d 字符" % len(lines[1]))
    m_head = re.match(r"^-- (.+)  Date: (.+)$", lines[2]) if len(lines) > 2 else None
    check(bool(m_head) and bool(m_head.group(1).strip()) and bool(m_head.group(2).strip()),
          "第 3 行 = `-- <用途>  Date: <时间>`", repr(lines[2]))
    m_el = ELEMENT_LINE_RE.match(lines[3]) if len(lines) > 3 else None
    check(bool(m_el), "第 4 行 = 一行 `-- 元素：…` 计数注释", repr(lines[3]))
    check(len(lines) > 4 and lines[4] == ONERROR,
          "第 5 行 = %r（〔R7〕出错继续）" % ONERROR, repr(lines[4]))
    body = next((i for i, l in enumerate(lines) if l.strip().startswith("NEW ")), None)
    check(body is not None, "找到元素主体第一行")
    if body is not None:
        check(lines[body].strip() == "NEW SITE %s" % SITE_NAME,
              "主体第一行 = `NEW SITE %s`" % SITE_NAME, repr(lines[body].strip()))
        extra = [l for l in lines[5:body] if l.strip() and not l.startswith("-- ")]
        check(not extra, "头部只有标准 5 行 + 可选 `-- ` 说明行", "%r" % (extra[:3],))

    # ---- A3 禁项 ----
    for bad in FORBIDDEN:
        hit = [i + 1 for i, l in enumerate(lines) if bad in l]
        check(not hit, "不含 %r（零运行期函数依赖 / 已删错误块）" % bad,
              ("命中行 %s" % hit[:5]) if hit else "0 处")

    # ---- A4 名字查重 + 形态 ----
    named, dups, bad_shape = {}, [], []
    for i, l in enumerate(lines, 1):
        m = re.match(r"^\s*NEW\s+(\w+)\s+(/\S+)\s*$", l)
        if not m:
            continue
        ty, nm = m.group(1), m.group(2)
        if nm in named:
            dups.append((nm, named[nm], ty, i))
        named[nm] = ty
        if ty in ("STRU", "FRMW", "SBFR") and not NAME_RE.match(nm):
            bad_shape.append(nm)
    check(not dups, "带名 NEW 的名字集合无重复（%d 个唯一名字）" % len(named), str(dups[:5]))
    check(not bad_shape, "中间层名字形如 /<SITE名>_<段>", str(bad_shape[:5]))
    check(sorted(n for n in named if named[n] == "SITE") == [SITE_NAME],
          "SITE 名 == 传入值 %r" % SITE_NAME,
          str(sorted(n for n in named if named[n] == "SITE")))

    # ---- A5 底层 unnamed ----
    counts = {t: 0 for t in ELEM_TYPES}
    unnamed = {t: 0 for t in UNNAMED_TYPES}
    named_bottom = []
    for i, l in enumerate(lines, 1):
        s = l.strip()
        if not s.startswith("NEW "):
            continue
        toks = s.split()
        if len(toks) < 2 or toks[1] not in counts:
            continue
        counts[toks[1]] += 1
        if toks[1] in unnamed:
            if len(toks) == 2:
                unnamed[toks[1]] += 1
            else:
                named_bottom.append((i, s))
    check(not named_bottom, "SCTN/PANE/STWALL 全部无名创建（`NEW <T>`）", str(named_bottom[:3]))
    check(all(unnamed[t] == counts[t] for t in UNNAMED_TYPES),
          "无名计数对平", "无名 %s / 总数 %s" % (unnamed, counts))
    check(sum(unnamed.values()) > 0, "无名底层元素条数 > 0", "%d" % sum(unnamed.values()))

    # ---- A6 头部计数注释 vs 实际条数 ----
    hdr_counts = {}
    if m_el:
        for part in m_el.group(1).split(" / "):
            mo = re.match(r"^(\w+) (\d+)$", part.strip())
            if mo:
                hdr_counts[mo.group(1)] = int(mo.group(2))
    check(sorted(hdr_counts) == sorted(counts)
          and all(hdr_counts[k] == counts[k] for k in hdr_counts),
          "头部 `-- 元素：…` 计数 == 宏内实际 NEW 条数",
          "注释 %s / 实际 %s" % (hdr_counts, counts))

    # ---- A2 尾部 ----
    tail = lines[-3:]
    m_end = re.match(r"^-- End (.+)  Date: (.+)$", tail[0])
    check(bool(m_end), "尾: `-- End <用途>  Date: <时间>`", repr(tail[0]))
    check(tail[1] == TAIL_ON, "尾: %r" % TAIL_ON, repr(tail[1]))
    check(tail[2] == SEP, "尾: 分隔线（与宏头第 2 行相同）", "%d 字符" % len(tail[2]))
    if m_head and m_end:
        check(m_head.group(1) == m_end.group(1), "头尾「用途」串一致", repr(m_head.group(1)))
        check(m_head.group(2) == m_end.group(2), "头尾 Date 串一致", repr(m_head.group(2)))
    check(not any("ONERROR GOLABEL" in l or "GOLABEL" in l for l in lines),
          "不再出现 GOLABEL 错误块（R7 改 ONERROR CONTINUE，无 LABEL/handle 尾）")

    print("  统计：%s" % json.dumps(
        {"lines": len(lines), "named_new": len(named), "unnamed": sum(unnamed.values()),
         "counts": counts, "sep_len": len(lines[1])}, ensure_ascii=False))
    return len(FAILS) == before


# --------------------------------------------------------------------------
# B. auto2pdms
# --------------------------------------------------------------------------
def check_auto2pdms(skip_sample=False):
    print("\n=== B. auto2pdms 子命令 ===")
    sys.path.insert(0, ENGINE)
    import cli as cli_mod

    check("auto2pdms" in cli_mod.TOOLS, "TOOLS 含 auto2pdms", str(cli_mod.TOOLS))
    parser = cli_mod.build_parser()
    subs = {}
    for act in (parser._subparsers._group_actions if parser._subparsers else []):
        subs.update(act.choices)
    check("auto2pdms" in subs, "argparse 已注册 auto2pdms", "%d 个子命令" % len(subs))
    a_new, a_ref = subs.get("auto2pdms"), subs.get("jwd2pdms")
    if a_new is not None and a_ref is not None:
        opt_new = sorted(o for x in a_new._actions for o in x.option_strings)
        opt_ref = sorted(o for x in a_ref._actions for o in x.option_strings)
        check(opt_new == opt_ref, "选项集与 jwd2pdms 逐项相同", str(opt_new))
        check("--site-name" in opt_new, "〔R7〕选项集含 --site-name", str(opt_new))
        pos_new = [x.dest for x in a_new._actions if not x.option_strings]
        pos_ref = [x.dest for x in a_ref._actions if not x.option_strings]
        check(pos_new == ["src"] and pos_ref == ["jwd"],
              "位置参数 dest = src（对照 jwd2pdms 的 jwd）",
              "auto=%s jwd=%s" % (pos_new, pos_ref))
        # §p.5 的 --request 还原：src / jwd / pdt 三个键都落同一个位置槽；site_name 落 --site-name
        for key in ("src", "jwd", "pdt"):
            argv = cli_mod._request_to_argv(parser, "auto2pdms",
                                            {key: "X.jwd", "out": "Y.mac",
                                             "site_name": SITE_NAME})
            check(argv[:2] == ["auto2pdms", "X.jwd"] and "--site-name" in argv,
                  "--request 键 %r + site_name → argv %s" % (key, argv))
        argv_h = cli_mod._request_to_argv(parser, "auto2pdms",
                                          {"src": "X.jwd", "out": "Y.mac",
                                           "site-name": SITE_NAME})
        check("--site-name" in argv_h, "连字符键 site-name 同样认", str(argv_h))
        bad = False
        try:
            cli_mod._request_to_argv(parser, "auto2pdms", {"nope": "X"})
        except cli_mod.InputError:
            bad = True
        check(bad, "--request 未知键仍报错（协议不放宽）")

    os.makedirs(OUT, exist_ok=True)
    mac_j = os.path.join(OUT, "cli_jwd.mac")
    mac_p = os.path.join(OUT, "cli_pdt.mac")
    if skip_sample:
        print("  （--skip-sample：跳过需要 G 盘样本的 B2/B3/B5/B6/B7）")
        return mac_j, mac_p
    if not (os.path.isfile(SAMPLE_JWD) and os.path.isfile(SAMPLE_PDT)):
        check(False, "样本可读（G 盘）", SAMPLE_DIR)
        return mac_j, mac_p

    def run_auto(src, mac, tag, extra=()):
        rep = os.path.join(OUT, "%s.report.json" % tag)
        code, out, err = run_cli(["auto2pdms", src, "--out", mac, "--secmap", SAMPLE_MAP,
                                  "--project", "R7CHK", "--site-name", SITE_NAME]
                                 + list(extra))
        r = json.load(open(rep, encoding="utf-8")) if os.path.isfile(rep) else {}
        return code, out, err, r

    # ---- B2 / B3 ----
    code, out, err, rj = run_auto(SAMPLE_JWD, mac_j, "cli_jwd")
    check(code == 0, "B2 jwd：退出码 0", "code=%d %s" % (code, (out + err)[-160:]))
    check(rj.get("tool") == "auto2pdms", "B2 jwd：报告 tool='auto2pdms'", str(rj.get("tool")))
    check(rj.get("options", {}).get("auto_detected") == "jwd",
          "B2 jwd：报告 options.auto_detected='jwd'",
          str(rj.get("options", {}).get("auto_detected")))
    check(rj.get("source_format") == "jwd", "B2 jwd：报告 source_format='jwd'",
          str(rj.get("source_format")))
    check(rj.get("options", {}).get("site_name") == SITE_NAME,
          "B2 jwd：〔R7〕报告 options.site_name == %r" % SITE_NAME,
          str(rj.get("options", {}).get("site_name")))
    ren = rj.get("renames") or []
    check(len(ren) == 1 and ren[0].get("kind") == "site-name-probe"
          and ren[0].get("site_name") == SITE_NAME,
          "B2 jwd：〔R7〕renames = SITE 名探测记录", json.dumps(ren, ensure_ascii=False)[:100])
    st = rj.get("stats") or {}
    check(st.get("used_names_count") == len(st.get("used_names") or [])
          and st.get("used_names_count") == len(set(st.get("used_names") or [])),
          "B2 jwd：〔R7〕stats.used_names 无重复且与计数对平",
          "%r / %d" % (st.get("used_names_count"), len(st.get("used_names") or [])))
    check(isinstance(st.get("unnamed_count"), int) and st["unnamed_count"] > 0,
          "B2 jwd：〔R7〕stats.unnamed_count = %r" % st.get("unnamed_count"))
    check(any("自动识别" in a for a in rj.get("assumptions", [])),
          "B2 jwd：assumptions 记录了自动识别",
          str([a for a in rj.get("assumptions", []) if "自动识别" in a][:1]))
    # 同一要素：识别分支的 counts 与显式 jwd2pdms 逐键相等（同一执行函数）
    code2, out2, err2 = run_cli(["jwd2pdms", SAMPLE_JWD, "--out",
                                 os.path.join(OUT, "explicit_jwd.mac"),
                                 "--secmap", SAMPLE_MAP, "--project", "R7CHK",
                                 "--site-name", SITE_NAME])
    r2 = json.load(open(os.path.join(OUT, "cli_jwd.report.json"), encoding="utf-8"))
    r_plain = json.load(open(os.path.join(OUT, "explicit_jwd.report.json"), encoding="utf-8"))
    check(code2 == 0 and r2.get("counts") == r_plain.get("counts"),
          "B2 jwd：counts 与显式 jwd2pdms 逐键相等（同一执行函数）",
          "%s" % (r2.get("counts"),))

    code, out, err, rp = run_auto(SAMPLE_PDT, mac_p, "cli_pdt")
    check(code == 0, "B3 pdt：退出码 0", "code=%d %s" % (code, (out + err)[-160:]))
    check(rp.get("options", {}).get("auto_detected") == "pdt",
          "B3 pdt：报告 options.auto_detected='pdt'",
          str(rp.get("options", {}).get("auto_detected")))
    check(rp.get("source_format") == "pdt", "B3 pdt：报告 source_format='pdt'",
          str(rp.get("source_format")))

    # ---- B4 认不出 ⇒ 码 2 ----
    junk = os.path.join(OUT, "no_feature.bin")
    with open(junk, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 8)
    code, out, err, _r = run_auto(junk, os.path.join(OUT, "junk.mac"), "junk")
    check(code == 2, "B4 认不出：退出码 2（不猜）", "code=%d" % code)
    check("无法自动识别" in (out + err), "B4 认不出：报错文案含「无法自动识别」",
          ((out + err).strip().splitlines() or [""])[0][:130])

    # ---- B7 缺 --site-name ⇒ 码 2（引擎不默认、不改名） ----
    rep7 = os.path.join(OUT, "nosite.report.json")
    code, out, err = run_cli(["auto2pdms", SAMPLE_JWD, "--out",
                              os.path.join(OUT, "nosite.mac"), "--secmap", SAMPLE_MAP,
                              "--project", "R7CHK", "--report", rep7])
    check(code == 2 and "site_name" in (out + err),
          "B7 缺 --site-name ⇒ 退出码 2 且报错含 site_name",
          "code=%d %s" % (code, (out + err).strip().splitlines()[-1][:110]))
    check(not os.path.isfile(os.path.join(OUT, "nosite.mac")), "B7 缺 site_name 时不写宏")

    # ---- B5 --request（.NET 路径 §p.5）+ 与命令行等价 ----
    for key in ("src", "jwd", "pdt"):
        req = os.path.join(OUT, "req_%s.json" % key)
        mac = os.path.join(OUT, "req_%s.mac" % key)
        with open(req, "w", encoding="utf-8") as fh:
            json.dump({"tool": "auto2pdms",
                       "args": {key: SAMPLE_JWD, "out": mac, "secmap": SAMPLE_MAP,
                                "project": "R7CHK", "site_name": SITE_NAME}},
                      fh, ensure_ascii=False)
        p = subprocess.run([PY, CLI, "--request", req], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
        check(p.returncode == 0, "B5 --request 键 %r → 退出码 0" % key,
              "code=%d %s" % (p.returncode, p.stdout.decode("utf-8", "replace")[-120:]))
    a = mask_dates(read_bytes(mac_j).decode("gbk"))
    b = mask_dates(read_bytes(os.path.join(OUT, "req_src.mac")).decode("gbk"))
    check(a == b, "B5 --request 与命令行产物（除 Date 行）逐字节一致", "len=%d/%d"
          % (len(a), len(b)))

    # ---- B6 判据只看文件头 ----
    swapped = os.path.join(OUT, "magic_swap.pdt")          # jwd 字节 + .pdt 扩展名
    with open(swapped, "wb") as fh:
        fh.write(read_bytes(SAMPLE_JWD))
    code, out, err, r = run_auto(swapped, os.path.join(OUT, "swap.mac"), "swap")
    check(code == 0 and r.get("options", {}).get("auto_detected") == "jwd",
          "B6 扩展名 .pdt 但内容是 SQLite ⇒ 仍判 jwd（只看文件头）",
          "code=%d detected=%s" % (code, r.get("options", {}).get("auto_detected")))
    return mac_j, mac_p


def main():
    ap = argparse.ArgumentParser(description="引擎自检（R7：宏结构 + 命名 + auto2pdms）")
    ap.add_argument("--mac", nargs="*", default=None,
                    help="只核对既有宏文件（跳过 B 段）")
    ap.add_argument("--skip-sample", action="store_true",
                    help="不做需要 G 盘样本的检查")
    args = ap.parse_args()

    print("=" * 78)
    print("引擎自检：宏结构 + R7 命名方案（macgen）+ 自动识别子命令（cli.auto2pdms）")
    print("=" * 78)

    if args.mac:
        macs = list(args.mac)
    else:
        mac_j, mac_p = check_auto2pdms(skip_sample=args.skip_sample)
        macs = [] if args.skip_sample else [mac_j, mac_p]
    for p in macs:
        if os.path.isfile(p):
            check_macro(p)
        else:
            check(False, "宏文件存在：%s" % p)

    print("\n" + "-" * 78)
    print("汇总：断言 %d 项，FAIL %d 项" % (N[0], len(FAILS)))
    for f in FAILS:
        print("  FAIL: %s" % f)
    print("结论：%s" % ("全部通过" if not FAILS else "存在 FAIL"))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
