# -*- coding: utf-8 -*-
"""PDMS 目录（Catalogue）/等级（Specification）宏 —— **生成器**（契约 v2 §(l)）。

本模块只做一件事：把 :class:`sectionlib.SectionTable`（PKPM ⇄ PDMS 截面的
双向转化表）渲染成一份 **可在 PDMS 里执行的目录+规格重建宏**。

--------------------------------------------------------------------------
契约与证据
--------------------------------------------------------------------------
* 骨架、两遍式（第一遍 ``NEW…END`` 建元素、第二遍 ``OLD`` 补引用且无 ``END``）、
  参数化链（TEXT→DTSET→PTSSET→GMSSET→SPRFILE→SPWLD→SPECIFICATION→SELEC→SPCOMPONENT）、
  头尾逐字、不变量 1–8、清场范式、唯一名与 ASCII 纪律：
  契约 §l.1–§l.4；``_recon/db_pdms_catalogue.md`` §1/§2/§3/§6。
* 参数化族的几何（PTSSET 的 PLINE、GMSSET 的 SRECTANGLE/SANNULUS/SPROFILE）
  **逐字取自用户原件**（只读）：

  - ``/USER_RECT``   〃 ``PKPM（PDMS数据库）.txt:2826-2995``
  - ``/USER_CIRCLE`` 〃 ``:2494-2615``
  - ``/USER_H``      〃 ``:946-1280``

  三族的 DESP 顺序与契约 §e.3 一致（RECT=B,H；CIRCLE=D；H=B1,B2,H,Tw,T1,T2），
  故 ``secmap.resolve`` 给出的 ``desp_params`` 可直接喂给生成的 ``SPREF``。

--------------------------------------------------------------------------
安全闸（契约 §l.1，硬约束：命中即 ``DbMacroError``，不"警告后继续"）
--------------------------------------------------------------------------
1. 宏只创建/修改本包自己的 4 个容器（``DbOptions`` 的 4 个名字，``/PKPM2PDMS_`` 前缀）；
2. 生成物里 **不得** 出现 ``NEW``/``OLD``/``DELETE`` + 用户既有容器名
   （``/PKPM_USER``、``/PKPM_STSS``、``/PKPMDATA``、``/PKPM_USER_SECTION``、``/PKPM_LIB``）；
   转化表里带的原目录名（``SectionRec.pdms_catalogue``）一律**映射成本包容器**；
3. ``clean_first=True`` 时清场目标必须 ∈ 上述 4 个容器（含 ``suffix``）；
4. 产物 **纯 ASCII**（写前断言）。

--------------------------------------------------------------------------
与契约 §l.3 的三处**已声明偏离**（都是契约内部自相矛盾/无数据可依，取硬约束一侧）
--------------------------------------------------------------------------
A. §l.3.1 的头注释示例含中文，但 §l.1-5 要求产物纯 ASCII 并断言 ⇒ 头注释写 ASCII。
B. §l.3.2 要求型钢库写"11 个 ``STSECTION``"，但转化表（§k.1 ``SectionRec``）没有
   "族 → STSECTION"字段 ⇒ 缺省按 **每个 SPECIFICATION 一个 STSECTION**，名
   ``/STSS_<SPEC 基名去 SECTION_ 前缀>``（原件 11 个里 10 个可用此规则复现，
   ``/SECTION_H_I`` → 原件为 ``/STSS_I_H``，要精确复现请传 ``DbOptions.stsection_of``）；
   用户侧仍用原件名 ``/USER_SECTION``。
C. 除 ``/USER_RECT``、``/USER_CIRCLE``、``/USER_H`` 三族外，转化表没有几何信息 ⇒
   这些族的 ``PTSSET`` 只写参考点（``PKEY NA``）、**不写** ``GMSSET``（同时第二遍也不写
   ``GSTR``，避免引用不存在的元素）；该差异逐族进 ``plan`` 与报告，禁止臆造轮廓。

``DbOptions`` 在 §l.2 的冻结字段之外另加若干**有缺省值**的渲染选项（不改冻结语义），
见 :class:`DbOptions`。``generate_db_macro(table, opts) -> str`` 与
``write_db_macro(path, text) -> str`` 的调用形式与契约 §(l) 一致。
"""

import os
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:                      # 与 cli.py 同一约定：绝对导入、单实例
    sys.path.insert(0, _HERE)

__all__ = [
    "DbOptions", "DbMacroError", "generate_db_macro", "write_db_macro",
    "macro_plan", "scan_forbidden_names", "safety_report", "resolve_containers",
    "FORBIDDEN_NAMES", "TEMPLATE_FAMILIES",
]

CONTRACT_PKG_PREFIX = "/PKPM2PDMS_"

#: 用户既有容器名（契约 §l.1-2 / 变更记录 §0.4-7）。生成物里出现即违规。
FORBIDDEN_NAMES: Tuple[str, ...] = (
    "/PKPM_USER", "/PKPM_STSS", "/PKPMDATA", "/PKPM_USER_SECTION", "/PKPM_LIB",
)

_OP_RE = re.compile(r"^\s*(NEW|OLD|DELETE)\s+(\S+)\s*(.*)$", re.IGNORECASE)
_PLACEHOLDER_PARAM_RE = re.compile(r"^Parameter\s*\d+$", re.IGNORECASE)


class DbMacroError(ValueError):
    """生成期的契约违反（安全闸命中、不可渲染的记录等）。"""


# ---------------------------------------------------------------------------
# 选项
# ---------------------------------------------------------------------------

@dataclass
class DbOptions(object):
    """生成选项。前 9 个字段的名字与缺省**逐字照抄契约 §l.2**。"""

    # ---- 契约 §l.2 冻结字段 ----
    catalogue_user: str = "/PKPM2PDMS_USER"
    catalogue_stss: str = "/PKPM2PDMS_STSS"
    spec_world_user: str = "/PKPM2PDMS_USER_SECTION"
    spec_world_lib: str = "/PKPM2PDMS_LIB"
    uniquify: bool = True
    suffix: str = ""
    clean_first: bool = False
    onerror_label: str = "/PKPKERR"
    date_text: str = ""

    # ---- 本实现的渲染选项（全部有缺省；见模块 docstring 的"已声明偏离"）----
    source_note: str = ""            # 头注释里的 <table 来源>；空 ⇒ "SectionTable"
    stsection_of: Optional[Dict[str, str]] = None   # {族名(如 /C_COMMON): STSECTION 名}
    input_wrap: bool = False         # True ⇒ 另写 INPUT BEGIN/END/FINISH（§l.3.1 默认不写）
    report: Optional[Dict[str, Any]] = None         # 传入即被填充（统计 + 差异 + 安全闸）

    #: 渲染后实际的 4 个容器名（由 :func:`resolve_containers` 填）
    resolved: Dict[str, str] = field(default_factory=dict)


