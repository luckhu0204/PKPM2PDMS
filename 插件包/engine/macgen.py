# -*- coding: utf-8 -*-
"""PKPM-JWD导入导出 —— 规范模型 → PDMS 宏生成器（``engine/macgen.py``）。

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
``NEW SCTN`` + ``SPREF``        ``mypml\\forms\\StlGrating.pmlfrm:92-93``；``design\\functions\\sctlcrelem.pmlfnc:267-273``
``DESP``                       ``mypml\\forms\\StlGrating.pmlfrm:94``；``sctlcrelem.pmlfnc:180``
``POSS E .. N .. U ..``/``POSE``  ``mypml\\forms\\StlGrating.pmlfrm:96-97``
``JUSL``/``MEML``              ``sctlcrelem.pmlfnc:338-340``；``MYTOOLS\\…\\sdnfinver3.pmlfnc:187-188``
``BANG``                       ``MYTOOLS\\test\\Tekla2PDMS\\sdnf\\functions\\sdnfinver3.pmlfnc:192``
``NEW PANE``/``ORI Y IS N AND Z IS U``/``NEW PLOOP``/``HEIGHT <t> SJUS dbot``/``NEW PAVERT``/``POS``  ``mypml\\forms\\StlGrating.pmlfrm:45-56``；``sctlcrelem.pmlfnc:229-256``
裸类型名 ``PANE``（回退）        ``design\\objects\\mergegensectpane.pmlobj:1041``
``NEW STWALL`` + ``SPRE``       ``design\\functions\\sctlcrelem.pmlfnc:201-202``；``concrete_design\\TRADUCTEUR\\nucdesogwall.pmlobj:180-196``
``--`` 行注释 / ``$S-`` ``$S+``   ``mypml\\forms\\scale-STRU.mac``；用户原件 ``PKPM（PDMS数据库）.txt`` 首/末行
唯一化模板（``!!pkpmjwdType``/``!n = !!pkpmjwdUniquename``/故障注入/``NEW <T> $!n``）
                               契约 §o.4/附录 F.2（占用探测 ``VAR EXIST $!x``+``handle (2,109)`` 出处 ``aba\\Forms\\abaarealib.pmlfrm:107-114`` 与带斜杠名字惯用法 tgautonum.pmlfnc:33-41；``defined()`` 出处 ``nucdesogwall.pmlobj:206``；``ONERROR/LABEL`` 尾出处 ``PKPM（PDMS数据库）.txt`` L5/L70291-70295）
============================  ==========================================================

契约 §d.4-2 的"未解析截面"处置：仍建构件几何，省略 ``SPREF``/``SPRE`` 行，并在其上方写
``-- UNRESOLVED SECTION <id> <name> <reason>``；对应条目回流到 :attr:`MacroPlan.unresolved`。
"""

from __future__ import annotations

import math
import os
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

__all__ = ["MacOptions", "MacroPlan", "build_plan", "generate_macro", "write_macro",
           "UNIT_FACTOR", "MEMBER_GROUPS"]

# --------------------------------------------------------------------------
# 契约常量（值全部取自 CONTRACT §d，不得在此处另立新值）
# --------------------------------------------------------------------------

#: 长度单位 → mm 系数（契约 §d.4-1：mm=×1、cm=÷10、m=÷1000）
UNIT_FACTOR = {"mm": 1.0, "cm": 10.0, "m": 1000.0}
UNITS = ("mm", "cm", "m")

SITE_NAME = "/PKPM_JWD"                  # §d.1 / §d.4
STRU_NAME = "/MAINFRAME"                 # §d.1 / §d.4
FRMW_STL = "/STL_FRAME/EL"               # §d.1：每层一个 FRMW，名称字面 /STL_FRAME/EL<n>
FRMW_FLOOR_WALL = "/FLOOR&WALL"          # §d.1
FRMW_GRID = "/GRID"                      # §d.1
SBFR_COLUMN = "/COLUMN"                  # §d.1
SBFR_BEAM = "/BEAM"
SBFR_HBRACE = "/HBRACE"
SBFR_VBRACE = "/VBRACE"
SBFR_SLAB = "/SLAB"
SBFR_WALL = "/WALL"

