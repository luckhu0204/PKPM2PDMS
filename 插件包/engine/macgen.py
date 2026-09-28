# -*- coding: utf-8 -*-
"""PKPM2PDMS导入导出 —— 规范模型 → PDMS 宏生成器（``engine/macgen.py``）。

契约：``spec/CONTRACT.md`` §(b).6（``MacOptions``）、§(d)（层级/命名/允许的语法）、
§(f).1（基点与转角公式）、§(g)（GBK 无 BOM + CRLF）。

对外入口（契约冻结的三个）
--------------------------
* :class:`MacOptions`      —— 生成参数（字段与 §b.6 表**逐一对应**，无增减）
* :func:`generate_macro`   —— ``generate_macro(model: Model, opts: MacOptions) -> str``
* :func:`write_macro`      —— ``write_macro(path: str, text: str) -> str``（写 GBK+CRLF 并回读校验）

除上述三个之外，本模块提供 :func:`build_plan`（返回 :class:`MacroPlan`），它**不新增任何契约
字段或语法**，只是把"字符串 + 统计 + 未解析清单 + 报告用截面明细"一次算好，供 ``cli.py``
填 ``report.counts``/``report.sections``/``report.warnings`` 时直接取用：
``generate_macro(model, opts)`` 与 ``build_plan(model, opts).text()`` 结果**逐字节相同**。

本模块**不 import secmap**：契约 §e 规定截面解析的唯一裁决者是 ``opts.secmap.resolve()``，
本模块只把它当鸭子类型的解析器调用（因此两者可以独立开发、独立测试）。

命名方案〔R7，2026-09-28 用户确认，不得偏离〕
--------------------------------------------
================  =============================================================
层级               名字
================  =============================================================
SITE              **外部传入**：``opts.site_name``（.NET 侧执行前用 DbElement
                  直查逐个试名——``/PKPM2PDMS``、``/PKPM2PDMSre``…——试出第一个可用
                  的，经 ``--request`` 的 ``site_name`` 键给引擎）。引擎**不生成、
                  不改名、不做 re 逻辑**；缺失即报错（不自行默认）。
ZONE              ``/<SITE名>_<工程名>``
STRU              ``/<SITE名>_MF``
FRMW              ``/<SITE名>_EL<n>``（每层一个）、``/<SITE名>_FW``（板墙）、
                  ``/<SITE名>_GR``（轴网）
SBFR              ``/<SITE名>_EL<n>_COLUMN|BEAM|HBRACE|VBRACE``（层 FRMW 下）、
                  ``/<SITE名>_EL<n>_SLAB|WALL``（``_FW`` 下）
SCTN/PANE/STWALL  **unnamed**：``NEW SCTN`` 不带名字，PDMS 自动分配系统名；
                  其后的属性行（SPREF/DESP/POSS/POSE/JUSL/MEML/BANG/ORI/PLOOP/
                  HEIGHT/PAVERT…）都作用在当前元素（CE）上，不需要名字引用。
================  =============================================================

这里 ``<SITE名>`` = ``opts.site_name`` 去掉前导 ``/`` 的那一段（如 ``PKPM2PDMS``）。
中间层含层号 ⇒ **全宏唯一**；生成器维护"已用名字集合"，每个带名 ``NEW`` 写入前查重，
重复即抛 :class:`MacroNameError`（生成失败，绝不带病出宏）；宏落盘前再做一遍全量自查
（:func:`_audit_macro` 重新解析全部 ``NEW <TYPE> /名字``）。

运行期函数依赖：**零**。宏内不出现任何 ``!!pkpm2pdms*`` 调用、不 ``$M`` 预载任何
``.pmlfnc``；``pdms/pkpm2pdmsuniquename*.pmlfnc`` 系列自 R7 起不再部署、不再被引用
（旧文件保留在工作树，只是不进部署清单）。

PDMS 语法出处（本文件只使用下列形式，均为本机安装内的既有代码，逐条可复核）
--------------------------------------------------------------------------
============================  ==========================================================
宏里发出的命令                 出处（本机 ``D:\\AVEVA\\Plant\\PDMS12.1.SP4\\PMLLIB\\``）
============================  ==========================================================
``NEW SITE/ZONE/STRU/FRMW``    ``Building_Design\\pmllib\\concrete_design\\ANCHOR\\nucdesoanchier.pmlobj:91,96,101,106``
``NEW FRMW /X``（含 ``/`` 名）  ``mypml\\forms\\GRIDDESIGN.pmlfrm:969-975``（``!!CE.NAME = name OF OWNER + '/ALLX' + …``）
``NEW SBFR``                   ``mypml\\forms\\GRIDDESIGN.pmlfrm:974``
裸类型名回退 ``SBFR/FRMW``       ``design\\functions\\aslspecinit.pmlfnc:79,81``；``design\\forms\\aslhandrail.pmlfrm:158``
裸类型名回退 ``STRU``            ``mypml\\forms\\StlGrating.pmlfrm:105``；``mypml\\forms\\GRIDDESIGN.pmlfrm:1458``
无名 ``NEW SCTN``（配 SPREF）    ``design\\functions\\createasl.pmlfnc:58``；``design\\forms\\strsectionedit.pmlfrm:530-535``；
                              ``Building_Design\\…\\GCCATA\\nuccatosctnflite.pmlobj:92``〔R7 实测 PMLLIB 内 2694 处〕
``NEW PANE``/``ORI Y IS N AND Z IS U``/``NEW PLOOP``/``HEIGHT <t> SJUS dbot``/``NEW PAVERT``/``POS``
                              ``mypml\\forms\\StlGrating.pmlfrm:42-56``；``sctlcrelem.pmlfnc:229-256``
                              〔R7：无名 ``NEW PANE`` 在 PMLLIB 内 22 处，如 ``accommodation\\objects\\accceilingbasics.pmlobj:228``〕
无名 ``NEW STWALL`` + ``SPRE``   ``Building_Design\\…\\TRADUCTEUR\\nucdesogwall.pmlobj:180-188``〔PMLLIB 内 1 处〕
``DESP``                       ``mypml\\forms\\StlGrating.pmlfrm:94``；``sctlcrelem.pmlfnc:180``
``POSS E .. N .. U ..``/``POSE``  ``mypml\\forms\\StlGrating.pmlfrm:96-97``
``JUSL``/``MEML``              ``sctlcrelem.pmlfnc:338-340``；``MYTOOLS\\…\\sdnfinver3.pmlfnc:187-188``
``BANG``                       ``MYTOOLS\\test\\Tekla2PDMS\\sdnf\\functions\\sdnfinver3.pmlfnc:192``
``NEW PAVERT``/``NEW PLOOP``/``POS``  ``mypml\\forms\\StlGrating.pmlfrm:45-56``
``ONERROR CONTINUE``           ``aba\\Forms\\abaprocess.pmlfrm:1455``；``aba\\Objects\\abadrawing.pmlobj:288``
                              〔R7 实测 PMLLIB 内 251 处；与 ``ONERROR GOLABEL`` 同族（533 处带 ``ONERROR``）〕
``--`` 行注释 / ``$S-`` ``$S+``   ``mypml\\forms\\scale-STRU.mac``；用户原件 ``PKPM（PDMS数据库）.txt`` 首/末行
宏头/宏尾标准结构〔R6/R7〕        ``-- `+64 个 ``-`` 的分隔线、``-- <用途>  Date: …``、
                              ``-- End <用途>  Date: …``、``$S+  -- Synonym translation ON``
                              用户原件 ``G:\\…\\P-TRANS\\pkpm_section_DBOutput.txt`` L1-3 / L70303-70305
                              （逐行同形，见 :data:`SEP_LINE`/:data:`MACRO_PURPOSE`）
============================  ==========================================================

〔R7〕宏结构（2026-09-28 用户确认）
----------------------------------
头（5 行 + 可选 ``-- `` 说明行）::

    $S-  -- Synonym translation OFF        ← 冻结首行
    -- ----…（64 个 ``-``）                 ← 分隔线
    -- <用途>  Date: <生成时间>
    -- 元素：SITE 1 / ZONE 1 / … / STWALL n ← 计数注释一行（与宏内实际 NEW 条数逐类相等）
    ONERROR CONTINUE                        ← 出错继续；**不再有** LABEL/handle 错误块
    <元素主体>

尾::

    -- End <用途>  Date: <生成时间>
    $S+  -- Synonym translation ON
    -- ----…（64 个 ``-``）

〔R6/R7 已从宏里删除、不得回归〕函数预载（``!pkpm2pdmsFuncPath`` + ``$M <…>``）、唯一化函数
可用性检查 + 故障注入（``…UniquenameMissing()``）、逐元素唯一化模板
（``!!pkpm2pdmsType`` / ``!n = !!pkpm2pdmsUniquename(…)`` / ``var … EXIST $!n`` /
``NEW <T> $!n``）、``LABEL /PKPM2PDMSERR`` / ``handle ANY`` / ``RETURN ERROR`` 错误块。
:func:`_audit_macro` 会在返回前硬性拦截其中的运行期函数依赖形态。

契约 §d.4-2 的"未解析截面"处置：仍建构件几何，省略 ``SPREF``/``SPRE`` 行，并在其上方写
``-- UNRESOLVED SECTION <id> <name> <reason>``；对应条目回流到 :attr:`MacroPlan.unresolved`。
"""

