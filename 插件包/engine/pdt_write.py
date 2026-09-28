# -*- coding: utf-8 -*-
"""PKPM2PDMS导入导出 —— ``.pdt`` 写出器（契约 §(j)，v2.0 / 变更记录 §0.4-4/5/6）。

把 :class:`canonical.Model` 写成 PKPM 的文本中间模型 ``.pdt``——**逐字**照
``1_PM.pdt`` 的行式（契约 §j.4 的模板表）与 ``PDMSxCA_Addin121.dll`` 里的格式串
（契约附录 D.1；本模块的自检脚本 ``test/pdt_write_selfcheck.py`` 会自己从 DLL 里
按偏移重新提取一遍再比对，不转述）。

两个入口（§j.1 **冻结**）::

    write_pdt(model, path, opts=None) -> dict           # 规范模型 → .pdt
    write_pdt_sections(sections, path, opts=None) -> dict  # db2pdt 的唯一入口

文件级纪律（§j.2，全部以样本 ``1_PM.pdt`` 为据）

1. **GBK 无 BOM + CRLF**；写完回读校验（GBK 严格可解码、不存在单 ``\\n``）。
2. 段序 13 段：``$VERSION`` → ``$DESIGNPARA`` → ``$STORY`` → ``$NODECOOR`` → ``$NET``
   → ``$DEFFRAMESECTION`` → ``$DEFWASLABSECTION`` → ``$DEFMATERIAL`` → ``$SETELEMENT``
   → ``$SETWALL`` → ``$SETSLAB`` → ``$RIGID`` → 荷载分组头 → ``$END``。
3. 第 1 行 ``;File <note> saved <time>``；第 2 行空行；第 3 行 ``$VERSION``。
4. 每段 = 段头 + 数据行 + **1 个空行**；``$DEADLOAD``/``$LIVELOAD`` 是分组头，
   其后**紧随**首个子段头（样本 L8104→L8105、L8933→L8934）。
5. 缩进即语法：记录行 4 空格、续行 7 空格、``EXR`` 续行 **8** 空格、
   ``$RIGID.SLABID`` 续行 **11** 空格。
6. ``$END`` 前 2 个空行、``$END`` 后 1 个空行（= 文件以 ``$END`` + CRLF 结尾，
   见 :data:`TAIL_NOTE` 与自检脚本里的字节级比对）。
7. ``$VERSION`` 段体 = ``   4.2.0``（**3** 空格）。
8. **行尾空白不写**（模板比对一律 ``rstrip()``）。

全局 ID（§j.3，**冻结**）：``ID = N × 100 + CC``，``N`` 从 1 连续发号，顺序 = 材料(10)
→ 框架截面(09) → 节点(07) → 线段/构件(08，``$NET.ID == $SETELEMENT.ID``) →
墙板截面(11) → 墙(05) → 板(06)；荷载**不发号**（§n-4：荷载不做）。

与 DLL 的已知差异（§j.8，**不得"改正"**）：段名与 KEY 名/顺序以 DLL 为准，
数值格式与空白布局以样本为准。本模块的自检脚本会把两侧证据都贴出来。
"""

from __future__ import annotations

import datetime
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

try:                                     # 直接运行 / 测试把 engine/ 加入 sys.path
    from canonical import Level, Member, Model, Section, Slab, TOL, Wall
except ImportError:                      # pragma: no cover - 作为包导入
    from .canonical import Level, Member, Model, Section, Slab, TOL, Wall

#: 段序（§j.2-2，13 段；荷载那一段在 §j.6 展开成 10 个空子段头）
SEGMENT_ORDER = ("$VERSION", "$DESIGNPARA", "$STORY", "$NODECOOR", "$NET",
                 "$DEFFRAMESECTION", "$DEFWASLABSECTION", "$DEFMATERIAL",
                 "$SETELEMENT", "$SETWALL", "$SETSLAB", "$RIGID")

#: ``$VERSION`` 段体（§j.2-7：**3** 个空格）
VERSION_BODY = "   4.2.0"

#: 荷载段：只写段头，体内为空（§j.6〔R2 §9.3：荷载不做〕）
LOAD_SEGMENT_BLOCK = (
    ("$DEADLOAD", ("$DEFNODELOAD", "$SETNODELOAD", "$DEFLINELOAD",
                   "$SETLINELOAD", "$DEFSLABLOAD", "$SETSLABLOAD")),
    ("$LIVELOAD", ("$DEFLINELOAD", "$SETLINELOAD", "$DEFSLABLOAD", "$SETSLABLOAD")),
)

#: 每种记录的 ID 类码（§j.3）
CC_MATERIAL = 10
CC_SECTION = 9
CC_NODE = 7
CC_ELEMENT = 8
CC_PANEL_SECTION = 11
CC_WALL = 5
CC_SLAB = 6

#: 构件类型 → ``$SETELEMENT.TYPE``（§j.4.5：1=柱、2=梁、3=支撑〔R2 冻结〕）
TYPE_OF_MEMBER = {"column": "1", "beam": "2", "brace": "3"}

#: 内置材料表（§j.9，取自样本 ``1_PM.pdt:2535-2539``；同名多定义时取被构件引用的那条）
BUILTIN_MATERIALS = {
    "C30":  {"type": 262, "es": 3e+04,   "pr": 0.2, "exc": 1e-05,  "ds": 25},
    "Q235": {"type": 261, "es": 2.1e+05, "pr": 0.3, "exc": 1e-05,  "ds": 78},
    "Q345": {"type": 261, "es": 2.1e+05, "pr": 0.3, "exc": 0.00012, "ds": 78.5},
}

#: 材料缺表时的兜底值（§j.7.5：**不得**猜钢号）
MATERIAL_FALLBACK = {"type": 262, "es": 3e+04, "pr": 0.2, "exc": 1e-05, "ds": 25}

#: 文件尾说明（§j.2-6 与样本字节的差异，逐字留痕，供报告引用）
TAIL_NOTE = ("$END 前 2 个空行；$END 后 1 个空行 = 文件最后 6 字节为 "
             "'$END\\r\\n'（样本 1_PM.pdt 实测 bytes[-8:] = b'\\r\\n$END\\r\\n'，"
             "契约 §j.2-6 写成 '$END\\r\\n\\r\\n' 是同一件事的两种记法——"
             "按样本，$END 行本身以 CRLF 结束即文件结束）")