NAME_COL = "/STL_COL_"                   # §d.2
NAME_BEAM = "/BM_"
NAME_HBRACE = "/HB_"
NAME_VBRACE = "/VB_"
NAME_SLAB = "/SLAB_"
NAME_WALL = "/W_"

#: PANE 的 ORI 命令原文（§d.3/d.4；等价于 canonical.PANE_ORI == 'YNZU'）
PANE_ORI_CMD = "ORI Y IS N AND Z IS U"

#: 构件组定义：(SBFR 名, 元素名前缀, 类别键, 成员类型, 是否只取水平支撑)
MEMBER_GROUPS = (
    (SBFR_COLUMN, NAME_COL, "column", "column", None),
    (SBFR_BEAM, NAME_BEAM, "beam", "beam", None),
    (SBFR_HBRACE, NAME_HBRACE, "hbrace", "brace", True),
    (SBFR_VBRACE, NAME_VBRACE, "vbrace", "brace", False),
)

#: 构件类型 → SectionMap.resolve 的 kind（§e.6）
SECTION_KIND = {"beam": "beam", "column": "col", "brace": "brace"}

# 缩进（纯排版；PDMS 宏忽略行首空白，见 §6.2 的 Tab 缩进实例）
_I2, _I4, _I6, _I8 = "  ", "    ", "      ", "        "


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

    只拒绝会破坏宏分词规则的字符（空白、控制字符）；``/`` 在名称内是**合法**的
    （§d.2 的证据：``GRIDDESIGN.pmlfrm:975`` 给 SBFR 起含 ``/`` 的名字）。
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
    """``generate_macro`` 的参数 —— 字段与契约 §b.6 的表**逐一对应**。

    ``secmap`` 为 ``None`` 时 :func:`generate_macro`/`build_plan` 抛 ``ValueError``：
    契约 §b.6 明令禁止静默产出"无规格宏"。本模块不 import ``secmap``，只要求它
    提供 ``.resolve(section, kind) -> Resolution``（§e.6）。
    """

    project: str = "PKPM_PROJECT"
    base_e: float = 0.0
    base_n: float = 0.0
    base_u: float = 0.0
    angle_deg: float = 0.0
    unit: str = "mm"
    secmap: Any = None                # SectionMap | None
    header_note: str = ""
    time_text: str = ""               # 留空 ⇒ 取当前时间
    uniquify: bool = True             # 〔R3 §b.6/§o.4〕True ⇒ 每个创建元素前 emit 唯一化模板；
                                      #   False ⇒ v1 行为（直接 NEW <TYPE> /名），仅测试用
    pml_func_path: str = ""           # 〔R3 §b.6/§o.4〕pkpmjwduniquename.pmlfnc 的路径；
                                      #   非空 ⇒ 宏头 emit $M <$!pkpmjwdFuncPath>；空 ⇒ 只发注释提醒

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
    * :attr:`name_renames` —— SBFR 内重名被迫改名清单（契约 §d.2 只保证层内唯一）
    """

    lines: List[str] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    sections: List[Dict[str, Any]] = field(default_factory=list)
    unresolved: List[Dict[str, Any]] = field(default_factory=list)
    inferred: List[Dict[str, Any]] = field(default_factory=list)
    name_renames: List[Tuple[str, str]] = field(default_factory=list)

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


def _alloc_name(prefix: str, no: int, seq: int, used: set, level_no: int,
                renames: List[Tuple[str, str]]) -> str:
    """在同一个 SBFR 内分配唯一元素名（契约 §d.2：``<前缀><No_>``）。

    ``No_`` 是**层内**编号，而 §d.1 把同类别构件放在**同一个** SBFR 下（板/墙尤其明显），
    跨层重名必须去重，否则 PDMS 的同级唯一性被破坏。去重规则（确定性、可追溯）：
    首次出现保持原样；重名时追加 ``_EL<层号>``；仍冲突则追加 ``_<k>``。
    """
    if no and int(no) > 0:
        base = "%s%d" % (prefix, int(no))
    else:
        base = "%s%d" % (prefix, int(seq))
    name = base
    if name in used:
        alt = "%s_EL%d" % (base, int(level_no))
        if alt in used:
            k = 2
            while ("%s_%d" % (alt, k)) in used:
                k += 1
            alt = "%s_%d" % (alt, k)
        renames.append((base, alt))
        name = alt
    used.add(name)
    return name


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
    if not isinstance(opts.uniquify, bool):
        raise ValueError("MacOptions.uniquify 必须是 bool，收到 %r（契约 §b.6）" % (opts.uniquify,))
    if not isinstance(opts.pml_func_path, str):
        raise ValueError("MacOptions.pml_func_path 必须是 str，收到 %r（契约 §b.6）"
                         % (opts.pml_func_path,))
    if "'" in opts.pml_func_path:
        raise ValueError("MacOptions.pml_func_path=%r 含单引号：会破坏宏内 PML 字符串字面量"
                         % (opts.pml_func_path,))


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
    uniq = bool(opts.uniquify)          # §o.4：True ⇒ 唯一化模板；False ⇒ v1 行为

    def warn(msg: str) -> None:
        if msg not in plan.warnings:
            plan.warnings.append(msg)

    # ---- 名称与计数（先生成，供头部注释统计） ----------------------------
    project = _clean_name(opts.project or "PKPM_PROJECT", "MacOptions.project")
    if not (opts.project or "").strip():
        warn("MacOptions.project 为空，已退回缺省 'PKPM_PROJECT'（契约 §b.6）")
    time_text = opts.time_text or time.strftime("%Y-%m-%d %H:%M:%S")

    lv_map: Dict[int, Level] = model.level_map()
    levels = model.sorted_levels()
    known_levels = {lv.stdflr_id for lv in levels}

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

    braces_h = sum(len(b["hbrace"]) for b in by_level.values())
    braces_v = sum(len(b["vbrace"]) for b in by_level.values())
    n_mem = len(model.members) - len(unknown_level_members) - n_bad_type
    n_slab = len(model.slabs)

    # ---- 头部（§d.4 骨架 + 统计/说明注释；§o.4/§o.5 唯一化前置） ----------
    if uniq:
        em.line("$S-  -- Synonym translation OFF")   # §o.5 冻结首行（逐字）
    else:
        em.line("$S-  -- 关闭同义词翻译（Synonym translation OFF，见 PKPM（PDMS数据库）.txt 首行）")
    em.line("-- PKPM-JWD导入导出 自动生成：%s  %s  契约 v%s"
            % (_one_line(model.source) or "(未标注来源)", time_text, CONTRACT_VERSION))
    em.line("-- 单位：%s（本宏不含单位设置语句，须先把 PDMS 当前单位设为 %s，契约 §d.4-1）；"
            "基点 E/N/U = %s/%s/%s；转角 = %s 度"
            % (opts.unit, opts.unit, _num(opts.base_e), _num(opts.base_n),
               _num(opts.base_u), _num(opts.angle_deg)))
    em.line("-- 构件 %d：柱 %d / 梁 %d / 支撑 %d（水平 %d、竖向 %d）；板面 %d；墙 %d；"
            "荷载 %d（本版本不导出荷载：契约 §d 无荷载命令）"
            % (n_mem,
               sum(len(b["column"]) for b in by_level.values()),
               sum(len(b["beam"]) for b in by_level.values()), braces_h + braces_v,
               braces_h, braces_v, n_slab, len(model.walls), len(model.loads)))
    if uniq:
        # 元素计数注释 + 命名约定说明（§o 同步更新；计数与下方实际 emit 的创建命令一一对应）
        n_frmw = len(levels) + 2                      # 每层 1 个 + /FLOOR&WALL + /GRID
        n_sbfr = len(levels) * 4 + 2                  # 每层 4 个 + /SLAB + /WALL
        n_create = 3 + n_frmw + n_sbfr + n_mem + n_slab + len(model.walls)
        em.line("-- 创建元素 %d = SITE 1 + ZONE 1 + STRU 1 + FRMW %d（%d 层 + /FLOOR&WALL + /GRID）"
                " + SBFR %d（%d 层×4 + /SLAB + /WALL）+ SCTN %d + PANE %d + STWALL %d；"
                "每个创建前都做唯一化探测"
                % (n_create, n_frmw, len(levels), n_sbfr, len(levels),
                   n_mem, n_slab, len(model.walls)))
        em.line("-- 命名约定（契约 §d.2/§o）：名称照 §d.2（/STL_COL_<No_>、/BM_<No_>、/HB_<No_>、"
                "/VB_<No_>、/SLAB_<No_>、/W_<No_> 与骨架名）；若与 PDMS 库中已有模型重名，"
                "则追加后缀 re（还冲突继续 re2、re3…re99，候选上限 100，耗尽即整宏中止——"
                "不跳过、不覆盖）；本文件内仍写原名，运行期改名记录在 !!pkpmjwdRenames"
                "（报告导出为 report.renames，§o.7）")
    for ln in str(opts.header_note or "").splitlines():
        if ln.strip():
            em.line("-- " + _one_line(ln))
    if uniq:
        em.line("ONERROR GOLABEL /PKPMJWDERR")        # §o.5 冻结（逐字）
        if (opts.pml_func_path or "").strip():
            # §o.4 冻结的预载写法：$M <$!pkpmjwdFuncPath>；先给变量赋值使宏可独立运行
            em.line("!pkpmjwdFuncPath = '%s'" % opts.pml_func_path.replace("\\", "/"))
            em.line("$M <$!pkpmjwdFuncPath>")         # §o.4 逐字（出处 nucdesogwall.pmlobj:204）
        else:
            # §b.6：pml_func_path 为空 ⇒ 只发注释提醒"函数须已加载"
            em.line("-- 唯一化函数 !!pkpmjwdUniquename 须已加载（$M pdms/pkpmjwduniquename.pmlfnc，"
                    "契约 §o.2 / 附录 F.1）")
        # 唯一化函数可用性检查（每个宏一次；缺失 ⇒ 故障注入中止，绝不静默继续）
        em.line("-- 唯一化函数可用性检查：!!pkpmjwdUniquename 未加载时本宏立即中止（不静默继续）")
        em.line("-- 安装提示：先执行 $M <包目录>/pdms/pkpmjwduniquename.pmlfnc（GBK 无 BOM + CRLF）")
        em.line("--         或安装 PKPMJWD 插件（deploy 会把函数复制到 <PDMS根>\\PKPMJWD\\pml\\ 并在启动时预载）")
        em.line("if (defined(!!pkpmjwdUniquename)) then")   # defined()：nucdesogwall.pmlobj:206
        em.line("else")
        em.line("  var !pkpmjwdFuncMissing EXIST /")        # 故障注入（§o.4 机制）⇒ ONERROR 中止
        em.line("endif")

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
    if uniq:
        plan.assumptions.append(
            "命名唯一化（契约 §o）：每个创建元素前经 !!pkpmjwdUniquename 运行期探测占用"
            "（EXIST $!x + handle (2,109)；探测/重探形态与 62 处带斜杠名字的 PMLLIB 惯用法一致，"
            "§o.3/§0.4-12）；重名追加 re/re2..re99"
            "（候选上限 100，§o.1）；生成文件内仍写原名，运行期改名由 PDMS 侧 !!pkpmjwdRenames "
            "导出为 report.renames（§o.7）")
        plan.assumptions.append(
            "唯一化失败语义待实机（§12#26/27/28）：候选耗尽 ⇒ 函数返回空串 + 故障注入 "
            "（无名参数的 EXIST）⇒ ONERROR /PKPMJWDERR 中止整宏（不跳过、不覆盖）；"
            "(2,109) 的占用判定语义与故障注入行为均标注为推断待实机")
        if not (opts.pml_func_path or "").strip():
            plan.assumptions.append(
                "宏未带 $M 预载（MacOptions.pml_func_path 为空）：运行前须先 "
                "$M <包>/pdms/pkpmjwduniquename.pmlfnc 加载唯一化函数，"
                "否则在头部可用性检查处中止（§b.6/§o.4）")

    if unknown_level_members:
        warn("有 %d 个构件的 level 不可解析（契约 §a.7 E-MEM-LEVEL），未写入宏：%s"
             % (len(unknown_level_members),
                ", ".join("Member %s(%s)" % (m.id, m.type) for m in unknown_level_members[:10])))
    if model.loads:
        warn("本版本不导出荷载：%d 条荷载未写入宏（契约 §d 的允许语法里没有荷载命令）"
             % (len(model.loads),))

    # ---- 截面明细的登记器 ------------------------------------------------
    detail: Dict[Tuple[Any, ...], Dict[str, Any]] = {}

    def register(sec: Section, kind: str, res: Resolution, used_by_key: str) -> Resolution:
        key = _Resolver._key(sec, kind)
        if key in detail:
            d = detail[key]
            d["used_by"][used_by_key] = d["used_by"].get(used_by_key, 0) + 1
        else:
            detail[key] = _section_detail(sec, kind, res, {used_by_key: 1})
        return res

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

    def emit_new(ind: str, etype: str, name: str) -> None:
        """一条创建语句：uniquify=True 时 emit 契约 §o.4 的**逐字模板**，False 时 v1 直写。

        模板（CONTRACT §o.4 / 附录 F.2 夹具，逐字；§0.4-12 修订后的形态）::

            !!pkpmjwdType = '<TYPE>'
            !n = !!pkpmjwdUniquename('<名>')
            if (!n eq '') then
              var !pkpmjwdFatal EXIST $!n
            endif
            NEW <TYPE> $!n

        * ``name`` 必须带前导 '/'（§o.1：base 含前导 '/'）；
        * ``!!pkpmjwdType`` 是**双 ! 全局**（§0.4-12：单 ! 变量在函数作用域内不可见；
          旧实现误赋单 ! ⇒ 函数读到的 TYPE 恒 '?'，report.renames 的 type 字段失真）；
        * `if (!n eq '')` 的故障注入：候选耗尽 ⇒ 函数返回 '' ⇒ 该行变成无名参数的
          ``VAR … EXIST`` ⇒ 非法 ⇒ 触发宏头 ``ONERROR GOLABEL /PKPMJWDERR`` ⇒ 整宏中止
          （§o.5/§o.6，不跳过、不覆盖；§12#27 标注该行为【推断-高】待实机）；
        * `!n` 非空时该行只是重探一次刚验证过的名字（`EXIST /名`，§o.3 已证实形态），无副作用。
        """
        if not uniq:
            em.line(ind + "NEW %s %s" % (etype, name))
            return
        em.line(ind + "!!pkpmjwdType = '%s'" % etype)
        em.line(ind + "!n = !!pkpmjwdUniquename('%s')" % name)
        em.line(ind + "if (!n eq '') then")
        em.line(ind + "  var !pkpmjwdFatal EXIST $!n")
        em.line(ind + "endif")
        em.line(ind + "NEW %s $!n" % etype)
        em.bump("唯一化调用")

    # ---- SITE / ZONE / STRU（§d.4 骨架） ---------------------------------
    emit_new("", "SITE", SITE_NAME)
    emit_new("", "ZONE", "/" + project)
    emit_new("", "STRU", STRU_NAME)
    if not levels:
        warn("模型没有任何 Level，宏内只有 SITE/ZONE/STRU 骨架")

    # ---- 每层一个 FRMW /STL_FRAME/EL<n>（§d.1、§d.4、§12#1） -------------
    for idx, lv in enumerate(levels):
        n = lv.no if lv.no > 0 else idx + 1
        if lv.no <= 0:
            warn("Level %s 的 no=%s 不可用，FRMW 编号改用序号 %d（契约 §d.1）"
                 % (lv.stdflr_id, lv.no, n))
        emit_new("", "FRMW", "%s%d" % (FRMW_STL, n))
        bucket = by_level.get(lv.stdflr_id, {"column": [], "beam": [],
                                             "hbrace": [], "vbrace": []})
        groups = MEMBER_GROUPS
        for gi, (sbfr, prefix, key, _mtype, _horiz) in enumerate(groups):
            emit_new(_I2, "SBFR", sbfr)
            used: set = set()
            items = bucket.get(key, [])
            for i, m in enumerate(items):
                sec = model.sections.get(m.section)
                nm = _alloc_name(prefix, m.no, i + 1, used, n, plan.name_renames)
                if sec is None:
                    emit_new(_I4, "SCTN", nm)
                    em.bump("SCTN[%s]" % sbfr)
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
                    emit_new(_I4, "SCTN", nm)
                    em.bump("SCTN[%s]" % sbfr)
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

    # ---- FRMW /FLOOR&WALL：SBFR /SLAB + SBFR /WALL（§d.1） ---------------
    emit_new("", "FRMW", FRMW_FLOOR_WALL)

    def _level_sort_key(lv_key: int, no: int, ident: int):
        lv = lv_map.get(lv_key)
        if lv is None:
            return (1, 0.0, no, ident)
        return (0, lv.z_bot, no, ident)

    # SBFR /SLAB —— NEW PANE + SPREF + ORI + NEW PLOOP + HEIGHT + SJUS + PAVERT/POS
    emit_new(_I2, "SBFR", SBFR_SLAB)
    used_slab: set = set()
    slabs: List[Slab] = sorted(model.slabs, key=lambda s: _level_sort_key(s.level, s.no, s.id))
    for i, s in enumerate(slabs):
        lv = lv_map.get(s.level)
        lv_no = lv.no if lv is not None and lv.no > 0 else (i + 1)
        nm = _alloc_name(NAME_SLAB, s.no, i + 1, used_slab, lv_no, plan.name_renames)
        psec = Section.for_panel("slab", s.thickness)
        pres = resolver.resolve(psec, "slab")
        if pres.status == INFERRED:                  # §d.4-2b
            em.line(_I4 + inferred_note(psec, pres))
        emit_new(_I4, "PANE", nm)
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
    em.line(_I2 + "FRMW")                         # 组结束回退到 FRMW

    # SBFR /WALL —— NEW STWALL + SPRE（墙用 SPRE，§d.3/§12#2）
    emit_new(_I2, "SBFR", SBFR_WALL)
    used_wall: set = set()
    walls: List[Wall] = sorted(model.walls, key=lambda w: _level_sort_key(w.level, w.no, w.id))
    for i, w in enumerate(walls):
        lv = lv_map.get(w.level)
        lv_no = lv.no if lv is not None and lv.no > 0 else (i + 1)
        nm = _alloc_name(NAME_WALL, w.no, i + 1, used_wall, lv_no, plan.name_renames)
        if w.section >= 0 and w.section in model.sections:
            wsec = model.sections[w.section]
        else:
            wsec = Section.for_panel("wall", w.thickness, name=w.name or "")
        wres = resolver.resolve(wsec, "wall")
        if wres.status == INFERRED:                  # §d.4-2b
            em.line(_I4 + inferred_note(wsec, wres))
        emit_new(_I4, "STWALL", nm)
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
    em.line(_I2 + "STRU")                         # 最后一组结束回退到 STRU

    # ---- FRMW /GRID（承载轴网；v1.0 不写轴网构件，§d.1/§12#13） -----------
    emit_new("", "FRMW", FRMW_GRID)
    em.line(_I2 + "-- 轴网不导出（v1.0 只建 FRMW，不写轴网构件：契约 §d.1、§12#13）")
    em.line("STRU")
    if uniq:
        # §o.5 冻结尾（逐字；出处：PKPM（PDMS数据库）.txt L70291-70295 / rptoutput.pmlfrm）
        em.line("LABEL /PKPMJWDERR")
        em.line("handle ANY")
        em.line("$S+")
        em.line("RETURN ERROR")
        em.line("endhandle")
    else:
        em.line("$S+  -- 恢复同义词翻译（Synonym translation ON）")

    plan.lines = em.lines
    plan.stats = em.stats
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
    if plan.name_renames:
        warn("SBFR 内出现重名（契约 §d.2 的 <No_> 是层内编号，而 §d.1 把同类构件放在同一个 SBFR 下），"
             "已按 _EL<层号> 去重 %d 处：%s%s"
             % (len(plan.name_renames),
                ", ".join("%s→%s" % (a, b) for a, b in plan.name_renames[:6]),
                " …" if len(plan.name_renames) > 6 else ""))
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

    ``opts.secmap is None`` 时抛 ``ValueError``（契约 §b.6）。
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
    * 回读校验：不得出现 BOM、不得出现孤立 ``\\n``（契约 §g）。
    """
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
