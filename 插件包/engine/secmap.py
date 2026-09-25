# -*- coding: utf-8 -*-
"""PKPM-JWD导入导出 —— 截面匹配文件解析与 PDMS 规格解析（契约 §e 的唯一实现）。

契约：``spec/CONTRACT.md`` §b.1/§e（版本 ``CONTRACT_VERSION = "1.0"``）。

本模块只做三件事：

1. **解析「PKPM 截面名 → PDMS 等级库规格路径」映射文件**（用户原件
   ``PKPM转PDMS截面匹配文件.txt`` 与补充文件 ``secmap_extra.txt`` 同一套语法）；
2. ``resolve(section, kind)``：按契约 §e.1/§e.1a 的**优先级**把一个 ``Section``
   解析成 PDMS 规格路径（或用户参数化族 / 推断族 + DESP 参数）；
3. ``reverse(spec_path)``：反查（PDMS 规格路径 → PKPM 截面名）；
   ``validate(catalogue_macro_path)``：把右值与目录宏里的 ``NEW SPCOMPONENT`` 集合比对。

映射文件语法（§e.2，全部为原件实测事实；本模块**只读**，禁止写用户原件）::

    * GBK、CRLF、无 BOM（用户原件实测 3,023 物理行）
    * ``//`` 开头 = 注释；空白行忽略；整行只有 ``/`` 的分隔线也当注释
    * 数据行 ``<PKPM 名>,<空白><PDMS 路径>``；逗号两侧空白随意；
      右值可能**缺前导 ``/``**（原件 L2979-2982 实测 4 条）⇒ 补齐
    * **补充文件**里还允许一种指令行（§e.4a）：``@FAMILY <kind> = <族键|none>``
      —— 声明/停用"``Kind=<kind>`` 的推断族"（§e.1a）。未知族键记 warnings 且不启用
    * 比较**严格区分大小写**（原件同时存在 ``L25X3`` 与 ``3-L25x16x3``）
    * 左值在原件里实测 **0 重复**；重复时后加载者覆盖，并记进 :attr:`SectionMap.warnings`

``Resolution.source`` 的取值：本模块按契约 §e.1/§e.1a 的**五级**给出
``'name' | 'shapeval' | 'family' | 'none'``（``status='inferred'`` 也用 ``'family'``，
因为它是按族判定而非原件里写明的映射；见 §e.1a）。（``canonical.py`` 的注释里另列了一个
``'extra'``；§e.1 是接口条款，故以其为准：命中的是「原名键」还是「解码候选键」
与映射来自原件还是补充文件无关——补充文件的介入通过 :attr:`SectionMap.warnings` 留痕。）

加载顺序（§e.4）：**原件 → 补充文件**；同名左值以补充文件为准。
``load(path, extra_path=None)`` 的 ``extra_path=None`` 表示「用默认补充文件
``engine/secmap_extra.txt``（若存在）」——这正是契约 §f.1 里 ``--extra`` 省略时的缺省行为；
给定其它文件时**只**加载该文件（默认补充文件不再加载）。

本模块只依赖标准库与 ``canonical``（契约 §b.5）。
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Tuple

try:                                     # 直接运行 / 测试把 engine/ 加进 sys.path
    from canonical import (INFERRED, PARAMETRIC, RESOLVED, UNRESOLVED, Section, Resolution)
except ImportError:                      # pragma: no cover - 作为包导入（python -m engine.cli）
    from .canonical import (INFERRED, PARAMETRIC, RESOLVED, UNRESOLVED, Section, Resolution)

#: ``load(..., extra_path=None)`` 时自动尝试的补充文件（契约 §e.4 / §f.1）
DEFAULT_EXTRA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "secmap_extra.txt")

#: ``resolve(section, kind)`` 允许的构件类别（契约 §e.6）
RESOLVE_KINDS = ("beam", "col", "brace", "slab", "wall")

#: 用户参数化族（契约 §e.3）：族键 -> (spec_path, DESP 参数顺序)
FAMILY_RECT = "RECT"
FAMILY_H = "H"
FAMILY_CIRCLE = "CIRCLE"                 # §e.3 的 Kind=3 推断族（§e.1a）
FAMILY_SPEC = {
    FAMILY_RECT: "/USER_RECT-SPEC/Rectangle_Profile",
    FAMILY_H: "/USER_H-SPEC/H_Profile",
    FAMILY_CIRCLE: "/USER_CIRCLE-SPEC/Circle_Profile",
}

#: 推断族的 DESP 参数名（按 DESP[1..n] 顺序；取自目录宏 DTSET 的 ``DKEY``，契约 §e.3）
FAMILY_PARAM_NAMES = {
    FAMILY_CIRCLE: ("d",),               # /USER_CIRCLE 的唯一参数：DKEY D → ATTRIB DESP[1]
}

#: 推断族必须随产物给出的**证据链**与**残余风险**（文本照抄契约 §e.3 的 Kind=3 行与变更记录 §0.4-1；
#: 改动前先改契约——本模块不得自造语义）。
FAMILY_EVIDENCE = {
    FAMILY_CIRCLE: (
        "1_PM.pdt:2387-2388 SHAPE=3/KIND=3 B1=4800 NAME=圆形4800（B1=直径）；"
        "同一 JLCJ2 模型把 薄壁方钢管: B20 归 Kind=303（pkpmBraceSect ID=62965）⇒ 排除方管；"
        "PKPM（PDMS数据库）.txt:2502-2513 /USER_CIRCLE 的 DTSET 唯一参数 DKEY D→ATTRIB DESP[1]；"
        "PKPM转PDMS截面匹配文件.txt:27 CIRCLE→/USER_CIRCLE-SPEC/Circle_Profile"
    ),
}

#: 推断族的残余风险（写进 ``Resolution.reason``，随报告与宏注释一起交付）
FAMILY_RISK = {
    FAMILY_CIRCLE: (
        "单尺寸截面的族别按证据判为圆形（实心圆钢，dim=直径）；不能 100% 排除是别的单尺寸族，"
        "影响面仅本样本的屋面水平支撑。若实为别的族：改 engine/secmap_extra.txt 的 "
        "@FAMILY <kind> 行；要停用推断改回 unresolved 写 @FAMILY <kind> = none"
    ),
}

#: 补充文件的指令行：``@FAMILY <kind> = <族键|none>``（契约 §e.4a；唯一允许的非"左值,右值"行）
_RE_FAMILY_RULE = re.compile(r"^@FAMILY\s+(-?\d+)\s*=\s*([A-Za-z_][A-Za-z_0-9]*|none|-)\s*$",
                             re.IGNORECASE)

_RE_SPCOMPONENT = re.compile(r"^\s*NEW\s+SPCOMPONENT\s+(\S+)", re.IGNORECASE)
_RE_SPRFILE = re.compile(r"^\s*NEW\s+SPRFILE\s+(\S+)", re.IGNORECASE)
_RE_COMMENT = re.compile(r"^\s*(--|\$\*)")


def _norm_spec(text: str) -> str:
    """右值归一化（契约 §e.2）：合并内部空白 + 补齐前导 ``/``；**不改大小写**。"""
    r = " ".join((text or "").split())
    if r and not r.startswith("/"):
        r = "/" + r
    return r


def _is_slash_rule(s: str) -> bool:
    """整行只由 ``/`` 组成的分隔线（原件实测 0 条，容错保留，§e.2）。"""
    return bool(s) and set(s) == {"/"}


def _num(text) -> Optional[float]:
    try:
        return float(str(text).strip())
    except (TypeError, ValueError):
        return None


def _fmt_num(v: float) -> str:
    """``%g`` 风格的紧凑数字串（键里用；750.0 -> '750'）。"""
    return "%g" % float(v)


class SectionMap(object):
    """截面匹配文件（原件 + 可选补充文件）的双向映射。

    公开属性（供 CLI / report.json 取用）::

        entries       原件数据行 [(行号, 左值, 右值), ...]（按文件顺序）
        extra_entries 补充文件数据行（同上）
        warnings      加载期的非致命问题（重复左值被覆盖等，契约 §e.2 要求记账）
        stats         计数统计（见 :meth:`load` 的说明）

    纯函数式：``resolve`` / ``reverse`` 不改变实例状态（契约 §e.6）。
    """

    # ------------------------------------------------------------------ 构造
    def __init__(self, source: str = "", extra_source: str = ""):
        self.source = source                  # 匹配文件（原件）路径
        self.extra_source = extra_source      # 实际加载的补充文件路径（'' = 未加载）
        self.entries: List[Tuple[int, str, str]] = []
        self.extra_entries: List[Tuple[int, str, str]] = []
        self.warnings: List[str] = []
        self.stats: Dict[str, object] = {}
        self.family_rules: Dict[int, str] = {}  # Kind -> 推断族键（'none' = 停用），见 §e.4a
        self._fwd: Dict[str, str] = {}        # 左值 -> 右值（补充文件优先）
        self._fwd_origin: Dict[str, str] = {}  # 左值 -> 'file' | 'extra'
        self._rev: Dict[str, str] = {}        # 右值 -> 首个左值（加载顺序）

    # ------------------------------------------------------------------ 解析
    @staticmethod
    def _parse_text(text: str, path: str) -> Tuple[List[Tuple[int, str, str]],
                                                   Dict[str, int], List[str],
                                                   List[Tuple[int, int, str]]]:
        """按 §e.2 解析一份映射文件文本（外加 §e.4a 的指令行）。

        返回 ``(entries, counters, problems, family_rules)``；``problems`` 是"无法解析的行"
        （原件实测 0 条，不静默丢弃）。``family_rules`` 是 ``@FAMILY`` 指令
        ``[(行号, Kind, 族键或 'none'), …]``（按文件顺序，调用方按"后加载者覆盖"合并）。
        """
        entries: List[Tuple[int, str, str]] = []
        family_rules: List[Tuple[int, int, str]] = []
        counters = {"lines": 0, "data": 0, "comments": 0, "blank": 0,
                    "slash_rule": 0, "unparsable": 0, "family_rules": 0}
        problems: List[str] = []
        # 行数口径与契约附录 B.2 一致（原文 3,023 行 = 3022 个 CRLF + 末尾空行）
        body = text.replace("\r\n", "\n").replace("\r", "\n")
        for lineno, line in enumerate(body.split("\n"), 1):
            counters["lines"] += 1
            s = line.strip()
            if not s:
                counters["blank"] += 1
                continue
            if s.startswith("//"):
                counters["comments"] += 1
                continue
            if _is_slash_rule(s):
                counters["slash_rule"] += 1
                continue
            if s.startswith("@"):                       # §e.4a：指令行（唯一的非"左值,右值"形式）
                mo = _RE_FAMILY_RULE.match(s)
                if not mo:
                    counters["unparsable"] += 1
                    problems.append("%s L%d 无法解析（只支持 @FAMILY <kind> = <族键|none>）：%r"
                                    % (path, lineno, s))
                    continue
                kind_no = int(mo.group(1))
                value = mo.group(2)
                value = "none" if value.lower() in ("none", "-") else value.upper()
                family_rules.append((lineno, kind_no, value))
                counters["family_rules"] += 1
                continue
            if "," not in s:
                counters["unparsable"] += 1
                problems.append("%s L%d 无法解析（无逗号）：%r" % (path, lineno, s))
                continue
            left, right = s.split(",", 1)
            left = left.strip()
            right = _norm_spec(right)
            if not left or not right:
                counters["unparsable"] += 1
                problems.append("%s L%d 无法解析（左值或右值为空）：%r" % (path, lineno, s))
                continue
            entries.append((lineno, left, right))
            counters["data"] += 1
        return entries, counters, problems, family_rules

    @classmethod
    def load(cls, path: str, extra_path: Optional[str] = None) -> "SectionMap":
        """读取匹配文件（契约 §b.1 / §e.4）。

        :param path: 用户原件（``PKPM转PDMS截面匹配文件.txt``）。**只读**。
        :param extra_path: 补充文件；``None`` ⇒ 若 ``engine/secmap_extra.txt`` 存在则加载它
            （= 契约 §f.1 中 ``--extra`` 省略时的缺省行为），否则不加载补充文件。
            显式给出的路径不存在 ⇒ ``FileNotFoundError``（调用方按 §f.2 码 2 处理）。

        ``stats`` 的键：``lines/data/comments/blank/slash_rule/unparsable``（原件）、
        ``extra_*`` 同名前缀（补充文件）、``spec_prefixes``（**原件**的右值规格前缀个数，
        契约附录 B.2 的 53 就是它）、``extra_spec_prefixes``、
        ``family_rules``（生效的 ``@FAMILY`` 指令 ``{kind: 族键}``，§e.4a）。
        """
        self = cls(source=path)

        with open(path, "rb") as fh:
            raw = fh.read()
        try:
            text = raw.decode("gbk")
        except UnicodeDecodeError as exc:      # 契约 §g.1：禁止 errors='replace'
            raise ValueError("匹配文件不是 GBK 编码（契约 §e.2）：%s：%s" % (path, exc))

        entries, counters, problems, rules = cls._parse_text(text, path)
        self.entries = entries
        self.warnings.extend(problems)

        # 补充文件：None ⇒ 尝试默认文件；'' ⇒ 显式不加载
        chosen = extra_path
        if chosen is None:
            chosen = DEFAULT_EXTRA_FILE if os.path.isfile(DEFAULT_EXTRA_FILE) else ""
        if chosen:
            if not os.path.isfile(chosen):
                raise FileNotFoundError("补充映射文件不存在：%s" % chosen)
            with open(chosen, "rb") as fh:
                eraw = fh.read()
            try:
                etext = eraw.decode("gbk")
            except UnicodeDecodeError as exc:
                raise ValueError("补充映射文件不是 GBK 编码（契约 §e.4）：%s：%s"
                                 % (chosen, exc))
            e_entries, e_counters, e_problems, e_rules = cls._parse_text(etext, chosen)
            self.extra_entries = e_entries
            self.extra_source = chosen
            self.warnings.extend(e_problems)
        else:
            e_counters = {"lines": 0, "comments": 0, "blank": 0,
                          "unparsable": 0, "family_rules": 0}
            e_rules = []

        # ---- 合并（原件 → 补充；同名覆盖并记 warnings，§e.2/§e.4）
        for lineno, left, right in self.entries:
            if left in self._fwd:
                self.warnings.append(
                    "匹配文件左值重复：L%d %r -> %r（后者覆盖前者）" % (lineno, left, right))
            else:
                self._rev.setdefault(right, left)
            self._fwd[left] = right
            self._fwd_origin[left] = "file"
        for lineno, left, right in self.extra_entries:
            if left in self._fwd:
                self.warnings.append(
                    "补充文件覆盖原件左值：%s L%d %r -> %r（原值 %r）"
                    % (self.extra_source, lineno, left, right, self._fwd[left]))
            else:
                self._rev.setdefault(right, left)
            self._fwd[left] = right
            self._fwd_origin[left] = "extra"

        # ---- @FAMILY 指令合并（§e.4a：原件 → 补充，后加载者覆盖；未知族键不启用）
        for src, rlist in ((path, rules), (self.extra_source or "", e_rules)):
            for lineno, kind_no, value in rlist:
                if value != "none" and value not in FAMILY_SPEC:
                    self.warnings.append(
                        "%s L%d @FAMILY %d = %s：未知族键（已知 %s），该指令不生效"
                        % (src, lineno, kind_no, value, "/".join(sorted(FAMILY_SPEC))))
                    continue
                if kind_no in self.family_rules:
                    self.warnings.append(
                        "%s L%d @FAMILY %d 覆盖前一条规则 %r -> %r"
                        % (src, lineno, kind_no, self.family_rules[kind_no], value))
                self.family_rules[kind_no] = value

        # ---- 统计
        prefixes: Dict[str, int] = {}
        for _, _, right in self.entries:
            head = right.rsplit("/", 1)[0] if "/" in right else ""
            prefixes[head] = prefixes.get(head, 0) + 1
        e_prefixes: Dict[str, int] = {}
        for _, _, right in self.extra_entries:
            head = right.rsplit("/", 1)[0] if "/" in right else ""
            e_prefixes[head] = e_prefixes.get(head, 0) + 1
        self.stats = {
            "path": path,
            "extra_path": self.extra_source,
            "lines": counters["lines"],
            "data": counters["data"],
            "comments": counters["comments"],
            "blank": counters["blank"],
            "slash_rule": counters["slash_rule"],
            "unparsable": counters["unparsable"],
            "extra_lines": e_counters["lines"] if self.extra_entries or self.extra_source else 0,
            "extra_data": len(self.extra_entries),
            "extra_comments": e_counters["comments"] if self.extra_source else 0,
            "extra_blank": e_counters["blank"] if self.extra_source else 0,
            "extra_unparsable": e_counters["unparsable"] if self.extra_source else 0,
            "extra_family_rules": e_counters["family_rules"] if self.extra_source else 0,
            "family_rules": dict(self.family_rules),
            "spec_prefixes": len(prefixes),
            "extra_spec_prefixes": len(e_prefixes),
            "prefixes": prefixes,
            "extra_prefixes": e_prefixes,
            "unique_left": len(self._fwd),
        }
        return self

    # ------------------------------------------------------------- 基本信息
    def __len__(self) -> int:
        """**原件**的有效数据行数（契约基线 2,836）。"""
        return len(self.entries)

    def __contains__(self, pkpm_name: str) -> bool:
        return pkpm_name in self._fwd

    def spec_prefixes(self) -> Dict[str, int]:
        """**原件**的「规格前缀 -> 条数」（契约基线 53 个前缀）。"""
        return dict(self.stats.get("prefixes") or {})

    def origin_of(self, left: str) -> str:
        """某个左值来自 ``'file'``（原件）还是 ``'extra'``（补充文件）；未知返回 ``''``。"""
        return self._fwd_origin.get(left, "")

    # ------------------------------------------------------------- 候选键
    def candidate_keys(self, section: Section, kind: str = "beam") -> List[str]:
        """§e.1 的候选键生成器（按序尝试，命中即止）。

        ``report.json`` 的 ``sections.unresolved[].candidate_keys`` 直接取本方法的返回值
        （契约 §h）。顺序：原名 → ``<子类型>-<名>``(Kind=26) → ``<库族码>-<打包规格串>``
        (Kind=303) → ``T<厚度>``(板/墙) → ``矩<B>X<H>``(Kind=1) → ``<Kind>#<参数体>``。

        Kind=26/303 的两个键取自 ``Section.dims``（§a.4 冻结的解码结果由 ``*_read`` 产出，
        本模块**不**再实现一遍 ShapeVal 解码，契约 §b.1 纪律 1）。
        """
        if kind not in RESOLVE_KINDS:
            raise ValueError("kind 必须 ∈ %s，收到 %r" % (list(RESOLVE_KINDS), kind))

        dims = section.dims or {}
        cands: List[str] = []

        if section.name:                                   # 0) 原名（含中文/`[`/空格）
            cands.append(section.name)

        if section.kind == 26:                             # 1) <子类型>-<名>
            sub = dims.get("subtype")
            if sub is None and len(section.params) > 1:
                sub = section.params[1]
            if sub is not None and section.name:
                cands.append("%s-%s" % (_fmt_num(sub) if _num(sub) is not None else sub,
                                        section.name))

        if section.kind == 303:                            # 2) <库族码>-<打包规格串>
            lib = dims.get("lib_family")
            spec = dims.get("spec_str")
            if lib is not None and spec:
                cands.append("%s-%s" % (_fmt_num(lib) if _num(lib) is not None else lib,
                                        spec))

        if kind in ("slab", "wall"):                       # 3) T<厚度>
            t = self._thickness_of(section)
            if t:
                cands.append("T%s" % _fmt_num(t))

        if section.kind == 1:                              # 4) 矩<B>X<H>
            b, h = self._rect_bh(section)
            if b is not None and h is not None:
                cands.append("矩%sX%s" % (_fmt_num(b), _fmt_num(h)))

        if section.params:                                 # 5) <Kind>#<参数体>（兜底）
            cands.append("%s#%s" % (section.kind, ",".join(str(p) for p in section.params)))

        out: List[str] = []                                # 去重、保序、剔除空串
        for c in cands:
            if c and c not in out:
                out.append(c)
        return out

    # ------------------------------------------------------------- 解析
    def resolve(self, section: Section, kind: str) -> Resolution:
        """按 §e.1 的优先级解析截面（纯函数）。

        1. ``Section.name`` 在原件或补充文件中命中 → ``resolved`` / ``source='name'``
        2. 否则用 :meth:`candidate_keys` 的解码候选键命中 → ``resolved`` / ``source='shapeval'``
        3. 否则走用户参数化族（§e.3，Kind=1→RECT、Kind=2 对称→H）
           → ``parametric`` / ``source='family'``
        3b. 否则走**推断族**（§e.1a：由补充文件的 ``@FAMILY`` 指令启用，§e.3 的 Kind=3→CIRCLE）
           → ``inferred`` / ``source='family'``（带 ``evidence``，且可用 ``= none`` 改回第 4 级）
        4. 全都失败 → ``unresolved`` / ``source='none'``（:attr:`Resolution.reason`
           必须写清"缺什么证据"，措辞沿用契约 §e.5 的模板）

        ``kind ∈ {'beam','col','brace','slab','wall'}``；板/墙传
        ``Section.for_panel(kind, 厚度)`` 合成的 Section（§e.6）。
        命中的 ``spec_path`` 若属于 ``/USER_*-SPEC/`` 参数化族而 ``desp_params`` 为空，
        调用方应自行确认该族的参数是否需要显式给出（§e.3 只冻结了 RECT/H/CIRCLE 的顺序）。
        """
        if kind not in RESOLVE_KINDS:
            raise ValueError("kind 必须 ∈ %s，收到 %r" % (list(RESOLVE_KINDS), kind))

        cands = self.candidate_keys(section, kind)
        for idx, key in enumerate(cands):
            hit = self._fwd.get(key)
            if hit:
                return Resolution(spec_path=hit, desp_params=[],
                                  status=RESOLVED, reason="", pkpm_name=key,
                                  source="name" if idx == 0 else "shapeval")

        # ---- 3) 用户参数化族（§e.3 只列有证据的两个族）
        fam = self._family(section, kind)
        if fam is not None:
            fam_key, spec_path, desp, reason = fam
            if spec_path:
                return Resolution(spec_path=spec_path, desp_params=list(desp),
                                  status=PARAMETRIC, reason="", pkpm_name=fam_key,
                                  source="family")
            return Resolution(spec_path="", desp_params=[], status=UNRESOLVED,
                              reason=reason, pkpm_name=fam_key, source="none")

        # ---- 3b) 推断族（§e.1a；启用规则来自补充文件的 @FAMILY 指令，§e.4a）
        inf = self._inferred(section, kind)
        if inf is not None:
            return inf

        return Resolution(spec_path="", desp_params=[], status=UNRESOLVED,
                          reason=self._unresolved_reason(section, kind, cands),
                          pkpm_name=cands[0] if cands else "", source="none")

    # ------------------------------------------------------------- 反查
    def reverse(self, spec_path: str) -> Optional[str]:
        """PDMS 规格路径 → PKPM 截面名（契约 §e.6）。

        右值按 §e.2 归一化后查逆映射；多条左值映射到同一右值时返回**加载顺序中第一条**
        （原件优先，其次补充文件；各自按行序）。找不到返回 ``None``（调用方必须记进报告）。
        """
        return self._rev.get(_norm_spec(spec_path))

    # ------------------------------------------------------------- 校验
    def validate(self, catalogue_macro_path: str) -> List[str]:
        """逐条校验**原件**右值与 PDMS 目录宏的一致性（契约 §e.6）。

        目录宏（``PKPM（PDMS数据库）.txt``，本次实测 BOM=``EF BB BF``、70,301 行、
        ``NEW SPRFILE``×2920、``NEW SPCOMPONENT``×2920）以 ``utf-8-sig`` 读入，检查：

        1. 右值是否出现在 ``NEW SPCOMPONENT <path>`` 集合中
           ⇒ ``"specmap L<行号> <左值> -> <右值> : SPCOMPONENT 不存在"``
        2. 右值所属主 ``<X>-SPEC`` 是否在属主集合里
           ⇒ ``"… : 属主 <X>-SPEC 不存在"``

        返回值是问题清单（空 = 通过），**不阻断**流程；**禁止**自动改用户原件。
        已知原件有 **257** 条坏映射（``DOUBLE_L_EQUAL_CROSS`` 缺 ``C``、
        两个不等边双角钢缺 ``D``/``DUS``、1 条 ``组卷L`` 的规格名多了 ``-421``）——
        该基线是在**原件**上统计的，故本方法只检查 :attr:`entries`（原件行）；
        补充文件的行由 :meth:`extra_issues` 单独列出，以免两组数字混在一起
        （补充文件里的板/墙规格本来就不在钢材目录宏里，见 ``secmap_extra.txt`` 头部说明）。

        可行的纠正建议会附在消息尾部（"建议改为 …"）：在**同一属主**的现存 SPCOMPONENT
        里找与右值叶子名编辑距离最小且唯一的那一个（原件 257 条全部能给出唯一候选）。
        """
        comp, owners = _read_catalogue(catalogue_macro_path)
        return self._check_pairs(self.entries, comp, owners, "specmap", "")

    def extra_issues(self, catalogue_macro_path: str) -> List[str]:
        """同 :meth:`validate`，但检查**补充文件**的行（返回值同样空 = 通过）。

        这是契约 §e.6 之外的**附加**方法（§b.1 只冻结 ``validate``）：默认补充文件
        ``secmap_extra.txt`` 里的板/墙规格指向的是混凝土规格库，而 ``PKPM（PDMS数据库）.txt``
        只是钢材目录宏（57 个属主全为钢截面），因此这些行**必然**在这一项检查里报出——
        属于预期，不是错误。消息前缀用 ``specmap[补充]`` 以便与 §e.6 的清单区分。
        """
        comp, owners = _read_catalogue(catalogue_macro_path)
        return self._check_pairs(self.extra_entries, comp, owners, "specmap[补充]",
                                 self.extra_source)

    # ================================================================= 内部
    @staticmethod
    def _check_pairs(entries, comp, owners, prefix: str, origin: str) -> List[str]:
        out: List[str] = []
        for lineno, left, right in entries:
            if right not in comp:
                out.append("%s L%d %s -> %s : SPCOMPONENT 不存在%s"
                           % (prefix, lineno, left, right, _suggest(right, comp)))
            head = right.lstrip("/").split("/")
            owner = head[0] if len(head) >= 2 else ""
            if owner and owner not in owners:
                out.append("%s L%d %s -> %s%s : 属主 %s 不存在"
                           % (prefix, lineno, left, right,
                              "（补充文件 %s）" % origin if origin else "", owner))
        return out

    @staticmethod
    def _thickness_of(section: Section) -> Optional[float]:
        dims = section.dims or {}
        for key in ("T", "T1", "thickness"):
            v = _num(dims.get(key))
            if v:
                return v
        return None

    @staticmethod
    def _rect_bh(section: Section):
        """Kind=1 的 (B, H)。

        ``.jwd`` 的 §a.4 键是 ``B``/``H``；``.pdt`` 的 §b.4 键是 ``B1``/``H1``
        （pdt_format.md §2.6：SHAPE=1 时 ``B1×H1`` = 矩形宽×高），两种写法都接受。
        """
        dims = section.dims or {}
        b = _num(dims.get("B"))
        h = _num(dims.get("H"))
        if b is None:
            b = _num(dims.get("B1"))
        if h is None:
            h = _num(dims.get("H1"))
        if (b is None or h is None) and len(section.params) >= 2:
            if b is None:
                b = _num(section.params[0])
            if h is None:
                h = _num(section.params[1])
        return b, h

    @staticmethod
    def _params6(section: Section, names) -> List[Optional[float]]:
        """按 ``names`` 取 6 个参数：先 ``dims[名]``，再 ``params[下标]``（§a.4 的顺序）。"""
        dims = section.dims or {}
        out: List[Optional[float]] = []
        for idx, nm in enumerate(names):
            v = _num(dims.get(nm))
            if v is None and idx < len(section.params):
                v = _num(section.params[idx])
            out.append(v)
        return out

    def _family(self, section: Section, kind: str):
        """§e.3 的参数化族：命中返回 ``(族键, spec_path, desp, reason)``，否则 ``None``。

        ``spec_path`` 为空即"族内判定为不可解析"，此时 ``reason`` 说明缺什么证据。
        """
        if kind in ("slab", "wall"):
            return None                                  # 板/墙只能靠 T<厚度> 键（§e.3 末行）

        if section.kind == 1:
            b, h = self._rect_bh(section)
            if b is not None and h is not None:
                return (FAMILY_RECT, FAMILY_SPEC[FAMILY_RECT], [b, h], "")
            return (FAMILY_RECT, "", [],
                    "Kind=1 缺 B/H 参数，无法走 %s 参数化族（§e.3）；"
                    "请给出 dims['B']/dims['B1'] 与 dims['H']/dims['H1']"
                    % FAMILY_SPEC[FAMILY_RECT])

        if section.kind == 2:
            tw, h, b1, t1, b2, t2 = self._params6(
                section, ("Tw", "H", "B1", "T1", "B2", "T2"))
            if None in (tw, h, b1, t1, b2, t2):
                return (FAMILY_H, "", [],
                        "Kind=2 缺 Tw/H/B1/T1/B2/T2 中的参数，无法走 %s 参数化族（§e.3）"
                        % FAMILY_SPEC[FAMILY_H])
            if abs(b1 - b2) <= 1e-9 and abs(t1 - t2) <= 1e-9:
                # §e.3 / §12#4：对称时才出 [B1,B2,H,Tw,T1,T2]
                return (FAMILY_H, FAMILY_SPEC[FAMILY_H],
                        [b1, b2, h, tw, t1, t2], "")
            return (FAMILY_H, "", [],
                    "Kind=2 的 B1/T1 交错序未证实（jwd_format.md §9.3#5），无法确定 DESP 顺序")

        # Kind=3/26/303 与其它族：v1.0 **不**启用参数化族（§e.3 / §12#4#5）；
        # Kind=3 的**推断族**在 :meth:`_inferred` 里按 §e.1a/§e.4a 的数据规则处理。
        return None

    def _inferred(self, section: Section, kind: str) -> Optional[Resolution]:
        """§e.1a 的推断族（第 3b 级）：启用规则来自 ``self.family_rules``（数据，§e.4a）。

        * 没有该 ``Kind`` 的规则（或规则是 ``'none'`` 停用）⇒ 返回 ``None``（落到第 4 级 unresolved）；
        * 规则启用了某族但截面缺该族参数 ⇒ 返回 ``unresolved`` 并写明缺什么（禁止静默）；
        * 命中 ⇒ ``inferred``：``spec_path``/``desp_params`` 按 §e.3 的族定义给出，
          ``evidence`` 是证据链（§e.5a），``reason`` 是残余风险与改法。
        """
        if kind in ("slab", "wall"):
            return None                     # 板/墙只走 T<厚度> 键（§e.3 末行）
        rule = self.family_rules.get(section.kind)
        if not rule or rule == "none":
            return None
        spec_path = FAMILY_SPEC.get(rule)
        if not spec_path:                   # 未知族键：load() 已记 warnings 且不启用
            return None
        names = FAMILY_PARAM_NAMES.get(rule, ())
        dims = section.dims or {}
        desp: List[float] = []
        for i, nm in enumerate(names):
            v = _num(dims.get(nm))
            if v is None and i < len(section.params):
                v = _num(section.params[i])
            if v is None:
                return Resolution(
                    spec_path="", desp_params=[], status=UNRESOLVED, pkpm_name=rule,
                    source="none",
                    reason="Kind=%s 已启用推断族 %s（%s），但截面缺参数 %r（dims/params 均无）；"
                           "契约 §e.3" % (section.kind, rule, spec_path, nm))
            desp.append(v)
        return Resolution(spec_path=spec_path, desp_params=desp, status=INFERRED,
                          reason=FAMILY_RISK.get(rule, ""),
                          evidence=FAMILY_EVIDENCE.get(rule, ""), pkpm_name=rule,
                          source="family")

    def _unresolved_reason(self, section: Section, kind: str, cands: List[str]) -> str:
        """§e.5：``unresolved`` 必须写清"缺什么证据"（措辞沿用 §e.5 的模板）。"""
        if kind in ("slab", "wall"):
            t = self._thickness_of(section)
            what = "板" if kind == "slab" else "墙"
            if t:
                return "%s厚 T%s 无匹配条目，需在 secmap_extra.txt 给出 T%s → %s规格" % (
                    what, _fmt_num(t), _fmt_num(t), what)
            return "板/墙截面缺厚度参数，无法生成 T<厚度> 键（§e.3）"
        if section.kind == 3:
            rule = self.family_rules.get(3)
            extra = ""
            if section.table == "pdt":
                extra = ("；.pdt 的 KIND=3 已知是圆形（B1=直径，pdt_format.md §5.3），"
                         "可在 secmap_extra.txt 用原名键（如 圆形4800）显式点名")
            if rule == "none":
                where = os.path.basename(self.extra_source) if self.extra_source else "补充文件"
                return ("Kind=3 的推断族已被 @FAMILY 3 = none 停用（%s，契约 §e.4a），"
                        "无候选键命中；candidate keys %s%s" % (where, cands, extra))
            if rule:
                return ("Kind=3 启用了推断族 %s 但未解析成功（见上一条 reason）；"
                        "candidate keys %s%s" % (rule, cands, extra))
            if self.family_rules:
                extra += ("；本文件的 @FAMILY 规则 = %s" % (sorted(self.family_rules.items()),))
            return ("Kind=3 族别未定（jwd_format.md §9.3#1），无候选键命中；"
                    "可在 engine/secmap_extra.txt 用 @FAMILY 3 = CIRCLE 启用推断族"
                    "（§e.3/§e.4a）或按原名/兜底键补条目；candidate keys %s%s"
                    % (cands, extra))
        if section.kind in (26, 303):
            return ("Kind=%s 不走参数化族（族属性无法由 H/B 反推，§e.3）；"
                    "candidate keys %s 不在匹配文件，建议在 secmap_extra.txt 用 "
                    "<Kind>#<参数体> 键或原名键补条目" % (section.kind, cands))
        if section.name:
            return "Name %r 及 candidate keys %s 不在匹配文件；Kind=%s 建议在 secmap_extra.txt 补条目" % (
                section.name, cands, section.kind)
        return "Name 为空且 candidate keys %s 不在匹配文件；Kind=%s 建议在 secmap_extra.txt 补条目" % (
            cands, section.kind)


# --------------------------------------------------------------------------
# 目录宏读取（契约 §e.6）
# --------------------------------------------------------------------------

def _read_catalogue(path: str) -> Tuple[set, set]:
    """读 PDMS 目录宏，返回 ``(SPCOMPONENT 路径集合, 属主集合)``。

    原文带 UTF-8 BOM ⇒ ``encoding='utf-8-sig'``；注释行（``--`` / ``$*``）跳过。
    属主集合 = 每个 ``NEW SPCOMPONENT <path>`` 的第一段（本次实测 57 个），
    并并入 ``NEW SPRFILE <path>`` 里含属主段的名字（同样 57 个）。
    """
    comp = set()
    owners = set()
    with open(path, "r", encoding="utf-8-sig") as fh:
        for line in fh:
            if _RE_COMMENT.match(line):
                continue
            m = _RE_SPCOMPONENT.match(line)
            if m:
                name = m.group(1)
                comp.add(name)
                seg = name.lstrip("/").split("/")
                if len(seg) >= 2 and seg[0]:
                    owners.add(seg[0])
                continue
            m = _RE_SPRFILE.match(line)
            if m:
                seg = m.group(1).lstrip("/").split("/")
                if len(seg) >= 2 and seg[0]:
                    owners.add(seg[0])
    return comp, owners


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
        prev = cur
    return prev[len(b)]


def _suggest(right: str, comp: set) -> str:
    """给出"可用的纠正建议"：同一属主下编辑距离最小且唯一的现存 SPCOMPONENT。

    仅作建议（返回文本），**不**改原件、也**不**自动替换（契约 §e.6）。
    找不到唯一候选时返回空串。
    """
    if "/" not in right or not comp:
        return ""
    owner, leaf = right.rsplit("/", 1)
    cands = [c for c in comp if c.rsplit("/", 1)[0] == owner]
    if not cands:
        return ""
    cap = max(2, len(leaf) // 4)
    best, best_d, tie = None, cap + 1, False
    for c in sorted(cands):
        d = _levenshtein(leaf, c.rsplit("/", 1)[1])
        if d < best_d:
            best, best_d, tie = c, d, False
        elif d == best_d:
            tie = True
    if best is None or tie:
        return ""
    return "；建议改为 %s（同属主下最接近的现存截面，编辑距离 %d，原件未改）" % (best, best_d)
