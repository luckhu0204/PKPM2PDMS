# -*- coding: utf-8 -*-
"""PDMS 目录（Catalogue）/等级（Specification）宏 —— **解析器**（契约 v2 §l.5）。

输入：PDMS ``DB Listing``（Datal 模式）导出的宏文本（用户原件
``PKPM（PDMS数据库）.txt`` 就是这种），或本包 :mod:`dbmacro` 生成的宏。
输出：:class:`sectionlib.SectionTable`（每条 ``SPCOMPONENT`` → 一个 ``SectionRec``）。

--------------------------------------------------------------------------
契约 §l.5 的 12 条规则（实现逐条对应）
--------------------------------------------------------------------------
1. 编码自动判定 ``utf-8-sig`` → ``utf-8`` → ``gbk``（**不**用 ``errors='replace'``）；
2. 丢弃 ``--`` 注释行与 ``$S±``；空行忽略；
3. 合并 ``$`` 续行成逻辑行；续行允许是"无关键字的纯值行"；
4. 按 ``INPUT BEGIN … INPUT END … INPUT FINISH`` 切段（1..n 段）；无包裹时整文件一段；
5. 栈式块解析：``NEW <TYPE> [name]`` 入栈、``END`` 出栈；``END`` 可省；
6. ``OLD <TYPE> <target>`` **无 END**：遇下一个 ``NEW``/``OLD``/段尾/``LABEL``/``handle`` 即结束；
7. ``OLD`` 的类型名可省（``OLD /XI_Profile`` 与 ``OLD SPRFILE /XI_Profile`` 都支持）；
8. ``LABEL``/``handle``/``endhandle``/``RETURN`` ⇒ 关闭全部开放语句并丢弃它们；
9. token 化：``'…'`` 整体、``( … )`` 成对递归整体、名字整体取（可含 ``/``）；
10. 类型名同义词归一化（PLIN/PLINE、SPRF/SPRFILE、SPCO/SPCOMPONENT、SELE/SELEC、
    SPEC/SPECIFICATION、SPWL/SPWLD、PTSE|PTSET/PTSSET、GMSE|GMSET/GMSSET、CATE/CATALOGUE、
    DTSE/DTSET）；
11. 属性可"只有 key 没有值"（``LOCK``）；``KEY value`` 与 ``KEY=value`` 都接受；
12. ``PARA`` 逐项解析：按 ``DTSET`` 的 ``NUMB``/``DTIT`` 消化 token，**word 型参数允许 2 个
    token**（原件 ``/H_AMERICA``、``/H_EUROPE`` 的 ``S RSA``）；长度不一致 ⇒ ``warnings``。

--------------------------------------------------------------------------
除 §l.5 外另外吃透的坑（``_recon/db_pdms_catalogue.md`` §5.3 的 24 条）
--------------------------------------------------------------------------
``$`` 续行里的注释/空行、``ONERROR GOLABEL /ERRORn`` 的 n 不固定、嵌套 ``SELEC``（原件
1 处）、同一族可有 2 个 ``GMSSET``、``PKEY NA`` 是参考点、``NARE`` 缺失不是错误、
``PTSSET n of STCATEGORY X`` 的"序号+宿主"引用、``/PKPMDATA`` 空目录与其后的**顶层**
``OLD``、名字里含 ``/``、``LOCK`` 零值属性、``DTIT`` 的尾随空格、负数 ``(-180)`` 与
``-179.44`` 两种写法、表达式括号三层嵌套。

对外 API（契约 §l.5/§m.3）：

* ``parse_db_macro(text, **kw)`` / ``parse_db_macro_file(path, **kw)`` → ``SectionTable``；
* ``parse_macro(text)`` → 内部结构（元素树 + 警告），``macro_stats(text)`` → 元素计数；
* ``parse_stats(table)`` → 规模统计（报告的 ``db.parsed``）；
* ``cross_check(table, secmap, match_path=…, builtin=…)`` → §l.5 阈值表的归类报告；
* ``closure_report(src, via, direction)`` → §l.6 的 ``covered/not_closable/differences``。

``report.json`` 的 ``db`` 键接法（契约 §m.3）：``generated`` ← ``macro_stats(text)``、
``parsed`` ← ``parse_stats(table)``、``cross_check`` ← ``cross_check(...)``、
``closure`` ← ``closure_report(...)``、``safety`` ← ``dbmacro.safety_report(text, opts, …)``、
``losses`` ← ``sectionlib.SectionTable.loss_report(direction)``。

**参数装法**（与 sectionlib 的 ``validate()`` 对齐）：族的 ``DTSET`` 里同时有 ``PURP=PARA`` 与
``PURP=DESP`` 时（原件里 14 个型钢族就是这样），``rec.params`` **只装 DESP 参数**
（§k.1 的 ParamDef：``is_parametric=True ⇒ desp_index 1..N``），``PURP=PARA`` 的参数无损放在
``extra['para_params']``（含 ``dkey``/``numb``/``ppro``），全部具名参数另在
``extra['params_named']``。这样 ``sectionlib.to_pdms`` 给出的 ``desp_params`` 才是正确的
DESP 向量（否则会把 PARA 值当成 DESP 值）。
"""

import os
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

__all__ = [
    "DbParseError", "parse_macro", "parse_db_macro", "parse_db_macro_file",
    "macro_stats", "parse_stats", "cross_check", "closure_report",
    "read_macro_text", "normalize_name", "norm_pkpm", "norm_pkpm2",
    "split_para", "TYPE_SYNONYMS",
]

CONTRACTS = "CONTRACT v2 §(l)"

# ---------------------------------------------------------------------------
# 常量：类型同义词（规则 10）、属性名白名单（规则 11）
# ---------------------------------------------------------------------------

TYPE_SYNONYMS: Dict[str, str] = {
    "PLIN": "PLINE", "PLINE": "PLINE",
    "SPRF": "SPRFILE", "SPRFILE": "SPRFILE",
    "SPCO": "SPCOMPONENT", "SPCOMPONENT": "SPCOMPONENT",
    "SELE": "SELEC", "SELEC": "SELEC",
    "SPEC": "SPECIFICATION", "SPECIFICATION": "SPECIFICATION",
    "SPWL": "SPWLD", "SPWLD": "SPWLD",
    "PTSE": "PTSSET", "PTSET": "PTSSET", "PTSSET": "PTSSET",
    "GMSE": "GMSSET", "GMSET": "GMSSET", "GMSSET": "GMSSET",
    "CATE": "CATALOGUE", "CATALOGUE": "CATALOGUE",
    "DTSE": "DTSET", "DTSET": "DTSET",
}

#: 属性名白名单（``recon §1.3`` 的实测属性全集 + AVEVA ``.pmldat`` 样例里的点属性名）。
#: 不在表里的 token 一律当"值"（含 ``PURP CLEW`` 的 ``CLEW``、``CCON ANY`` 的 ``ANY``）。
ATTRIB_KEYS = frozenset("""
PURP STEX DKEY PPRO DPRO NUMB DTIT PTYP PKEY PX PY DX DY TUFL CLFL CCON PLAX
PXLE PYLE DXL DYL PANG PRAD PWID DRAD DWID GTYP PARA DESC LNTP QUES TANS
PSTR GSTR DTRE CATR NARE LOCK
PCON PSKEY PVIF PBOR PAXI PZAXI PDIS PZ PHEI PTCDIR
""".split())

#: **单值**属性：紧跟其后的 token 一定是它的值，**即使那个 token 本身是个关键字**。
#: 必须这样做的原因是 ``PURP PARA`` / ``NARE PLINE …`` / ``PSTR PTSSET …``：
#: ``PARA``、``PLINE``、``PTSSET`` 都同时是关键字，按"下一个是不是 key"判会丢值。
#: 例外：``LOCK`` 是零值属性（单行 ``LOCK``，recon §1.4-8），故不在此表内。
SINGLE_VALUE_KEYS = frozenset("""
PURP STEX DKEY PTYP GTYP NUMB DTIT PPRO DPRO DESC LNTP QUES TANS PSTR GSTR DTRE
CATR NARE PKEY PLAX CCON TUFL CLFL PX PY DX DY PXLE PYLE DXL DYL PANG PRAD PWID
DRAD DWID
""".split())