#: 不可回算的截面统一写占位块（§j.7.1）
PLACEHOLDER_NOTE = ("截面不可回算 ⇒ 写 5 行占位块（数值全 0、M=mat、NAME=原名或 "
                    "<kind>#<params>、SHAPE=kind），引用它的构件照写（§j.7.1）")


@dataclass
class PdtOptions:
    """``write_pdt*`` 的选项（§j.1，**冻结**）。"""

    file_note: str = ""                # 首行 `;File <file_note> saved <time>`；缺省 = 输出文件绝对路径
    time_text: str = ""                # 时间文本；缺省 = 当前时间 "M/D/YYYY H:M:S"（无前导零）
    designpara: Optional[List[str]] = None   # 50×20 的原始文本（行=list[str]）；None ⇒ 全 0 占位
    materials: Optional[Dict[str, dict]] = None  # {材料名: {type,es,pr,exc,ds}}；None ⇒ 内置表
    skeleton: str = "full"             # "full" | "sections-only"
    brace_type: str = "3"              # 支撑的 $SETELEMENT.TYPE（§j.4.5 冻结为 3）
    rigid: bool = True                 # 是否写 $RIGID（False ⇒ 段头仍写、体内为空）
    floor_index_base: int = 1          # 层号起始（$STORY.ID / FLOORID 编号基准）


# ==========================================================================
# 数值/文本格式（§j.8：数值格式与空白以样本为准）
# ==========================================================================

def _fmt_f2(v) -> str:
    return "%.2f" % float(v)


def _fmt_f3(v) -> str:
    return "%.3f" % float(v)


def _fmt_g(v, prec: int) -> str:
    """C# 的 ``{x:G<n>}``：``%.nG`` 后把 ``E`` 换成小写（样本 ``3e+04``/``1e-05``/``2e+06``）。"""
    return (("%%.%dG" % prec) % float(v)).replace("E", "e")


def _num_str(v) -> str:
    """``$STORY`` 的 ``HI/BL/TL`` 与 ``ID`` 用的整数字面（样本全是整数）。"""
    f = float(v)
    if abs(f - round(f)) < 1e-9:
        return "%d" % int(round(f))
    return _fmt_g(f, 6)


def _g_e06(v) -> str:
    """节点 ``EXR`` 的 ``10012`` 值：``层号*1e6`` 的 G 形式（样本 ``2e+06``）。"""
    return _fmt_g(v, 2)


def _now_text() -> str:
    """样本首行的时间格式：``M/D/YYYY H:M:S``，**无前导零**（``3/19/2025 8:4:27``）。"""
    n = datetime.datetime.now()
    return "%d/%d/%d %d:%d:%d" % (n.month, n.day, n.year, n.hour, n.minute, n.second)


def _clean(text: str) -> str:
    """行尾空白不写（§j.2-8）；同时把行内的裸 CR/LF 去掉（防御）。"""
    return str(text).replace("\r", "").replace("\n", "").rstrip()


def _safe_name(text: str) -> Tuple[str, bool]:
    """把截面名放进 ``NAME=`` 时做最小净化，返回 ``(净化后, 是否改过)``。

    ``.pdt`` 用逗号分字段（``NAME=abc, SHAPE=1``）⇒ 名字里的逗号会破坏行式；
    ``=`` 会破坏 ``KEY=`` 的识别。占位块的 ``<kind>#<params>`` 名字天然含逗号，
    故替换成 ``;`` 并逐条记 warnings（不静默）。
    """
    out = str(text).replace(",", ";").replace("=", "-")
    return out, (out != str(text))


# ==========================================================================
# 小工具：段、行
# ==========================================================================

class _Seg:
    """一段的行缓冲：段头 + 数据行 + 1 个空行（§j.2-4）。"""

    def __init__(self, name: str):
        self.name = name
        self.lines: List[str] = [name]
        self.rows = 0                    # 数据行数（不含段头/空行）

    def add(self, line: str) -> None:
        self.lines.append(_clean(line))
        self.rows += 1

    def close(self) -> List[str]:
        return self.lines + [""]


def _exr_element_form(pairs: Sequence[Tuple[str, str]], cont_indent: int = 8,
                      per_line: int = 10) -> List[str]:
    """构件/墙板的 ``EXR`` 行式（样本 ``       EXR=19, -1004, 0.000, …``）。

    首行 ``       EXR=<k>`` + ``', <KEY>, <VAL>'``；每行最多 ``per_line`` 组，
    续行 ``cont_indent`` 个空格 + ``'<KEY>, <VAL>'``（§j.5）。
    """
    lines: List[str] = []
    k = len(pairs)
    head = "       EXR=%d" % k
    body = []
    for i, (key, val) in enumerate(pairs):
        chunk = "%s, %s" % (key, val)
        body.append(chunk)
    first = head + "".join(", " + b for b in body[:per_line])
    lines.append(_clean(first))
    rest = body[per_line:]
    for i in range(0, len(rest), per_line):
        lines.append(_clean(" " * cont_indent + ", ".join(rest[i:i + per_line])))
    return lines


def _exr_node_form(pairs: Sequence[Tuple[str, str]]) -> List[str]:
    """节点 ``EXR`` 行式（样本 ``       EXR= 2 ,10005, 2 ,10012, 2e+06``）。

    空白布局取自 DLL ``0x02029F``/``0x0202C1``（``EXI= {0} `` + ``,{0}, {1} ``）。
    """
    k = len(pairs)
    out = "       EXR= %d " % k + "".join(",%s, %s " % (key, val) for key, val in pairs)
    return [_clean(out)]


def _exi_element_form(rec_id: int, concrete: int, steel: int) -> str:
    """``       EXI=3, 10011, <id>, 10013, <混凝土等级>, 10014, <钢牌号>``（§j.5）。"""
    return _clean("       EXI=3, 10011, %d, 10013, %d, 10014, %d"
                  % (rec_id, concrete, steel))


def _exi_section_form(rec_id: int) -> str:
    """``       EXI=1, 10011, <id>``（§j.5）。"""
    return _clean("       EXI=1, 10011, %d" % rec_id)


def _material_grade(name: str) -> Tuple[int, int]:
    """材料名 → ``(10013 混凝土等级, 10014 钢牌号)``（§j.5 冻结）。

    ``C##`` → ``(##, 0)``；``Q###`` → ``(0, ###)``；认不出/空 → ``(30, 0)``。
    """
    s = (name or "").strip().upper()
    try:
        if s.startswith("C") and s[1:].isdigit():
            return int(s[1:]), 0
        if s.startswith("Q") and s[1:].isdigit():
            return 0, int(s[1:])
    except (IndexError, ValueError):      # pragma: no cover - 防御
        pass
    return 30, 0