from __future__ import annotations

import math
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:  # 以 engine/ 为 sys.path 直接运行（cli.py、test 的用法）
    from canonical import (CONTRACT_VERSION, INFERRED, PANE_ORI, PANE_SJUS, PARAMETRIC,
                           RESOLVED, RESOLUTION_STATUS, TOL, UNRESOLVED, Level,
                           Member, Model, Resolution, Section, Slab, Wall)
except ImportError:  # 作为包导入（import engine.macgen）
    from .canonical import (CONTRACT_VERSION, INFERRED, PANE_ORI, PANE_SJUS, PARAMETRIC,
                            RESOLVED, RESOLUTION_STATUS, TOL, UNRESOLVED, Level,
                            Member, Model, Resolution, Section, Slab, Wall)

__all__ = ["MacOptions", "MacroPlan", "MacroNameError", "build_plan", "generate_macro",
           "write_macro", "UNIT_FACTOR", "MEMBER_GROUPS", "ELEM_TYPES"]

# --------------------------------------------------------------------------
# 契约常量（值全部取自 CONTRACT §d，不得在此处另立新值）
# --------------------------------------------------------------------------

#: 长度单位 → mm 系数（契约 §d.4-1：mm=×1、cm=÷10、m=÷1000）
UNIT_FACTOR = {"mm": 1.0, "cm": 10.0, "m": 1000.0}
UNITS = ("mm", "cm", "m")

#: 〔R7〕中间层名字的段（`<SITE名>_<段>`；SITE 名由 ``opts.site_name`` 传入）
SEG_MF = "MF"                            # STRU：主框架
SEG_FW = "FW"                            # FRMW：板墙
SEG_GR = "GR"                            # FRMW：轴网
SEG_EL = "EL"                            # FRMW/SBFR：层号段（EL1、EL2…）
SEG_COLUMN = "COLUMN"                    # SBFR 类别段
SEG_BEAM = "BEAM"
SEG_HBRACE = "HBRACE"
SEG_VBRACE = "VBRACE"
SEG_SLAB = "SLAB"
SEG_WALL = "WALL"

#: PANE 的 ORI 命令原文（§d.3/d.4；等价于 canonical.PANE_ORI == 'YNZU'）
PANE_ORI_CMD = "ORI Y IS N AND Z IS U"

#: 〔R6/R7〕宏头/宏尾的分隔线：`-- ` + 64 个 `-`（逐字对齐用户原件 DB Output 宏
#: `G:\…\P-TRANS\pkpm_section_DBOutput.txt` 第 2 行/倒数第 2 行，实测 67 字符）。
SEP_LINE = "-- " + "-" * 64

#: 〔R6/R7〕宏头/宏尾的"用途说明"（DB Output 宏里是 `Data Listing` 的位置；头尾必须同一串）
MACRO_PURPOSE = "PKPM2PDMS 导入：PKPM 模型 → PDMS 建模型宏"

#: 〔R7〕宏头的错误处置：出错**继续**（PMLLIB 内 251 处先例，见模块头；）
#: 层级名在生成期已唯一、底层元素 unnamed，预期不触发；不再有 LABEL/handle 错误块。
ONERROR_LINE = "ONERROR CONTINUE"

#: 〔R7〕宏头计数注释的 8 类元素（顺序即注释里的顺序；= 生成器逐类对平的键）
ELEM_TYPES = ("SITE", "ZONE", "STRU", "FRMW", "SBFR", "SCTN", "PANE", "STWALL")

#: 构件组定义：(SBFR 类别段, 层内分桶键, 成员类型, 是否只取水平支撑)
MEMBER_GROUPS = (
    (SEG_COLUMN, "column", "column", None),
    (SEG_BEAM, "beam", "beam", None),
    (SEG_HBRACE, "hbrace", "brace", True),
    (SEG_VBRACE, "vbrace", "brace", False),
)

#: 构件类型 → SectionMap.resolve 的 kind（§e.6）
SECTION_KIND = {"beam": "beam", "column": "col", "brace": "brace"}

#: 〔R7〕宏内**禁止出现**的运行期函数依赖形态（:func:`_audit_macro` 硬性拦截；
#: 只在非注释行上检查，避免把说明性文字误判）
FORBIDDEN_TOKENS = ("!!pkpm2pdms", "$M ", "pkpm2pdmsType", "pkpm2pdmsFatal")