_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_KV_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)=(.*)$")
_REF_RE = re.compile(
    r"^(?:(?P<type>[A-Za-z]+)\s+)?(?P<idx>\d+)\s+of\s+(?P<owner_type>[A-Za-z]+)\s+"
    r"(?P<owner>\S+?)(?:\s+of\s+[A-Za-z]+\s+\S+)*$")

#: 尺寸类具名参数 → ``Section.dims`` 键（契约 §k.2 的"位置规则"）
SIZE_KEYS: Dict[str, str] = {
    "h": "H", "b": "B", "tw": "tw", "tf": "tf", "t": "t", "d": "d", "r": "r",
}
#: 用户参数化族的族码（conflicts §4.1/§4.4；§k.2 的 ``family`` 键）
PARAM_FAMILY_CODES = frozenset({2, 3, 15, 16, 17, 18, 20, 21, 22, 23, 24})
#: 归一化用（conflicts §2.6 / 21_final.py 的 ``norm``/``norm2``）
_CJK_RE = re.compile(r"^[\u4e00-\u9fff]+")
_NUMP_RE = re.compile(r"^\d+-")


class DbParseError(ValueError):
    """致命解析错误（编码、语法、结构）。契约要求"不许静默丢弃"。"""


# ---------------------------------------------------------------------------
# 读文件 / 归一化
# ---------------------------------------------------------------------------

def read_macro_text(path: str) -> Tuple[str, str]:
    """按 §l.5-1 自动判编码读宏文本，返回 ``(text, encoding)``。"""
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    raise DbParseError("无法用 utf-8-sig/utf-8/gbk 解码（契约 §l.5-1）：%s" % path)


def normalize_name(name: str) -> str:
    """名字归一化：去首尾空白、合并内部空白、补前导 ``/``；**不改大小写**（§e.2）。"""
    n = " ".join((name or "").split())
    if n and not n.startswith("/"):
        n = "/" + n
    return n


def norm_pkpm(name: str) -> str:
    """PKPM 名归一化：去中文前缀 + 大写（conflicts §2.6）。"""
    return _CJK_RE.sub("", (name or "").strip()).upper()


def norm_pkpm2(name: str) -> str:
    """再剥掉名字前缀里的 ``<数字>-``（conflicts §2.6 的 ``norm2``）。"""
    return _NUMP_RE.sub("", norm_pkpm(name))


def _num(text: Any) -> Optional[float]:
    s = str(text or "").strip()
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1].strip()
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _unquote(tok: str) -> str:
    """去掉一对单引号（``'BEAM'`` → ``BEAM``），保留内部空白（``DTIT 'B '`` → ``B ``）。"""
    s = tok or ""
    if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
        return s[1:-1]
    return s


def _unparen(tok: str) -> str:
    """去掉最外层一对括号（``( 500 )`` → ``500``）；不是整串一对括号则原样返回。"""
    s = (tok or "").strip()
    if s.startswith("(") and s.endswith(")"):
        depth = 0
        for i, ch in enumerate(s):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return s[1:-1].strip() if i == len(s) - 1 else s
    return s


# ---------------------------------------------------------------------------
# 词法：逻辑行（规则 2/3）与 token（规则 9）
# ---------------------------------------------------------------------------

def _logical_lines(text: str) -> List[Tuple[int, str]]:
    """→ ``[(首行行号, 逻辑行)]``：丢注释/``$S±``、合并 ``$`` 续行（含续行里的空行/注释）。"""
    body = text.replace("\r\n", "\n").replace("\r", "\n")
    out: List[Tuple[int, str]] = []
    pending: List[str] = []
    start = 0
    for lineno, raw in enumerate(body.split("\n"), 1):
        st = raw.rstrip().strip()
        if not st:
            continue                                   # 空行忽略（含续行中间的空行）
        if st.startswith("--") or st.startswith("$*"):
            continue                                   # 注释
        if re.match(r"^\$[A-Za-z+-]", st):
            continue                                   # $S- / $S+ / 其它宏命令
        if st.endswith("$"):
            if not pending:
                start = lineno
            pending.append(st[:-1].strip())
            continue
        if pending:
            pending.append(st)
            out.append((start, " ".join(pending)))
            pending = []
        else:
            out.append((lineno, st))
    if pending:
        out.append((start, " ".join(pending)))
    return out


def _tokenize(line: str) -> List[str]:
    """把一条逻辑行切成 token：``'…'`` 整体、``( … )``（可嵌套）整体、其余按空白。"""
    toks: List[str] = []
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        if ch.isspace():
            i += 1
            continue
        if ch == "'":
            j = line.find("'", i + 1)
            if j < 0:
                toks.append(line[i:])
                break
            toks.append(line[i:j + 1])
            i = j + 1
            continue
        if ch == "(":
            depth = 0
            j = i
            while j < n:
                if line[j] == "(":
                    depth += 1
                elif line[j] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            toks.append(line[i:min(j + 1, n)])
            i = j + 1
            continue
        j = i
        while j < n and (not line[j].isspace()) and line[j] not in "('":
            j += 1
        toks.append(line[i:j])
        i = j
    return [t for t in toks if t != ""]


# ---------------------------------------------------------------------------
# 内部元素模型
# ---------------------------------------------------------------------------

class Elem(object):
    """一个 ``NEW``/``OLD`` 元素。"""

    __slots__ = ("type", "name", "attrs", "kids", "line", "op", "raw_old", "text")

    def __init__(self, type_: str, name: str, line: int, op: str = "NEW",
                 raw_old: str = "", text: str = ""):
        self.type = type_
        self.name = name
        self.attrs: Dict[str, str] = {}
        self.kids: List["Elem"] = []
        self.line = line
        self.op = op
        self.raw_old = raw_old
        self.text = text

    def get(self, key: str, default: str = "") -> str:
        return self.attrs.get(key, default)

    def find(self, *types: str) -> List["Elem"]:
        want = set(types)
        return [k for k in self.kids if k.type in want]

    def __repr__(self):                                    # pragma: no cover
        return "<%s %s %s L%d>" % (self.op, self.type, self.name, self.line)


class _Macro(object):
    """解析后的宏（内部结构；:func:`macro_stats` 从它取计数）。"""

    def __init__(self):
        self.elements: List[Elem] = []         # 按出现顺序（含 OLD）
        self.roots: List[Elem] = []            # 顶层 NEW 元素（含 OLD 元素）
        self.olds: List[Elem] = []             # OLD 元素
        self.segments: List[List[Elem]] = []
        self.input_end_items: List[str] = []
        self.commands: List[str] = []          # ONERROR/INPUT/DELETE 等宏级命令原文
        self.deletes = 0
        self.onerror = ""
        self.label = ""
        self.warnings: List[str] = []
        self.lines = 0

    def by_type(self, *types: str) -> List[Elem]:
        want = set(types)
        return [el for el in self.elements if el.type in want and el.op == "NEW"]

    def first_of(self, *types: str) -> Optional[Elem]:
        want = set(types)
        for el in self.elements:
            if el.type in want and el.op == "NEW":
                return el
        return None


def _walk(el: Elem) -> Iterable[Elem]:
    for k in el.kids:
        yield k
        for g in _walk(k):
            yield g


def _build_parents(roots: Sequence[Elem]) -> Dict[int, Optional[Elem]]:
    """一次遍历建"子 → 直接父"映射（O(n)，不能用逐元素重扫）。"""
    parents: Dict[int, Optional[Elem]] = {id(r): None for r in roots}
    stack: List[Elem] = list(roots)
    while stack:
        el = stack.pop()
        for k in el.kids:
            parents[id(k)] = el
            stack.append(k)
    return parents


# ---------------------------------------------------------------------------
# 块解析（规则 4/5/6/7/8/11）
# ---------------------------------------------------------------------------