def resolve_containers(opts: DbOptions) -> Dict[str, str]:
    """把 4 个顶层容器名按 ``uniquify``/``suffix`` 展开（契约 §l.4 / §0.4-9）。

    * 显式 ``suffix``：容器名 = 基名 + suffix（用户点名的确定名）；
      ``clean_first=True`` 时**重建容器再加运行戳**（``suffix + _YYYYMMDD_HHMMSS``）——
      清场段只清成员（``DELETE … MEM`` 语义未直证，§12#16），若重建同名容器必然撞名
      （PDMS 无 OVERRIDE）⇒ 重建一律落在新名上，重跑永不撞名。
    * 缺省（``uniquify=True``、无 ``suffix``）：容器名 = 基名 + ``_YYYYMMDD_HHMMSS``
      （到**秒**；旧版只到日 ⇒ 同日重跑必撞名，R3 复核发现⑤b/c）。
    * 清场目标（``clean_first``）单独用**清场后缀**：显式 suffix 原样；
      缺省用**当日日期戳**（清旧命名规则的容器，尽力而为）——见 ``_render_text``。
    """
    run_stamp = time.strftime("_%Y%m%d_%H%M%S")
    if opts.suffix:
        build_suffix = opts.suffix + (run_stamp if opts.clean_first else "")
    else:
        build_suffix = run_stamp if opts.uniquify else ""
    build_suffix = build_suffix if opts.uniquify or opts.suffix else ""
    clean_suffix = (opts.suffix or time.strftime("_%Y%m%d")) if opts.uniquify else ""
    for s in (build_suffix, clean_suffix):
        if s and not re.match(r"^[A-Za-z0-9_]+$", s):
            raise DbMacroError("suffix 只允许 ASCII 字母/数字/下划线：%r" % s)
    out = {
        "catalogue_user": opts.catalogue_user + build_suffix,
        "catalogue_stss": opts.catalogue_stss + build_suffix,
        "spec_world_user": opts.spec_world_user + build_suffix,
        "spec_world_lib": opts.spec_world_lib + build_suffix,
    }
    for key, name in out.items():
        if not name.startswith(CONTRACT_PKG_PREFIX):
            raise DbMacroError("容器名必须带 %s 前缀（契约 §l.1-1）：%s=%r"
                               % (CONTRACT_PKG_PREFIX, key, name))
    opts.resolved = dict(out)
    opts.resolved["clean_suffix"] = clean_suffix
    return out


# ---------------------------------------------------------------------------
# 安全闸（契约 §l.1）
# ---------------------------------------------------------------------------

def scan_forbidden_names(text: str, extra_names: Sequence[str] = ()) -> List[str]:
    """扫描文本，返回"危险行"清单（空 = 通过）。

    只看 ``NEW``/``OLD``/``DELETE`` 开头的行；行内出现任一禁用容器名
    （按标识符边界匹配，避免 ``/PKPM_USER`` 误命中 ``/PKPM_USER_SECTION``）即记一条。
    """
    bad: List[str] = []
    names = list(FORBIDDEN_NAMES) + [n for n in extra_names if n]
    for lineno, line in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
        if not _OP_RE.match(line):
            continue
        for name in names:
            pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])")
            if pat.search(line):
                bad.append("L%d %s：出现用户既有容器名 %s" % (lineno, line.strip(), name))
                break
    return bad


def safety_report(text: str, opts: Optional[DbOptions] = None,
                  clean_targets: Sequence[str] = ()) -> Dict[str, Any]:
    """契约 §m.3 的 ``report.db.safety`` 三键（生成方向），外加自检明细。"""
    opts = opts or DbOptions()
    res = opts.resolved or {
        "catalogue_user": opts.catalogue_user, "catalogue_stss": opts.catalogue_stss,
        "spec_world_user": opts.spec_world_user, "spec_world_lib": opts.spec_world_lib}
    bases = (opts.catalogue_user, opts.catalogue_stss,
             opts.spec_world_user, opts.spec_world_lib)
    own = {v for k, v in res.items() if k != "clean_suffix"}
    # 清场目标是"基名 + 清场后缀"（§0.4-9）：与重建容器（基名 + 运行戳）不同名，但仍是本包容器
    owned = all(any(t == b or t.startswith(b + "_") for b in bases) for t in clean_targets)
    return {
        "forbidden_names_scanned": True,
        "forbidden_hits": scan_forbidden_names(text),
        "clean_targets": list(clean_targets),
        "clean_targets_owned": owned and bool(clean_targets) or not clean_targets,
        "ascii_only": text.isascii(),
        "containers": {k: v for k, v in res.items() if k != "clean_suffix"},
    }


# ---------------------------------------------------------------------------
# 参数化族模板（几何逐字取自用户原件，见模块 docstring）
# ---------------------------------------------------------------------------

def _pl(block: str) -> List[str]:
    return [ln for ln in block.split("\n") if ln.strip()]


#: /USER_RECT：DESP[1]=B、DESP[2]=H（原件 L2826-2992 的 PTSSET/GMSSET）
_RECT_PTSSET = _pl("""
NEW PLINE
PKEY TOS
PX 0
PY ( ATTRIB DESP[2 ] / 2 )
DX 0
DY 0
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY LTOS
PX ( - ATTRIB DESP[1 ] / 2 )
PY ( ATTRIB DESP[2 ] / 2 )
DX 0
DY 0
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY RTOS
PX ( ATTRIB DESP[1 ] / 2 )
PY ( ATTRIB DESP[2 ] / 2 )
DX 0
DY 0
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY BOS
PX 0
PY ( - ATTRIB DESP[2 ] / 2 )
DX 0
DY 0
PLAX -Y
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY LBOS
PX ( - ATTRIB DESP[1 ] / 2 )
PY ( - ATTRIB DESP[2 ] / 2 )
DX 0
DY 0
PLAX -Y
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY LEFT
PX ( - ATTRIB DESP[1 ] / 2 )
PY 0
DX 0
DY 0
PLAX -X
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY RIGH
PX ( ATTRIB DESP[1 ] / 2 )
PY 0
DX 0
DY 0
PLAX X
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY RBOS
PX ( ATTRIB DESP[1 ] / 2 )
PY ( - ATTRIB DESP[2 ] / 2 )
DX 0
DY 0
PLAX -Y
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY NA
PX 0
PY 0
DX 0
DY 0
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
""")

_RECT_GMSSET = _pl("""
NEW SRECTANGLE
PX 0
PY 0
PXLE ( ATTRIB DESP[1 ] )
PYLE ( ATTRIB DESP[2 ] )
DX 0
DY 0
DXL 0
DYL 0
TUFL true
END
""")

#: /USER_CIRCLE：DESP[1]=D（原件 L2494-2614）
_CIRCLE_PTSSET = _pl("""
NEW PLINE
PKEY GG
PX 0
PY ( ATTRIB DESP[1 ] / 2 )
DX 0
DY 0
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY SS
PX 0
PY ( - ATTRIB DESP[1 ] / 2 )
DX 0
DY 0
PLAX -Y
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY MM
PX ( - ATTRIB DESP[1 ] / 2 )
PY 0
DX 0
DY 0
PLAX -X
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY AA
PX ( ATTRIB DESP[1 ] / 2 )
PY 0
DX 0
DY 0
PLAX X
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY NA
PX 0
PY 0
DX 0
DY 0
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
""")