# ==========================================================================
# 截面：向 sectionlib（§k.3）要 5 行块
# ==========================================================================

def _load_sectionlib():
    """惰性 import ``sectionlib``（§k.3 的 ``encode_defframesection`` 是唯一实现）。"""
    try:
        import sectionlib                # type: ignore
        return sectionlib
    except ImportError:
        try:                             # 作为包导入时
            from . import sectionlib     # type: ignore
            return sectionlib
        except ImportError:
            return None


def _synth_section_name(section: Section) -> str:
    """``$DEFFRAMESECTION`` 第 1 行 ``NAME=`` 的补名（只在 ``.jwd`` 那边没有名字时用）。

    * ``Kind=1`` → ``矩<B>X<H>``：契约 §e.1 **候选键 4** 明确「`.pdt` 里混凝土矩形叫
      `矩750X750/矩300X600`」（样本 ``1_PM.pdt:2367`` ``NAME=矩750X750``）；
    * ``Kind=3`` → ``圆形<d>``：样本 ``1_PM.pdt:2387`` ``ID=1009, NAME=圆形4800, SHAPE=3``
      配 ``KIND=3, B1=4800``（= 直径，``pdt_format.md`` §5.3；契约 §0.4-1 的证据③同源）
      ⇒ 格式为【事实】的**推广**（其它直径未观测）。

    其它 Kind 一律不补（不猜）。
    """
    if section.name:
        return section.name
    dims = section.dims or {}
    if section.kind == 1:
        b = dims.get("B", dims.get("B1"))
        h = dims.get("H", dims.get("H1"))
        if b is not None and h is not None:
            return "矩%sX%s" % (_num_str(b), _num_str(h))
    if section.kind == 3:
        d = dims.get("d", dims.get("B1"))
        if d is not None:
            return "圆形%s" % _num_str(d)
    return ""


def _rec_with_name(rec, section: Section, warnings: List[str]):
    """给 ``rec`` 补上 ``pkpm_name``（不改 sectionlib 的对象：``dataclasses.replace`` 复制一份）。"""
    name = _synth_section_name(section)
    if not name or getattr(rec, "pkpm_name", ""):
        return rec
    try:
        import dataclasses
        return dataclasses.replace(rec, pkpm_name=name)
    except Exception as exc:              # pragma: no cover - SectionRec 不是 dataclass 时
        warnings.append("无法给截面 %s 的 rec 补 NAME=%r（%s）" % (section.id, name, exc))
        return rec


def _build_rec_from_section(section: Section):
    """**兜底**：``sectionlib.rec_from_section`` 不可用时，按 §k.1 的字段直填一个 SectionRec。

    正常路径**不用**它（§b.5：不得另起一套）——5 行块与 ShapeVal 编解码始终由
    ``sectionlib`` 提供；这里只做数据搬运，且只在 sectionlib 缺 ``rec_from_section`` 时触发。
    """
    lib = _load_sectionlib()
    if lib is None:
        return None
    name = section.name or ""
    try:
        return lib.SectionRec(
            key=name or str(section.id), pkpm_name=name, family_code=0,
            family_name_cn="", kind=int(section.kind or 0), shapeval=section.shapeval or "",
            dims=dict(section.dims or {}), mat=(section.mat if section.mat in (5, 6) else 5),
            pdms_spec_path="", pdms_catalogue="", is_parametric=False, params=[],
            confidence="unknown", source="pdt_write-fallback",
            extra={"pdt_write_id": section.id})
    except Exception:                    # pragma: no cover - sectionlib 未就绪/签名不符
        return None


def _rec_from_table(lib, table, section: Section):
    """从 ``SectionTable`` 里找与该 Section 对应的 rec（按 id → 名字 → dims 兜底）。"""
    if table is None:
        return None
    try:
        for r in table.recs:
            extra = r.extra or {}
            for key in ("jwd_id", "pdt_id", "pdt_write_id"):
                if str(extra.get(key, "")) == str(section.id):
                    return r
    except AttributeError:
        return None
    try:
        if section.name:
            r = table.get(pkpm_name=section.name)
            if r is not None:
                return r
    except Exception:                    # pragma: no cover - get() 签名/实现差异
        pass
    return None