def _is_type_token(tok: str) -> bool:
    return tok.upper() in TYPE_SYNONYMS


def _norm_type(tok: str) -> str:
    return TYPE_SYNONYMS.get((tok or "").upper(), (tok or "").upper())


def _consume_attrs(el: Elem, toks: Sequence[str], i: int, macro: _Macro,
                   lineno: int) -> None:
    """从 ``toks[i:]`` 消化属性（规则 11 + 裸值追加）。"""
    last = ""
    while i < len(toks):
        tk = toks[i]
        mo = _KV_RE.match(tk)
        if mo:
            el.attrs[mo.group(1).upper()] = mo.group(2)
            last = mo.group(1).upper()
            i += 1
            continue
        up = tk.upper()
        if up in ATTRIB_KEYS:
            if up in SINGLE_VALUE_KEYS:
                if i + 1 < len(toks):
                    el.attrs[up] = toks[i + 1]
                    i += 2
                else:
                    el.attrs[up] = ""
                    i += 1
            elif i + 1 < len(toks) and toks[i + 1].upper() not in ATTRIB_KEYS \
                    and not _KV_RE.match(toks[i + 1]):
                el.attrs[up] = toks[i + 1]
                i += 2
            else:
                el.attrs[up] = ""
                i += 1
            last = up
            continue
        if last:                                   # 裸值行 / 多值（PARA …）挂到上一个字段
            cur = el.attrs.get(last, "")
            el.attrs[last] = (cur + " " + tk).strip() if cur else tk
        else:
            macro.warnings.append("L%d %s %s：无法归属的 token %r"
                                  % (lineno, el.type, el.name, tk))
        i += 1


def _split_old_target(toks: Sequence[str]) -> Tuple[List[str], int]:
    """``OLD`` 的目标（§l.5-6 修订，§0.4-9）：

    * ``['/XI_Profile']``（裸名）；
    * ``['1','of','STCATEGORY','/X']``（序号+宿主，recon §5.3-21）；
    * 带父级限定链（生成侧 §0.4-9 的安全形式）：
      ``['/X','of','STCATEGORY','/Y','of','STSECTION','/S','of','CATALOGUE','/C']``、
      ``['1','of','STCATEGORY','/Y','of','STSECTION','/S','of','CATALOGUE','/C']``。

    返回 ``(目标 token 列表, 目标消耗的 token 数)``；每个链节 = ``of <TYPE> <名字|序号>``。
    """
    if not toks:
        return [], 0
    n = len(toks)

    def chain(start: int) -> int:
        used = start
        while used + 2 < n + 1 and used < n and toks[used].upper() == "OF" \
                and used + 2 <= n - 1:
            used += 3
        return used

    if len(toks) >= 4 and toks[1].upper() == "OF":
        used = chain(4)                          # [N, of, TYPE, NAME] 或 [NAME, of, TYPE, NAME] 起头
        return list(toks[:used]), used
    if len(toks) >= 2 and toks[0].upper() == "OF":
        used = chain(2)
        return list(toks[:used]), 2 if used == 2 else used
    if len(toks) >= 4 and toks[2].upper() == "OF":
        used = chain(4)
        return list(toks[:used]), used
    return list(toks[:1]), 1


def _old_target_name(target: Sequence[str]) -> str:
    """``OLD`` 目标的**本体名**：序号+宿主形态取宿主名，其余取首 token（§l.5-6 修订）。

    ``['1','of','STCATEGORY','/X',…]`` → ``/X``；``['/X','of',…]`` → ``/X``；
    ``['/X']`` → ``/X``。链上的 STSECTION/CATALOGUE 等只是限定，不是本体。
    """
    if not target:
        return ""
    if len(target) >= 4 and target[1].upper() == "OF" and target[0].isdigit():
        return target[3]
    return target[0]


def _parse_block(lines: Sequence[Tuple[int, str]], macro: _Macro) -> List[Elem]:
    """把一段（一个 INPUT 段）解析成元素列表（含顶层 OLD）。"""
    stack: List[Elem] = []
    roots: List[Elem] = []
    open_old: Optional[Elem] = None

    def close_old():
        nonlocal open_old
        open_old = None

    for lineno, text in lines:
        toks = _tokenize(text)
        if not toks:
            continue
        head = toks[0].upper()

        # ---- 尾段容错块（规则 8）
        if head in ("LABEL", "HANDLE", "ENDHANDLE", "RETURN"):
            if head == "LABEL" and len(toks) > 1:
                macro.label = toks[1]
            close_old()
            stack = []
            break

        # ---- 宏级命令：不携带元素语义，直接丢弃（ONERROR/INPUT/DELETE/…）
        if head in ("ONERROR", "INPUT", "DELETE", "GOTO", "PAUSE", "MESSAGE"):
            macro.commands.append(text)
            if head == "DELETE":
                close_old()
                macro.deletes += 1
            continue

        # ---- NEW（规则 5）
        if head == "NEW":
            close_old()
            if len(toks) < 2:
                macro.warnings.append("L%d NEW 缺类型名：%r" % (lineno, text))
                continue
            t = _norm_type(toks[1])
            idx = 2
            name = ""
            if idx < len(toks):
                cand = toks[idx]
                if cand.startswith("/") or (not _KEY_RE.match(cand) and cand not in ATTRIB_KEYS):
                    name = cand
                    idx += 1
            el = Elem(t, name, lineno, "NEW", text=text)
            if stack:
                stack[-1].kids.append(el)
            else:
                roots.append(el)
            stack.append(el)
            macro.elements.append(el)
            _consume_attrs(el, toks, idx, macro, lineno)
            continue

        # ---- END（规则 5）
        if head == "END":
            close_old()
            if stack:
                stack.pop()
            else:
                macro.warnings.append("L%d 多余的 END（栈已空）" % lineno)
            continue

        # ---- OLD（规则 6/7）
        if head == "OLD":
            close_old()
            idx = 1
            t = ""
            if idx < len(toks) and _is_type_token(toks[idx]):
                t = _norm_type(toks[idx])
                idx += 1
            target, used = _split_old_target(toks[idx:])
            raw = " ".join(target)
            name = _old_target_name(target)
            el = Elem(t or "?", name, lineno, "OLD", raw, text)
            roots.append(el)
            macro.elements.append(el)
            macro.olds.append(el)
            open_old = el
            _consume_attrs(el, toks, idx + used, macro, lineno)
            continue

        # ---- 其它：属性行（挂到 open_old 或栈顶）
        target_el = open_old if open_old is not None else (stack[-1] if stack else None)
        if target_el is None:
            macro.warnings.append("L%d 游离行（无宿主元素）：%r" % (lineno, text))
            continue
        _consume_attrs(target_el, toks, 0, macro, lineno)
    return roots


def parse_macro(text: str, *, meta: Optional[Dict[str, Any]] = None) -> _Macro:
    """把宏文本解析成 :class:`_Macro`（结构 + 警告；不做"规格"级解释）。"""
    macro = _Macro()
    lines = _logical_lines(text)
    macro.lines = len(lines)
    for _lineno, st in lines:
        mo = re.match(r"^ONERROR\s+GOLABEL\s+(\S+)", st, re.IGNORECASE)
        if mo:
            macro.onerror = mo.group(1)
        mo = re.match(r"^INPUT\s+END\b(.*)$", st, re.IGNORECASE)
        if mo:
            macro.input_end_items.extend(_tokenize(mo.group(1)))

    # 切段（规则 4）：INPUT BEGIN…INPUT END/FINISH；无包裹的行按"首段/尾段"处理
    segs: List[List[Tuple[int, str]]] = []
    head: List[Tuple[int, str]] = []
    tail: List[Tuple[int, str]] = []
    cur: Optional[List[Tuple[int, str]]] = None
    for item in lines:
        up = item[1].upper()
        if up.startswith("INPUT BEGIN"):
            cur = []
            continue
        if up.startswith("INPUT END") or up.startswith("INPUT FINISH"):
            if cur is not None:
                segs.append(cur)
                cur = None
            continue
        if cur is not None:
            cur.append(item)
        elif not segs:
            head.append(item)
        else:
            tail.append(item)
    if cur is not None:
        segs.append(cur)
    allsegs = ([head] if head else []) + segs + ([tail] if tail else [])
    if not allsegs:
        allsegs = [list(lines)]
    for seg in allsegs:
        macro.segments.append(_parse_block(seg, macro))
    for seg in macro.segments:
        macro.roots.extend(seg)
    if meta is not None:
        meta["logical_lines"] = len(lines)
        meta["segments"] = len([s for s in macro.segments if s])
    return macro