_CIRCLE_GMSSET = _pl("""
NEW SANNULUS
PX 0
PY 0
PANG 180
PRAD ( ATTRIB DESP[1 ] / 2 )
PWID ( ATTRIB DESP[1 ] / 2 )
DX 0
DY 0
DRAD 0
DWID 0
TUFL true
END
NEW SANNULUS
PX 0
PY 0
PANG ( -180 )
PRAD ( ATTRIB DESP[1 ] / 2 )
PWID ( ATTRIB DESP[1 ] / 2 )
DX 0
DY 0
DRAD 0
DWID 0
TUFL true
END
""")

#: /USER_H：DESP[1..6]=B1,B2,H,Tw,T1,T2（原件 L946-1279）
_H_PTSSET = _pl("""
NEW PLINE
PKEY TOS
PX 0
PY ( ATTRIB DESP[3 ] / 2 )
DX 0
DY 0
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY BOS
PX 0
PY ( - ATTRIB DESP[3 ] / 2 )
DX 0
DY 0
PLAX -Y
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY LTOS
PX ( - ATTRIB DESP[1 ] / 2 )
PY ( ATTRIB DESP[3 ] / 2 )
DX 0
DY 0
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY LTBS
PX ( - ATTRIB DESP[1 ] / 2 )
PY ( ATTRIB DESP[3 ] / 2 - ATTRIB DESP[5 ] )
DX 0
DY 0
PLAX -Y
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY LBOS
PX ( - ATTRIB DESP[1 ] / 2 )
PY ( - ATTRIB DESP[3 ] / 2 )
DX 0
DY 0
PLAX -Y
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY LBTS
PX ( - ATTRIB DESP[1 ] / 2 )
PY ( - ATTRIB DESP[3 ] / 2 + ATTRIB DESP[6 ] )
DX 0
DY 0
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY RTOS
PX ( ATTRIB DESP[1 ] / 2 )
PY ( ATTRIB DESP[3 ] / 2 )
DX 0
DY 0
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY RTBS
PX ( ATTRIB DESP[1 ] / 2 )
PY ( ATTRIB DESP[3 ] / 2 - ATTRIB DESP[5 ] )
DX 0
DY 0
PLAX -Y
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY RBOS
PX ( ATTRIB DESP[1 ] / 2 )
PY ( - ATTRIB DESP[3 ] / 2 )
DX 0
DY 0
PLAX -Y
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY RBTS
PX ( ATTRIB DESP[1 ] / 2 )
PY ( - ATTRIB DESP[3 ] / 2 + ATTRIB DESP[6 ] )
DX 0
DY 0
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY NAL
PX ( - ATTRIB DESP[4 ] / 2 )
PY 0
DX 0
DY 0
PLAX -X
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY NAR
PX ( ATTRIB DESP[4 ] / 2 )
PY 0
DX 0
DY 0
PLAX X
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
NEW PLINE
PKEY NA
PX 0
PY 0
DX 0
DY 0
TUFL true
PURP CLEW
CCON ANY
END
""")

_H_GMSSET = _pl("""
NEW SPROFILE
TUFL true
NEW SPVERT /USH1
PX ( - ATTRIB DESP[2 ] / 2 )
PY ( ATTRIB DESP[3 ] / 2 - ATTRIB DESP[6 ] )
END
NEW SPVERT /USH2
PX ( - ATTRIB DESP[2 ] / 2 )
PY ( ATTRIB DESP[3 ] / 2 )
END
NEW SPVERT /USH3
PX ( ATTRIB DESP[2 ] / 2 )
PY ( ATTRIB DESP[3 ] / 2 )
END
NEW SPVERT /USH4
PX ( ATTRIB DESP[2 ] / 2 )
PY ( ATTRIB DESP[3 ] / 2 - ATTRIB DESP[6 ] )
END
NEW SPVERT /USH5
PX ( ATTRIB DESP[4 ] / 2 )
PY ( ATTRIB DESP[3 ] / 2 - ATTRIB DESP[6 ] )
END
NEW SPVERT /USH6
PX ( ATTRIB DESP[4 ] / 2 )
PY ( - ATTRIB DESP[3 ] / 2 + ATTRIB DESP[5 ] )
END
NEW SPVERT /USH7
PX ( ATTRIB DESP[1 ] / 2 )
PY ( - ATTRIB DESP[3 ] / 2 + ATTRIB DESP[5 ] )
END
NEW SPVERT /USH8
PX ( ATTRIB DESP[1 ] / 2 )
PY ( - ATTRIB DESP[3 ] / 2 )
END
NEW SPVERT /USH9
PX ( - ATTRIB DESP[1 ] / 2 )
PY ( - ATTRIB DESP[3 ] / 2 )
END
NEW SPVERT /USH10
PX ( - ATTRIB DESP[1 ] / 2 )
PY ( - ATTRIB DESP[3 ] / 2 + ATTRIB DESP[5 ] )
END
NEW SPVERT /USH11
PX ( - ATTRIB DESP[4 ] / 2 )
PY ( - ATTRIB DESP[3 ] / 2 + ATTRIB DESP[5 ] )
END
NEW SPVERT /USH12
PX ( - ATTRIB DESP[4 ] / 2 )
PY ( ATTRIB DESP[3 ] / 2 - ATTRIB DESP[6 ] )
END
END
""")

#: 三个有原件几何证据的参数化族（族基名 → 模板）
TEMPLATE_FAMILIES: Dict[str, Dict[str, Any]] = {
    "RECT": {
        # (参数名, DKEY, DPRO) 顺序即 DESP 下标（契约 §e.3：DESP=[B,H]）
        "params": [("B", "B", "500"), ("H", "H", "500")],
        "texts": ["Parameter 1"],            # 原件只写 1 条占位 TEXT
        "ptsset": _RECT_PTSSET,
        "gmsset": _RECT_GMSSET,
        "para": "0",                         # 参数化族的 PARA 是占位（原件 L2990）
        "evidence": "PKPM（PDMS数据库）.txt:2826-2995",
    },
    "CIRCLE": {
        "params": [("D", "D", "300")],
        "texts": ["Parameter 1"],
        "ptsset": _CIRCLE_PTSSET,
        "gmsset": _CIRCLE_GMSSET,
        "para": "0",
        "evidence": "PKPM（PDMS数据库）.txt:2494-2615",
    },
    "H": {
        "params": [("B1", "APAR", "250"), ("B2", "BPAR", "250"), ("H", "CPAR", "500"),
                   ("Tw", "DPAR", "8"), ("T1", "EPAR", "10"), ("T2", "FPAR", "10")],
        "texts": ["B1", "B2", "H", "Tw", "T1", "T2"],
        "ptsset": _H_PTSSET,
        "gmsset": _H_GMSSET,
        "para": "250 250 500 8 10 10",
        "evidence": "PKPM（PDMS数据库）.txt:946-1280",
    },
}

#: 只写参考点的占位 PTSSET（无几何的族）
_NA_ONLY_PTSSET = _pl("""
NEW PLINE
PKEY NA
PX 0
PY 0
DX 0
DY 0
CLFL true
TUFL true
PURP CLEW
CCON ANY
END
""")