#: 〔R7〕`NEW <TYPE> /名字` 的全量自查正则（带名新建行）
NAMED_NEW_RE = re.compile(r"^\s*NEW\s+(\w+)\s+(/\S+)\s*$")

# 缩进（纯排版；PDMS 宏忽略行首空白，见 §6.2 的 Tab 缩进实例）
_I2, _I4, _I6, _I8 = "  ", "    ", "      ", "        "


class MacroNameError(ValueError):
    """宏内名字冲突/非法（生成失败，绝不带病出宏）。``ValueError`` 子类 ⇒ ``cli`` 码 2。"""


def _num(v: float) -> str:
    """数值 → PDMS 可读的十进制字符串（不用科学计数法，去掉多余的 0）。"""
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("数值 %r 无法转成 float（宏内数值必须是十进制）" % (v,))
    if not math.isfinite(x):
        raise ValueError("数值 %r 非有限值（禁止 NaN/Inf）" % (v,))
    if abs(x) < 5e-7:          # -0.0 / 浮点残渣一律归零
        x = 0.0
    s = "%.6f" % x
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def _one_line(text: str) -> str:
    """把多行/含控制字符的文本压成单行，供 ``--`` 注释使用。"""
    s = str(text).replace("\r", " ").replace("\n", " ")
    return "".join(ch if ch >= " " else " " for ch in s).strip()


def _clean_name(value: str, what: str) -> str:
    """清洗 PDMS 名称：去首尾空白、去掉前导 ``/``（调用方再补）。

    只拒绝会破坏宏分词规则的字符（空白、控制字符）；``/`` 在名称**内部**是合法的
    （§d.2 的证据：``GRIDDESIGN.pmlfrm:975`` 给 SBFR 起含 ``/`` 的名字），但 SITE 名
    是单段顶层名 ⇒ :func:`_clean_site` 额外拒绝内部 ``/``。
    """
    s = str(value or "").strip()
    while s.startswith("/"):
        s = s[1:]
    if not s:
        raise ValueError("%s 为空：PDMS 名称不能为空（契约 §d.1）" % (what,))
    bad = [ch for ch in s if ch.isspace() or ch < " "]
    if bad:
        raise ValueError("%s=%r 含空白/控制字符 %r：PDMS 名称不得含空白（契约 §d.1）"
                         % (what, value, bad[0]))
    if "~" in s:
        raise ValueError("%s=%r 含 '~'：'~' 是导出文本的可选尾部分隔符（契约 §c.1）"
                         % (what, value))
    return s


def _clean_site(site_name: str) -> str:
    """SITE 名（``opts.site_name``）→ 去前导 ``/`` 的名字段（如 ``/PKPM2PDMS`` → ``PKPM2PDMS``）。

    〔R7〕引擎**不生成也不改名**：这个名字是 .NET 侧执行前用 DbElement 直查逐个试出来的
    （``/PKPM2PDMS``、``/PKPM2PDMSre``…），经 ``--request`` 的 ``site_name`` 键传入。
    """
    if not isinstance(site_name, str):
        raise ValueError("MacOptions.site_name 必须是 str，收到 %r（§b.6/R7）"
                         % (type(site_name).__name__,))
    tok = _clean_name(site_name, "MacOptions.site_name")
    if "/" in tok:
        raise ValueError("MacOptions.site_name=%r 含内部 '/': SITE 名是单段顶层名"
                         "（如 /PKPM2PDMS），不能是多段路径（§d.1/R7）" % (site_name,))
    return tok


