# -*- coding: utf-8 -*-
"""PKPM2PDMS导入导出 —— 命令行入口（契约 ``spec/CONTRACT.md`` v2.0 的 §(f)/§(h)/§(m)）。

v1 的三条（§f.1，**签名不变**）::

    python PKPM2PDMS导入导出/engine/cli.py jwd2pdms <jwd> --out <macro.mac>
            [--secmap F] [--extra F] [--project N] [--base E N U] [--angle D] [--unit mm] [--report R.json]
    python PKPM2PDMS导入导出/engine/cli.py pdms2jwd <dump.txt> --out <out.jwd>
            [--secmap F] [--dump-unit mm] [--report R.json]
    python PKPM2PDMS导入导出/engine/cli.py pdt2model <pdt> --out <model.json> [--report R.json]

R2 追加的九条（§m.1 的命令矩阵，参数名与缺省逐字对应）::

    pdt2pdms  <pdt>  --out <macro.mac>   [v1 §f.1 的全部选项，pdt 代替 jwd]
    pdms2pdt  <dump> --out <out.pdt>     [--dump-unit mm] [--report R.json] [--skeleton full|sections-only]
    jwd2db    <jwd>  --out <db.mac>      [--secmap F] [--extra F] [--report R.json]
                                         [--suffix S] [--clean] [--catalogue-user N] [--catalogue-stss N]
    pdt2db    <pdt>  --out <db.mac>      [同 jwd2db]
    db2jwd    <db.macro> --out <out.jwd> [--secmap F] [--report R.json]
    db2pdt    <db.macro> --out <out.pdt> [--secmap F] [--report R.json] [--skeleton full|sections-only]
    jwd2pdt   <jwd>  --out <out.pdt>     [--secmap F] [--extra F] [--report R.json] [--skeleton full|sections-only]
    pdt2jwd   <pdt>  --out <out.jwd>     [--secmap F] [--report R.json]
    dbsections <db.macro|--from-builtin> --out <F.csv|F.json>
                                         [--format csv|json] [--report R.json] [--secmap F]

R6 追加的一条（用户实机反馈问题③：窗体下拉收敛为三项，第一项要"自动识别"）::

    auto2pdms <src>  --out <macro.mac>   [与 jwd2pdms **逐项相同**的选项]

R7〔2026-09-28 用户确认的命名方案〕：三个建模型命令（``jwd2pdms``/``pdt2pdms``/``auto2pdms``）
各增一个选项 ``--site-name N``（= ``--request`` 协议里的 ``site_name`` 键）：

* **SITE 名由 .NET 侧探测**：执行前用 ``DbElement.GetElement("/候选名")`` 逐个试
  ``/PKPM2PDMS`` → ``/PKPM2PDMSre`` → ``/PKPM2PDMSre2`` …（上限 re99），试出第一个可用的
  再传给引擎；**静默、零弹窗**；
* 引擎**只按传入值创建 SITE**：不生成候选名、不做 re 逻辑、缺失即码 2（不自行默认）；
* 中间层名（ZONE/STRU/FRMW/SBFR）= ``<SITE名>_<段>``，含层号 ⇒ **全宏唯一**（生成期查重，
  重复即生成失败）；底层 SCTN/PANE/STWALL 一律 **unnamed** 创建（PDMS 自动分配系统名）；
* 宏头 ``ONERROR CONTINUE``、宏尾 ``$S+  -- Synonym translation ON`` + 分隔线，
  **没有** LABEL/handle 错误块；宏内**零** ``!!pkpm2pdms*`` 调用、**零** ``$M`` 预载
  （``pkpm2pdmsuniquename*.pmlfnc`` 系列不再部署、不再被引用）；
* 报告：``renames`` 语义变为 **SITE 名探测结果**（.NET 传入什么就记什么），
  另加 ``options.site_name``、``stats.used_names``/``used_names_count``、``stats.unnamed_count``。

``auto2pdms`` 按**文件头**判定走 ``jwd2pdms`` 还是 ``pdt2pdms``（前 16 字节
``SQLite format 3`` ⇒ jwd；否则按文本解码 GBK/UTF-8 后命中 ``$VERSION``/``$NODECOOR``
或首个非空行以 ``;File`` 开头 ⇒ pdt；两者都不像 ⇒ 码 2 报错，**不猜**），
判定后内部调用那两个 **同一个执行函数**（不复制逻辑，§f.3 的纪律）。

退出码（§f.2 冻结，v2 不新增码）：``0`` 成功 / ``1`` 未捕获异常（打印 traceback）/
``2`` 参数或输入文件错误 / ``3`` ``Model.validate()`` 出现 ``E-``（**不写产物**）。
``db2jwd``/``db2pdt`` 的"不可闭环节点 / 不可反算族"**不是**错误 ⇒ 退出 0 + 报告列出（§l.6）。

本模块同时是 GUI 的执行后端（§f.3：「逻辑必须复用 cli.py 里的同一个执行函数」）：
所有 ``run_*`` 函数**不打印任何东西**，只返回 :class:`RunResult`（含 ``lines`` 摘要、
报告 dict、产物路径、未解析清单）；``main()`` 把 ``RunResult.lines`` 打到 stdout，
``gui.py`` 把它显示在文本框里。

与契约的贴合点
--------------
* ``report.json`` 的键与层次照 §h 的模板；``counts`` **只**取 ``Model.counts()``（§h 明令）；
  ``geometry_anomalies`` 含 ``Model.validate()`` 的全部 ``W-`` 项（原文照抄）+ 逐条非零偏心
  （§a.2）；``sections.detail`` 覆盖每个被用到的截面，``sections.unresolved`` 是其子集。
* §m.3 的 ``report.db`` **7 键齐全**（``macro_source``/``generated``/``parsed``/``cross_check``/
  ``closure``/``losses``/``safety``）；缺席方向写 ``null``（**不得省略键**）。
* ``Model.notes``（§a.9 的唯一回流通道）全量并入 ``report.warnings``，并按既定前缀整理出
  ``report.skipped`` 的结构化条目——原文始终留在 ``warnings`` 里，两处都能查到。
* 截面解析只有一条路（§b.1 纪律 1 / §e.6）：一律 ``SectionMap.resolve()``。

对**调用方**的修正（模块间接口缺口，逐条记进交付说明的 openIssues）
----------------------------------------------------------------
1. ``pdms_dump.parse_dump(text)`` 没有接受"缺省单位"的入口 ⇒ 仅在 dump **确实没有**
   ``UNITS`` 行且 ``--dump-unit != mm`` 时，把 ``UNITS <单位>`` 插在头部行之后再交给它
   （不修改任何模块，也不改变"有 ``UNITS`` 行时以该行为准"的语义）。
2. ``pdt2model`` 的冻结签名里没有 ``--secmap``（§f.1），而 §h 要求报告含截面清单 ⇒ 在
   "与 .pdt 同目录存在匹配文件"时用它生成报告里的截面状态（**不参与** model.json 生成）。
3. ``sectionlib.table_from_jwd/table_from_pdt`` 只用 ``pkpm_name`` 查内置转化表；内置表没有的
   截面（含**名字为空**的那批）拿不到 ``pdms_spec_path`` ⇒ ``jwd2db``/``pdt2db`` 会漏掉它们。
   CLI 在拿到表之后按 §e.6 的**唯一路径** ``secmap.resolve()`` 补齐（``resolved`` 直接落规格；
   ``parametric`` 落参数化族并补 DESP 参数名/默认值；``inferred``/``unresolved`` 记报告），
   并把这批记录标 ``source='…+secmap'``。
4. 板/墙厚度的缺口（§l.3.6）由 CLI 补成 ``SectionRec``（``Section.for_panel`` + ``secmap``）——
   ``table_from_*`` 只处理 ``model.sections``，模型里没有"板厚截面"这种对象。
5. ``pdt2jwd`` 走 ``pdt_read`` → ``write_jwd``：``.pdt`` 的 ``Section.dims`` 是**文件字段名**
   （``B1/H1/T1…``，§b.4），而 ``write_jwd`` 吃 §a.4 的键空间 ⇒ CLI 用
   ``table_from_pdt`` 的折算规则把它换成 ``B/H``、``d``（``Kind=39`` 的 ``tf/tw`` 在 ``.pdt``
   里恒 0，**不从目录宏补**——§9.1 明令两条链路不绕道互转，缺就是缺，进报告）。
6. 报告 ``source_format='pdmsdb'`` 表示输入是 PDMS 目录/规格宏（§a.2 的 ``Model.source_format``
   词表没有该输入类型；``Model`` 侧从不使用这个值，只在报告里出现，已写进 ``assumptions``）。

本文件只依赖标准库与 ``engine/`` 内的兄弟模块（契约 §b.5）。
"""

from __future__ import annotations

import argparse
import codecs
import json
import os
import re
import sqlite3
import sys
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:               # 直接运行 cli.py，或作为 engine.cli 导入
    sys.path.insert(0, _HERE)           # 统一用绝对导入 ⇒ 全进程只有一份模块实例
                                        # （pdms_dump.py 等兄弟模块内部就是绝对导入）

import canonical as C                                      # noqa: E402
import dbmacro                                             # noqa: E402
import dbparse                                             # noqa: E402
import jwd_read                                            # noqa: E402
import jwd_write                                           # noqa: E402
import macgen                                              # noqa: E402
import pdms_dump                                           # noqa: E402
import pdt_read                                            # noqa: E402
import pdt_write                                           # noqa: E402
import secmap as secmap_mod                                # noqa: E402
import sectionlib                                          # noqa: E402

__all__ = ["RunResult", "InputError", "ModelError", "main", "build_parser",
           "run_jwd2pdms", "run_pdms2jwd", "run_pdt2model",
           "run_pdt2pdms", "run_pdms2pdt", "run_jwd2pdt", "run_pdt2jwd",
           "run_jwd2db", "run_pdt2db", "run_db2jwd", "run_db2pdt", "run_dbsections",
           "run_auto2pdms", "detect_source_format",
           "build_section_report",
           "EXIT_OK", "EXIT_EXCEPTION", "EXIT_INPUT", "EXIT_MODEL",
           "CATEGORIES", "CATEGORY_CN", "DEFAULT_SECMAP_NAME", "TOOLS"]

# --------------------------------------------------------------------------
# 常量（契约 §f.1/§f.2）
# --------------------------------------------------------------------------

EXIT_OK = 0
EXIT_EXCEPTION = 1
EXIT_INPUT = 2
EXIT_MODEL = 3

#: §m.1 的子命令全集（v1 三条 + R2 九条；顺序与 §m.1 的表一致）
#: 〔R6〕末尾追加 ``auto2pdms``（自动识别 .jwd/.pdt；参数与 jwd2pdms 逐项相同），
#: 追加在**末尾**以免改动 §m.1 既有的顺序（`metavar` 与错误提示都用这个元组）。
TOOLS = ("jwd2pdms", "pdt2pdms", "pdms2jwd", "pdms2pdt",
         "jwd2db", "pdt2db", "db2jwd", "db2pdt",
         "jwd2pdt", "pdt2jwd", "dbsections", "pdt2model",
         "auto2pdms")

#: 走"规范模型 → PDMS 建模型宏"的命令（macgen）
PDMS_MACRO_TOOLS = ("jwd2pdms", "pdt2pdms")

#: 走"唯一名/清场"选项的数据库生成命令（§l.2）
DB_GEN_TOOLS = ("jwd2db", "pdt2db")

#: 走目录宏解析 → 反算的命令（§l.5/§l.6）
DB_PARSE_TOOLS = ("db2jwd", "db2pdt")

#: 数据库方向 → §k.5 的信息损失申报方向（四个方向一一对应）
LOSS_DIRECTION = {"jwd2db": "jwd2db", "pdt2db": "pdt2db",
                  "db2jwd": "db2jwd", "db2pdt": "db2pdt"}

#: §e.3 的两个用户参数化族的 DESP 顺序（补齐 parametric 记录时用它命名 DESP 参数）
FAMILY_DESP_ORDER = {
    "/USER_RECT-SPEC/Rectangle_Profile": ("B", "H"),
    "/USER_H-SPEC/H_Profile": ("B1", "B2", "H", "Tw", "T1", "T2"),
}

#: §j.1 的 skeleton 取值
SKELETONS = ("full", "sections-only")

#: §f.1：``--secmap`` 省略时，取与主输入文件同目录的这个名字
DEFAULT_SECMAP_NAME = "PKPM转PDMS截面匹配文件.txt"

#: §f.1：``--project`` 取不到工程名时的缺省值（= macgen.MacOptions.project 的缺省）
DEFAULT_PROJECT = "PKPM_PROJECT"

#: §e.6：构件类别 -> SectionMap.resolve 的 kind
SECTION_KIND = {"beam": "beam", "column": "col", "brace": "brace"}

#: GUI 的"构件类别勾选"（§f.3；CLI 无此选项，见本文件头部说明）
CATEGORIES = ("column", "beam", "brace", "slab", "wall")
CATEGORY_CN = {"column": "柱", "beam": "梁", "brace": "支撑",
               "slab": "板", "wall": "墙"}

#: stdout/GUI 摘要里最多逐条列出几个未解析截面（其余折叠成计数，报告里是全量）
UNRESOLVED_PRINT_LIMIT = 30

_NOTE_PROJECT_RE = re.compile(r"PROJECT_NAME=([^\s（(]+)")


class InputError(Exception):
    """参数 / 输入文件错误（§f.2 码 2：文件不存在、编码失败、dump 文法错误、匹配文件缺失）。"""


class ModelError(Exception):
    """``Model.validate()`` 出现 ``E-`` 项（§f.2 码 3：不写产物）。"""

    def __init__(self, issues: Sequence[str]):
        super().__init__("模型校验失败：%d 个 E- 项" % (len(issues),))
        self.issues = list(issues)


@dataclass
class RunResult:
    """一次执行的完整结果（CLI 的 stdout 与 GUI 的文本框**共用** ``lines``）。"""

    tool: str = ""
    ok: bool = False
    exit_code: int = EXIT_OK
    source: str = ""
    output: str = ""
    report_path: str = ""
    report: Dict[str, Any] = field(default_factory=dict)
    lines: List[str] = field(default_factory=list)     # 摘要（含未解析清单）
    errors: List[str] = field(default_factory=list)    # E- 项 / 异常（码 3 时另打 stderr）
    error: str = ""
    elapsed: float = 0.0

    def text(self) -> str:
        return "\n".join(self.lines)


# --------------------------------------------------------------------------
# 小工具
# --------------------------------------------------------------------------


def _default_report_path(out_path: str) -> str:
    """§f.1：``--report`` 省略 ⇒ ``<--out 同目录>\\<--out 基名>.report.json``。"""
    base = os.path.splitext(os.path.abspath(out_path))[0]
    return base + ".report.json"


def _ensure_parent(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)


def _write_report(path: str, report: Dict[str, Any]) -> str:
    """写 ``report.json``：UTF-8 无 BOM + LF（§g），返回路径。"""
    _ensure_parent(path)
    text = json.dumps(report, ensure_ascii=False, indent=1, sort_keys=False)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text + "\n")
    return path


def _resolve_secmap_path(explicit: Optional[str], source_path: str,
                         allow_missing: bool = False) -> Optional[str]:
    """§f.1 的 ``--secmap`` 缺省规则：与主输入同目录的 ``PKPM转PDMS截面匹配文件.txt``。"""
    if explicit:
        p = os.path.abspath(explicit)
        if not os.path.isfile(p):
            raise InputError("截面匹配文件不存在：%s（--secmap）" % (p,))
        return p
    cand = os.path.join(os.path.dirname(os.path.abspath(source_path)), DEFAULT_SECMAP_NAME)
    if os.path.isfile(cand):
        return cand
    if allow_missing:
        return None
    raise InputError("未找到与输入文件同目录的 %s：%s；请用 --secmap 指定（契约 §f.1）"
                     % (DEFAULT_SECMAP_NAME, os.path.dirname(os.path.abspath(source_path))))


def _load_secmap(path: Optional[str], extra: Optional[str]) -> Optional[secmap_mod.SectionMap]:
    """``SectionMap.load`` 的包装：模块异常一律翻成 :class:`InputError`（§f.2 码 2）。"""
    if path is None:
        return None
    try:
        # extra=None ⇒ 自动加载 engine/secmap_extra.txt（若存在）；给定则只加载它（§f.1/§e.4）
        return secmap_mod.SectionMap.load(path, extra_path=extra)
    except FileNotFoundError as exc:
        raise InputError(str(exc))
    except UnicodeDecodeError as exc:
        raise InputError("截面匹配文件解码失败（须 GBK，契约 §e.2/§g.1）：%s" % (exc,))
    except ValueError as exc:
        raise InputError(str(exc))
    except OSError as exc:
        raise InputError("读取截面匹配文件失败：%s" % (exc,))


def _project_from_notes(notes: Sequence[str]) -> str:
    """§b.2：``pkpmSysInfo.ID=2`` 的工程名由 ``read_jwd`` 以
    ``工程名候选 PROJECT_NAME=<名字> …`` 的 note 回流（notes 是唯一通道）。"""
    for n in notes:
        m = _NOTE_PROJECT_RE.search(n)
        if m:
            return m.group(1).strip()
    return ""


def _resolve(smap: Optional[secmap_mod.SectionMap], sec: C.Section,
             kind: str) -> C.Resolution:
    """截面解析（§e.1 四级优先级）——全项目**唯一**裁决者 ``SectionMap.resolve``（§e.6）。"""
    if smap is None:
        return C.Resolution(
            status=C.UNRESOLVED, pkpm_name=sec.name, source="none",
            reason="本次运行没有截面匹配文件（未给 --secmap，且输入同目录没有 %s）"
                   "：未做 PDMS 规格解析" % DEFAULT_SECMAP_NAME)
    try:
        res = smap.resolve(sec, kind)
    except Exception as exc:                       # 解析器异常不得让报告生成崩溃
        return C.Resolution(
            status=C.UNRESOLVED, pkpm_name=sec.name, source="none",
            reason="SectionMap.resolve(%s, %s) 抛出 %s: %s"
                   % (sec.id, kind, type(exc).__name__, exc))
    if not isinstance(res, C.Resolution):
        return C.Resolution(status=C.UNRESOLVED, pkpm_name=sec.name, source="none",
                            reason="SectionMap.resolve 返回 %r，不是 canonical.Resolution"
                                   % (type(res).__name__,))
    return res


