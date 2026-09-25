# -*- coding: utf-8 -*-
"""PKPM-JWD导入导出 —— **独立验收测试**（7 条验收标准，逐条实现为检查项）。

用法（工作目录 = 工作区根 ``D:\\AI_Work\\PKPM数据解析``）::

    python PKPM-JWD导入导出/test/acceptance.py
    python PKPM-JWD导入导出/test/acceptance.py --allow-unresolved-sections   # 见下

输出：先打印逐条结论与关键数字；**最后一行**打印机器可读的汇总 JSON
``{"passed":true,"passedCount":7,"failedCount":0}``（键名 ASCII）。全部通过 ⇒ 退出码 0；
任一条失败 ⇒ 打印失败详情 + ``{"passed":false,…}`` + 退出码非 0。

独立性声明（本文件是本测试的**全部**代码，不含任何从 engine/ 复制的实现）
------------------------------------------------------------------------
* **期望值一律由本文件从原始样本重算**：直接读 ``.jwd``（自建只读 sqlite3 连接）、
  直接按行读 ``.pdt`` 文本、直接解析 ``PKPM转截面匹配文件``；
  ``engine/`` 只作为**被测对象**（SUT）被调用（``cli.py`` 子进程、``jwd_read/pdt_read`` 导入）。
* 重算用到的规则只来自 ``spec/CONTRACT.md``（§a.3 z 推导、§a.4 ShapeVal 解码、
  §a.5 几何公式、§e.1 候选键与四级优先级），并在本文件内**另行实现**一份。
* 测试确定性：不依赖时间/随机/网络；只读用户原件；自建产物写入
  ``PKPM-JWD导入导出/test/_acceptance_out/``（同目录同名文件覆盖写，不删除任何文件）。

一处**曾经**的判据与契约冲突（现已由契约变更消解，本测试**未**放宽任何判定）
--------------------------------------------------------------------------------
本测试最初实现「每个构件都有 SPREF 或 DESP」时，该句在本样本上按字面**不可能**成立：
``pkpmBraceSect`` 的 ID=32335 是 Kind=3（``ShapeVal='3,20,5,32335,'``），12 根支撑引用它；
用户原件 ``PKPM转PDMS截面匹配文件.txt`` 没有 ``3#20`` 条目，随包目录宏
``PKPM（PDMS数据库）.txt`` 里也没有任何 20 mm 的圆形截面（最小圆管是 ``/TUBE_TUBE-SPEC/D32X2.5``），
于是当时只能按契约 §d.4-2 省略 ``SPREF`` 并留 ``-- UNRESOLVED SECTION`` 标记，字面判定必失败。

**契约已按证据修订**（``spec/CONTRACT.md`` §0.4 变更记录 #1-#3，编排方授权）：
Kind=3 的单尺寸截面判为**圆形族** ``/USER_CIRCLE-SPEC/Circle_Profile`` + ``DESP <d>``，
状态是 ``status='inferred'``（**不是** ``resolved``——不确定性必须机器可见），
启用规则放在 ``engine/secmap_extra.txt`` 的 ``@FAMILY 3 = CIRCLE`` 指令行里（可一行停用）。
本测试据此：
* 检查 1 仍按**字面**判定「每个构件都有 SPREF 或 DESP」（811/811 必须满足），
  **并加强**：12 根推断构件的 ``SPREF``/``DESP`` 值必须与独立复算的截面尺寸一致、
  且宏内必须带 ``-- 推断截面`` 注释；
* 检查 2 的独立复算按契约 §e.3 把该截面期望为 ``inferred``（不是 unresolved，也不是 resolved），
  并要求报告里 ``evidence`` 非空。
``--allow-unresolved-sections`` 只是**诊断**开关，不是本测试的通过路径（默认判定才是）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys

# --------------------------------------------------------------------------
# 路径（本文件位置推导；样本路径来自验收标准）
# --------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)                      # PKPM-JWD导入导出/
ROOT = os.path.dirname(PKG)                      # 工作区根
ENGINE = os.path.join(PKG, "engine")
OUT = os.path.join(HERE, "_acceptance_out")      # 自建产物（可重复覆盖）

SAMPLE_DIR = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
SAMPLE_JWD = os.path.join(SAMPLE_DIR, "JLCJ2.jwd")
SAMPLE_PDT = os.path.join(SAMPLE_DIR, "1_PM.pdt")
SAMPLE_MAP = os.path.join(SAMPLE_DIR, "PKPM转PDMS截面匹配文件.txt")
EXTRA_MAP = os.path.join(ENGINE, "secmap_extra.txt")
CLI = os.path.join(ENGINE, "cli.py")

PDMS_PKG = os.path.join(PKG, "pdms")
PDMS_FILES = ("pkpmjwd.pmlfrm", "pkpmjwdexport.pmlfnc", "pkpmjwdrun.mac")
INSTALL_PS1 = os.path.join(PKG, "install", "install.ps1")
PDMS_ROOT = r"D:\AVEVA\Plant\PDMS12.1.SP4"
DESIGN_UIC = os.path.join(PDMS_ROOT, "design.uic")

#: 契约 §a.3/§a.5/§e.1 的常量（本测试独立实现时用到）
TOL = 1e-6
SECT_TABLE_TAG = {"pkpmBeamSect": "beam", "pkpmColSect": "col", "pkpmBraceSect": "brace"}

if ENGINE not in sys.path:                        # 只为了调用被测模块（不取期望值）
    sys.path.insert(0, ENGINE)


# --------------------------------------------------------------------------
# 通用小工具（本文件自用）
# --------------------------------------------------------------------------
def _dec(b):
    """契约 §b.2 的文本列解码规则（ASCII → UTF-8 → GBK）；本文件独立实现。"""
    if not isinstance(b, bytes):
        return b
    for enc in ("ascii", "utf-8"):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode("gbk", "replace")


def _num(v, default=0.0):
    if v is None:
        return default
    if isinstance(v, bool):
        return float(int(v))
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return default
    try:
        return float(s)
    except ValueError:
        return default


def _num_or_none(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def _f(v):
    """契约 §e.1 候选键里的 ``%g`` 数字串（'' 表示不是数字）。"""
    x = _num_or_none(v)
    return "" if x is None else ("%g" % x)


def _pairs_equal(a, b, tol=TOL):
    return len(a) == len(b) and all(abs(x - y) <= tol for x, y in zip(a, b))


def _sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def _read_text_gbk_strict(path):
    return _read_bytes(path).decode("gbk")          # 失败即抛（不允许 errors=replace）


def _text_lines(path):
    return _read_text_gbk_strict(path).replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _conn(path):
    """自建只读连接 + 自己的 text_factory（**不**复用 engine 的 dec 函数对象）。"""
    con = sqlite3.connect("file:" + str(path).replace("\\", "/") + "?mode=ro", uri=True)
    con.text_factory = _dec
    return con


def _table_counts(con):
    out = {}
    for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        out[name] = int(con.execute("SELECT COUNT(*) FROM %s" % name).fetchone()[0])
    return out


def _rows(con, sql):
    return [tuple(r) for r in con.execute(sql)]


def _run(argv, cwd=ROOT):
    p = subprocess.run(argv, cwd=cwd, capture_output=True)
    return (p.returncode,
            p.stdout.decode("utf-8", "replace"),
            p.stderr.decode("utf-8", "replace"))


# --------------------------------------------------------------------------
# 独立复算：原始 .jwd（不经过 engine）
# --------------------------------------------------------------------------
def load_raw_jwd(path):
    """从 ``.jwd`` 直接读出本次验收需要的全部原始事实（自己的 SQL/解码/公式）。"""
    con = _conn(path)
    try:
        r = {"tables": _table_counts(con)}
        # 层：pkpmFloor.LevelB/Height（契约 §a.3：禁止用 pkpmStdFlr.Height）
        r["floor_rows"] = _rows(con, "SELECT ID, No_, StdFlrID, LevelB, Height FROM pkpmFloor")
        r["level"] = {int(x[2]): (_num(x[3]), _num(x[3]) + _num(x[4]), _num(x[4]))
                      for x in r["floor_rows"]}
        r["stdflr"] = _rows(con, "SELECT ID, No_, Height FROM pkpmStdFlr")
        # 节点 / 网格线
        r["joint"] = {int(x[0]): (_num(x[1]), _num(x[2]), _num(x[3]), int(x[4]))
                      for x in _rows(con, "SELECT ID, X, Y, HDiff, StdFlrID FROM pkpmJoint")}
        r["grid"] = {int(x[0]): (int(x[1]), int(x[2]))
                     for x in _rows(con, "SELECT ID, Jt1ID, Jt2ID FROM pkpmGrid")}
        # 截面（ID -> kind/mat/name/shapeval）
        r["sect"] = {}
        for tbl in ("pkpmBeamSect", "pkpmColSect", "pkpmBraceSect"):
            for sid, no, name, mat, kind, sv in _rows(
                    con, "SELECT ID, No_, Name, Mat, Kind, ShapeVal FROM %s" % tbl):
                r["sect"][int(sid)] = {"id": int(sid), "table": SECT_TABLE_TAG[tbl],
                                       "no": int(no), "name": "" if name is None else str(name),
                                       "mat": int(mat), "kind": int(kind),
                                       "shapeval": "" if sv is None else str(sv), "tbl": tbl}
        # 段表（含几何公式所需的列）
        r["col"] = _rows(con, "SELECT ID, No_, StdFlrID, SectID, JtID, EccX, EccY, Rotation,"
                              " HDiffB FROM pkpmColSeg")
        r["beam"] = _rows(con, "SELECT ID, No_, StdFlrID, SectID, GridID, Ecc, HDiff1, HDiff2,"
                               " Rotation, JYDef FROM pkpmBeamSeg")
        r["brace"] = _rows(con, "SELECT ID, No_, StdFlrID, SectID, Jt1ID, Jt2ID, EccX1, EccY1,"
                                " HDiff1, EccX2, EccY2, HDiff2, Rotation FROM pkpmBraceSeg")
        # 板
        r["slab"] = _rows(con, "SELECT ID, No_, StdFlrID, GridsID, VertexX, VertexY, VertexZ,"
                               " RoomIsHole, Thickness, dead, live FROM pkpmSlab ORDER BY ID")
        # 荷载（分流：ElementKind 12→beam-line、-1→joint-point）
        r["loadsect"] = _rows(con, "SELECT ID, No, Loadname, ElementKind, ShapeVal"
                                   " FROM pkpmLoadSect ORDER BY ID")
        r["loadseg"] = _rows(con, "SELECT ID, No, SectID, Type, ElementID, strParas1, nPtCnt,"
                                  " strParasX, strParasY, strParasZ, StdFlrID"
                                  " FROM pkpmLoadSeg ORDER BY ID")
        # 构件计数（期望值的唯一来源）
        r["seg_counts"] = {t: len(r[key]) for t, key in
                           (("beam", "beam"), ("column", "col"), ("brace", "brace"))}
        r["member_count"] = sum(r["seg_counts"].values())
        r["slab_count"] = len(r["slab"])
        r["hole_count"] = sum(1 for x in r["slab"] if int(x[7]) == 1)
        # 原始段表里用到的截面（期望「被用到的截面」集合）
        r["used_sect_ids"] = {t: sorted({int(x[3]) for x in r[key]})
                              for t, key in (("beam", "beam"), ("column", "col"),
                                             ("brace", "brace"))}
        # 板厚（引擎按每个 pkpmSlab 行合成 for_panel 截面 ⇒ 期望集合 = 去重厚度）
        r["slab_thicknesses"] = sorted({_num(x[8]) for x in r["slab"]})
        # 独立事实：未被任何梁引用的网格线 / 未被任何荷载引用的荷载截面 / 混凝土构件数
        used_grids = {int(x[4]) for x in r["beam"]}
        r["grid_unused"] = sorted(set(r["grid"]) - used_grids)
        used_ls = {int(x[2]) for x in r["loadseg"]}
        all_ls = {int(x[0]) for x in r["loadsect"]}
        r["loadsect_used"] = sorted(used_ls)
        r["loadsect_unused"] = sorted(all_ls - used_ls)
        mat_of = {sid: v["mat"] for sid, v in r["sect"].items()}
        r["concrete_members"] = sum(1 for rows in (r["col"], r["beam"], r["brace"])
                                    for x in rows if mat_of.get(int(x[3]), 0) == 6)
        # 独立复算几何（契约 §a.5）
        r["geometry"] = _recompute_geometry(r)
        return r
    finally:
        con.close()


def _recompute_geometry(r):
    """按契约 §a.5 独立复算每根构件的 (start, end) 与板面 z，返回 ``{id: (type, level, start, end)}``。"""
    lv, jt, grid = r["level"], r["joint"], r["grid"]
    geo = {}
    for x in r["col"]:
        mid, sf, jj = int(x[0]), int(x[2]), int(x[4])
        ex, ey, hb = _num(x[5]), _num(x[6]), _num(x[8])
        j = jt[jj]
        zb, zt, _h = lv[sf]
        geo[mid] = ("column", sf, (j[0] + ex, j[1] + ey, zb + hb), (j[0] + ex, j[1] + ey, zt))
    for x in r["beam"]:
        mid, sf, g = int(x[0]), int(x[2]), int(x[4])
        h1, h2 = _num(x[6]), _num(x[7])
        a, b = grid[g]
        ja, jb = jt[a], jt[b]
        zb, zt, _h = lv[sf]
        geo[mid] = ("beam", sf, (ja[0], ja[1], zt + h1), (jb[0], jb[1], zt + h2))
    for x in r["brace"]:
        mid, sf, a, b = int(x[0]), int(x[2]), int(x[4]), int(x[5])
        ex1, ey1, h1 = _num(x[6]), _num(x[7]), _num(x[8])
        ex2, ey2, h2 = _num(x[9]), _num(x[10]), _num(x[11])
        ja, jb = jt[a], jt[b]
        zb, zt, _h = lv[sf]
        geo[mid] = ("brace", sf, (ja[0] + ex1, ja[1] + ey1, zt + h1),
                    (jb[0] + ex2, jb[1] + ey2, zt + h2))
    return geo


def raw_bbox(r, include_slabs=True):
    pts = []
    for start, end in ((g[2], g[3]) for g in r["geometry"].values()):
        pts.append(start)
        pts.append(end)
    if include_slabs:
        for x in r["slab"]:
            xs = [_num(t) for t in str(x[4]).split(',') if t.strip()]
            ys = [_num(t) for t in str(x[5]).split(',') if t.strip()]
            zt = r["level"][int(x[2])][1]
            pts.extend((a, b, zt) for a, b in zip(xs, ys))
    if not pts:
        return None
    return (min(p[0] for p in pts), min(p[1] for p in pts), min(p[2] for p in pts),
            max(p[0] for p in pts), max(p[1] for p in pts), max(p[2] for p in pts))


# --------------------------------------------------------------------------
# 独立复算：原始 .pdt / 匹配文件 / ShapeVal
# --------------------------------------------------------------------------
def load_raw_pdt(path):
    """从 ``.pdt`` 文本直接取出本次验收需要的原始事实（自己的极简解析）。"""
    r = {"story_tl": [], "node_xyz": [], "elem_types": {}, "waslab": [], "lines": 0}
    sect = None
    for ln in _text_lines(path):
        s = ln.strip()
        if not s or s.startswith(';'):
            continue
        if s.startswith('$'):
            sect = s.split()[0]
            continue
        if sect == '$STORY':
            mo = re.search(r'TL=\s*(-?[\d.]+)', s)
            if mo and 'NO=' in s:
                r["story_tl"].append(float(mo.group(1)))
        elif sect == '$NODECOOR':
            mo = re.match(r'ID=\s*(-?\d+)\s*,\s*X=\s*(-?[\d.]+)\s*,\s*Y=\s*(-?[\d.]+)\s*,'
                          r'\s*Z=\s*(-?[\d.]+)', s)
            if mo:
                r["node_xyz"].append((float(mo.group(2)), float(mo.group(3)), float(mo.group(4))))
        elif sect == '$SETELEMENT':
            mo = re.search(r'TYPE=\s*(\d+)', s)
            if mo:
                r["elem_types"][mo.group(1)] = r["elem_types"].get(mo.group(1), 0) + 1
        elif sect == '$DEFWASLABSECTION':
            mo = re.search(r'NAME=\s*([^,]+)', s)
            if mo:
                r["waslab"].append(mo.group(1).strip())
    return r


def load_mapping(paths):
    """契约 §e.2 的匹配文件解析（自己的实现）：返回 ``{左值: 右值}``（后加载者覆盖）。"""
    fwd, stats = {}, []
    for p in paths:
        data = 0
        for i, line in enumerate(_text_lines(p), 1):
            s = line.strip()
            if not s or s.startswith("//") or set(s) == {"/"} or "," not in s:
                continue
            left, right = s.split(",", 1)
            left = left.strip()
            right = " ".join(right.split())
            if not left or not right:
                continue
            if not right.startswith("/"):
                right = "/" + right
            fwd[left] = right
            data += 1
        stats.append((os.path.basename(p), data))
    return fwd, stats


def _split_shapeval(sv):
    toks = str(sv).split(',')
    while toks and toks[-1].strip() == '':
        toks.pop()
    return toks


def _packed_spec_str(params):
    buf = bytearray()
    for t in list(params[1:7]):
        v = int(float(t or 0)) if _num_or_none(t) is not None else 0
        buf.append(v & 0xFF)
        buf.append((v >> 8) & 0xFF)
    return bytes(buf).split(b"\x00")[0].decode("ascii", "replace")


def decode_section(sec):
    """契约 §a.4 的 ShapeVal 解码（自己的实现）：返回 ``(params, dims)``。"""
    toks = _split_shapeval(sec["shapeval"])
    params = toks[1:-2] if len(toks) >= 3 else []
    k = sec["kind"]
    d = {}

    def f(i):
        return _num_or_none(params[i]) if i < len(params) else None

    if k == 1 and len(params) >= 2:
        d = {"B": f(0), "H": f(1)}
    elif k == 2 and len(params) >= 6:
        d = {"Tw": f(0), "H": f(1), "B1": f(2), "T1": f(3), "B2": f(4), "T2": f(5)}
    elif k == 3 and len(params) >= 1:
        d = {"d": f(0)}
    elif k == 26 and len(params) >= 7:
        d = {"family": f(0), "subtype": f(1), "H": f(2), "B": f(4), "tf": f(5), "tw": f(6)}
    elif k == 303 and len(params) >= 27:
        d = {"family": f(0), "spec_str": _packed_spec_str(params), "d": f(17), "b": f(19),
             "lib_family": f(26)}
    return params, d


def candidate_keys(sec, dims, params, kind):
    """契约 §e.1 的候选键生成器（自己的实现，顺序与契约一致）。"""
    out = []
    if sec["name"]:
        out.append(sec["name"])
    if sec["kind"] == 26:
        sub = dims.get("subtype")
        if sub is not None and sec["name"]:
            out.append("%s-%s" % (_f(sub), sec["name"]))
    if sec["kind"] == 303:
        lib, spec = dims.get("lib_family"), dims.get("spec_str")
        if lib is not None and spec:
            out.append("%s-%s" % (_f(lib), spec))
    if kind in ("slab", "wall"):
        t = dims.get("T")
        if _num_or_none(t):
            out.append("T%s" % _f(t))
    if sec["kind"] == 1:
        b, h = dims.get("B"), dims.get("H")
        if b is not None and h is not None:
            out.append("矩%sX%s" % (_f(b), _f(h)))
    if params:
        out.append("%s#%s" % (sec["kind"], ",".join(str(p) for p in params)))
    uniq = []
    for c in out:
        if c and c not in uniq:
            uniq.append(c)
    return uniq


def expected_resolution(sec, dims, params, kind, fwd):
    """契约 §e.1/§e.1a/§e.3 的优先级（自己的实现）→ ``(status, source, spec_path)``。"""
    cands = candidate_keys(sec, dims, params, kind)
    for i, key in enumerate(cands):
        if key in fwd:
            return ("resolved", "name" if i == 0 else "shapeval", fwd[key])
    if kind not in ("slab", "wall"):
        if sec["kind"] == 1:
            b, h = dims.get("B"), dims.get("H")
            if b is not None and h is not None:
                return ("parametric", "family", "/USER_RECT-SPEC/Rectangle_Profile")
        elif sec["kind"] == 2:
            need = [dims.get(k) for k in ("Tw", "H", "B1", "T1", "B2", "T2")]
            if all(v is not None for v in need):
                tw, hh, b1, t1, b2, t2 = need
                if abs(b1 - b2) <= 1e-9 and abs(t1 - t2) <= 1e-9:
                    return ("parametric", "family", "/USER_H-SPEC/H_Profile")
        elif sec["kind"] == 3:
            # 契约 §e.3 的 Kind=3 行（变更记录 §0.4-1）：单尺寸 = 直径 → 圆形族（推断，不是 resolved）
            if dims.get("d") is not None:
                return ("inferred", "family", "/USER_CIRCLE-SPEC/Circle_Profile")
    return ("unresolved", "none", "")


# --------------------------------------------------------------------------
# 结果收集
# --------------------------------------------------------------------------
class Checker(object):
    """7 个检查项（每条验收标准 1 项）；项内任何 error 即该项失败。"""

    def __init__(self):
        self.items = []          # (cid, 标题, [error], [明细行])

    def add(self, cid, title, errors, details):
        self.items.append((cid, title, list(errors or []), list(details)))

    def passed_count(self):
        return sum(1 for _c, _t, e, _d in self.items if not e)

    def failed(self):
        return [x for x in self.items if x[2]]


# ==========================================================================
# 检查 1：jwd2pdms 零报错 + 宏编码/计数 + 每根构件有规格引用
# ==========================================================================
def check_1(ch, raw, allow_unresolved):
    det, errs = [], []
    mac = os.path.join(OUT, "JLCJ2.mac")
    rep_path = os.path.join(OUT, "JLCJ2.report.json")
    code, out, err = _run([sys.executable, CLI, "jwd2pdms", SAMPLE_JWD,
                           "--out", mac, "--report", rep_path])
    det.append("命令：python engine/cli.py jwd2pdms <样本 JLCJ2.jwd> --out _acceptance_out/JLCJ2.mac"
               " --report _acceptance_out/JLCJ2.report.json")
    det.append("退出码 = %d" % code)
    if code != 0:
        errs.append("jwd2pdms 退出码 %d ≠ 0" % code)
    if "Traceback" in out or "Traceback" in err:
        errs.append("stdout/stderr 出现 Traceback（未捕获异常）")
    report = {}
    if os.path.isfile(rep_path):
        with open(rep_path, encoding="utf-8") as fh:
            report = json.load(fh)
    else:
        errs.append("未生成报告 %s" % rep_path)
    det.append("report.errors = %s" % json.dumps(report.get("errors", []), ensure_ascii=False))
    if report.get("errors"):
        errs.append("report.errors 非空：%s" % report["errors"])

    # --- 宏字节纪律：GBK 可解码 + CRLF + 无 BOM
    if not os.path.isfile(mac):
        errs.append("未生成宏 %s" % mac)
        ch.add(1, "jwd2pdms 零报错；宏 GBK+CRLF；598/200/13/222；每构件有 SPREF 或 DESP",
               errs, det)
        return None
    blob = _read_bytes(mac)
    try:
        text = blob.decode("gbk")
        det.append("宏字节 = %d；GBK 严格解码通过" % len(blob))
    except UnicodeDecodeError as exc:
        text = ""
        errs.append("宏不是 GBK：%s" % exc)
    if blob[:3] == b"\xef\xbb\xbf":
        errs.append("宏带 BOM（契约 §g 禁止）")
    lone = blob.replace(b"\r\n", b"").count(b"\n")
    if lone:
        errs.append("宏含 %d 个孤立 LF（要求 CRLF）" % lone)
    det.append("无 BOM、孤立 LF = %d" % lone)

    # --- 计数：按 SBFR 分组数 NEW SCTN / NEW PANE（期望值取自原始 .jwd 行数）
    # 两种宏格式都支持（契约 v3 / §o.4：R3 起每个具名 NEW 的名字经唯一化函数走 $!n 变量，
    # 字面名为**禁止**项——acceptance_r3 检查 20 断言 literal_named==0）：
    #   v1/R2 字面形：NEW SBFR /BEAM          → 组名 = 行尾 token
    #   R3 变量形：  !n = !!pkpmjwdUniquename('/BEAM') + NEW SBFR $!n
    #                → 组名 = 唯一化调用的**基名实参**（意图名）
    group, got, pending = None, {}, None
    call_re = re.compile(r"!\w+\s*=\s*!!pkpmjwdUniquename\('(.+)'\)")
    for ln in text.split("\r\n"):
        s = ln.strip()
        mo = call_re.match(s)
        if mo:
            pending = mo.group(1)
            continue
        if s.startswith("NEW SBFR"):
            group = pending if pending else s.split()[-1]
        elif s.startswith("NEW SCTN") and group:
            got[group] = got.get(group, 0) + 1
        elif s.startswith("NEW PANE"):
            got["/PANE"] = got.get("/PANE", 0) + 1
    want = {"/BEAM": raw["seg_counts"]["beam"], "/COLUMN": raw["seg_counts"]["column"],
            "/HBRACE + /VBRACE": raw["seg_counts"]["brace"], "/PANE": raw["slab_count"]}
    got_hb = got.get("/HBRACE", 0)
    got_vb = got.get("/VBRACE", 0)
    table = [("梁 SCTN（SBFR /BEAM）", want["/BEAM"], got.get("/BEAM", 0)),
             ("柱 SCTN（SBFR /COLUMN）", want["/COLUMN"], got.get("/COLUMN", 0)),
             ("支撑 SCTN（/HBRACE+/VBRACE）", want["/HBRACE + /VBRACE"], got_hb + got_vb),
             ("板 PANE", want["/PANE"], got.get("/PANE", 0))]
    for name, w, g in table:
        det.append("  %-28s 宏内 = %-5d 原始 .jwd 行数 = %-5d %s"
                   % (name, g, w, "OK" if w == g else "**不一致**"))
        if w != g:
            errs.append("%s：宏内 %d ≠ 原始 .jwd %d" % (name, g, w))
    if got_hb + got_vb == raw["seg_counts"]["brace"]:
        det.append("  （支撑细分：水平 /HBRACE = %d、竖向 /VBRACE = %d）" % (got_hb, got_vb))

    # --- 每个构件（NEW SCTN 块）必须给出规格引用
    blocks, cur = [], None
    pending_infer = False                       # 上一行是否是 `-- 推断截面…`（§d.4-2b）
    for ln in text.split("\r\n"):
        s = ln.strip()
        if s.startswith("NEW SCTN") or s.startswith("NEW PANE") or s.startswith("NEW STWALL"):
            cur = {"what": s.split()[1], "head": s, "spec": False, "marker": False,
                   "marker_ids": [], "specs": [], "desp": [], "infer_comment": pending_infer}
            pending_infer = False
            blocks.append(cur)
        elif cur is not None:
            if s.startswith("SPREF") or s.startswith("SPRE "):
                cur["spec"] = True
                cur["specs"].append(s.split(None, 1)[1].strip() if len(s.split(None, 1)) > 1 else "")
            elif s.startswith("DESP"):
                cur["desp"].append([_num_or_none(v) for v in s.split()[1:]])
            if "UNRESOLVED SECTION" in s:
                cur["marker"] = True
                mo = re.search(r"UNRESOLVED SECTION\s+(\S+)", s)
                if mo:
                    cur["marker_ids"].append(mo.group(1))
        if s.startswith("--") and "推断截面" in s:
            pending_infer = True
    member_blocks = [b for b in blocks if b["what"] == "SCTN"]
    no_spec = [b for b in member_blocks if not b["spec"]]
    no_any = [b for b in no_spec if not b["marker"]]
    det.append("构件块（NEW SCTN）共 %d 个：有 SPREF/DESP = %d；无 SPREF/DESP = %d"
               "（其中无显式 UNRESOLVED 标记 = %d）"
               % (len(member_blocks), len(member_blocks) - len(no_spec), len(no_spec), len(no_any)))
    if no_spec:
        heads = sorted({b["head"] for b in no_spec})[:6]
        det.append("   无规格引用的构件示例：%s%s"
                   % (", ".join(heads), " …" if len(no_spec) > 6 else ""))
        det.append("   这些块的未解析截面 ID = %s"
                   % sorted({i for b in no_spec for i in b["marker_ids"]}))
    if no_any:
        errs.append("%d 根构件既无 SPREF/DESP 也无 -- UNRESOLVED SECTION 标记（静默跳过，"
                    "契约 §d.4-2 禁止）" % len(no_any))
    if not allow_unresolved:
        if no_spec:
            errs.append("字面判定「每个构件都有 SPREF 或 DESP」不成立：%d/%d 根构件缺规格引用"
                        "（其中 %d 根有契约 §d.4-2 的显式 UNRESOLVED 标记）。"
                        "如需按「显式标记即可」诊断，用 --allow-unresolved-sections 复跑。"
                        % (len(no_spec), len(member_blocks), len(no_spec) - len(no_any)))
    else:
        detail = ("[放宽判定] 按 --allow-unresolved-sections：%d 根无 SPREF/DESP 的构件全部带"
                  "显式 UNRESOLVED 标记；改为校验「标记存在且对应截面在报告 sections.unresolved 里」"
                  % len(no_spec))
        det.append(detail)
        rep_un = {str(d.get("id")) for d in (report.get("sections", {}) or {}).get("unresolved", [])}
        for b in no_spec:
            if not b["marker"]:
                errs.append("%s 无 SPREF/DESP 且无 UNRESOLVED 标记" % b["head"])
            elif not (set(b["marker_ids"]) & rep_un):
                errs.append("%s 的 UNRESOLVED 标记 %s 未出现在报告 sections.unresolved"
                            % (b["head"], b["marker_ids"]))

    # --- 加强：推断截面（契约 §e.3 的 Kind=3）必须写出 圆形族 SPREF + DESP <直径> + 推断注释
    kind3_ids = {sid for sid, sec in raw["sect"].items() if int(sec["kind"]) == 3}
    kind3_d = {sid: decode_section(raw["sect"][sid])[1].get("d") for sid in kind3_ids}
    want_inf = {}
    for sid in kind3_ids:
        n = sum(1 for x in raw["brace"] if int(x[3]) == sid) \
            + sum(1 for x in raw["beam"] if int(x[3]) == sid) \
            + sum(1 for x in raw["col"] if int(x[3]) == sid)
        if n:
            want_inf[sid] = (n, kind3_d[sid])
    inf_blocks = [b for b in member_blocks
                  if b["specs"] and all(x == "/USER_CIRCLE-SPEC/Circle_Profile" for x in b["specs"])]
    det.append("推断构件（SPREF=%s）= %d 根；独立复算 Kind=3 截面 %s 被 %d 根构件引用"
               % ("/USER_CIRCLE-SPEC/Circle_Profile", len(inf_blocks),
                  sorted(want_inf), sum(v[0] for v in want_inf.values())))
    if want_inf:
        exp_n = sum(v[0] for v in want_inf.values())
        exp_desp = sorted(d for _sid, (n, d) in want_inf.items() for _ in range(n))
        if len(inf_blocks) != exp_n:
            errs.append("推断构件数 宏内 %d ≠ 独立复算 %d（Kind=3 截面 %s）"
                        % (len(inf_blocks), exp_n, sorted(want_inf)))
        got_desp = []
        for b in inf_blocks:
            if not b["infer_comment"]:
                errs.append("%s 用圆形族推断规格但没有 -- 推断截面 注释（契约 §d.4-2b）" % b["head"])
            if len(b["desp"]) == 1 and b["desp"][0]:
                got_desp.extend(b["desp"][0])
            else:
                errs.append("%s 的 DESP=%s 不是恰好 1 行有效数值（契约 §d.4-3 / §0.4-2 必须写出）"
                            % (b["head"], b["desp"]))
        if sorted(got_desp) != exp_desp:
            errs.append("推断构件的 DESP 取值 %s ≠ 独立复算的直径多重集 %s"
                        % (sorted(got_desp), exp_desp))
        # 报告里必须能查到该推断（不是 resolved、不是 unresolved）
        rep_inf = [(d.get("table"), d.get("id")) for d in
                   (report.get("sections", {}) or {}).get("detail", [])
                   if d.get("status") == "inferred"]
        if len(rep_inf) != len([k for k in want_inf]):
            errs.append("报告 sections.detail 的 inferred 条目 %s ≠ 独立复算的 Kind=3 截面 %s"
                        % (rep_inf, [("brace", sid) for sid in sorted(want_inf)]))
    elif inf_blocks:
        errs.append("宏内出现 %d 根圆形族推断构件，但独立复算找不到 Kind=3 截面" % len(inf_blocks))
    ch.add(1, "jwd2pdms 零报错；宏 GBK+CRLF；598/200/13/222；每构件有 SPREF 或 DESP",
           errs, det)
    return report


# ==========================================================================
# 检查 2：截面解析覆盖率（无静默跳过；未解析清单与实情一致）
# ==========================================================================
def check_2(ch, raw, report, fwd):
    det, errs = [], []
    # --- 本样本"用到的每个截面"（独立枚举：段表引用的截面 + 每个 pkpmSlab 合成板截面）
    want = {}          # key -> [status/source/spec, {构件类别: 用量}]
    for mtype, ids in raw["used_sect_ids"].items():
        kind = mtype                                    # 'beam'/'col'/'brace' 即 §e.6 的 kind
        seg_key = {"beam": "beam", "column": "col", "brace": "brace"}[mtype]
        for sid in ids:
            sec = raw["sect"][sid]
            params, dims = decode_section(sec)
            key = (sec["table"], sid, sec["name"])
            n = sum(1 for x in raw[seg_key] if int(x[3]) == sid)
            if key in want:                             # 同一截面被多类构件引用（Report 会合并）
                want[key][1][mtype] = want[key][1].get(mtype, 0) + n
            else:
                want[key] = [expected_resolution(sec, dims, params, kind, fwd), {mtype: n}]
    for t in raw["slab_thicknesses"]:
        sec = {"kind": 0, "name": "T%g" % t, "table": "panel", "shapeval": ""}
        dims = {"T": t}
        used = sum(1 for x in raw["slab"] if abs(_num(x[8]) - t) <= TOL)
        want[("panel", -1, sec["name"])] = [expected_resolution(sec, dims, [], "slab", fwd),
                                            {"slab": used}]
    det.append("独立枚举「被用到的截面」= %d 个（构件引用 %d 个 + 板厚合成 %d 个）"
               % (len(want), len(want) - len(raw["slab_thicknesses"]),
                  len(raw["slab_thicknesses"])))
    det.append("板厚取值：%s（每个 pkpmSlab 行都合成一个板截面）"
               % ", ".join("T%g×%d" % (t, sum(1 for x in raw["slab"] if abs(_num(x[8]) - t) <= TOL))
                           for t in raw["slab_thicknesses"]))

    # --- 报告的覆盖情况
    sec_block = (report or {}).get("sections") or {}
    detail = sec_block.get("detail") or []
    have = {(d.get("table"), d.get("id"), d.get("name")): d for d in detail}
    det.append("报告 sections.detail = %d 条；total=%s resolved=%s parametric=%s inferred=%s"
               " unresolved=%d%s"
               % (len(detail), sec_block.get("total"), sec_block.get("resolved"),
                  sec_block.get("parametric"), sec_block.get("inferred"),
                  len(sec_block.get("unresolved") or []),
                  ("；未解析条目 = %s" % [(d.get("table"), d.get("id"), d.get("name"))
                                          for d in (sec_block.get("unresolved") or [])])
                  if sec_block.get("unresolved") else ""))
    missing = sorted(k for k in want if k not in have)
    extra = sorted(k for k in have if k not in want)
    if missing:
        errs.append("报告未覆盖 %d 个被用到的截面（静默跳过）：%s" % (len(missing), missing[:5]))
    if extra:
        errs.append("报告多出 %d 个未被用到的截面条目：%s" % (len(extra), extra[:5]))
    det.append("逐条比对：缺失 = %d，多余 = %d" % (len(missing), len(extra)))

    # --- 逐条核对状态/来源/spec/used_by
    bad = []
    for k, (exp, used_by_want) in sorted(want.items()):
        d = have.get(k)
        if d is None:
            continue
        got = (d.get("status"), d.get("source"), d.get("spec_path"))
        if got != exp:
            bad.append("%s：报告 %s ≠ 独立复算 %s" % (k, got, exp))
        used_by = d.get("used_by") or {}
        for mtype, n_used in sorted(used_by_want.items()):
            if used_by.get(mtype) != n_used:
                bad.append("%s：used_by[%s]=%s ≠ 独立复算 %d"
                           % (k, mtype, used_by.get(mtype), n_used))
    for b in bad[:8]:
        det.append("  ** %s" % b)
    if bad:
        errs.append("%d 个截面的结论与独立复算不一致（前 3 条：%s）" % (len(bad), bad[:3]))
    if sec_block.get("total") != len(want):
        errs.append("sections.total=%s ≠ 独立枚举 %d" % (sec_block.get("total"), len(want)))

    # --- 未解析清单与实情一致
    exp_un = sorted(k for k, v in want.items() if v[0][0] == "unresolved")
    rep_un = sorted((d.get("table"), d.get("id"), d.get("name"))
                    for d in (sec_block.get("unresolved") or []))
    det.append("未解析（独立复算）= %s" % (exp_un,))
    det.append("未解析（报告）    = %s" % (rep_un,))
    if exp_un != rep_un:
        errs.append("未解析清单不一致：报告 %s ≠ 独立复算 %s" % (rep_un, exp_un))
    statuses = [v[0][0] for v in want.values()]
    exp_counts = {s: statuses.count(s)
                  for s in ("resolved", "parametric", "inferred", "unresolved")}
    got_counts = {"resolved": sec_block.get("resolved"), "parametric": sec_block.get("parametric"),
                  "inferred": sec_block.get("inferred"),
                  "unresolved": len(sec_block.get("unresolved") or [])}
    if exp_counts != got_counts:
        errs.append("状态计数不一致：报告 %s ≠ 独立复算 %s" % (got_counts, exp_counts))
    det.append("状态计数：报告 %s；独立复算 %s" % (got_counts, exp_counts))

    # --- 加强：inferred 条目必须机器可见（status/spec/desp/evidence），且不得混进 resolved/unresolved
    inf_want = sorted(k for k, v in want.items() if v[0][0] == "inferred")
    inf_got = [d for d in detail if d.get("status") == "inferred"]
    det.append("推断条目（独立复算）= %s；报告 = %s"
               % (inf_want, [(d.get("table"), d.get("id"), d.get("name"), d.get("source"),
                              d.get("spec_path"), d.get("desp_params")) for d in inf_got]))
    for k in inf_want:
        d = have.get(k)
        if d is None:
            errs.append("推断截面 %s 未出现在报告 sections.detail" % (k,))
            continue
        exp = want[k][0]
        if d.get("spec_path") != exp[2]:
            errs.append("%s 的 spec_path=%r ≠ 契约 §e.3 的 %r" % (k, d.get("spec_path"), exp[2]))
        if not d.get("evidence"):
            errs.append("%s 的 status=inferred 但 evidence 为空（契约 §e.5a/§h 要求可追溯）" % (k,))
        if not d.get("reason"):
            errs.append("%s 的 status=inferred 但 reason（残余风险/改法）为空" % (k,))
        if k in {(x.get("table"), x.get("id"), x.get("name"))
                 for x in (sec_block.get("unresolved") or [])}:
            errs.append("%s 既标 inferred 又出现在 sections.unresolved（状态必须唯一）" % (k,))
    if inf_want and sec_block.get("inferred") != len(inf_want):
        errs.append("报告 sections.inferred=%s ≠ 独立复算 %d"
                    % (sec_block.get("inferred"), len(inf_want)))

    # --- 报告里每条未解析必须写明原因（不可空）
    no_reason = [d.get("id") for d in (sec_block.get("unresolved") or []) if not d.get("reason")]
    if no_reason:
        errs.append("未解析条目缺 reason：%s" % no_reason)
    det.append("每条未解析都带 reason：%s" % ("是" if not no_reason else "否"))
    ch.add(2, "截面解析覆盖率：每个被用到的截面都有结论；未解析清单与实情一致",
           errs, det)


# ==========================================================================
# 检查 3：几何自检（层标高 / 构件端点 Z / 板顶点 Z vs pkpmFloor 推导值）
# ==========================================================================
def check_3(ch, raw):
    import jwd_read                                     # SUT
    det, errs = [], []
    model = jwd_read.read_jwd(SAMPLE_JWD)
    # 层标高
    lv_bad = []
    for l in model.levels:
        want = raw["level"].get(l.stdflr_id)
        if want is None or not _pairs_equal((l.z_bot, l.z_top, l.height), want):
            lv_bad.append((l.stdflr_id, (l.z_bot, l.z_top, l.height), want))
    det.append("层标高：%d 层；与 pkpmFloor(LevelB, LevelB+Height) 逐项一致 = %d/%d"
               % (len(model.levels), len(model.levels) - len(lv_bad), len(model.levels)))
    det.append("  实测层顶 = %s" % sorted(l.z_top for l in model.levels))
    det.append("  pkpmStdFlr.Height 全 0（%s）⇒ 按契约 §a.3 不得使用"
               % sorted({_num(x[2]) for x in raw["stdflr"]}))
    if lv_bad:
        errs.append("层标高不一致：%s" % lv_bad[:5])
    # 节点
    j_bad = []
    for j in model.joints.values():
        want = raw["joint"].get(j.id)
        if want is None:
            j_bad.append((j.id, "缺失"))
            continue
        x, y, hd, sf = want
        zb, zt, _h = raw["level"][sf]
        if (abs(j.x - x) > TOL or abs(j.y - y) > TOL or abs(j.z - (zt + hd)) > TOL):
            j_bad.append((j.id, (j.x, j.y, j.z), (x, y, zt + hd)))
    det.append("节点：%d 个；z == 层顶 + HDiff 且 x/y 一致 = %d/%d"
               % (len(model.joints), len(model.joints) - len(j_bad), len(model.joints)))
    if j_bad:
        errs.append("节点不一致：%s" % j_bad[:5])
    # 构件端点（含 x/y/z 全分量）
    bad, badz = [], 0
    for m in model.members:
        want = raw["geometry"].get(m.id)
        if want is None:
            bad.append((m.id, "独立复算缺失"))
            continue
        wtype, wlev, ws, we = want
        if m.type != wtype or m.level != wlev:
            bad.append((m.id, "type/level", (m.type, m.level), (wtype, wlev)))
            continue
        for tag, got, exp in (("start", m.start, ws), ("end", m.end, we)):
            if not _pairs_equal(got, exp):
                bad.append((m.id, tag, tuple(round(v, 6) for v in got),
                            tuple(round(v, 6) for v in exp)))
                if abs(got[2] - exp[2]) > TOL:
                    badz += 1
    det.append("构件：%d 根（梁 %d/柱 %d/支撑 %d）；端点 (x,y,z) 与契约 §a.5 独立复算一致"
               " = %d/%d；其中 Z 不符 = %d"
               % (len(model.members), model.counts()["members"]["beam"],
                  model.counts()["members"]["column"], model.counts()["members"]["brace"],
                  len(model.members) - len(bad), len(model.members), badz))
    for b in bad[:5]:
        det.append("  ** %s" % (b,))
    if bad:
        errs.append("%d 根构件端点与推导值不符（Z 不符 %d）" % (len(bad), badz))
    # 板
    z_bad, vz_bad = [], []
    for s in model.slabs:
        zb, zt, h = raw["level"][s.level]
        if abs(s.z - zt) > TOL:
            z_bad.append((s.id, s.z, zt))
    for x in raw["slab"]:
        zb, zt, h = raw["level"][int(x[2])]
        for t in str(x[6]).split(','):
            if t.strip() and abs(_num(t) - h) > TOL:
                vz_bad.append((x[0], _num(t), h))
                break
    det.append("板：%d 块；z == 层顶(pkpmFloor.LevelB+Height) = %d/%d"
               % (len(model.slabs), len(model.slabs) - len(z_bad), len(model.slabs)))
    det.append("板顶点 Z 列（pkpmSlab.VertexZ）：%d 块中与所在层层高不符 = %d（契约 §a.3/§a.5："
               "板面 = 层顶 = LevelB + VertexZ）" % (len(raw["slab"]), len(vz_bad)))
    if z_bad:
        errs.append("板面标高不一致：%s" % z_bad[:5])
    if vz_bad:
        errs.append("板顶点 Z 与层高不一致：%s" % vz_bad[:5])
    det.append("例外合计 = %d（层 %d + 节点 %d + 构件 %d + 板 %d + 板顶点 Z %d）"
               % (len(lv_bad) + len(j_bad) + len(bad) + len(z_bad) + len(vz_bad),
                  len(lv_bad), len(j_bad), len(bad), len(z_bad), len(vz_bad)))
    ch.add(3, "几何自检：层标高/构件端点 Z/板顶点 Z 与 pkpmFloor 推导值逐项一致（0 例外）",
           errs, det)


# ==========================================================================
# 检查 4：.pdt 与 .jwd 两个读取器的对比表（差异有解释）
# ==========================================================================
def check_4(ch, raw_j, raw_p):
    import jwd_read, pdt_read                          # SUT
    det, errs = [], []
    mj = jwd_read.read_jwd(SAMPLE_JWD)
    mp = pdt_read.read_pdt(SAMPLE_PDT)

    # 独立复算（jwd：原始 SQL + 契约公式；pdt：原始文本）
    zt_j = sorted(v[1] for v in raw_j["level"].values())
    bbox_j = raw_bbox(raw_j)
    cnt_j = raw_j["seg_counts"]
    z_p = sorted(set(p[2] for p in raw_p["node_xyz"]))
    bbox_p = (min(p[0] for p in raw_p["node_xyz"]), min(p[1] for p in raw_p["node_xyz"]),
              min(p[2] for p in raw_p["node_xyz"]), max(p[0] for p in raw_p["node_xyz"]),
              max(p[1] for p in raw_p["node_xyz"]), max(p[2] for p in raw_p["node_xyz"]))
    ty = raw_p["elem_types"]
    cnt_p = {"column": ty.get("1", 0), "beam": ty.get("2", 0), "brace": 0}

    # 读取器输出
    cj = mj.counts()["members"]
    cp = mp.counts()["members"]
    bj = _model_bbox(mj)
    bp = _model_bbox(mp)
    zt_j_reader = sorted(l.z_top for l in mj.levels)
    z_p_reader = sorted(l.z_bot for l in mp.levels)

    # 各读取器与自身原始来源逐项核对
    if zt_j_reader != zt_j:
        errs.append(".jwd 读取器层顶 %s ≠ 独立复算 %s" % (zt_j_reader, zt_j))
    if cj != cnt_j:
        errs.append(".jwd 读取器构件数 %s ≠ 原始段表行数 %s" % (cj, cnt_j))
    if bj != bbox_j:
        errs.append(".jwd 读取器包围盒 %s ≠ 独立复算 %s" % (bj, bbox_j))
    if z_p_reader != z_p:
        errs.append(".pdt 读取器标高 %s ≠ $NODECOOR 去重 Z %s" % (z_p_reader, z_p))
    if cp != cnt_p:
        errs.append(".pdt 读取器构件数 %s ≠ $SETELEMENT TYPE 直方图 %s" % (cp, cnt_p))
    if bp != bbox_p:
        errs.append(".pdt 读取器包围盒 %s ≠ $NODECOOR 极点 %s" % (bp, bbox_p))

    def fmt3(v):
        return None if v is None else tuple(round(x, 3) for x in v)

    rows = [
        ("层标高",
         "%d 层（楼层型）层顶=%s 层底=%s" % (len(mj.levels), zt_j_reader,
                                             sorted(l.z_bot for l in mj.levels)),
         "%d 个平面（平面型）标高=%s" % (len(mp.levels), z_p_reader),
         zt_j_reader == z_p_reader),
        ("构件总数",
         "%d（梁 %d/柱 %d/支撑 %d）" % (mj.counts()["members_total"], cj["beam"],
                                       cj["column"], cj["brace"]),
         "%d（梁 %d/柱 %d/支撑 %d）" % (mp.counts()["members_total"], cp["beam"],
                                       cp["column"], cp["brace"]),
         mj.counts()["members_total"] == mp.counts()["members_total"]),
        ("包围盒(E,N,U)",
         str(fmt3(bj)), str(fmt3(bp)), bj == bp),
    ]

    # 差异解释（其事实前提在本函数内逐条校验）
    inter_z = sorted(set(zt_j) & set(z_p))
    tl = sorted(set(raw_p["story_tl"]))
    tl_in_planes = [v for v in tl if any(abs(v - z) <= TOL for z in z_p)]
    pj = {(round(g[2][0], 1), round(g[2][1], 1), round(g[2][2], 1))
          for g in raw_j["geometry"].values()}
    pp = {(round(p[0], 1), round(p[1], 1), round(p[2], 1)) for p in raw_p["node_xyz"]}
    common = len(pj & pp)
    expl = {
        "层标高":
            "口径不同（契约 §a.3）：.jwd 是楼层型（z_bot<z_top，来源 pkpmFloor.LevelB/Height），"
            ".pdt 是平面型（z_bot==z_top，来源 $NODECOOR 的不同 Z，不按 FLOORID）；"
            "且两样本不是同一栋结构：两组标高交集 = %s（%d 个），.jwd 的 %d 个层顶里 %d 个"
            "出现在 .pdt 的 %d 个平面标高里；.pdt 的 %d 个标高里只有 %d 个等于 $STORY.TL"
            "（%s），其余是层内标高/夹层 ⇒ 层标高列本就不可比。"
            % (inter_z, len(inter_z), len(zt_j), len(inter_z), len(z_p), len(z_p),
               len(tl_in_planes), tl),
        "构件总数":
            "两样本不同：构件起点坐标集合交集 = %d（.jwd %d 个去重点 vs .pdt %d 个 $NODECOOR 点，"
            "坐标范围 .jwd E∈[%g,%g]/N∈[%g,%g] 与 .pdt E∈[%g,%g]/N∈[%g,%g] 不重合）；"
            "口径不同：.pdt 的 $SETELEMENT 只出现 TYPE=%s（%s）⇒ .pdt 侧没有支撑，"
            "而 .jwd 有 %d 根支撑（pkpmBraceSeg 行数）。"
            % (common, len(pj), len(pp),
               bbox_j[0], bbox_j[3], bbox_j[1], bbox_j[4],
               bbox_p[0], bbox_p[3], bbox_p[1], bbox_p[4],
               sorted(ty), sorted(ty.items()), cnt_j["brace"]),
        "包围盒(E,N,U)":
            "两样本不同（同上：平面范围与标高范围互不覆盖）；.jwd 的 U∈[%g,%g] 来自 5 个楼层"
            "（首层层底 %g、顶层层顶 %g），.pdt 的 U∈[%g,%g] 来自其样本含 %g 基础层与 %g 顶层"
            "（实测 $NODECOOR 极值 = 读取器包围盒逐分量相同）。"
            % (bbox_j[2], bbox_j[5], bbox_j[2], bbox_j[5],
               bbox_p[2], bbox_p[5], bbox_p[2], bbox_p[5]),
    }
    det.append("对比表（读取器值 = engine 读取结果；独立复算 = 本测试从原始样本重算）")
    for name, a, b, eq in rows:
        det.append("  [%s] 一致=%s" % (name, "是" if eq else "否"))
        det.append("     .jwd 读取器 : %s" % a)
        det.append("     .pdt 读取器 : %s" % b)
        det.append("     差异解释    : %s" % ("（一致，无需解释）" if eq else expl[name]))
    det.append("各读取器与其**自身原始来源**逐项核对：层标高/构件总数/包围盒 6 项断言，"
               "不符 = %d" % len(errs))
    det.append("差异解释的事实前提（本测试已验证）：标高交集=%s；$STORY.TL=%s（%d/%d 命中平面）；"
               "起点坐标交集=%d；$SETELEMENT TYPE=%s"
               % (inter_z, tl, len(tl_in_planes), len(tl), common, sorted(ty.items())))
    # 解释必须覆盖每一处"不一致"
    for name, _a, _b, eq in rows:
        if not eq and not expl.get(name):
            errs.append("%s 不一致但没有解释" % name)
    ch.add(4, ".pdt 与 .jwd 读取器的层标高/构件总数/包围盒对比表，差异有解释",
           errs, det)


def _model_bbox(model):
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


# ==========================================================================
# 检查 5：往返 JLCJ2.jwd → Model → .jwd' → Model
# ==========================================================================
#: 往返后必须**逐行逐列相同**的表（列 = 规范模型承载的关键列）
_RT_EXACT = (
    ("pkpmStdFlr", ("ID", "No_", "Height")),
    ("pkpmFloor", ("ID", "No_", "Name", "StdFlrID", "LevelB", "Height")),
    ("pkpmJoint", ("ID", "No_", "StdFlrID", "X", "Y", "HDiff")),
    ("pkpmColSeg", ("ID", "No_", "StdFlrID", "SectID", "JtID", "EccX", "EccY", "Rotation",
                    "HDiffB")),
    ("pkpmBeamSeg", ("ID", "No_", "StdFlrID", "SectID", "GridID", "Ecc", "HDiff1", "HDiff2",
                     "Rotation", "JYDef")),
    ("pkpmBraceSeg", ("ID", "No_", "StdFlrID", "SectID", "Jt1ID", "Jt2ID", "EccX1", "EccY1",
                      "HDiff1", "EccX2", "EccY2", "HDiff2", "Rotation")),
    ("pkpmSlab", ("ID", "No_", "StdFlrID", "GridsID", "VertexX", "VertexY", "VertexZ",
                  "RoomIsHole", "Thickness", "dead", "live", "nEdge", "xc", "yc")),
    ("pkpmBeamSect", ("ID", "No_", "Name", "Mat", "Kind", "ShapeVal")),
    ("pkpmColSect", ("ID", "No_", "Name", "Mat", "Kind", "ShapeVal")),
    ("pkpmBraceSect", ("ID", "No_", "Name", "Mat", "Kind", "ShapeVal")),
    ("pkpmLoadSeg", ("ID", "No", "SectID", "Type", "ElementID", "strParas1", "nPtCnt",
                     "strParasX", "strParasY", "strParasZ", "StdFlrID")),
)
#: 往返后行是原表子集（只写被引用的行），且同 ID 行各列相同
#: （第三个元素 = 允许不同的列，理由写在检查 5 的输出里）
_RT_SUBSET = (
    ("pkpmLoadSect", ("ID", "No", "Loadname", "ElementKind", "ShapeVal"), ("No", "Loadname")),
    ("pkpmProperty", ("ID", "Name", "Type", "ShapeVal"), ()),
    ("pkpmSlabHole", ("ID", "No_", "StdFlrID", "SectID", "JtID", "SlabID", "EccX", "EccY",
                      "Rotation"), ("ID", "No_")),
)
#: 上面这三张表"允许不同的列"的语义说明（契约 §b.3 / jwd_write 的 warnings）
_RT_ALLOWED_WHY = {
    "pkpmLoadSect": "No 按写入顺序重排、Loadname 写空串（规范模型不承载荷载名；"
                    "write_jwd 的 warnings 已注明）；ID/ElementKind/ShapeVal 必须相同",
    "pkpmProperty": "规范模型只承载构件材料等级（HNTDJ/GANGH），往返行必须逐列出现在原表里",
    "pkpmSlabHole": "ID 为按 RoomIsHole=1 合成的序号、No_ 用 pkpmSlab.No_（样本 hole ID "
                    "63830..63882 不可还原；write_jwd 的 warnings 已注明）",
}
#: 行数按契约 §b.3 归并/合成变化的表 → （期望行数计算式说明, 期望值）
def _rt_rowcount_expectations(raw):
    n_beam = raw["seg_counts"]["beam"]
    return {
        "pkpmAxis": ("每根梁合成 1 行轴线（契约 §b.3/§12#13）", n_beam),
        "pkpmGrid": ("每根梁合成 1 行网格线（契约 §b.3）", n_beam),
        "pkpmLoadSect": ("只写被荷载引用的荷载截面", len(raw["loadsect_used"])),
        "pkpmProperty": ("只写构件材料等级（混凝土构件数）", raw["concrete_members"]),
        "pkpmSatTower": ("规范模型不承载（契约 §b.3 只建表）", 0),
        "pkpmSatTowPara": ("规范模型不承载", 0),
        "pkpmSatTowReinInfo": ("规范模型不承载", 0),
        "pkpmStdFlrPara": ("规范模型不承载", 0),
        "pkpmSysInfo": ("规范模型不承载", 0),
    }


def check_5(ch, raw):
    import jwd_read, jwd_write                        # SUT
    det, errs = [], []
    rt = os.path.join(OUT, "JLCJ2.roundtrip.jwd")
    m1 = jwd_read.read_jwd(SAMPLE_JWD)
    stats = jwd_write.write_jwd(m1, rt)
    m2 = jwd_read.read_jwd(rt)
    det.append("链路：JLCJ2.jwd → read_jwd → write_jwd(_acceptance_out/JLCJ2.roundtrip.jwd) → read_jwd")

    # --- Model ↔ Model
    d1, d2 = m1.to_dict(), m2.to_dict()
    diffs = []
    for k in sorted(set(d1) | set(d2)):
        if k in ("source", "notes"):
            continue                                  # 路径不同 / notes 是读取期信息
        if d1.get(k) != d2.get(k):
            diffs.append(k)
    det.append("模型逐字段一致（除 source/notes）：%s；不一致的域 = %s"
               % ("是" if not diffs else "否", diffs or "无"))
    if diffs:
        errs.append("往返后模型域不一致：%s" % diffs)
    c1, c2 = m1.counts(), m2.counts()
    det.append("counts 一致 = %s；%s" % (c1 == c2, json.dumps(c2, ensure_ascii=False)))
    if c1 != c2:
        errs.append("往返后 counts 不同：%s vs %s" % (c1, c2))

    # --- DB ↔ DB：逐表行数
    ca, cb = _table_counts(_conn(SAMPLE_JWD)), _table_counts(_conn(rt))
    exp = _rt_rowcount_expectations(raw)
    diffs, unexplained = [], []
    for t in sorted(ca):
        if ca[t] == cb.get(t):
            continue
        if t in exp:
            why, want = exp[t]
            ok = (cb.get(t) == want)
            diffs.append((t, ca[t], cb.get(t), why, want, ok))
            if not ok:
                unexplained.append("%s：rt=%s ≠ 期望 %s（%s）" % (t, cb.get(t), want, why))
        else:
            unexplained.append("%s：%d → %s（无解释）" % (t, ca[t], cb.get(t)))
    det.append("逐表行数：46 张表中相同 = %d；有差异 = %d（全部应有解释）"
               % (sum(1 for t in ca if ca[t] == cb.get(t)), len(diffs)))
    for t, a, b, why, want, ok in diffs:
        det.append("  %-18s 原 %-6d → 往返 %-6d 期望 %-6d %s（%s）"
                   % (t, a, b, want, "OK" if ok else "**不符**", why))
    if raw["grid_unused"]:
        det.append("    （原始 pkpmGrid 有 %d 行未被任何梁引用：%s —— 契约 §b.3 的合成轴网"
                   "每根梁一行，故往返后消失）" % (len(raw["grid_unused"]), raw["grid_unused"][:8]))
    if raw["loadsect_unused"]:
        det.append("    （原始 pkpmLoadSect 有 %d 行未被任何荷载引用：%s）"
                   % (len(raw["loadsect_unused"]), raw["loadsect_unused"]))
    if unexplained:
        errs.extend(unexplained[:6])

    # --- 关键列逐列比对
    ac, bc = _conn(SAMPLE_JWD), _conn(rt)
    for tbl, cols in _RT_EXACT:
        q = "SELECT %s FROM %s ORDER BY ID" % (",".join(cols), tbl)
        ra, rb = _rows(ac, q), _rows(bc, q)
        bad_cols = []
        if len(ra) != len(rb):
            bad_cols = ["行数 %d≠%d" % (len(ra), len(rb))]
        else:
            for x, y in zip(ra, rb):
                if tuple(x) != tuple(y):
                    for j, c in enumerate(cols):
                        if x[j] != y[j] and c not in bad_cols:
                            bad_cols.append(c)
        det.append("  %-16s 关键列 %d 个、行 %d：%s"
                   % (tbl, len(cols), len(ra), "一致" if not bad_cols else "差异 %s" % bad_cols))
        if bad_cols:
            errs.append("%s 关键列往返不一致：%s" % (tbl, bad_cols))
    for tbl, cols, allowed in _RT_SUBSET:
        q = "SELECT %s FROM %s ORDER BY ID" % (",".join(cols), tbl)
        ra = _rows(ac, q)
        rb = _rows(bc, q)
        key = "SlabID" if tbl == "pkpmSlabHole" else "ID"
        kk = cols.index(key)
        om = {}
        for r in ra:
            om.setdefault(r[kk], []).append(r)
        diff_cols, bad_key, n_diff = set(), [], 0
        if tbl == "pkpmProperty":
            # 原表同一 ID 有多行（各自列名不同）⇒ 按"整行多重集包含"判定
            from collections import Counter
            ctr = Counter(ra)
            missing = [r for r in rb if ctr[r] <= 0]
            bad_key = missing[:3]
            n_diff = len(missing)
            det.append("  %-16s 往返 %d 行按整行多重集包含于原表 %d 行：缺失 %d 行"
                       % (tbl, len(rb), len(ra), len(missing)))
        else:
            dup = [k for k, v in om.items() if len(v) > 1]
            for r in rb:
                cand = om.get(r[kk])
                if not cand:
                    bad_key.append(r[kk])
                    continue
                o = cand[0]
                if tuple(r) != tuple(o):
                    n_diff += 1
                    for j, c in enumerate(cols):
                        if r[j] != o[j] and c not in allowed:
                            diff_cols.add(c)
            det.append("  %-16s 往返 %d 行按 %s 对应原表 %d 行：键失配 %d；有差异的行 %d；"
                       "差异列（允许集之外）= %s"
                       % (tbl, len(rb), key, len(ra), len(bad_key), n_diff,
                          sorted(diff_cols) or "无"))
            if dup:
                errs.append("%s 原表 %s 不唯一：%s" % (tbl, key, dup[:3]))
        det.append("       允许不同的列 = %s（%s）"
                   % (list(allowed) or "无", _RT_ALLOWED_WHY.get(tbl, "")))
        if bad_key:
            errs.append("%s 往返行的 %s=%s 未在原表中出现" % (tbl, key, bad_key[:5]))
        if diff_cols:
            errs.append("%s 关键列往返不一致（允许集之外）：%s" % (tbl, sorted(diff_cols)))
    ac.close()
    bc.close()

    # --- write_jwd 返回值与实际库一致
    tw = stats.get("tables") or {}
    mism = [t for t in ca if tw.get(t, 0) != cb.get(t)]
    det.append("write_jwd 返回的 tables 计数与实际写入一致：%s（不符 %d 张）"
               % ("是" if not mism else "否", len(mism)))
    if mism:
        errs.append("write_jwd 返回的表计数与实际库不符：%s" % mism[:6])
    ch.add(5, "往返 JLCJ2.jwd → Model → .jwd' → Model：逐表行数与关键列一致（差异有解释）",
           errs, det)


# ==========================================================================
# 检查 6：导出链路（自造 dump → pdms2jwd，产物外键全部可解析）
# ==========================================================================
#: 本测试自造的 dump 文本（依据契约 §c.2/§c.4 的文法；GBK+CRLF 写盘）
FIXTURE_DUMP = [
    "#PKPM-JWD-PDMSDUMP 1.0",
    "UNITS mm",
    "#SITE /PKPM_JWD",
    "#ZONE /ACCTEST",
    "#STRU /MAINFRAME",
    "#FRMW /STL_FRAME/EL1",
    "#SBFR /COLUMN",
    "#SCTN /STL_COL_1 COLUMN /H_INTERNATIONAL-SPEC/HN450X200 400 400 -2000 400 400 -1000 U rboc rboc 0",
    "#SCTN /STL_COL_2 COLUMN /USER_RECT-SPEC/Rectangle_Profile 600 600 600 600 -2000 600 600 -1000 U rboc rboc 0",
    "#SBFR /BEAM",
    "#SCTN /BM_1 BEAM /H_INTERNATIONAL-SPEC/HN300X150 400 400 -1000 6400 400 -1000 E lbos lbos 0",
    "#SBFR /HBRACE",
    "#SCTN /HB_1 HBRACE /TUBE_TUBE-SPEC/D194X8.0 400 400 -1000 6400 400 -1000 E - - 0",
    "#SBFR /VBRACE",
    "#FRMW /FLOOR&WALL",
    "#SBFR /SLAB",
    "#PANE /SLAB_1 120 400 400 -1000 6400 400 -1000 6400 4400 -1000 400 4400 -1000"
    " ~ /Concrete_Slab-SPEC/T120 YNZU dbot",
    "#SBFR /WALL",
    "#STWALL /W_1 /Concrete_Wall-SPEC/WALL-600 3000 0 0 -2000 6000 0 -2000 ~ 600",
    "#FRMW /GRID",
    "#SCTN /AXIS_1 BEAM /H_INTERNATIONAL-SPEC/HN300X150 0 0 0 1000 0 0 E - - 0",
    "#END",
]


def check_6(ch):
    det, errs = [], []
    dpath = os.path.join(OUT, "acc_fixture_dump.txt")
    jpath = os.path.join(OUT, "acc_fixture.jwd")
    rpath = os.path.join(OUT, "acc_fixture.report.json")
    with open(dpath, "wb") as fh:                       # 契约 §c.1：GBK + CRLF
        fh.write(("\r\n".join(FIXTURE_DUMP) + "\r\n").encode("gbk"))
    det.append("自造 dump：%s（%d 行，GBK+CRLF；含 2 柱 1 梁 1 水平支撑 1 板 1 墙 + 1 条 /GRID 轴网线）"
               % (os.path.basename(dpath), len(FIXTURE_DUMP)))
    code, out, err = _run([sys.executable, CLI, "pdms2jwd", dpath, "--out", jpath,
                           "--secmap", SAMPLE_MAP, "--report", rpath])
    det.append("命令：python engine/cli.py pdms2jwd <自造 dump> --out _acceptance_out/acc_fixture.jwd"
               " --secmap <样本匹配文件>；退出码 = %d" % code)
    if code != 0:
        errs.append("pdms2jwd 退出码 %d ≠ 0：%s" % (code, (out + err).strip()[:300]))
        ch.add(6, "导出链路：自造 dump → pdms2jwd，产物外键全部可解析", errs, det)
        return
    report = {}
    if os.path.isfile(rpath):
        with open(rpath, encoding="utf-8") as fh:
            report = json.load(fh)
    if report.get("errors"):
        errs.append("报告 errors 非空：%s" % report["errors"])

    con = _conn(jpath)
    try:
        counts = _table_counts(con)
        nonzero = {t: n for t, n in counts.items() if n}
        det.append("产物 .jwd 非空表：%s" % json.dumps(nonzero, ensure_ascii=False))
        want = {"pkpmStdFlr": 2, "pkpmFloor": 2, "pkpmJoint": 5, "pkpmGrid": 1, "pkpmAxis": 1,
                "pkpmBeamSect": 1, "pkpmColSect": 2, "pkpmBraceSect": 1, "pkpmColSeg": 2,
                "pkpmBeamSeg": 1, "pkpmBraceSeg": 1, "pkpmSlab": 1}
        for t, n in sorted(want.items()):
            got = counts.get(t, 0)
            if got != n:
                errs.append("%s 行数 %d ≠ 期望 %d" % (t, got, n))
        det.append("关键表行数期望 %s ⇒ 全部命中：%s"
                   % (json.dumps(want, ensure_ascii=False),
                      "是" if not errs else "否"))
        if counts.get("pkpmWallSeg", 0):
            errs.append("pkpmWallSeg 非空（契约 §a.8：墙不写回 .jwd）")

        # --- 外键全解析：从产物自身的 DDL 抽出全部 REFERENCES 子句逐条校验
        fks, bad = [], []
        for (tbl, sql) in _rows(con, "SELECT name, sql FROM sqlite_master WHERE type='table'"):
            if not sql:
                continue
            for mo in re.finditer(r"(\w+)\s+[^,()]*?REFERENCES\s+(\w+)\s*\(\s*(\w+)\s*\)", sql):
                col, rtbl, rcol = mo.group(1), mo.group(2), mo.group(3)
                if (tbl, col) in [(f[0], f[1]) for f in fks]:
                    continue
                fks.append((tbl, col, rtbl, rcol))
        for tbl, col, rtbl, rcol in fks:
            vals = [v for (v,) in _rows(con, 'SELECT DISTINCT "%s" FROM "%s" WHERE "%s" IS NOT NULL'
                                        % (col, tbl, col))]
            for v in vals:
                n = con.execute('SELECT COUNT(*) FROM "%s" WHERE "%s" = ?' % (rtbl, rcol),
                                (v,)).fetchone()[0]
                if not n:
                    bad.append("%s.%s=%s 在 %s.%s 中不存在" % (tbl, col, v, rtbl, rcol))
        det.append("DDL REFERENCES 抽出 %d 对外键（列级），取值检查 %d 处，不可解析 = %d"
                   % (len(fks), len(fks), len(bad)))
        for b in bad[:5]:
            det.append("  ** %s" % b)
        if bad:
            errs.append("产物外键不可解析：%s" % bad[:5])

        # --- 另加关键外键的显式检查（不依赖正则抽 DDL）
        def exists(tbl, col, val):
            return con.execute('SELECT COUNT(*) FROM "%s" WHERE "%s" = ?' % (tbl, col),
                               (val,)).fetchone()[0] > 0

        explicit, ebad = 0, []
        for sid, sf, jt in _rows(con, "SELECT SectID, StdFlrID, JtID FROM pkpmColSeg"):
            explicit += 1
            for tbl, val in (("pkpmColSect", sid), ("pkpmStdFlr", sf), ("pkpmJoint", jt)):
                if not exists(tbl, "ID", val):
                    ebad.append("pkpmColSeg → %s.ID=%s" % (tbl, val))
        for sid, sf, gid in _rows(con, "SELECT SectID, StdFlrID, GridID FROM pkpmBeamSeg"):
            explicit += 1
            for tbl, val in (("pkpmBeamSect", sid), ("pkpmStdFlr", sf), ("pkpmGrid", gid)):
                if not exists(tbl, "ID", val):
                    ebad.append("pkpmBeamSeg → %s.ID=%s" % (tbl, val))
        for sid, sf, j1, j2 in _rows(con, "SELECT SectID, StdFlrID, Jt1ID, Jt2ID"
                                          " FROM pkpmBraceSeg"):
            explicit += 1
            for tbl, val in (("pkpmBraceSect", sid), ("pkpmStdFlr", sf),
                             ("pkpmJoint", j1), ("pkpmJoint", j2)):
                if not exists(tbl, "ID", val):
                    ebad.append("pkpmBraceSeg → %s.ID=%s" % (tbl, val))
        for gid, j1, j2, ax in _rows(con, "SELECT ID, Jt1ID, Jt2ID, AxisID FROM pkpmGrid"):
            explicit += 3
            for v, tbl in ((j1, "pkpmJoint"), (j2, "pkpmJoint"), (ax, "pkpmAxis")):
                if not exists(tbl, "ID", v):
                    ebad.append("pkpmGrid → %s.%s" % (tbl, v))
        for sid, sf in _rows(con, "SELECT ID, StdFlrID FROM pkpmSlab"):
            explicit += 1
            if not exists("pkpmStdFlr", "ID", sf):
                ebad.append("pkpmSlab.StdFlrID=%s" % sf)
        det.append("关键外键显式检查 %d 处（段表→截面/层/节点、网格→节点/轴线、板→层），"
                   "不可解析 = %d" % (explicit, len(ebad)))
        if ebad:
            errs.append("关键外键不可解析：%s" % ebad[:5])
    finally:
        con.close()
    ch.add(6, "导出链路：自造 dump → pdms2jwd，产物外键全部可解析", errs, det)


# ==========================================================================
# 检查 7：静态检查（PML/宏编码；install.ps1 -DryRun 不改盘）
# ==========================================================================
def check_7(ch):
    det, errs = [], []
    for name in PDMS_FILES:
        p = os.path.join(PDMS_PKG, name)
        if not os.path.isfile(p):
            errs.append("缺文件 %s" % p)
            continue
        blob = _read_bytes(p)
        try:
            blob.decode("gbk")
            gbk = "GBK 可解码"
        except UnicodeDecodeError as exc:
            gbk = "GBK 解码失败：%s" % exc
            errs.append("%s 不是 GBK" % name)
        bom = blob[:3] == b"\xef\xbb\xbf"
        lone = blob.replace(b"\r\n", b"").count(b"\n")
        det.append("  %-24s %7d 字节  %s  BOM=%s  孤立LF=%d"
                   % (name, len(blob), gbk, bom, lone))
        if bom:
            errs.append("%s 带 BOM" % name)
        if lone:
            errs.append("%s 含 %d 个孤立 LF（PDMS 侧产物要求 CRLF）" % (name, lone))

    if not os.path.isfile(DESIGN_UIC):
        errs.append("找不到 %s：无法做 -DryRun 的不改盘校验" % DESIGN_UIC)
    if not os.path.isfile(INSTALL_PS1):
        errs.append("缺安装脚本 %s" % INSTALL_PS1)
    if errs:
        ch.add(7, "静态检查：PML/宏 GBK+CRLF；install.ps1 -DryRun 有输出且不改盘", errs, det)
        return

    before = _sha256(DESIGN_UIC)
    ps = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                      "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
    p = subprocess.run([ps, "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-File", INSTALL_PS1, "-DryRun"], capture_output=True)
    out = p.stdout.decode("gbk", "replace")
    errout = p.stderr.decode("gbk", "replace")
    lines = [l for l in out.splitlines() if l.strip()]
    after = _sha256(DESIGN_UIC)
    det.append("命令：powershell -NoProfile -ExecutionPolicy Bypass -File install/install.ps1 -DryRun")
    det.append("  退出码 = %d；stdout = %d 字节 / %d 个非空行；stderr = %d 字节"
               % (p.returncode, len(p.stdout), len(lines), len(p.stderr)))
    if p.returncode != 0:
        errs.append("install.ps1 -DryRun 退出码 %d ≠ 0（stderr: %s）" % (p.returncode, errout[:200]))
    if not lines:
        errs.append("install.ps1 -DryRun 无输出")
    if "DRYRUN-OK" not in out:
        errs.append("输出里没有 DRYRUN-OK（未走到「只打印不落盘」的收尾）")
    det.append("  design.uic sha256 前 = %s" % before[:16])
    det.append("  design.uic sha256 后 = %s" % after[:16])
    det.append("  design.uic 哈希不变 = %s（%s）" % (before == after, DESIGN_UIC))
    if before != after:
        errs.append("install.ps1 -DryRun 改动了 design.uic（哈希变化）")
    ch.add(7, "静态检查：PML/宏 GBK+CRLF；install.ps1 -DryRun 有输出且不改盘", errs, det)


# ==========================================================================
# 主流程
# ==========================================================================
def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(
        description="PKPM-JWD导入导出 独立验收测试（7 条验收标准）",
        epilog="默认按字面判定「每个构件都有 SPREF 或 DESP」（本样本 811/811，含契约 §e.1a 的 "
               "12 根 Kind=3 推断圆形构件）；--allow-unresolved-sections 只是诊断开关，"
               "把该句放宽为「SPREF/DESP 或契约 §d.4-2 的显式 UNRESOLVED 标记」，不是通过路径。")
    ap.add_argument("--allow-unresolved-sections", action="store_true",
                    help="诊断用：把验收标准 1 的末句放宽为「SPREF/DESP 或显式 UNRESOLVED 标记」")
    args = ap.parse_args(list(argv) if argv is not None else None)

    os.makedirs(OUT, exist_ok=True)
    print("=" * 78)
    print(" PKPM-JWD导入导出 验收测试（独立复算；确定性）")
    print("=" * 78)
    print("工作区根 : %s" % ROOT)
    print("交付包   : %s" % PKG)
    print("样本     : %s" % SAMPLE_DIR)
    print("自建产物 : %s" % OUT)
    print("判定方式 : %s" % ("放宽（允许契约 §d.4-2 的 UNRESOLVED 标记）"
                             if args.allow_unresolved_sections else "严格（按字面）"))
    print()

    missing = [p for p in (SAMPLE_JWD, SAMPLE_PDT, SAMPLE_MAP, CLI, EXTRA_MAP)
               if not os.path.isfile(p)]
    if missing:
        print("无法开始：缺输入 %s" % missing)
        print(json.dumps({"passed": False, "passedCount": 0, "failedCount": 7},
                         ensure_ascii=False, separators=(",", ":")))
        return 2

    ch = Checker()
    raw = load_raw_jwd(SAMPLE_JWD)
    raw_p = load_raw_pdt(SAMPLE_PDT)
    fwd, map_stats = load_mapping([SAMPLE_MAP, EXTRA_MAP])
    print("独立复算：原始 .jwd 表 %d 张；层 %d；构件 %d（梁 %d/柱 %d/支撑 %d）；板 %d（洞 %d）；"
          "截面 %d"
          % (len(raw["tables"]), len(raw["level"]), raw["member_count"],
             raw["seg_counts"]["beam"], raw["seg_counts"]["column"],
             raw["seg_counts"]["brace"], raw["slab_count"], raw["hole_count"],
             len(raw["sect"])))
    print("独立复算：.pdt 节点 %d 个 / 标高 %d 个 / $SETELEMENT TYPE 直方图 %s"
          % (len(raw_p["node_xyz"]), len(set(p[2] for p in raw_p["node_xyz"])),
             sorted(raw_p["elem_types"].items())))
    print("独立复算：匹配文件 %s（合并后左值 %d 条）"
          % (" + ".join("%s %d 条" % (n, c) for n, c in map_stats), len(fwd)))
    print()

    report = check_1(ch, raw, args.allow_unresolved_sections)
    calls = (
        (2, "截面解析覆盖率：每个被用到的截面都有结论；未解析清单与实情一致",
         lambda: check_2(ch, raw, report or {}, fwd)),
        (3, "几何自检：层标高/构件端点 Z/板顶点 Z 与 pkpmFloor 推导值逐项一致（0 例外）",
         lambda: check_3(ch, raw)),
        (4, ".pdt 与 .jwd 读取器的层标高/构件总数/包围盒对比表，差异有解释",
         lambda: check_4(ch, raw, raw_p)),
        (5, "往返 JLCJ2.jwd → Model → .jwd' → Model：逐表行数与关键列一致（差异有解释）",
         lambda: check_5(ch, raw)),
        (6, "导出链路：自造 dump → pdms2jwd，产物外键全部可解析", lambda: check_6(ch)),
        (7, "静态检查：PML/宏 GBK+CRLF；install.ps1 -DryRun 有输出且不改盘",
         lambda: check_7(ch)),
    )
    for cid, title, fn in calls:
        n_before = len(ch.items)
        try:
            fn()
        except Exception as exc:                 # 单条检查内部异常 ⇒ 该条判失败并留痕
            import traceback
            if len(ch.items) == n_before:        # 该检查还没登记自己的条目
                ch.add(cid, title,
                       ["检查内部异常：%s: %s" % (type(exc).__name__, exc),
                        traceback.format_exc().strip().splitlines()[-1]], [])
            else:                                # 已登记 ⇒ 改为失败并附异常
                c, t, e, d = ch.items[-1]
                ch.items[-1] = (c, t, e + ["该检查内部异常：%s: %s"
                                           % (type(exc).__name__, exc)], d)

    print("-" * 78)
    for cid, title, errors, details in ch.items:
        print("[%s] %s" % ("FAIL" if errors else "PASS", title))
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
        for cid, title, errors, _details in failed:
            print("检查 %d 未通过：%s" % (cid, title))
            for e in errors:
                print("    - %s" % e)
            print()
    print(json.dumps({"passed": n_fail == 0, "passedCount": n_pass, "failedCount": n_fail},
                     ensure_ascii=False, separators=(",", ":")))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