# ---------------------------------------------------------------------------
# 元素索引（树 + 第二遍引用）
# ---------------------------------------------------------------------------

class _Index(object):
    """宏内索引：名字 → 元素、族 → 参数/几何、SPCOMPONENT → SPRFILE。"""

    def __init__(self, macro: _Macro):
        self.macro = macro
        self.parents: Dict[int, Optional[Elem]] = _build_parents(macro.roots)
        self.by_name: Dict[str, List[Elem]] = {}
        for el in macro.elements:
            if el.name:
                self.by_name.setdefault(el.name, []).append(el)
        self.comp_by_spr_name: Dict[str, List[Elem]] = {}
        self.comp_by_family_name: Dict[Tuple[str, str], List[Elem]] = {}
        self.comp_by_lastname: Dict[str, List[Elem]] = {}
        for el in macro.elements:
            if el.op == "NEW" and el.type == "SPCOMPONENT" and el.name:
                fam = family_of_comp(el.name)
                last = el.name.rsplit("/", 1)[-1]
                self.comp_by_family_name.setdefault((fam, last), []).append(el)
                self.comp_by_lastname.setdefault(last, []).append(el)
        self._link_refs()

    # ---- 第二遍引用
    def _link_refs(self) -> None:
        for el in self.macro.olds:
            if el.type == "SPRFILE":
                for target in self._find_by_name(el.name, ("SPRFILE",)):
                    for key in ("PSTR", "GSTR", "DTRE", "PARA"):
                        if key in el.attrs:
                            target.attrs[key] = el.attrs[key]
                    self._register_comp(target, el)
            elif el.type == "SPCOMPONENT":
                for target in self._find_by_name(el.name, ("SPCOMPONENT",)):
                    v = el.get("CATR")
                    if v:
                        target.attrs["CATR"] = v
                        self._register_comp(target, el)
                    if "LOCK" in el.attrs:
                        target.attrs["LOCK"] = el.attrs["LOCK"]
            elif el.type == "PTSSET":
                for target in self._families_of_old(el):
                    if "NARE" in el.attrs:
                        target.attrs["NARE"] = el.attrs["NARE"]
            elif el.type == "?":
                # `OLD /XI_Profile`（类型可省，规则 7）：按名字在全库查
                for target in self._find_by_name(el.name, ()):
                    for key in ("PSTR", "GSTR", "DTRE", "CATR", "NARE", "DESC", "LOCK"):
                        if key in el.attrs:
                            target.attrs[key] = el.attrs[key]
                    self._register_comp(target, el)

    def _register_comp(self, target: Elem, old: Elem) -> None:
        """把 ``OLD SPCOMPONENT`` 与它 ``CATR`` 指的 SPRFILE 关联起来。"""
        if target.type != "SPCOMPONENT":
            return
        v = target.get("CATR")
        if not v:
            return
        # 值形如 ``SPRFILE /X`` 或带父级链 ``SPRFILE /X of STCATEGORY /Y of …``（§0.4-9）：
        # 本体名 = 链头（第一个 `` of `` 之前）的最后一个 token。
        head = []
        for tok in v.split():
            if tok.upper() == "OF":
                break
            head.append(tok)
        name = normalize_name(head[-1] if head else "")
        self.comp_by_spr_name.setdefault(name, []).append(target)

    def _find_by_name(self, name: str, types: Sequence[str]) -> List[Elem]:
        if not name:
            return []
        want = set(types)
        return [e for e in self.by_name.get(name, [])
                if e.op == "NEW" and (not want or e.type in want)]

    def _families_of_old(self, el: Elem) -> List[Elem]:
        """``OLD PTSSET 1 of STCATEGORY /X`` → 族 ``/X`` 的第 1 个 PTSSET。"""
        m = _REF_RE.match("%s %s" % (el.type, el.raw_old)) if el.raw_old else None
        if not m:
            return []
        owner, idx = m.group("owner"), m.group("idx")
        out: List[Elem] = []
        for fam in self.by_name.get(owner, []):
            if fam.op != "NEW" or fam.type != "STCATEGORY":
                continue
            ts = fam.find("PTSSET")
            if idx is None:
                out.extend(ts)
            else:
                k = int(idx) - 1
                if 0 <= k < len(ts):
                    out.append(ts[k])
        return out

    # ---- 族一级信息
    def family_of(self, spr: Elem) -> Optional[Elem]:
        """SPRFILE 的族：先看树（嵌套即所有权），再看第二遍的 PSTR/GSTR/DTRE 引用。"""
        par = self.parents.get(id(spr))
        if par is not None and par.type == "STCATEGORY":
            return par
        for key in ("PSTR", "GSTR", "DTRE"):
            v = spr.get(key)
            if not v:
                continue
            m = _REF_RE.match("%s %s" % (key, v))
            if m and m.group("owner"):
                for fam in self.by_name.get(m.group("owner"), []):
                    if fam.op == "NEW" and fam.type == "STCATEGORY":
                        return fam
        return None

    def ancestor(self, el: Elem, types: Sequence[str]) -> Optional[Elem]:
        want = set(types)
        cur: Optional[Elem] = el
        for _ in range(64):
            cur = self.parents.get(id(cur)) if cur is not None else None
            if cur is None:
                return None
            if cur.type in want:
                return cur
        return None

    def catalogue_of(self, el: Elem) -> str:
        """元素所属的 CATALOGUE / SPWLD 名（顶层 OLD 段落 ⇒ ``''``）。"""
        a = self.ancestor(el, ("CATALOGUE", "SPWLD"))
        return a.name if a is not None else ""

    def dtset_params(self, fam: Elem) -> List[Dict[str, Any]]:
        """族的参数定义（按 ``NUMB`` 排序）。

        ``var_index``：``PURP=DESP`` 的 DESP 下标（取自 ``PPRO`` 的 ``ATTRIB DESP[n]``，
        取不到时退回 ``NUMB``）；``PURP=PARA`` 的参数按 NUMB 顺序与 ``SPRFILE.PARA`` 对位
        （注意：PARA 与 DESP 各有自己的 NUMB 编号空间，原件里两组都从 1 开始）。
        """
        out: List[Dict[str, Any]] = []
        for ds in fam.find("DTSET"):
            for data in ds.find("DATA"):
                numb = _num(_unparen(data.get("NUMB")))
                ppro = data.get("PPRO")
                purpos = (data.get("PURP") or "").strip().upper()
                desp_index = 0
                if purpos == "DESP":
                    mo = re.search(r"DESP\s*\[\s*(\d+)\s*\]", ppro or "")
                    desp_index = int(mo.group(1)) if mo else (int(numb) if numb else 0)
                out.append({
                    "numb": int(numb) if numb is not None else 0,
                    "dkey": data.get("DKEY"),
                    "dtit": _unquote(data.get("DTIT")).strip(),
                    "purpos": purpos,
                    "desp_index": desp_index,
                    "dpro": _unparen(data.get("DPRO")),
                    "ppro": ppro,
                    "ptyp": data.get("PTYP"),
                    "line": data.line,
                    "elem": data,
                })
        out.sort(key=lambda d: (d["purpos"] != "PARA", d["numb"]))
        return out

    def sprfiles_of(self, fam: Elem) -> List[Elem]:
        return list(fam.find("SPRFILE"))


# ---------------------------------------------------------------------------
# PARA 逐项消化（规则 12）
# ---------------------------------------------------------------------------

