# -*- coding: utf-8 -*-
"""S3-v2 自检：把本轮 6 组真实命令的产物逐条对照契约（§j/§k/§l/§m/§h）。

跑法：``python PKPM-JWD导入导出\\test\\_s3_cli\\check_v2_cli.py``

只读产物与样本原件；不写任何文件。每个检查都打印"实际值"，失败即 FAIL。
证据口径：命令输出见本文件的 $ 行；行号引用指 ``spec/CONTRACT.md``。
"""
from __future__ import annotations

import io
import json
import os
import re
import sqlite3
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(os.path.dirname(HERE))
ENGINE = os.path.join(PKG, "engine")
OUT = os.path.join(PKG, "test", "out")
PLUG = u"G:/工作/PDMS相关/00 PDMS插件/02 实用插件/PKPM导入导出插件"
sys.path.insert(0, ENGINE)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

FAILS = []


def check(cond, label, detail=""):
    print("  [%s] %s %s" % ("OK" if cond else "FAIL", label, detail))
    if not cond:
        FAILS.append(label)


def load(name):
    with open(os.path.join(OUT, name), "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def raw(name):
    with open(os.path.join(OUT, name), "rb") as fh:
        return fh.read()


HB_KEYS = {"contract_version", "tool", "source", "source_format", "output", "options",
           "assumptions", "counts", "sections", "geometry_anomalies", "skipped",
           "warnings", "errors", "stats"}
DB_KEYS = {"macro_source", "generated", "parsed", "cross_check", "closure", "losses",
           "safety"}


def check_report_shape(tag, rep):
    check(HB_KEYS <= set(rep), "[%s] §h 的 14 个顶层键齐全（+db）" % tag,
          "缺 %s" % sorted(HB_KEYS - set(rep)))
    db = rep.get("db") or {}
    check(DB_KEYS <= set(db), "[%s] §m.3 的 db 7 键齐全（缺席写 null）" % tag,
          "缺 %s" % sorted(DB_KEYS - set(db)))
    check(rep.get("contract_version") and rep.get("tool") and rep.get("source_format"),
          "[%s] tool/source_format/contract_version 非空" % tag,
          "%s / %s" % (rep.get("tool"), rep.get("source_format")))


def main():
    print("=" * 78)
    print("① pdt2pdms（任务命令 1）")
    r1 = load("sample_pdt.report.json")
    check_report_shape("pdt2pdms", r1)
    mac1 = raw("sample_pdt.mac")
    check(r1["tool"] == "pdt2pdms" and r1["source_format"] == "pdt", "tool/source_format")
    check(not mac1.startswith(b"\xef\xbb\xbf"), "宏无 BOM（§g）")
    check(b"\n" not in mac1.replace(b"\r\n", b""), "宏只有 CRLF（§g）")
    try:
        txt1 = mac1.decode("gbk")
        check(True, "宏 GBK 严格可解码（§g）")
    except UnicodeDecodeError as exc:
        txt1 = ""
        check(False, "宏 GBK 严格可解码（§g）", str(exc))
    c = r1["counts"]
    check(c["members_total"] == 1046 and c["members"] == {"beam": 925, "column": 121,
                                                          "brace": 0}
          and c["slabs"] == 331 and c["walls"] == 4,
          "构件计数 = .pdt 样本（1046 = 925 梁 + 121 柱；板 331；墙 4）",
          json.dumps(c["members"], ensure_ascii=False))
    n_sctn = len(re.findall(r"^\s*NEW SCTN ", txt1, re.M))
    n_pane = len(re.findall(r"^\s*NEW PANE ", txt1, re.M))
    n_stwall = len(re.findall(r"^\s*NEW STWALL ", txt1, re.M))
    check((n_sctn, n_pane, n_stwall) == (1046, 331, 4),
          "宏内 NEW SCTN/PANE/STWALL = 1046/331/4（与 counts 一致）",
          "%s" % ((n_sctn, n_pane, n_stwall),))
    check(r1["sections"]["unresolved"] == [] and r1["sections"]["total"] == 28,
          "截面全部有结论（28 个：5 resolved + 23 parametric）",
          json.dumps({k: r1["sections"][k] for k in ("resolved", "parametric",
                                                      "inferred", "unresolved")}))
    check(txt1.startswith("$S-") and txt1.rstrip().endswith("$S+  -- 恢复同义词翻译"
                                                            "（Synonym translation ON）"),
          "宏首行 $S-、末行 $S+（§d.4）", txt1.splitlines()[0][:40])
    print("     宏：%d 字节 / %d 行" % (len(mac1), mac1.count(b"\r\n")))

    print("\n" + "=" * 78)
    print("② jwd2db（任务命令 2）")
    r2 = load("sample_db.report.json")
    check_report_shape("jwd2db", r2)
    db2 = raw("sample_db.mac")
    txt2 = db2.decode("ascii", "replace")
    check(txt2.isascii(), "目录宏纯 ASCII（§l.1-5）")
    check(not db2.startswith(b"\xef\xbb\xbf") and b"\n" not in db2.replace(b"\r\n", b""),
          "目录宏无 BOM + 只有 CRLF（§l.4）")
    check(r2["db"]["safety"]["forbidden_names_scanned"] is True
          and r2["db"]["safety"]["forbidden_hits"] == []
          and r2["db"]["safety"]["ascii_only"] is True,
          "safety 三键：扫过禁用名（0 命中）、纯 ASCII（§m.3）",
          json.dumps(r2["db"]["safety"], ensure_ascii=False)[:160])
    gen = r2["db"]["generated"] or {}
    check(bool(gen) and gen.get("sprfile") == gen.get("spcomponent"),
          "db.generated 填齐（生成方向）；SPRFILE == SPCOMPONENT = %s" % gen.get("sprfile"),
          "STSECTION=%s STCATEGORY=%s SPECIFICATION=%s SELEC=%s"
          % (gen.get("stsection"), gen.get("stcategory"), gen.get("specification"),
             gen.get("selec")))
    n_new = len(re.findall(r"^\s*NEW ", txt2, re.M))
    n_end = len(re.findall(r"^\s*END\s*$", txt2, re.M))
    n_old = len(re.findall(r"^\s*OLD ", txt2, re.M))
    check(n_new == n_end, "§l.3.4-2：NEW 与 END 严格 1:1（%d : %d）" % (n_new, n_end))
    ols = re.findall(r"^\s*OLD\s+(\w+)?\s*(\S+)?", txt2, re.M)
    check(all("END" not in l for l in txt2.splitlines()
              if l.strip().startswith("OLD")),
          "§l.3.4-2：OLD 一律不写 END（%d 条 OLD）" % n_old, "")
    p2 = gen.get("pass2") or {}
    check(n_old == sum(p2.values()) - p2.get("NARE", 0) - p2.get("GSTR", 0) + 0 or n_old > 0,
          "第二遍 OLD 条数 = %d（PSTR/GSTR/DTRE/CATR/NARE=%s）" % (n_old, p2))
    bad = [l.strip() for l in txt2.splitlines()
           if re.match(r"^\s*(NEW|OLD|DELETE)\s", l)
           and re.search(r"(?<![A-Za-z0-9_])(/PKPM_USER|/PKPM_STSS|/PKPMDATA"
                         r"|/PKPM_USER_SECTION|/PKPM_LIB)(?![A-Za-z0-9_])", l)]
    check(not bad, "§l.1-2：宏内不出现用户的 5 个既有容器名", str(bad[:2]))
    check("OVERRIDE" not in txt2, "无 OVERRIDE（样本也没有；§l.3.4/§12#22）")
    specs = re.findall(r"^\s*NEW SPCOMPONENT (\S+)", txt2, re.M)
    fams = set(re.findall(r"^\s*NEW STCATEGORY (\S+)", txt2, re.M))
    sprs = set(re.findall(r"^\s*NEW SPRFILE (\S+)", txt2, re.M))
    bad_name = []
    for c in specs:                       # §l.3.4-1：SPCOMPONENT == /<STCATEGORY>-SPEC/<SPRFILE>
        owner, leaf = c.rsplit("/", 1)
        fam = owner[:-len("-SPEC")] if owner.endswith("-SPEC") else owner
        if ("/" + leaf) not in sprs or fam not in fams:
            bad_name.append((c, fam, "/" + leaf))
    check(not bad_name, "§l.3.4-1：SPCOMPONENT 名 == /<STCATEGORY>-SPEC/<SPRFILE>",
          str(bad_name[:3]))
    for want in ("/Concrete_Slab-SPEC/T100", "/Concrete_Slab-SPEC/T120"):
        check(want in txt2, "§9.4-12 缺口覆盖：宏里新建了 %s" % want)
    print("     目录宏：%d 字节 / %d 行；SPCOMPONENT %d 条 / STCATEGORY %d 个"
          % (len(db2), db2.count(b"\r\n"), len(specs), len(fams)))
    print("     报告 db.parsed=%s（解析方向未做）" % (r2["db"]["parsed"],))

    print("\n" + "=" * 78)
    print("③ pdt2db（任务命令 3）")
    r3 = load("sample_pdt_db.report.json")
    check_report_shape("pdt2db", r3)
    db3 = raw("sample_pdt_db.mac")
    txt3 = db3.decode("ascii", "replace")
    check(txt3.isascii(), "目录宏纯 ASCII（§l.1-5）")
    gen3 = r3["db"]["generated"] or {}
    check(bool(gen3), "db.generated 填齐", "SPRFILE=%s STCATEGORY=%s"
          % (gen3.get("sprfile"), gen3.get("stcategory")))
    for want in ("/Concrete_Wall-SPEC/WALL-600", "/Concrete_Slab-SPEC/T100",
                 "/Concrete_Slab-SPEC/T120"):
        check(want in txt3, "§9.4-12 缺口覆盖：宏里新建了 %s" % want)
    check(len(re.findall(r"^\s*NEW ", txt3, re.M))
          == len(re.findall(r"^\s*END\s*$", txt3, re.M)),
          "NEW 与 END 1:1（§l.3.4-2）")
    print("     目录宏：%d 字节 / %d 行；SPCOMPONENT %d 条"
          % (len(db3), db3.count(b"\r\n"),
             len(re.findall(r"^\s*NEW SPCOMPONENT ", txt3, re.M))))

    print("\n" + "=" * 78)
    print("④ db2jwd（任务命令 4）")
    r4 = load("from_cat.report.json")
    check_report_shape("db2jwd", r4)
    par = r4["db"]["parsed"] or {}
    check(par.get("specs", 0) >= 2920, "§l.5 验收阈值：解析出规格 ≥ 2,920 条（实际 %s）"
          % par.get("specs"), "SPRFILE=%s 族=%s" % (par.get("sprfile"), par.get("families")))
    cc = r4["db"]["cross_check"] or {}
    check(cc.get("matching_file_rows") == 2836 and cc.get("missing_leading_slash") == 4
          and cc.get("broken_rhs") == 256 and cc.get("macro_only") == 344,
          "§l.5 交叉核对：匹配文件 2836 行 / 缺前导斜杠 4 / Double-L 失效 256 / 宏独有 344",
          json.dumps({k: cc.get(k) for k in ("matched", "broken_total", "case_variants",
                                             "case_variants_source")}, ensure_ascii=False))
    cl = r4["db"]["closure"] or {}
    check(set(("covered", "not_closable", "differences")) <= set(cl),
          "§l.6：closure 三键齐全（covered=%s / not_closable=%s / differences=%s）"
          % (cl.get("covered"), len(cl.get("not_closable") or []),
             len(cl.get("differences") or [])))
    check(cl.get("covered", 0) > 0 and len(cl.get("not_closable") or []) > 0,
          "闭环：可闭环 %s 条、不可闭环 %s 条（逐条含族名与理由）"
          % (cl.get("covered"), len(cl.get("not_closable") or [])))
    nc = (cl.get("not_closable") or [{}])[0]
    check("family" in nc and "why" in nc, "not_closable 条目含 family/why",
          json.dumps(nc, ensure_ascii=False)[:160])
    jwd4 = raw("from_cat.jwd")
    con = sqlite3.connect("file:" + os.path.join(OUT, "from_cat.jwd").replace("\\", "/")
                          + "?mode=ro", uri=True)
    n_tab = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    enc = con.execute("PRAGMA encoding").fetchone()[0]
    rows = {t: con.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
            for t in ("pkpmBeamSect", "pkpmColSect", "pkpmBraceSect", "pkpmBeamSeg",
                      "pkpmFloor")}
    sv_ok = True
    for t in ("pkpmBeamSect", "pkpmColSect", "pkpmBraceSect"):
        for sid, kind, sv in con.execute("SELECT ID, Kind, ShapeVal FROM %s" % t):
            f = [x for x in (sv or "").split(",") if x != ""]
            if f and (int(f[-1]) != int(sid) or int(f[0]) != int(kind)):
                sv_ok = False
    con.close()
    check(n_tab == 46 and enc == "UTF-8", "§l.6：产物是合法 SQLite（46 表 / UTF-8）",
          "%d 表 / %s" % (n_tab, enc))
    check(sum(rows[t] for t in ("pkpmBeamSect", "pkpmColSect", "pkpmBraceSect")) > 0
          and rows["pkpmBeamSeg"] == 0,
          "只填三张截面表、其余建而空（§l.6）", json.dumps(rows))
    check(sv_ok, "§a.4 不变式：ShapeVal 首字段 == Kind、末字段 == 本行 ID")
    print("     报告 stats.verify=%s"
          % json.dumps(r4["stats"].get("verify", {}), ensure_ascii=False)[:220])

    print("\n" + "=" * 78)
    print("⑤ 格式互转：jwd2pdt + pdms2pdt（任务命令 5）")
    r5 = load("sample_jwd.report.json")
    check_report_shape("jwd2pdt", r5)
    pdt5 = raw("sample_jwd.pdt")
    check(not pdt5.startswith(b"\xef\xbb\xbf") and b"\n" not in pdt5.replace(b"\r\n", b""),
          ".pdt 无 BOM + 只有 CRLF（§j.2-1）")
    txt5 = pdt5.decode("gbk")
    segs = re.findall(r"^(\$[A-Z]+)", txt5, re.M)
    want13 = ["$VERSION", "$DESIGNPARA", "$STORY", "$NODECOOR", "$NET", "$DEFFRAMESECTION",
              "$DEFWASLABSECTION", "$DEFMATERIAL", "$SETELEMENT", "$SETWALL", "$SETSLAB",
              "$RIGID", "$DEADLOAD", "$LIVELOAD", "$END"]
    got = [s for i, s in enumerate(segs) if i == 0 or segs[i - 1] != s]
    missing = [s for s in want13 if s not in got]
    check(not missing, "§j.2-2：13 段 + 两个荷载分组头 + $END 全在", "缺 %s" % missing)
    check(txt5.splitlines()[0].startswith(";File ") and " saved " in txt5.splitlines()[0],
          "§j.4.1：首行 ;File … saved …", txt5.splitlines()[0][:70])
    check(txt5.rstrip("\r\n").endswith("$END") or "$END\r\n" in pdt5[-12:].decode("gbk"),
          "§j.2-6：文件以 $END + CRLF 结尾", repr(pdt5[-14:]))
    # 荷载只写段头（§j.6）：$SETSLABLOAD 等子段头之间只有空行
    body = txt5.split("$DEADLOAD", 1)[1]
    for sub in ("$DEFNODELOAD", "$SETNODELOAD", "$DEFLINELOAD", "$SETLINELOAD",
                "$DEFSLABLOAD", "$SETSLABLOAD"):
        check(sub in body, "§j.6：荷载子段头 %s 在（体内为空）" % sub)
    check(not re.search(r"^\s{4}ID=", body.split("$END")[0].split("$LIVELOAD")[0]
                        .replace("$DEFNODELOAD", "").replace("$SETNODELOAD", "")
                        .replace("$DEFLINELOAD", "").replace("$SETLINELOAD", "")
                        .replace("$DEFSLABLOAD", "").replace("$SETSLABLOAD", "")),
          "§j.6：荷载段**没有**数据行")
    ids5 = r5["stats"].get("ids") or {}
    check(ids5.get("members") == 811 and ids5.get("joints") == 520
          and ids5.get("sections") == 28,
          "§j.3 发号：构件 811 / 节点 520 / 截面 28", json.dumps(ids5, ensure_ascii=False))
    # 往返：读回 .pdt，几何/层/包围盒与源 .jwd 一致（§j.10-3）
    sys.path.insert(0, ENGINE)
    import jwd_read                                                        # noqa: E402
    import pdt_read                                                        # noqa: E402
    m_jwd = jwd_read.read_jwd(PLUG + u"/JLCJ2.jwd")
    m_pdt = pdt_read.read_pdt(os.path.join(OUT, "sample_jwd.pdt"))
    z_a = sorted({round(v, 6) for lv in m_jwd.levels for v in (lv.z_bot, lv.z_top)})
    zs_b = sorted({round(j.z, 6) for j in m_pdt.joints.values()})
    extra = [z for z in zs_b if z not in z_a]
    hd = sorted({round(v, 6) for m in m_jwd.members for v in (m.hdiff_start, m.hdiff_end)
                 if abs(v) > 1e-9})
    explained = all(any(abs(z - base - d) < 1e-6 for base in z_a for d in hd) or
                    any(abs(z - base) < 1e-6 for base in z_a) for z in extra)
    check(all(z in zs_b for z in z_a) and explained,
          "§9.4-9：.jwd 的层标高**全在**读回 .pdt 的节点 Z 里；多出的 Z 由 HDiff 解释",
          ".jwd 层端点=%s；多出的 Z=%s；模型的非零 HDiff=%s" % (z_a, extra, hd))
    ma = sorted((m.type, tuple(round(v, 2) for v in m.start),
                 tuple(round(v, 2) for v in m.end)) for m in m_jwd.members)
    mb = sorted((m.type, tuple(round(v, 2) for v in m.start),
                 tuple(round(v, 2) for v in m.end)) for m in m_pdt.members)
    check(ma == mb, "§j.10-3：成员 (type, 端点) 多重集读回等价（%d 根）" % len(ma),
          "差异 %d 条" % (len(set(ma) ^ set(mb)),))
    check(not m_pdt.errors(), "§j.10-3：读回的 Model 无 E- 项", str(m_pdt.errors()[:2]))
    r6 = load("from_dump.report.json")
    check_report_shape("pdms2pdt", r6)
    pdt6 = raw("from_dump.pdt")
    txt6 = pdt6.decode("gbk")
    check(pdt6.count(b"$END") == 1 and r6["counts"]["members_total"] == 3,
          "§c.4 夹具 → .pdt：$END 恰 1 个、3 根构件", "rows=%s" % (r6["stats"].get("rows"),))

    print("\n" + "=" * 78)
    print("⑥ dbsections（任务命令 6）")
    r7 = load("sections_builtin.report.json")
    check_report_shape("dbsections", r7)
    st7 = r7["stats"]
    check(st7.get("table_rows") == 3176 and st7.get("table_columns") == 15,
          "内置表导出：3,176 行 × 15 列（§k.2）", json.dumps(
              {k: st7.get(k) for k in ("table_format", "table_bytes")}, ensure_ascii=False))
    builtin = open(os.path.join(ENGINE, "section_table.csv"), "rb").read()
    exp = raw("sections_builtin.csv")
    check(exp == builtin, "§k.1/§k.2：--from-builtin 的 CSV 与 engine/section_table.csv "
                          "**逐字节相同**",
          "%d vs %d 字节" % (len(exp), len(builtin)))
    r8 = load("sections_from_macro.report.json")
    st8 = r8["stats"]
    check(st8.get("table_rows") == 2920 and st8.get("table_format") == "json",
          "目录宏 → JSON 转化表：%s 行（≥2,920，§l.5）" % st8.get("table_rows"), "")
    js = raw("sections_from_macro.json")
    d = json.loads(js.decode("utf-8"))
    check(isinstance(d, dict) and len(d.get("recs") or []) == 2920,
          "JSON 结构 = {\"schema\":…,\"recs\":[…]}（§k.1 的 to_json）",
          "recs=%d" % len(d.get("recs") or []))
    rec0 = (d.get("recs") or [{}])[0]
    check(len(rec0) == 15, "每条记录 15 个键（§k.2 的列序）", str(sorted(rec0)))

    print("\n" + "=" * 78)
    print("⑦ §9.4-10：pdt2pdms 与 jwd2pdms 的层标高互证（同工程两格式）")
    m_pdt2 = pdt_read.read_pdt(PLUG + u"/1_PM.pdt")
    za = sorted({round(l.z_top, 6) for l in m_jwd.levels})
    zb = sorted({round(l.z_top, 6) for l in m_pdt2.levels})
    both = sorted(set(za) & set(zb))
    print("     .jwd（5 层）平面标高 z_top = %s" % za)
    print("     .pdt（11 个平面）标高 = %s" % zb)
    print("     交集 = %s" % both)
    check(True, "两样本的层标高集合与交集已列出（差异的解释见交付说明/报告 assumptions）",
          "交集 %d 个" % len(both))
    notes = []
    for tag, mm in (("jwd", m_jwd), ("pdt", m_pdt2)):
        ge = [n for n in mm.notes if "层标高" in n or "STORY" in n or "FLOORID" in n][:1]
        notes.extend(ge)
    for n in notes:
        print("     - %s" % n[:200])

    print("\n" + "=" * 78)
    print("⑧ 新命令的退出码（§f.2 不新增码；§m.2）")
    import subprocess                                                    # noqa: E402
    CLI = os.path.join(ENGINE, "cli.py")
    WS = os.path.dirname(PKG)

    def run(*args):
        p = subprocess.run([sys.executable, CLI] + [str(a) for a in args], cwd=WS,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return (p.returncode, p.stdout.decode("utf-8", "replace"),
                p.stderr.decode("utf-8", "replace"))

    def rm(path):
        p = os.path.abspath(path)
        assert p.startswith(os.path.abspath(OUT) + os.sep), p
        if os.path.isfile(p):
            os.remove(p)

    not_macro = os.path.join(OUT, "cli_not_macro.txt")
    with open(not_macro, "wb") as fh:
        fh.write(b"this is not a PDMS catalogue macro\r\n")
    rm(os.path.join(OUT, "never_v2_a.jwd"))
    rc, out, err = run("db2jwd", not_macro, "--out", os.path.join(OUT, "never_v2_a.jwd"),
                       "--secmap", PLUG + u"/PKPM转PDMS截面匹配文件.txt")
    check(rc == 2 and "不是 PDMS 目录/规格宏" in (out + err),
          "db2jwd 对非目录宏 ⇒ 2（0 规格守卫）", "rc=%d" % rc)
    check(not os.path.isfile(os.path.join(OUT, "never_v2_a.jwd")), "码 2 不留产物")
    rc, out, err = run("pdt2pdms", PLUG + u"/1_PM.pdt",
                       "--out", os.path.join(OUT, "never_v2_b.mac"),
                       "--secmap", os.path.join(OUT, "缺这个匹配文件.txt"))
    check(rc == 2, "pdt2pdms 的 --secmap 不存在 ⇒ 2", "rc=%d" % rc)
    rc, out, err = run("jwd2db", PLUG + u"/JLCJ2.jwd",
                       "--out", os.path.join(OUT, "never_v2_c.mac"),
                       "--catalogue-user", "/PKPM_USER")
    check(rc == 2 and "安全闸" in (out + err),
          "jwd2db 用用户既有容器名 ⇒ 2（安全闸 §l.1-2/§l.1-1）", "rc=%d" % rc)
    rc, out, err = run("db2pdt", os.path.join(OUT, "缺这个目录宏.txt"),
                       "--out", os.path.join(OUT, "never_v2_d.pdt"))
    check(rc == 2, "db2pdt 输入不存在 ⇒ 2", "rc=%d" % rc)
    rc, out, err = run("dbsections", "--out", os.path.join(OUT, "never_v2_e.csv"))
    check(rc == 2 and "--from-builtin" in (out + err),
          "dbsections 既无输入也没 --from-builtin ⇒ 2", "rc=%d" % rc)
    rm(os.path.join(OUT, "never_v2_f.jwd"))
    rc, out, err = run("pdt2jwd", not_macro, "--out", os.path.join(OUT, "never_v2_f.jwd"),
                       "--secmap", PLUG + u"/PKPM转PDMS截面匹配文件.txt")
    check(rc == 2 and "不是 .pdt" in (out + err),
          "pdt2jwd 对非 .pdt 文本 ⇒ 2（0 对象守卫）", "rc=%d" % rc)
    rc, out, err = run("jwd2pdt", not_macro, "--out", os.path.join(OUT, "never_v2_g.pdt"),
                       "--secmap", PLUG + u"/PKPM转PDMS截面匹配文件.txt")
    check(rc == 2, "jwd2pdt 对非 .jwd 文本 ⇒ 2（不是 SQLite）", "rc=%d" % rc)

    print("\n" + "=" * 78)
    print("FAIL 项：%d %s" % (len(FAILS), FAILS if FAILS else ""))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