# ---------------------------------------------------------------------------
# SectionRec 投影（对字段缺失容错；契约 §k.1 的字段名是唯一依据）
# ---------------------------------------------------------------------------

def _attr(rec: Any, name: str, default: Any = "") -> Any:
    v = getattr(rec, name, default)
    return default if v is None else v


def _extra(rec: Any) -> Dict[str, Any]:
    e = _attr(rec, "extra", {})
    return e if isinstance(e, dict) else {}


def _param_fields(rec: Any) -> List[Tuple[str, int, str]]:
    """``rec.params`` → ``[(name, desp_index, default), …]``。"""
    out: List[Tuple[str, int, str]] = []
    for p in (_attr(rec, "params", []) or []):
        if isinstance(p, dict):
            nm, di, dv = p.get("name", ""), p.get("desp_index", 0), p.get("default", "")
        else:
            nm = getattr(p, "name", "")
            di = getattr(p, "desp_index", 0)
            dv = getattr(p, "default", "")
        try:
            di = int(di or 0)
        except (TypeError, ValueError):
            di = 0
        out.append((str(nm or "").strip(), di, str(dv if dv is not None else "").strip()))
    return out


def _path_join(owner: str, name: str) -> str:
    """``('/PKPM2PDMS_LIB', '/SECTION_C')`` → ``/PKPM2PDMS_LIB/SECTION_C``（只给消息用）。"""
    return "%s/%s" % ((owner or "").rstrip("/"), (name or "").lstrip("/"))


def _split_spec(path: str) -> Tuple[str, str]:
    """``/OWNER/NAME`` → ``(owner, name)``。"""
    p = (path or "").strip()
    if not p.startswith("/"):
        p = "/" + p.lstrip("/")
    i = p.find("/", 1)
    if i < 0:
        return p, ""
    return p[:i], p[i + 1:]


def _family_of_owner(owner: str) -> str:
    """``/USER_RECT-SPEC`` → ``/USER_RECT``（契约 §l.3.4-1 的命名不变量）。"""
    o = owner.rstrip("/")
    if o.endswith("-SPEC"):
        o = o[:-len("-SPEC")]
    return o or "/"


def _fam_base(family: str) -> str:
    n = family.rsplit("/", 1)[-1]
    if n.upper().startswith("USER_"):
        n = n[len("USER_"):]
    return n.upper()


def _is_parametric_rec(rec: Any) -> bool:
    if bool(_attr(rec, "is_parametric", False)):
        return True
    return any(di > 0 for _, di, _ in _param_fields(rec))


def _side_of(rec: Any, family: str) -> str:
    """``'user'`` / ``'stss'``：决定落在哪个本包 CATALOGUE（§l.1-1 只能用自己的容器）。"""
    if family.startswith("/USER_"):
        return "user"
    cat = str(_attr(rec, "pdms_catalogue", "") or "").strip()
    if cat:
        base = cat.rstrip("/").rsplit("/", 1)[-1].upper()
        if base in ("PKPM_USER", "PKPM2PDMS_USER") or base.startswith("PKPM_USER"):
            return "user"
        return "stss"
    return "stss"


# ---------------------------------------------------------------------------
# 生成计划（渲染前的摊平；CLI 的报告与差异清单也用它）
# ---------------------------------------------------------------------------

class _Family(object):
    __slots__ = ("name", "catalogue", "world", "specname", "stsection", "params",
                 "texts", "parametric", "ptsset", "gmsset", "para", "recs", "specs",
                 "dup_specs", "template", "placeholder_geometry", "desc", "notes")

    def __init__(self, name: str):
        self.name = name
        self.catalogue = ""
        self.world = ""
        self.specname = ""
        self.stsection = ""
        self.params: List[Tuple[str, str, str, int]] = []   # (name, dkey, dpro, desp_index)
        self.texts: List[str] = []
        self.parametric = False
        self.ptsset: List[str] = []
        self.gmsset: List[str] = []
        self.para = ""
        self.recs: List[Tuple[str, str, Any]] = []
        # 去重后的规格（同一 STCATEGORY 下同 path 的 PDMS 对象只有一个：契约 §l.3.4 / §12#22）
        self.specs: List[Tuple[str, str, Any]] = []
        self.dup_specs = 0
        self.template = ""
        self.placeholder_geometry = False
        self.desc = ""
        self.notes: List[str] = []