def split_para(tokens: Sequence[str], n_params: int) -> Tuple[List[str], List[str]]:
    """按"参数个数"消化 ``PARA`` 的 token（word 型参数吃 2 个 token）。

    返回 ``(values, notes)``；``values`` 长度恒为 ``n_params``（不足补 ``''``）。
    """
    notes: List[str] = []
    toks = [t for t in tokens if t != ""]
    if n_params <= 0:
        # 纯参数化族（无 PURP=PARA 参数）的 `PARA 0` 是占位，原件即如此（/USER_RECT L2990）
        if toks in ([], ["0"]):
            return [], []
        return [], ["PARA 有 %d 个值但该族没有 PURP=PARA 的 DTSET 参数" % len(toks)]
    out: List[str] = []
    i = 0
    while i < len(toks):
        remaining = len(toks) - i
        slots = n_params - len(out)
        if slots <= 0:
            notes.append("PARA 值多于参数，多余的被丢弃：%s" % (" ".join(toks[i:i + 4]),))
            break
        if remaining == slots:
            out.append(toks[i])
            i += 1
        elif remaining > slots and i + 1 < len(toks) \
                and _num(toks[i]) is None and _num(toks[i + 1]) is None:
            out.append(toks[i] + " " + toks[i + 1])      # word 型参数（原件 `S RSA`）
            notes.append("第 %d 个参数按 word 型吃了 2 个 token：%r" % (len(out), out[-1]))
            i += 2
        else:
            out.append(toks[i])
            i += 1
    while len(out) < n_params:
        out.append("")
    return out, notes


# ---------------------------------------------------------------------------
# sectionlib 适配（构造 SectionRec/SectionTable/ParamDef）
# ---------------------------------------------------------------------------

def _import_sectionlib() -> Any:
    try:
        import sectionlib                                       # noqa: F401
        return sectionlib
    except ImportError as exc:                                  # pragma: no cover
        raise DbParseError(
            "解析需要 engine/sectionlib.py（契约 §k.1 的 SectionTable/SectionRec），"
            "但它不存在或不可导入：%s" % exc)


def _make_rec(lib: Any, **kw: Any) -> Any:
    cls = getattr(lib, "SectionRec")
    try:
        return cls(**kw)
    except TypeError:                                          # 字段名漂移时的退化路径
        rec = cls()
        for k, v in kw.items():
            try:
                setattr(rec, k, v)
            except Exception:                                  # pragma: no cover
                pass
        return rec


def _make_table(lib: Any, recs: List[Any]) -> Any:
    cls = getattr(lib, "SectionTable")
    try:
        return cls(recs=recs)
    except TypeError:
        tbl = cls()
        try:
            tbl.recs = recs
        except Exception:                                      # pragma: no cover
            pass
        return tbl


def _make_params(lib: Any, shape: List[Dict[str, Any]]) -> List[Any]:
    cls = getattr(lib, "ParamDef", None)
    out: List[Any] = []
    for d in shape:
        if cls is None:
            out.append(dict(d))
            continue
        try:
            out.append(cls(name=d["name"], desp_index=d["desp_index"], default=d["default"]))
        except TypeError:                                      # pragma: no cover
            out.append(dict(d))
    return out


def _builtin_index(builtin: Any) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """``(spec_path → rec, pdms_stcategory → family_code)``。"""
    by_path: Dict[str, Any] = {}
    fam: Dict[str, int] = {}
    for rec in getattr(builtin, "recs", []) or []:
        path = normalize_name(str(getattr(rec, "pdms_spec_path", "") or ""))
        if path:
            by_path.setdefault(path, rec)
        extra = getattr(rec, "extra", None)
        if isinstance(extra, dict):
            stcat = normalize_name(str(extra.get("pdms_stcategory", "") or ""))
            fc = int(getattr(rec, "family_code", 0) or 0)
            if stcat and fc:
                fam.setdefault(stcat, fc)
    return by_path, fam


def family_of_comp(path: str) -> str:
    """``/USER_RECT-SPEC/Rectangle_Profile`` → ``/USER_RECT``（§l.3.4-1 的不变量）。"""
    p = normalize_name(path)
    parts = p.split("/")
    owner = parts[1] if len(parts) > 1 else ""
    if owner.endswith("-SPEC"):
        owner = owner[:-len("-SPEC")]
    return "/" + owner if owner else "/"


def _norm_param_key(name: str) -> str:
    return re.sub(r"\(.*?\)", "", (name or "")).replace(" ", "").strip().lower()


# ---------------------------------------------------------------------------
# 对外：宏 → SectionTable（契约 §l.5）
# ---------------------------------------------------------------------------

def parse_db_macro(text: str, *, secmap: Any = None, builtin: Any = None,
                   sectionlib: Any = None, encoding: str = "") -> Any:
    """宏文本 → :class:`sectionlib.SectionTable`（契约 §l.5）。

    * ``secmap``：可选 :class:`secmap.SectionMap`，给了才做 ``pkpm_name`` 逆查（§l.5）；
    * ``builtin``：可选内置转化表（``sectionlib.load_builtin_table()``），用于反查
      ``family_code``（§l.5）与 ``kind``/``mat``（只有表里有这两项）；
    * ``sectionlib``：注入用（自检）；缺省 ``import sectionlib``。
    """
    lib = sectionlib or _import_sectionlib()
    macro = parse_macro(text)
    index = _Index(macro)
    warnings: List[str] = list(macro.warnings)
    if encoding:
        warnings.append("宏编码判定为 %s（契约 §l.5-1）" % encoding)
    by_path, fam_map = _builtin_index(builtin)

    recs: List[Any] = []
    seen: Dict[str, int] = {}
    n_para_warned: Dict[str, bool] = {}
    shapeval_fail: Dict[str, int] = {}
    for fam in [e for e in macro.elements if e.op == "NEW" and e.type == "STCATEGORY"]:
        params = index.dtset_params(fam)
        para_params = [p for p in params if p["purpos"] == "PARA"]
        desp_params = [p for p in params if p["purpos"] == "DESP"]
        parametric = bool(desp_params)
        for spr in index.sprfiles_of(fam):
            if not spr.name:
                continue
            toks = (spr.get("PARA") or "").split()
            values, notes = split_para(toks, len(para_params))
            for nt in notes:
                warnings.append("族 %s 的 SPRFILE %s：%s" % (fam.name, spr.name, nt))
            if para_params and len(toks) != len(para_params) and not n_para_warned.get(fam.name):
                if not (parametric and len(toks) == 1 and _num(toks[0]) == 0):
                    warnings.append(
                        "族 %s：SPRFILE.PARA 个数 %d ≠ PURP=PARA 的 DATA 条数 %d"
                        "（§l.3.4-5；原件 /H_AMERICA、/H_EUROPE 的 25/26 即此类）"
                        % (fam.name, len(toks), len(para_params)))
                    n_para_warned[fam.name] = True
            spr_name = normalize_name(spr.name)
            fam_key = normalize_name(fam.name)
            # 名字→规格：同一 SPRFILE 名可能被多个族复用（如 /DLE100x10 同属
            # /DOUBLE_L_EQUAL 与 /DOUBLE_L_EQUAL_CROSS），原件里还有属主名写错的
            # SPCOMPONENT（如 /STSS_DOUBLE_THIN_L-SPEC/… 实际属于 /DOUBLE_THIN_L_COIL_EQUAL）
            # ⇒ 四级关联，逐级放宽并记账：
            cands = index.comp_by_spr_name.get(spr_name, [])
            comps = [c for c in cands if family_of_comp(c.name) == fam_key]
            if not comps and cands:
                comps = list(cands)
                warnings.append("SPRFILE %s（族 %s）：SPCOMPONENT 属主与 CATR 的族不一致 ⇒ "
                                "按 CATR 关联：%s"
                                % (spr_name, fam_key,
                                   ", ".join(sorted({family_of_comp(c.name) for c in cands}))))
            if not comps:
                comps = list(index.comp_by_family_name.get(
                    (fam_key, spr_name.lstrip("/")), []))
            if not comps:
                comps = [c for c in index.comp_by_lastname.get(spr_name.lstrip("/"), [])
                         if family_of_comp(c.name) == fam_key]
            if not comps:
                warnings.append("SPRFILE %s（族 %s）没有对应 SPCOMPONENT ⇒ 该规格不可选"
                                % (spr_name, fam.name))
                continue
            for comp in comps:
                path = normalize_name(comp.name)
                if path in seen:
                    warnings.append("SPCOMPONENT %s 重复（L%d 与 L%d）⇒ 保留第一条"
                                    % (path, seen[path], comp.line))
                    continue
                seen[path] = comp.line
                recs.append(_build_rec(lib, index, fam, spr, comp, params, para_params,
                                       values, notes, parametric, path, by_path, fam_map,
                                       secmap, warnings, shapeval_fail))

    if shapeval_fail:
        top = sorted(shapeval_fail.items(), key=lambda kv: -kv[1])[:5]
        warnings.append("shapeval 回算不可用 %d 条（逐条见 rec.extra['shapeval_error']）：%s"
                        % (sum(shapeval_fail.values()),
                           "；".join("%d×%s" % (v, k) for k, v in top)))

    n_comps = len({normalize_name(e.name) for e in macro.elements
                   if e.op == "NEW" and e.type == "SPCOMPONENT" and e.name})
    if n_comps != len(recs):
        warnings.append("SPCOMPONENT %d 条、可落规格 %d 条（差额=无 SPRFILE/重复/无名）"
                        % (n_comps, len(recs)))
    table = _make_table(lib, recs)
    try:
        setattr(table, "parse_warnings", warnings)
    except Exception:                                          # pragma: no cover
        pass
    return table