class _Xform:
    """坐标变换：基点平移 + 整模转角（契约 §f.1）。

    ``θ = angle_deg``（度，从 +U 俯视逆时针）::

        E = base_e + (x·cosθ − y·sinθ)
        N = base_n + (x·sinθ + y·cosθ)
        U = base_u + z

    ``base_*`` 以 ``unit`` 为单位传入，先换算成 mm 参与计算，输出前再缩放回 ``unit``。
    """

    def __init__(self, opts: "MacOptions") -> None:
        self.unit = opts.unit
        self.f = UNIT_FACTOR[opts.unit]          # unit -> mm
        th = math.radians(float(opts.angle_deg))
        c, s = math.cos(th), math.sin(th)
        # 0/90/180/270 度这些常用角度的浮点残渣归零（6e-17 之类）
        if abs(c) < 1e-12:
            c = 0.0
        if abs(s) < 1e-12:
            s = 0.0
        self.cos, self.sin = c, s
        self.de = float(opts.base_e) * self.f
        self.dn = float(opts.base_n) * self.f
        self.du = float(opts.base_u) * self.f

    def pt(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
        """模型坐标 (x,y,z) [mm] → 输出坐标 (E,N,U) [unit]。"""
        e = (self.de + x * self.cos - y * self.sin) / self.f
        n = (self.dn + x * self.sin + y * self.cos) / self.f
        u = (self.du + z) / self.f
        return (e, n, u)

    def length(self, v: float) -> float:
        """长度量 mm → unit。"""
        return float(v) / self.f

    def pos(self, keyword: str, p: Sequence[float]) -> str:
        """``POSS``/``POSE``/``POS`` 行（§d.3：``POSS E .. N .. U ..``）。"""
        e, n, u = self.pt(float(p[0]), float(p[1]), float(p[2]))
        return "%s E %s N %s U %s" % (keyword, _num(e), _num(n), _num(u))


# --------------------------------------------------------------------------
# 参数
# --------------------------------------------------------------------------


@dataclass
class MacOptions:
    """``generate_macro`` 的参数 —— 字段与契约 §b.6 的表**逐一对应**（〔R7〕见下）。

    ``secmap`` 为 ``None`` 时 :func:`generate_macro`/:func:`build_plan` 抛 ``ValueError``：
    契约 §b.6 明令禁止静默产出"无规格宏"。本模块不 import ``secmap``，只要求它
    提供 ``.resolve(section, kind) -> Resolution``（§e.6）。

    〔R7〕相对 §b.6 的 R3 版字段表，**删去** ``uniquify``/``pml_func_path``（运行期唯一化
    模板与 PML 函数预载整体作废：宏内不再有任何 ``!!pkpm2pdms*`` 调用），**新增**
    ``site_name``：SITE 名（必填；.NET 侧直查试出后经 ``--request`` 的 ``site_name`` 键传入）。
    """

    project: str = "PKPM_PROJECT"
    site_name: str = ""               # 〔R7〕必填：如 '/PKPM2PDMS'（.NET 直查试出的可用名）
    base_e: float = 0.0
    base_n: float = 0.0
    base_u: float = 0.0
    angle_deg: float = 0.0
    unit: str = "mm"
    secmap: Any = None                # SectionMap | None
    header_note: str = ""
    time_text: str = ""               # 留空 ⇒ 取当前时间

    def unit_factor(self) -> float:
        return UNIT_FACTOR[self.unit]


# --------------------------------------------------------------------------
# 截面解析（唯一裁决者是 opts.secmap）
# --------------------------------------------------------------------------


class _Resolver:
    """按 (Section, kind) 缓存 ``opts.secmap.resolve()`` 的结果（纯读取，不改 secmap）。"""

    def __init__(self, secmap: Any, warn) -> None:
        self._secmap = secmap
        self._warn = warn
        self._cache: Dict[Tuple[Any, ...], Resolution] = {}

    @staticmethod
    def _key(sec: Section, kind: str) -> Tuple[Any, ...]:
        dims = tuple(sorted((str(k), "%r" % (v,)) for k, v in (sec.dims or {}).items()))
        return (kind, sec.id, sec.table, sec.kind, sec.name, sec.shapeval, dims)

    def resolve(self, sec: Section, kind: str) -> Resolution:
        key = self._key(sec, kind)
        if key in self._cache:
            return self._cache[key]
        res: Optional[Resolution] = None
        try:
            res = self._secmap.resolve(sec, kind)
        except Exception as exc:                     # 解析器异常不得让宏生成崩溃
            self._warn("secmap.resolve(%s, %s) 抛出 %s: %s；按 unresolved 处理"
                       % (sec.id, kind, type(exc).__name__, exc))
        if not isinstance(res, Resolution):
            self._warn("secmap.resolve(%s, %s) 返回 %r，不是 canonical.Resolution；"
                       "按 unresolved 处理" % (sec.id, kind, res))
            res = Resolution(status=UNRESOLVED, pkpm_name=sec.name,
                             reason="secmap.resolve 未返回 Resolution 对象")
        elif res.status not in RESOLUTION_STATUS:
            self._warn("secmap.resolve(%s, %s) 返回非法 status=%r；按 unresolved 处理"
                       % (sec.id, kind, res.status))
            res = Resolution(spec_path=res.spec_path, desp_params=list(res.desp_params),
                             status=UNRESOLVED, pkpm_name=res.pkpm_name,
                             reason="secmap 返回非法 status=%r" % (res.status,),
                             source=res.source)
        self._cache[key] = res
        return res


# --------------------------------------------------------------------------
# 计划（宏文本 + 统计 + 报告用清单）
# --------------------------------------------------------------------------


@dataclass
class MacroPlan:
    """一次生成的完整结果。

    * :attr:`lines` / :meth:`text` —— 宏正文（CRLF 在 ``text()`` 里统一加）
    * :attr:`stats` —— 各类命令/注释的条数（便于核对"598 梁 / 200 柱 / …"）
    * :attr:`warnings` / :attr:`assumptions` —— 供 ``report.warnings`` / ``report.assumptions``
    * :attr:`sections` / :attr:`unresolved` / :attr:`inferred` —— 供
      ``report.sections.detail`` / ``.unresolved``（键名取自契约 §h 的示例，未新增字段名）
    * :attr:`used_names` —— 〔R7〕宏内**带名** ``NEW`` 用掉的全部名字（中间层，已查重）
    * :attr:`unnamed_count` —— 〔R7〕无名 ``NEW``（SCTN/PANE/STWALL）的条数
    """

    lines: List[str] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    sections: List[Dict[str, Any]] = field(default_factory=list)
    unresolved: List[Dict[str, Any]] = field(default_factory=list)
    inferred: List[Dict[str, Any]] = field(default_factory=list)
    used_names: List[str] = field(default_factory=list)      # 排序后的名字集合（已查重）
    unnamed_count: int = 0                                   # 无名 NEW 的条数

    def text(self) -> str:
        """宏全文（每条 CRLF 结尾，含末行）。"""
        return "".join(ln + "\r\n" for ln in self.lines)


class _Emitter:
    """负责行缓冲与统计：每条非注释行按第一个 token 计数。"""

    def __init__(self) -> None:
        self.lines: List[str] = []
        self.stats: Dict[str, int] = {}

    def bump(self, key: str, n: int = 1) -> None:
        self.stats[key] = self.stats.get(key, 0) + n

    def line(self, text: str = "") -> None:
        self.lines.append(text)
        s = text.strip()
        if not s:
            self.bump("空行")
        elif s.startswith("--"):
            self.bump("注释行")
        elif s.startswith("$"):
            self.bump("指令行")
        else:
            toks = s.split()
            # `NEW SCTN …` 记成 "NEW SCTN"；裸回退行（FRMW/STRU/PANE）记成自身
            key = (" ".join(toks[:2]) if toks[0].upper() == "NEW" and len(toks) > 1
                   else toks[0])
            self.bump(key)


class _Namer:
    """〔R7〕已用名字集合：每个带名 ``NEW`` 写入**之前**查重，重复即抛错。"""

    def __init__(self) -> None:
        self._seen: Dict[str, str] = {}          # 名字 → 首次由哪个类型占用
        self.used: List[str] = []

    def take(self, name: str, etype: str) -> str:
        if not name.startswith("/"):
            raise MacroNameError("带名创建的名字必须以 '/' 开头：%s %r" % (etype, name))
        if name in self._seen:
            raise MacroNameError(
                "宏内名字重复：%s 已在 %s 用过（R7 硬保证：中间层名含层号 ⇒ 全宏唯一；"
                "重复即生成失败，绝不带病出宏）" % (name, self._seen[name]))
        self._seen[name] = etype
        self.used.append(name)
        return name


def _count_creates(lines: Sequence[str]) -> Dict[str, int]:
    """逐类统计 ``NEW <TYPE>`` 条数（8 类元素；PLOOP/PAVERT 等子元素不在其列）。"""
    out = {t: 0 for t in ELEM_TYPES}
    for ln in lines:
        s = ln.strip()
        if not s.startswith("NEW "):
            continue
        toks = s.split()
        if len(toks) >= 2 and toks[1] in out:
            out[toks[1]] += 1
    return out


def _count_unnamed(lines: Sequence[str]) -> int:
    """〔R7〕无名 ``NEW``（``NEW SCTN``/``NEW PANE``/``NEW STWALL``，无第二 token）的条数。"""
    n = 0
    for ln in lines:
        s = ln.strip()
        if s in ("NEW SCTN", "NEW PANE", "NEW STWALL"):
            n += 1
    return n


def _audit_macro(lines: Sequence[str]) -> Dict[str, int]:
    """宏落盘前的**全量自查**（〔R7〕硬保证；任何一项不过即抛 :class:`MacroNameError`）。

    1. 重新解析全部 ``NEW <TYPE> /名字``（不依赖生成期的簿记）——同名即失败；
    2. 非注释行不得出现运行期函数依赖形态（``!!pkpm2pdms``/``$M ``/…）；
    3. 统计并把结果交给调用方（带名/无名条数）。
    """
    named: Dict[str, str] = {}
    n_named = 0
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if s and not s.startswith("--"):
            for bad in FORBIDDEN_TOKENS:
                if bad in s:
                    raise MacroNameError(
                        "宏第 %d 行含运行期函数依赖 %r（R7 已删除 PML 函数预载/唯一化模板）：%r"
                        % (i, bad, s))
        m = NAMED_NEW_RE.match(ln)
        if not m:
            continue
        etype, name = m.group(1), m.group(2)
        n_named += 1
        if name in named:
            raise MacroNameError(
                "宏内名字重复（落盘前全量自查）：%s 出现在 %s 与 %s 两处创建行"
                % (name, named[name], etype))
        named[name] = etype
    return {"named": n_named, "unnamed": _count_unnamed(lines),
            "names": len(named)}


def _check(model: Model, opts: MacOptions) -> None:
    if not isinstance(model, Model):
        raise ValueError("model 必须是 canonical.Model，收到 %r" % (type(model).__name__,))
    if not isinstance(opts, MacOptions):
        raise ValueError("opts 必须是 macgen.MacOptions，收到 %r" % (type(opts).__name__,))
    if opts.unit not in UNIT_FACTOR:
        raise ValueError("MacOptions.unit=%r 非法，须为 %s（契约 §d.4-1）"
                         % (opts.unit, "/".join(UNITS)))
    if opts.secmap is None:
        raise ValueError("MacOptions.secmap 为 None：禁止静默产出'无规格宏'（契约 §b.6）——"
                         "CLI 必须注入 SectionMap.load(...) 的结果")
    if not (str(opts.site_name or "").strip()):
        raise ValueError(
            "MacOptions.site_name 为空：SITE 名由 .NET 侧在执行前用 DbElement 直查逐个试出"
            "（/PKPM2PDMS → /PKPM2PDMSre → …），经 --request 的 site_name 键传入；"
            "引擎不生成、不默认、不做 re 逻辑（R7）")


def _section_detail(sec: Section, kind: str, res: Resolution, used_by: Dict[str, int]) -> Dict[str, Any]:
    """契约 §h ``report.sections.detail`` 的一条记录（键名照抄 §h 示例）。"""
    return {
        "id": sec.id,
        "table": sec.table,
        "name": sec.name,
        "kind": sec.kind,
        "status": res.status,
        "source": res.source,
        "pkpm_name": res.pkpm_name,
        "spec_path": res.spec_path,
        "desp_params": list(res.desp_params),
        "reason": res.reason,
        "used_by": dict(sorted(used_by.items())),
    }


def build_plan(model: Model, opts: MacOptions) -> MacroPlan:
    """生成 :class:`MacroPlan`（宏正文 + 统计 + 未解析清单 + 报告用截面明细）。"""
    _check(model, opts)
    em = _Emitter()
    plan = MacroPlan()
    resolver = _Resolver(opts.secmap, plan.warnings.append)
    xf = _Xform(opts)
    namer = _Namer()

    def warn(msg: str) -> None:
        if msg not in plan.warnings:
            plan.warnings.append(msg)

    # ---- 名字骨架（〔R7〕SITE 名外部传入；中间层 = <SITE名>_<段>；底层 unnamed） ----
    project = _clean_name(opts.project or "PKPM_PROJECT", "MacOptions.project")
    if not (opts.project or "").strip():
        warn("MacOptions.project 为空，已退回缺省 'PKPM_PROJECT'（契约 §b.6）")
    elif not str(project).isascii():
        warn("MacOptions.project=%r 含非 ASCII 字符：ZONE 名会带中文（PDMS 名字按 GBK 落盘，"
             "建议用 ASCII 工程名）" % (project,))
    site = _clean_site(opts.site_name)                 # 去前导 '/' 的名字段
    time_text = opts.time_text or time.strftime("%Y-%m-%d %H:%M:%S")

    lv_map: Dict[int, Level] = model.level_map()
    levels = model.sorted_levels()
    known_levels = {lv.stdflr_id for lv in levels}
    #: 层 → FRMW/SBFR 名里的层号（§d.1；no 不可用时退回层序）
    n_of_level: Dict[int, int] = {}
    for idx, lv in enumerate(levels):
        n_of_level[lv.stdflr_id] = lv.no if lv.no > 0 else idx + 1

    # 构件按层、按类别分组（§d.1 的 4 个 SBFR；支撑按 |ΔU| 分水平/竖向，§c.5）
    by_level: Dict[int, Dict[str, List[Member]]] = {}
    unknown_level_members: List[Member] = []
    n_bad_type = 0
    for m in model.members:
        if m.level not in known_levels:
            unknown_level_members.append(m)
            continue
        bucket = by_level.setdefault(m.level, {"column": [], "beam": [],
                                               "hbrace": [], "vbrace": []})
        if m.type == "column":
            bucket["column"].append(m)
        elif m.type == "beam":
            bucket["beam"].append(m)
        elif m.type == "brace":
            horizontal = abs(m.end[2] - m.start[2]) <= TOL
            bucket["hbrace" if horizontal else "vbrace"].append(m)
        else:                                     # 契约 §a.7 的 E-MEM-TYPE
            n_bad_type += 1
            warn("构件 %s 的 type=%r 非法（契约 §a.7 E-MEM-TYPE），已跳过" % (m.id, m.type))
    for bucket in by_level.values():
        for key in bucket:
            bucket[key].sort(key=lambda m: (m.no if m.no > 0 else 10 ** 12, m.id))

    # ---- 元素主体（先写体，再按体的实际条数拼头：注释不许说谎） ---------------
    def emit_new(ind: str, etype: str, name: Optional[str] = None) -> None:
        """一条创建语句：``name`` 为 ``None`` ⇒ **无名创建**（底层 SCTN/PANE/STWALL）。

        带名时先过 :class:`_Namer`（重复即抛 :class:`MacroNameError`）再写行。
        """
        if name is None:
            em.line(ind + "NEW %s" % etype)
            return
        namer.take(name, etype)
        em.line(ind + "NEW %s %s" % (etype, name))

    def emit_clause(ind: str, sec: Section, res: Resolution,
                    ref_keyword: str, label: str) -> None:
        """写规格引用；未解析 ⇒ 省略该行并留 ``-- UNRESOLVED SECTION`` 标记（§d.4-2）。

        ``DESP`` 的写出条件：**只要** ``res.desp_params`` 非空（契约 §d.4-3 / §0.4-2）——
        `resolved`（型钢等固定规格）为 ``[]`` 故行为不变；`parametric`（RECT/H）与
        `inferred`（§e.1a 的 Kind=3→CIRCLE）都按族参数出 ``DESP``。
        """
        if res.spec_path and res.status in (RESOLVED, PARAMETRIC, INFERRED):
            em.line("%s%s %s" % (ind, ref_keyword, res.spec_path))
            if res.desp_params:
                em.line("%sDESP %s" % (ind, " ".join(_num(xf.length(v))
                                                     for v in res.desp_params)))
            return
        why = res.reason or ("spec_path 为空且无 DESP 参数" if res.status != UNRESOLVED
                             else "匹配文件、参数化族与推断族均未命中")
        em.line("%s-- UNRESOLVED SECTION %s %s %s（%s：%s）"
                % (ind, sec.id, _one_line(sec.name) or "(无名)", label, res.status, _one_line(why)))
        em.bump("未解析标记")

    def inferred_note(sec: Section, res: Resolution) -> str:
        """§d.4-2b：推断截面（`status='inferred'`）在元素块**上方**留的 GBK 注释。

        文本只用 GBK 可编码字符（宏纪律 §g.3），并给出"实为别的族时怎么改"。
        """
        vals = ", ".join(_num(xf.length(v)) for v in res.desp_params)
        return ("-- 推断截面（非原件映射，契约 §e.1a）：Kind=%s 按证据判为族 %s → %s；"
                "DESP = %s（单位 %s）；若实为别的族请改 engine/secmap_extra.txt 的 @FAMILY 行"
                % (sec.kind, res.pkpm_name or "(未命名族)", res.spec_path, vals or "(无)",
                   opts.unit))

    # 截面明细的登记器
    detail: Dict[Tuple[Any, ...], Dict[str, Any]] = {}

    def register(sec: Section, kind: str, res: Resolution, used_by_key: str) -> Resolution:
        key = _Resolver._key(sec, kind)
        if key in detail:
            d = detail[key]
            d["used_by"][used_by_key] = d["used_by"].get(used_by_key, 0) + 1
        else:
            detail[key] = _section_detail(sec, kind, res, {used_by_key: 1})
        return res

    # ---- SITE / ZONE / STRU（§d.4 骨架） ---------------------------------
    emit_new("", "SITE", "/" + site)
    emit_new("", "ZONE", "/%s_%s" % (site, project))
    emit_new("", "STRU", "/%s_%s" % (site, SEG_MF))
    if not levels:
        warn("模型没有任何 Level，宏内只有 SITE/ZONE/STRU 骨架")

    # ---- 每层一个 FRMW /<SITE>_EL<n>（§d.1、§d.4、§12#1） ------------------
    for idx, lv in enumerate(levels):
        n = n_of_level[lv.stdflr_id]
        if lv.no <= 0:
            warn("Level %s 的 no=%s 不可用，FRMW/SBFR 编号改用序号 %d（契约 §d.1）"
                 % (lv.stdflr_id, lv.no, n))
        emit_new("", "FRMW", "/%s_%s%d" % (site, SEG_EL, n))
        bucket = by_level.get(lv.stdflr_id, {})
        groups = [g for g in MEMBER_GROUPS if bucket.get(g[1])]
        for gi, (seg, key, _mtype, _horiz) in enumerate(groups):
            emit_new(_I2, "SBFR", "/%s_%s%d_%s" % (site, SEG_EL, n, seg))
            for m in bucket[key]:
                sec = model.sections.get(m.section)
                if sec is None:
                    emit_new(_I4, "SCTN")
                    em.bump("SCTN[%s]" % seg)
                    # 契约 §a.7 的 E-MEM-SEC：仍然建几何，但标记缺截面（不许静默）
                    em.line("%s-- UNRESOLVED SECTION %s (无名) %s 的外键不可解析（契约 §a.7 E-MEM-SEC）"
                            % (_I6, m.section, "SCTN"))
                    em.bump("未解析标记")
                    warn("构件 %s(%s) 引用截面 %s 不存在（契约 §a.7 E-MEM-SEC）："
                         "已建几何并留 -- UNRESOLVED SECTION 标记，未写 SPREF"
                         % (m.id, m.type, m.section))
                else:
                    res = resolver.resolve(sec, SECTION_KIND[m.type])
                    if res.status == INFERRED:               # §d.4-2b：推断构件块上方留注释
                        em.line(_I4 + inferred_note(sec, res))
                    emit_new(_I4, "SCTN")
                    em.bump("SCTN[%s]" % seg)
                    register(sec, SECTION_KIND[m.type], res, m.type)
                    emit_clause(_I6, sec, res, "SPREF", "SCTN")
                em.line(_I6 + xf.pos("POSS", m.start))
                em.line(_I6 + xf.pos("POSE", m.end))
                for kw, val in (("JUSL", m.jusl), ("MEML", m.meml)):
                    if not val:                       # 契约 §d.4-4：为空则不写该行
                        continue
                    tok = str(val).strip()
                    if not tok or any(c.isspace() or c < " " for c in tok):
                        warn("构件 %s 的 %s=%r 含空白/控制字符，不写入宏（避免破坏宏分词）"
                             % (m.id, kw, val))
                        continue
                    em.line(_I6 + "%s %s" % (kw, tok))
                em.line(_I6 + "BANG %s" % _num(m.rotation))
            # 组结束回退（§d.4-5）：非最后一组回 FRMW，最后一组回 STRU
            em.line(_I2 + ("FRMW" if gi < len(groups) - 1 else "STRU"))
        if not groups:                                # 该层无构件：FRMW 之后直接回 STRU
            em.line(_I2 + "STRU")

    # ---- FRMW /<SITE>_FW：SBFR /<SITE>_EL<n>_SLAB 与 _WALL（§d.1） --------
    def _level_sort_key(lv_key: int, no: int, ident: int):
        lv = lv_map.get(lv_key)
        if lv is None:
            return (1, 0.0, no, ident)
        return (0, lv.z_bot, no, ident)

    def group_by_level(items: Sequence[Any], what: str,
                       seg: str) -> List[Tuple[Optional[Level], List[Any]]]:
        """按其 level 分组，顺序 = 层序（z_bot），层内按 No_/id；未知层归 ``None`` 组（末尾）。"""
        buckets: Dict[int, List[Any]] = {}
        for s in items:
            buckets.setdefault(s.level, []).append(s)
        out: List[Tuple[Optional[Level], List[Any]]] = []
        for k in sorted(buckets, key=lambda x: _level_sort_key(x, 0, 0)):
            lv = lv_map.get(k)
            out.append((lv, sorted(buckets[k],
                                   key=lambda x: (x.no if x.no > 0 else 10 ** 12, x.id))))
            if lv is None:
                warn("有 %d 个%s的 level=%s 不在模型的 Level 表里（契约 §a.7 E-MEM-LEVEL）："
                     "它们的 SBFR 用不带层号的兜底名（/…_%s）"
                     % (len(buckets[k]), what, k, seg))
        return out

    def sbfr_name(lv: Optional[Level], seg: str) -> str:
        n = n_of_level.get(lv.stdflr_id) if lv is not None else None
        if n:
            return "/%s_%s%d_%s" % (site, SEG_EL, n, seg)
        return "/%s_%s" % (site, seg)          # 未知层：不带层号的兜底名（警告已记）

    emit_new("", "FRMW", "/%s_%s" % (site, SEG_FW))

    # SBFR /<SITE>_EL<n>_SLAB —— NEW PANE + SPREF + ORI + NEW PLOOP + HEIGHT + SJUS + PAVERT/POS
    slab_groups: List[Tuple[Optional[Level], List[Slab]]] = group_by_level(
        model.slabs, "板", SEG_SLAB)
    for lv, items in slab_groups:
        emit_new(_I2, "SBFR", sbfr_name(lv, SEG_SLAB))
        for s in items:
            psec = Section.for_panel("slab", s.thickness)
            pres = resolver.resolve(psec, "slab")
            if pres.status == INFERRED:                  # §d.4-2b
                em.line(_I4 + inferred_note(psec, pres))
            emit_new(_I4, "PANE")
            register(psec, "slab", pres, "slab")
            emit_clause(_I6, psec, pres, "SPREF", "PANE")
            if s.ori and s.ori != PANE_ORI:
                warn("板 %s 的 ori=%r 不是 %r：宏内仍按 §d.3 的 ORI 写法输出"
                     % (s.id, s.ori, PANE_ORI))
            em.line(_I6 + PANE_ORI_CMD)
            em.line(_I6 + "NEW PLOOP")
            sjus = (s.sjus or PANE_SJUS).strip()
            if any(c.isspace() or c < " " for c in sjus):
                warn("板 %s 的 sjus=%r 含空白/控制字符，改用缺省 %r" % (s.id, s.sjus, PANE_SJUS))
                sjus = PANE_SJUS
            em.line(_I8 + "HEIGHT %s SJUS %s" % (_num(xf.length(s.thickness)), sjus))
            em.bump("SJUS")
            if len(s.polygon) < 3:
                em.line("%s-- SLAB %s 多边形顶点数 %d < 3，未生成 PAVERT（契约 §a.7 E-SLAB-POLY）"
                        % (_I8, s.id, len(s.polygon)))
                em.bump("异常标记")
                warn("板 %s 多边形顶点数 %d < 3（契约 §a.7 E-SLAB-POLY）：PANE 已建但不含 PAVERT"
                     % (s.id, len(s.polygon)))
            for p in s.polygon:
                em.line(_I8 + "NEW PAVERT")
                em.line(_I8 + xf.pos("POS", (p[0], p[1], s.z)))
            em.line(_I4 + "PANE")                     # 回退到 PANE（§d.4 骨架）
    em.line(_I2 + "FRMW")                             # 组结束回退到 FRMW

    # SBFR /<SITE>_EL<n>_WALL —— NEW STWALL + SPRE（墙用 SPRE，§d.3/§12#2）
    wall_groups: List[Tuple[Optional[Level], List[Wall]]] = group_by_level(
        model.walls, "墙", SEG_WALL)
    for lv, items in wall_groups:
        emit_new(_I2, "SBFR", sbfr_name(lv, SEG_WALL))
        for w in items:
            if w.section >= 0 and w.section in model.sections:
                wsec = model.sections[w.section]
            else:
                wsec = Section.for_panel("wall", w.thickness, name=w.name or "")
            wres = resolver.resolve(wsec, "wall")
            if wres.status == INFERRED:                  # §d.4-2b
                em.line(_I4 + inferred_note(wsec, wres))
            emit_new(_I4, "STWALL")
            register(wsec, "wall", wres, "wall")
            emit_clause(_I6, wsec, wres, "SPRE", "STWALL")
            if len(w.loop) >= 2:
                em.line(_I6 + xf.pos("POSS", w.loop[0]))     # 底边起点（§c.3.8：loop[0]）
                em.line(_I6 + xf.pos("POSE", w.loop[1]))     # 底边终点
            else:
                em.line("%s-- WALL %s 回路顶点数 %d < 2，未生成 POSS/POSE（契约 §a.7 E-WALL-LOOP）"
                        % (_I6, w.id, len(w.loop)))
                em.bump("异常标记")
                warn("墙 %s 回路顶点数 %d < 2（契约 §a.7 E-WALL-LOOP）：STWALL 已建但无 POSS/POSE"
                     % (w.id, len(w.loop)))
            if not wres.desp_params:                     # §d.4-3 / §0.4-2：有 desp_params 才写 DESP
                warn("墙 %s 的高度 %g mm 无法用已证实的宏命令表达（墙高在已证实的写法里经规格 "
                     "DESP 传入，见 nucdesogwall.pmlobj:58/184-187；本宏不发 DESP）："
                     "STWALL 仅有 SPRE 与底边 POSS/POSE" % (w.id, w.z_top - w.z_bot))
            if w.spec_path and w.spec_path != wres.spec_path:
                warn("墙 %s 自带 spec_path=%r 与 secmap 的解析结果 %r 不一致：按契约 §e.6 以 secmap 为准"
                     % (w.id, w.spec_path, wres.spec_path))
    em.line(_I2 + "STRU")                             # 最后一组结束回退到 STRU

    # ---- FRMW /<SITE>_GR（承载轴网；v1.0 不写轴网构件，§d.1/§12#13） ------
    emit_new("", "FRMW", "/%s_%s" % (site, SEG_GR))
    em.line(_I2 + "-- 轴网不导出（v1.0 只建 FRMW，不写轴网构件：契约 §d.1、§12#13）")
    em.line("STRU")

    # ---- 头部与尾部（〔R7〕标准结构；计数注释按体的实际条数写） --------------
    body = em.lines
    counts = _count_creates(body)
    em_head = _Emitter()
    em_head.line("$S-  -- Synonym translation OFF")         # §o.5 冻结首行（逐字）
    em_head.line(SEP_LINE)
    em_head.line("-- %s  Date: %s" % (MACRO_PURPOSE, time_text))
    em_head.line("-- 元素：%s" % " / ".join("%s %d" % (t, counts[t]) for t in ELEM_TYPES))
    for ln in str(opts.header_note or "").splitlines():
        if ln.strip():
            em_head.line("-- " + _one_line(ln))
    em_head.line(ONERROR_LINE)                              # 〔R7〕出错继续

    em_tail = _Emitter()
    em_tail.line("-- End %s  Date: %s" % (MACRO_PURPOSE, time_text))
    em_tail.line("$S+  -- Synonym translation ON")
    em_tail.line(SEP_LINE)

    plan.lines = em_head.lines + body + em_tail.lines
    stats: Dict[str, int] = dict(em.stats)
    for k, v in list(em_head.stats.items()) + list(em_tail.stats.items()):
        stats[k] = stats.get(k, 0) + v
    plan.stats = stats
    plan.used_names = sorted(namer.used)
    plan.unnamed_count = _count_unnamed(plan.lines)

    # ---- 落盘前全量自查（重解析 `NEW <TYPE> /名字`；禁项扫描） ---------------
    audit = _audit_macro(plan.lines)
    if audit["names"] != len(plan.used_names):
        raise MacroNameError(
            "宏内名字集合与生成期簿记不一致：自查 %d 个 / 簿记 %d 个（不许带病出宏）"
            % (audit["names"], len(plan.used_names)))

    # ---- 报告用清单 ------------------------------------------------------
    plan.assumptions.append(
        "SITE 名由**外部传入**（MacOptions.site_name=%r）：.NET 侧执行前用 DbElement 直查逐个"
        "试名（/PKPM2PDMS → /PKPM2PDMSre → … re99），引擎不改名、不做 re 逻辑（R7）"
        % (opts.site_name,))
    plan.assumptions.append(
        "中间层名字 = <SITE名>_<段>（ZONE=_<工程名>、STRU=_%s、FRMW=_%s<n>/_%s/_%s、"
        "SBFR=_%s<n>_%s|%s|%s|%s|%s|%s）：含层号 ⇒ 全宏唯一；每个带名 NEW 写入前查重，"
        "重复即生成失败（R7 硬保证）"
        % (SEG_MF, SEG_EL, SEG_FW, SEG_GR, SEG_EL, SEG_COLUMN, SEG_BEAM, SEG_HBRACE,
           SEG_VBRACE, SEG_SLAB, SEG_WALL))
    plan.assumptions.append(
        "底层 SCTN/PANE/STWALL 一律**无名创建**（NEW SCTN / NEW PANE / NEW STWALL，不带名字，"
        "PDMS 自动分配系统名）：其后的 SPREF/DESP/POSS/POSE/JUSL/MEML/BANG/ORI/PLOOP/HEIGHT/"
        "PAVERT 等属性行都作用在当前元素上，不需要名字引用（R7；PMLLIB 先例见模块头）")
    plan.assumptions.append(
        "宏头 %r：出错继续（PMLLIB 内 251 处先例）；层级名生成期唯一、底层元素无名 ⇒ 预期不触发。"
        "宏内**没有** LABEL/handle 错误块（〔R6/R7〕已删除）" % (ONERROR_LINE,))
    plan.assumptions.append(
        "宏内**零运行期函数依赖**：不出现任何 !!pkpm2pdms* 调用、不 $M 预载任何 .pmlfnc；"
        "pdms/pkpm2pdmsuniquename*.pmlfnc 系列自 R7 起不再部署、不再被引用（R7）")
    plan.assumptions.append(
        "宏内不发出单位设置语句，需 PDMS 当前单位为 %s（契约 §d.4-1）" % (opts.unit,))
    plan.assumptions.append(
        "DESP 参数按长度量随单位缩放（契约 §d.4-3 / §0.4-2：只要 resolution 带 desp_params 就写出）")
    plan.assumptions.append(
        "板/墙规格由 Section.for_panel(kind, 厚度) 经 opts.secmap.resolve 得到"
        "（契约 §e.6：截面解析只有一条路）")
    plan.assumptions.append(
        "推断族（status=inferred，契约 §e.1a）由补充文件的 @FAMILY 指令启用；"
        "该结论是**有证据的判定**而非原件映射，逐条 evidence 见报告 report.sections.detail")

    if unknown_level_members:
        warn("有 %d 个构件的 level 不可解析（契约 §a.7 E-MEM-LEVEL），未写入宏：%s"
             % (len(unknown_level_members),
                ", ".join("Member %s(%s)" % (m.id, m.type) for m in unknown_level_members[:10])))
    if model.loads:
        warn("本版本不导出荷载：%d 条荷载未写入宏（契约 §d 的允许语法里没有荷载命令）"
             % (len(model.loads),))

    # 报告里的截面明细按 (表, id, 名) 排序，保证同内容必得同顺序（便于跨包比对）
    plan.sections = sorted(detail.values(),
                           key=lambda d: (str(d["table"]), d["id"], d["name"]))
    plan.unresolved = [d for d in plan.sections if d["status"] == UNRESOLVED]
    plan.inferred = [d for d in plan.sections if d["status"] == INFERRED]
    if plan.inferred:
        warn("有 %d 个被用到的截面按**推断族**解析（status=inferred，非 resolved；宏内已在上方留 "
             "-- 推断截面 注释）：%s"
             % (len(plan.inferred),
                ", ".join("%s/%s(→%s)" % (d["id"], d["name"] or "(无名)", d["spec_path"])
                          for d in plan.inferred[:10])))
    if plan.unresolved:
        warn("有 %d 个被用到的截面未解析（宏内已留 -- UNRESOLVED SECTION 标记，未静默跳过）：%s"
             % (len(plan.unresolved),
                ", ".join("%s/%s" % (d["id"], d["name"] or "(无名)")
                          for d in plan.unresolved[:10])))
    return plan


# --------------------------------------------------------------------------
# 契约冻结的三个入口
# --------------------------------------------------------------------------


def generate_macro(model: Model, opts: MacOptions) -> str:
    """规范模型 → PDMS 宏全文（str，各行以 CRLF 结尾）。

    ``opts.secmap is None``（或 ``opts.site_name`` 为空）时抛 ``ValueError``（契约 §b.6/R7）。
    """
    return build_plan(model, opts).text()


def _to_gbk_crlf(text: str) -> bytes:
    """str → GBK 字节 + CRLF（无 BOM）。编码失败即抛错，禁止 errors='replace'。"""
    if not isinstance(text, str):
        raise ValueError("text 必须是 str，收到 %r" % (type(text).__name__,))
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    try:
        data = t.encode("gbk")
    except UnicodeEncodeError as exc:
        raise ValueError("宏文本含 GBK 无法编码的字符 %r（位置 %d）：PDMS 侧产物必须 GBK，"
                         "禁止用 errors='replace' 静默替换（契约 §g）"
                         % (t[exc.start:exc.end], exc.start))
    return data.replace(b"\n", b"\r\n")


def write_macro(path: str, text: str) -> str:
    """把宏文本写成 **GBK 无 BOM + CRLF** 文件，回读校验后返回 ``path``。

    * 先编码再写（契约 §g 硬性纪律 3），不用平台默认编码；
    * 父目录不存在则创建（``--out`` 指定路径的一部分）；
    * 回读校验：不得出现 BOM、不得出现孤立 ``\\n``（契约 §g）；
    * 〔R7〕落盘前再跑一遍 :func:`_audit_macro`（名字查重 + 运行期函数依赖禁项扫描），
      这样"直接调 ``write_macro`` 的调用方"也拿不到带病宏。
    """
    if isinstance(text, str):
        _audit_macro(text.replace("\r\n", "\n").replace("\r", "\n").split("\n"))
    data = _to_gbk_crlf(text)
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    with open(path, "rb") as f:
        back = f.read()
    if back != data:
        raise IOError("写回校验失败：%s 的字节与预期不一致" % (path,))
    if back.startswith(b"\xef\xbb\xbf"):
        raise ValueError("产物带 BOM：%s（契约 §g 禁止 BOM）" % (path,))
    if b"\n" in back.replace(b"\r\n", b""):
        raise ValueError("产物含孤立 LF：%s（契约 §g 要求 CRLF）" % (path,))
    return path