def build_section_report(model: C.Model,
                         smap: Optional[secmap_mod.SectionMap]) -> Dict[str, Any]:
    """契约 §h 的 ``report.sections``：覆盖**每一个被用到的截面**（含板/墙厚度合成的）。

    返回 ``{resolved, parametric, unresolved, total, detail, unresolved}``；
    ``detail`` 的键与 §h 示例一致（``id/table/name/kind/status/source/pkpm_name/
    spec_path/desp_params/reason/used_by``）；``unresolved`` 是 ``detail`` 中
    ``status='unresolved'`` 的子集，并按 §h 的示例额外带上 ``candidate_keys``。
    """
    detail: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    owner: Dict[Tuple[Any, ...], Tuple[C.Section, str]] = {}

    def key_of(sec: C.Section, kind: str) -> Tuple[Any, ...]:
        dims = tuple(sorted((str(k), repr(v)) for k, v in (sec.dims or {}).items()))
        return (kind, sec.id, sec.table, sec.kind, sec.name, sec.shapeval, dims)

    def add(sec: C.Section, kind: str, used_by_key: str) -> None:
        k = key_of(sec, kind)
        if k in detail:
            d = detail[k]
            d["used_by"][used_by_key] = d["used_by"].get(used_by_key, 0) + 1
            return
        res = _resolve(smap, sec, kind)
        owner[k] = (sec, kind)
        detail[k] = {
            "id": sec.id, "table": sec.table, "name": sec.name, "kind": sec.kind,
            "status": res.status, "source": res.source, "pkpm_name": res.pkpm_name,
            "spec_path": res.spec_path, "desp_params": list(res.desp_params),
            "reason": res.reason, "evidence": res.evidence, "used_by": {used_by_key: 1},
        }

    def add_missing(m: C.Member, kind: str) -> None:
        """构件引用的截面 ID 不在截面表（§a.7 E-MEM-SEC）：不许静默——仍列进报告。"""
        k = ("<missing>", m.section, "", 0, "", "", ())
        if k in detail:
            d = detail[k]
            d["used_by"][m.type] = d["used_by"].get(m.type, 0) + 1
            return
        detail[k] = {
            "id": m.section, "table": "", "name": "", "kind": 0,
            "status": C.UNRESOLVED, "source": "none", "pkpm_name": "",
            "spec_path": "", "desp_params": [], "evidence": "",
            "reason": "构件引用的截面 ID=%s 不在截面表（契约 §a.7 E-MEM-SEC）" % (m.section,),
            "used_by": {m.type: 1},
        }

    for m in model.members:
        sec = model.sections.get(m.section)
        kind = SECTION_KIND.get(m.type, "beam")
        if sec is None:
            add_missing(m, kind)
        else:
            add(sec, kind, m.type)
    for s in model.slabs:                       # 板面（含板洞）：与 macgen 同一口径
        add(C.Section.for_panel("slab", s.thickness), "slab", "slab")
    for w in model.walls:                       # 墙：有真截面则用真截面（同 macgen §d.1）
        if w.section >= 0 and w.section in model.sections:
            wsec = model.sections[w.section]
        else:
            wsec = C.Section.for_panel("wall", w.thickness, name=w.name or "")
        add(wsec, "wall", "wall")

    items: List[Dict[str, Any]] = []
    unresolved: List[Dict[str, Any]] = []
    for k, d in sorted(detail.items(),
                       key=lambda kv: (str(kv[1]["table"]), kv[1]["id"], kv[1]["name"])):
        items.append(d)
        if d["status"] != C.UNRESOLVED:
            continue
        u = dict(d)                                  # §h：unresolved 是 detail 的子集
        pair = owner.get(k)                          # 合成截面 / 缺失截面不在 owner 里
        if pair is not None and smap is not None:
            sec, kind = pair
            try:
                u["candidate_keys"] = smap.candidate_keys(sec, kind)
            except Exception:
                pass
        unresolved.append(u)

    stat = {s: 0 for s in C.RESOLUTION_STATUS}
    for d in items:
        if d["status"] in stat:
            stat[d["status"]] += 1
    return {
        "resolved": stat[C.RESOLVED],
        "parametric": stat[C.PARAMETRIC],
        "inferred": stat[C.INFERRED],
        "unresolved": stat[C.UNRESOLVED],
        "total": len(items),
        "detail": items,
        "unresolved": unresolved,
    }


def _skipped_from_notes(notes: Sequence[str]) -> List[Dict[str, Any]]:
    """把 ``Model.notes`` 里"被跳过/未解码"的条目整理成 §h 的 ``skipped`` 结构。

    **只**识别各 ``*_read`` 模块既定的前缀（``未解码表 …`` / ``跳过 …`` /
    ``W-DUMP-…`` / 含 ``哨兵`` / 含 ``轴网线``）；识别不出的 note 一律只留在
    ``report.warnings``（§a.9：notes 全量并入 warnings）——不猜、不丢。
    """
    out: List[Dict[str, Any]] = []
    for n in notes:
        m = re.match(r"未解码表\s+(\S+?)[：:]\s*(\d+)\s*行", n)
        if m:
            out.append({"what": m.group(1), "count": int(m.group(2)), "why": n})
            continue
        m = re.match(r"跳过\s+(\S+?)\s*[:：]", n)
        if m:
            item: Dict[str, Any] = {"what": m.group(1), "why": n}
            mid = re.search(r"(\d+)", m.group(1))
            if mid:
                item["id"] = int(mid.group(1))
            out.append(item)
            continue
        if n.startswith("W-DUMP-NOSPEC") or "哨兵" in n:
            out.append({"what": "spec", "why": n})
            continue
        if "轴网线" in n:
            out.append({"what": "grid-sctn", "why": n})
            continue
    return out


def _counts_line(counts: Dict[str, Any]) -> str:
    mem = counts.get("members") or {}
    loads = counts.get("loads") or {}
    return ("构件计数：levels=%s joints=%s sections=%s members_total=%s"
            "（柱=%s/梁=%s/支撑=%s）slabs=%s(其中洞 %s) walls=%s loads=%s"
            "（beam-line=%s/joint-point=%s）"
            % (counts.get("levels"), counts.get("joints"), counts.get("sections"),
               counts.get("members_total"), mem.get("column"), mem.get("beam"),
               mem.get("brace"), counts.get("slabs"), counts.get("slabs_holes"),
               counts.get("walls"), counts.get("loads_total"), loads.get("beam-line"),
               loads.get("joint-point")))


def _db_summary_lines(report: Dict[str, Any]) -> List[str]:
    """§m.3 的 ``report.db`` 摘要（目录宏/解析/交叉核对/闭环/安全），供 CLI 与 GUI 共用。"""
    db = report.get("db") or {}
    out: List[str] = []
    gen = db.get("generated") or {}
    if gen:
        p2 = gen.get("pass2") or {}
        out.append("    目录宏：STSECTION=%s STCATEGORY=%s SPRFILE=%s SPCOMPONENT=%s "
                   "TEXT=%s DTSET=%s DATA=%s PTSSET=%s PLINE=%s GMSSET=%s SPECIFICATION=%s "
                   "SELEC=%s（第二遍 PSTR=%s GSTR=%s DTRE=%s CATR=%s NARE=%s）"
                   % (gen.get("stsection"), gen.get("stcategory"), gen.get("sprfile"),
                      gen.get("spcomponent"), gen.get("text"), gen.get("dtset"),
                      gen.get("data"), gen.get("ptsset"), gen.get("pline"),
                      gen.get("gmsset"), gen.get("specification"), gen.get("selec"),
                      p2.get("PSTR"), p2.get("GSTR"), p2.get("DTRE"), p2.get("CATR"),
                      p2.get("NARE")))
        if gen.get("catalogue") or gen.get("spec_world"):
            out.append("    本包容器：CATALOGUE=%s；SPWLD=%s（只操作本包容器，契约 §l.1）"
                       % (gen.get("catalogue"), gen.get("spec_world")))
    par = db.get("parsed") or {}
    if par:
        out.append("    解析：规格 %s 条；SPRFILE %s；族 %s；参数化 %s；族码已知 %s；"
                   "有 PKPM 名 %s；有 ShapeVal %s；解析期警告 %s"
                   % (par.get("specs"), par.get("sprfile"), par.get("families"),
                      par.get("parametric"), par.get("family_code_known"),
                      par.get("pkpm_name_known"), par.get("shapeval_known"),
                      len(par.get("warnings") or [])))
    cc = db.get("cross_check") or {}
    if cc:
        out.append("    与匹配文件交叉核对：匹配文件 %s 行；命中 %s；右值失效 %s（其中 "
                   "Double-L 族 %s）；缺前导斜杠 %s；大小写差异 %s；宏独有 SPRFILE %s"
                   % (cc.get("matching_file_rows"), cc.get("matched"),
                      cc.get("broken_total"), cc.get("broken_rhs"),
                      cc.get("missing_leading_slash"), cc.get("case_variants"),
                      cc.get("macro_only")))
    cl = db.get("closure") or {}
    if cl:
        out.append("    闭环（%s）：covered=%s（src=%s → via=%s）；not_closable=%s；"
                   "differences=%s"
                   % (cl.get("direction"), cl.get("covered"), cl.get("src_specs"),
                      cl.get("via_specs"), len(cl.get("not_closable") or []),
                      len(cl.get("differences") or [])))
    sf = db.get("safety") or {}
    if sf:
        out.append("    安全：forbidden_names_scanned=%s（命中 %s）；clean_targets=%s；"
                   "ascii_only=%s"
                   % (sf.get("forbidden_names_scanned"),
                      len(sf.get("forbidden_hits") or []), sf.get("clean_targets"),
                      sf.get("ascii_only")))
    if db.get("losses"):
        out.append("    信息损失申报：%s 条（详见报告的 db.losses）" % (len(db["losses"]),))
    st = report.get("stats") or {}
    if isinstance(st.get("rows"), int):
        extra = ""
        if st.get("tables"):
            extra = "（tables %d 张）" % (len(st["tables"]),)
        elif st.get("segments"):
            extra = "（段行数：%s）" % ", ".join(
                "%s=%s" % (k, v) for k, v in sorted(st["segments"].items()))
        out.append("    产物行数：rows=%s%s" % (st.get("rows"), extra))
    if isinstance(st.get("table_rows"), int):
        out.append("    转化表：%s 行 × %s 列（format=%s，sha256=%s…）"
                   % (st.get("table_rows"), st.get("table_columns"),
                      st.get("table_format"), str(st.get("table_sha256") or "")[:12]))
    return out


def _summary_lines(tool: str, code: int, source: str, output: str, report_path: str,
                   report: Dict[str, Any], elapsed: float, error: str = "") -> List[str]:
    """一行摘要 + 未解析清单（§h：即使为空也要打印 ``unresolved: 0``）。"""
    lines: List[str] = []
    if code == EXIT_OK:
        lines.append("[%s] 成功（退出码 0）：%s -> %s"
                     % (tool, source, output or "（无产物）"))
        lines.append("    耗时 %.2f s；产物：%s" % (elapsed, output))
    else:
        lines.append("[%s] 未完成（退出码 %d）：%s" % (tool, code, source))
        lines.append("    耗时 %.2f s；产物：未写出（原本要写 %s）" % (elapsed, output))
    lines.append("    报告：%s" % (report_path or "（未写）"))
    counts = report.get("counts") or {}
    if counts:
        lines.append("    " + _counts_line(counts))
    sec = report.get("sections") or {}
    un = sec.get("unresolved") or []
    if sec:
        lines.append("    截面：resolved=%s parametric=%s inferred=%s unresolved=%s（共 %s）"
                     % (sec.get("resolved"), sec.get("parametric"), sec.get("inferred"),
                        len(un), sec.get("total")))
    if sec:
        lines.append("    unresolved: %d" % (len(un),))
        for d in un[:UNRESOLVED_PRINT_LIMIT]:
            lines.append("      - id=%s table=%s kind=%s name=%r used_by=%s reason=%s"
                         % (d.get("id"), d.get("table"), d.get("kind"), d.get("name"),
                            d.get("used_by"), d.get("reason")))
        if len(un) > UNRESOLVED_PRINT_LIMIT:
            lines.append("      …（其余 %d 条见报告 %s）"
                         % (len(un) - UNRESOLVED_PRINT_LIMIT, report_path))
    elif code == EXIT_OK:
        # 数据库方向（§m.1 的 5 条）不产出构件的截面清单：它们是宏/转化表的解析与生成，
        # §h 的 sections 块不适用（键仍在，值为空）。此处不得说成"转换未完成"。
        lines.append("    unresolved: 不适用（本命令不产出构件截面清单，看下面的 db 块）")
    else:
        lines.append("    unresolved: （未生成截面清单：转换未完成）")
    inf = [d for d in (sec.get("detail") or []) if d.get("status") == C.INFERRED]
    if inf:
        lines.append("    inferred: %d（不是 resolved；逐条见报告 evidence）" % (len(inf),))
        for d in inf[:UNRESOLVED_PRINT_LIMIT]:
            lines.append("      - id=%s table=%s kind=%s name=%r spec=%s desp=%s"
                         % (d.get("id"), d.get("table"), d.get("kind"), d.get("name"),
                            d.get("spec_path"), d.get("desp_params")))
    lines.extend(_db_summary_lines(report))
    lines.append("    warnings=%d geometry_anomalies=%d skipped=%d errors=%d"
                 % (len(report.get("warnings") or []),
                    len(report.get("geometry_anomalies") or []),
                    len(report.get("skipped") or []),
                    len(report.get("errors") or [])))
    if error:
        lines.append("    错误：%s" % error)
        lines.extend("      " + ln for ln in str(error).splitlines()[1:])
    return lines


def _new_db_block(macro_source: str = "") -> Dict[str, Any]:
    """契约 §m.3 的 ``report.db``：**7 键齐全**，缺席的方向写 ``null``（不得省略键）。"""
    return {"macro_source": macro_source, "generated": None, "parsed": None,
            "cross_check": None, "closure": None, "losses": [], "safety": None}


def _loss_items(direction: str) -> List[Dict[str, Any]]:
    """§k.5 的信息损失申报，逐条补 ``direction`` 字段（§m.3 的 ``losses`` 项含该键）。

    ``SectionTable.loss_report(direction)`` 只是 ``sectionlib.loss_items(direction)`` 的
    方法包装（同一份冻结清单）⇒ 模块级调用即可，CLI 不必先建表。
    """
    out: List[Dict[str, Any]] = []
    for it in sectionlib.loss_items(direction):
        d = dict(it)
        d["direction"] = direction
        out.append(d)
    return out


def _parse_safety(text: str) -> Dict[str, Any]:
    """解析方向的安全汇报（§m.3 要求 ``safety`` 三键**必须存在**）。

    本包在解析方向**不生成**任何宏 ⇒ 不做禁用名扫描（§l.1 只约束本包的生成物）；
    三个冻结键照写，另附一句说明——不用"扫过了"来充数，也不省略键。
    """
    return {"forbidden_names_scanned": False,
            "forbidden_hits": [],
            "clean_targets": [],
            "ascii_only": bool(text.isascii()),
            "note": "解析方向不生成宏，未做禁用容器名扫描（契约 §l.1 只约束本包生成物）"}


def _new_report(tool: str, source: str, fmt: str, output: str,
                options: Dict[str, Any]) -> Dict[str, Any]:
    """§h + §m.3 的报告骨架（v1 键位不变，追加 ``db`` 块与 §h v3 的 ``renames`` 键）。

    ``renames``〔R7 语义变更〕：不再是"运行期被迫改名清单"（唯一化函数与宏内唯一化模板已
    整体作废），而是 **SITE 名探测结果** —— .NET 侧直查试出的可用名经 ``site_name`` 传入，
    引擎按传入值原样创建、不改名；三个宏子命令由 :func:`_record_macro_names` 填这一项，
    其余方向恒为 ``[]``（键仍必须存在，§h 纪律）。
    """
    return {
        "contract_version": C.CONTRACT_VERSION,
        "tool": tool,
        "source": source,
        "source_format": fmt,
        "output": output,
        "options": options,
        "assumptions": [],
        "counts": {},
        "sections": {},
        "geometry_anomalies": [],
        "skipped": [],
        "warnings": [],
        "errors": [],
        "stats": {},
        "renames": [],
        "db": _new_db_block(source if fmt == "pdmsdb" else ""),
    }


def _finish(res: RunResult, rep: Dict[str, Any], code: int, t0: float,
            error: str = "", stderr_issues: Optional[Sequence[str]] = None) -> RunResult:
    """收尾：写报告（§h；成功路径写失败 ⇒ 降为码 2）→ 生成摘要 → 填 RunResult。"""
    res.report = rep
    res.elapsed = time.time() - t0
    res.report_path = str(rep.get("_report_path") or res.report_path)
    rep.pop("_report_path", None)

    if code == EXIT_OK:
        try:
            _write_report(res.report_path, rep)
        except Exception as exc:                     # §h：缺省写入失败 ⇒ 按码 2 退出
            code = EXIT_INPUT
            error = "报告写入失败：%s（契约 §h：按码 2 退出）" % (exc,)
            rep["errors"].append(error)
            res.exit_code = code
            res.ok = False
            res.lines = _summary_lines(res.tool, code, res.source, res.output,
                                       res.report_path, rep, res.elapsed, error)
            return res
    else:
        try:                                          # 失败路径也尽力留一份报告
            _write_report(res.report_path, rep)
        except Exception as exc:
            rep["errors"].append("报告写入失败：%s" % (exc,))

    res.exit_code = code
    res.ok = (code == EXIT_OK)
    res.error = error
    res.errors = list(stderr_issues or [])
    res.lines = _summary_lines(res.tool, code, res.source, res.output, res.report_path,
                               rep, res.elapsed, error)
    return res


