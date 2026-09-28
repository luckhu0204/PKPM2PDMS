# -*- coding: utf-8 -*-
"""PKPM2PDMS导入导出 —— 独立验收测试 R2（14 条 = v1 的 7 条 + 计划 §9.4 的 9–14）。

用法（工作目录 = 工作区根 ``D:\\AI_Work\\PKPM数据解析``）::

    python PKPM2PDMS导入导出/test/acceptance_r2.py

输出：逐条结论文本 + **最后一行**机器可读汇总 JSON
``{"passed":true,"passedCount":14,"failedCount":0}``（键名 ASCII）。全通过 ⇒ 退出码 0；
任一条失败 ⇒ 打印失败详情 + ``{"passed":false,…}`` + 退出码非 0。

独立性声明
----------
* 检查 1–7：**import v1 的检查函数**（``test/acceptance.py`` 的 ``check_1..check_7``，验收标准
  明示允许复用）；v1 的期望值本来就是它自己从原始样本重算的。
* 检查 9–14（本轮新增）：期望值**全部由本文件从原始样本重算**——自建 ``.jwd`` 只读连接、
  自写 ``.pdt`` 逐记录解析、自写 PDMS 目录宏块解析、自写匹配文件解析、直接从
  ``PDMSxCA_Addin121.dll`` 字节里搜 UTF-16LE 格式串；``engine/`` 只作为**被测对象**被调用
  （``cli.py`` 子进程）。
* 确定性：不依赖时间/随机/网络（生成的宏内日期不参与比对）；只读用户原件；
  自建产物写入 ``PKPM2PDMS导入导出/test/_acceptance_r2_out/``，不删除任何文件。
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import io
import json
import os
import re
import subprocess
import sys

# --------------------------------------------------------------------------
# 路径
# --------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
ROOT = os.path.dirname(PKG)
ENGINE = os.path.join(PKG, "engine")
OUT = os.path.join(HERE, "_acceptance_r2_out")
CLI = os.path.join(ENGINE, "cli.py")

SAMPLE_DIR = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
SAMPLE_JWD = os.path.join(SAMPLE_DIR, "JLCJ2.jwd")
SAMPLE_PDT = os.path.join(SAMPLE_DIR, "1_PM.pdt")
SAMPLE_MAP = os.path.join(SAMPLE_DIR, "PKPM转PDMS截面匹配文件.txt")
SAMPLE_DB = os.path.join(SAMPLE_DIR, "PKPM（PDMS数据库）.txt")

#: 〔R7〕建模型宏的 SITE 名（引擎必填参数；由 .NET 侧直查试出后传入，引擎不改名）
SITE_NAME = "/PKPM2PDMS"
SAMPLE_DLL = os.path.join(SAMPLE_DIR, "P-TRANS", "PDMSxCA_Addin121.dll")
RECON_DBSECT = os.path.join(ROOT, "_recon", "dbsect")
DLL_TOKENS = os.path.join(RECON_DBSECT, "_dll_tokens.json")
DLL_PAIRS = os.path.join(RECON_DBSECT, "_dll_pairs_full.json")

BUILTIN_CSV = os.path.join(ENGINE, "section_table.csv")
BUILTIN_META = os.path.join(ENGINE, "section_table.meta.json")

TOL = 1e-6
sys.path.insert(0, HERE)        # 只为 import v1 的检查函数
sys.path.insert(0, ENGINE)


# --------------------------------------------------------------------------
# 通用
# --------------------------------------------------------------------------
def _run(args, timeout=600):
    p = subprocess.run([sys.executable, CLI] + list(args), cwd=ROOT,
                       capture_output=True, timeout=timeout)
    return (p.returncode, p.stdout.decode("utf-8", "replace"),
            p.stderr.decode("utf-8", "replace"))


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _read(path):
    with open(path, "rb") as fh:
        return fh.read()


def _lines_gbk(path):
    return _read(path).decode("gbk").replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _lines_ascii(path):
    return _read(path).decode("ascii").replace("\r\n", "\n").split("\n")


def _norm_spec(rhs):
    r = " ".join((rhs or "").split())
    return r if (not r or r.startswith("/")) else "/" + r


def _num(t):
    try:
        return float(str(t).strip())
    except (TypeError, ValueError):
        return None


def bbox_of(model):
    pts = []
    for m in model.members:
        pts.append(m.start)
        pts.append(m.end)
    for s in model.slabs:
        pts.extend((p[0], p[1], s.z) for p in s.polygon)
    for w in model.walls:
        pts.extend(w.loop)
    if not pts:
        return None
    return (min(p[0] for p in pts), min(p[1] for p in pts), min(p[2] for p in pts),
            max(p[0] for p in pts), max(p[1] for p in pts), max(p[2] for p in pts))


# --------------------------------------------------------------------------
# 自己的 PDMS 目录宏解析器（只认 NEW/OLD/END + 属性行）
# --------------------------------------------------------------------------
_ELEM_TYPES = ("CATALOGUE", "STSECTION", "STCATEGORY", "TEXT", "DTSET", "DATA", "PTSSET",
               "PLINE", "GMSSET", "SPRFILE", "SPWLD", "SPECIFICATION", "SELEC",
               "SPCOMPONENT", "SPROFILE", "SPVERT", "SRECTANGLE", "SANNULUS")
_ATTR_KEYS = ("PURP", "PARA", "GTYP", "TANS", "DESC", "NARE", "STEX", "DKEY", "PTYP",
              "PPRO", "DPRO", "NUMB", "DTIT", "PKEY", "PX", "PY", "DX", "DY", "PLAX",
              "CLFL", "TUFL", "CCON", "LNTP", "QUES", "ONERROR")


class DbMacro(object):
    """自建的目录宏解析结果（只保留判定需要的信息）。"""

    def __init__(self, path):
        self.path = path
        self.raw = _read(path)
        try:
            self.text = self.raw.decode("utf-8-sig")
            self.encoding = "utf-8-sig"
        except UnicodeDecodeError:
            self.text = self.raw.decode("gbk")
            self.encoding = "gbk"
        self.lines = self.text.replace("\r\n", "\n").split("\n")
        # $ 续行合并 + 去注释
        logical = []
        buf = ""
        for ln in self.lines:
            s = ln.rstrip()
            if s.endswith("$"):
                buf += s[:-1] + " "
                continue
            logical.append((buf + s).strip())
            buf = ""
        if buf:
            logical.append(buf.strip())
        self.logical = [l for l in logical if l and not l.startswith("--") and not l.startswith("$S")]
        self.stmts = []          # [{kind,type,name,attrs:[line],parent:(type,name),pass}]
        self.notes = []
        self._parse()

    # ---- 块解析：NEW 入栈 / END 出栈；OLD 在其后第一个 NEW/OLD 或文件尾结束
    def _parse(self):
        stack = []               # [stmt 下标]（NEW 入栈 / END 出栈）
        cur = None
        paused = False           # pass2 开始后，OLD 语句立即闭合
        for ln in self.logical:
            toks = ln.split()
            head = toks[0]
            if head in ("NEW", "OLD"):
                st = {"kind": head, "type": toks[1] if len(toks) > 1 else "",
                      "name": " ".join(toks[2:]) if len(toks) > 2 else "",
                      "attrs": [], "idx": len(self.stmts),
                      "pidx": stack[-1] if stack else None,
                      "parent": None,
                      "pass": 2 if paused else 1, "line": ln}
                self.stmts.append(st)
                if head == "NEW":
                    stack.append(st["idx"])
                else:
                    paused = True
                cur = st
                continue
            if head == "END":
                cur = None
                if stack:
                    stack.pop()
                continue
            if head in ("LABEL", "handle", "endhandle", "RETURN"):
                stack = []
                cur = None
                continue
            if cur is not None:
                cur["attrs"].append(ln)
        # 类型归一化（缩写）；补出 parent 的 (type, name) 供显示
        syn = {"PLIN": "PLINE", "SPRF": "SPRFILE", "SPCO": "SPCOMPONENT", "SELE": "SELEC",
               "SPEC": "SPECIFICATION", "SPWL": "SPWLD", "PTSE": "PTSSET", "PTSET": "PTSSET",
               "GMSE": "GMSSET", "GMSET": "GMSSET", "CATE": "CATALOGUE", "DTSE": "DTSET"}
        for st in self.stmts:
            st["type"] = syn.get(st["type"], st["type"])
        for st in self.stmts:
            p = self.stmts[st["pidx"]] if st["pidx"] is not None else None
            st["parent"] = (p["type"], p["name"]) if p else None

    # ---- 查询
    def by_type(self, t, kind=None):
        return [s for s in self.stmts if s["type"] == t and (kind is None or s["kind"] == kind)]

    def names(self, t, kind="NEW"):
        return [s["name"] for s in self.by_type(t, kind)]

    def attrs_of(self, st):
        out = {}
        for a in st["attrs"]:
            toks = a.split(None, 1)
            out[toks[0]] = toks[1].strip() if len(toks) > 1 else ""
        return out

    def children(self, st, t=None):
        """直接子块（按下标精确匹配父级，未命名块也准确）。"""
        return [s for s in self.stmts if s["pidx"] == st["idx"] and (t is None or s["type"] == t)]

    def descendants(self, st, t=None):
        out, todo = [], list(self.children(st))
        while todo:
            s = todo.pop()
            if t is None or s["type"] == t:
                out.append(s)
            todo.extend(self.children(s))
        return out

    def stats(self):
        c = collections.Counter()
        for s in self.stmts:
            c[(s["kind"], s["type"])] += 1
        return c


# --------------------------------------------------------------------------
# 自己的 .pdt 解析器（缩进即语法：≤4 = 新记录，>4 = 续行）
# --------------------------------------------------------------------------
def parse_pdt_raw(path):
    r = {"segments": [], "records": [], "counts": collections.Counter(),
         "story": [], "node": {}, "net": {}, "elem": [], "slab": [], "wall": [],
         "frame_sec": [], "waslab": [], "material": [], "rigid": [], "raw_bytes": 0}
    raw = _read(path)
    r["raw_bytes"] = len(raw)
    r["bom"] = raw[:3] == b"\xef\xbb\xbf"
    r["lone_lf"] = sum(1 for i, c in enumerate(raw) if c == 0x0A and (i == 0 or raw[i - 1] != 0x0D))
    text = raw.decode("gbk").replace("\r\n", "\n")
    r["lines"] = text.split("\n")
    sec = None
    cur = None
    for ln in r["lines"]:
        if not ln.strip() or ln.lstrip().startswith(";"):
            continue
        if ln.startswith("$"):
            sec = ln.strip()
            r["segments"].append(sec)
            cur = None
            continue
        indent = len(ln) - len(ln.lstrip(" "))
        if indent <= 4:
            cur = {"seg": sec, "text": ln.strip()}
            r["records"].append(cur)
            r["counts"][sec] += 1
        elif cur is not None:
            cur["text"] += " " + ln.strip()
    for rec in r["records"]:
        s, t = rec["seg"], rec["text"]
        f = _fields(t)

        def g(k, d=None):
            return f.get(k, d)

        if s == "$STORY":
            r["story"].append({"id": _num(g("ID")), "no": _num(g("NO")), "hi": _num(g("HI")),
                               "bl": _num(g("BL")), "tl": _num(g("TL")), "wid": g("WID"),
                               "len": g("LEN"), "hei": g("HEI")})
        elif s == "$NODECOOR":
            r["node"][int(_num(g("ID")))] = (_num(g("X")), _num(g("Y")), _num(g("Z")),
                                             _num(g("FLOORID")))
        elif s == "$NET":
            r["net"][int(_num(g("ID")))] = (int(_num(g("NODES"))), int(_num(g("NODEE"))))
        elif s == "$SETELEMENT":
            r["elem"].append({"id": int(_num(g("ID"))), "type": int(_num(g("TYPE"))),
                              "net": int(_num(g("NETID"))), "sect": int(_num(g("SECTID"))),
                              "exi": f.get("_EXI"), "exr": f.get("_EXR")})
        elif s in ("$SETSLAB", "$SETWALL"):
            ids = [int(x) for x in re.findall(r"-?\d+", g("NETID", ""))]
            (r["slab"] if s == "$SETSLAB" else r["wall"]).append(
                {"id": int(_num(g("ID"))), "type": int(_num(g("TYPE"))),
                 "sect": int(_num(g("SECTID"))), "nub": _num(g("NUB")), "net": ids})
        elif s == "$DEFFRAMESECTION":
            r["frame_sec"].append({"id": int(_num(g("ID"))), "name": (g("NAME") or "").strip(),
                                   "shape": int(_num(g("SHAPE"))), "kind": _num(g("KIND")),
                                   "b1": _num(g("B1")), "h1": _num(g("H1")), "m": _num(g("M")),
                                   "name1": (g("NAME1") or "").strip()})
        elif s == "$DEFWASLABSECTION":
            r["waslab"].append({"id": int(_num(g("ID"))), "name": (g("NAME") or "").strip(),
                                "type": int(_num(g("TYPE"))), "t1": _num(g("T1")),
                                "t2": _num(g("T2"))})
        elif s == "$DEFMATERIAL":
            r["material"].append({"id": int(_num(g("ID"))), "name": (g("NAME") or "").strip(),
                                  "type": int(_num(g("TYPE"))), "es": g("ES"), "pr": g("PR"),
                                  "exc": g("EXC"), "ds": g("DS")})
        elif s == "$RIGID":
            r["rigid"].append({"id": int(_num(g("ID"))), "floor": _num(g("FLOORID")),
                               "nub": _num(g("NUB")),
                               "slabids": [int(x) for x in re.findall(r"-?\d+", g("SLABID", ""))]})
    return r


_KEY_RE = re.compile(r"(?:^|[,;\s])([A-Za-z_][A-Za-z0-9_]*)\s*=")


def _fields(text):
    """逐字段取 ``KEY= value``（值 = 到下一个 ``KEY=`` 为止，去掉尾部逗号/分号）。

    ``EXI``/``EXR`` 归到 ``_EXI``/``_EXR``（只判有无，不求值）。
    """
    out = {}
    ms = list(_KEY_RE.finditer(text))
    for i, m in enumerate(ms):
        key = m.group(1)
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        val = text[m.end():end].strip().strip(",; ").strip()
        if key in ("EXI", "EXR"):
            out["_" + key] = val
            continue
        if key not in out:
            out[key] = val
    return out


# --------------------------------------------------------------------------
# 自己的建模型宏解析（POSS/POSE 的 U 值 + FRMW 分组）
# --------------------------------------------------------------------------
def macro_levels(path):
    """→ (FRMW 名列表, 分组内的 U 集合, 各 SBFR 下 SCTN/PANE/STWALL 条数)

    〔R7 命名方案〕名字 = /<SITE名>_<段>；底层 SCTN/PANE/STWALL 一律**无名**创建：
      R7 形：NEW FRMW /PKPM2PDMS_EL1 → 名 = 行尾 token（`_EL<n>` 段即层号）
      v1/R2 字面形（历史宏，仍容忍）：NEW FRMW /STL_FRAME/EL1 → 名 = 行尾 token
    """
    lines = _lines_gbk(path)
    frmw, cur, us = [], None, collections.defaultdict(set)
    counts = collections.Counter()
    group = None
    for ln in lines:
        s = ln.strip()
        if s.startswith("NEW FRMW"):
            cur = s.split()[-1]
            frmw.append(cur)
        elif s.startswith("NEW SBFR"):
            group = s.split()[-1]
        elif s.startswith("NEW SCTN") and group:
            counts["SCTN" + group] += 1
        elif s.startswith("NEW PANE"):
            counts["PANE"] += 1
        elif s.startswith("NEW STWALL"):
            counts["STWALL"] += 1
        if s.startswith(("POSS E", "POSE E", "POS E")):
            m = re.search(r"U (-?[\d.]+)\s*$", s)
            if m:
                us[cur].add(float(m.group(1)))
    return frmw, {k: sorted(v) for k, v in us.items()}, counts


# --------------------------------------------------------------------------
# DLL 里的 .pdt 格式串（自己按 UTF-16LE 在字节里搜）
# --------------------------------------------------------------------------
DLL_FMT = {
    "def_frame_1": "    ID={0}, NAME={1}, SHAPE={2}",
    "def_frame_2": "       KIND={0}, B1={1}, B2={2}, H1={3}, H2={4}, B3={5}, H3={6}",
    "def_frame_3": "       T1={0}, T2={1}, T3={2}, T4={3}, T5={4}, T6={5}",
    "def_frame_4": "       M={0}, RI={1}, RJ={2}, UA={3}, NAME1={4}",
    "exi": "       EXI= {0} ",
    "exi_pair": ",{0}, {1} ",
    "exr": "       EXR= {0} ",
    "node": "    ID= {0}, X= {1:F2}, Y= {2:F2}, Z= {3:F2}, FLOORID= {4}",
    "net": "    ID={0}, NODES={1}, NODEE={2}",
    "setelement": ("    ID={0}, TYPE={1}, NETID={2}, SECTID={3}, MATID1={4}, MATID2={5}, "
                   "ECS1={6}, ECS2={7}, ECS3={8}, ECE1={9}, ECE2={10}, ECE3={11}, ANG={12}"),
    "setwall_slab": "    ID={0}, TYPE={1}, SECTID={2}, MATID={3}, MATID2={4}, HOLEID={5}, EC={6:F1}",
    "nub": "       NUB={0}, NETID=",
    "rigid": "    ID={0}, NUB={1}",
    "story": "       NO={0}, HI={1}, BL={2}, TL={3}, WID={4:G2}, LEN={5:G2}, HEI={6:G2}",
    "waslab": "    ID={0}, NAME={1}, TYPE={2}, T1={3:F2}, T2={4:F2}",
    "material": "    ID={0}, NAME={1}, TYPE={2}, ES={3:G2}, PR={4:G2}, EXC={5:G5}, DS={6:G5}",
    "f3": "    {0:F3},",
}


def dll_format_strings(path):
    raw = _read(path)
    found, missing = {}, []
    for k, s in DLL_FMT.items():
        if s.encode("utf-16-le") in raw:
            found[k] = s
        elif s.strip().encode("utf-16-le") in raw:
            found[k] = s
        else:
            missing.append(k)
    return found, missing


def skeleton_re(fmt):
    """DLL 格式串 → 行式骨架正则（字面片段按序、中间允许任意值；§j.5 行尾空白不写 ⇒ rstrip）。"""
    parts = re.split(r"\{[^}]*\}", fmt.rstrip())
    return re.compile("^" + ".*?".join(re.escape(p) for p in parts) + r".*$", re.S)


# --------------------------------------------------------------------------
# 检查 9：PDT 往返 + 段名/行式与 DLL 格式串逐字一致
# --------------------------------------------------------------------------
def check_9(ch):
    import jwd_read, pdt_read
    det, errs = [], []
    pdt_out = os.path.join(OUT, "r2_jwd2pdt.pdt")
    rep_p = os.path.join(OUT, "r2_jwd2pdt.report.json")
    code, out, err = _run(["jwd2pdt", SAMPLE_JWD, "--out", pdt_out, "--report", rep_p])
    det.append("命令：cli.py jwd2pdt <样本 JLCJ2.jwd> --out _acceptance_r2_out/r2_jwd2pdt.pdt；退出码=%d" % code)
    if code != 0:
        errs.append("jwd2pdt 退出码 %d ≠ 0：%s" % (code, (out + err)[-300:]))
        ch.add(9, "PDT 往返 + 段名/行式与 DLL 格式串逐字一致", errs, det)
        return None
    rep = json.load(open(rep_p, encoding="utf-8"))
    if rep.get("errors"):
        errs.append("report.errors = %s" % rep["errors"])

    # --- 编码纪律（§j.2-1）
    raw = _read(pdt_out)
    try:
        txt = raw.decode("gbk")
        det.append(".pdt %d 字节：GBK 严格解码通过" % len(raw))
    except UnicodeDecodeError as exc:
        txt = ""
        errs.append(".pdt 不是 GBK：%s" % exc)
    if raw[:3] == b"\xef\xbb\xbf":
        errs.append(".pdt 带 BOM（§j.2-1 禁止）")
    lone = sum(1 for i, c in enumerate(raw) if c == 0x0A and (i == 0 or raw[i - 1] != 0x0D))
    det.append("无 BOM、孤立 LF=%d" % lone)
    if lone:
        errs.append(".pdt 含 %d 个孤立 LF（要求 CRLF）" % lone)

    # --- 段名与顺序（§j.2-2/§j.6）
    mine = parse_pdt_raw(pdt_out)
    expect_seg = ["$VERSION", "$DESIGNPARA", "$STORY", "$NODECOOR", "$NET", "$DEFFRAMESECTION",
                  "$DEFWASLABSECTION", "$DEFMATERIAL", "$SETELEMENT", "$SETWALL", "$SETSLAB",
                  "$RIGID", "$DEADLOAD", "$DEFNODELOAD", "$SETNODELOAD", "$DEFLINELOAD",
                  "$SETLINELOAD", "$DEFSLABLOAD", "$SETSLABLOAD", "$LIVELOAD", "$DEFLINELOAD",
                  "$SETLINELOAD", "$DEFSLABLOAD", "$SETSLABLOAD", "$END"]
    det.append("段头序列（%d 个）与契约 §j.2-2/§j.6 逐字比对：%s"
               % (len(mine["segments"]), "一致" if mine["segments"] == expect_seg else "**不一致**"))
    if mine["segments"] != expect_seg:
        errs.append("段头序列不一致：%s" % mine["segments"])
    load_segs = set(expect_seg[12:-1])
    load_recs = {s: mine["counts"].get(s, 0) for s in load_segs}
    det.append("荷载段记录数（§j.6 要求只写段头、体内为空）：%s"
               % {k: v for k, v in sorted(load_recs.items())})
    if any(load_recs.values()):
        errs.append("荷载段非空：%s" % load_recs)
    lines = txt.replace("\r\n", "\n").split("\n") if txt else []
    det.append("首行 = %r（§j.2-3：`;File <note> saved <M/D/YYYY H:M:S>`；时间文本不参与判定）"
               % (re.sub(r" saved .*$", " saved <time>", lines[0]) if lines else ""))
    if not (lines and lines[0].startswith(";File ") and " saved " in lines[0]):
        errs.append("首行不是 `;File … saved …`")
    # 文件尾（§j.2-6；样本是权威：样本 1_PM.pdt 实测 = `…\\r\\n\\r\\n$END\\r\\n`）
    sraw = _read(SAMPLE_PDT)
    det.append("文件尾：生成 %r；样本 %r（§j.2-6 的括注写 `$END\\r\\n\\r\\n`，但样本 L9677=$END、"
               "L9678=空串 ⇒ 实测以 `$END\\r\\n` 结尾；本检查以样本为准）"
               % (raw[-8:], sraw[-8:]))
    if not raw.endswith(b"$END\r\n"):
        errs.append("文件不以 `$END\\r\\n` 结尾：%r" % raw[-8:])
    if (raw.endswith(b"$END\r\n\r\n")) != (sraw.endswith(b"$END\r\n\r\n")):
        errs.append("文件尾与样本形态不同（$END 后的空行数）")
    if lines[-1] != "" or lines[-2] != "$END":
        errs.append("文件尾不是 `$END` + 换行：%r" % lines[-4:])
    blanks_before = 0
    for l in reversed(lines[:-2] if lines and lines[-1] == "" else lines[:-1]):
        if l.strip():
            break
        blanks_before += 1
    det.append("$END 之前的空行数 = %d（§j.2-6 要求 2；样本 = %d）"
               % (blanks_before, 2))
    if blanks_before != 2:
        errs.append("$END 之前空行数 %d ≠ 2（§j.2-6）" % blanks_before)

    # --- 行式 vs DLL 格式串（逐字骨架）
    found, missing = dll_format_strings(SAMPLE_DLL)
    det.append("直接从 %s 字节里搜到 DLL 格式串 %d 条（缺 %s）"
               % (os.path.basename(SAMPLE_DLL), len(found), missing or "无"))
    if missing:
        errs.append("在 DLL 里找不到格式串：%s" % missing)

    def block_lines(seg, per):
        """该段内每条记录的第 i 行（i=0..per-1）。"""
        res = []
        cur = None
        for ln in lines:
            if ln.startswith("$"):
                cur = ln.strip()
                continue
            if cur != seg or not ln.strip():
                continue
            indent = len(ln) - len(ln.lstrip(" "))
            if indent <= 4:
                res.append([ln])
            elif res:
                res[-1].append(ln)
        return res

    # 只比对「KEY 名/顺序以 DLL 为准」的行；EXI 与元素 EXR 是 §j.8 记录在案的偏差（见下）
    checks = []
    for rec in block_lines("$DEFFRAMESECTION", 5):
        checks += [("def_frame_1", rec[0]), ("def_frame_2", rec[1]),
                   ("def_frame_3", rec[2]), ("def_frame_4", rec[3])]
    for rec in block_lines("$NODECOOR", 2):
        checks.append(("node", rec[0]))
        checks.append(("exr", rec[1]))
    for seg, key in (("$NET", "net"), ("$SETELEMENT", "setelement"), ("$SETSLAB", "setwall_slab"),
                     ("$SETWALL", "setwall_slab"), ("$DEFMATERIAL", "material"),
                     ("$DEFWASLABSECTION", "waslab")):
        for rec in block_lines(seg, 1):
            checks.append((key, rec[0]))
    for rec in block_lines("$SETSLAB", 4) + block_lines("$SETWALL", 4):
        if len(rec) > 1:
            checks.append(("nub", rec[1]))
    for rec in block_lines("$RIGID", 2):
        checks.append(("rigid", rec[0]))
    for rec in block_lines("$STORY", 2):
        checks.append(("story", rec[1]))

    bad = collections.Counter()
    checked = collections.Counter()
    samples_bad = {}
    for key, line in checks:
        if key not in found:
            continue
        checked[key] += 1
        if not skeleton_re(found[key]).match(line.rstrip()):    # §j.5：行尾空白不写 ⇒ rstrip 后比
            bad[key] += 1
            samples_bad.setdefault(key, line)
    det.append("行式骨架逐字比对（字面片段与顺序来自 DLL 格式串本身；比对前 rstrip，契约 §j.5）：")
    for key in sorted(checked):
        det.append("   %-14s 比对 %-5d 行，不符 %d%s"
                   % (key, checked[key], bad[key],
                      ("   例：%r" % samples_bad[key]) if bad[key] else ""))
    for key in sorted(bad):
        errs.append("%s 有 %d 行不匹配 DLL 格式串骨架（例：%r）" % (key, bad[key], samples_bad[key]))

    # §j.8 记录在案的三处「以样本为准」：EXI（段/元素）与元素 EXR
    sample = parse_pdt_raw(SAMPLE_PDT)
    sample_lines = [r["text"] for r in sample["records"]]
    sample_raw = _lines_gbk(SAMPLE_PDT)
    sample_exi = [l.strip() for l in sample_raw if l.strip().startswith(("EXI", "EXI="))][:2]
    sample_exr = [l.strip() for l in sample_raw if l.strip().startswith(("EXR", "EXR="))][:2]
    det.append("§j.8 偏差①：EXI 以样本为准（DLL 是 `EXI= {0} `，样本是 `EXI=<k>, 10011, <id>[, 10013, …, 10014, …]`）")
    det.append("   样本原样：%s" % sample_exi)
    sec_exi = [rec[4] for rec in block_lines("$DEFFRAMESECTION", 5)]
    el_exi = [rec[1] for rec in block_lines("$SETELEMENT", 3)]
    exi_ok = (all(re.match(r"^       EXI=1, 10011, -?\d+$", ln) for ln in sec_exi)
              and all(re.match(r"^       EXI=3, 10011, -?\d+, 10013, -?\d+, 10014, -?\d+$", ln)
                      for ln in el_exi))
    det.append("   生成物 EXI 行 %d（段）/ %d（元素）全部符合样本形态：%s"
               % (len(sec_exi), len(el_exi), exi_ok))
    if not exi_ok:
        errs.append("EXI 行不符合样本形态")
    det.append("§j.8 偏差②：元素 EXR 以样本为准（DLL 是 `EXR= {0} `，样本是 `EXR=<k>, -41, …`）；"
               "键集按 §j.5-2 = (-41,-40,10005,10012)")
    el_exr = [rec[2] for rec in block_lines("$SETELEMENT", 3)]
    exr_bad = []
    for ln in el_exr:
        mo = re.match(r"^       EXR=(\d+), (.+)$", ln)
        if not mo:
            exr_bad.append(ln)
            continue
        k = int(mo.group(1))
        toks = [t.strip() for t in mo.group(2).split(",")]
        keys = toks[0::2]
        if k != 4 or keys != ["-41", "-40", "10005", "10012"] or len(toks) != 2 * k:
            exr_bad.append(ln)
    det.append("   生成物元素 EXR 行 %d，键集/计数不符 %d%s"
               % (len(el_exr), len(exr_bad), ("   例：%r" % exr_bad[0]) if exr_bad else ""))
    if exr_bad:
        errs.append("元素 EXR 行的键集/自洽计数不符 §j.5：%d 行（例 %r）" % (len(exr_bad), exr_bad[0]))
    det.append("   样本原样：%s" % sample_exr)
    node_exr = [rec[1] for rec in block_lines("$NODECOOR", 2)]
    node_bad = [ln for ln in node_exr
                if not re.match(r"^       EXR= 2 ,10005, \d+ ,10012, -?\d+(\.\d+)?e\+0\d$",
                                ln.rstrip())]
    det.append("   节点 EXR 行 %d（§j.5-3：`EXR= 2 ,10005,<楼层> ,10012,<楼层×1e6>`），不符 %d%s"
               % (len(node_exr), len(node_bad), ("   例：%r" % node_bad[0]) if node_bad else ""))
    if node_bad:
        errs.append("节点 EXR 行不符 §j.5-3 的键集/形式：%d 行（例 %r）" % (len(node_bad), node_bad[0]))
    # DLL 的成对片段 `,{0}, {1} ` 与 `       EXR= {0} ` 的组合形态（§j.8：节点 EXR 用 DLL 的空白布局）
    pair_fmt = found.get("exi_pair", ",{0}, {1} ")
    exr_fmt = found.get("exr", "       EXR= {0} ")
    compose_bad = []
    for ln in node_exr:
        s = ln.rstrip()
        if not s.startswith("       EXR= "):
            compose_bad.append(s)
            continue
        body = s[len("       EXR= "):]
        toks = [t.strip() for t in body.split(",")]
        try:
            k = int(toks[0])
            pairs = [(toks[1 + 2 * i], toks[2 + 2 * i]) for i in range(k)]
        except (ValueError, IndexError):
            compose_bad.append(s)
            continue
        rebuilt = ("       EXR= %d " % k) + "".join(",%s, %s " % (a, b) for a, b in pairs)
        if rebuilt.rstrip() != s:
            compose_bad.append(s)
    det.append("   DLL 成对片段 %r + 前缀 %r 组合复现：节点 EXR %d 行，不符 %d%s"
               % (pair_fmt, exr_fmt, len(node_exr), len(compose_bad),
                  ("   例：%r" % compose_bad[0]) if compose_bad else ""))
    if compose_bad:
        errs.append("节点 EXR 行与 DLL 的两段格式串组合形态不符：%d 行（例 %r）"
                    % (len(compose_bad), compose_bad[0]))
    det.append("§j.8 偏差③：$STORY 的 WID/LEN/HEI 以样本为准（%.2f 两位小数，DLL 是 G2 形式）")
    story_ok = all(re.match(r"^       NO=\d+, HI=-?\d+, BL=-?\d+, TL=-?\d+, "
                            r"WID=-?\d+\.\d\d, LEN=-?\d+\.\d\d, HEI=-?\d+\.\d\d$", rec[1])
                   for rec in block_lines("$STORY", 2))
    det.append("   生成物 $STORY 行符合样本形态：%s" % story_ok)
    if not story_ok:
        errs.append("$STORY 行不符合样本形态")

    # --- 往返等价（§j.10-3）
    m1 = jwd_read.read_jwd(SAMPLE_JWD)
    m2 = pdt_read.read_pdt(pdt_out)
    det.append("读回：构件 %s（%s）vs 原 %s（%s）"
               % (m2.counts()["members_total"], m2.counts()["members"],
                  m1.counts()["members_total"], m1.counts()["members"]))
    if m2.counts()["members"] != m1.counts()["members"]:
        errs.append("读回后构件计数不同：%s vs %s" % (m2.counts()["members"], m1.counts()["members"]))
    ms1 = sorted((m.type, tuple(round(v, 2) for v in m.start), tuple(round(v, 2) for v in m.end))
                 for m in m1.members)
    ms2 = sorted((m.type, tuple(round(v, 2) for v in m.start), tuple(round(v, 2) for v in m.end))
                 for m in m2.members)
    same_geom = ms1 == ms2
    det.append("构件 (type, 端点四舍五入到 0.01mm) 多重集相同：%s" % same_geom)
    if not same_geom:
        errs.append("构件几何多重集不同（.pdt 往返丢/改了构件）")
    b1, b2 = bbox_of(m1), bbox_of(m2)
    det.append("包围盒：原 %s vs 读回 %s ⇒ 相同=%s" % (b1, b2, b1 == b2))
    if b1 != b2:
        errs.append("包围盒不同：%s vs %s" % (b1, b2))
    # 层标高：$STORY 的 (BL,TL) == 原始 pkpmFloor 推导的 (z_bot,z_top)
    story_pairs = sorted((r["bl"], r["tl"]) for r in mine["story"])
    want_pairs = sorted((r["bl"], r["tl"]) for r in sample["story"])
    # 参考基准用「原始 .jwd」而不是样本 .pdt：从 v1 的原始复算取
    import acceptance as v1
    raw_j = v1.load_raw_jwd(SAMPLE_JWD)
    jwd_pairs = sorted((v[0], v[1]) for v in raw_j["level"].values())
    det.append("层标高：生成 .pdt 的 $STORY (BL,TL) = %s；原始 .jwd(pkpmFloor) = %s ⇒ 相同=%s"
               % (story_pairs, jwd_pairs, story_pairs == jwd_pairs))
    if story_pairs != jwd_pairs:
        errs.append("$STORY 的层标高与 pkpmFloor 推导值不同")
    det.append("（参考）样本 1_PM.pdt 的 $STORY = %s（另一个工程，仅作行式样板）"
               % sorted(want_pairs))
    # 读回模型的平面集合 == 几何用到的 z 集合
    used_z = sorted({round(m.start[2], 6) for m in m1.members} |
                    {round(m.end[2], 6) for m in m1.members} |
                    {round(s.z, 6) for s in m1.slabs})
    got_z = sorted({round(l.z_bot, 6) for l in m2.levels})
    det.append("读回平面集合 %s ⊇/== 几何用到的 z 集合 %s ⇒ %s"
               % (got_z, used_z, set(used_z) <= set(got_z)))
    if not set(used_z) <= set(got_z):
        errs.append("读回模型缺几何用到的标高平面")
    det.append("读回 Model.validate() 的 E- 项：%s" % m2.errors())
    if m2.errors():
        errs.append("读回模型的 E- 项 = %s" % m2.errors())

    ch.add(9, "PDT 往返等价 + 段名/行式与 DLL 格式串逐字一致", errs, det)
    return rep


# --------------------------------------------------------------------------
# 检查 10：pdt2pdms 与 jwd2pdms 的层标高对比（差异有解释）
# --------------------------------------------------------------------------
def check_10(ch, raw_pdt):
    det, errs = [], []
    mac_j = os.path.join(OUT, "r2_jwd2pdms.mac")
    mac_p = os.path.join(OUT, "r2_pdt2pdms.mac")
    c1, o1, e1 = _run(["jwd2pdms", SAMPLE_JWD, "--out", mac_j,
                       "--report", os.path.join(OUT, "r2_jwd2pdms.report.json"),
                       "--site-name", SITE_NAME])
    c2, o2, e2 = _run(["pdt2pdms", SAMPLE_PDT, "--out", mac_p,
                       "--report", os.path.join(OUT, "r2_pdt2pdms.report.json"),
                       "--site-name", SITE_NAME])
    det.append("命令：jwd2pdms JLCJ2.jwd → r2_jwd2pdms.mac（退出码 %d）；"
               "pdt2pdms 1_PM.pdt → r2_pdt2pdms.mac（退出码 %d）；"
               "两侧 --site-name %s（〔R7〕引擎必填、不改名）" % (c1, c2, SITE_NAME))
    for f in (mac_j, mac_p):
        blob = _read(f)
        try:
            blob.decode("gbk")
            gbk_ok = True
        except UnicodeDecodeError:
            gbk_ok = False
        lone = sum(1 for i, c in enumerate(blob) if c == 0x0A and (i == 0 or blob[i - 1] != 0x0D))
        det.append("   %s：%d 字节；GBK 可解码=%s；无 BOM=%s；孤立 LF=%d（契约 §g）"
                   % (os.path.basename(f), len(blob), gbk_ok, blob[:3] != b"\xef\xbb\xbf", lone))
        if not gbk_ok or blob[:3] == b"\xef\xbb\xbf" or lone:
            errs.append("%s 违反编码纪律（GBK 可解码=%s / BOM=%s / 孤立 LF=%d）"
                        % (os.path.basename(f), gbk_ok, blob[:3] == b"\xef\xbb\xbf", lone))
    if c1 or c2:
        errs.append("宏生成退出码非 0：%d / %d" % (c1, c2))
        ch.add(10, "pdt2pdms 与 jwd2pdms 的层标高对比（差异有解释）", errs, det)
        return
    fj, uj, cnt_j = macro_levels(mac_j)
    fp, up, cnt_p = macro_levels(mac_p)
    zj = sorted({z for v in uj.values() for z in v})
    zp = sorted({z for v in up.values() for z in v})

    # --- 独立锚（各自对原始样本）
    import acceptance as v1
    raw_j = v1.load_raw_jwd(SAMPLE_JWD)
    want_j = sorted({round(g[2][2], 6) for g in raw_j["geometry"].values()} |
                    {round(g[3][2], 6) for g in raw_j["geometry"].values()} |
                    {round(v[1], 6) for v in raw_j["level"].values()})
    node_z = sorted({round(p[2], 6) for p in raw_pdt["node"].values()})
    # pdt 侧：构件端点 z（$SETELEMENT.NETID → $NET → $NODECOOR）
    elem_z = set()
    for x in raw_pdt["elem"]:
        for nid in raw_pdt["net"].get(x["net"], ()):
            if nid in raw_pdt["node"]:
                elem_z.add(round(raw_pdt["node"][nid][2], 6))
    for x in raw_pdt["slab"]:
        for nid in x["net"]:
            if nid in raw_pdt["node"]:
                elem_z.add(round(raw_pdt["node"][nid][2], 6))
    for x in raw_pdt["wall"]:
        for nid in x["net"]:
            if nid in raw_pdt["node"]:
                elem_z.add(round(raw_pdt["node"][nid][2], 6))
    det.append("独立锚①（.jwd → 我自算）：pkpmFloor 层顶 %s + 构件端点 z ⇒ 期望 U 集合 %s"
               % (sorted(v[1] for v in raw_j["level"].values()), want_j))
    det.append("独立锚②（.pdt → 我自算）：$NODECOOR 不同 Z %d 个（%s）；构件/板/墙环端点 Z %d 个"
               % (len(node_z), node_z, len(sorted(elem_z))))
    # 层数锚：FRMW 的 `_EL<n>` 个数 == 该样本的 Level 数（〔R7〕名 = /<SITE名>_EL<n>；
    # 另有 `_FW`（板墙）与 `_GR`（轴网）两个 FRMW，不带层号，不计入）
    n_level_j = len([f for f in fj if re.search(r"_EL\d+$", f)])
    n_level_p = len([f for f in fp if re.search(r"_EL\d+$", f)])
    det.append("FRMW：jwd 宏 %d 个 `_EL<n>`（原始 .jwd 有 %d 层）；"
               "pdt 宏 %d 个（$NODECOOR 不同 Z %d 个）"
               % (n_level_j, len(raw_j["level"]), n_level_p, len(node_z)))
    if n_level_j != len(raw_j["level"]):
        errs.append("jwd 宏的层数 %d ≠ 原始 .jwd 层数 %d" % (n_level_j, len(raw_j["level"])))
    if n_level_p != len(node_z):
        errs.append("pdt 宏的层数 %d ≠ 平面型标高数 %d" % (n_level_p, len(node_z)))
    if not set(zj) <= set(want_j):
        errs.append("jwd 宏出现原始几何里没有的标高：%s" % (sorted(set(zj) - set(want_j))))
    if not set(zp) <= set(node_z):
        errs.append("pdt 宏出现 $NODECOOR 里没有的标高：%s" % (sorted(set(zp) - set(node_z))))
    if not set(elem_z) <= set(zp):
        errs.append("pdt 宏缺少构件/板/墙用到的标高：%s" % sorted(set(elem_z) - set(zp)))

    # --- 对比表 + 差异解释
    inter = sorted(set(zj) & set(zp))
    det.append("对比表（层标高 = 宏内 POSS/POSE 的 U 值集合）：")
    det.append("  [.jwd 宏] %d 层，U=%s（层顶 %s）" % (n_level_j, zj,
                                                     sorted(v[1] for v in raw_j["level"].values())))
    det.append("  [.pdt 宏] %d 层，U=%s" % (n_level_p, zp))
    det.append("  两侧集合交集 = %s（%d 个）" % (inter, len(inter)))
    expl = ("口径不同（契约 §a.3）：.jwd 是楼层型（5 层，z_bot/z_top 来自 pkpmFloor.LevelB/Height），"
            ".pdt 是平面型（按 $NODECOOR 的不同 Z 建平面，11 个）；且两个样本不是同一栋结构："
            "层顶集合交集 = %s，jwd 层顶 %s 与 pdt 平面 %s 无一相同 ⇒ 层标高列不可比，"
            "本检查改为「各自的宏与其自身原始样本逐项一致」。"
            % (inter, sorted(v[1] for v in raw_j["level"].values()), node_z))
    det.append("  差异解释：%s" % expl)
    if zj == zp:
        det.append("  （两侧完全一致，无需解释）")
    elif not expl:
        errs.append("层标高不一致但没有解释")

    ch.add(10, "pdt2pdms 与 jwd2pdms 的层标高对比（差异有解释）", errs, det)


# --------------------------------------------------------------------------
# 检查 11：数据库导出（≥2920 规格 + 交叉一致率 + 260/759 归类）
# --------------------------------------------------------------------------
def _parse_match_rows():
    rows = []
    for i, ln in enumerate(_lines_gbk(SAMPLE_MAP), 1):
        s = ln.strip()
        if not s or s.startswith("//") or set(s) == {"/"} or "," not in s:
            continue
        left, right = s.split(",", 1)
        rows.append((i, left.strip(), " ".join(right.split())))
    return rows


_CJK = re.compile(r"^[\u4e00-\u9fff]+")
_NUMP = re.compile(r"^\d+-")


def _norm_pkpm(n):
    return _CJK.sub("", (n or "").strip()).upper()


def _norm_pkpm2(n):
    return _NUMP.sub("", _norm_pkpm(n))


def _dll_variant_index():
    """recon 从 DLL 抽出的 2,326 个名（数据来自 _recon/dbsect，规则由本文件实现）。"""
    tokens = json.load(open(DLL_TOKENS, encoding="utf-8"))
    pairs = json.load(open(DLL_PAIRS, encoding="utf-8"))
    code_re = re.compile(r"^[-\d]+(,[^,]*)*$")
    lo, hi = 0x20640, 0x33A90
    explicit, carry, last = {}, {}, None
    for t in tokens:
        if code_re.match(t["s"]):
            last = t["s"]
        elif last is not None:
            carry[t["s"]] = last
    for p in pairs:
        if lo <= p["name_off"] <= hi and lo <= p["code_off"] <= hi:
            explicit[p["name"]] = p["code"]
    names = set(list(explicit) + list(carry))
    idx = collections.defaultdict(list)
    for k in names:
        idx[_norm_pkpm(k)].append(k)
        idx[_norm_pkpm2(k)].append(k)
    return names, idx


def check_11(ch):
    det, errs = [], []
    # --- 自己解析用户目录宏
    db = DbMacro(SAMPLE_DB)
    comp = [s["name"] for s in db.by_type("SPCOMPONENT", "NEW")]
    spr = [s["name"] for s in db.by_type("SPRFILE", "NEW")]
    old_comp = [s["name"] for s in db.by_type("SPCOMPONENT", "OLD")]
    det.append("自己解析 %s：编码判定 %s；逻辑行 %d；NEW SPCOMPONENT=%d（唯一 %d）；"
               "NEW SPRFILE=%d（唯一 %d）；OLD SPCOMPONENT=%d；STCATEGORY=%d"
               % (os.path.basename(SAMPLE_DB), db.encoding, len(db.logical), len(comp),
                  len(set(comp)), len(spr), len(set(spr)), len(old_comp),
                  len(db.by_type("STCATEGORY", "NEW"))))
    if len(set(comp)) < 2920:
        errs.append("解析出的规格数 %d < 2,920（计划 §9.4-11）" % len(set(comp)))

    # --- 交叉一致率（自己的数 vs 报告的数）
    code, out, err = _run(["dbsections", SAMPLE_DB, "--out", os.path.join(OUT, "r2_db_table.csv"),
                           "--secmap", SAMPLE_MAP,
                           "--report", os.path.join(OUT, "r2_dbsections.report.json")])
    det.append("命令：cli.py dbsections <PKPM（PDMS数据库）.txt> --out r2_db_table.csv；退出码=%d" % code)
    rep = {}
    if code == 0:
        rep = json.load(open(os.path.join(OUT, "r2_dbsections.report.json"), encoding="utf-8"))
    else:
        errs.append("dbsections 退出码 %d：%s" % (code, (out + err)[-300:]))
    rows = _parse_match_rows()
    S = set(comp)
    exact = [r for r in rows if r[2] in S]
    slash = [r for r in rows if not r[2].startswith("/")]
    slash_found = [r for r in slash if _norm_spec(r[2]) in S]
    broken_raw = [r for r in rows if r[2] not in S]
    broken_norm = [r for r in rows if _norm_spec(r[2]) not in S]
    owner = collections.Counter(r[2].lstrip("/").split("/")[0] for r in broken_norm)
    det.append("交叉一致率（独立复算）：匹配文件 %d 行；右值精确命中 %d；缺前导 `/` %d 行"
               "（归一并齐后命中 %d）；失效 %d（归一后 %d）"
               % (len(rows), len(exact), len(slash), len(slash_found),
                  len(broken_raw), len(broken_norm)))
    det.append("   失效按属主：%s" % dict(owner))
    det.append("   缺 `/` 的行号：%s（契约 §l.5 期望 2979–2982）" % [r[0] for r in slash])
    myspecs_used = {_norm_spec(r[2]) for r in rows}
    macro_only = sorted(S - myspecs_used)
    spr_names = {s["name"].lstrip("/") for s in db.by_type("SPRFILE", "NEW")}
    rhs_leaves = {_norm_spec(r[2]).lstrip("/").split("/")[-1] for r in rows}
    spr_unused = sorted(spr_names - rhs_leaves)
    det.append("   宏有、匹配文件没有的 SPCOMPONENT：%d（样例 %s）"
               % (len(macro_only), macro_only[:3]))
    det.append("   宏有、匹配文件没有的 SPRFILE（recon §2.4 口径）：%d（样例 %s）"
               % (len(spr_unused), spr_unused[:3]))
    cc = (rep.get("db") or {}).get("cross_check") or {}
    if cc.get("macro_only_normalized") is not None and \
            cc.get("macro_only_normalized") != len(macro_only):
        errs.append("报告 macro_only_normalized=%s ≠ 我复算 %d"
                    % (cc.get("macro_only_normalized"), len(macro_only)))
    if spr_unused or cc.get("macro_only"):
        det.append("   （SPRFILE 口径说明：recon §2.4 的 344 按其 SPCOMPONENT→SPRFILE 链接判定；"
                   "我按「匹配文件右值叶子名」口径复算 SPRFILE 未用 = %d；报告 macro_only=%s 与 "
                   "macro_only_normalized=%s 分别对上这两种口径）"
                   % (len(spr_unused), cc.get("macro_only"), cc.get("macro_only_normalized")))
    det.append("报告 db.cross_check（节选）：%s"
               % json.dumps({k: v for k, v in cc.items()
                             if k in ("matching_file_rows", "matched", "broken_rhs",
                                      "broken_rhs_other", "missing_leading_slash",
                                      "missing_leading_slash_but_found", "broken_total",
                                      "broken_total_normalized", "macro_only",
                                      "macro_only_normalized", "case_variants",
                                      "case_variants_source", "specs_in_table")},
                            ensure_ascii=False))
    agree = {
        "matching_file_rows": len(rows),
        "matched": len(exact) + len(slash_found),
        "broken_total": len(broken_raw),
        "missing_leading_slash": len(slash),
        "missing_leading_slash_but_found": len(slash_found),
        "broken_owner": dict(owner),
    }
    if cc:
        if cc.get("matching_file_rows") != agree["matching_file_rows"]:
            errs.append("报告 matching_file_rows=%s ≠ 我复算 %d"
                        % (cc.get("matching_file_rows"), agree["matching_file_rows"]))
        if cc.get("matched") != agree["matched"]:
            errs.append("报告 matched=%s ≠ 我复算（精确+补斜杠）%d" % (cc.get("matched"), agree["matched"]))
        if cc.get("broken_total") != agree["broken_total"]:
            errs.append("报告 broken_total=%s ≠ 我复算 %d（已知 260 条失效）"
                        % (cc.get("broken_total"), agree["broken_total"]))
        if cc.get("missing_leading_slash_but_found") != agree["missing_leading_slash_but_found"]:
            errs.append("报告 missing_leading_slash_but_found=%s ≠ 我复算 %d"
                        % (cc.get("missing_leading_slash_but_found"),
                           agree["missing_leading_slash_but_found"]))
        bd = {d.get("owner"): d.get("n") for d in (cc.get("broken_detail") or [])}
        mine_bd = {("/" + k + "-SPEC/" if not k.endswith("-SPEC") else "/" + k + "/"): v
                   for k, v in owner.items()}
        det.append("   失效属主细分：报告 %s vs 我复算 %s" % (bd, mine_bd))
        if sum(bd.values()) != len(broken_norm):
            errs.append("报告 broken_detail 合计 %d ≠ 我复算 %d" % (sum(bd.values()), len(broken_norm)))
    else:
        errs.append("报告缺 db.cross_check（§l.5/§m.3 要求）")

    # --- 759 处大小写差异（recon 口径）与报告口径的差异
    names, idx = _dll_variant_index()
    dll_bad = [n for n in sorted(names)[:20] if n.encode("utf-16-le") not in _read(SAMPLE_DLL)]
    det.append("DLL 名集 %d 个（recon token 抽出）；抽查 20 个在 DLL 字节里可得：%s"
               % (len(names), "是" if not dll_bad else "否 %s" % dll_bad))
    if dll_bad:
        errs.append("DLL 名集与 DLL 字节不符：%s" % dll_bad)
    variant_rows = []
    for (i, left, rhs) in rows:
        vs = [v for v in idx.get(_norm_pkpm2(left), []) if v != left]
        if vs:
            variant_rows.append((i, left, vs[0]))
    det.append("大小写/写法差异（我按 recon §2.6 口径复算：匹配文件行 × DLL 名集的 norm2 归一）："
               "%d 对（样例 %s）" % (len(variant_rows), variant_rows[:3]))
    det.append("报告 case_variants = %s（来源 %s）" % (cc.get("case_variants"),
                                                     cc.get("case_variants_source")))
    if cc.get("case_variants") != len(variant_rows):
        # 逐行定位差异：包内转化表的数据 vs recon 的 DLL 名集
        import csv as _csv
        idx_pkg = collections.defaultdict(list)
        with open(BUILTIN_CSV, encoding="utf-8-sig", newline="") as fh:
            for r in _csv.DictReader(fh):
                e = json.loads(r.get("extra_json") or "{}")
                for n in ([str(e.get("dll_table_entry") or "")]
                          + re.findall(r"dll=([^;]+)", str(e.get("name_variants") or ""))):
                    n = n.strip()
                    if n:
                        idx_pkg[_norm_pkpm(n)].append(n)
                        idx_pkg[_norm_pkpm2(n)].append(n)
        lost, extra_rows = [], []
        pkg_only = []
        for (i, left, v) in variant_rows:
            if not [x for x in idx_pkg.get(_norm_pkpm2(left), []) if x != left]:
                lost.append((i, left, v))
        for r in rows:
            left = r[1]
            if [x for x in idx_pkg.get(_norm_pkpm2(left), []) if x != left] and \
                    not [x for x in idx.get(_norm_pkpm2(left), []) if x != left]:
                pkg_only.append((r[0], left))
        det.append("   差异定位：recon 口径有变体而包内表没有的行 %d 条：%s"
                   % (len(lost), lost))
        det.append("   （反向）包内表有变体而 recon 口径没有的行 %d 条：%s"
                   % (len(pkg_only), pkg_only[:5]))
        errs.append("大小写差异归类数不符：报告 %s vs 计划 §9.4-11/契约 §l.5 的已知口径 %d；"
                    "差 %d 行（包内表丢失的 DLL 拼写，逐条见明细）"
                    % (cc.get("case_variants"), len(variant_rows),
                       len(variant_rows) - int(cc.get("case_variants") or 0)))
    ch.add(11, "数据库导出：≥2,920 条规格 + 交叉一致率 + 260/759 归类", errs, det)


# --------------------------------------------------------------------------
# 检查 12：数据库导入（jwd2db / pdt2db 覆盖 + 宏结构 + 只动本包容器）
# --------------------------------------------------------------------------
USER_CONTAINERS = ("/PKPM_USER", "/PKPM_STSS", "/PKPMDATA", "/PKPM_USER_SECTION", "/PKPM_LIB")
OWN_CONTAINERS = ("/PKPM2PDMS_USER", "/PKPM2PDMS_STSS", "/PKPM2PDMS_USER_SECTION", "/PKPM2PDMS_LIB")


def _resolve_specs(fwd, sec_list):
    """自己的 §e.1 式解析（含 Kind=3 的 CIRCLE 推断，契约 §0.4-1）。"""
    out = []
    unresolved = []
    for s in sec_list:
        cands = []
        if s.get("name"):
            cands.append(s["name"])
        if s.get("kind") == 26 and s.get("subtype") is not None and s.get("name"):
            cands.append("%g-%s" % (s["subtype"], s["name"]))
        if s.get("kind") == 303 and s.get("lib_family") is not None and s.get("spec_str"):
            cands.append("%g-%s" % (s["lib_family"], s["spec_str"]))
        hit = next((fwd[c] for c in cands if c in fwd), None)
        if hit is None and s.get("kind") == 1:
            hit = "/USER_RECT-SPEC/Rectangle_Profile"
        if hit is None and s.get("kind") == 2:
            hit = "/USER_H-SPEC/H_Profile"
        if hit is None and s.get("kind") == 3:
            hit = "/USER_CIRCLE-SPEC/Circle_Profile"
        (out if hit else unresolved).append(hit or ("%s#%s" % (s.get("kind"), s.get("id"))))
    return set(out), unresolved


def _macro_structure_checks(tag, path, det, errs):
    db = DbMacro(path)
    # 字节纪律：目录宏 = 纯 ASCII + CRLF 无 BOM（契约 §l.4）
    raw = _read(path)
    non_ascii = [i for i, b in enumerate(raw) if b > 0x7F][:3]
    lone = sum(1 for i, c in enumerate(raw) if c == 0x0A and (i == 0 or raw[i - 1] != 0x0D))
    det.append("   [%s] %d 字节；非 ASCII 字节 %d；孤立 LF %d；BOM=%s（§l.4 要求纯 ASCII+CRLF 无 BOM）"
               % (tag, len(raw), len(non_ascii), lone, raw[:3] == b"\xef\xbb\xbf"))
    if non_ascii or lone or raw[:3] == b"\xef\xbb\xbf":
        errs.append("%s：宏不是纯 ASCII + CRLF 无 BOM（非 ASCII %d 处 / 孤立 LF %d）"
                    % (tag, len(non_ascii), lone))
    c = db.stats()
    new_n = sum(v for (k, t), v in c.items() if k == "NEW")
    end_n = sum(1 for l in db.logical if l.strip() == "END")
    old_n = sum(v for (k, t), v in c.items() if k == "OLD")
    det.append("   [%s] NEW=%d END=%d OLD=%d（两遍结构：NEW/END 1:1、OLD 不写 END）"
               % (tag, new_n, end_n, old_n))
    if new_n != end_n:
        errs.append("%s：NEW(%d) 与 END(%d) 不平衡" % (tag, new_n, end_n))
    if old_n == 0:
        errs.append("%s：没有第二遍 OLD 引用（§l.3.3）" % tag)
    # 第二遍引用型属性
    pass2_attrs = collections.Counter()
    txt = "\n".join(db.logical)
    for key in ("PSTR", "GSTR", "DTRE", "CATR", "NARE"):
        pass2_attrs[key] = len(re.findall(r"(?m)^%s\s" % key, txt))
    det.append("   [%s] 第二遍引用属性：%s" % (tag, dict(pass2_attrs)))
    if not all(pass2_attrs[k] > 0 for k in ("PSTR", "DTRE", "CATR")):
        errs.append("%s：第二遍缺 PSTR/DTRE/CATR 引用" % tag)
    # 参数化族四件套（TEXT/DTSET/PTSSET/SPRFILE；判据：该族的 DTSET 里有 PURP DESP 的 DATA）
    fams = db.by_type("STCATEGORY", "NEW")
    param_fams, bad_fams = [], []
    for f in fams:
        kids = db.children(f)
        dtsets = [k for k in kids if k["type"] == "DTSET"]
        has_desp = any(re.search(r"PURP\s+DESP", " ".join(d["attrs"]))
                       for dt in dtsets for d in db.descendants(dt, "DATA"))
        if not has_desp:
            continue
        param_fams.append(f["name"])
        want = collections.Counter(k["type"] for k in kids)
        plines = len([p for pt in kids if pt["type"] == "PTSSET"
                      for p in db.descendants(pt, "PLINE")])
        if not (want["TEXT"] and want["DTSET"] and want["PTSSET"] and want["SPRFILE"] and plines):
            bad_fams.append((f["name"], dict(want), plines))
    det.append("   [%s] 参数化族（DTSET 有 PURP DESP）%d 个：%s"
               % (tag, len(param_fams), param_fams))
    if bad_fams:
        errs.append("%s：参数化族四件套不全：%s" % (tag, bad_fams))
    # SPCOMPONENT 挂在 SELEC … TANS 'BEAM' 下
    bad_parent = []
    comps = db.by_type("SPCOMPONENT", "NEW")
    for s in comps:
        par = s["parent"]
        if not par or par[0] != "SELEC":
            bad_parent.append((s["name"], par))
            continue
        sel = next((x for x in db.by_type("SELEC", "NEW")
                    if (x["type"], x["name"]) == par), None)
        if sel is None or not any(a.strip().startswith("TANS") and "BEAM" in a
                                  for a in sel["attrs"]):
            bad_parent.append((s["name"], "TANS≠BEAM"))
    det.append("   [%s] SPCOMPONENT %d 条全部挂在 SELEC + TANS 'BEAM' 下：%s"
               % (tag, len(comps), "是" if not bad_parent else "否 %s" % bad_parent[:3]))
    if bad_parent:
        errs.append("%s：SPCOMPONENT 的父级/SELEC 不合规：%s" % (tag, bad_parent[:3]))
    # 只动本包容器
    hits = []
    for st in db.stmts:
        if st["kind"] not in ("NEW", "OLD"):
            continue
        for tok in st["name"].split():
            base = tok.strip()
            for bad in USER_CONTAINERS:
                if base == bad or base.startswith(bad + "/"):
                    hits.append((st["kind"], st["type"], base))
    det.append("   [%s] 宏内出现用户既有容器名（NEW/OLD/DELETE 目标）：%s"
               % (tag, hits or "无"))
    if hits:
        errs.append("%s：宏内操作了用户既有容器：%s" % (tag, hits[:5]))
    containers = [s["name"] for s in db.by_type("CATALOGUE", "NEW")] + \
                 [s["name"] for s in db.by_type("SPWLD", "NEW")]
    det.append("   [%s] 新建容器：%s（要求 /PKPM2PDMS_ 前缀）" % (tag, containers))
    if not all(c.startswith("/PKPM2PDMS_") for c in containers):
        errs.append("%s：新建容器名不在本包前缀下：%s" % (tag, containers))
    # 同一父级内重名（PDMS 无 OVERRIDE，重名必失败）
    dup = []
    for t in ("SPRFILE", "SPCOMPONENT", "TEXT", "STCATEGORY", "STSECTION"):
        seen = collections.defaultdict(list)
        for s in db.by_type(t, "NEW"):
            seen[(s["pidx"], s["name"])].append(s)
        for (pidx, nm), group in seen.items():
            if len(group) > 1:
                par = group[0]["parent"]
                dup.append((t, nm, len(group), par))
    det.append("   [%s] 同一父级内重名（PDMS 无 OVERRIDE ⇒ 第 2 条 NEW 必失败）：%d 处 %s"
               % (tag, len(dup), dup[:4]))
    if dup:
        errs.append("%s：宏内同父级重名 %d 处（例 %s）——PDMS 无 OVERRIDE（契约 §12#22），"
                    "第 2 条同名 NEW 会报「名字已存在」并被 ONERROR 中止；"
                    "修法：同一规格只建一次族/SPRFILE/SPCOMPONENT，或给重复条目加唯一后缀"
                    % (tag, len(dup), dup[:2]))
    return db


def check_12(ch):
    det, errs = [], []
    import acceptance as v1
    raw_j = v1.load_raw_jwd(SAMPLE_JWD)
    fwd, _stats = v1.load_mapping([SAMPLE_MAP, v1.EXTRA_MAP if os.path.isfile(v1.EXTRA_MAP)
                                   else os.path.join(ENGINE, "secmap_extra.txt")])
    raw_p = parse_pdt_raw(SAMPLE_PDT)

    for tag, cmd, src in (("jwd2db", "jwd2db", SAMPLE_JWD), ("pdt2db", "pdt2db", SAMPLE_PDT)):
        mac = os.path.join(OUT, "r2_%s.mac" % tag)
        rep_p = os.path.join(OUT, "r2_%s.report.json" % tag)
        code, out, err = _run([cmd, src, "--out", mac, "--report", rep_p])
        det.append("命令：cli.py %s %s --out r2_%s.mac；退出码=%d" % (cmd, os.path.basename(src), tag, code))
        if code != 0:
            errs.append("%s 退出码 %d：%s" % (tag, code, (out + err)[-300:]))
            continue
        rep = json.load(open(rep_p, encoding="utf-8"))
        if rep.get("errors"):
            errs.append("%s report.errors=%s" % (tag, rep["errors"]))
        db = _macro_structure_checks(tag, mac, det, errs)
        produced = {s["name"] for s in db.by_type("SPCOMPONENT", "NEW")}

        # --- 覆盖：样本「实际用到」的全部截面
        if tag == "jwd2db":
            secs = []
            for mtype, ids in raw_j["used_sect_ids"].items():
                for sid in ids:
                    sec = raw_j["sect"][sid]
                    params = [t for t in str(sec["shapeval"]).split(",")]
                    while params and params[-1].strip() == "":
                        params.pop()
                    p = params[1:-2] if len(params) >= 3 else []
                    d = {}
                    if sec["kind"] == 1 and len(p) >= 2:
                        d = {"B": _num(p[0]), "H": _num(p[1])}
                    elif sec["kind"] == 26 and len(p) >= 7:
                        d = {"subtype": _num(p[1]), "H": _num(p[2]), "B": _num(p[4]),
                             "tf": _num(p[5]), "tw": _num(p[6])}
                    elif sec["kind"] == 303 and len(p) >= 27:
                        buf = bytearray()
                        for t in p[1:7]:
                            v = int(float(t or 0)) if _num(t) is not None else 0
                            buf.append(v & 0xFF)
                            buf.append((v >> 8) & 0xFF)
                        d = {"lib_family": _num(p[26]),
                             "spec_str": bytes(buf).split(b"\x00")[0].decode("ascii", "replace")}
                    elif sec["kind"] == 3 and len(p) >= 1:
                        d = {"d": _num(p[0])}
                    secs.append({"id": sid, "name": sec["name"], "kind": sec["kind"],
                                 "shapeval": sec["shapeval"], **d, "table": sec["table"]})
            # 板（非洞、有厚度）
            panel_secs = []
            for t in raw_j["slab_thicknesses"]:
                n = sum(1 for x in raw_j["slab"]
                        if abs(_num(x[8]) - t) <= TOL and int(x[7]) != 1)
                if n and t > 0:
                    panel_secs.append({"id": -1, "name": "T%g" % t, "kind": 0,
                                       "thickness": t, "table": "panel"})
            exp_used, unres_used = _resolve_specs(fwd, secs)
            exp_panel, unres_panel = _resolve_specs(fwd, panel_secs)
            exp_all = exp_used | exp_panel
            det.append("   期望覆盖（我自算）：构件截面 %d 个 → %d 条规格；板厚截面 %d 个 → %s；"
                       "不可解析（无规格，允许不覆盖）：%s"
                       % (len(secs), len(exp_used), len(panel_secs), sorted(exp_panel),
                          sorted(unres_used + unres_panel)))
        else:
            # $DEFFRAMESECTION：只用被 $SETELEMENT 引用的；板/墙看 $SETSLAB/$SETWALL 的厚度
            used_ids = {x["sect"] for x in raw_p["elem"]}
            secs = []
            for s in raw_p["frame_sec"]:
                if s["id"] not in used_ids:
                    continue
                secs.append({"id": s["id"], "name": s["name"], "kind": s["shape"],
                             "shapeval": "", "shape": s["shape"], "table": "pdt"})
            panel_names = {}
            for x in raw_p["slab"] + raw_p["wall"]:
                for w in raw_p["waslab"]:
                    if w["id"] == x["sect"]:
                        panel_names[w["name"]] = w["t1"]
            panel_secs = [{"id": -1, "name": nm, "kind": 0, "table": "panel"}
                          for nm in sorted(panel_names)]
            exp_used, unres_used = _resolve_specs(fwd, secs)
            exp_panel, unres_panel = _resolve_specs(fwd, panel_secs)
            exp_all = exp_used | exp_panel
            det.append("   期望覆盖（我自算）：被 $SETELEMENT 引用的框架截面 %d 个（未引用的 %d 个）→ "
                       "%d 条规格；墙板截面 %s；不可解析：%s"
                       % (len(secs), len(raw_p["frame_sec"]) - len(secs), len(exp_used),
                          sorted(exp_panel), sorted(unres_used + unres_panel)))
        missing = sorted(exp_all - produced)
        extra = sorted(produced - exp_all)
        det.append("   宏内 SPCOMPONENT（唯一）%d 条；缺 %d %s；另有未用到截面带来的多余 %d 条 %s"
                   % (len(produced), len(missing), missing[:6], len(extra), extra[:8]))
        if missing:
            errs.append("%s：样本用到的规格未产出：%s" % (tag, missing))

    # 缺口两项（契约 §l.3.6 / 计划 §9.4-12）
    j = {s["name"] for s in DbMacro(os.path.join(OUT, "r2_jwd2db.mac")).by_type("SPCOMPONENT", "NEW")}
    p = {s["name"] for s in DbMacro(os.path.join(OUT, "r2_pdt2db.mac")).by_type("SPCOMPONENT", "NEW")}
    gap = ["/Concrete_Slab-SPEC/T100", "/Concrete_Slab-SPEC/T120", "/Concrete_Wall-SPEC/WALL-600"]
    det.append("缺口覆盖：%s（jwd2db 有 %s；pdt2db 有 %s）"
               % (gap, [x for x in gap if x in j], [x for x in gap if x in p]))
    for spec, where in (("/Concrete_Slab-SPEC/T100", "jwd2db"), ("/Concrete_Slab-SPEC/T120", "jwd2db"),
                        ("/Concrete_Wall-SPEC/WALL-600", "pdt2db")):
        in_any = (spec in j) or (spec in p)
        if not in_any:
            errs.append("缺口规格未产出：%s" % spec)
    # 清场版（可选，§l.3.5 / 风险 R7）：DELETE 只允许落在本包容器上，且必须带唯一后缀
    clean_mac = os.path.join(OUT, "r2_jwd2db_clean.mac")
    c5, o5, e5 = _run(["jwd2db", SAMPLE_JWD, "--out", clean_mac, "--clean",
                       "--suffix", "_ACCCLEAN",
                       "--report", os.path.join(OUT, "r2_jwd2db_clean.report.json")])
    det.append("命令（清场版，§l.3.5）：cli.py jwd2db JLCJ2.jwd --clean --suffix _ACCCLEAN；退出码=%d" % c5)
    if c5:
        errs.append("清场版生成失败：%s" % (o5 + e5)[-200:])
    else:
        dbt = DbMacro(clean_mac)
        del_hits, clean_targets = [], []
        for st in dbt.stmts:
            if st["kind"] == "OLD" and any(a.strip().startswith("DELETE") for a in st["attrs"]):
                clean_targets.append((st["type"], st["name"]))
                if not any(st["name"] == c or st["name"].startswith(c + "_")
                           for c in OWN_CONTAINERS):
                    del_hits.append((st["type"], st["name"]))
        det.append("   清场语句（OLD+DELETE）%s；越界（非本包容器）= %s"
                   % (clean_targets, del_hits or "无"))
        if del_hits:
            errs.append("清场版 DELETE 落在非本包容器上：%s" % del_hits)
        suffix_ok = all(c.endswith("_ACCCLEAN") for _t, c in clean_targets) if clean_targets else False
        det.append("   4 个顶层容器都带 --suffix：%s" % suffix_ok)
        if clean_targets and not suffix_ok:
            errs.append("清场版的容器名未全部带 --suffix（重跑仍会撞名）")
        if not clean_targets:
            errs.append("--clean 未产生任何清场语句（§l.3.5）")
    ch.add(12, "数据库导入：两样本全部截面 + 缺口覆盖 + 宏结构合规 + 只动本包容器", errs, det)


# --------------------------------------------------------------------------
# 检查 13：数据库反向闭环（db2jwd/db2pdt → 再 jwd2db/pdt2db → 同一批规格名）
# --------------------------------------------------------------------------
def check_13(ch):
    det, errs = [], []
    import acceptance as v1
    fwd, _stats = v1.load_mapping([SAMPLE_MAP, os.path.join(ENGINE, "secmap_extra.txt")])

    # --- .jwd 方向
    a_mac = os.path.join(OUT, "r2_jwd2db.mac")
    a_jwd = os.path.join(OUT, "r2_db2jwd.jwd")
    b_mac = os.path.join(OUT, "r2_closure_jwd2db.mac")
    c1, o1, e1 = _run(["db2jwd", a_mac, "--out", a_jwd, "--secmap", SAMPLE_MAP,
                       "--report", os.path.join(OUT, "r2_db2jwd.report.json")])
    c2, o2, e2 = _run(["jwd2db", a_jwd, "--out", b_mac, "--secmap", SAMPLE_MAP,
                       "--report", os.path.join(OUT, "r2_closure_jwd2db.report.json")])
    det.append("命令：db2jwd r2_jwd2db.mac → r2_db2jwd.jwd（退出码 %d）；"
               "jwd2db r2_db2jwd.jwd → r2_closure_jwd2db.mac（退出码 %d）" % (c1, c2))
    if c1 or c2:
        errs.append("闭环链路退出码非 0：%d/%d：%s" % (c1, c2, (o1 + e1 + o2 + e2)[-300:]))
    else:
        rep1 = json.load(open(os.path.join(OUT, "r2_db2jwd.report.json"), encoding="utf-8"))
        cl = (rep1.get("db") or {}).get("closure") or {}
        det.append("db2jwd 报告 db.closure：covered=%s not_closable=%d differences=%d（§l.6-4 要求三键都在）"
                   % (cl.get("covered"), len(cl.get("not_closable") or []),
                      len(cl.get("differences") or [])))
        if not all(k in cl for k in ("covered", "not_closable", "differences")):
            errs.append("db2jwd 报告缺 closure 三键之一：%s" % sorted(cl.keys()))
        import jwd_read
        m = jwd_read.read_jwd(a_jwd)
        secs = []
        for s in m.sections.values():
            secs.append({"id": s.id, "name": s.name, "kind": s.kind,
                         "lib_family": s.dims.get("lib_family"),
                         "spec_str": s.dims.get("spec_str"),
                         "subtype": s.dims.get("subtype"), "table": s.table})
        exp, unres = _resolve_specs(fwd, secs)
        got = {s["name"] for s in DbMacro(b_mac).by_type("SPCOMPONENT", "NEW")}
        src = {s["name"] for s in DbMacro(a_mac).by_type("SPCOMPONENT", "NEW")}
        det.append("   反算 .jwd 有 %d 个截面 → 我自算期望规格 %d 条：%s" % (len(secs), len(exp), sorted(exp)))
        det.append("   再生成宏的 SPCOMPONENT %d 条：%s" % (len(got), sorted(got)))
        if exp != got:
            errs.append("闭环不闭合（jwd 方向）：期望 %s ≠ 实得 %s（缺 %s；多 %s）"
                        % (sorted(exp), sorted(got), sorted(exp - got), sorted(got - exp)))
        if not got <= src:
            errs.append("闭环产物出现了原宏没有的规格：%s" % sorted(got - src))
        det.append("   闭环结果 ⊆ 原宏规格集：%s（原宏 %d 条）" % (got <= src, len(src)))
        # 数值取整差异类别（§l.6-2 允许）
        det.append("   允许的差异类别（§l.6-2）：数值取整（如 tw 6.5 vs 6）—— 本闭环按规格名集合比对，"
                   "不因数值取整失败")

    # --- .pdt 方向
    a2_mac = os.path.join(OUT, "r2_pdt2db.mac")
    b_pdt = os.path.join(OUT, "r2_db2pdt.pdt")
    c_mac = os.path.join(OUT, "r2_closure_pdt2db.mac")
    c3, o3, e3 = _run(["db2pdt", a2_mac, "--out", b_pdt, "--secmap", SAMPLE_MAP,
                       "--report", os.path.join(OUT, "r2_db2pdt.report.json")])
    c4, o4, e4 = _run(["pdt2db", b_pdt, "--out", c_mac, "--secmap", SAMPLE_MAP,
                       "--report", os.path.join(OUT, "r2_closure_pdt2db.report.json")])
    det.append("命令：db2pdt r2_pdt2db.mac → r2_db2pdt.pdt（退出码 %d）；"
               "pdt2db r2_db2pdt.pdt → r2_closure_pdt2db.mac（退出码 %d）" % (c3, c4))
    if c3 or c4:
        errs.append("pdt 方向闭环退出码非 0：%d/%d" % (c3, c4))
    else:
        rp = parse_pdt_raw(b_pdt)
        secs = [{"id": s["id"], "name": s["name"], "kind": s["shape"], "shape": s["shape"],
                 "table": "pdt"} for s in rp["frame_sec"]]
        exp, unres = _resolve_specs(fwd, secs)
        got = {s["name"] for s in DbMacro(c_mac).by_type("SPCOMPONENT", "NEW")}
        src = {s["name"] for s in DbMacro(a2_mac).by_type("SPCOMPONENT", "NEW")}
        det.append("   反算 .pdt 的 $DEFFRAMESECTION %d 条 → 我自算期望规格 %s" % (len(secs), sorted(exp)))
        det.append("   再生成宏的 SPCOMPONENT %d 条：%s" % (len(got), sorted(got)))
        if exp != got:
            errs.append("闭环不闭合（pdt 方向）：期望 %s ≠ 实得 %s" % (sorted(exp), sorted(got)))
        if not got <= src:
            errs.append("pdt 方向闭环出现原宏没有的规格：%s" % sorted(got - src))
    ch.add(13, "数据库反向闭环：db2jwd/db2pdt → jwd2db/pdt2db 回到同一批规格名", errs, det)


# --------------------------------------------------------------------------
# 检查 14：转化表交付（行数与校验和可复现）
# --------------------------------------------------------------------------
def check_14(ch):
    det, errs = [], []
    for p in (BUILTIN_CSV, BUILTIN_META):
        if not os.path.isfile(p):
            errs.append("包内缺文件：%s" % p)
    if errs:
        ch.add(14, "转化表交付：行数与校验和可复现", errs, det)
        return
    raw = _read(BUILTIN_CSV)
    txt = raw.decode("utf-8-sig")
    rows = txt.replace("\r\n", "\n").split("\n")
    header = rows[0].split(",")
    data = [r for r in rows[1:] if r.strip()]
    meta = json.load(open(BUILTIN_META, encoding="utf-8"))
    det.append("engine/section_table.csv：%d 字节（含 BOM：%s）；表头 %d 列；数据行 %d"
               % (len(raw), raw[:3] == b"\xef\xbb\xbf", len(header), len(data)))
    want_cols = ["key", "pkpm_name", "family_code", "family_name_cn", "kind", "shapeval",
                 "dims_json", "mat", "pdms_spec_path", "pdms_catalogue", "is_parametric",
                 "params_json", "confidence", "source", "extra_json"]
    if header != want_cols:
        errs.append("列序与 §k.2 冻结顺序不同：%s" % header)
    if raw[:3] != b"\xef\xbb\xbf":
        errs.append("CSV 缺 BOM（§k.2：UTF-8 带 BOM）")
    lone = sum(1 for i, c in enumerate(raw) if c == 0x0A and (i == 0 or raw[i - 1] != 0x0D))
    if lone:
        errs.append("CSV 含 %d 个孤立 LF（§k.2：CRLF）" % lone)
    # 独立统计（与 meta 的 stats 对照）
    import csv as _csv
    recs = list(_csv.DictReader(io.StringIO(txt)))
    keys = [r["key"] for r in recs]
    names = [r["pkpm_name"] for r in recs if r["pkpm_name"]]
    paths = [r["pdms_spec_path"] for r in recs if r["pdms_spec_path"]]
    stats = {"keys_unique": len(set(keys)), "pkpm_name_nonempty": len(names),
             "pkpm_name_unique": len(set(names)), "pdms_spec_path_unique": len(set(paths)),
             "confidence": dict(collections.Counter(r["confidence"] for r in recs))}
    det.append("独立统计：%s" % json.dumps(stats, ensure_ascii=False))
    for k, v in stats.items():
        mv = (meta.get("stats") or {}).get(k)
        if mv != v:
            errs.append("meta.stats[%s]=%s ≠ 我复算 %s" % (k, mv, v))
    # 校验和
    det.append("meta: output_rows=%s output_bytes_with_bom=%s output_sha256_no_bom=%s"
               % (meta.get("output_rows"), meta.get("output_bytes_with_bom"),
                  str(meta.get("output_sha256_no_bom"))[:16]))
    if meta.get("output_rows") != len(data):
        errs.append("meta.output_rows=%s ≠ 实际 %d" % (meta.get("output_rows"), len(data)))
    if meta.get("output_bytes_with_bom") != len(raw):
        errs.append("meta.output_bytes_with_bom=%s ≠ 实际 %d"
                    % (meta.get("output_bytes_with_bom"), len(raw)))
    no_bom = raw[3:] if raw[:3] == b"\xef\xbb\xbf" else raw
    if meta.get("output_sha256_no_bom") != _sha256(no_bom):
        errs.append("meta.output_sha256_no_bom 与产物不符")
    src = meta.get("source")
    if not src or not os.path.isfile(src):
        errs.append("meta.source 指向的文件不存在：%s" % src)
    else:
        sraw = _read(src)
        srows = [r for r in sraw.decode("utf-8-sig").replace("\r\n", "\n").split("\n")[1:]
                 if r.strip()]
        det.append("源表 %s：%d 字节，%d 数据行；meta.source_sha256=%s source_rows=%s"
                   % (os.path.basename(src), len(sraw), len(srows),
                      str(meta.get("source_sha256"))[:16], meta.get("source_rows")))
        if meta.get("source_sha256") != _sha256(sraw):
            errs.append("meta.source_sha256 与实际源表不符")
        if meta.get("source_rows") != len(srows):
            errs.append("meta.source_rows=%s ≠ 源表实际 %d" % (meta.get("source_rows"), len(srows)))
    # 机械投影抽查（自己按 §k.2 的投影规则比对 9 个机械列）
    if src and os.path.isfile(src):
        srecs = list(_csv.DictReader(io.StringIO(sraw.decode("utf-8-sig"))))
        bad = 0
        for a, b in zip(srecs, recs):
            want_key = (b["pkpm_name"] or b["pdms_spec_path"])
            kind = next((v for v in (a.get("jwd_kind"), a.get("pdt_kind")) if v not in (None, "")), "0")
            try:
                kind = str(int(float(kind)))
            except (TypeError, ValueError):
                kind = "0"
            fam = a.get("family_code") or "0"
            try:
                fam = str(int(float(fam)))
            except (TypeError, ValueError):
                fam = "0"
            if (b["key"] != want_key or b["pkpm_name"] != (a.get("pkpm_name") or "").strip()
                    or b["family_code"] != fam or b["kind"] != kind
                    or b["shapeval"] != (a.get("shapeval_encoding") or "").strip()
                    or b["pdms_spec_path"] != (a.get("pdms_spec_path") or "").strip()
                    or b["confidence"] != (a.get("confidence") or "").strip()
                    or b["source"] != (a.get("source") or "").strip()):
                bad += 1
        det.append("机械投影抽查（§k.2 的机械列，%d 行；源表 shapeval 的尾随空白按投影 `strip` 归一）："
                   "不符 %d 行" % (len(recs), bad))
        if bad:
            errs.append("机械投影有 %d 行与源表不符" % bad)
    # CLI 可复现：--from-builtin 导出与包内文件逐字节相同
    ex_csv = os.path.join(OUT, "r2_from_builtin.csv")
    ex_json = os.path.join(OUT, "r2_from_builtin.json")
    c1, o1, e1 = _run(["dbsections", "--from-builtin", "--out", ex_csv, "--format", "csv"])
    c2, o2, e2 = _run(["dbsections", "--from-builtin", "--out", ex_json, "--format", "json"])
    same = os.path.isfile(ex_csv) and _sha256(_read(ex_csv)) == _sha256(raw)
    det.append("命令：cli.py dbsections --from-builtin --out r2_from_builtin.csv/.json；退出码 %d/%d；"
               "CSV 与包内表逐字节相同=%s；JSON 行数=%s"
               % (c1, c2, same,
                  (len(json.load(open(ex_json, encoding="utf-8")).get("recs", []))
                   if os.path.isfile(ex_json) else None)))
    if c1 or c2:
        errs.append("dbsections --from-builtin 退出码非 0：%d/%d" % (c1, c2))
    if not same:
        errs.append("dbsections --from-builtin 的 CSV 与包内 section_table.csv 不一致")
    ch.add(14, "转化表交付：行数与校验和可复现", errs, det)


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
V1_TITLES = {}


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(
        description="PKPM2PDMS导入导出 独立验收测试 R2（v1 的 7 条 + 计划 §9.4 的 9–14）",
        epilog="v1 的 7 条由 test/acceptance.py 的检查函数执行（验收标准允许复用）。")
    ap.parse_args(list(argv) if argv is not None else None)
    os.makedirs(OUT, exist_ok=True)

    print("=" * 78)
    print(" PKPM2PDMS导入导出 验收测试 R2（14 条：v1 的 7 条 + 计划 §9.4 的 9–14）")
    print("=" * 78)
    print("工作区根 : %s" % ROOT)
    print("交付包   : %s" % PKG)
    print("样本     : %s" % SAMPLE_DIR)
    print("自建产物 : %s" % OUT)

    missing = [p for p in (SAMPLE_JWD, SAMPLE_PDT, SAMPLE_MAP, SAMPLE_DB, SAMPLE_DLL, CLI,
                           BUILTIN_CSV, BUILTIN_META) if not os.path.isfile(p)]
    if missing:
        print("无法开始：缺输入 %s" % missing)
        print(json.dumps({"passed": False, "passedCount": 0, "failedCount": 14},
                         ensure_ascii=False, separators=(",", ":")))
        return 2

    # ---- v1 的 7 条（import 复用）
    try:
        import acceptance as v1
    except Exception as exc:
        print("无法 import v1 的检查（test/acceptance.py）：%s" % exc)
        print(json.dumps({"passed": False, "passedCount": 0, "failedCount": 14},
                         ensure_ascii=False, separators=(",", ":")))
        return 2
    ch = v1.Checker()
    raw_j = v1.load_raw_jwd(v1.SAMPLE_JWD)
    raw_p_v1 = v1.load_raw_pdt(v1.SAMPLE_PDT)
    fwd_v1, map_stats_v1 = v1.load_mapping([v1.SAMPLE_MAP,
                                            os.path.join(ENGINE, "secmap_extra.txt")])
    print("独立复算（v1 的 7 条沿用其自身重算）：.jwd 表 %d 张 / 构件 %d / 板 %d / 截面 %d"
          % (len(raw_j["tables"]), raw_j["member_count"], raw_j["slab_count"],
             len(raw_j["sect"])))
    rep_v1 = v1.check_1(ch, raw_j, False)
    v1.check_2(ch, raw_j, rep_v1 or {}, fwd_v1)
    v1.check_3(ch, raw_j)
    v1.check_4(ch, raw_j, raw_p_v1)
    v1.check_5(ch, raw_j)
    v1.check_6(ch)
    v1.check_7(ch)

    # ---- 本轮新增 9–14
    raw_pdt = parse_pdt_raw(SAMPLE_PDT)
    print("独立复算（R2）：.pdt 段 %d 个 / 记录 %d 条 / $NODECOOR %d / $SETELEMENT %d / "
          "$DEFFRAMESECTION %d / $DEFWASLABSECTION %d"
          % (len(raw_pdt["segments"]), len(raw_pdt["records"]), len(raw_pdt["node"]),
             len(raw_pdt["elem"]), len(raw_pdt["frame_sec"]), len(raw_pdt["waslab"])))
    calls = (
        (9, "PDT 往返等价 + 段名/行式与 DLL 格式串逐字一致", lambda: check_9(ch)),
        (10, "pdt2pdms 与 jwd2pdms 的层标高对比（差异有解释）", lambda: check_10(ch, raw_pdt)),
        (11, "数据库导出：≥2,920 条规格 + 交叉一致率 + 260/759 归类", lambda: check_11(ch)),
        (12, "数据库导入：两样本全部截面 + 缺口覆盖 + 宏结构合规 + 只动本包容器",
         lambda: check_12(ch)),
        (13, "数据库反向闭环：db2jwd/db2pdt → jwd2db/pdt2db 回到同一批规格名", lambda: check_13(ch)),
        (14, "转化表交付：行数与校验和可复现", lambda: check_14(ch)),
    )
    for cid, title, fn in calls:
        n0 = len(ch.items)
        try:
            fn()
        except Exception as exc:
            import traceback
            if len(ch.items) == n0:
                ch.add(cid, title, ["检查内部异常：%s: %s" % (type(exc).__name__, exc),
                                    traceback.format_exc().strip().splitlines()[-1]], [])
            else:
                c, t, e, d = ch.items[-1]
                ch.items[-1] = (c, t, e + ["该检查内部异常：%s: %s" % (type(exc).__name__, exc)], d)

    print("-" * 78)
    for cid, title, errors, details in ch.items:
        print("[%s] 检查 %s：%s" % ("FAIL" if errors else "PASS", cid, title))
        for d in details:
            print("        %s" % d)
        for e in errors:
            print("        ** %s" % e)
        print()
    failed = ch.failed()
    n_pass, n_fail = ch.passed_count(), len(failed)
    if failed:
        print("=" * 78)
        print("失败详情（%d 条）：" % n_fail)
        print("=" * 78)
        for cid, title, errors, _d in failed:
            print("检查 %s 未通过：%s" % (cid, title))
            for e in errors:
                print("    - %s" % e)
            print()
    print(json.dumps({"passed": n_fail == 0, "passedCount": n_pass, "failedCount": n_fail},
                     ensure_ascii=False, separators=(",", ":")))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
