# -*- coding: utf-8 -*-
"""R2 自检：`engine/dbmacro.py`（生成器）× `engine/dbparse.py`（解析器）。

跑四组检查（全部真实执行、失败即非 0 退出）：

A. 解析用户原件宏 ``PKPM（PDMS数据库）.txt``：≥2,920 条规格 + 元素计数与侦察报告逐项对齐
   + 抽查若干条的 PARA/dims/shapeval；
B. 与匹配文件交叉核对：失效 260 / 大小写差异 759 的口径复盘（759 需要 DLL 的 2,326 个名，
   本脚本从侦察产物 ``_recon/dbsect/_dll_pairs_full.json`` + ``_dll_tokens.json`` 重建）；
C. 生成器 × 解析器闭环：内置转化表（3,176）→ 生成宏 → 写盘 → 读回 → 逐条比对（列出不可逆项）；
   另跑 jwd 侧的 ``table_from_jwd`` → 生成 → 读回；
D. 纪律与安全：纯 ASCII、CRLF、`NEW`:END 1:1、`OLD` 无 END、引用只在第二遍、
   §l.3.4 的不变量、唯一名后缀、清场版目标、禁用容器名的负向控制。

用法：``python test/check_v2_db.py``（可选 ``--quiet`` 只打印汇总）。
只读用户原件；产物写在 ``test/_db_out/``。
"""

import argparse
import json
import os
import re
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ENG = os.path.join(os.path.dirname(_HERE), "engine")
if _ENG not in sys.path:
    sys.path.insert(0, _ENG)

import dbmacro                                              # noqa: E402
import dbparse                                              # noqa: E402
import jwd_read                                             # noqa: E402
import secmap as secmap_mod                                 # noqa: E402
import sectionlib as slib                                    # noqa: E402

SAMPLES = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
CAT_MACRO = os.path.join(SAMPLES, "PKPM（PDMS数据库）.txt")
MATCH_FILE = os.path.join(SAMPLES, "PKPM转PDMS截面匹配文件.txt")
SAMPLE_JWD = os.path.join(SAMPLES, "JLCJ2.jwd")
RECON = r"D:\AI_Work\PKPM数据解析\_recon\dbsect"
OUTDIR = os.path.join(_HERE, "_db_out")

FAILED = []
CHECKS = []


def check(label, ok, detail=""):
    CHECKS.append((label, bool(ok), detail))
    if not ok:
        FAILED.append(label)
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                           ("  —— " + detail) if detail else ""))
    return bool(ok)