def _section_block(section: Section, sec_id: int, lib, table,
                   skipped: List[dict], warnings: List[str]) -> List[str]:
    """产出一个 ``$DEFFRAMESECTION`` 记录块（5 行 + EXI 行）。

    路径（§j.4.7/§k.3，**单实现**）：

    1. 取 rec：优先 ``SectionTable`` 里按 id/名字匹配到的那条（``table_from_jwd/table_from_pdt``
       的产物）；否则用 ``sectionlib.rec_from_section``（公开的 Section→SectionRec 转换）；
       都没有 ⇒ 兜底直填 + 记 warnings。
    2. ``sectionlib.encode_defframesection(rec, sec_id, mat, notes=warnings)``；
    3. 抛 ``unencodable`` ⇒ 记 ``skipped`` 并改用 ``sectionlib.placeholder_defframesection``
       （§j.7.1 的 5 行占位块）；连它也不可用时才用本模块的字面占位块（**只在不猜**的前提下）。
    """
    mat = section.mat if section.mat in (5, 6) else 5
    rec = None
    if lib is not None:
        rec = _rec_from_table(lib, table, section)
        if rec is None and hasattr(lib, "rec_from_section"):
            try:
                rec = lib.rec_from_section(
                    section, table=("pdt" if (table is not None or
                                              (section.table == "pdt")) else "jwd"))
            except Exception as exc:
                warnings.append("sectionlib.rec_from_section 抛 %s: %s；改用兜底直填"
                                % (type(exc).__name__, exc))
        if rec is None:
            rec = _build_rec_from_section(section)
        if rec is not None:
            rec = _rec_with_name(rec, section, warnings)
    if rec is not None:
        try:
            try:
                block = lib.encode_defframesection(rec, sec_id, mat, notes=warnings)
            except TypeError:            # sectionlib 的签名没有 notes（旧版本）
                block = lib.encode_defframesection(rec, sec_id, mat)
            if block:
                return [b if isinstance(b, str) else str(b) for b in block]
        except ValueError as exc:        # §k.3：其它 Kind 抛 ValueError('unencodable')
            reason = "encode_defframesection 抛 ValueError: %s" % exc
            if "unencodable" in str(exc).lower():
                skipped.append({"what": "section-shapeval", "id": section.id,
                                "why": "Kind=%s 不可回算（%s）；写 5 行占位块"
                                       % (section.kind, reason)})
            else:
                warnings.append("截面 %s 回算异常（非 unencodable）：%s"
                                % (section.id, reason))
            try:
                ph = lib.placeholder_defframesection(rec, sec_id, mat)
                if ph:
                    return [b if isinstance(b, str) else str(b) for b in ph]
            except Exception as exc2:    # pragma: no cover
                warnings.append("sectionlib.placeholder_defframesection 也不可用：%s"
                                % exc2)
    else:
        why = "sectionlib 不可用（§k.3 的 encode_defframesection 是唯一实现）"
        skipped.append({"what": "section-shapeval", "id": section.id,
                        "why": why + "；写 5 行占位块"})
        if not any("sectionlib 不可用" in w for w in warnings):
            warnings.append("sectionlib 不可用：全部截面按 §j.7.1 写占位块"
                            "（几何仍完整，PDMS 规格需另行决定）")

    # ---- 最后兜底：字面占位块（§j.7.1：数值全 0、M=mat、NAME=原名或 <kind>#、SHAPE=kind）
    name, changed = _safe_name(section.name or "%s#" % section.kind)
    if changed:
        warnings.append("占位块 NAME 含逗号/等号，已替换为 ';'/'-'：%r -> %r"
                        % (section.name, name))
    return [
        _clean("    ID=%d, NAME=%s, SHAPE=%s" % (sec_id, name, section.kind)),
        _clean("       KIND=%s, B1=0, B2=0, H1=0, H2=0, B3=0, H3=0" % section.kind),
        _clean("       T1=0, T2=0, T3=0, T4=0, T5=0, T6=0"),
        _clean("       M=%d, RI=0.000, RJ=0.000, UA=0.000, NAME1=" % mat),
        _exi_section_form(sec_id),
    ]


# ==========================================================================
# 主入口
# ==========================================================================