def macro_plan(table: Any, opts: Optional[DbOptions] = None) -> Dict[str, Any]:
    """把 :class:`SectionTable` 摊成"渲染计划"（族/规格/参数/几何/差异/统计）。

    纯函数（不改 ``table``、不写文件）；``generate_db_macro`` 与本模块的报告都走它。
    """
    opts = opts or DbOptions()
    res = resolve_containers(opts)
    recs = list(getattr(table, "recs", []) or [])

    fams: Dict[str, _Family] = {}
    warnings: List[str] = []
    skipped: List[Dict[str, Any]] = []
    catalogue_map: Dict[str, str] = {}
    warned_pairs: set = set()

    for rec in recs:
        path = str(_attr(rec, "pdms_spec_path", "") or "").strip()
        if not path:
            skipped.append({"what": "section", "key": str(_attr(rec, "key", "")),
                            "why": "pdms_spec_path 为空（没有 PDMS 侧落点）"})
            continue
        owner, name = _split_spec(path)
        if not name:
            skipped.append({"what": "section", "key": str(_attr(rec, "key", "")),
                            "why": "规格路径不是 /OWNER/NAME 形态：%r" % path})
            continue
        family = _family_of_owner(owner)
        side = _side_of(rec, family)
        cat = res["catalogue_user"] if side == "user" else res["catalogue_stss"]
        world = res["spec_world_user"] if side == "user" else res["spec_world_lib"]
        raw_cat = str(_attr(rec, "pdms_catalogue", "") or "").strip()
        if raw_cat and raw_cat != cat:
            catalogue_map.setdefault(raw_cat, cat)
        specname = str(_extra(rec).get("pdms_specification", "") or "").strip() \
            or ("/PKPM_SECTION_USER" if side == "user" else "/PKPM2PDMS_SPEC")
        sprfile = str(_extra(rec).get("pdms_sprfile", "") or "").strip() or ("/" + name)
        sprfile = "/" + sprfile.lstrip("/")

        f = fams.get(family)
        if f is None:
            f = _Family(family)
            fams[family] = f
            f.catalogue, f.world, f.specname = cat, world, specname
            f.desc = (str(_extra(rec).get("family_desc_en", "") or "").strip()
                      or str(_attr(rec, "family_name_cn", "") or "").split("|")[-1].strip()
                      or family.rsplit("/", 1)[-1])
            f.stsection = ((opts.stsection_of or {}).get(family)
                           or str(_extra(rec).get("pdms_stsection", "") or "").strip()
                           or _default_stsection(side, specname))
        else:
            if (f.catalogue, f.specname) != (cat, specname) and family not in warned_pairs:
                warned_pairs.add(family)
                warnings.append("族 %s 同时落在 %s 与 %s ⇒ 按前者生成"
                                % (family, _path_join(f.catalogue, f.specname),
                                   _path_join(cat, specname)))
        expected = "%s-SPEC/%s" % (family, sprfile.lstrip("/"))
        if path != expected:
            warnings.append("规格名 %s 与 §l.3.4-1 的不变量不符（期望 %s）⇒ 按原样写出"
                            % (path, expected))
        f.recs.append((path, sprfile, rec))

    # ---- 族级参数 / 文本 / 几何 / PARA
    for family in sorted(fams):
        f = fams[family]
        first = f.recs[0][2]
        given = _param_fields(first)
        base = _fam_base(family)
        tpl = TEMPLATE_FAMILIES.get(base)
        given_names = [n for n, _d, _v in given]
        use_tpl = bool(tpl) and (
            not given
            or all(_PLACEHOLDER_PARAM_RE.match(n or "") for n in given_names)
            or (len(given) == len(tpl["params"])
                and [n.upper() for n in given_names]
                == [n.upper() for n, _d, _v in tpl["params"]])
        )
        if use_tpl:
            f.parametric = True
            f.params = [(n, dk, dv, i + 1) for i, (n, dk, dv) in enumerate(tpl["params"])]
            f.texts = list(tpl["texts"])
            f.template = "%s（%s）" % (base, tpl["evidence"])
            if given_names:
                f.notes.append("表内参数名 %s 视为占位/同名 ⇒ 采用原件证据版 %s"
                               % (given_names, [n for n, _d, _v, _i in f.params]))
        else:
            f.parametric = any(_is_parametric_rec(r) for _p, _s, r in f.recs)
            f.params = []
            for i, (nm, di, dv) in enumerate(given, 1):
                dkey = "" if tpl else ""
                f.params.append((nm, _dkey_for(nm, di, i), dv, di if f.parametric else 0))
            f.texts = [n for n, _d, _v, _i in f.params]
        # 几何：只有参数个数与模板一致才用模板（DESP 下标必须对得上）
        if tpl and len(f.params) == len(tpl["params"]) and f.parametric:
            f.ptsset = list(tpl["ptsset"])
            f.gmsset = list(tpl["gmsset"])
            if not f.template:
                f.template = "%s（%s：几何）" % (base, tpl["evidence"])
        elif tpl and len(f.ptsset) == 0 and f.parametric and len(f.params) != len(tpl["params"]):
            f.ptsset = list(_NA_ONLY_PTSSET)
            f.placeholder_geometry = True
            warnings.append("族 %s：参数个数 %d ≠ 模板 %d ⇒ 不用模板几何，改用占位 PTSSET"
                            % (family, len(f.params), len(tpl["params"])))
        else:
            f.ptsset = list(_NA_ONLY_PTSSET)
            f.gmsset = []
            f.placeholder_geometry = True
        # 参数化族没有 PURP=PARA 的参数 ⇒ SPRFILE.PARA 写占位（原件 /USER_RECT 是 PARA 0）
        f.para = "0"
        n_para = sum(1 for _n, _d, _v, i in f.params if i == 0)
        if tpl and use_tpl and f.parametric and not any(i == 0 for _n, _d, _v, i in f.params):
            f.para = tpl["para"]                 # /USER_H 的 PARA 写了等于 nDESP 个默认值
        if not f.parametric:
            n_para = len(f.params)
        f.notes.append("params=%d PURP=PARA(DATA)=%d parametric=%s（每规格的 PARA 值取自该规格的"
                       "参数默认值，见 plan['per_spec_para']）"
                       % (len(f.params), n_para, f.parametric))

    # ---- 规格去重（契约 §12#22：PDMS 无 OVERRIDE，同一父级第 2 条同名 NEW 必失败）----
    # 参数化族（/USER_RECT、/USER_H、/USER_CIRCLE）的一条规格会被多条截面记录命中
    # （样本 JLCJ2 的 14 根 Kind=1 梁柱都落 /USER_RECT-SPEC/Rectangle_Profile）。
    # SPRFILE/SPCOMPONENT 是"每个 spec 一个 PDMS 对象"：同一 path 只建一次，PARA 取第一条，
    # 并把共用事实写进 warnings（不许静默）。
    for family in sorted(fams):
        f = fams[family]
        seen: Dict[Tuple[str, str], Tuple[str, str, Any]] = {}
        para_conflicts: List[str] = []
        for path, sprfile, rec in f.recs:
            k = (path, sprfile)
            if k in seen:
                f.dup_specs += 1
                first = seen[k]
                if _para_of(f, rec) != _para_of(f, first[2]):
                    para_conflicts.append("%s: PARA %r ≠ %r（取第一条）"
                                          % (str(_attr(rec, "key", "") or path),
                                             _para_of(f, rec), _para_of(f, first[2])))
                continue
            seen[k] = (path, sprfile, rec)
        f.specs = [seen[k] for k in sorted(seen)]
        if f.dup_specs:
            shared = sorted({p for p, _s, _r in f.specs if sum(1 for p2, _s2, _r2 in f.recs
                                                               if p2 == p) > 1})
            warnings.append(
                "族 %s 有 %d 条记录共用同一规格路径（PDMS 同父级重名会失败，契约 §12#22）⇒ "
                "SPRFILE/SPCOMPONENT 只建一次：%s%s"
                % (family, f.dup_specs, shared[:4], "…" if len(shared) > 4 else ""))
            if para_conflicts:
                warnings.append("族 %s 共用规格的 PARA 默认值不一致，取第一条：%s"
                                % (family, para_conflicts[:4]))

    order = sorted(fams.values(), key=lambda x: (x.catalogue, x.name))
    pline_of = {f.name: sum(1 for ln in f.ptsset
                            if ln.strip().upper().startswith("NEW PLINE")) for f in order}
    stats = {
        "catalogue": sorted({f.catalogue for f in order}),
        "spec_world": sorted({f.world for f in order}),
        "stsection": len({(f.catalogue, f.stsection) for f in order}),
        "stcategory": len(order),
        "sprfile": sum(len(f.specs) for f in order),
        "spcomponent": sum(len(f.specs) for f in order),
        "text": sum(len(f.texts) for f in order),
        "dtset": len(order),
        "data": sum(len(f.params) for f in order),
        "ptsset": len(order),
        "pline": sum(pline_of.values()),
        "gmsset": sum(1 for f in order if f.gmsset),
        "profile": sum(1 for f in order if f.gmsset),
        "specification": len({(f.catalogue, f.specname) for f in order}),
        "selec": len(order),
        "pass2": {
            "PSTR": sum(len(f.specs) for f in order), "DTRE": sum(len(f.specs) for f in order),
            "NARE": len(order),
            "GSTR": sum(1 for f in order if f.gmsset),
            "CATR": sum(len(f.specs) for f in order),
        },
    }
    return {
        "families": order,
        "pline_of": pline_of,
        "stats": stats,
        "warnings": warnings,
        "skipped": skipped,
        "containers": res,
        "catalogue_map": catalogue_map,
        "assumptions": [
            "头注释为纯 ASCII（契约 §l.1-5 与 §l.3.1 的中文示例冲突，取硬约束一侧）",
            "STSECTION：用户侧用原件名 /USER_SECTION；型钢侧按每个 SPECIFICATION 一个 "
            "/STSS_<SPEC 基名>，可用 DbOptions.stsection_of 指定（契约 §l.3.2 要求 11 个，"
            "但转化表没有族到 STSECTION 的字段）",
            "除 /USER_RECT、/USER_CIRCLE、/USER_H 三族外，其余族的 PTSSET 只写参考点 PLINE、"
            "不写 GMSSET（转化表无几何信息；禁止臆造轮廓）",
            "SPRFILE/SPCOMPONENT/STCATEGORY/SPECIFICATION 保持源名；只有 4 个顶层容器带唯一名"
            "（契约 §l.4）",
            "第二遍引用全部带父级限定链（of STCATEGORY/STSECTION/CATALOGUE、of SELEC/"
            "SPECIFICATION/SPWLD，§0.4-9）：供应商源名与用户库可能同名并存，裸名 OLD 的归属"
            "取决于 PDMS 运行时解析顺序；链深为样本同文法的外推 ⇒ §12#25 待实机确认",
            "uniquify 缺省后缀到秒（_YYYYMMDD_HHMMSS，§0.4-9）：同日重跑不撞名；--clean 只清"
            "成员（DELETE … MEM 未直证，§12#16）且重建容器带新的运行戳、绝不复用刚清场的名字",
            "宏不写 INPUT BEGIN/END/FINISH（契约 §l.3.1；DbOptions.input_wrap=True 可写）",
        ],
    }