def _apply_categories(model: C.Model, categories: Optional[Sequence[str]]):
    """GUI 的"构件类别勾选"（§f.3）。``None``/全选 ⇒ 原样返回（与命令行**完全等价**）。

    过滤只发生在 GUI 路径上；被滤掉的对象**逐类记账**（notes + skipped + warnings），
    绝不静默。被滤掉构件的 beam-line 荷载会一并滤掉（否则外键不可解析 ⇒ §a.7
    ``E-LOAD-TARGET`` 会以码 3 中止）。
    """
    if not categories:
        return model, [], []
    keep = {str(c) for c in categories}
    bad = sorted(keep - set(CATEGORIES))
    if bad:
        raise InputError("构件类别 %s 非法：须 ∈ %s" % (bad, list(CATEGORIES)))
    if keep >= set(CATEGORIES):
        return model, [], []

    dropped_members = [m for m in model.members if m.type not in keep]
    drop_mids = {m.id for m in dropped_members}
    dropped_loads = [l for l in model.loads
                     if l.kind == "beam-line" and l.target_id in drop_mids]
    drop_lids = {id(l) for l in dropped_loads}
    dropped_slabs = [s for s in model.slabs if "slab" not in keep]
    dropped_walls = [w for w in model.walls if "wall" not in keep]

    note = ("构件类别勾选（GUI，§f.3）：保留 %s；已过滤构件 %d 根（柱 %d/梁 %d/支撑 %d）、"
            "板面 %d 块、墙 %d 面、随之不可解析的 beam-line 荷载 %d 条"
            % ("/".join(CATEGORY_CN[c] for c in CATEGORIES if c in keep),
               len(dropped_members),
               sum(1 for m in dropped_members if m.type == "column"),
               sum(1 for m in dropped_members if m.type == "beam"),
               sum(1 for m in dropped_members if m.type == "brace"),
               len(dropped_slabs), len(dropped_walls), len(dropped_loads)))
    skipped: List[Dict[str, Any]] = []
    if dropped_members:
        for t in ("column", "beam", "brace"):
            ids = [m.id for m in dropped_members if m.type == t]
            if ids:
                skipped.append({"what": "member", "type": t, "count": len(ids),
                                "why": note})
    if dropped_slabs:
        skipped.append({"what": "slab", "count": len(dropped_slabs), "why": note})
    if dropped_walls:
        skipped.append({"what": "wall", "count": len(dropped_walls), "why": note})
    if dropped_loads:
        skipped.append({"what": "load", "count": len(dropped_loads),
                        "why": "目标构件已被构件类别勾选过滤 ⇒ 一并滤掉（" + note + "）"})

    sub = C.Model(levels=list(model.levels), joints=dict(model.joints),
                  sections=dict(model.sections), members=[m for m in model.members
                                                          if m.type in keep],
                  slabs=[s for s in model.slabs if "slab" in keep],
                  loads=[l for l in model.loads if id(l) not in drop_lids],
                  walls=[w for w in model.walls if "wall" in keep],
                  source=model.source, source_format=model.source_format,
                  units=model.units, contract_version=model.contract_version,
                  notes=list(model.notes) + [note])
    return sub, [note], skipped


def _ecc_anomalies(model: C.Model) -> List[str]:
    """§a.2：非零偏心的构件必须**逐条**列入报告的 ``geometry_anomalies``。

    偏心正负方向未证实（§9.3#6 / §12#6）⇒ 只报"值 + 已并入几何"，不断言方向语义。
    """
    out: List[str] = []
    for m in model.members:
        vals = [v for v in m.ecc if abs(v) > C.TOL]
        if vals:
            out.append("ECC: Member %s(%s): ecc=%s → start=%s end=%s"
                       "（偏心方向语义未证实，几何按原值相加并入 start/end；"
                       "jwd_format.md §9.3#6 / 契约 §12#6）"
                       % (m.id, m.type, tuple(m.ecc),
                          tuple(round(v, 6) for v in m.start),
                          tuple(round(v, 6) for v in m.end)))
    return out


def _check_plan_sections(plan_sections: Sequence[Dict[str, Any]],
                         detail: Sequence[Dict[str, Any]]) -> Optional[str]:
    """交叉核对 CLI 的截面明细与 ``macgen.MacroPlan.sections``（§b.1 纪律 1）。"""
    def norm(items):
        return sorted((str(d.get("table")), d.get("id"), d.get("name"), d.get("status"),
                       d.get("spec_path"), tuple(sorted((d.get("used_by") or {}).items())))
                      for d in items)
    a, b = norm(plan_sections), norm(detail)
    if a == b:
        return None
    only_plan = [x for x in a if x not in b][:3]
    only_cli = [x for x in b if x not in a][:3]
    return ("截面明细与 macgen.MacroPlan.sections 不一致（契约 §b.1 纪律 1：截面解析只有一条路）"
            "：宏侧独有的 %s；报告侧独有的 %s" % (only_plan, only_cli))


def _record_macro_names(rep: Dict[str, Any], plan: Any, site_name: str) -> None:
    """〔R7〕把命名/探测结果填进报告（只对生成 PDMS 建模型宏的三个子命令）。

    * ``options.site_name`` —— .NET 侧直查试出的可用 SITE 名（引擎原样使用）；
    * ``renames`` —— **语义变更**：不再表示"运行期被迫改名清单"（那套唯一化函数已不再部署），
      而是 **SITE 名探测结果**：.NET 传入什么就记什么，引擎不改名、不做 re 逻辑；
    * ``stats.used_names``/``used_names_count`` —— 宏内**带名**创建用掉的全部名字（已查重）；
    * ``stats.unnamed_count`` —— 无名创建（``NEW SCTN``/``NEW PANE``/``NEW STWALL``）的条数。
    """
    rep["options"]["site_name"] = site_name
    rep["renames"] = [{
        "kind": "site-name-probe",
        "site_name": site_name,
        "provider": ".NET（DbElement 直查逐个试名：/PKPM2PDMS → /PKPM2PDMSre → … re99）",
        "renamed": False,
        "why": "〔R7〕改名责任全在 .NET 探测侧：引擎按传入的 site_name 原样创建 SITE，"
               "不生成候选名、不做 re 逻辑；中间层名含层号 ⇒ 全宏唯一（生成期查重）",
    }]
    rep["stats"]["used_names"] = list(getattr(plan, "used_names", []) or [])
    rep["stats"]["used_names_count"] = len(rep["stats"]["used_names"])
    rep["stats"]["unnamed_count"] = int(getattr(plan, "unnamed_count", 0))


def _section_block_and_warnings(model: C.Model, smap, rep: Dict[str, Any],
                                tool: str) -> Dict[str, Any]:
    """填 ``rep.sections`` 并把 ``SectionMap`` 的加载期问题并入 ``warnings``。"""
    block = build_section_report(model, smap)
    rep["sections"] = block
    if smap is not None:
        rep["warnings"].extend(smap.warnings)
        rules = dict(getattr(smap, "family_rules", {}) or {})
        active = sorted((int(k), v) for k, v in rules.items() if v != "none")
        if active:
            rep["assumptions"].append(
                "推断族已启用（契约 §e.1a/§e.4a，来自补充文件的 @FAMILY 指令）：%s；"
                "对应截面在报告里 status='inferred'（不是 resolved）并带 evidence"
                % ", ".join("@FAMILY %d = %s" % (k, v) for k, v in active))
    inf = [d for d in (block.get("detail") or []) if d.get("status") == C.INFERRED]
    if inf:
        rep["warnings"].append(
            "有 %d 个被用到的截面按**推断族**解析（status=inferred，非 resolved）：%s；"
            "残余风险与改法见 CONTRACT §e.3 的 Kind 行与各条 evidence"
            % (len(inf),
               ", ".join("%s/%s(kind=%s)→%s" % (d.get("id"), d.get("name") or "(无名)",
                                                d.get("kind"), d.get("spec_path"))
                         for d in inf[:10])))
    if block["unresolved"]:
        rep["warnings"].append(
            "有 %d 个被用到的截面未解析（status=unresolved）：%s"
            % (len(block["unresolved"]),
               ", ".join("%s/%s" % (d.get("id"), d.get("name") or "(无名)")
                         for d in block["unresolved"][:10])))
    if tool == "pdt2model":
        if smap is None:
            rep["assumptions"].append(
                "pdt2model 的冻结签名（契约 §f.1）没有 --secmap：报告里的截面状态按"
                "\"未做解析\"记账（reason 已写明），**未**加载与 .pdt 同目录的匹配文件")
        else:
            rep["assumptions"].append(
                "pdt2model 的冻结签名（契约 §f.1）没有 --secmap：报告里的截面状态取自与"
                " .pdt 同目录的 %s（仅用于报告，**不参与** model.json 的生成）"
                % DEFAULT_SECMAP_NAME)
    return block


# --------------------------------------------------------------------------
# 子命令实现（GUI 复用这三个函数；它们**不打印**任何东西）
# --------------------------------------------------------------------------


def run_jwd2pdms(jwd: str, out: str, secmap: Optional[str] = None,
                 extra: Optional[str] = None, project: Optional[str] = None,
                 base: Sequence[float] = (0.0, 0.0, 0.0), angle: float = 0.0,
                 unit: str = "mm", report: Optional[str] = None,
                 categories: Optional[Sequence[str]] = None,
                 site_name: Optional[str] = None) -> RunResult:
    """``jwd2pdms``：``.jwd``（SQLite3）→ PDMS 宏 ``.mac``（GBK+CRLF）+ ``report.json``。

    ``categories``：GUI 的构件类别勾选（§f.3）；``None`` = 不过滤（与命令行逐项等价）。
    ``site_name``：〔R7〕SITE 名（.NET 侧直查试出的可用名，经 ``--request`` 的 ``site_name``
    传入；命令行用 ``--site-name``）。**必填**：引擎不生成、不默认、不做 re 逻辑（缺 ⇒ 码 2）。
    """
    t0 = time.time()
    src = os.path.abspath(jwd)
    out_abs = os.path.abspath(out)
    rep_path = os.path.abspath(report) if report else _default_report_path(out_abs)
    res = RunResult(tool="jwd2pdms", source=src, output=out_abs, report_path=rep_path)
    rep = _new_report("jwd2pdms", src, "jwd", out_abs,
                      {"secmap": "", "extra": "", "project": project or "",
                       "site_name": site_name or "",
                       "base": [float(x) for x in base], "angle": float(angle),
                       "unit": unit})
    rep["_report_path"] = rep_path
    try:
        if not os.path.isfile(src):
            raise InputError("输入文件不存在：%s" % (src,))
        smap_path = _resolve_secmap_path(secmap, src)
        smap = _load_secmap(smap_path, extra)
        rep["options"]["secmap"] = smap_path or ""
        rep["options"]["extra"] = smap.extra_source if smap is not None else ""
        rep["stats"]["secmap"] = dict(smap.stats) if smap is not None else {}

        try:
            model = jwd_read.read_jwd(src)                       # 只读（契约 §b.2）
        except sqlite3.Error as exc:
            raise InputError("不是可读的 SQLite3 库 / 打开失败：%s：%s" % (src, exc))
        rep["warnings"].extend(model.notes)                      # §a.9：全量并入
        proj = (project or "").strip()
        if not proj:
            proj = _project_from_notes(model.notes)
            if proj:
                rep["warnings"].append(
                    "未给 --project：取 pkpmSysInfo.ID=2 的工程名 %r（契约 §f.1/§b.2）" % proj)
            else:
                proj = DEFAULT_PROJECT
                rep["assumptions"].append(
                    "未给 --project 且取不到 pkpmSysInfo.ID=2 的工程名 ⇒ ZONE 用缺省 %r"
                    "（契约 §f.1）" % DEFAULT_PROJECT)
        rep["options"]["project"] = proj

        model, notes, skipped = _apply_categories(model, categories)
        rep["skipped"].extend(skipped)
        rep["warnings"].extend(notes)

        issues = model.validate()                                # §a.7 / §f.2 码 3
        rep["counts"] = model.counts()                           # §h：唯一出处
        rep["geometry_anomalies"] = [s for s in issues if s.startswith("W-")]
        rep["geometry_anomalies"].extend(_ecc_anomalies(model))
        rep["skipped"].extend(_skipped_from_notes(model.notes))
        errors = [s for s in issues if s.startswith("E-")]
        if errors:
            raise ModelError(errors)                             # §f.2 码 3：不写产物

        opts = macgen.MacOptions(project=proj, site_name=site_name or "",
                                 base_e=float(base[0]), base_n=float(base[1]),
                                 base_u=float(base[2]), angle_deg=float(angle), unit=unit,
                                 secmap=smap)
        try:
            plan = macgen.build_plan(model, opts)
        except ValueError as exc:                    # 名字/单位/site_name 非法 ⇒ 输入错误（码 2）
            raise InputError(str(exc))
        block = _section_block_and_warnings(model, smap, rep, "jwd2pdms")
        mismatch = _check_plan_sections(plan.sections, block["detail"])
        if mismatch:
            rep["warnings"].append(mismatch)
        rep["assumptions"].extend(plan.assumptions)
        rep["warnings"].extend(plan.warnings)
        rep["stats"]["commands"] = dict(plan.stats)
        _record_macro_names(rep, plan, opts.site_name)

        try:
            macgen.write_macro(out_abs, plan.text())             # GBK+CRLF + 回读校验（§g）
        except (ValueError, IOError, OSError) as exc:
            raise InputError("写出宏失败：%s" % (exc,))
        try:
            with open(out_abs, "rb") as fh:                      # 回读统计（字节纪律已在
                raw = fh.read()                                  # write_macro 内校验过）
        except OSError as exc:
            raise InputError("回读宏失败：%s" % (exc,))
        rep["stats"]["macro_bytes"] = len(raw)
        rep["stats"]["macro_lines"] = len(raw.split(b"\r\n")) - 1
        return _finish(res, rep, EXIT_OK, t0)
    except InputError as exc:
        rep["errors"].append(str(exc))
        return _finish(res, rep, EXIT_INPUT, t0, error=str(exc))
    except ModelError as exc:
        rep["errors"].extend(exc.issues)
        return _finish(res, rep, EXIT_MODEL, t0,
                       error="Model.validate() 报出 %d 个 E- 项 ⇒ 不写产物（契约 §f.2 码 3）"
                             % len(exc.issues), stderr_issues=exc.issues)
    except Exception:                                            # 码 1：打印 traceback
        tb = traceback.format_exc()
        rep["errors"].append(tb.strip().splitlines()[-1])
        return _finish(res, rep, EXIT_EXCEPTION, t0, error=tb)


def run_pdms2jwd(dump: str, out: str, secmap: Optional[str] = None,
                 dump_unit: str = "mm", report: Optional[str] = None,
                 categories: Optional[Sequence[str]] = None) -> RunResult:
    """``pdms2jwd``：``#PKPM2PDMS-PDMSDUMP 1.0`` 文本（GBK）→ ``.jwd``（SQLite）+ 报告。

    ``--dump-unit``（§f.1）：**仅当 dump 没有 ``UNITS`` 行时**生效；有 ``UNITS`` 行时以该行
    为准并记 ``warnings``。``parse_dump(text)`` 的冻结签名没有"缺省单位"入口，故这里在
    缺 ``UNITS`` 行且单位非 mm 时补一行 ``UNITS <单位>``（见本文件头部说明）。
    """
    t0 = time.time()
    src = os.path.abspath(dump)
    out_abs = os.path.abspath(out)
    rep_path = os.path.abspath(report) if report else _default_report_path(out_abs)
    res = RunResult(tool="pdms2jwd", source=src, output=out_abs, report_path=rep_path)
    rep = _new_report("pdms2jwd", src, "pdmsdump", out_abs,
                      {"secmap": "", "extra": "", "dump_unit": dump_unit})
    rep["_report_path"] = rep_path
    try:
        if not os.path.isfile(src):
            raise InputError("输入文件不存在：%s" % (src,))
        smap_path = _resolve_secmap_path(secmap, src)
        smap = _load_secmap(smap_path, None)          # §12#11：pdms2jwd 只用默认补充文件
        rep["options"]["secmap"] = smap_path or ""
        rep["options"]["extra"] = smap.extra_source if smap is not None else ""
        rep["stats"]["secmap"] = dict(smap.stats) if smap is not None else {}

        try:
            text = pdms_dump.load_dump(src)           # GBK，失败即抛（§c.1 禁止 replace）
        except UnicodeDecodeError as exc:
            raise InputError("dump 不是 GBK 编码（契约 §c.1）：%s" % (exc,))
        except OSError as exc:
            raise InputError("读取 dump 失败：%s" % (exc,))

        head = [ln for ln in text.splitlines() if ln.strip()]
        if head and head[0].split()[:1] != [pdms_dump.HEADER]:
            raise InputError("首行不是 %s（契约 §c.2）：%r" % (pdms_dump.HEADER, head[0][:60]))
        has_units = len(head) > 1 and head[1].split()[:1] == ["UNITS"]
        if not has_units:
            if dump_unit != "mm":
                lines = text.splitlines()
                for i, ln in enumerate(lines):
                    if ln.strip():
                        lines.insert(i + 1, "UNITS %s" % dump_unit)
                        break
                text = "\r\n".join(lines)
                rep["warnings"].append(
                    "dump 缺 UNITS 行 ⇒ 按 --dump-unit=%s 解析（CLI 在头部行后补了一行 "
                    "UNITS %s；契约 §f.1：--dump-unit 仅在此情况下生效）" % (dump_unit, dump_unit))
            else:
                rep["warnings"].append(
                    "dump 缺 UNITS 行 ⇒ 按 --dump-unit 的缺省 mm 解析（契约 §c.1/§f.1）")
        else:
            got = head[1].split()[1] if len(head[1].split()) > 1 else ""
            if got != dump_unit:
                rep["warnings"].append(
                    "dump 的 UNITS=%s 与 --dump-unit=%s 不一致 ⇒ 以 UNITS 行为准（契约 §f.1）"
                    % (got, dump_unit))

        pdms_dump.set_default_section_map(smap)       # §e.6 的注入入口（parse_dump 签名冻结）
        try:
            model = pdms_dump.parse_dump(text)
        except pdms_dump.DumpSyntaxError as exc:
            raise InputError("dump 文法错误，退出码 2（契约 §c.3/§f.2）：%s" % (exc,))
        finally:
            pdms_dump.set_default_section_map(None)
        model.source = src                            # 报告/JSON 里标注真实来源
        rep["warnings"].extend(model.notes)

        model, notes, skipped = _apply_categories(model, categories)
        rep["skipped"].extend(skipped)
        rep["warnings"].extend(notes)

        issues = model.validate()
        rep["counts"] = model.counts()
        rep["geometry_anomalies"] = [s for s in issues if s.startswith("W-")]
        rep["geometry_anomalies"].extend(_ecc_anomalies(model))
        rep["skipped"].extend(_skipped_from_notes(model.notes))
        errors = [s for s in issues if s.startswith("E-")]
        if errors:
            raise ModelError(errors)                             # §f.2 码 3：不写产物

        _section_block_and_warnings(model, smap, rep, "pdms2jwd")
        try:
            stats = jwd_write.write_jwd(model, out_abs)   # §b.3 的返回值
        except (IOError, OSError) as exc:
            raise InputError("写出 .jwd 失败：%s" % (exc,))
        except ValueError as exc:
            raise InputError("模型无法写成 .jwd：%s" % (exc,))
        rep["stats"].update(stats)
        rep["skipped"].extend(stats.get("skipped") or [])
        rep["warnings"].extend(stats.get("warnings") or [])
        return _finish(res, rep, EXIT_OK, t0)
    except InputError as exc:
        rep["errors"].append(str(exc))
        return _finish(res, rep, EXIT_INPUT, t0, error=str(exc))
    except ModelError as exc:
        rep["errors"].extend(exc.issues)
        return _finish(res, rep, EXIT_MODEL, t0,
                       error="Model.validate() 报出 %d 个 E- 项 ⇒ 不写产物（契约 §f.2 码 3）"
                             % len(exc.issues), stderr_issues=exc.issues)
    except Exception:
        tb = traceback.format_exc()
        rep["errors"].append(tb.strip().splitlines()[-1])
        return _finish(res, rep, EXIT_EXCEPTION, t0, error=tb)