def write_pdt(model: Model, path: str, opts: Optional[PdtOptions] = None) -> dict:
    """规范模型 → ``.pdt``（§j.1）。返回报告字典（键固定，供 CLI 并入 report.json）。"""
    opts = opts or PdtOptions()
    if opts.skeleton not in ("full", "sections-only"):
        raise ValueError("skeleton 必须 ∈ {'full','sections-only'}，收到 %r" % opts.skeleton)

    warnings: List[str] = []
    skipped: List[dict] = []
    assumptions: List[str] = [
        "荷载不导出（R2 §9.3）：只写 $DEADLOAD/$LIVELOAD 及其子段头，体内为空（§j.6）",
        "EXR 只写最小自洽集（§j.5）：节点 10005/10012，构件与墙板 -41/-40/10005/10012；"
        "样本里的其它 EXR 键（-1004..-1001、-119、-84、-82、-73、-71、-67、-64、-63、-57、"
        "-44、-43、-42、10001..10003、10217）语义未证，未复刻",
        "ECS 写出规则（§0.4-10）：``Member.ecc`` 是 6 元组（= ``pdt_read`` 记录的原始 "
        "ECS1..ECE3，仅记录、未并入几何）时**原样写回**；.jwd 源的构件 canonical 的 "
        "start/end 已含偏心（§a.5）、且其 ecc 是 1/2 元组的不同语义 ⇒ ECS 一律 0.000"
        "（几何仍经 $NET 无损表达；旧申报对 .pdt 源不成立的理由已修正，R3 复核发现④）",
        "节点由构件端点、墙板回路顶点与 ``model.joints`` **合成**（canonical 没有节点对象，"
        "§j.3）：唯一性按 round(v,6) 归一；``FLOORID`` 优先用 Joint 自己的 Level，"
        "面板边与构件边几何重合时复用同一条 $NET",
        "``10012`` 的「层内序号」取 ``Member.no``（.jwd 的 PKPM 原编号）。"
        "**读回后不幂等**：``read_pdt`` 会按层内文件顺序重编 1..n，故 .pdt→.pdt 的第二遍"
        "只在 ``10012`` 的值上不同（构件类型/几何/包围盒不变，见自检脚本的字节级 diff）",
        "板洞与无厚度的「房间」、回路点 <3 的墙不写，逐条记 skipped（§j.7.3/§j.7.4）",
        "无名的 Kind=1 截面按 §e.1 候选键 4 的格式补 NAME=矩<B>X<H>（样本 1_PM.pdt:2367 "
        "`NAME=矩750X750`）；其它 Kind 不补名（不猜）",
        TAIL_NOTE,
        PLACEHOLDER_NOTE,
    ]

    # ---------------------------------------------------------------- 1) 分层与发号
    levels = model.sorted_levels()
    levels_by_key = {lv.key: lv for lv in levels}
    story_of: Dict[int, int] = {}
    for i, lv in enumerate(levels):
        story_of[lv.key] = int(opts.floor_index_base) + i
    out_of_range: Dict[float, int] = {}

    def level_for_z(z: float) -> Optional[Level]:
        """节点 Z → Level（floor 型按区间、plane 型按相等；下界优先，越界则夹到最近层）。"""
        best: Optional[Level] = None
        for lv in levels:
            if lv.z_bot - TOL <= z <= lv.z_top + TOL:
                if best is None or lv.z_bot < best.z_bot:
                    best = lv
        if best is None and levels:
            best = min(levels, key=lambda lv: min(abs(z - lv.z_bot), abs(z - lv.z_top)))
            key = round(float(z), 6)
            out_of_range[key] = out_of_range.get(key, 0) + 1
        return best

    # ---------------------------------------------------------------- 2) 材料
    declared: Dict[str, dict] = {}
    if opts.materials:
        for name, props in opts.materials.items():
            declared[str(name)] = dict(props)
    else:
        declared = {k: dict(v) for k, v in BUILTIN_MATERIALS.items()}
    used_names = sorted({m.material for m in model.members if m.material})
    for nm in used_names:
        if nm not in declared:
            declared[nm] = dict(MATERIAL_FALLBACK)
            warnings.append("材料 %r 不在 opts.materials 也不在内置表 ⇒ 用兜底值 %s（§j.7.5）"
                            % (nm, MATERIAL_FALLBACK))
    material_names = sorted(declared)
    material_ids: Dict[str, int] = {}

    panel_mat_name = ""
    for nm in material_names:                     # 板/墙的 MATID：第一个混凝土名（C 开头）
        if nm.upper().startswith("C"):
            panel_mat_name = nm
            break
    panel_mat_name = panel_mat_name or (material_names[0] if material_names else "")
    panel_mat = material_ids.get(panel_mat_name, 0)
    assumptions.append("板/墙的 MATID 取声明材料里第一个 C 开头的混凝土名（本模型 %r → ID %s）；"
                       "§j.4.11 只给模板 <mid>，canonical 的 Slab/Wall 无材料字段"
                       % (panel_mat_name, panel_mat))

    # ---------------------------------------------------------------- 3) 节点合成
    node_ids: Dict[Tuple[float, float, float], int] = {}

    def nkey(p) -> Tuple[float, float, float]:
        return (round(float(p[0]), 6), round(float(p[1]), 6), round(float(p[2]), 6))

    for m in model.members:                       # 构件端点
        node_ids.setdefault(nkey(m.start), 0)
        node_ids.setdefault(nkey(m.end), 0)
    level_hint: Dict[Tuple[float, float, float], int] = {}
    for j in model.joints.values():               # canonical 的节点也写（含孤立节点）
        k = nkey((j.x, j.y, j.z))
        node_ids.setdefault(k, 0)
        level_hint.setdefault(k, j.level)
    # 板：板洞不写（.pdt 的洞语义未证，不猜）；无厚度的"房间"也不写 —— 两者都逐条记 skipped（§j.7.3）
    slab_rows = []
    for s in sorted(model.slabs, key=lambda s: s.id):
        if s.is_hole:
            skipped.append({"what": "slab-hole", "id": s.id,
                            "why": "Slab.is_hole=True：.pdt 的板洞由 HOLEID 表达、语义未证，"
                                   "不猜（§j.7.3）"})
            continue
        if s.thickness <= TOL:
            skipped.append({"what": "slab-nothick", "id": s.id,
                            "why": "is_hole=False 且 thickness<=0 的「房间」不写 $SETSLAB（§j.7.3）"})
            continue
        slab_rows.append(s)
    # 墙：回路点 <3 不写（§j.7.4）
    wall_rows = []
    for w in sorted(model.walls, key=lambda w: w.id):
        if len(w.loop) < 3:
            skipped.append({"what": "wall-loop", "id": w.id,
                            "why": "Wall.loop 只有 %d 个点（<3），无法成环（§j.7.4）"
                                   % len(w.loop)})
            continue
        wall_rows.append(w)
    for s in slab_rows:
        for (x, y) in s.polygon:
            node_ids.setdefault(nkey((x, y, s.z)), 0)
    for w in wall_rows:
        for p in w.loop:
            node_ids.setdefault(nkey(p), 0)
    ordered_nodes = sorted(node_ids, key=lambda p: (p[2], p[1], p[0]))

    # -------------------------------------------------------------- 全局流水号
    # §j.3 / §0.4-10：ID = N×100+CC，N 是**全局唯一流水号**（样本 1..2841 跨类 0 复用，
    # pdt_format.md §3.2），发号顺序 = 材料(10) → 框架截面(09) → 节点(07) → 构件/线段(08，
    # 含面板环的附加 NET) → 墙板截面(11) → 墙(05) → 板(06)。旧实现按类别各自从 1 起号
    # （跨类复用 N），与样本和本模块 docstring 均不符（R3 复核发现①b）。
    all_sections = sorted(model.sections.values(), key=lambda s: s.id)
    gid = 1

    material_ids: Dict[str, int] = {}
    for nm in material_names:                     # ① 材料（10）
        material_ids[nm] = gid * 100 + CC_MATERIAL
        gid += 1

    section_ids: Dict[int, int] = {}
    for sec in all_sections:                      # ② 框架截面（09）
        section_ids[sec.id] = gid * 100 + CC_SECTION
        gid += 1

    for p in ordered_nodes:                       # ③ 节点（07）
        node_ids[p] = gid * 100 + CC_NODE
        gid += 1

    # ---------------------------------------------------------------- 4) 墙板截面
    thicknesses = sorted({round(s.thickness, 6) for s in slab_rows} |
                         {round(w.thickness, 6) for w in wall_rows if w.thickness > TOL})
    if any(w.thickness <= TOL for w in wall_rows):
        warnings.append("有墙的 thickness<=0：$DEFWASLABSECTION 的 T1 按 0.00 写出")
    panel_sec_id: Dict[float, int] = {}

    # ---------------------------------------------------------------- 5) 构件与线段
    members = sorted(model.members, key=lambda m: (
        story_of.get(m.level, 0), TYPE_OF_MEMBER.get(m.type, "9"), m.id))
    seq_by_level: Dict[int, int] = {}
    member_seq: Dict[int, int] = {}
    for m in members:
        if m.no and m.no > 0:
            member_seq[m.id] = m.no
        else:
            seq_by_level[m.level] = seq_by_level.get(m.level, 0) + 1
            member_seq[m.id] = seq_by_level[m.level]
    element_ids: Dict[int, int] = {}
    net_rows: Dict[int, Tuple[int, int]] = {}     # NET ID -> (起点节点, 终点节点)
    edge_lookup: Dict[Tuple[int, int], int] = {}  # 无序节点对 -> NET ID（先构件、后面板）
    panel_edges: Dict[Tuple[str, int], List[int]] = {}
    for m in members:                             # ④ 构件/线段（08）
        element_ids[m.id] = gid * 100 + CC_ELEMENT
        gid += 1
        a, b = node_ids[nkey(m.start)], node_ids[nkey(m.end)]
        net_rows[element_ids[m.id]] = (a, b)      # 一根构件的 $NET.ID 恒等于 $SETELEMENT.ID（§j.3）
        edge_lookup.setdefault((min(a, b), max(a, b)), element_ids[m.id])

    def _ring_edges(points: Sequence) -> List[int]:
        """闭合环的有序边（不重复首点）：返回 NET ID 列表。

        面板边与**已有**的线段（构件的 NET）几何相同时复用同一个 NET（面板边没有
        ``$SETELEMENT``，不会与构件抢 ID）；否则按 §j.3 的 08 类码续全局流水号。
        """
        nonlocal gid
        ids: List[int] = []
        n = len(points)
        for i in range(n):
            a = node_ids[nkey(points[i])]
            b = node_ids[nkey(points[(i + 1) % n])]
            key = (min(a, b), max(a, b))
            if key not in edge_lookup:
                nid = gid * 100 + CC_ELEMENT
                gid += 1
                edge_lookup[key] = nid
                net_rows[nid] = (a, b)
            ids.append(edge_lookup[key])
        return ids

    wall_ids: List[int] = []
    for i, w in enumerate(sorted(wall_rows, key=lambda w: w.id)):
        wall_ids.append(w.id)
        panel_edges[("wall", w.id)] = _ring_edges(w.loop)
    slab_ids: List[int] = []
    for i, s in enumerate(sorted(slab_rows, key=lambda s: s.id)):
        slab_ids.append(s.id)
        panel_edges[("slab", s.id)] = _ring_edges([(x, y, s.z) for (x, y) in s.polygon])

    for t in thicknesses:                         # ⑤ 墙板截面（11）
        panel_sec_id[t] = gid * 100 + CC_PANEL_SECTION
        gid += 1
    wall_net_ids: Dict[int, int] = {}
    for wid in wall_ids:                          # ⑥ 墙（05）
        wall_net_ids[wid] = gid * 100 + CC_WALL
        gid += 1
    slab_net_ids: Dict[int, int] = {}
    for sid in slab_ids:                          # ⑦ 板（06）
        slab_net_ids[sid] = gid * 100 + CC_SLAB
        gid += 1

    lib = _load_sectionlib()
    table = None
    if lib is not None and opts.skeleton == "full":
        fmt = (model.source_format or "").lower()
        try:
            if fmt == "pdt" and hasattr(lib, "table_from_pdt"):
                table = lib.table_from_pdt(model)
            elif hasattr(lib, "table_from_jwd"):
                table = lib.table_from_jwd(model)
        except Exception as exc:      # pragma: no cover - sectionlib 内部错误不该吞
            warnings.append("sectionlib.%s(model) 抛 %s: %s；改用逐 Section 组装 rec"
                            % ("table_from_pdt" if fmt == "pdt" else "table_from_jwd",
                               type(exc).__name__, exc))

    # ---------------------------------------------------------------- 7) 出段
    out: List[str] = []
    segments: Dict[str, int] = {}

    def emit(seg: _Seg) -> None:
        lines = seg.close()
        out.extend(lines)
        segments[seg.name] = seg.rows

    note = opts.file_note or os.path.abspath(path)
    out.append(_clean(";File %s saved %s" % (note, opts.time_text or _now_text())))
    out.append("")

    # $VERSION
    seg = _Seg("$VERSION")
    seg.add(VERSION_BODY)
    emit(seg)

    # $DESIGNPARA
    seg = _Seg("$DESIGNPARA")
    dp = opts.designpara
    if dp is None:
        dp = ["    " + ", ".join(["0.000"] * 20) for _ in range(50)]
        assumptions.append("$DESIGNPARA 未给定 ⇒ 写 50 行 × 20 个 '0.000' 占位（§j.4.3/§j.7.6）")
    elif len(dp) != 50:
        warnings.append("opts.designpara 有 %d 行（样本 50 行）；原样写出" % len(dp))
    for line in dp:
        seg.add(line)
    emit(seg)

    node_by_id = {v: k for k, v in node_ids.items()}
    node_level: Dict[int, Optional[Level]] = {}
    for nid, p in ((v, k) for k, v in node_ids.items()):
        hint = level_hint.get(p)
        node_level[nid] = (levels_by_key.get(hint) if hint is not None else None) \
            or level_for_z(p[2])
    if out_of_range:
        warnings.append("有 %d 个节点 Z 不在任何 Level 区间内（%s），其 FLOORID 夹到最近层；"
                        "floor 型 Level 的区间之外出现节点是样本 JLCJ2 的既有现象"
                        "（越层柱/夹层），$STORY 段仍按模型的 Level 原样写"
                        % (sum(out_of_range.values()), sorted(out_of_range)))

    if opts.skeleton == "full":
        # $STORY
        seg = _Seg("$STORY")
        for lv in levels:
            xs = [p[0] for p in ordered_nodes if node_level[node_ids[p]] is lv]
            ys = [p[1] for p in ordered_nodes if node_level[node_ids[p]] is lv]
            wide = (max(ys) - min(ys)) if ys else 0.0
            length = (max(xs) - min(xs)) if xs else 0.0
            spans = [abs(float(m.end[2]) - float(m.start[2]))
                     for m in members if m.level == lv.key]
            hei = max(spans) if spans else 0.0
            seg.add("    ID=%d, NUB=1" % story_of[lv.key])
            seg.add("       NO=1, HI=%s, BL=%s, TL=%s, WID=%s, LEN=%s, HEI=%s"
                    % (_num_str(lv.height), _num_str(lv.z_bot), _num_str(lv.z_top),
                       _fmt_f2(wide), _fmt_f2(length), _fmt_f2(hei)))
            if not xs:
                warnings.append("Level %s 没有任何节点：WID/LEN 写 0.00" % lv.stdflr_id)
        emit(seg)

        # $NODECOOR
        seg = _Seg("$NODECOOR")
        for p in ordered_nodes:
            nid = node_ids[p]
            lv = node_level[nid]
            fl = story_of.get(lv.key, 0) if lv is not None else 0
            seg.add("    ID= %d, X= %s, Y= %s, Z= %s, FLOORID= %d"
                    % (nid, _fmt_f2(p[0]), _fmt_f2(p[1]), _fmt_f2(p[2]), fl))
            for line in _exr_node_form([("10005", "%d" % fl),
                                        ("10012", _g_e06(fl * 1e6))]):
                seg.add(line)
        emit(seg)

        # $NET
        seg = _Seg("$NET")
        for nid in sorted(net_rows):
            a, b = net_rows[nid]
            seg.add("    ID=%d, NODES=%d, NODEE=%d" % (nid, a, b))
        emit(seg)

    # $DEFFRAMESECTION（两个 skeleton 都写）
    seg = _Seg("$DEFFRAMESECTION")
    slash_names = []
    for sec in all_sections:
        sid = section_ids[sec.id]
        for line in _section_block(sec, sid, lib, table, skipped, warnings):
            seg.add(line)
        if (sec.name or "").startswith("/"):
            slash_names.append(sec.name)
    if slash_names:
        warnings.append("有 %d 个截面的名字以 '/' 开头（如 %s）：.pdt 与 PKPM 的截面名都不带"
                        "前导 '/'（样本与匹配文件的左值均如此）⇒ 上游（如 "
                        "sectionlib 的 pkpm_name 来源/匹配文件逆查）可能多加了 '/'；"
                        "本模块按 §j.4.7 原样写出、不擅自改名，此处仅留痕"
                        % (len(slash_names), slash_names[:3]))
    emit(seg)

    if opts.skeleton == "full":
        # $DEFWASLABSECTION
        seg = _Seg("$DEFWASLABSECTION")
        for t in thicknesses:
            seg.add("    ID=%d, NAME=T%g, TYPE=1, T1=%s, T2=0.00"
                    % (panel_sec_id[t], t, _fmt_f2(t)))
        emit(seg)

        # $DEFMATERIAL
        seg = _Seg("$DEFMATERIAL")
        for nm in material_names:
            pr = declared[nm]
            seg.add("    ID=%d, NAME=%s, TYPE=%d, ES=%s, PR=%s, EXC=%s, DS=%s"
                    % (material_ids[nm], nm, int(pr.get("type", 261)),
                       _fmt_g(pr.get("es", 0.0), 2), _fmt_g(pr.get("pr", 0.0), 2),
                       _fmt_g(pr.get("exc", 0.0), 5), _fmt_g(pr.get("ds", 0.0), 5)))
        emit(seg)

        # $SETELEMENT
        seg = _Seg("$SETELEMENT")
        for m in members:
            fl = story_of.get(m.level, 0)
            mat_name = m.material if m.material in material_ids else panel_mat_name
            concrete, steel = _material_grade(mat_name)
            # ECS：.pdt 源（ecc=原始 6 元组，§0.4-10）原样写回；其余写 0.000（见 assumptions）
            if len(tuple(m.ecc or ())) == 6:
                ecs = [float(v) for v in m.ecc]          # ECS1..3, ECE1..3
            else:
                ecs = [0.0] * 6
            seg.add("    ID=%d, TYPE=%s, NETID=%d, SECTID=%d, MATID1=%d, MATID2=-9999, "
                    "ECS1=%s, ECS2=%s, ECS3=%s, ECE1=%s, ECE2=%s, "
                    "ECE3=%s, ANG=%s"
                    % (element_ids[m.id], TYPE_OF_MEMBER.get(m.type, opts.brace_type),
                       element_ids[m.id], section_ids.get(m.section, 0),
                       material_ids.get(mat_name, 0),
                       _fmt_f3(ecs[0]), _fmt_f3(ecs[1]), _fmt_f3(ecs[2]),
                       _fmt_f3(ecs[3]), _fmt_f3(ecs[4]), _fmt_f3(ecs[5]),
                       _fmt_f3(m.rotation)))
            seg.add(_exi_element_form(element_ids[m.id], concrete, steel))
            pairs = [("-41", _fmt_f3(int(TYPE_OF_MEMBER.get(m.type, "0")))),
                     ("-40", _fmt_f3(fl)), ("10005", _fmt_f3(fl)),
                     ("10012", _fmt_f3(fl * 1e6 + member_seq.get(m.id, 0)))]
            for line in _exr_element_form(pairs):
                seg.add(line)
        emit(seg)

        # $SETWALL / $SETSLAB
        for tag, rows, ids_map, type_code in (
                ("$SETWALL", [w for w in sorted(wall_rows, key=lambda w: w.id)],
                 wall_net_ids, 5),
                ("$SETSLAB", [s for s in sorted(slab_rows, key=lambda s: s.id)],
                 slab_net_ids, 6)):
            seg = _Seg(tag)
            for obj in rows:
                netids = panel_edges[("wall" if type_code == 5 else "slab", obj.id)]
                z = float(obj.z_bot) if type_code == 5 else float(obj.z)
                lv = level_for_z(z)
                fl = story_of.get(lv.key, 0) if lv is not None else 0
                t = round(float(obj.thickness), 6)
                concrete, steel = _material_grade(panel_mat_name)
                seg.add("    ID=%d, TYPE=%d, SECTID=%d, MATID=%d, MATID2=0, "
                        "HOLEID=-9999, EC=0.0"
                        % (ids_map[obj.id], type_code, panel_sec_id.get(t, 0),
                           panel_mat))
                seg.add("       NUB=%d, NETID= %s" % (len(netids),
                                                      ", ".join(str(x) for x in netids)))
                seg.add(_exi_element_form(ids_map[obj.id], concrete, steel))
                pairs = [("-41", "%d" % type_code), ("-40", "%d" % fl),
                         ("10005", "%d" % fl), ("10012", _g_e06(fl * 1e6))]
                for line in _exr_element_form(pairs):
                    seg.add(line)
            emit(seg)

        # $RIGID
        seg = _Seg("$RIGID")
        if opts.rigid:
            for lv in levels:
                mine = [s for s in sorted(slab_rows, key=lambda s: s.id)
                        if (level_for_z(s.z) is lv)]
                if not mine:
                    continue
                seg.add("    ID=%d, FLOORID=%d, NUB=%d"
                        % (story_of[lv.key], story_of[lv.key], len(mine)))
                vals = [str(slab_net_ids[s.id]) for s in mine]
                for i in range(0, len(vals), 20):
                    chunk = ", ".join(vals[i:i + 20])
                    seg.add(("       SLABID= " + chunk) if i == 0
                            else (" " * 11 + chunk))
        else:
            assumptions.append("opts.rigid=False ⇒ $RIGID 段头照写、体内为空")
        emit(seg)

    # 荷载：只写段头（§j.6）
    for group, subs in LOAD_SEGMENT_BLOCK:
        out.append(group)
        for sub in subs:
            out.append(sub)
            out.append("")
    out.append("")
    out.append("$END")
    out.append("")

    text = "\r\n".join(out)
    data = text.encode("gbk")            # 先编码再写（§g-3；失败即报错）
    with open(path, "wb") as fh:
        fh.write(data)

    # ---- 回读校验（§j.2-1）
    back = open(path, "rb").read()
    try:
        back.decode("gbk")
    except UnicodeDecodeError as exc:    # pragma: no cover - 不可能发生（刚编码过）
        raise ValueError(".pdt 回读校验失败（GBK 不可解）：%s" % exc)
    bare = back.count(b"\n") - back.count(b"\r\n")
    if bare:
        raise ValueError(".pdt 回读校验失败：发现 %d 个裸 \\n（必须全 CRLF）" % bare)

    return {
        "segments": segments,
        "rows": len(out) + 1,            # +1 = CRLF 切分后的「末尾幽灵行」（样本 9678 同口径）
        "ids": {"materials": len(material_names), "sections": len(all_sections),
                "joints": len(ordered_nodes), "members": len(members),
                "panels": len(slab_ids) + len(wall_ids)},
        "skipped": skipped,
        "warnings": warnings,
        "assumptions": assumptions,
    }