def _para_numb(f: _Family, i: int) -> int:
    """族内第 ``i`` 个参数在 ``PURP=PARA`` 组里的 ``NUMB``（PARA 与 DESP 各有自己的编号）。"""
    n = 0
    for j, (_n, _d, _v, desp) in enumerate(f.params, 1):
        if desp == 0:
            n += 1
        if j == i:
            return n
    return n


def _dkey_for(name: str, desp_index: int, i: int) -> str:
    """DKEY：单字母参数名用其本身（原件 /USER_RECT 是 ``DKEY B``/``DKEY H``），否则 APAR…。"""
    n = (name or "").strip()
    if re.match(r"^[A-Za-z]$", n):
        return n.upper()
    if re.match(r"^[A-Za-z]\d*$", n) and len(n) <= 2:
        return n[:1].upper()
    return ("%sPAR" % chr(ord("A") + i - 1)) if i <= 26 else ("PAR%d" % i)


def _default_stsection(side: str, specname: str) -> str:
    if side == "user":
        return "/USER_SECTION"
    base = (specname or "").rsplit("/", 1)[-1]
    if base.upper().startswith("SECTION_"):
        base = base[len("SECTION_"):]
    if not base or base.startswith("PKPM"):
        return "/STSS_ALL"
    return "/STSS_" + base


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------

_IND = "  "


def _render_text(opts: DbOptions, plan: Dict[str, Any]) -> str:
    res = plan["containers"]
    fams: List[_Family] = plan["families"]
    pline_of: Dict[str, int] = plan["pline_of"]
    date_text = opts.date_text or time.strftime("%d %b %Y %H:%M")
    note = opts.source_note or "SectionTable"
    lines: List[str] = []
    A = lines.append
    A("$S-  -- Synonym translation OFF")
    A("-- " + "-" * 70)
    A("-- PKPM2PDMS dbmacro: %s  %s" % (note, date_text))
    A("-- CONTRACT v2  engine/dbmacro.py")
    A("-- containers: %s | %s | %s | %s"
      % (res["catalogue_user"], res["catalogue_stss"],
         res["spec_world_user"], res["spec_world_lib"]))
    A("")
    if opts.input_wrap:
        A("INPUT BEGIN")
        A("")
    clean_targets: List[str] = []
    # ONERROR 必须先于清场段（§0.4-9）：空库首跑时 OLD <本包容器> 会失败，
    # 未 armed 的 ONERROR 会让宏直接中止。清场目标 = 旧运行的同名容器（显式 suffix 或当日
    # 日期戳）；DELETE … MEM 的语义未直证（§12#16）⇒ 重建容器一律带运行戳、绝不复用刚清的名字。
    A("ONERROR GOLABEL %s" % opts.onerror_label)
    A("")
    if opts.clean_first:
        A("-- clean (optional): only this package's own containers.")
        A("-- [UNVERIFIED] DELETE CATE MEM / DELETE SPWL MEM has no official proof "
          "(contract 12#16); rebuilt containers get a fresh run stamp so this never "
          "collides with the purged names.")
        csfx = opts.resolved.get("clean_suffix") or ""
        for kind, key in (("CATALOGUE", "catalogue_user"), ("CATALOGUE", "catalogue_stss"),
                          ("SPWLD", "spec_world_user"), ("SPWLD", "spec_world_lib")):
            base = (opts.catalogue_user if key == "catalogue_user"
                    else opts.catalogue_stss if key == "catalogue_stss"
                    else opts.spec_world_user if key == "spec_world_user"
                    else opts.spec_world_lib)
            target = base + csfx
            A("OLD %s %s" % (kind, target))
            A("DELETE %s MEM" % ("CATE" if kind == "CATALOGUE" else "SPWL"))
            A("")
            clean_targets.append(target)
    by_cat: Dict[str, List[_Family]] = {}
    for f in fams:
        by_cat.setdefault(f.catalogue, []).append(f)
    for cat in sorted(by_cat):
        mine = by_cat[cat]
        world = mine[0].world
        A("NEW CATALOGUE %s" % cat)
        A("PURP STL")
        A("")
        stsecs: Dict[str, List[_Family]] = {}
        for f in mine:
            stsecs.setdefault(f.stsection, []).append(f)
        for sts in sorted(stsecs):
            A("%sNEW STSECTION %s" % (_IND, sts))
            A("%sPURP STL" % _IND)
            A("")
            for f in sorted(stsecs[sts], key=lambda x: x.name):
                lines.extend(_render_family(f))
                A("")
            A("%sEND" % _IND)
            A("")
        A("END")
        A("")
        A("NEW SPWLD %s" % world)
        A("DESC 'Structural Steel'")
        A("PURP STL")
        A("")
        specs: Dict[str, List[_Family]] = {}
        for f in mine:
            specs.setdefault(f.specname, []).append(f)
        for sp in sorted(specs):
            A("%sNEW SPECIFICATION %s" % (_IND, sp))
            A("%sDESC '%s'" % (_IND, "PKPM_User_Section"
                               if cat == res["catalogue_user"] else "PKPM_Section"))
            A("%sLNTP unset" % _IND)
            A("%sQUES GTYP" % _IND)
            A("%sPURP STL" % _IND)
            A("")
            for f in sorted(specs[sp], key=lambda x: x.name):
                A("%s%sNEW SELEC" % (_IND, _IND))
                A("%s%sDESC '%s'" % (_IND, _IND, f.desc.replace("'", "")))
                A("%s%sTANS 'BEAM'" % (_IND, _IND))
                A("")
                for path, _spr, _rec in f.specs:      # 去重后的规格（§12#22）
                    A("%s%s%sNEW SPCOMPONENT %s" % (_IND, _IND, _IND, path))
                    A("%s%s%sEND" % (_IND, _IND, _IND))
                A("%s%sEND" % (_IND, _IND))
                A("")
            A("%sEND" % _IND)
            A("")
        A("END")
        A("")
    # ---- pass 2（契约 §l.3.4 / §0.4-9：全部引用带**父级限定链**）
    # 供应商源名（STCATEGORY/SPRFILE/SPCOMPONENT）按 §l.4 保留 ⇒ 目标库若已装供应商 PKPM 库，
    # 同类型同名元素会在不同父下合法并存，裸名 OLD 的归属取决于 PDMS 运行时解析顺序（无法静态
    # 验证）——一旦解析到用户元素，PSTR/GSTR/DTRE/CATR 会改写**用户**目录元素。因此第二遍的
    # 每个引用都从本包**唯一**顶层容器向下限定（of 链；语法证据：用户原件 L46778
    # `OLD PTSSET 1 of STCATEGORY /USER_XI`、L46779 两级链 `NARE PLINE 9 of PTSSET 1 of
    # STCATEGORY /USER_XI`、PMLLIB isometricadp\data\*.dat 的 `OLD RRULE 1 of RRST /…`；
    # 链深（STSECTION/CATALOGUE/SPECIFICATION/SELEC 段）为同一文法的外推 ⇒ §12#25 待实机确认）。
    A("-- pass 2: cross references (OLD has no END, contract 1.3.3; refs are parent-qualified)")
    A("")
    # SELEC 序号：与 pass 1 的 SELEC 生成顺序一致（同一 SPECIFICATION 下按族名排序）
    selec_no: Dict[str, int] = {}
    world_of: Dict[str, str] = {}
    for cat in sorted(by_cat):
        wname = by_cat[cat][0].world
        by_spec: Dict[str, List[_Family]] = {}
        for f in by_cat[cat]:
            by_spec.setdefault(f.specname, []).append(f)
            world_of[f.name] = wname
        for sp in sorted(by_spec):
            for i, f in enumerate(sorted(by_spec[sp], key=lambda x: x.name), 1):
                selec_no[f.name] = i
    for f in fams:

        fam_chain = (" of STCATEGORY %s of STSECTION %s of CATALOGUE %s"
                     % (f.name, f.stsection, f.catalogue))
        A("OLD PTSSET 1%s" % fam_chain)
        A("NARE PLINE %d of PTSSET 1 of STCATEGORY %s%s"
          % (pline_of[f.name], f.name, fam_chain))
        A("")
    for f in fams:
        fam_chain = (" of STCATEGORY %s of STSECTION %s of CATALOGUE %s"
                     % (f.name, f.stsection, f.catalogue))
        for _path, sprfile, _rec in f.specs:          # 去重后的规格（§12#22）
            A("OLD SPRFILE %s%s" % (sprfile, fam_chain))
            A("PSTR PTSSET 1 of STCATEGORY %s%s" % (f.name, fam_chain))
            if f.gmsset:
                A("GSTR GMSSET 1 of STCATEGORY %s%s" % (f.name, fam_chain))
            A("DTRE DTSET 1 of STCATEGORY %s%s" % (f.name, fam_chain))
            A("")
    for f in fams:
        comp_chain = (" of SELEC %d of SPECIFICATION %s of SPWLD %s"
                      % (selec_no.get(f.name, 1), f.specname, world_of.get(f.name, "")))
        for path, sprfile, _rec in f.specs:           # 去重后的规格（§12#22）
            A("OLD SPCOMPONENT %s%s" % (path, comp_chain))
            A("CATR SPRFILE %s%s"
              % (sprfile, " of STCATEGORY %s of STSECTION %s of CATALOGUE %s"
                 % (f.name, f.stsection, f.catalogue)))
            A("")
    if opts.input_wrap:
        names = []
        for cat in sorted(by_cat):
            names.append("CATALOGUE %s" % cat)
            names.append("SPWLD %s" % by_cat[cat][0].world)
        A("INPUT END  " + " ".join(names))
        A("INPUT FINISH")
        A("")
    A("LABEL %s" % opts.onerror_label)
    A("handle ANY")
    A("$S+")
    A("RETURN ERROR")
    A("endhandle")
    A("")
    plan["clean_targets"] = clean_targets
    return "\r\n".join(ln.rstrip() for ln in "\n".join(lines).split("\n")) + "\r\n"