def section(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def dll_names_from_recon():
    """从侦察产物重建 DLL 的 2,326 个 PKPM 名（复刻 ``_recon/dbsect/21_final.py`` 的
    ``explicit`` + ``carry`` 规则；**只读**，只服务 759 的口径复盘）。"""
    pairs = json.load(open(os.path.join(RECON, "_dll_pairs_full.json"), encoding="utf-8"))
    tokens = json.load(open(os.path.join(RECON, "_dll_tokens.json"), encoding="utf-8"))
    code_re = re.compile(r"^[-\d]+(,[^,]*)*$")
    lo, hi = 0x20640, 0x33A90
    explicit, carry = {}, {}
    last = None
    for t in tokens:
        if code_re.match(t["s"]):
            last = t["s"]
        elif last is not None:
            carry[t["s"]] = last
    for p in pairs:
        if lo <= p["name_off"] <= hi and lo <= p["code_off"] <= hi:
            explicit[p["name"]] = p["code"]
    return sorted(set(list(explicit) + list(carry)))


def walk(el):
    for k in el.kids:
        yield k
        for g in walk(k):
            yield g


def invariants(text, label):
    """生成物必须满足的结构不变量（契约 §l.3.4 / recon §1.1）。"""
    macro = dbparse.parse_macro(text)
    ends = len(re.findall(r"(?m)^\s*END\s*$", text))
    news = len([e for e in macro.elements if e.op == "NEW"])
    check("%s：NEW 与 END 严格 1:1" % label, news == ends, "NEW=%d END=%d" % (news, ends))
    # OLD 一律无 END：OLD 的条数与 NEW+OLD 的 END 数无关 ⇒ 用文本证据：OLD 块内不得出现 END
    lines = [ln.strip() for ln in text.replace("\r\n", "\n").split("\n")]
    bad = []
    for i, ln in enumerate(lines):
        if ln.startswith("OLD "):
            j = i + 1
            while j < len(lines) and lines[j] and not re.match(
                    r"^(OLD|NEW|LABEL|handle|INPUT|--)", lines[j]):
                if lines[j] == "END":
                    bad.append(i + 1)
                j += 1
    check("%s：OLD 块内没有 END（契约 §l.3.4-2）" % label, not bad, "命中行 %s" % bad[:5])
    # 引用型属性只在第二遍
    pass1 = text.split("-- pass 2")[0]
    refs = [k for k in ("PSTR", "GSTR", "DTRE", "CATR", "NARE")
            if re.search(r"(?m)^\s*%s\b" % k, pass1)]
    check("%s：PSTR/GSTR/DTRE/CATR/NARE 只在第二遍（§l.3.4-3）" % label, not refs,
          "第一遍出现 %s" % refs)
    # SPCOMPONENT 名 == /<STCATEGORY>-SPEC/<SPRFILE>
    comps = [e.name for e in macro.elements if e.op == "NEW" and e.type == "SPCOMPONENT"]
    comps2spr = {}
    for e in macro.olds:
        if e.type == "SPCOMPONENT" and e.name:
            v = e.get("CATR")
            if v:
                # §0.4-9：CATR 值可带父级限定链（`SPRFILE /X of STCATEGORY /Y of …`），
                # 本体名 = 第一个 " of " 之前链头的最后一个 token
                head = []
                for tok in v.split():
                    if tok.upper() == "OF":
                        break
                    head.append(tok)
                comps2spr[e.name] = "/" + (head[-1] if head else "").lstrip("/")
    bad = [c for c in comps if c.rsplit("/", 1)[0] + "/" !=
           "/%s-SPEC/" % c.split("/")[1][:-len("-SPEC")] or len(c.split("/")) != 3]
    check("%s：SPCOMPONENT 名 == /<族>-SPEC/<轮廓>（§l.3.4-1）" % label, not bad,
          "异常 %s" % bad[:3])
    # NARE == 该 PTSSET 的 PLINE 条数
    idx = dbparse._Index(macro)
    bad = []
    for e in macro.olds:
        if e.type == "PTSSET":
            nare = re.search(r"(\d+)", e.get("NARE") or "")
            for ts in idx._families_of_old(e):
                n_pl = len(ts.find("PLINE"))
                if not nare or int(nare.group(1)) != n_pl:
                    bad.append((e.name, e.get("NARE"), n_pl))
    check("%s：NARE == PTSSET 里的 PLINE 条数（§l.3.4-4）" % label, not bad, str(bad[:3]))
    # len(PARA) == count(PURP=PARA)；纯 DESP 族的 PARA 按原件惯例写占位 0 或 nDESP 个值
    bad = []
    for fam in [e for e in macro.elements if e.op == "NEW" and e.type == "STCATEGORY"]:
        ps_ = idx.dtset_params(fam)
        n_para = len([p for p in ps_ if p["purpos"] == "PARA"])
        n_desp = len([p for p in ps_ if p["purpos"] == "DESP"])
        for spr in fam.find("SPRFILE"):
            toks = (spr.get("PARA") or "").split()
            ok = (len(toks) == n_para)
            if n_para == 0 and n_desp:
                # 原件 /USER_H 就是这种写法（PARA 250 250 500 8 10 10，recon §3.4/§3.7）
                ok = toks == ["0"] or len(toks) == n_desp
            if not ok:
                bad.append((fam.name, spr.name, len(toks), n_para, n_desp))
    check("%s：len(SPRFILE.PARA) == count(PURP=PARA)（§l.3.4-5）" % label, not bad,
          str(bad[:3]))
    return macro


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    if not os.path.isdir(OUTDIR):
        os.makedirs(OUTDIR)
    t0 = time.time()
    builtin = slib.load_builtin_table()
    print("sectionlib 内置表：%d 条（%s）" % (len(builtin.recs), slib.BUILTIN_TABLE))

    # ---------------------------------------------------------------- A
    section("A. 解析用户原件宏 %s" % CAT_MACRO)
    ref = dbparse.parse_db_macro_file(CAT_MACRO, builtin=builtin)
    ps = dbparse.parse_stats(ref)
    text = open(CAT_MACRO, "rb").read().decode("utf-8-sig")
    ms = dbparse.macro_stats(text)
    print("  规模：specs=%d sprfile=%d families=%d unique_paths=%d"
          % (ps["specs"], ps["sprfile"], ps["families"], ps["unique_paths"]))
    check("≥2,920 条规格（契约 §l.5 验收阈值）", ps["specs"] >= 2920,
          "实际 %d" % ps["specs"])
    check("SPCOMPONENT 3,176… 实为 2,920 且路径唯一",
          ps["specs"] == 2920 and ps["unique_paths"] == 2920,
          "specs=%d unique=%d" % (ps["specs"], ps["unique_paths"]))
    census = {"catalogue": 3, "stsection": 12, "stcategory": 57, "text": 533,
              "dtset": 57, "data": 578, "ptsset": 57, "pline": 430, "gmsset": 57,
              "profile": 59, "sprfile": 2920, "spwld": 2, "specification": 12,
              "selec": 57, "spcomponent": 2920, "olds": 5890}
    bad = {k: (ms[k], v) for k, v in census.items() if ms[k] != v}
    check("元素计数与侦察报告 §7.1-3 逐项一致", not bad, str(bad))
    p2 = ms["pass2"]
    check("第二遍引用计数（PSTR/GSTR/DTRE/CATR 各 2,920、NARE 50）",
          p2.get("PSTR") == 2920 and p2.get("GSTR") == 2920 and p2.get("DTRE") == 2920
          and p2.get("CATR") == 2920 and p2.get("NARE") == 50, str(p2))

    by = {r.pdms_spec_path: r for r in ref.recs}
    r1 = by.get("/C_COIL-SPEC/C100X50X15X2.5")
    check("抽查 /C_COIL-SPEC/C100X50X15X2.5 的 PARA 21 项（recon §4.3 的 P1..P21）",
          r1 is not None and r1.extra["para_raw"][:8]
          == ["100", "50", "15", "2.5", "5.23", "4.11", "1.71", "81.34"],
          str(r1.extra["para_raw"][:8]) if r1 else "缺失")
    r2 = by.get("/H_INTERNATIONAL-SPEC/HN450X200")
    check("抽查 HN450X200 的 ShapeVal 回算 = 26,39,1,450,0,200,14,9,0,5,0,",
          r2 is not None and r2.shapeval == "26,39,1,450,0,200,14,9,0,5,0,",
          repr(r2.shapeval) if r2 else "缺失")
    r3 = by.get("/H_AMERICA-SPEC/WUS1000x642")
    check("word 型参数：/WUS1000x642 第 14 项 = 'S RSA'（recon §4.4-1）",
          r3 is not None and r3.extra["para_raw"][13] == "S RSA" and len(r3.params) == 25,
          "%r n=%d" % (r3.extra["para_raw"][13], len(r3.params)) if r3 else "缺失")
    r4 = by.get("/USER_RECT-SPEC/Rectangle_Profile")
    check("参数化族：/USER_RECT 的 DESP=（B,H）默认 500/500（原件 L2837-2853）",
          r4 is not None and [(q.name, q.desp_index, q.default) for q in r4.params]
          == [("B", 1, "500"), ("H", 2, "500")],
          str([(q.name, q.desp_index, q.default) for q in r4.params]) if r4 else "缺失")
    check("族码反查：/H_INTERNATIONAL → 39、/C_COIL → 72、/USER_CIRCLE → 3",
          (by["/H_INTERNATIONAL-SPEC/HN450X200"].family_code == 39
           and by["/C_COIL-SPEC/C100X50X15X2.5"].family_code == 72
           and by["/USER_CIRCLE-SPEC/Circle_Profile"].family_code == 3), "")
    pm = {r.pdms_spec_path: r for r in ref.recs}
    check("pkpm_name 逆查（有 secmap 时 2,579 条、无 secmap 时回落内置表）",
          ps["pkpm_name_known"] >= 2579, "pkpm_name_known=%d" % ps["pkpm_name_known"])
    # 原件异常：10 条 SPCOMPONENT 属主写成 /STSS_DOUBLE_THIN_L-SPEC（与 §l.3.4-1 不符）
    stss = [p for p in pm if p.startswith("/STSS_")]
    anomaly = [w for w in ps["warnings"] if "属主与 CATR 的族不一致" in w]
    check("原件异常被吃下：/STSS_DOUBLE_THIN_L-SPEC/… 10 条按 CATR 关联并留痕",
          len(stss) == 10 and len(anomaly) == 10,
          "paths=%d warn=%d" % (len(stss), len(anomaly)))
    print("  解析告警 %d 条（应全部可解释）：" % len(ps["warnings"]))
    for w in ps["warnings"]:
        print("     -", w[:150])

    # ---------------------------------------------------------------- B
    section("B. 与匹配文件交叉核对（失效 260 / 大小写差异 759）")
    sm = secmap_mod.SectionMap.load(MATCH_FILE)
    cc = dbparse.cross_check(ref, sm, match_path=MATCH_FILE, builtin=builtin)
    check("匹配文件数据行 2,836", cc["matching_file_rows"] == 2836,
          str(cc["matching_file_rows"]))
    check("失效 260（= 256 Double-L 三族 + 4 缺前导斜杠）", cc["broken_total"] == 260,
          "broken_total=%s（归一化后 %s；broken_rhs=%s other=%s missing_slash=%s）"
          % (cc["broken_total"], cc["broken_total_normalized"], cc["broken_rhs"],
             cc["broken_rhs_other"], cc["missing_leading_slash"]))
    check("右值失效 256 条（Double-L 三族，conflicts §2.1/§2.2）",
          cc["broken_rhs"] == 256 and cc["broken_rhs_other"] == 1,
          json.dumps(cc["broken_detail"], ensure_ascii=False))
    check("右值缺前导 / 4 条（第 2979–2982 行，其中 3 条补齐后命中宏）",
          cc["missing_leading_slash"] == 4
          and cc["missing_leading_slash_lines"] == [2979, 2980, 2981, 2982]
          and cc["missing_leading_slash_but_found"] == 3, "")
    check("宏有、匹配文件没有的 SPRFILE 344（原文口径；归一化后 341）",
          cc["macro_only"] == 344 and cc["macro_only_normalized"] == 341,
          "macro_only=%s / %s" % (cc["macro_only"], cc["macro_only_normalized"]))
    check("命中宏 2,579（= 2,836 − 256 − 1；侦察报告按未补斜杠记 2,576）",
          cc["matched"] == 2579, str(cc["matched"]))
    dll = dll_names_from_recon()
    check("DLL 名表重建 2,326 个（复刻 recon 21_final.py 的 explicit+carry）",
          len(dll) == 2326, str(len(dll)))
    cc2 = dbparse.cross_check(ref, sm, match_path=MATCH_FILE, builtin=builtin,
                              variant_names=dll)
    check("大小写/写法差异 759（DLL 全名表口径；内置表口径经 §0.4-8 的 dll_siblings 修复后同为 759）",
          cc2["case_variants"] == 759 and cc["case_variants"] == 759,
          "759口径=%s 内置表口径=%s" % (cc2["case_variants"], cc["case_variants"]))
    only_full = [x for x in cc2["case_variant_samples"]]
    print("  759 与前 10 例：", json.dumps(cc2["case_variant_samples"][:4], ensure_ascii=False))
    print("  失效明细：", json.dumps(cc["broken_detail"], ensure_ascii=False))
    print("  宏独有前 8：", json.dumps(cc["macro_only_samples"][:8], ensure_ascii=False))
    del only_full

    # ---------------------------------------------------------------- C
    section("C. 生成器 × 解析器闭环（内置表 %d 条 → 宏 → 写盘 → 读回）"
            % len(builtin.recs))
    opts = dbmacro.DbOptions(source_note="engine/section_table.csv",
                             suffix="_SELFTEST", report={})
    mac = dbmacro.generate_db_macro(builtin, opts)
    rep = opts.report
    p = dbmacro.write_db_macro(os.path.join(OUTDIR, "selftest_db.mac"), mac)
    print("  产物：%s（%d 字节，纯 ASCII=%s）" % (p, os.path.getsize(p), mac.isascii()))
    print("  生成统计：", json.dumps(rep["stats"], ensure_ascii=False))
    check("生成统计：3,176 SPRFILE / 3,176 SPCOMPONENT / 57 STCATEGORY / 12 STSECTION",
          rep["stats"]["sprfile"] == 3176 and rep["stats"]["spcomponent"] == 3176
          and rep["stats"]["stcategory"] == 57 and rep["stats"]["stsection"] == 12, "")
    back = dbparse.parse_db_macro_file(p, builtin=builtin)
    bs = dbparse.parse_stats(back)
    check("读回 3,176 条规格、路径唯一", bs["specs"] == 3176 and bs["unique_paths"] == 3176,
          "specs=%d unique=%d" % (bs["specs"], bs["unique_paths"]))
    cl = dbparse.closure_report(builtin, back, "gen")
    check("闭环：covered=3,176 / not_closable=0（规格集合逐个相等）",
          cl["covered"] == 3176 and not cl["not_closable"],
          "covered=%d not_closable=%d" % (cl["covered"], len(cl["not_closable"])))
    diff = cl["differences"]
    classes = cl["differences_by_class"]
    print("  差异 %d 条，分类：%s" % (len(diff), json.dumps(classes, ensure_ascii=False)))
    print("  （src-no-params = 内置表里『只出现在匹配文件』的 256 行本身没有参数定义；"
          "desp-param-added = 输入表没有 DESP 参数（/USER_RECT 与 /USER_CIRCLE 只写了占位名"
          "'Parameter 1'），生成侧按原件证据给出 B/H 与 D）")
    shown = 0
    for d in diff:
        if d.get("class") == "src-no-params":
            continue
        if shown < 6:
            print("     不可逆项：%s | %s" % (d["spec_path"], d["why"][:160]))
        shown += 1
    print("     非 src-no-params 的不可逆项共 %d 条（全部在 closure.json 里）" % shown)
    # 方向不对称：解析原件能恢复 14 个族的 PURP=DESP 参数，而内置表没有记 ⇒ 生成方向复现不了
    mix = [r for r in ref.recs
           if r.is_parametric and int((r.extra or {}).get("n_desp_params", 0)) > 0]
    dd = [r for r in ref.recs
          if r.pdms_spec_path == "/DOUBLE_THIN_C_COIL_TUBE-SPEC/DC[]80X40X15X2.0"]
    check("解析方向能恢复内置表没有的 DESP 参数（14 个族 %d 条；样例 DESP=d(mm)/10）" % len(mix),
          len(mix) >= 600 and dd and [(q.name, q.desp_index, q.default) for q in dd[0].params]
          == [("d(mm)", 1, "10")]
          and len(dd[0].extra["para_params"]) == 4,
          "mix=%d" % len(mix))
    check("差异只来自可解释的两类（表缺参数 256 + 模板族参数名 2）",
          classes.get("src-no-params") == 256 and classes.get("desp-param-added") == 2
          and set(classes) <= {"src-no-params", "desp-param-added"},
          json.dumps(classes, ensure_ascii=False))
    with open(os.path.join(OUTDIR, "closure.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"closure": cl, "stats": rep["stats"], "warnings": rep["warnings"],
                   "assumptions": rep["assumptions"], "safety": rep["safety"]},
                  fh, ensure_ascii=False, indent=1)
    print("  逐条差异已写：%s" % os.path.join(OUTDIR, "closure.json"))
    check("生成侧告警只有 3 条『同时落在』（256 行没有 pdms_specification 的族）",
          len(rep["warnings"]) == 3
          and all("同时落在" in w for w in rep["warnings"]),
          "%d 条：%s" % (len(rep["warnings"]), rep["warnings"][:1]))

    # jwd 侧（真实截面定义 → 表 → 宏 → 读回）
    model = jwd_read.read_jwd(SAMPLE_JWD)
    tj = slib.table_from_jwd(model)
    have = [r for r in tj.recs if r.pdms_spec_path]
    print("\n  jwd 侧：table_from_jwd → %d 条（带 pdms_spec_path 的 %d 条）"
          % (len(tj.recs), len(have)))
    oj = dbmacro.DbOptions(source_note="JLCJ2.jwd", suffix="_JWD", report={})
    macj = dbmacro.generate_db_macro(tj, oj)
    pj = dbmacro.write_db_macro(os.path.join(OUTDIR, "from_jwd.mac"), macj)
    tj2 = dbparse.parse_db_macro_file(pj, builtin=builtin, secmap=sm)
    clj = dbparse.closure_report(tj, tj2, "jwd")
    check("jwd 侧闭环：covered=%d/%d、差异 0" % (len(have), len(have)),
          clj["covered"] == len(have) and not clj["differences"],
          "covered=%d differences=%s" % (clj["covered"], clj["differences_by_class"]))

    # ---------------------------------------------------------------- D
    section("D. 纪律与安全")
    raw = open(p, "rb").read()
    check("产物纯 ASCII + CRLF（无单 \\n、无 BOM）",
          raw.isascii() and b"\n" not in raw.replace(b"\r\n", b"")
          and not raw.startswith(b"\xef\xbb\xbf"), "size=%d" % len(raw))
    hits = dbmacro.scan_forbidden_names(mac)
    check("禁用容器名扫描：0 命中（§l.1-2）", not hits, str(hits[:3]))
    check("safety 报告三键齐全（§m.3）",
          set(["forbidden_names_scanned", "clean_targets", "ascii_only"])
          <= set(rep["safety"]), str(sorted(rep["safety"])))
    check("4 个顶层容器都带 /PKPM2PDMS_ 前缀与唯一后缀",
          all(v.startswith("/PKPM2PDMS_") and v.endswith("_SELFTEST")
              for v in dbmacro.resolve_containers(dbmacro.DbOptions(suffix="_SELFTEST")).values()),
          "")
    inv = invariants(mac, "生成宏")
    del inv
    # 清场版
    oc = dbmacro.DbOptions(suffix="_CLN", clean_first=True, report={})
    macc = dbmacro.generate_db_macro(tj, oc)
    check("清场版含 DELETE 且目标只在本包容器（§l.3.5）",
          "DELETE CATE MEM" in macc and "DELETE SPWL MEM" in macc
          and all(t.startswith("/PKPM2PDMS_") for t in oc.report["safety"]["clean_targets"]),
          json.dumps(oc.report["safety"]["clean_targets"], ensure_ascii=False))
    check("清场版仍然只操作本包容器（禁用名 0 命中）",
          not dbmacro.scan_forbidden_names(macc), "")
    # INPUT 包裹（可选项）
    ow = dbmacro.DbOptions(suffix="_WRAP", input_wrap=True, report={})
    macw = dbmacro.generate_db_macro(tj, ow)
    check("input_wrap=True 时写出 INPUT BEGIN/END/FINISH 且能被解析器切段",
          "INPUT BEGIN" in macw and "INPUT FINISH" in macw
          and dbparse.parse_stats(dbparse.parse_db_macro(macw, builtin=builtin))["specs"]
          == len(have), "")
    # 负向控制
    check("负向控制：scan_forbidden_names 能抓出 `OLD CATALOGUE /PKPM_USER`",
          bool(dbmacro.scan_forbidden_names("OLD CATALOGUE /PKPM_USER")), "")
    try:
        dbmacro.resolve_containers(dbmacro.DbOptions(catalogue_user="/PKPM_USER"))
        raised = False
    except dbmacro.DbMacroError:
        raised = True
    check("负向控制：容器名不带 /PKPM2PDMS_ 前缀 ⇒ DbMacroError", raised, "")
    # 确定性
    o1 = dbmacro.DbOptions(suffix="_D", date_text="FIXED", report={})
    o2 = dbmacro.DbOptions(suffix="_D", date_text="FIXED", report={})
    check("确定性：同输入 + 同参数 ⇒ 逐字节相同",
          dbmacro.generate_db_macro(tj, o1) == dbmacro.generate_db_macro(tj, o2), "")
    # 编码纪律：脚本自身
    src = open(os.path.join(_ENG, "dbmacro.py"), "rb").read()
    src2 = open(os.path.join(_ENG, "dbparse.py"), "rb").read()
    check("engine/*.py 为 UTF-8 无 BOM",
          not src.startswith(b"\xef\xbb\xbf") and not src2.startswith(b"\xef\xbb\xbf"), "")

    # ---------------------------------------------------------------- E
    section("E. 逆向坑夹具（契约 §l.5 的 12 条规则 + recon §5.3 的坑）")
    # 一、全名/缩写并存、OLD 无类型、NEW 无 END、$ 续行 + 裸值行、括号三层、负数两种写法、
    #     LOCK 零值、KEY=value、INPUT 四段式（每段一个元素）
    seg = ("INPUT BEGIN\n"
           "%s\n"
           "INPUT END  CATALOGUE /FIX_C\n"
           "INPUT FINISH\n")
    body1 = ("NEW CATE /FIX_C\nPURP STL\n"
             "NEW STCATEGORY /FAM\nPURP STL\n"
             "NEW TEXT /FAM-PA1\nPURP PARA\nSTEX 'h(mm)'\nEND\n"
             "NEW DTSE\nNEW DATA\nDKEY APAR\nPPRO ( ATTRIB PARA[1 ] )\nDPRO ( 0 )\n"
             "PURP PARA\nNUMB 1\nDTIT 'h(mm)'\nEND\n"
             "NEW DATA\nDKEY BPAR\nPPRO ( ATTRIB PARA[2 ] )\nDPRO ( 0 )\n"
             "PURP PARA\nNUMB 2\nDTIT 'b(mm)'\nEND\nEND\n"
             "NEW PTSE\nNEW PLIN\nPKEY NA\nPX 0\nPY ( - ( ATTRIB PARA[1 ] / 2 ) )\n"
             "DX 0\nDY 0\nLOCK\nEND\nEND\n"
             "NEW SPRF /FIX_Profile\nGTYP BEAM\nPARA 100 $\n 200\nEND\n"
             "NEW STCATEGORY /FAM2\nPURP STL\n"
             "NEW SPRF /FIX2_Profile\nGTYP=BEAM\nPARA -179.44 (-180)\nEND\n")
    body2 = ("NEW SPWL /FIX_W\nDESC 'Structural Steel'\nPURP STL\n"
             "NEW SPEC /FIX_SPEC\nDESC 'x'\nLNTP unset\nQUES GTYP\nPURP STL\n"
             "NEW SELE\nDESC 'FIX'\nTANS 'BEAM'\n"
             "NEW SPCO /FAM-SPEC/FIX_Profile\nEND\nEND\nEND\n")
    body3 = ("OLD /FIX_Profile\nPSTR PTSSET 1 of STCATEGORY /FAM\n"
             "GSTR GMSSET 1 of STCATEGORY /FAM\nDTRE DTSET 1 of STCATEGORY /FAM\n")
    body4 = ("OLD SPCO /FAM-SPEC/FIX_Profile\nCATR SPRF /FIX_Profile\n")
    fixture = (seg % body1) + (seg % body2) + (seg % body3) + (seg % body4)
    fx = dbparse.parse_db_macro(fixture, builtin=None)
    paths = sorted(r.pdms_spec_path for r in fx.recs)
    check("INPUT 四段式 + 类型缩写（CATE/DTSE/PTSE/PLIN/SPRF/SPCO/SELE/SPEC/SPWL）",
          paths == ["/FAM-SPEC/FIX_Profile"], str(paths))
    r = fx.recs[0] if fx.recs else None
    check("OLD 省略类型名（`OLD /FIX_Profile`，recon §5.3-5）+ NEW 省略 END（§5.3-6）",
          r is not None and r.extra["sprfile"] == "/FIX_Profile"
          and r.extra["catalogue"] == "/FIX_C", str(r.extra) if r else "无规格")
    check("$ 续行 + 裸值行：PARA 100 $ / 200 合成 2 个值（§5.3-8）",
          r is not None and r.extra["para_raw"] == ["100", "200"],
          str(r.extra["para_raw"]) if r else "")
    check("LOCK 零值属性被解析（只有 key 没有值，§5.3-23）",
          any(e.get("LOCK") == "" for e in dbparse.parse_macro(fixture).elements
              if e.op == "NEW"), "")
    sprs = {e.name: e for e in dbparse.parse_macro(fixture).elements
            if e.op == "NEW" and e.type == "SPRFILE"}
    check("`KEY=value` 写法被接受：`GTYP=BEAM`（规则 11）",
          sprs.get("/FIX2_Profile") is not None
          and sprs["/FIX2_Profile"].get("GTYP") == "BEAM",
          str(sprs.get("/FIX2_Profile").attrs) if sprs.get("/FIX2_Profile") else "")
    check("负数的两种写法（`-179.44` 与 `(-180)`）原样保留（§5.3-10）",
          sprs.get("/FIX2_Profile") is not None
          and sprs["/FIX2_Profile"].get("PARA").split() == ["-179.44", "(-180)"],
          sprs.get("/FIX2_Profile").get("PARA") if sprs.get("/FIX2_Profile") else "")

    # 二、GBK 编码 + LF 行尾
    gbk_path = os.path.join(OUTDIR, "fixture_gbk.txt")
    with open(gbk_path, "wb") as fh:
        fh.write(("-- 中文注释（GBK）\n" + fixture.replace("\n", "\n")).encode("gbk"))
    text_gbk, enc_gbk = dbparse.read_macro_text(gbk_path)
    check("编码自动判定：GBK 文件被判为 gbk（§l.5-1）", enc_gbk == "gbk", enc_gbk)
    fx2 = dbparse.parse_db_macro_file(gbk_path, builtin=None)
    check("GBK + LF 的宏照样解析出同一批规格",
          sorted(x.pdms_spec_path for x in fx2.recs)
          == sorted(x.pdms_spec_path for x in fx.recs), "")

    # ---------------------------------------------------------------- 汇总
    section("汇总")
    print("  用时 %.1fs" % (time.time() - t0))
    print("  检查 %d 项：PASS %d，FAIL %d" % (len(CHECKS), len(CHECKS) - len(FAILED),
                                             len(FAILED)))
    for lab in FAILED:
        print("   FAIL:", lab)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