def write_pdt_sections(sections: dict, path: str,
                       opts: Optional[PdtOptions] = None) -> dict:
    """``sections`` 字典 → ``.pdt``（**db2pdt 的唯一入口**，§j.1/§j.7.6）。

    ``sections = {"beam": [Section, …], "col": […], "brace": […]}``（canonical
    :class:`Section`，``kind``/``mat``/``name``/``dims``/``shapeval`` 已由 ``sectionlib``
    填好）。``skeleton="full"``（缺省）⇒ 写全 13 段，但除 ``$DEFFRAMESECTION`` 外
    几何段只有段头与空行（空段是合法的，Add-in 按 KEY 解析）；``"sections-only"``
    ⇒ 只写 首行 + ``$VERSION`` + ``$DESIGNPARA`` + ``$DEFFRAMESECTION`` + ``$END``。
    """
    opts = opts or PdtOptions()
    if opts.skeleton not in ("full", "sections-only"):
        raise ValueError("skeleton 必须 ∈ {'full','sections-only'}，收到 %r" % opts.skeleton)

    warnings: List[str] = []
    skipped: List[dict] = []
    assumptions: List[str] = [
        "db2pdt：$DEFFRAMESECTION 由 sectionlib.encode_defframesection 回算（§k.3/§l.6）",
        "db2pdt：其余几何段只有段头与空行（0 条记录），$SETELEMENT 空段是合法的（§j.7.6）",
        "荷载不导出（R2 §9.3）：只写段头（§j.6）",
        "EXR 只写最小自洽集（§j.5）",
        PLACEHOLDER_NOTE,
    ]
    order = (("beam", "beam"), ("col", "col"), ("brace", "brace"))
    secs: List[Section] = []
    for key, _ in order:
        for s in (sections or {}).get(key, []) or []:
            secs.append(s)
    dup = {}
    for s in secs:
        dup[s.id] = dup.get(s.id, 0) + 1
    for sid, n in sorted(dup.items()):
        if n > 1:
            warnings.append("sections 里 id=%s 出现 %d 次（按出现顺序各写一条记录）"
                            % (sid, n))

    # §0.4-10（R3 复核发现⑤）：**同一截面身份（Section.id）只写一条记录** —— to_jwd_sections
    # 把 Kind=303 等同时放进 col+brace 两表（同一 Section 对象、同一 id），逐条各写会在 .pdt 里
    # 产生重复定义（实测旧产物 1,883 条记录里 876 组是同体复制）；样本的截面名唯一。
    # 注意按 **id** 而不是 (NAME,SHAPE) 去重：不同 Section 对象可能共用占位名（如 .jwd 里
    # 两条同尺寸无名焊接 H 都渲染成 "2#"），它们是不同截面、必须各自保留。
    lib = _load_sectionlib()
    seen_ids: set = set()
    blocks: List[str] = []
    n_dup = 0
    for i, s in enumerate(secs, 1):
        if s.id in seen_ids:
            n_dup += 1
            continue
        seen_ids.add(s.id)
        sid = i * 100 + CC_SECTION
        blocks.extend(_section_block(s, sid, lib, None, skipped, warnings))
    if n_dup:
        warnings.append(
            "db2pdt：按截面身份（Section.id）去重，少写 %d 条重复的 $DEFFRAMESECTION 记录"
            "（同一截面在 col/brace 两表各出现一次所致，§0.4-10）" % n_dup)

    out: List[str] = []
    segments: Dict[str, int] = {}

    def emit(name: str, lines: List[str]) -> None:
        seg = _Seg(name)
        for l in lines:
            seg.add(l)
        out.extend(seg.close())
        segments[name] = seg.rows

    out.append(_clean(";File %s saved %s"
                      % (opts.file_note or os.path.abspath(path),
                         opts.time_text or _now_text())))
    out.append("")
    emit("$VERSION", [VERSION_BODY])
    dp = opts.designpara
    if dp is None:
        dp = ["    " + ", ".join(["0.000"] * 20) for _ in range(50)]
        assumptions.append("$DESIGNPARA 未给定 ⇒ 写 50 行 × 20 个 '0.000' 占位（§j.4.3）")
    emit("$DESIGNPARA", list(dp))

    if opts.skeleton == "full":
        # 段序按 §j.2-2 的 SEGMENT_ORDER（§0.4-10，R3 复核发现①a：旧实现把
        # $DEFFRAMESECTION 提到 $STORY 之前）；空段是合法的（Add-in 按 KEY 解析）
        for name in ("$STORY", "$NODECOOR", "$NET"):
            emit(name, [])
    emit("$DEFFRAMESECTION", blocks)

    if opts.skeleton == "full":
        for name in ("$DEFWASLABSECTION", "$DEFMATERIAL", "$SETELEMENT",
                     "$SETWALL", "$SETSLAB", "$RIGID"):
            emit(name, [])
        for group, subs in LOAD_SEGMENT_BLOCK:
            out.append(group)
            for sub in subs:
                out.append(sub)
                out.append("")
    out.append("")
    out.append("$END")
    out.append("")

    text = "\r\n".join(out)
    data = text.encode("gbk")
    with open(path, "wb") as fh:
        fh.write(data)
    back = open(path, "rb").read()
    back.decode("gbk")
    if back.count(b"\n") - back.count(b"\r\n"):
        raise ValueError(".pdt 回读校验失败：发现裸 \\n（必须全 CRLF）")

    return {
        "segments": segments,
        "rows": len(out) + 1,
        "ids": {"materials": 0, "sections": len(secs), "joints": 0,
                "members": 0, "panels": 0},
        "skipped": skipped,
        "warnings": warnings,
        "assumptions": assumptions,
    }