def _build_rec(lib: Any, index: _Index, fam: Elem, spr: Elem, comp: Elem,
               params: List[Dict[str, Any]], para_params: List[Dict[str, Any]],
               values: List[str], notes: List[str],
               parametric: bool, path: str, by_path: Dict[str, Any],
               fam_map: Dict[str, int], secmap: Any, warnings: List[str],
               shapeval_fail: Dict[str, int]) -> Any:
    """一个 ``SPCOMPONENT`` → 一个 ``SectionRec``。"""
    family = normalize_name(fam.name)
    base = by_path.get(path)
    family_code = fam_map.get(family, 0) or int(getattr(base, "family_code", 0) or 0)
    kind = int(getattr(base, "kind", 0) or 0) if base is not None else 0
    mat = int(getattr(base, "mat", 0) or 0) if base is not None else 0
    if not mat:
        mat = 5

    dims: Dict[str, Any] = {}
    named: Dict[str, str] = {}
    desp_view: List[Dict[str, Any]] = []
    para_view: List[Dict[str, Any]] = []
    for i, p in enumerate(params):
        if p in para_params:                       # PURP=PARA：值来自 SPRFILE.PARA（按 NUMB 对位）
            k = para_params.index(p)
            v = values[k] if k < len(values) else ""
            if v == "":
                v = p["dpro"]
            desp = 0
        else:                                      # PURP=DESP：值来自 DPRO（建模时输入）
            v = p["dpro"]
            desp = p["desp_index"] or p["numb"]
        label = p["dtit"] or p["dkey"] or ("P%d" % (i + 1))
        named[label] = v
        if desp == 0:
            para_view.append({"name": label, "default": v, "desp_index": 0, "dkey": p["dkey"],
                              "numb": p["numb"], "ppro": p["ppro"]})
        else:
            desp_view.append({"name": p["dtit"] or label, "desp_index": desp,
                              "default": v})
        key = SIZE_KEYS.get(_norm_param_key(p["dtit"]))
        if key:
            num = _num(v)
            dims[key] = num if num is not None else v
    # `rec.params` 的装法（§k.1 的 ParamDef：`is_parametric=True ⇒ desp_index 1..N`，
    # 否则 0 —— 两者互斥，sectionlib 的 validate() 把这条写成当且仅当）：
    #   * 族有 DESP 参数 ⇒ 只放 DESP 参数（PARA 参数无损留在 extra['para_params']）；
    #   * 纯 PARA 族     ⇒ 全部参数（desp_index=0）。
    shape = desp_view if desp_view else para_view
    if family_code in PARAM_FAMILY_CODES:
        dims.setdefault("family", family_code)
    spr_base = spr.name.lstrip("/")
    m = re.match(r"^(\d+)-(.*)$", spr_base)
    if family_code == 77:
        dims.setdefault("family", 77)
        if m:
            dims.setdefault("lib_family", int(m.group(1)))
            dims.setdefault("spec_str", m.group(2))
        else:
            dims.setdefault("spec_str", spr_base)
    elif family_code == 26 and family == "/H_INTERNATIONAL":
        dims.setdefault("subtype", 1)          # §l.6：族码 39 的 subtype=1

    spec_el = index.ancestor(comp, ("SPECIFICATION",))
    extra: Dict[str, Any] = {
        "sprfile": normalize_name(spr.name),
        "stcategory": family,
        "specification": spec_el.name if spec_el is not None else "",
        "catalogue": index.catalogue_of(spr),
        "para_raw": list(values),
        "params_named": named,
        "para_params": para_view,
        "para_tokens": len((spr.get("PARA") or "").split()),
        "params_notes": list(notes),
        "source_lines": {"family": fam.line, "sprfile": spr.line, "component": comp.line},
        "parametric": parametric,
        "family_has_desp": parametric,
        "n_para_params": len(para_params),
        "n_desp_params": len(params) - len(para_params),
        "pline": sum(1 for _k in fam.find("PTSSET") for _p in _k.find("PLINE")),
        "gmsset": len(fam.find("GMSSET")),
        "nare": (fam.find("PTSSET")[0].get("NARE") if fam.find("PTSSET") else ""),
        "lock": ("LOCK" in comp.attrs),
    }
    if not extra["catalogue"]:
        warnings.append("SPCOMPONENT %s 的 SPRFILE %s 不在任何 CATALOGUE/SPWLD 内"
                        % (path, spr.name))

    pkpm_name = ""
    if secmap is not None:
        try:
            # 注意：PKPM 名**不是** PDMS 路径，不能补前导 '/'（§k.1/§k.2：两者的取值域不相交）
            pkpm_name = " ".join((secmap.reverse(path) or "").split())
        except Exception:                                      # pragma: no cover
            pkpm_name = ""
    if not pkpm_name and base is not None:
        pkpm_name = " ".join(str(getattr(base, "pkpm_name", "") or "").split())
    key = pkpm_name or path

    rec = _make_rec(
        lib,
        key=key,
        pkpm_name=pkpm_name,
        family_code=family_code,
        family_name_cn=(str(getattr(base, "family_name_cn", "") or "")
                        if base is not None else ""),
        kind=kind,
        shapeval="",
        dims=dims,
        mat=mat,
        pdms_spec_path=path,
        pdms_catalogue=extra["catalogue"],
        is_parametric=parametric,
        params=_make_params(lib, shape),
        confidence=("medium" if (family_code and params and not notes)
                    else ("low" if params else "unknown")),
        source="dbmacro" + ("+builtin" if base is not None else ""),
        extra=extra,
    )
    if rec.confidence == "unknown":
        extra.setdefault("reason", "族 %s 没有 DTSET 参数定义（无法按 PARA 对位）" % family)
    enc = getattr(lib, "encode_shapeval", None)
    if callable(enc):
        try:
            rec.shapeval = enc(rec, 0, mat)
        except Exception as exc:
            rec.shapeval = ""
            why = (str(exc) or exc.__class__.__name__).strip()
            extra["shapeval_error"] = why
            shapeval_fail[why[:80]] = shapeval_fail.get(why[:80], 0) + 1
    return rec


def parse_db_macro_file(path: str, **kw: Any) -> Any:
    """按契约读文件（自动判编码）再 :func:`parse_db_macro`。"""
    text, enc = read_macro_text(path)
    kw.setdefault("encoding", enc)
    return parse_db_macro(text, **kw)