def run_pdt2model(pdt: str, out: str, report: Optional[str] = None,
                  secmap: Optional[str] = None,
                  categories: Optional[Sequence[str]] = None) -> RunResult:
    """``pdt2model``：``.pdt``（GBK 文本）→ ``model.json``（UTF-8/LF，契约 §a.6）+ 报告。

    只做 ``read_pdt`` → ``Model.save_json``（§f.1）。报告里的截面状态在"与 .pdt 同目录存在
    ``PKPM转PDMS截面匹配文件.txt``"时用它算出（**不参与** model.json 的生成，见文件头说明）；
    ``secmap`` 参数只是给 GUI/测试一个显式入口，命令行**没有**这个选项。
    """
    t0 = time.time()
    src = os.path.abspath(pdt)
    out_abs = os.path.abspath(out)
    rep_path = os.path.abspath(report) if report else _default_report_path(out_abs)
    res = RunResult(tool="pdt2model", source=src, output=out_abs, report_path=rep_path)
    rep = _new_report("pdt2model", src, "pdt", out_abs, {"secmap": ""})
    rep["_report_path"] = rep_path
    try:
        if not os.path.isfile(src):
            raise InputError("输入文件不存在：%s" % (src,))
        try:
            smap_path = _resolve_secmap_path(secmap, src, allow_missing=True)
        except InputError:
            smap_path = None
        smap = _load_secmap(smap_path, None)
        rep["options"]["secmap"] = smap_path or ""
        rep["options"]["extra"] = smap.extra_source if smap is not None else ""
        rep["stats"]["secmap"] = dict(smap.stats) if smap is not None else {}

        try:
            model = pdt_read.read_pdt(src)                 # 只读；GBK 严格解码（§b.4/§g.1）
        except UnicodeDecodeError as exc:
            raise InputError(".pdt 不是 GBK 编码（契约 §b.4）：%s" % (exc,))
        except OSError as exc:
            raise InputError("读取 .pdt 失败：%s" % (exc,))
        rep["warnings"].extend(model.notes)                # §a.9

        model, notes, skipped = _apply_categories(model, categories)
        rep["skipped"].extend(skipped)
        rep["warnings"].extend(notes)

        issues = model.validate()
        rep["counts"] = model.counts()
        rep["geometry_anomalies"] = [s for s in issues if s.startswith("W-")]
        rep["geometry_anomalies"].extend(_ecc_anomalies(model))
        rep["skipped"].extend(_skipped_from_notes(model.notes))
        errors = [s for s in issues if s.startswith("E-")]
        if errors:
            raise ModelError(errors)                             # §f.2 码 3：不写产物

        _section_block_and_warnings(model, smap, rep, "pdt2model")
        rep["assumptions"].append(
            "model.json 用 Model.save_json() 的缺省规范形式（§a.6：UTF-8 无 BOM + LF、"
            "sort_keys=True、紧凑分隔符），供跨模块逐字节比对")
        try:
            model.save_json(out_abs)
        except OSError as exc:
            raise InputError("写出 model.json 失败：%s" % (exc,))
        rep["stats"]["output_bytes"] = os.path.getsize(out_abs)
        rep["stats"]["output_lines"] = 1
        return _finish(res, rep, EXIT_OK, t0)
    except InputError as exc:
        rep["errors"].append(str(exc))
        return _finish(res, rep, EXIT_INPUT, t0, error=str(exc))
    except ModelError as exc:
        rep["errors"].extend(exc.issues)
        return _finish(res, rep, EXIT_MODEL, t0, error=str(exc), stderr_issues=exc.issues)
    except Exception:
        tb = traceback.format_exc()
        rep["errors"].append(tb.strip().splitlines()[-1])
        return _finish(res, rep, EXIT_EXCEPTION, t0, error=tb)


# --------------------------------------------------------------------------
# R2 追加：格式互转 / PDMS 宏 / 数据库双向（契约 §(j) §(k) §(l) §(m)）
# --------------------------------------------------------------------------


def _read_model(fmt: str, src: str) -> C.Model:
    """按格式读取规范模型（``'jwd'`` / ``'pdt'``）；失败一律翻成 :class:`InputError`。"""
    if fmt == "jwd":
        try:
            return jwd_read.read_jwd(src)                    # 只读（§b.2）
        except sqlite3.Error as exc:
            raise InputError("不是可读的 SQLite3 库 / 打开失败：%s：%s" % (src, exc))
        except OSError as exc:
            raise InputError("读取 .jwd 失败：%s" % (exc,))
    try:
        model = pdt_read.read_pdt(src)                       # 只读；GBK 严格解码（§b.4/§g.1）
    except UnicodeDecodeError as exc:
        raise InputError(".pdt 不是 GBK 编码（契约 §b.4）：%s" % (exc,))
    except OSError as exc:
        raise InputError("读取 .pdt 失败：%s" % (exc,))
    if not model.levels and not model.members and not model.sections:
        raise InputError("没有解析出任何对象（无 Level/构件/截面）：这个文件不是 .pdt"
                         "（判据见契约 §b.4 的 13 段）")
    return model


def _validate_or_raise(model: C.Model, rep: Dict[str, Any]) -> None:
    """§a.7 的校验 → 填 ``counts``/``geometry_anomalies``/``skipped``；有 ``E-`` ⇒ 码 3。"""
    issues = model.validate()
    rep["counts"] = model.counts()                           # §h：唯一出处
    rep["geometry_anomalies"] = [s for s in issues if s.startswith("W-")]
    rep["geometry_anomalies"].extend(_ecc_anomalies(model))
    rep["skipped"].extend(_skipped_from_notes(model.notes))
    errors = [s for s in issues if s.startswith("E-")]
    if errors:
        raise ModelError(errors)