def _para_of(f: _Family, rec: Any) -> str:
    """本规格的 ``SPRFILE.PARA`` 值向量。

    1. 该规格里 ``desp_index == 0``（= ``PURP=PARA``）的参数默认值，按参数顺序；
    2. 没有值可给时：族是 PARA 族 ⇒ 按该族的 PARA 参数个数补 ``0``（保持
       ``len(PARA) == count(PURP=PARA)`` 的不变量 §l.3.4-5）；族是纯 DESP 族 ⇒
       用族的占位值（原件 ``PARA 0``；``/USER_H`` 见 ``TEMPLATE_FAMILIES``）。
    """
    vals = [str(d) if str(d) != "" else "0" for _n, _d, d, i in _param_fields4(rec) if i == 0]
    if vals:
        return " ".join(vals)
    n_para = sum(1 for _n, _d, _v, i in f.params if i == 0)
    if n_para:
        return " ".join(["0"] * n_para)
    return f.para or "0"


def _param_fields4(rec: Any) -> List[Tuple[str, str, str, int]]:
    """``rec.params`` → ``[(name, dkey, default, desp_index), …]``（desp_index 用 rec 给的）。"""
    out: List[Tuple[str, str, str, int]] = []
    for p in (_attr(rec, "params", []) or []):
        if isinstance(p, dict):
            nm, dv, di = p.get("name", ""), p.get("default", ""), p.get("desp_index", 0)
        else:
            nm = getattr(p, "name", "")
            dv = getattr(p, "default", "")
            di = getattr(p, "desp_index", 0)
        try:
            di = int(di or 0)
        except (TypeError, ValueError):
            di = 0
        out.append((str(nm or "").strip(), "", str(dv if dv is not None else "").strip(), di))
    return out