# ---------------------------------------------------------------------------
# 统计（报告用）
# ---------------------------------------------------------------------------

def macro_stats(text: str) -> Dict[str, Any]:
    """元素计数（与契约 §m.3 的 ``report.db.generated`` 同构）。"""
    macro = parse_macro(text)
    cnt: Dict[str, int] = {}
    for el in macro.elements:
        if el.op == "NEW":
            cnt[el.type] = cnt.get(el.type, 0) + 1
    pass2: Dict[str, int] = {}
    for el in macro.olds:
        pass2[el.type] = pass2.get(el.type, 0) + 1
        for k in ("PSTR", "GSTR", "DTRE", "CATR", "NARE"):
            if k in el.attrs:
                pass2[k] = pass2.get(k, 0) + 1
    return {
        "catalogue": cnt.get("CATALOGUE", 0), "stsection": cnt.get("STSECTION", 0),
        "stcategory": cnt.get("STCATEGORY", 0), "text": cnt.get("TEXT", 0),
        "dtset": cnt.get("DTSET", 0), "data": cnt.get("DATA", 0),
        "ptsset": cnt.get("PTSSET", 0), "pline": cnt.get("PLINE", 0),
        "gmsset": cnt.get("GMSSET", 0), "profile": cnt.get("SPROFILE", 0),
        "sprfile": cnt.get("SPRFILE", 0), "spwld": cnt.get("SPWLD", 0),
        "specification": cnt.get("SPECIFICATION", 0), "selec": cnt.get("SELEC", 0),
        "spcomponent": cnt.get("SPCOMPONENT", 0),
        "pass2": pass2, "logical_lines": macro.lines,
        "elements": sum(1 for e in macro.elements if e.op == "NEW"),
        "olds": len(macro.olds),
        "warnings": list(macro.warnings),
    }


def parse_stats(table: Any) -> Dict[str, Any]:
    """解析结果的规模统计（契约 §m.3 的 ``report.db.parsed`` 同义）。"""
    recs = list(getattr(table, "recs", []) or [])

    def ex(r: Any, k: str) -> str:
        e = getattr(r, "extra", None)
        return str(e.get(k, "")) if isinstance(e, dict) else ""

    paths = [normalize_name(str(getattr(r, "pdms_spec_path", "") or "")) for r in recs]
    return {
        "specs": len(recs),
        "sprfile": len({ex(r, "sprfile") for r in recs if ex(r, "sprfile")}),
        "spcomponent": len(recs),
        "families": len({ex(r, "stcategory") for r in recs if ex(r, "stcategory")}),
        "parametric": sum(1 for r in recs if getattr(r, "is_parametric", False)),
        "family_code_known": sum(1 for r in recs if int(getattr(r, "family_code", 0) or 0)),
        "pkpm_name_known": sum(1 for r in recs if str(getattr(r, "pkpm_name", "") or "")),
        "shapeval_known": sum(1 for r in recs if str(getattr(r, "shapeval", "") or "")),
        "unique_paths": len(set(paths)),
        "warnings": list(getattr(table, "parse_warnings", []) or []),
    }


# ---------------------------------------------------------------------------
# 与匹配文件的交叉核对（契约 §l.5 的验收阈值表）
# ---------------------------------------------------------------------------

def _variant_index(builtin: Any,
                   variant_names: Optional[Sequence[str]] = None) -> Dict[str, List[str]]:
    """变体索引：归一化键 → 该截面的"另一种拼写"（DLL 侧优先，其次内置表 extra）。"""
    idx: Dict[str, List[str]] = {}

    def add(name: str) -> None:
        n = (name or "").strip()
        if not n:
            return
        for key in (norm_pkpm(n), norm_pkpm2(n)):
            if n not in idx.setdefault(key, []):
                idx[key].append(n)

    if variant_names:
        for n in variant_names:
            add(n)
        return idx
    # 缺省只用**DLL 侧拼写**（内置转化表 extra 的 dll_table_entry/name_variants 与派生列
    # dll_siblings；recon conflicts §2.6 的 759 就是这个口径），不与内置表自己的 pkpm_name
    # 混（那会把口径放大）。dll_siblings 由 test/build_section_table.py 从 recon 的 DLL 名集
    # 派生（§k.2）：源表把"冷弯/热轧同名异族"两行标成同一个 DLL 拼写，包内表因此丢 8 个键的
    # 另一种拼写 —— 不补齐则 §l.5 的 759 对只归得出 751 对。
    for rec in getattr(builtin, "recs", []) or []:
        extra = getattr(rec, "extra", None)
        if not isinstance(extra, dict):
            continue
        add(str(extra.get("dll_table_entry", "") or ""))
        for m in re.finditer(r"dll=([^;]+)", str(extra.get("name_variants", "") or "")):
            add(m.group(1))
        for n in str(extra.get("dll_siblings", "") or "").split(";"):
            add(n)
    return idx


def _raw_match_rows(match_path: str) -> Dict[int, bool]:
    """``{行号: 右值是否缺前导 /}``（只服务 §l.5"右值原本缺前导 / 4"的归类）。"""
    raw = open(match_path, "rb").read()
    try:
        text = raw.decode("gbk")
    except UnicodeDecodeError:
        text = raw.decode("utf-8-sig")
    out: Dict[int, bool] = {}
    for lineno, line in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
        s = line.strip()
        if not s or s.startswith("//") or set(s) == {"/"} or "," not in line:
            continue
        rhs = " ".join(line.split(",", 1)[1].split())
        out[lineno] = bool(rhs) and not rhs.startswith("/")
    return out