def _emit_pdms_macro(tool: str, model: C.Model, out_abs: str,
                     smap: Optional[secmap_mod.SectionMap], project: str,
                     base: Sequence[float], angle: float, unit: str,
                     rep: Dict[str, Any], site_name: str = "") -> None:
    """``jwd2pdms``/``pdt2pdms`` 的宏生成（§d.4 的骨架由 macgen 负责）。

    ``plan.sections``（宏侧实际用到的截面）与 CLI 的 ``sections`` 块交叉核对（§b.1 纪律 1）。
    ``site_name``：〔R7〕SITE 名（必填；.NET 直查试出后传入，引擎不改名）。
    """
    opts = macgen.MacOptions(project=project, site_name=site_name or "",
                             base_e=float(base[0]), base_n=float(base[1]),
                             base_u=float(base[2]), angle_deg=float(angle), unit=unit,
                             secmap=smap)
    try:
        plan = macgen.build_plan(model, opts)
    except ValueError as exc:                    # 名字/单位/site_name 非法 ⇒ 输入错误（码 2）
        raise InputError(str(exc))
    spec_kind = {"jwd2pdms": "jwd2pdms", "pdt2pdms": "pdt2pdms"}.get(tool, tool)
    block = _section_block_and_warnings(model, smap, rep, spec_kind)
    mismatch = _check_plan_sections(plan.sections, block["detail"])
    if mismatch:
        rep["warnings"].append(mismatch)
    rep["assumptions"].extend(plan.assumptions)
    rep["warnings"].extend(plan.warnings)
    rep["stats"]["commands"] = dict(plan.stats)
    _record_macro_names(rep, plan, opts.site_name)
    try:
        macgen.write_macro(out_abs, plan.text())             # GBK+CRLF + 回读校验（§g）
    except (ValueError, IOError, OSError) as exc:
        raise InputError("写出宏失败：%s" % (exc,))
    try:
        with open(out_abs, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        raise InputError("回读宏失败：%s" % (exc,))
    rep["stats"]["macro_bytes"] = len(raw)
    rep["stats"]["macro_lines"] = len(raw.split(b"\r\n")) - 1


def _ascii_note(path: str) -> str:
    """宏头注释用的 ASCII 安全文本（§l.1-5：生成的宏必须纯 ASCII）。"""
    base = os.path.basename(path or "")
    return "".join(ch if 32 <= ord(ch) < 127 else "_" for ch in base) or "?"


def _kind_hint(rec: Any) -> str:
    """``SectionMap.resolve`` 的 kind 提示（§e.6 的允许值）。

    ``.jwd`` 的表来源是已知的（``extra['jwd_table']``）；``.pdt`` 没有构件类别信息
    ⇒ 用 ``'beam'``——对**框架**截面而言 ``beam/col/brace`` 在 §e.1/§e.3 里等价
    （``kind`` 只影响板/墙的 ``T<厚度>`` 候选键与族选择），故不构成猜测。
    """
    t = str((getattr(rec, "extra", None) or {}).get("jwd_table") or "")
    return t if t in ("beam", "col", "brace") else "beam"


def _pdef_default(v: float) -> str:
    return "%g" % float(v)


def _backfill_from_secmap(table: "sectionlib.SectionTable", model: C.Model,
                          smap: Optional[secmap_mod.SectionMap],
                          rep: Dict[str, Any]) -> Tuple["sectionlib.SectionTable", int]:
    """内置转化表没有 ``pdms_spec_path`` 的记录 → 按 §e.6 的唯一路径用 secmap 补齐。

    见模块头「对调用方的修正」第 3 条：``table_from_jwd/table_from_pdt`` 只按
    ``pkpm_name`` 查内置表（含**名字为空**的那批截面查不到）⇒ 不补的话 ``jwd2db``/
    ``pdt2db`` 会漏截面。只补 ``resolved``（落规格）与 ``parametric``（落参数化族 + DESP）；
    ``inferred``/``unresolved`` 一律记进报告，不猜。
    """
    recs = []
    n_fill = 0
    for rec in list(table.recs):
        rec = rec                                   # 就地改（表刚建、索引未生成）
        if rec.pdms_spec_path:
            recs.append(rec)
            continue
        extra = rec.extra if isinstance(rec.extra, dict) else {}
        sid = int(extra.get("jwd_id") or extra.get("pdt_id") or 0)
        sec = model.sections.get(sid)
        if sec is None:
            rep["skipped"].append({"what": "section-spec", "key": rec.key,
                                   "kind": rec.kind,
                                   "why": "内置表无该截面的规格路径，且模型里找不到 id=%s "
                                          "⇒ 无法按 §e.6 解析（不猜）" % (sid,)})
            recs.append(rec)
            continue
        res = _resolve(smap, sec, _kind_hint(rec))
        if res.ok and res.spec_path:
            rec.pdms_spec_path = res.spec_path
            rec.source = (rec.source or "") + "+secmap(%s)" % (res.status,)
            extra["secmap"] = {"status": res.status, "source": res.source,
                               "pkpm_name": res.pkpm_name, "reason": res.reason,
                               "evidence": res.evidence}
            if res.status == C.PARAMETRIC:
                order = FAMILY_DESP_ORDER.get(res.spec_path)
                if order and len(order) == len(res.desp_params):
                    rec.params = [sectionlib.ParamDef(name=nm, desp_index=i + 1,
                                                      default=_pdef_default(v))
                                  for i, (nm, v) in enumerate(zip(order, res.desp_params))]
                    rec.is_parametric = True
                    rec.confidence = "medium"
                else:
                    rep["warnings"].append(
                        "截面 %s（%s）走了参数化族 %s，但 DESP 个数 %d 与 §e.3 的顺序表 %s "
                        "对不上 ⇒ 不写 DESP 参数（DESP 位置错位比缺参数更糟）"
                        % (rec.key, rec.pkpm_name or "(无名)", res.spec_path,
                           len(res.desp_params), order))
            elif res.status == C.RESOLVED:
                rec.confidence = "high"
            else:
                rec.confidence = "low"
            n_fill += 1
        else:
            rep["skipped"].append({
                "what": "section-spec", "key": rec.key, "pkpm_name": rec.pkpm_name,
                "kind": rec.kind, "family_code": int(rec.family_code or 0),
                "why": "内置转化表没有该截面的 pdms_spec_path，§e.6 的 secmap 也没解析到"
                       "（status=%s）：%s" % (res.status, res.reason or "—")})
        recs.append(rec)
    return sectionlib.SectionTable(recs, source=table.source), n_fill


def _panel_recs(model: C.Model, smap: Optional[secmap_mod.SectionMap],
                rep: Dict[str, Any]) -> List[Any]:
    """板/墙厚度 → ``SectionRec``（契约 §l.3.6 的缺口补建）。

    模型里没有"板厚截面"这种对象（``thickness`` 落在 ``Slab``/``Wall`` 上）⇒ 由 CLI 合成
    ``Section.for_panel`` 再走 §e.6 的唯一解析路径。**只有 ``resolved``** 才落记录：
    ``parametric`` 会把板挂到框架族（``/USER_RECT-SPEC``）上、``inferred`` 是圆形族——
    两者都不是板/墙，一律记报告（不猜）。
    """
    groups = (("slab", sorted({float(s.thickness) for s in model.slabs
                               if (not s.is_hole) and s.thickness})),
              ("wall", sorted({float(w.thickness) for w in model.walls if w.thickness})))
    n_in = 0
    out: List[Any] = []
    for kind, thicknesses in groups:
        for t in thicknesses:
            sec = C.Section.for_panel(kind, t)
            res = _resolve(smap, sec, kind)
            if res.status != C.RESOLVED or not res.spec_path:
                rep["skipped"].append({
                    "what": "panel-section", "panel": kind, "thickness": t,
                    "key": sec.name,
                    "why": "板/墙厚度 %g 的规格未解析（status=%s）：%s；缺口按 §l.3.6 "
                           "需在匹配文件里给出 %s → 规格（§e.4 的 secmap_extra.txt）"
                           % (t, res.status, res.reason or "—", sec.name)})
                rep["warnings"].append(
                    "板/墙缺口未补：%s 厚 %g（status=%s）—— 该缺口不会出现在目录宏里"
                    % ("板" if kind == "slab" else "墙", t, res.status))
                continue
            out.append(sectionlib.SectionRec(
                key=res.spec_path, pkpm_name=sec.name, family_code=0, family_name_cn="",
                kind=0, shapeval="", dims={"T": float(t)}, mat=int(sec.mat or 6),
                pdms_spec_path=res.spec_path, pdms_catalogue="", is_parametric=False,
                params=[], confidence="medium", source="panel+secmap",
                extra={"panel": kind, "thickness": float(t),
                       "secmap_source": res.source, "secmap_pkpm_name": res.pkpm_name,
                       "reason": "板/墙厚度缺口按 §l.3.6 补建；规格路径来自匹配文件（§e.6）"}))
            n_in += 1
    rep["assumptions"].append(
        "板/墙厚度按 §l.3.6 补成目录宏条目：候选 %d 个厚度（去重后），成功落规格 %d 个；"
        "规格路径取自匹配文件（§e.6 的唯一路径），未解析的厚度已逐条记进 skipped/warnings"
        % (sum(len(t) for _k, t in groups), n_in))
    return out


def _db_table_from_model(tool: str, model: C.Model, smap: Optional[secmap_mod.SectionMap],
                         rep: Dict[str, Any]) -> Tuple["sectionlib.SectionTable", int, int]:
    """模型 → ``SectionTable``：内置表 + §e.6 补齐 + 板/墙缺口（§l.6/§l.3.6）。"""
    fmt = "jwd" if tool == "jwd2db" else "pdt"
    base = (sectionlib.table_from_jwd(model) if fmt == "jwd"
            else sectionlib.table_from_pdt(model))
    table, n_fill = _backfill_from_secmap(base, model, smap, rep)
    panels = _panel_recs(model, smap, rep)
    have = {str(r.key) for r in table.recs}
    kept = []
    for rec in panels:
        if rec.key in have:
            rep["skipped"].append({"what": "panel-section", "key": rec.key,
                                   "why": "同名规格已在表里（框架截面占用了该规格路径）⇒ "
                                          "不重复建族（§l.3.4-1 的不变量）"})
            continue
        have.add(rec.key)
        kept.append(rec)
    recs = list(table.recs) + kept
    return sectionlib.SectionTable(recs, source=table.source), n_fill, len(kept)


def _merge_closure_reasons(closure: Dict[str, Any],
                           skipped: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """把反算期"不可编码"的具体理由并进 ``closure.not_closable``（§l.6-3：含族名与理由）。"""
    by_spec: Dict[str, str] = {}
    for it in skipped or []:
        spec = str(it.get("spec_path") or "")
        why = str(it.get("why") or "")
        if spec and why and spec not in by_spec:
            by_spec[spec] = why
    for it in closure.get("not_closable") or []:
        why = by_spec.get(str(it.get("spec_path") or ""))
        if why:
            it["why"] = "%s；反算期：%s" % (it.get("why"), why)
    return closure


def _run_db_generate(tool: str, src: str, out: str, secmap: Optional[str],
                     extra: Optional[str], report: Optional[str],
                     suffix: Optional[str], clean: bool,
                     catalogue_user: Optional[str], catalogue_stss: Optional[str],
                     categories: Optional[Sequence[str]],
                     project: Optional[str] = None) -> RunResult:
    """``jwd2db`` / ``pdt2db``（§m.1 第 5/6 行）：PKPM 截面定义 → PDMS 目录+规格宏。"""
    t0 = time.time()
    src_abs = os.path.abspath(src)
    out_abs = os.path.abspath(out)
    rep_path = os.path.abspath(report) if report else _default_report_path(out_abs)
    fmt = "jwd" if tool == "jwd2db" else "pdt"
    res = RunResult(tool=tool, source=src_abs, output=out_abs, report_path=rep_path)
    rep = _new_report(tool, src_abs, fmt, out_abs,
                      {"secmap": "", "extra": "", "project": (project or "").strip(),
                       "suffix": suffix or "", "clean": bool(clean),
                       "catalogue_user": catalogue_user or "",
                       "catalogue_stss": catalogue_stss or ""})
    rep["_report_path"] = rep_path
    rep["db"] = _new_db_block(src_abs)
    try:
        if not os.path.isfile(src_abs):
            raise InputError("输入文件不存在：%s" % (src_abs,))
        smap_path = _resolve_secmap_path(secmap, src_abs)
        smap = _load_secmap(smap_path, extra)
        rep["options"]["secmap"] = smap_path or ""
        rep["options"]["extra"] = smap.extra_source if smap is not None else ""
        rep["stats"]["secmap"] = dict(smap.stats) if smap is not None else {}

        model = _read_model(fmt, src_abs)
        rep["warnings"].extend(model.notes)                  # §a.9：全量并入
        proj = (project or "").strip()
        if not proj:
            proj = _project_from_notes(model.notes)          # §b.2（.jwd 才有；.pdt 没有）
            if proj:
                rep["warnings"].append(
                    "未给 --project：从 notes 取到工程名 %r（契约 §b.2）" % proj)
        if proj and not proj.isascii():
            rep["warnings"].append(
                "--project=%r 含非 ASCII 字符 ⇒ 不写进宏头注释（生成的宏必须纯 ASCII，"
                "契约 §l.1-5）；只保留在报告的 options.project 里" % proj)
            proj = ""
        rep["options"]["project"] = proj or str(rep["options"]["project"])
        proj = str(rep["options"]["project"] or "")
        model, notes, sk = _apply_categories(model, categories)
        rep["skipped"].extend(sk)
        rep["warnings"].extend(notes)
        _validate_or_raise(model, rep)

        _section_block_and_warnings(model, smap, rep, tool)
        rep["assumptions"].append(
            "报告 sections 块是 §e.6 的 secmap 解析结果；目录宏的**落点**另有来源：框架截面优先"
            "用内置转化表（= 目录宏的机械投影，§k.2）的 pdms_spec_path，内置表没有的才回退 "
            "secmap（见 stats.secmap_backfilled）；板/墙厚度按 §l.3.6 补建（stats.panel_recs）")

        table, n_fill, n_panel = _db_table_from_model(tool, model, smap, rep)
        rep["stats"].update({"table_recs": len(table), "secmap_backfilled": n_fill,
                             "panel_recs": n_panel})
        n_used = {m.section for m in model.members}
        rep["warnings"].append(
            "生成范围：模型定义的 %d 个截面全部进表（其中被构件用到的 %d 个；"
            "未用到的 %d 个也一并生成——它们可能被其它标准层/后续版本引用）"
            % (len(model.sections), len(n_used), len(model.sections) - len(n_used)))

        opts = dbmacro.DbOptions(source_note="%s %s%s"
                                 % (tool, _ascii_note(src_abs),
                                    (" project=" + proj) if proj else ""),
                                 report={})
        rep["assumptions"].append(
            "--project=%s 记进报告 options.project 与宏头注释；目录宏的骨架（§l.3）里没有 "
            "ZONE 概念 ⇒ 它不改变生成物语义（§m.1 的可选参数列里也没有 --project，"
            "本轮任务命令要求接受它）" % (proj or "(未给)",))
        opts.uniquify = True                                  # §l.2 缺省（唯一名路线，R7）
        if suffix:
            opts.suffix = suffix
        opts.clean_first = bool(clean)
        if catalogue_user:
            opts.catalogue_user = catalogue_user
        if catalogue_stss:
            opts.catalogue_stss = catalogue_stss
        try:
            text = dbmacro.generate_db_macro(table, opts)     # 内含安全闸（§l.1）
        except dbmacro.DbMacroError as exc:
            raise InputError("目录宏生成被安全闸/校验拦下（契约 §l.1）：%s" % (exc,))
        try:
            dbmacro.write_db_macro(out_abs, text)             # 纯 ASCII + CRLF（§l.4）
        except (dbmacro.DbMacroError, OSError) as exc:
            raise InputError("写出目录宏失败：%s" % (exc,))

        info = opts.report or {}
        rep["db"]["generated"] = dict(info.get("stats") or {})
        rep["db"]["safety"] = dict(info.get("safety") or {})
        rep["db"]["losses"] = _loss_items(LOSS_DIRECTION[tool])
        rep["warnings"].extend(info.get("warnings") or [])
        rep["skipped"].extend(info.get("skipped") or [])
        rep["assumptions"].extend(info.get("assumptions") or [])
        rep["assumptions"].append(
            "生成的宏由用户在 PDMS 里自行执行（契约 §n-1）；本包不代跑 PDMS、不写任何 PDMS 数据库文件")
        rep["assumptions"].append(
            "报告 source_format 表示输入类型：本命令的输入是 PKPM 侧（%s）；"
            "（§a.2 的 Model.source_format 词表只服务 Model，报告另有 'pdmsdb' 表示 PDMS 目录宏）"
            % fmt)
        try:
            raw = open(out_abs, "rb").read()
        except OSError as exc:
            raise InputError("回读目录宏失败：%s" % (exc,))
        rep["stats"].update({"macro_bytes": len(raw), "macro_lines": raw.count(b"\r\n"),
                             "containers": info.get("containers") or {},
                             "families": len(info.get("families") or [])})
        return _finish(res, rep, EXIT_OK, t0)
    except InputError as exc:
        rep["errors"].append(str(exc))
        return _finish(res, rep, EXIT_INPUT, t0, error=str(exc))
    except ModelError as exc:
        rep["errors"].extend(exc.issues)
        return _finish(res, rep, EXIT_MODEL, t0,
                       error="Model.validate() 报出 %d 个 E- 项 ⇒ 不写产物（契约 §f.2 码 3）"
                             % len(exc.issues), stderr_issues=exc.issues)
    except Exception:
        tb = traceback.format_exc()
        rep["errors"].append(tb.strip().splitlines()[-1])
        return _finish(res, rep, EXIT_EXCEPTION, t0, error=tb)


def _run_db_parse(tool: str, src: str, out: str, secmap: Optional[str],
                  report: Optional[str], skeleton: str,
                  categories: Optional[Sequence[str]]) -> RunResult:
    """``db2jwd`` / ``db2pdt``（§m.1 第 7/8 行）：目录宏 → PKPM 截面定义 + 闭环校验。"""
    t0 = time.time()
    src_abs = os.path.abspath(src)
    out_abs = os.path.abspath(out)
    rep_path = os.path.abspath(report) if report else _default_report_path(out_abs)
    res = RunResult(tool=tool, source=src_abs, output=out_abs, report_path=rep_path)
    rep = _new_report(tool, src_abs, "pdmsdb", out_abs,
                      {"secmap": "", "extra": "", "skeleton": skeleton})
    rep["_report_path"] = rep_path
    rep["db"] = _new_db_block(src_abs)
    try:
        if not os.path.isfile(src_abs):
            raise InputError("输入文件不存在：%s" % (src_abs,))
        smap_path = _resolve_secmap_path(secmap, src_abs)
        smap = _load_secmap(smap_path, None)
        rep["options"]["secmap"] = smap_path or ""
        rep["options"]["extra"] = smap.extra_source if smap is not None else ""
        rep["stats"]["secmap"] = dict(smap.stats) if smap is not None else {}

        try:
            text, enc = dbparse.read_macro_text(src_abs)      # 编码自动判定（§l.5-1）
        except UnicodeDecodeError as exc:
            raise InputError("目录宏编码无法判定（utf-8-sig/utf-8/gbk 都失败）：%s" % (exc,))
        except OSError as exc:
            raise InputError("读取目录宏失败：%s" % (exc,))
        rep["db"]["safety"] = _parse_safety(text)
        rep["stats"]["macro"] = dbparse.macro_stats(text)
        rep["warnings"].append("目录宏编码判定为 %s（契约 §l.5-1）" % (enc,))

        builtin = sectionlib.load_builtin_table()
        table = dbparse.parse_db_macro(text, secmap=smap, builtin=builtin)
        if not len(table):
            raise InputError("解析出 0 条规格：这个文件不是 PDMS 目录/规格宏"
                             "（判据见契约 §l.5：必须有 SPCOMPONENT/SPRFILE）")
        rep["db"]["parsed"] = dbparse.parse_stats(table)
        rep["warnings"].extend(rep["db"]["parsed"].get("warnings") or [])
        rep["db"]["cross_check"] = dbparse.cross_check(
            table, smap, match_path=smap_path or "", builtin=builtin)

        gen: Dict[str, Any] = {}
        sections = table.to_jwd_sections(report=gen)          # §k.1/§l.6
        rep["skipped"].extend(gen.get("skipped") or [])
        rep["warnings"].extend(gen.get("warnings") or [])
        rep["stats"]["reverse"] = {k: gen.get(k) for k in ("tables", "id_base",
                                                           "group_basis")}
        n_total = sum(len(v) for v in sections.values())
        rep["warnings"].append(
            "反算：目录宏 %d 条规格 → 可生成 %d 条记录（不可反算的族逐条见 skipped 与 "
            "db.closure.not_closable，§l.6/§12#18/#19）" % (len(table), n_total))

        if tool == "db2jwd":
            try:
                stats = jwd_write.write_jwd_sections(sections, out_abs)
            except (IOError, OSError, ValueError) as exc:
                raise InputError("写出 .jwd 失败：%s" % (exc,))
            try:
                model2 = jwd_read.read_jwd(out_abs)
            except (sqlite3.Error, OSError) as exc:
                raise InputError("回读 .jwd 失败：%s" % (exc,))
            via = sectionlib.table_from_jwd(model2)
            read_fmt = "jwd"
        else:
            try:
                stats = pdt_write.write_pdt_sections(
                    _pdt_sections_arg(sections, rep), out_abs,
                    pdt_write.PdtOptions(skeleton=skeleton))
            except (ValueError, OSError, IOError) as exc:
                raise InputError("写出 .pdt 失败：%s" % (exc,))
            try:
                model2 = pdt_read.read_pdt(out_abs)
            except (UnicodeDecodeError, OSError) as exc:
                raise InputError("回读 .pdt 失败：%s" % (exc,))
            via = sectionlib.table_from_pdt(model2)
            read_fmt = "pdt"
        rep["stats"]["write"] = stats
        rep["skipped"].extend(stats.get("skipped") or [])
        rep["warnings"].extend(stats.get("warnings") or [])
        rep["assumptions"].extend(stats.get("assumptions") or [])

        issues2 = model2.validate()                           # 产物自洽性（不含几何）
        errs2 = [s for s in issues2 if s.startswith("E-")]
        rep["stats"]["verify"] = {
            "read_back": read_fmt, "sections": len(model2.sections),
            "levels": len(model2.levels), "members": len(model2.members),
            "validate_E": errs2,
            "validate_W": [s for s in issues2 if s.startswith("W-")][:10],
        }
        rep["counts"] = model2.counts()
        rep["assumptions"].append(
            "counts 来自**读回产物**的 Model：本命令的产物只含截面定义 ⇒ members/slabs/walls "
            "均为 0（§l.6：这是截面定义文件，不含几何）")
        rep["warnings"].extend(model2.notes)
        if errs2:
            raise ModelError(errs2)

        closure = dbparse.closure_report(table, via, direction=LOSS_DIRECTION[tool])
        _merge_closure_reasons(closure, rep["skipped"])
        rep["db"]["closure"] = closure
        rep["db"]["losses"] = _loss_items(LOSS_DIRECTION[tool])
        rep["assumptions"].append(
            "闭环（§l.6）：产物的截面再喂回 %s 的同一路径（table_from_%s）与目录宏逐规格比对；"
            "not_closable 含族名与理由，differences 里的数值取整差异不算失败"
            % ("jwd2db" if tool == "db2jwd" else "pdt2db", read_fmt))
        return _finish(res, rep, EXIT_OK, t0)
    except InputError as exc:
        rep["errors"].append(str(exc))
        return _finish(res, rep, EXIT_INPUT, t0, error=str(exc))
    except ModelError as exc:
        rep["errors"].extend(exc.issues)
        return _finish(res, rep, EXIT_MODEL, t0,
                       error="产物读回后仍有 %d 个 E- 项 ⇒ 不认为成功（契约 §f.2 码 3）"
                             % len(exc.issues), stderr_issues=exc.issues)
    except Exception:
        tb = traceback.format_exc()
        rep["errors"].append(tb.strip().splitlines()[-1])
        return _finish(res, rep, EXIT_EXCEPTION, t0, error=tb)


def run_pdt2pdms(pdt: str, out: str, secmap: Optional[str] = None,
                 extra: Optional[str] = None, project: Optional[str] = None,
                 base: Sequence[float] = (0.0, 0.0, 0.0), angle: float = 0.0,
                 unit: str = "mm", report: Optional[str] = None,
                 categories: Optional[Sequence[str]] = None,
                 site_name: Optional[str] = None) -> RunResult:
    """``pdt2pdms``（§m.1 第 2 行）：``.pdt`` → PDMS 建模型宏（选项同 §f.1，``pdt`` 代替 ``jwd``）。

    ``site_name``：〔R7〕SITE 名（必填；.NET 直查试出后传入，引擎不改名）。
    """
    t0 = time.time()
    src = os.path.abspath(pdt)
    out_abs = os.path.abspath(out)
    rep_path = os.path.abspath(report) if report else _default_report_path(out_abs)
    res = RunResult(tool="pdt2pdms", source=src, output=out_abs, report_path=rep_path)
    rep = _new_report("pdt2pdms", src, "pdt", out_abs,
                      {"secmap": "", "extra": "", "project": project or "",
                       "site_name": site_name or "",
                       "base": [float(x) for x in base], "angle": float(angle),
                       "unit": unit})
    rep["_report_path"] = rep_path
    try:
        if not os.path.isfile(src):
            raise InputError("输入文件不存在：%s" % (src,))
        smap_path = _resolve_secmap_path(secmap, src)
        smap = _load_secmap(smap_path, extra)
        rep["options"]["secmap"] = smap_path or ""
        rep["options"]["extra"] = smap.extra_source if smap is not None else ""
        rep["stats"]["secmap"] = dict(smap.stats) if smap is not None else {}

        model = _read_model("pdt", src)
        rep["warnings"].extend(model.notes)
        proj = (project or "").strip()
        if not proj:
            proj = _project_from_notes(model.notes)
            if proj:
                rep["warnings"].append(
                    "未给 --project：从 notes 取到工程名 %r（契约 §f.1/§b.2）" % proj)
            else:
                proj = DEFAULT_PROJECT
                rep["assumptions"].append(
                    "未给 --project 且 .pdt 里没有工程名来源（§b.2 的工程名只来自 pkpmSysInfo）"
                    "⇒ ZONE 用缺省 %r（契约 §f.1）" % DEFAULT_PROJECT)
        rep["options"]["project"] = proj

        model, notes, sk = _apply_categories(model, categories)
        rep["skipped"].extend(sk)
        rep["warnings"].extend(notes)
        _validate_or_raise(model, rep)
        _emit_pdms_macro("pdt2pdms", model, out_abs, smap, proj, base, angle, unit, rep,
                         site_name=site_name or "")
        return _finish(res, rep, EXIT_OK, t0)
    except InputError as exc:
        rep["errors"].append(str(exc))
        return _finish(res, rep, EXIT_INPUT, t0, error=str(exc))
    except ModelError as exc:
        rep["errors"].extend(exc.issues)
        return _finish(res, rep, EXIT_MODEL, t0,
                       error="Model.validate() 报出 %d 个 E- 项 ⇒ 不写产物（契约 §f.2 码 3）"
                             % len(exc.issues), stderr_issues=exc.issues)
    except Exception:
        tb = traceback.format_exc()
        rep["errors"].append(tb.strip().splitlines()[-1])
        return _finish(res, rep, EXIT_EXCEPTION, t0, error=tb)


# --------------------------------------------------------------------------
# 〔R6〕auto2pdms：按文件头自动识别 .jwd / .pdt（用户实机反馈问题③）
# --------------------------------------------------------------------------

#: SQLite3 库的文件头魔数（§b.2：``.jwd`` 就是 SQLite3 库 ⇒ 前 16 字节即此串）
SQLITE_MAGIC = b"SQLite format 3"

#: ``.pdt`` 文本的识别标记（§b.4 的 13 段节头里最靠前的两个；GBK/UTF-8 解码后比对）
PDT_MARKERS = ("$VERSION", "$NODECOOR")

#: ``.pdt`` 首行形态（样本 ``1_PM.pdt`` 首行 = ``;File … saved …``；§b.4 的 ``;`` 注释行）
PDT_FIRST_LINE_PREFIX = ";File"

#: 识别时读取的文件头字节数（覆盖魔数、首行与 ``$VERSION``/``$NODECOOR`` 节头）
DETECT_HEAD_BYTES = 4096


def _decode_head(raw: bytes) -> Optional[str]:
    """按 GBK / UTF-8 严格解码文件头；两种编码都解不出 ⇒ ``None``。

    用增量解码器且 ``final=False``：文件头是按固定字节数**截断**读来的，末字节可能正好
    切开一个多字节字符——那不是"不是文本"的证据，所以只容忍**尾部不完整**，
    其余解码错误一律算解不出（禁止 ``errors='replace'``，契约 §g.1 的纪律）。
    """
    for enc in ("gbk", "utf-8"):
        dec = codecs.getincrementaldecoder(enc)("strict")
        try:
            return dec.decode(raw, False)
        except UnicodeDecodeError:
            continue
    return None


def detect_source_format(path: str) -> str:
    """读文件头判定来源格式，返回 ``'jwd'`` 或 ``'pdt'``；判不出即抛 :class:`InputError`。

    判据（**只按证据、不猜**；两条都是本包已冻结的格式事实）：

    * 前 16 字节含 ``SQLite format 3`` ⇒ ``'jwd'``（契约 §b.2：``.jwd`` 是 SQLite3 库）；
    * 否则按文本解码（GBK / UTF-8）：命中 ``$VERSION`` 或 ``$NODECOOR`` 节头，
      或**首个非空行**以 ``;File`` 开头 ⇒ ``'pdt'``（契约 §b.4 的 ``.pdt`` 形态）；
    * 两者都不像 ⇒ 抛 :class:`InputError`（退出码 2 的路径）：**不猜**、不静默按某一支处理。
    """
    if not os.path.isfile(path):
        raise InputError("输入文件不存在：%s" % (os.path.abspath(path),))
    try:
        with open(path, "rb") as fh:
            raw = fh.read(DETECT_HEAD_BYTES)
    except OSError as exc:
        raise InputError("读取输入文件失败：%s：%s" % (os.path.abspath(path), exc))
    if SQLITE_MAGIC in raw[:16]:
        return "jwd"
    text = _decode_head(raw)
    if text is not None:
        if any(m in text for m in PDT_MARKERS):
            return "pdt"
        head_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if head_lines and head_lines[0].startswith(PDT_FIRST_LINE_PREFIX):
            return "pdt"
    raise InputError(
        "无法自动识别输入格式（不猜）：%s —— 前 16 字节 %r 不是 SQLite3 魔数 %r；"
        "按文本解码（GBK/UTF-8）后也没有 .pdt 的特征（%s，或首个非空行以 %r 开头）。"
        "请显式指定方向：jwd2pdms（SQLite3 模型库）或 pdt2pdms（.pdt 文本）"
        % (os.path.abspath(path), raw[:16], SQLITE_MAGIC,
           " 或 ".join("含 %s" % m for m in PDT_MARKERS), PDT_FIRST_LINE_PREFIX))


def run_auto2pdms(src: str, out: str, secmap: Optional[str] = None,
                  extra: Optional[str] = None, project: Optional[str] = None,
                  base: Sequence[float] = (0.0, 0.0, 0.0), angle: float = 0.0,
                  unit: str = "mm", report: Optional[str] = None,
                  categories: Optional[Sequence[str]] = None,
                  site_name: Optional[str] = None) -> RunResult:
    """``auto2pdms``（〔R6〕用户实机反馈问题③）：自动识别 ``.jwd`` / ``.pdt`` → PDMS 宏。

    选项与 :func:`run_jwd2pdms` **逐项相同**（§f.1）。识别（:func:`detect_source_format`；
    判不出 ⇒ 退出码 2）之后**内部调用** :func:`run_jwd2pdms` 或 :func:`run_pdt2pdms`
    ——与命令行/窗体是**同一个执行函数**，不复制任何逻辑（契约 §f.3 的纪律对自动识别同样适用），
    因此缺省值、报告键、退出码、字节纪律与显式命令逐项一致。

    差异只有"身份"三处（机械可见，便于调用方区分本次是自动识别）：
    ``report.tool='auto2pdms'``、``report.options.auto_detected='jwd'|'pdt'``、
    ``assumptions`` 里一条说明；摘要首行也标出识别结果。

    ``site_name``：〔R7〕SITE 名（必填）——原样透传给 :func:`run_jwd2pdms` /
    :func:`run_pdt2pdms` 的**同一执行函数**（引擎不改名、不做 re 逻辑）。
    """
    t0 = time.time()
    src_abs = os.path.abspath(src)
    out_abs = os.path.abspath(out)
    rep_path = os.path.abspath(report) if report else _default_report_path(out_abs)
    res = RunResult(tool="auto2pdms", source=src_abs, output=out_abs, report_path=rep_path)
    rep = _new_report("auto2pdms", src_abs, "auto", out_abs,
                      {"secmap": "", "extra": "", "project": project or "",
                       "site_name": site_name or "",
                       "base": [float(x) for x in base], "angle": float(angle),
                       "unit": unit})
    rep["_report_path"] = rep_path
    try:
        fmt = detect_source_format(src_abs)             # 判不出 ⇒ InputError（码 2）
    except InputError as exc:
        rep["errors"].append(str(exc))
        return _finish(res, rep, EXIT_INPUT, t0, error=str(exc))
    rep["source_format"] = fmt                          # 识别结果（'jwd'/'pdt'）
    rep["options"]["auto_detected"] = fmt

    run = run_jwd2pdms if fmt == "jwd" else run_pdt2pdms
    res2 = run(src_abs, out_abs, secmap=secmap, extra=extra, project=project,
               base=base, angle=angle, unit=unit, report=rep_path,
               categories=categories, site_name=site_name)   # §f.3：同一执行函数

    # 回填 auto2pdms 身份（报告已由上面的执行函数写过一次 ⇒ 覆盖写成同一路径的最终版）
    res2.tool = "auto2pdms"
    rep2 = res2.report if isinstance(res2.report, dict) else {}
    rep2["tool"] = "auto2pdms"
    opts2 = rep2.setdefault("options", {})
    if isinstance(opts2, dict):
        opts2["auto_detected"] = fmt
    rep2.setdefault("assumptions", []).append(
        "auto2pdms：按文件头自动识别为 %s（%s）⇒ 内部调用 %s 的**同一执行函数**"
        "（不复制逻辑，契约 §f.3）；除本键与 tool 外，报告与显式命令逐项一致"
        % (fmt,
           "SQLite3 魔数" if fmt == "jwd"
           else "文本标记（%s / 首个非空行以 %r 开头）" % (" / ".join(PDT_MARKERS),
                                                        PDT_FIRST_LINE_PREFIX),
           "jwd2pdms" if fmt == "jwd" else "pdt2pdms"))
    try:
        _write_report(res2.report_path, rep2)
    except Exception as exc:                            # 回填失败不得让整次执行崩掉
        rep2.setdefault("warnings", []).append("auto2pdms 报告回填失败：%s" % (exc,))
    res2.lines = (["    auto2pdms：识别为 .%s ⇒ 走 %s 的同一执行函数"
                   % (fmt, "jwd2pdms" if fmt == "jwd" else "pdt2pdms")]
                  + _summary_lines("auto2pdms", res2.exit_code, res2.source, res2.output,
                                   res2.report_path, rep2, res2.elapsed, res2.error))
    return res2


def run_pdms2pdt(dump: str, out: str, secmap: Optional[str] = None,
                 dump_unit: str = "mm", report: Optional[str] = None,
                 skeleton: str = "full") -> RunResult:
    """``pdms2pdt``（§m.1 第 4 行）：PDMSDUMP → ``.pdt``（荷载只写段头，§j.6）。"""
    t0 = time.time()
    src = os.path.abspath(dump)
    out_abs = os.path.abspath(out)
    rep_path = os.path.abspath(report) if report else _default_report_path(out_abs)
    res = RunResult(tool="pdms2pdt", source=src, output=out_abs, report_path=rep_path)
    rep = _new_report("pdms2pdt", src, "pdmsdump", out_abs,
                      {"secmap": "", "extra": "", "dump_unit": dump_unit,
                       "skeleton": skeleton})
    rep["_report_path"] = rep_path
    try:
        if not os.path.isfile(src):
            raise InputError("输入文件不存在：%s" % (src,))
        smap_path = _resolve_secmap_path(secmap, src)
        smap = _load_secmap(smap_path, None)
        rep["options"]["secmap"] = smap_path or ""
        rep["options"]["extra"] = smap.extra_source if smap is not None else ""
        rep["stats"]["secmap"] = dict(smap.stats) if smap is not None else {}

        try:
            text = pdms_dump.load_dump(src)
        except UnicodeDecodeError as exc:
            raise InputError("dump 不是 GBK 编码（契约 §c.1）：%s" % (exc,))
        except OSError as exc:
            raise InputError("读取 dump 失败：%s" % (exc,))
        head = [ln for ln in text.splitlines() if ln.strip()]
        if head and head[0].split()[:1] != [pdms_dump.HEADER]:
            raise InputError("首行不是 %s（契约 §c.2）：%r" % (pdms_dump.HEADER, head[0][:60]))
        has_units = len(head) > 1 and head[1].split()[:1] == ["UNITS"]
        text, warn = _apply_dump_unit(text, has_units, dump_unit)
        rep["warnings"].extend(warn)

        pdms_dump.set_default_section_map(smap)
        try:
            model = pdms_dump.parse_dump(text)
        except pdms_dump.DumpSyntaxError as exc:
            raise InputError("dump 文法错误，退出码 2（契约 §c.3/§f.2）：%s" % (exc,))
        finally:
            pdms_dump.set_default_section_map(None)
        model.source = src
        rep["warnings"].extend(model.notes)
        _validate_or_raise(model, rep)

        block = _section_block_and_warnings(model, smap, rep, "pdms2pdt")
        del block
        try:
            stats = pdt_write.write_pdt(model, out_abs,
                                        pdt_write.PdtOptions(skeleton=skeleton))
        except (ValueError, OSError, IOError) as exc:
            raise InputError("写出 .pdt 失败：%s" % (exc,))
        rep["stats"].update(stats)
        rep["skipped"].extend(stats.get("skipped") or [])
        rep["warnings"].extend(stats.get("warnings") or [])
        rep["assumptions"].extend(stats.get("assumptions") or [])
        return _finish(res, rep, EXIT_OK, t0)
    except InputError as exc:
        rep["errors"].append(str(exc))
        return _finish(res, rep, EXIT_INPUT, t0, error=str(exc))
    except ModelError as exc:
        rep["errors"].extend(exc.issues)
        return _finish(res, rep, EXIT_MODEL, t0,
                       error="Model.validate() 报出 %d 个 E- 项 ⇒ 不写产物（契约 §f.2 码 3）"
                             % len(exc.issues), stderr_issues=exc.issues)
    except Exception:
        tb = traceback.format_exc()
        rep["errors"].append(tb.strip().splitlines()[-1])
        return _finish(res, rep, EXIT_EXCEPTION, t0, error=tb)


def _apply_dump_unit(text: str, has_units: bool, dump_unit: str) -> Tuple[str, List[str]]:
    """§f.1 的 ``--dump-unit``（仅当 dump 缺 ``UNITS`` 行时生效；见模块头第 1 条修正）。"""
    if not has_units:
        if dump_unit != "mm":
            lines = text.splitlines()
            for i, ln in enumerate(lines):
                if ln.strip():
                    lines.insert(i + 1, "UNITS %s" % dump_unit)
                    break
            return ("\r\n".join(lines),
                    ["dump 缺 UNITS 行 ⇒ 按 --dump-unit=%s 解析（CLI 在头部行后补了一行 "
                     "UNITS %s；契约 §f.1：--dump-unit 仅在此情况下生效）"
                     % (dump_unit, dump_unit)])
        return text, ["dump 缺 UNITS 行 ⇒ 按 --dump-unit 的缺省 mm 解析（契约 §c.1/§f.1）"]
    got = ""
    for ln in text.splitlines():
        if ln.strip().split()[:1] == ["UNITS"]:
            parts = ln.split()
            got = parts[1] if len(parts) > 1 else ""
            break
    if got != dump_unit:
        return text, ["dump 的 UNITS=%s 与 --dump-unit=%s 不一致 ⇒ 以 UNITS 行为准"
                      "（契约 §f.1）" % (got, dump_unit)]
    return text, []


def _pdt_sections_to_jwd_space(model: C.Model, rep: Dict[str, Any]) -> int:
    """``pdt2jwd``：把 ``.pdt`` 的 ``Section.dims``（文件字段名）折算到 §a.4 的键空间。

    ``pdt_read`` 按 §b.4 给的是 ``B1/H1/T1…``（文件字段名），而 ``write_jwd`` 吃 §a.4 的键
    （``B/H/d/…``）⇒ 用 ``sectionlib.table_from_pdt`` 的同一套折算规则（§3.3【事实】：
    ``Kind=1`` 的 ``B1=B``/``H1=H``、``Kind=3`` 的 ``B1=直径``、``Kind=39`` 的 ``B1=B``/``H1=H``）
    换成 ``Section``。``Kind=39`` 的 ``tf/tw`` 在 ``.pdt`` 里恒为 0 ⇒ **不从目录宏补**
    （§9.1：两条链路各自直连 PDMS，不绕道互转），缺就是缺，进报告。
    """
    table = sectionlib.table_from_pdt(model)
    n = 0
    for rec in table.recs:
        sid = int((rec.extra or {}).get("pdt_id") or 0)
        old = model.sections.get(sid)
        if old is None:
            continue
        new = rec.section(table=old.table)
        new.note = "；".join(x for x in (old.note, new.note) if x)
        if int(new.kind or 0) == 39:
            rep["warnings"].append(
                "截面 %s（Kind=39 型钢）：``.pdt`` 不提供板厚 ⇒ ``tf/tw`` 无法回算（§k.5 的 "
                "db2pdt loss 行）⇒ 该截面的 ShapeVal 会留空并进 skipped（不从目录宏补，§9.1）"
                % (old.name or old.id,))
        model.sections[sid] = new
        n += 1
    return n


def run_pdt2jwd(pdt: str, out: str, secmap: Optional[str] = None,
                report: Optional[str] = None,
                categories: Optional[Sequence[str]] = None) -> RunResult:
    """``pdt2jwd``（§m.1 第 10 行）：``.pdt`` → ``.jwd``（走规范模型）。"""
    t0 = time.time()
    src = os.path.abspath(pdt)
    out_abs = os.path.abspath(out)
    rep_path = os.path.abspath(report) if report else _default_report_path(out_abs)
    res = RunResult(tool="pdt2jwd", source=src, output=out_abs, report_path=rep_path)
    rep = _new_report("pdt2jwd", src, "pdt", out_abs, {"secmap": "", "extra": ""})
    rep["_report_path"] = rep_path
    try:
        if not os.path.isfile(src):
            raise InputError("输入文件不存在：%s" % (src,))
        smap_path = _resolve_secmap_path(secmap, src)
        smap = _load_secmap(smap_path, None)
        rep["options"]["secmap"] = smap_path or ""
        rep["options"]["extra"] = smap.extra_source if smap is not None else ""
        rep["stats"]["secmap"] = dict(smap.stats) if smap is not None else {}

        model = _read_model("pdt", src)
        rep["warnings"].extend(model.notes)
        n_norm = _pdt_sections_to_jwd_space(model, rep)
        rep["stats"]["sections_normalized"] = n_norm
        rep["assumptions"].append(
            "pdt2jwd：Section.dims 由 .pdt 的文件字段名（B1/H1/T1…，§b.4）折算到 §a.4 的键空间"
            "（%d 个截面；折算规则同 sectionlib.table_from_pdt，§3.3 的【事实】行）" % n_norm)
        model, notes, sk = _apply_categories(model, categories)
        rep["skipped"].extend(sk)
        rep["warnings"].extend(notes)
        _validate_or_raise(model, rep)
        _section_block_and_warnings(model, smap, rep, "pdt2jwd")
        try:
            stats = jwd_write.write_jwd(model, out_abs)
        except (IOError, OSError) as exc:
            raise InputError("写出 .jwd 失败：%s" % (exc,))
        except ValueError as exc:
            raise InputError("模型无法写成 .jwd：%s" % (exc,))
        rep["stats"].update(stats)
        rep["skipped"].extend(stats.get("skipped") or [])
        rep["warnings"].extend(stats.get("warnings") or [])
        return _finish(res, rep, EXIT_OK, t0)
    except InputError as exc:
        rep["errors"].append(str(exc))
        return _finish(res, rep, EXIT_INPUT, t0, error=str(exc))
    except ModelError as exc:
        rep["errors"].extend(exc.issues)
        return _finish(res, rep, EXIT_MODEL, t0,
                       error="Model.validate() 报出 %d 个 E- 项 ⇒ 不写产物（契约 §f.2 码 3）"
                             % len(exc.issues), stderr_issues=exc.issues)
    except Exception:
        tb = traceback.format_exc()
        rep["errors"].append(tb.strip().splitlines()[-1])
        return _finish(res, rep, EXIT_EXCEPTION, t0, error=tb)


def run_jwd2pdt(jwd: str, out: str, secmap: Optional[str] = None,
                extra: Optional[str] = None, report: Optional[str] = None,
                skeleton: str = "full",
                categories: Optional[Sequence[str]] = None) -> RunResult:
    """``jwd2pdt``（§m.1 第 9 行）：``.jwd`` → ``.pdt``（走规范模型；荷载只写段头）。"""
    t0 = time.time()
    src = os.path.abspath(jwd)
    out_abs = os.path.abspath(out)
    rep_path = os.path.abspath(report) if report else _default_report_path(out_abs)
    res = RunResult(tool="jwd2pdt", source=src, output=out_abs, report_path=rep_path)
    rep = _new_report("jwd2pdt", src, "jwd", out_abs,
                      {"secmap": "", "extra": "", "skeleton": skeleton})
    rep["_report_path"] = rep_path
    try:
        if not os.path.isfile(src):
            raise InputError("输入文件不存在：%s" % (src,))
        smap_path = _resolve_secmap_path(secmap, src)
        smap = _load_secmap(smap_path, extra)
        rep["options"]["secmap"] = smap_path or ""
        rep["options"]["extra"] = smap.extra_source if smap is not None else ""
        rep["stats"]["secmap"] = dict(smap.stats) if smap is not None else {}

        model = _read_model("jwd", src)
        rep["warnings"].extend(model.notes)
        model, notes, sk = _apply_categories(model, categories)
        rep["skipped"].extend(sk)
        rep["warnings"].extend(notes)
        _validate_or_raise(model, rep)
        _section_block_and_warnings(model, smap, rep, "jwd2pdt")
        try:
            stats = pdt_write.write_pdt(model, out_abs,
                                        pdt_write.PdtOptions(skeleton=skeleton))
        except (ValueError, OSError, IOError) as exc:
            raise InputError("写出 .pdt 失败：%s" % (exc,))
        rep["stats"].update(stats)
        rep["skipped"].extend(stats.get("skipped") or [])
        rep["warnings"].extend(stats.get("warnings") or [])
        rep["assumptions"].extend(stats.get("assumptions") or [])
        return _finish(res, rep, EXIT_OK, t0)
    except InputError as exc:
        rep["errors"].append(str(exc))
        return _finish(res, rep, EXIT_INPUT, t0, error=str(exc))
    except ModelError as exc:
        rep["errors"].extend(exc.issues)
        return _finish(res, rep, EXIT_MODEL, t0,
                       error="Model.validate() 报出 %d 个 E- 项 ⇒ 不写产物（契约 §f.2 码 3）"
                             % len(exc.issues), stderr_issues=exc.issues)
    except Exception:
        tb = traceback.format_exc()
        rep["errors"].append(tb.strip().splitlines()[-1])
        return _finish(res, rep, EXIT_EXCEPTION, t0, error=tb)


def run_jwd2db(jwd: str, out: str, secmap: Optional[str] = None,
               extra: Optional[str] = None, report: Optional[str] = None,
               suffix: Optional[str] = None, clean: bool = False,
               catalogue_user: Optional[str] = None,
               catalogue_stss: Optional[str] = None,
               project: Optional[str] = None,
               categories: Optional[Sequence[str]] = None) -> RunResult:
    """``jwd2db``（§m.1 第 5 行）：``.jwd`` 截面定义 → PDMS 目录 + 规格宏。"""
    return _run_db_generate("jwd2db", jwd, out, secmap, extra, report, suffix, clean,
                            catalogue_user, catalogue_stss, categories, project)


def run_pdt2db(pdt: str, out: str, secmap: Optional[str] = None,
               extra: Optional[str] = None, report: Optional[str] = None,
               suffix: Optional[str] = None, clean: bool = False,
               catalogue_user: Optional[str] = None,
               catalogue_stss: Optional[str] = None,
               project: Optional[str] = None,
               categories: Optional[Sequence[str]] = None) -> RunResult:
    """``pdt2db``（§m.1 第 6 行）：``.pdt`` 截面定义 → PDMS 目录 + 规格宏。"""
    return _run_db_generate("pdt2db", pdt, out, secmap, extra, report, suffix, clean,
                            catalogue_user, catalogue_stss, categories, project)


def _pdt_sections_arg(sections: Dict[str, Any],
                      rep: Dict[str, Any]) -> Dict[str, List[Any]]:
    """``db2pdt`` 的 ``sections`` 实参：**按 id 去重**（见模块头「对调用方的修正」第 7 条）。

    ``SectionTable.to_jwd_sections`` 按 §k.1 规则 3 把**同一条**记录放进多个分组
    （Kind=1 → beam+col、Kind=303 → col+brace …）——那是 ``.jwd`` 的**三张表**需要的；
    而 ``.pdt`` 只有**一张** ``$DEFFRAMESECTION`` 表，``write_pdt_sections`` 会把三个列表
    里的每一次出现都写成一条记录（模块文档明说"按出现顺序各写一条记录"）⇒ 直接传三个列表
    会让同一规格写 2 条（5 行块 ×2）。这里按 ``Section.id`` 保留首条。
    """
    out: List[Any] = []
    seen: set = set()
    dup = 0
    for key in ("beam", "col", "brace"):
        for sec in (sections or {}).get(key) or []:
            sid = int(getattr(sec, "id", 0) or 0)
            if sid in seen:
                dup += 1
                continue
            seen.add(sid)
            out.append(sec)
    if dup:
        rep["warnings"].append(
            "db2pdt：表侧把同一记录放进多个分组（§k.1 规则 3，为 .jwd 的三张表设计），"
            "而 .pdt 只有一张 $DEFFRAMESECTION 表 ⇒ 按 id 去重 %d 条（保留首条），"
            "去重后 %d 条" % (dup, len(out)))
    return {"beam": out, "col": [], "brace": []}


def run_db2jwd(db: str, out: str, secmap: Optional[str] = None,
               report: Optional[str] = None,
               categories: Optional[Sequence[str]] = None) -> RunResult:
    """``db2jwd``（§m.1 第 7 行）：目录宏 → ``.jwd`` 截面定义（含 §l.6 闭环校验）。"""
    return _run_db_parse("db2jwd", db, out, secmap, report, "full", categories)


def run_db2pdt(db: str, out: str, secmap: Optional[str] = None,
               report: Optional[str] = None, skeleton: str = "full",
               categories: Optional[Sequence[str]] = None) -> RunResult:
    """``db2pdt``（§m.1 第 8 行）：目录宏 → ``.pdt`` 截面定义（含 §l.6 闭环校验）。"""
    return _run_db_parse("db2pdt", db, out, secmap, report, skeleton, categories)


def run_dbsections(db: Optional[str] = None, out: str = "",
                   fmt: Optional[str] = None, secmap: Optional[str] = None,
                   report: Optional[str] = None, from_builtin: bool = False,
                   categories: Optional[Sequence[str]] = None) -> RunResult:
    """``dbsections``（§m.1 第 11 行）：列出/导出截面字典与转化表（CSV/JSON）。"""
    t0 = time.time()
    out_abs = os.path.abspath(out) if out else ""
    src = os.path.abspath(db) if db else ""
    rep_path = (os.path.abspath(report) if report
                else (_default_report_path(out_abs) if out_abs else ""))
    res = RunResult(tool="dbsections", source=src or "(engine/section_table.csv)",
                    output=out_abs, report_path=rep_path)
    rep = _new_report("dbsections", src or sectionlib.BUILTIN_TABLE, "pdmsdb", out_abs,
                      {"secmap": "", "extra": "", "format": fmt or "",
                       "from_builtin": bool(from_builtin)})
    rep["_report_path"] = rep_path
    rep["db"] = _new_db_block(src or sectionlib.BUILTIN_TABLE)
    try:
        if not out_abs:
            raise InputError("必须给 --out（CSV 或 JSON 文件路径）")
        if not from_builtin and not src:
            raise InputError("必须给 <db.macro> 位置参数，或用 --from-builtin")
        if src and not os.path.isfile(src):
            raise InputError("输入文件不存在：%s" % (src,))

        smap = None
        if not from_builtin:
            smap_path = _resolve_secmap_path(secmap, src)
            smap = _load_secmap(smap_path, None)
            rep["options"]["secmap"] = smap_path or ""
            rep["options"]["extra"] = smap.extra_source if smap is not None else ""
            rep["stats"]["secmap"] = dict(smap.stats) if smap is not None else {}

        if from_builtin:
            table = sectionlib.load_builtin_table()
            rep["warnings"].append(
                "--from-builtin：直接导出内置转化表 %s（§k.2 的冻结数据文件；只读）"
                % sectionlib.BUILTIN_TABLE)
            problems = sectionlib.verify_builtin_table()
            if problems:
                rep["errors"].extend(problems)
                raise InputError("内置转化表自检未通过（计划 §9.4-14）：%s" % (problems[:3],))
            rep["assumptions"].append(
                "内置表自检通过（行数/列序/去 BOM 后 sha256 与 section_table.meta.json 一致）")
        else:
            try:
                text, enc = dbparse.read_macro_text(src)
            except UnicodeDecodeError as exc:
                raise InputError("目录宏编码无法判定：%s" % (exc,))
            except OSError as exc:
                raise InputError("读取目录宏失败：%s" % (exc,))
            rep["db"]["safety"] = _parse_safety(text)
            rep["stats"]["macro"] = dbparse.macro_stats(text)
            rep["warnings"].append("目录宏编码判定为 %s（契约 §l.5-1）" % (enc,))
            builtin = sectionlib.load_builtin_table()
            table = dbparse.parse_db_macro(text, secmap=smap, builtin=builtin)
            if not len(table):
                raise InputError("解析出 0 条规格：这个文件不是 PDMS 目录/规格宏"
                                 "（判据见契约 §l.5：必须有 SPCOMPONENT/SPRFILE）")
            rep["db"]["parsed"] = dbparse.parse_stats(table)
            rep["warnings"].extend(rep["db"]["parsed"].get("warnings") or [])
            rep["db"]["cross_check"] = dbparse.cross_check(
                table, smap, match_path=(smap.source if smap is not None else ""),
                builtin=builtin)

        name = os.path.basename(out_abs).lower()
        use_fmt = (fmt or ("json" if name.endswith(".json") else "csv")).lower()
        rep["options"]["format"] = use_fmt
        if from_builtin and use_fmt == "csv":
            data = table.to_csv().encode("utf-8")            # 带 BOM + CRLF（§k.2）
        elif use_fmt == "csv":
            data = table.to_csv().encode("utf-8")
        else:
            data = table.to_json().encode("utf-8")           # 确定性 JSON（§k.1）
        _ensure_parent(out_abs)
        try:
            with open(out_abs, "wb") as fh:
                fh.write(data)
        except OSError as exc:
            raise InputError("写出转化表失败：%s" % (exc,))
        rep["stats"].update({
            "table_rows": len(table),
            "table_columns": len(sectionlib.CSV_COLUMNS),
            "table_format": use_fmt,
            "table_bytes": len(data),
            "table_sha256": _sha256_bytes(data),
        })
        rep["assumptions"].append(
            "转化表按 §k.1 的序列化输出：CSV 用 to_csv()（UTF-8 带 BOM + CRLF，与 §k.2 的冻结"
            "文件逐字节同构），JSON 用 to_json()（确定性 + sort_keys，UTF-8 无 BOM）")
        return _finish(res, rep, EXIT_OK, t0)
    except InputError as exc:
        rep["errors"].append(str(exc))
        return _finish(res, rep, EXIT_INPUT, t0, error=str(exc))
    except ModelError as exc:                                # 本命令不建模型，防御性保留
        rep["errors"].extend(exc.issues)
        return _finish(res, rep, EXIT_MODEL, t0, error=str(exc), stderr_issues=exc.issues)
    except Exception:
        tb = traceback.format_exc()
        rep["errors"].append(tb.strip().splitlines()[-1])
        return _finish(res, rep, EXIT_EXCEPTION, t0, error=tb)


def _sha256_bytes(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------
# 命令行
# --------------------------------------------------------------------------

def _add_macro_opts(p, src_help: str, src_meta: str):
    """§f.1 的宏生成选项（``jwd2pdms``/``pdt2pdms``/``auto2pdms`` 共用；§m.1 第 1/2 行）。

    ``--site-name``〔R7〕：SITE 名。**必填**——.NET 侧执行前用 DbElement 直查逐个试名
    （``/PKPM2PDMS`` → ``/PKPM2PDMSre`` → … re99）试出第一个可用的，再经 ``--request`` 的
    ``site_name`` 键传给引擎（命令行批处理用本选项显式给）。引擎**不生成、不默认、不做 re 逻辑**；
    缺省为空 ⇒ 退出码 2（错误信息会写明责任在 .NET 侧）。
    """
    p.add_argument(src_meta, metavar="<%s>" % src_meta, help=src_help)
    p.add_argument("--out", required=True, metavar="<macro.mac>", help="输出的 PDMS 宏")
    p.add_argument("--site-name", dest="site_name", metavar="N",
                   help="SITE 名（如 /PKPM2PDMS）：由 .NET 侧直查试出的可用名，引擎原样使用；"
                        "引擎不默认、不改名（缺 ⇒ 退出码 2）")
    p.add_argument("--secmap", metavar="F",
                   help="截面匹配文件；省略取与输入同目录的 %s" % DEFAULT_SECMAP_NAME)
    p.add_argument("--extra", metavar="F",
                   help="补充映射文件；省略自动加载 engine/secmap_extra.txt（若存在）")
    p.add_argument("--project", metavar="N",
                   help="PDMS ZONE 名；省略取 pkpmSysInfo.ID=2，再不行用 %s" % DEFAULT_PROJECT)
    p.add_argument("--base", nargs=3, type=float, default=[0.0, 0.0, 0.0],
                   metavar=("E", "N", "U"), help="基点（单位 = --unit），缺省 0 0 0")
    p.add_argument("--angle", type=float, default=0.0, metavar="D",
                   help="平面转角（度，+U 俯视逆时针），缺省 0")
    p.add_argument("--unit", choices=("mm", "cm", "m"), default="mm",
                   help="宏内数值单位（只影响数值缩放；缺省 mm）")
    p.add_argument("--report", metavar="R.json", help="报告文件；省略按 --out 派生")


def _add_db_gen_opts(p, src_help: str, src_meta: str):
    """§m.1 第 5/6 行（``jwd2db``/``pdt2db``）的选项。

    ``--project`` **不在 §m.1 的可选参数列**里（那列只有 --secmap/--extra/--report/--suffix/
    --clean/--catalogue-*），但本轮任务的命令 #2 用了它（``jwd2db … --project JLCJ2``）⇒
    接受该选项，并把它放到**有明确落点**的两处：报告的 ``options.project`` 与宏头注释
    （纯 ASCII 注释，§l.1-5）；目录宏本身没有 ZONE 概念（§l.3 的骨架里没有），所以它
    **不改变**任何生成物语义。该偏离记在交付说明的 openIssues 里。
    """
    p.add_argument(src_meta, metavar="<%s>" % src_meta, help=src_help)
    p.add_argument("--out", required=True, metavar="<db.mac>", help="输出的目录+规格宏")
    p.add_argument("--secmap", metavar="F",
                   help="截面匹配文件；省略取与输入同目录的 %s" % DEFAULT_SECMAP_NAME)
    p.add_argument("--extra", metavar="F",
                   help="补充映射文件；省略自动加载 engine/secmap_extra.txt（若存在）")
    p.add_argument("--project", metavar="N",
                   help="工程名标签；只记进报告 options.project 与宏头注释"
                        "（目录宏没有 ZONE 概念；契约 §m.1 的可选参数列里没有它）")
    p.add_argument("--report", metavar="R.json", help="报告文件；省略按 --out 派生")
    p.add_argument("--suffix", metavar="S",
                   help="4 个顶层容器名的唯一后缀；省略用 _YYYYMMDD（契约 §l.2/§l.4）")
    p.add_argument("--clean", action="store_true",
                   help="生成清场版（OLD … DELETE … MEM，只清本包自己的容器；§l.3.5）")
    p.add_argument("--catalogue-user", dest="catalogue_user", metavar="N",
                   help="参数化族目录名（缺省 /PKPM2PDMS_USER；必须带 /PKPM2PDMS_ 前缀）")
    p.add_argument("--catalogue-stss", dest="catalogue_stss", metavar="N",
                   help="型钢库目录名（缺省 /PKPM2PDMS_STSS；必须带 /PKPM2PDMS_ 前缀）")


def build_parser() -> argparse.ArgumentParser:
    """§f.1 的三条（签名冻结）+ §m.1 的九条 R2 命令。"""
    p = argparse.ArgumentParser(
        prog="cli.py",
        description="PKPM2PDMS导入导出：.jwd / .pdt / PDMSDUMP / PDMS 目录宏的转换"
                    "（插件版本 2.1.0；契约模型 schema 版本 v%s）"
                    % C.CONTRACT_VERSION,
        epilog="退出码：0 成功；1 未捕获异常；2 参数/输入文件错误；3 Model 有 E- 项"
               "（不写产物）。报告缺省写在 <--out 同目录>\\<--out 基名>.report.json。"
               "荷载不做：不导出、不映射（R2 §9.3）。"
               "〔R7〕建模型的三条（jwd2pdms/pdt2pdms/auto2pdms）必须给 --site-name："
               "SITE 名由 .NET 侧执行前用 DbElement 直查试出可用名后传入，引擎不默认、"
               "不改名（--request 协议里是同名的 site_name 键）。",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="tool", metavar="{%s}" % ",".join(TOOLS))

    # ---- v1 三条（§f.1，签名不变）---------------------------------------
    a = sub.add_parser("jwd2pdms", help=".jwd（SQLite3）→ PDMS 宏 .mac（GBK+CRLF）",
                       description="PKPM .jwd → PDMS 目录宏（契约 §f.1）")
    _add_macro_opts(a, "PKPM 模型文件（SQLite3）", "jwd")

    a = sub.add_parser("pdt2pdms", help=".pdt → PDMS 宏 .mac（GBK+CRLF）",
                       description="PKPM .pdt → PDMS 目录宏（契约 §m.1 第 2 行）")
    _add_macro_opts(a, "PKPM .pdt 中间模型", "pdt")

    # 〔R6〕自动识别（问题③）：选项与 jwd2pdms 逐项相同，位置参数名 = `<src>`
    a = sub.add_parser("auto2pdms", help=".jwd/.pdt 自动识别 → PDMS 宏 .mac（GBK+CRLF）",
                       description="按**文件头**自动识别 PKPM 模型：SQLite3 魔数 ⇒ jwd2pdms；"
                                   "文本（$VERSION/$NODECOOR/行首 ;File）⇒ pdt2pdms；"
                                   "两者都不像 ⇒ 退出码 2（不猜）。其余与 jwd2pdms 逐项相同。")
    _add_macro_opts(a, "PKPM 模型文件：.jwd（SQLite3）或 .pdt（文本），按文件头自动识别", "src")

    b = sub.add_parser("pdms2jwd", help="PDMSDUMP 1.0 文本 → .jwd（SQLite3）",
                       description="PDMS 导出文本 → PKPM .jwd（契约 §f.1）")
    b.add_argument("dump", metavar="<dump.txt>", help="#PKPM2PDMS-PDMSDUMP 1.0 文本（GBK）")
    b.add_argument("--out", required=True, metavar="<out.jwd>", help="输出的 .jwd")
    b.add_argument("--secmap", metavar="F",
                   help="截面匹配文件；省略取与 <dump.txt> 同目录的 %s" % DEFAULT_SECMAP_NAME)
    b.add_argument("--dump-unit", dest="dump_unit", choices=("mm", "cm", "m"), default="mm",
                   help="dump 缺 UNITS 行时的单位；缺省 mm（有 UNITS 行时以该行为准）")
    b.add_argument("--report", metavar="R.json", help="报告文件；省略按 --out 派生")

    c = sub.add_parser("pdt2model", help=".pdt（GBK 文本）→ model.json（规范模型）",
                       description="PKPM .pdt → 规范模型 JSON（契约 §f.1）")
    c.add_argument("pdt", metavar="<pdt>", help="PKPM .pdt 中间模型")
    c.add_argument("--out", required=True, metavar="<model.json>", help="输出的 model.json")
    c.add_argument("--report", metavar="R.json", help="报告文件；省略按 --out 派生")

    # ---- R2：格式互转 ----------------------------------------------------
    d = sub.add_parser("pdms2pdt", help="PDMSDUMP 1.0 文本 → .pdt",
                       description="PDMS 导出文本 → PKPM .pdt（契约 §m.1 第 4 行）")
    d.add_argument("dump", metavar="<dump.txt>", help="#PKPM2PDMS-PDMSDUMP 1.0 文本（GBK）")
    d.add_argument("--out", required=True, metavar="<out.pdt>", help="输出的 .pdt")
    d.add_argument("--secmap", metavar="F",
                   help="截面匹配文件；省略取与 <dump.txt> 同目录的 %s" % DEFAULT_SECMAP_NAME)
    d.add_argument("--dump-unit", dest="dump_unit", choices=("mm", "cm", "m"), default="mm",
                   help="dump 缺 UNITS 行时的单位；缺省 mm（有 UNITS 行时以该行为准）")
    d.add_argument("--skeleton", choices=SKELETONS, default="full",
                   help="full（13 段，缺省）| sections-only（只写截面段，§j.7.6）")
    d.add_argument("--report", metavar="R.json", help="报告文件；省略按 --out 派生")

    e = sub.add_parser("jwd2pdt", help=".jwd → .pdt（走规范模型；荷载只写段头）",
                       description="PKPM .jwd → .pdt（契约 §m.1 第 9 行）")
    e.add_argument("jwd", metavar="<jwd>", help="PKPM 模型文件（SQLite3）")
    e.add_argument("--out", required=True, metavar="<out.pdt>", help="输出的 .pdt")
    e.add_argument("--secmap", metavar="F",
                   help="截面匹配文件；省略取与 <jwd> 同目录的 %s" % DEFAULT_SECMAP_NAME)
    e.add_argument("--extra", metavar="F",
                   help="补充映射文件；省略自动加载 engine/secmap_extra.txt（若存在）")
    e.add_argument("--skeleton", choices=SKELETONS, default="full",
                   help="full（13 段，缺省）| sections-only（§j.7.6）")
    e.add_argument("--report", metavar="R.json", help="报告文件；省略按 --out 派生")

    f = sub.add_parser("pdt2jwd", help=".pdt → .jwd（走规范模型）",
                       description="PKPM .pdt → .jwd（契约 §m.1 第 10 行）")
    f.add_argument("pdt", metavar="<pdt>", help="PKPM .pdt 中间模型")
    f.add_argument("--out", required=True, metavar="<out.jwd>", help="输出的 .jwd")
    f.add_argument("--secmap", metavar="F",
                   help="截面匹配文件；省略取与 <pdt> 同目录的 %s" % DEFAULT_SECMAP_NAME)
    f.add_argument("--report", metavar="R.json", help="报告文件；省略按 --out 派生")

    # ---- R2：数据库方向 --------------------------------------------------
    g = sub.add_parser("jwd2db", help=".jwd 截面定义 → PDMS 目录+规格宏",
                       description="PKPM 截面定义 → PDMS Catalogue+Specification 宏"
                                   "（契约 §m.1 第 5 行）")
    _add_db_gen_opts(g, "PKPM 模型文件（SQLite3）", "jwd")

    h = sub.add_parser("pdt2db", help=".pdt 截面定义 → PDMS 目录+规格宏",
                       description="PKPM 截面定义 → PDMS Catalogue+Specification 宏"
                                   "（契约 §m.1 第 6 行）")
    _add_db_gen_opts(h, "PKPM .pdt 中间模型", "pdt")

    i = sub.add_parser("db2jwd", help="PDMS 目录宏 → .jwd 截面定义（含闭环校验）",
                       description="PDMS 目录+规格宏 → PKPM .jwd 截面定义（契约 §m.1 第 7 行）")
    i.add_argument("db", metavar="<db.macro>", help="PDMS 目录+规格宏（UTF-8/GBK 自动判定）")
    i.add_argument("--out", required=True, metavar="<out.jwd>", help="输出的 .jwd")
    i.add_argument("--secmap", metavar="F",
                   help="截面匹配文件；省略取与 <db.macro> 同目录的 %s" % DEFAULT_SECMAP_NAME)
    i.add_argument("--report", metavar="R.json", help="报告文件；省略按 --out 派生")

    j = sub.add_parser("db2pdt", help="PDMS 目录宏 → .pdt 截面定义（含闭环校验）",
                       description="PDMS 目录+规格宏 → PKPM .pdt 截面定义（契约 §m.1 第 8 行）")
    j.add_argument("db", metavar="<db.macro>", help="PDMS 目录+规格宏（UTF-8/GBK 自动判定）")
    j.add_argument("--out", required=True, metavar="<out.pdt>", help="输出的 .pdt")
    j.add_argument("--secmap", metavar="F",
                   help="截面匹配文件；省略取与 <db.macro> 同目录的 %s" % DEFAULT_SECMAP_NAME)
    j.add_argument("--skeleton", choices=SKELETONS, default="full",
                   help="full（13 段，缺省）| sections-only（§j.7.6）")
    j.add_argument("--report", metavar="R.json", help="报告文件；省略按 --out 派生")

    k = sub.add_parser("dbsections", help="列出/导出截面字典与转化表（CSV/JSON）",
                       description="目录宏（或内置表）→ 截面转化表导出（契约 §m.1 第 11 行）")
    k.add_argument("db", metavar="<db.macro>", nargs="?",
                   help="PDMS 目录+规格宏；用 --from-builtin 时可省略")
    k.add_argument("--from-builtin", dest="from_builtin", action="store_true",
                   help="直接导出 engine/section_table.csv（§k.2 的冻结表）")
    k.add_argument("--out", required=True, metavar="<F.csv|F.json>", help="输出的 CSV/JSON")
    k.add_argument("--format", choices=("csv", "json"), default=None,
                   help="输出格式；省略按 --out 扩展名（.json → json，其余 csv）")
    k.add_argument("--secmap", metavar="F",
                   help="截面匹配文件；省略取与 <db.macro> 同目录的 %s" % DEFAULT_SECMAP_NAME)
    k.add_argument("--report", metavar="R.json", help="报告文件；省略按 --out 派生")
    return p


def _dispatch(args: argparse.Namespace) -> RunResult:
    if args.tool == "jwd2pdms":
        return run_jwd2pdms(args.jwd, args.out, secmap=args.secmap, extra=args.extra,
                            project=args.project, base=tuple(args.base), angle=args.angle,
                            unit=args.unit, report=args.report,
                            site_name=getattr(args, "site_name", None))
    if args.tool == "pdt2pdms":
        return run_pdt2pdms(args.pdt, args.out, secmap=args.secmap, extra=args.extra,
                            project=args.project, base=tuple(args.base), angle=args.angle,
                            unit=args.unit, report=args.report,
                            site_name=getattr(args, "site_name", None))
    if args.tool == "auto2pdms":
        return run_auto2pdms(args.src, args.out, secmap=args.secmap, extra=args.extra,
                             project=args.project, base=tuple(args.base), angle=args.angle,
                             unit=args.unit, report=args.report,
                             site_name=getattr(args, "site_name", None))
    if args.tool == "pdms2jwd":
        return run_pdms2jwd(args.dump, args.out, secmap=args.secmap,
                            dump_unit=args.dump_unit, report=args.report)
    if args.tool == "pdms2pdt":
        return run_pdms2pdt(args.dump, args.out, secmap=args.secmap,
                            dump_unit=args.dump_unit, report=args.report,
                            skeleton=args.skeleton)
    if args.tool == "pdt2model":
        return run_pdt2model(args.pdt, args.out, report=args.report)
    if args.tool == "jwd2pdt":
        return run_jwd2pdt(args.jwd, args.out, secmap=args.secmap, extra=args.extra,
                           report=args.report, skeleton=args.skeleton)
    if args.tool == "pdt2jwd":
        return run_pdt2jwd(args.pdt, args.out, secmap=args.secmap, report=args.report)
    if args.tool == "jwd2db":
        return run_jwd2db(args.jwd, args.out, secmap=args.secmap, extra=args.extra,
                          report=args.report, suffix=args.suffix, clean=args.clean,
                          catalogue_user=args.catalogue_user,
                          catalogue_stss=args.catalogue_stss, project=args.project)
    if args.tool == "pdt2db":
        return run_pdt2db(args.pdt, args.out, secmap=args.secmap, extra=args.extra,
                          report=args.report, suffix=args.suffix, clean=args.clean,
                          catalogue_user=args.catalogue_user,
                          catalogue_stss=args.catalogue_stss, project=args.project)
    if args.tool == "db2jwd":
        return run_db2jwd(args.db, args.out, secmap=args.secmap, report=args.report)
    if args.tool == "db2pdt":
        return run_db2pdt(args.db, args.out, secmap=args.secmap, report=args.report,
                          skeleton=args.skeleton)
    if args.tool == "dbsections":
        return run_dbsections(args.db, args.out, fmt=args.format, secmap=args.secmap,
                             report=args.report, from_builtin=args.from_builtin)
    raise InputError("未知子命令：%r（须 ∈ %s）" % (getattr(args, "tool", None), list(TOOLS)))


# --------------------------------------------------------------------------
# §m〔R3〕--request：引擎进程调用协议（§p.5；对用户不暴露，.NET 的 EngineRunner 用）
# --------------------------------------------------------------------------


def _subparser_of(parser: argparse.ArgumentParser, tool: str) -> argparse.ArgumentParser:
    """取子命令自己的 parser（用于把 args 键还原成**真实**的选项串，不靠猜）。"""
    for ga in parser._subparsers._group_actions if parser._subparsers else []:
        if tool in ga.choices:
            return ga.choices[tool]
    raise InputError("--request：tool=%r 不是已注册的子命令（须 ∈ %s）"
                     % (tool, list(TOOLS)))


def _request_to_argv(parser: argparse.ArgumentParser, tool: Any,
                     args_map: Any) -> List[str]:
    """把 ``--request`` 的 ``{"tool":…, "args":{…}}`` 还原成**等价命令行 argv**。

    还原后再走同一个 ``parser``/ :func:`_dispatch`（§p.5：「与命令行**同一执行函数**，
    ``cli.py`` 的实现不许分叉」），因此缺省值、校验、退出码与命令行逐字一致。

    键的约定（与 .NET ``EngineRunner.BuildRequest`` 对齐，pdms-net/EngineRunner.cs:17-18、71-72）：
    * 键 = CLI 长选项名去前导 ``--``（= argparse dest，如 ``secmap``/``out``/``base``/
      ``site_name``）；连字符选项按 dest 给也行（``dump_unit`` ≡ ``dump-unit``，还原时按
      parser 里**真实注册的选项串**写回，故 ``--dump-unit``/``--from-builtin`` 等不会被拼错）；
      〔R7〕``site_name`` 键 → ``--site-name``（SITE 名，三个建模型命令认；值 = .NET 直查
      试出的可用名 —— 引擎按原样使用，不改名）；
    * 位置参数（``jwd``/``pdt``/``dump``/``db``）用**子命令自己的位置 dest** 落位（按声明顺序）；
    * ``True`` ⇒ 加选项串（store_true）；``False``/``None``/``""`` ⇒ 省略（= CLI 缺省语义）；
    * 列表 ⇒ 逐项展开（``base`` 的三元组，§f.1）；数值 ⇒ 十进制字符串。
    """
    if not isinstance(tool, str) or not tool:
        raise InputError("--request：缺少 \"tool\" 字符串（§p.5 的 {\"tool\":…,\"args\":{…}}）")
    sub = _subparser_of(parser, tool)
    if args_map is None:
        args_map = {}
    if not isinstance(args_map, dict):
        raise InputError("--request：\"args\" 必须是对象，收到 %s" % (type(args_map).__name__,))

    pos_actions = [a for a in sub._actions if not a.option_strings]
    flag_of: Dict[str, str] = {}
    for a in sub._actions:
        for opt in a.option_strings:
            if opt.startswith("--"):
                flag_of[a.dest] = opt
                break

    pos_index = {a.dest: i for i, a in enumerate(pos_actions)}
    positionals: List[Any] = [""] * len(pos_actions)
    filled: Dict[str, bool] = {}
    rest: List[str] = []
    for key, val in args_map.items():
        if not isinstance(key, str) or not key:
            raise InputError("--request：args 的键必须是字符串，收到 %r" % (key,))
        dest = key.replace("-", "_")
        if tool == "auto2pdms" and dest in ("jwd", "pdt") and "src" in pos_index:
            # 〔R6〕auto2pdms 的源位置参数与 jwd2pdms 的 `jwd` / pdt2pdms 的 `pdt` 是**同一语义槽**
            # （同一个文件路径），故容忍 .NET 侧沿用旧键名；规范键是 `src`（子命令的位置 dest）。
            dest = "src"
        if dest in pos_index:
            if val is None or val == "" or val is False:
                continue
            filled[dest] = True
            if isinstance(val, (list, tuple)):
                positionals[pos_index[dest]] = [str(v) for v in val]
            else:
                positionals[pos_index[dest]] = str(val)
            continue
        if dest not in flag_of:
            allowed = sorted(list(flag_of) + list(pos_index))
            raise InputError("--request：tool=%s 没有参数 %r（可选键 %s）" % (tool, key, allowed))
        if val is None or val is False or val == "":
            continue                                # 缺省参数：省略（= CLI 语义）
        if val is True:
            rest.append(flag_of[dest])              # store_true（如 clean / from_builtin）
        elif isinstance(val, (list, tuple)):
            rest.append(flag_of[dest])
            rest.extend(str(v) for v in val)
        else:
            rest.append(flag_of[dest])
            rest.append(str(val))

    flat: List[str] = []
    for a, v in zip(pos_actions, positionals):
        if isinstance(v, list):
            flat.extend(v)
        elif v != "":
            flat.append(v)
        elif a.required:
            raise InputError("--request：tool=%s 缺必需参数 %r（§m.1 的必需参数列）"
                             % (tool, a.dest))
    return [tool] + flat + rest


def _load_request(parser: argparse.ArgumentParser, path: str) -> List[str]:
    """读 ``--request`` 的 UTF-8 JSON 文件并还原成 argv（§p.5：UTF-8；容忍 BOM）。"""
    if not os.path.isfile(path):
        raise InputError("--request 文件不存在：%s" % (os.path.abspath(path),))
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except UnicodeDecodeError as exc:
        raise InputError("--request 文件不是 UTF-8（§p.5）：%s：%s" % (path, exc))
    except json.JSONDecodeError as exc:
        raise InputError("--request 文件不是合法 JSON（§p.5）：%s：%s" % (path, exc))
    if not isinstance(data, dict):
        raise InputError("--request 文件顶层必须是对象（§p.5）：收到 %s"
                         % (type(data).__name__,))
    return _request_to_argv(parser, data.get("tool"), data.get("args"))


def main(argv: Optional[Sequence[str]] = None) -> int:
    """命令行入口：返回 §f.2 的退出码（stdout 打摘要 + 未解析清单）。

    支持契约 §m〔R3〕的 ``--request FILE``（§p.5 的引擎进程调用协议）：从 UTF-8 JSON 读
    ``{"tool":…, "args":{…}}`` 并还原成等价命令行（同一个 parser/dispatch，不分叉）。
    """
    for stream in (sys.stdout, sys.stderr):
        try:                                    # 控制台编码可能装不下中文 ⇒ 只放开 errors
            stream.reconfigure(errors="replace")
        except Exception:
            pass
    if not sys.stdout.isatty():                 # §p.5：非交互（.NET/进程管道）⇒ stdout 用 UTF-8
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
    raw = list(argv) if argv is not None else sys.argv[1:]
    parser = build_parser()
    if raw and raw[0] == "--request":           # §p.5：<engine_entry> --request <file>
        if len(raw) < 2:
            print("参数错误（退出码 %d）：--request 需要一个 JSON 文件路径" % EXIT_INPUT)
            return EXIT_INPUT
        try:
            raw = _load_request(parser, raw[1])
        except InputError as exc:
            print("参数错误（退出码 %d）：%s" % (EXIT_INPUT, exc))
            return EXIT_INPUT
    args = parser.parse_args(raw)
    if not getattr(args, "tool", None):
        parser.print_help(sys.stderr)
        return EXIT_INPUT
    try:
        res = _dispatch(args)
    except InputError as exc:                   # 参数级错误（没走到任何模型）
        print("参数错误（退出码 %d）：%s" % (EXIT_INPUT, exc))
        return EXIT_INPUT
    except Exception:
        print("未捕获异常（退出码 %d）：" % EXIT_EXCEPTION)
        traceback.print_exc()
        return EXIT_EXCEPTION
    sys.stdout.write(res.text() + "\n")
    if res.exit_code == EXIT_MODEL:
        for e in res.errors:                    # §f.2 码 3：问题清单打到 stderr
            sys.stderr.write(e + "\n")
    return res.exit_code


if __name__ == "__main__":
    sys.exit(main())