def _render_family(f: _Family) -> List[str]:
    out: List[str] = []
    A = out.append
    A("%sNEW STCATEGORY %s" % (_IND * 2, f.name))
    A("%sPURP STL" % (_IND * 2))
    A("")
    short = f.name.rsplit("/", 1)[-1]
    for i, text_name in enumerate(f.texts, 1):
        A("%s%sNEW TEXT /%s-PA%d" % (_IND * 2, _IND, short, i))
        A("%s%sPURP PARA" % (_IND * 2, _IND))
        A("%s%sSTEX '%s'" % (_IND * 2, _IND, text_name.replace("'", "")))
        A("%s%sEND" % (_IND * 2, _IND))
    A("")
    A("%s%sNEW DTSET" % (_IND * 2, _IND))
    para_no = 0                                 # PARA 组内序号（与 NUMB 同一编号空间，§0.4-9）
    for i, (name, dkey, dpro, desp) in enumerate(f.params, 1):
        purpos = "DESP" if desp > 0 else "PARA"
        if purpos == "DESP":
            pp = "ATTRIB DESP[%d ]" % desp
        else:
            para_no += 1
            # PPRO 的 PARA[n] 必须用 **PARA 组内序号**（与该行的 NUMB 一致，原件
            # PKPM（PDMS数据库）.txt:3159-3204 是 PARA[1..4]+NUMB 1..4 之后才轮到 DESP[1]）；
            # 旧实现用全族位置 i，DESP 排在 PARA 前面时（混合族）会取错槽（R3 复核发现③）。
            pp = "ATTRIB PARA[%d ]" % para_no
        # PURP=PARA 的 DATA 的 DPRO 原件一律写 0（值由 SPRFILE.PARA 提供，见原件
        # /DOUBLE_THIN_C_COIL_TUBE L3159-3194）；PURP=DESP 才写真实默认值。
        dpro_txt = (dpro if dpro != "" else "0") if desp > 0 else "0"
        A("%s%s%sNEW DATA" % (_IND * 2, _IND, _IND))
        A("%s%s%sDKEY %s" % (_IND * 2, _IND, _IND, dkey))
        if purpos == "DESP":
            A("%s%s%sPTYP DIST" % (_IND * 2, _IND, _IND))
        A("%s%s%sPPRO ( %s )" % (_IND * 2, _IND, _IND, pp))
        A("%s%s%sDPRO ( %s )" % (_IND * 2, _IND, _IND, dpro_txt))
        A("%s%s%sPURP %s" % (_IND * 2, _IND, _IND, purpos))
        A("%s%s%sNUMB %d" % (_IND * 2, _IND, _IND,
                             desp if desp > 0 else para_no))
        A("%s%s%sDTIT '%s'" % (_IND * 2, _IND, _IND, name.replace("'", "")))
        A("%s%s%sEND" % (_IND * 2, _IND, _IND))
    A("%s%sEND" % (_IND * 2, _IND))
    A("")
    A("%s%sNEW PTSSET" % (_IND * 2, _IND))
    body = _IND * 4
    for ln in f.ptsset:
        s = ln.strip()
        if s.upper().startswith("NEW "):
            A(body + ln)
        elif s == "END":
            A(body + "END")
        else:
            A(body + _IND + ln)
    A("%s%sEND" % (_IND * 2, _IND))
    A("")
    if f.gmsset:
        A("%s%sNEW GMSSET" % (_IND * 2, _IND))
        for ln in f.gmsset:
            s = ln.strip()
            if s.upper().startswith("NEW "):
                A(body + ln)
            elif s == "END":
                A(body + "END")
            else:
                A(body + _IND + ln)
        A("%s%sEND" % (_IND * 2, _IND))
        A("")
    for _path, sprfile, rec in f.specs:          # 去重后的规格（§12#22：同 path 只建一次）
        A("%s%sNEW SPRFILE %s" % (_IND * 2, _IND, sprfile))
        A("%s%sGTYP BEAM" % (_IND * 2, _IND))
        for ln in _wrap_para(_para_of(f, rec)):
            A("%s%s%s" % (_IND * 2, _IND, ln))
        A("%s%sEND" % (_IND * 2, _IND))
    A("%sEND" % (_IND * 2))
    return out


def _wrap_para(para: str, per_line: int = 5) -> List[str]:
    """``PARA <v…>`` 折行：每行 5 个值、续行用 ``$``（原件写法，recon §6.3）。"""
    toks = [t for t in (para or "").split() if t != ""] or ["0"]
    lines: List[str] = []
    first = True
    for i in range(0, len(toks), per_line):
        chunk = toks[i:i + per_line]
        head = ("PARA " if first else "") + " ".join(chunk)
        first = False
        if i + per_line < len(toks):
            head += " $"
        lines.append(head)
    return lines


# ---------------------------------------------------------------------------
# 对外 API（契约 §(l)/§l.4）
# ---------------------------------------------------------------------------

def generate_db_macro(table: Any, opts: Optional[DbOptions] = None) -> str:
    """渲染目录+规格宏（契约：``generate_db_macro(table, opts) -> str``）。

    * ``opts`` 省略 ⇒ 契约 §l.2 的全部缺省；
    * 生成前跑安全闸（§l.1）：禁用容器名命中 ⇒ :class:`DbMacroError`；
    * 产物纯 ASCII、CRLF、行尾无空白；
    * ``opts.report`` 传入 dict 时被填充（``stats`` / ``warnings`` / ``skipped`` /
      ``safety`` / ``assumptions`` / ``families``），供 CLI 直接并入 ``report.json``。
    """
    opts = opts or DbOptions()
    plan = macro_plan(table, opts)
    text = _render_text(opts, plan)
    hits = scan_forbidden_names(text)
    if hits:
        raise DbMacroError("生成物出现用户既有容器名（契约 §l.1-2）：" + "；".join(hits[:5]))
    bases = (opts.catalogue_user, opts.catalogue_stss,
             opts.spec_world_user, opts.spec_world_lib)
    for target in plan.get("clean_targets", []):
        if not any(target == b or target.startswith(b + "_") for b in bases):
            raise DbMacroError("清场目标不在本包容器内（契约 §l.1-3）：%s" % target)
    if not text.isascii():
        raise DbMacroError("生成物含非 ASCII 字符（契约 §l.1-5）")
    safety = safety_report(text, opts, plan.get("clean_targets", []))
    plan["safety"] = safety
    if opts.report is not None:
        opts.report.clear()
        opts.report.update({
            "stats": plan["stats"], "warnings": plan["warnings"],
            "skipped": plan["skipped"], "safety": safety,
            "assumptions": plan["assumptions"],
            "containers": plan["containers"],
            "catalogue_map": plan["catalogue_map"],
            "families": [{"name": f.name, "catalogue": f.catalogue,
                          "specname": f.specname, "stsection": f.stsection,
                          "specs": len(f.specs), "records": len(f.recs),
                          "dup_specs": f.dup_specs, "params": len(f.params),
                          "parametric": f.parametric, "template": f.template,
                          "placeholder_geometry": f.placeholder_geometry,
                          "notes": f.notes} for f in plan["families"]],
        })
    return text


def write_db_macro(path: str, text: str) -> str:
    """写宏文件：**ASCII 无 BOM + CRLF**（契约 §l.4），写完回读校验，返回 ``path``。"""
    if not text.isascii():
        raise DbMacroError("宏含非 ASCII 字符，拒绝写出（契约 §l.1-5）")
    body = "\r\n".join(ln.rstrip() for ln in
                       text.replace("\r\n", "\n").replace("\r", "\n").split("\n"))
    if not body.endswith("\r\n"):
        body += "\r\n"
    data = body.encode("ascii")                     # 先编码再写（契约 §g-3）
    with open(path, "wb") as fh:
        fh.write(data)
    raw = open(path, "rb").read()
    if raw != data:
        raise DbMacroError("回读校验失败（字节不一致）：%s" % path)
    if b"\n" in raw.replace(b"\r\n", b""):
        raise DbMacroError("回读校验失败（存在单 \\n）：%s" % path)
    if raw.startswith(b"\xef\xbb\xbf"):
        raise DbMacroError("回读校验失败（出现 BOM）：%s" % path)
    return path