def cross_check(table: Any, secmap: Any = None, *, match_path: str = "",
                builtin: Any = None, variant_names: Optional[Sequence[str]] = None
                ) -> Dict[str, Any]:
    """解析结果 × 匹配文件的归类报告（契约 §l.5 的验收阈值表）。

    ``secmap`` 给了就用它的 ``entries``（``(行号, 左值, 右值)``，右值已按 §e.2 归一化）；
    ``match_path`` 另给时读原文，用于判"右值原本缺前导 ``/``"的那 4 行。
    ``variant_names`` 给了就用它当"另一种拼写"的来源（如 DLL 的 2,326 个名），
    否则用内置转化表 ``extra`` 里的 ``dll_table_entry``/``name_variants``。
    """
    recs = list(getattr(table, "recs", []) or [])
    comps = {normalize_name(str(getattr(r, "pdms_spec_path", "")))
             for r in recs if str(getattr(r, "pdms_spec_path", ""))}
    sprfiles = set()
    for r in recs:
        e = getattr(r, "extra", None)
        s = normalize_name(str(e.get("sprfile", ""))) if isinstance(e, dict) else ""
        if s:
            sprfiles.add(s)
    rows: List[Tuple[int, str, str]] = list(getattr(secmap, "entries", []) or []) \
        if secmap is not None else []
    raw_slash = _raw_match_rows(match_path) if match_path else {}
    variant = _variant_index(builtin, variant_names)

    matched = 0
    broken: List[Tuple[int, str, str]] = []
    case_variants: List[Tuple[int, str, str]] = []
    missing_slash: List[int] = []
    repaired_hit = 0
    referenced_spr: set = set()
    referenced_spr_raw: set = set()
    recs_by_path = {}
    for r in recs:
        p = normalize_name(str(getattr(r, "pdms_spec_path", "")))
        if p:
            recs_by_path[p] = r
    for lineno, left, right in rows:
        rhs = normalize_name(right)
        hit = rhs in comps
        if hit:
            matched += 1
            if raw_slash.get(lineno):
                repaired_hit += 1
        else:
            broken.append((lineno, left, rhs))
        if raw_slash.get(lineno):
            missing_slash.append(lineno)
        r0 = recs_by_path.get(rhs) if hit else None
        if r0 is not None:
            e0 = getattr(r0, "extra", None)
            if isinstance(e0, dict) and e0.get("sprfile"):
                spr0 = normalize_name(str(e0["sprfile"]))
                referenced_spr.add(spr0)
                if not raw_slash.get(lineno):
                    # 侦察报告的单据是"右值原文"口径（缺前导 / 的 4 行不算命中）
                    referenced_spr_raw.add(spr0)
        for cand in variant.get(norm_pkpm2(left), []):
            if cand != left:
                case_variants.append((lineno, left, cand))
                break
    macro_only = sorted(s for s in sprfiles if s.lstrip("/")
                        and s not in (referenced_spr_raw if match_path
                                      else referenced_spr))
    macro_only_norm = sorted(s for s in sprfiles if s.lstrip("/")
                             and s not in referenced_spr)
    by_owner: Dict[str, int] = {}
    for _ln, _left, rhs in broken:
        owner = (rhs.rsplit("/", 1)[0] + "/") if rhs.count("/") >= 1 else rhs
        by_owner[owner] = by_owner.get(owner, 0) + 1
    broken_256 = sum(v for k, v in by_owner.items() if k.startswith("/DOUBLE_L_"))
    broken_other = len(broken) - broken_256
    # 口径（与侦察报告 conflicts §2.1/§2.3 的"失效 260 条"一致）：
    #   原文直接比对不命中的行 = （带斜杠但不命中的） + （缺斜杠的 4 行）
    broken_raw = len(broken) - (len(missing_slash) - repaired_hit) + len(missing_slash)
    return {
        "matching_file_rows": len(rows),
        "matched": matched,
        "broken_rhs": broken_256,
        "broken_rhs_other": broken_other,
        "missing_leading_slash": len(missing_slash),
        "missing_leading_slash_lines": missing_slash,
        "missing_leading_slash_but_found": repaired_hit,
        "broken_total": broken_raw,
        "broken_total_normalized": len(broken) + len(missing_slash) - repaired_hit,
        "broken_detail": [{"owner": k, "n": v} for k, v in
                          sorted(by_owner.items(), key=lambda kv: -kv[1])],
        "broken_samples": [{"line": ln, "pkpm_name": l, "rhs": r} for ln, l, r in broken[:10]],
        "case_variants": len(case_variants),
        "case_variant_samples": [{"line": ln, "pkpm_name": l, "variant": v}
                                 for ln, l, v in case_variants[:10]],
        "case_variants_source": ("variant_names（调用方给的 DLL 名表）" if variant_names
                                 else "内置转化表 extra[dll_table_entry|name_variants|dll_siblings]"),
        "macro_only": len(macro_only),
        "macro_only_normalized": len(macro_only_norm),
        "macro_only_samples": macro_only[:10],
        "specs_in_table": len(comps),
        "sprfiles_in_table": len(sprfiles),
    }


# ---------------------------------------------------------------------------
# 闭环判据（契约 §l.6）
# ---------------------------------------------------------------------------

def closure_report(src: Any, via: Any, direction: str = "gen") -> Dict[str, Any]:
    """``db2jwd``/``db2pdt`` 反算结果再喂回生成器后的**规格集合闭环**（契约 §l.6）。

    * ``covered``：两边 ``pdms_spec_path`` 集合的交集大小；
    * ``not_closable``：``src`` 有、``via`` 没有的（逐条含族与理由）；
    * ``differences``：同一规格在两边**参数/取值/属性**上的差异（逐条含 why）。
    """
    def idx(t: Any) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for r in getattr(t, "recs", []) or []:
            p = normalize_name(str(getattr(r, "pdms_spec_path", "") or ""))
            if p:
                out.setdefault(p, r)
        return out

    a, b = idx(src), idx(via)
    covered = sorted(set(a) & set(b))
    not_closable = []
    for p in sorted(set(a) - set(b)):
        r = a[p]
        e = getattr(r, "extra", None)
        fam = (e.get("stcategory", "") if isinstance(e, dict) else "")
        not_closable.append({
            "key": str(getattr(r, "key", "") or p), "spec_path": p,
            "family": fam or family_of_comp(p),
            "why": "反算侧没有同名规格（族不可反算/未覆盖，契约 §l.6 的覆盖范围表）",
        })
    differences = []
    classes: Dict[str, int] = {}

    def add_diff(key: str, spec: str, why: str, cls: str) -> None:
        differences.append({"key": key, "spec_path": spec, "why": why, "class": cls})
        classes[cls] = classes.get(cls, 0) + 1

    def para_view(rec: Any) -> Dict[str, str]:
        """该记录的 ``PURP=PARA`` 参数视图：``{名: 默认值}``。

        解析侧把 PARA 参数放在 ``extra['para_params']`` 里（§k.1 的 ParamDef 只装 DESP 参数），
        输入表（内置转化表）则把 PARA 参数直接放在 ``rec.params`` 里（desp_index=0）。
        """
        e = getattr(rec, "extra", None)
        if isinstance(e, dict) and e.get("para_params"):
            return {str(x.get("name", "")): str(x.get("default", ""))
                    for x in e["para_params"]}
        return {str(getattr(q, "name", "") or ""): str(getattr(q, "default", "") or "")
                for q in (getattr(rec, "params", []) or [])
                if not isinstance(q, dict) and int(getattr(q, "desp_index", 0) or 0) == 0}

    def desp_view(rec: Any) -> Dict[str, str]:
        return {str(getattr(q, "name", "") or ""): str(getattr(q, "default", "") or "")
                for q in (getattr(rec, "params", []) or [])
                if not isinstance(q, dict) and int(getattr(q, "desp_index", 0) or 0) > 0}

    for p in covered:
        ra, rb = a[p], b[p]
        ea = getattr(ra, "extra", None) or {}
        eb = getattr(rb, "extra", None) or {}
        pa, pb = para_view(ra), para_view(rb)
        key = str(getattr(ra, "key", "") or p)
        if pa != pb:
            if not pa and pb:
                add_diff(key, p, "输入表该行没有参数定义（只出现在匹配文件的那批），"
                                 "生成侧按同族参数补齐：%s" % sorted(pb.items())[:4],
                         "src-no-params")
            elif pa and not pb:
                add_diff(key, p, "反算侧没有参数定义（族无 DTSET）", "via-no-params")
            else:
                add_diff(key, p, "参数名/默认值不同：%s vs %s"
                         % (sorted(pa.items())[:4], sorted(pb.items())[:4]), "params-differ")
        da, db = desp_view(ra), desp_view(rb)
        if pa != pb:
            pass                                   # 已在上面记过（每规格至多一条"参数形状"差异）
        elif set(db) - set(da):
            extra_desp = sorted(set(db) - set(da))
            flip = bool(getattr(ra, "is_parametric", False)) != \
                bool(getattr(rb, "is_parametric", False))
            add_diff(key, p, "生成侧补出了输入表没有的 DESP 参数 %s（表只留了 PURP=PARA 的参数名"
                             "%s）" % (extra_desp[:4],
                                    "；并因此 is_parametric 由 %s 变 %s"
                                    % (getattr(ra, "is_parametric", False),
                                       getattr(rb, "is_parametric", False)) if flip else ""),
                     "desp-param-added")
        elif bool(getattr(ra, "is_parametric", False)) != \
                bool(getattr(rb, "is_parametric", False)):
            add_diff(key, p, "parametric 标记不同：%s vs %s"
                     % (getattr(ra, "is_parametric", False),
                        getattr(rb, "is_parametric", False)), "parametric-flag")
        va = [str(x) for x in (ea.get("para_raw") or [])]
        vb = [str(x) for x in (eb.get("para_raw") or [])]
        if va and vb and va != vb:
            add_diff(key, p, "PARA 向量不同：%s vs %s" % (va[:4], vb[:4]), "para-differ")
    return {
        "direction": direction,
        "covered": len(covered),
        "src_specs": len(a),
        "via_specs": len(b),
        "not_closable": not_closable,
        "differences": differences,
        "differences_by_class": classes,
        "extra_specs": sorted(set(b) - set(a)),
    }
