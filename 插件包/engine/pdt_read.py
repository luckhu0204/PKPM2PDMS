# -*- coding: utf-8 -*-
"""PKPM-JWD导入导出 —— ``.pdt`` 读取器（契约 §b.4；格式规范 ``_recon/pdt_format.md``）。

``.pdt`` 是 PKPM 的**文本中间模型**（PKPM 插件 CA→PDMS 方向读的就是它，
见 ``pdms_target.md`` §3.2 的格式串直证）。本模块把它读成与 ``.jwd`` 完全相同的
:class:`canonical.Model`（契约 §a.2），单位 mm。

词法（pdt_format.md §1，全部为实测事实）::

    * GBK、CRLF；``;`` 开头 = 注释；``$`` 开头 = 节头；空白行忽略
    * **缩进即语法**：缩进 ≤4 空格 = 新记录；>4 = 上一条记录的续行
      （实测全文只有 3/4/7/8/11 五种缩进：4 = 记录行、7/8/11 = 续行）
    * 续行以 ``KEY=`` 开头 ⇒ 开始新字段；以**裸值**开头 ⇒ 追加到上一条物理行的
      最后一个字段（跨行记忆 ``last_key``）。实测发生折行的字段只有 ``EXR``
      （``$SETELEMENT`` 1046 条 + ``$SETWALL`` 4 条，缩进 8）与 ``$RIGID`` 的
      ``SLABID``（缩进 11）——契约 §b.4 点名的这一坑本模块按上述规则统一处理

装配规则（契约 §b.4 + §a.3 的**平面型 Level**）::

    * Level  —— 按**节点 Z** 分组建平面型 Level（``z_bot == z_top == z``、``height=0``、
      ``stdflr_id`` 按 z 升序 1..n）。**禁止**用 ``FLOORID``（pdt_format.md §8.3：
      38 个节点的 FLOORID 与几何不符）或只用 ``$STORY``（11 个标高里只有 5 个是层顶）
    * Joint  —— 全部 ``$NODECOOR`` 节点（样本 617 个）；``hdiff=0``、``z = level.z_top``
    * Member —— ``$SETELEMENT`` 的 ``TYPE=1``→``column``（**start 在下端**）、
      ``TYPE=2``→``beam``（start = ``$NET.NODES``）、``TYPE=3``→``brace``
      〔§0.4-5/§j.4.5/§12#15 冻结〕；其余 TYPE 不进 ``members``（记 ``notes``）
    * Slab   —— ``$SETSLAB``，``polygon`` 由 ``NETID`` 有序闭合环拼出（不闭合、不重复首点）
    * Wall   —— ``$SETWALL``，``loop`` 为环的 3D 顶点，``z_bot/z_top`` 取环上 U 的极值
    * Section—— ``$DEFFRAMESECTION`` → ``Section(table='pdt')``；
      ``$DEFWASLABSECTION`` **不建 Section**（契约 §b.4），厚度直接落到
      ``Slab.thickness``/``Wall.thickness``
    * Load   —— 荷载节可选解析（契约 §b.4）。本模块搬运 ``$SETNODELOAD``（→``joint-point``）
      与 ``$SETLINELOAD``（→``beam-line``）的力/弯矩分量，并把 ``$SETSLABLOAD`` 的
      恒/活载面荷载（kN/m²）落到 ``Slab.dead/Slab.live``；塞不进 Model 的语义（墙的
      均布线荷载、``DS/S`` 以 m 计的位置信息、``KIND/TYPE/UCS`` 含义未证实）一律进 ``notes``

只读：本模块不写任何文件；编码失败按契约 §g.1 抛 ``ValueError``（CLI 映射为退出码 2）。
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

try:                                     # 直接运行 / 测试把 engine/ 加入 sys.path
    from canonical import (Joint, Level, Load, Member, Model,
                           PANE_ORI, PANE_SJUS, Section, Slab, TOL,
                           WALL_DEFAULT_SJUS, Wall)
except ImportError:                      # pragma: no cover - 作为包导入
    from .canonical import (Joint, Level, Load, Member, Model,
                            PANE_ORI, PANE_SJUS, Section, Slab, TOL,
                            WALL_DEFAULT_SJUS, Wall)

#: 工况分组头（pdt_format.md §2.12：它们自身 0 条记录，只给后续子节分组）
LOAD_GROUPS = ("$DEADLOAD", "$LIVELOAD")
#: 荷载子节（同一节名会在两个工况里各出现一次 ⇒ 必须按 (节名, 工况) 二元组索引）
LOAD_SUBSECTIONS = ("$DEFNODELOAD", "$SETNODELOAD", "$DEFLINELOAD", "$SETLINELOAD",
                    "$DEFSLABLOAD", "$SETSLABLOAD")

#: ``$SETELEMENT.TYPE``（pdt_format.md §5.1）：1=柱（两端 X/Y 相同）、2=梁（两端 Z 相同）。
#: **3=支撑**〔R2 契约变更 §0.4-5 / §j.4.5 / §12#15 冻结〕：样本无支撑（§5.1【事实】）⇒ 无直证，
#: 但写 1/2 会静默改类型、写未映射值会丢构件 ⇒ 写出端（``pdt_write``）与读入端必须同码。
#: 水平/竖向支撑由几何（``|ΔZ| ≤ 1e-6``）在 PDMS 侧判 HBRACE/VBRACE（§d.4-2），
#: 本模块两者都映射成 ``Member.type='brace'``。
TYPE_COLUMN = "1"
TYPE_BEAM = "2"
TYPE_BRACE = "3"

#: ``$SETSLAB`` / ``$SETWALL`` 的 TYPE（pdt_format.md §5.2）
TYPE_WALL = "5"
TYPE_SLAB = "6"

#: ID 规范（pdt_format.md §3.2【事实】）：``ID = 全局序号 N × 100 + 两位对象类别码 CC``。
#: 本模块**不解码** ID（Model 只用它做键），但用它做自校验：类码不符即记 notes。
ID_CLASS = {
    "$DEFMATERIAL": 10,
    "$DEFFRAMESECTION": 9,
    "$NODECOOR": 7,
    "$NET": 8,
    "$SETELEMENT": 8,          # 与 $NET 同 ID（1046/1046）
    "$DEFWASLABSECTION": 11,
    "$SETWALL": 5,
    "$SETSLAB": 6,
    "$DEFNODELOAD": 12,
    "$DEFLINELOAD": 13,
    "$DEFSLABLOAD": 14,
}

#: 无洞口哨兵（pdt_format.md §2.10：``HOLEID=-9999`` = 无洞【推断-高】）
NO_HOLE = -9999

#: 节点荷载/线荷载的力与弯矩分量顺序（pdt_format.md §2.13 / §2.15）
NODE_FORCES = ("PX", "PY", "PZ", "MX", "MY", "MZ")
LINE_FORCES = ("FX", "FY", "FZ", "MX", "MY", "MZ",
               "FX2", "FY2", "FZ2", "MX2", "MY2", "MZ2")

_RE_COMMENT_LINE = re.compile(r"^\s*;")


# ==========================================================================
# 词法层：把 .pdt 切成"记录"（契约 §b.4 / pdt_format.md §1.1）
# ==========================================================================

def _read_text(path: str) -> str:
    """GBK 严格解码（契约 §b.4/§g.1）：失败即 ``ValueError``，**禁止** ``errors='replace'``。"""
    with open(path, "rb") as fh:
        raw = fh.read()
    try:
        text = raw.decode("gbk")
    except UnicodeDecodeError as exc:
        raise ValueError(".pdt 不是 GBK 编码（契约 §b.4）：%s：%s" % (path, exc))
    if text.startswith("\ufeff"):
        text = text[1:]
    return text


def _parse_fields(lines: List[str]) -> Dict[str, List[str]]:
    """解析一条记录（可能由多条物理行组成）的字段。

    ``KEY= value, KEY= value, ...``；不含 ``=`` 的 token 追加到上一个字段的值列表
    （这就是 ``EXR`` / ``SLABID`` 折行的统一解法，契约 §b.4）。字段名大小写原样保留；
    完全没有 ``KEY=`` 的行（``$VERSION`` 的裸值行、``$DESIGNPARA`` 的纯数字行）
    落在空串键 ``''`` 上。
    """
    out: Dict[str, List[str]] = {}
    last: Optional[str] = None
    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        for token in s.split(","):
            t = token.strip()
            if not t:
                continue
            if "=" in t:
                key, val = t.split("=", 1)
                key = key.strip()
                if not key:
                    out.setdefault("", []).append(t)
                    continue
                last = key
                out.setdefault(key, []).append(val.strip())
            elif last is not None:
                out.setdefault(last, []).append(t)
            else:
                out.setdefault("", []).append(t)
    return out


def _sections(text: str) -> Tuple[Dict[Tuple[Optional[str], str], List[Dict[str, List[str]]]],
                                  Dict[Tuple[Optional[str], str], int]]:
    """切成 ``{(工况, 节名): [记录, ...]}`` 与 ``{(工况, 节名): 物理行数}``。

    缩进 ≤4 = 新记录、>4 = 续行（pdt_format.md §1.1，实测无例外）。
    """
    records: Dict[Tuple[Optional[str], str], List[Dict[str, List[str]]]] = {}
    phys: Dict[Tuple[Optional[str], str], int] = {}
    group: Optional[str] = None
    section: Optional[str] = None
    cur: Optional[List[str]] = None

    body = text.replace("\r\n", "\n").replace("\r", "\n")
    for line in body.split("\n"):
        if not line.strip():
            continue
        stripped = line.strip()
        if _RE_COMMENT_LINE.match(line):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if stripped.startswith("$"):
            name = stripped.split()[0].rstrip(",")
            section = name
            cur = None
            if name in LOAD_GROUPS:
                group = name
            elif name not in LOAD_SUBSECTIONS:
                group = None
            continue
        if section is None:
            continue
        key = (group, section)
        phys[key] = phys.get(key, 0) + 1
        if indent <= 4 or cur is None:
            cur = [line]
            records.setdefault(key, []).append(_parse_fields(cur))
        else:
            cur.append(line)
            # 续行：把本行并进"当前记录"（重新解析整块，规则见 _parse_fields）
            records[key][-1] = _parse_fields(cur)
    return records, phys


# ==========================================================================
# 取值小工具
# ==========================================================================

def _raw(fields: Dict[str, List[str]], key: str, idx: int = 0) -> str:
    vals = fields.get(key)
    if not vals or idx >= len(vals):
        return ""
    return vals[idx]


def _num(fields: Dict[str, List[str]], key: str, idx: int = 0,
         default: float = 0.0) -> float:
    s = _raw(fields, key, idx).strip()
    if not s:
        return default
    try:
        return float(s)
    except ValueError:
        return default


def _int(fields: Dict[str, List[str]], key: str, idx: int = 0,
         default: int = 0) -> int:
    v = _num(fields, key, idx, float(default))
    try:
        return int(v)
    except (OverflowError, ValueError):
        return default


def _ring_order(netids: List[int], nets: Dict[int, Tuple[int, int]]) -> Optional[List[int]]:
    """把有序闭合环（``NETID`` 列表）解成顶点序列（节点 ID，长度 = 环边数，不重复首点）。

    相邻 NET 共用一个端点（pdt_format.md §2.10，样本 335/335 全部闭合）。非单环时返回
    ``None``（调用方记 ``notes``，不静默丢弃）。
    """
    if not netids:
        return None
    adj: Dict[int, List[int]] = {}
    for nid in netids:
        seg = nets.get(nid)
        if seg is None:
            return None
        a, b = seg
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    if any(len(v) != 2 for v in adj.values()):
        return None
    n = len(netids)
    seq: List[int] = []
    prev: Optional[int] = None
    cur = nets[netids[0]][0]
    for step in range(n):
        seq.append(cur)
        cands = adj.get(cur, [])
        if step == 0:                       # 起点：任选一个方向起步
            if not cands:
                return None
            nxt = cands[0]
        else:
            rest = [x for x in cands if x != prev]
            if len(rest) != 1:
                return None
            nxt = rest[0]
        prev, cur = cur, nxt
    if cur != seq[0] or len(set(seq)) != n:
        return None
    return seq


# ==========================================================================
# 主入口
# ==========================================================================

def read_pdt(path: str) -> Model:
    """读取 ``.pdt`` → :class:`canonical.Model`（契约 §b.4）。只读，不写任何文件。"""
    text = _read_text(path)
    records, phys = _sections(text)
    notes: List[str] = []
    model = Model(source=str(path), source_format="pdt", units="mm")

    def recs(name: str, group: Optional[str] = None) -> List[Dict[str, List[str]]]:
        return records.get((group, name), [])

    # ---------------------------------------------------------------- §0 版本
    version = ""
    for f in recs("$VERSION"):
        if f.get(""):
            version = f[""][0]
    notes.append("源文件 $VERSION=%s（pdt_format.md §2.1）；节记录数：%s"
                 % (version or "?",
                    ", ".join("%s%s=%d" % (k[1], "(%s)" % k[0] if k[0] else "", len(v))
                              for k, v in sorted(records.items(),
                                                 key=lambda kv: (str(kv[0]), kv[0][1])))))

    # -------------------------------------------------- §0b ID 规范自校验
    # ID = N × 100 + CC（pdt_format.md §3.2【事实】）。本模块不解码 ID，只用它校验：
    # 类码不符 / 全局序号被两个**不同类码**复用，都要看得见（不静默）。
    bad_class: List[str] = []
    seq_cc: Dict[int, set] = {}
    n_id = 0
    for (grp, sec), lst in records.items():
        cc = ID_CLASS.get(sec)
        if cc is None:
            continue
        for f in lst:
            for i in range(len(f.get("ID", []))):
                iid = _int(f, "ID", i)
                n_id += 1
                if iid % 100 != cc:
                    bad_class.append("%s %d(CC=%d 应为 %d)" % (sec, iid, iid % 100, cc))
                seq_cc.setdefault(iid // 100, set()).add(cc)
    reused = ["N=%d 被 CC=%s 复用" % (n, sorted(ccs))
              for n, ccs in sorted(seq_cc.items()) if len(ccs) > 1]
    dense = (sorted(seq_cc) == list(range(1, len(seq_cc) + 1)))
    notes.append("ID 规范自校验（pdt_format.md §3.2：ID = 全局序号 ×100 + 类码）："
                 "核对 %d 个带 ID 的对象；类码不符 %d 个%s；全局序号去重后 %d 个%s%s"
                 "（$NET 与 $SETELEMENT 同为 CC=8 且共用 ID，属正常）"
                 % (n_id, len(bad_class),
                    ("：%s" % bad_class[:5]) if bad_class else "",
                    len(seq_cc),
                    "，且密集连续 1..%d" % len(seq_cc) if dense else "",
                    ("；**跨类码复用** %s" % reused[:5]) if reused else "（无跨类码复用）"))

    # ---------------------------------------------------------------- §1 节点
    stories: Dict[int, Tuple[float, float, float]] = {}   # ID -> (BL, TL, HI)
    for f in recs("$STORY"):
        if f.get("ID"):
            stories[_int(f, "ID")] = (_num(f, "BL"), _num(f, "TL"), _num(f, "HI"))

    nodes: Dict[int, Tuple[float, float, float]] = {}
    node_floor: Dict[int, int] = {}
    dup_nodes = 0
    for f in recs("$NODECOOR"):
        if not f.get("ID"):
            notes.append("$NODECOOR 有一行无 ID，已跳过（pdt_format.md §1.2 的裸值行）")
            continue
        nid = _int(f, "ID")
        if nid in nodes:
            dup_nodes += 1
        nodes[nid] = (_num(f, "X"), _num(f, "Y"), _num(f, "Z"))
        node_floor[nid] = _int(f, "FLOORID", default=-1)
    if dup_nodes:
        notes.append("$NODECOOR 有 %d 个重复节点 ID（后者覆盖前者）" % dup_nodes)

    # ------------------------------------------------- 平面型 Level（§a.3）
    zs = sorted({round(v[2], 6) for v in nodes.values()})
    levels = [Level(stdflr_id=i + 1, floor_id=0, no=i + 1,
                    z_bot=z, z_top=z, height=0.0, name="")
              for i, z in enumerate(zs)]
    z2level = {lv.z_top: lv.stdflr_id for lv in levels}

    def level_of(z: float) -> Optional[int]:
        key = round(z, 6)
        if key in z2level:
            return z2level[key]
        best, bd = None, None
        for lv in levels:
            d = abs(lv.z_top - z)
            if bd is None or d < bd:
                best, bd = lv, d
        if best is not None and bd is not None and bd <= 1e-6:
            return best.stdflr_id
        return None

    model.levels = levels
    if len(z2level) != len(levels):
        notes.append("Level 标高有重复（%d 个 Level / %d 个唯一标高）"
                     % (len(levels), len(z2level)))

    # $STORY 与 FLOORID 只用来**交叉核对**（契约 §a.3 明令不得用它们建 Level）
    if stories:
        tops = [v[1] for _, v in sorted(stories.items())]
        notes.append("$STORY 共 %d 层（pdt_format.md §2.3）：TL=%s；其中 %d/%d 个 TL 等于"
                     "本次按节点 Z 推出的标高（其余是层内标高或夹层）；"
                     "契约 §a.3 实测 11 个标高里只有 5 个是层顶，故 Level 一律按节点 Z 分组建"
                     % (len(tops), tops, sum(1 for t in tops if round(t, 6) in z2level),
                        len(tops)))
        mismatch = []
        for nid, fno in node_floor.items():
            if fno in stories:
                bl, tl, _ = stories[fno]
                z = nodes[nid][2]
                if not (bl - 1e-6 <= z <= tl + 1e-6):
                    mismatch.append(nid)
        notes.append("FLOORID 与节点几何不符的节点 %d 个（pdt_format.md §8.3 记 38 个："
                     "4 个在基础 -5000、34 个在 22800 夹层）——这些节点一律按 Z 归入"
                     "对应平面，不按 FLOORID；%s"
                     % (len(mismatch), mismatch[:8]))

    # 节点 → Joint（z = level.z_top + hdiff，hdiff 恒 0）
    per_level_no: Dict[int, int] = {}
    for nid in sorted(nodes):
        x, y, z = nodes[nid]
        lv = level_of(z)
        if lv is None:
            notes.append("节点 %s 的 Z=%g 找不到 Level（已跳过该节点）" % (nid, z))
            continue
        per_level_no[lv] = per_level_no.get(lv, 0) + 1
        model.joints[nid] = Joint(id=nid, level=lv, x=x, y=y, z=z,
                                  no=0, hdiff=0.0)
    # 层内编号按 (y, x) 升序 1..n（与契约 §b.3 的 pkpmJoint.No_ 合成口径一致）
    for lv in levels:
        js = [j for j in model.joints.values() if j.level == lv.stdflr_id]
        for i, j in enumerate(sorted(js, key=lambda j: (j.y, j.x)), 1):
            j.no = i

    # ---------------------------------------------------------------- §2 线段
    nets: Dict[int, Tuple[int, int]] = {}
    for f in recs("$NET"):
        if not f.get("ID"):
            continue
        nets[_int(f, "ID")] = (_int(f, "NODES"), _int(f, "NODEE"))
    dangling = [nid for nid, (a, b) in nets.items() if a not in nodes or b not in nodes]
    if dangling:
        notes.append("$NET 有 %d 条线段的端点在 $NODECOOR 里找不到（前 5 个：%s）"
                     % (len(dangling), dangling[:5]))

    # -------------------------------------------------------------- §3 材料
    materials: Dict[int, Tuple[str, int]] = {}
    for f in recs("$DEFMATERIAL"):
        if not f.get("ID"):
            continue
        materials[_int(f, "ID")] = (_raw(f, "NAME"), _int(f, "TYPE"))

    # -------------------------------------------------------------- §4 截面
    n_steel_no_t = 0
    for f in recs("$DEFFRAMESECTION"):
        if not f.get("ID"):
            continue
        sid = _int(f, "ID")
        kind = _int(f, "KIND", default=_int(f, "SHAPE"))
        name = _raw(f, "NAME") or _raw(f, "NAME1")
        name1 = _raw(f, "NAME1")
        m = _int(f, "M")
        dims: Dict[str, object] = {}
        for key in ("B1", "B2", "B3", "H1", "H2", "H3", "T1", "T2", "T3", "T4", "T5", "T6"):
            if key in f:
                dims[key] = _num(f, key)
        note = ("pdt $DEFFRAMESECTION：dims 键 = 文件字段名（契约 §b.4）；"
                "SHAPE=1 时 B1×H1 = 矩形宽×高、SHAPE=3 时 B1 = 直径、"
                "SHAPE=39 时 B1 = 翼缘宽 / H1 = 高（pdt_format.md §2.6，【推断-高】）；"
                "mat 取 M=%d（pdt_format.md §2.6【推断-中】：6=混凝土/5=型钢，"
                "与 §a.2 的 5=钢/6=混凝土 同名同义）" % m)
        if name1 and name1 != name:
            note += "；NAME1=%r" % name1
        if kind == 39:
            tvals = [dims.get("T%d" % i, 0.0) for i in range(1, 7)]
            if not any(tvals):
                n_steel_no_t += 1
            note += ("；T1..T6 全 0——本格式不提供型钢板厚，只能靠 NAME 到"
                     "截面匹配文件映射（pdt_format.md §2.6，契约 §b.4 点名的坑）")
        model.sections[sid] = Section(id=sid, kind=kind,
                                      mat=m if m in (5, 6) else 0,
                                      name=name, dims=dims, table="pdt",
                                      no=_int(f, "ID"), shapeval="", params=[],
                                      note=note)
    if n_steel_no_t:
        notes.append("$DEFFRAMESECTION 有 %d 个 SHAPE=39 型钢截面的 T1..T6 全为 0："
                     "本格式不含型钢板厚，PDMS 规格只能靠名称映射（pdt_format.md §2.6）"
                     % n_steel_no_t)

    # 墙/板截面（不建 Section，只留 厚度/名称，契约 §b.4）
    panel_sec: Dict[int, Tuple[str, float]] = {}
    for f in recs("$DEFWASLABSECTION"):
        if not f.get("ID"):
            continue
        panel_sec[_int(f, "ID")] = (_raw(f, "NAME"), _num(f, "T1"))
    if panel_sec:
        notes.append("$DEFWASLABSECTION（墙板截面）按契约 §b.4 **不**建 Section，"
                     "厚度直接落到 Slab.thickness/Wall.thickness：%s"
                     % ", ".join("%s(ID=%s,T1=%g)" % (v[0], k, v[1])
                                 for k, v in sorted(panel_sec.items())))

    # ------------------------------------------------------------ §5 构件
    per_level_no = {}
    n_other_type: Dict[str, int] = {}
    n_brace = 0
    ecc_members: List[Tuple[int, str, Tuple[float, ...]]] = []
    for f in recs("$SETELEMENT"):
        if not f.get("ID"):
            continue
        eid = _int(f, "ID")
        etype = _raw(f, "TYPE").strip()
        if etype not in (TYPE_COLUMN, TYPE_BEAM, TYPE_BRACE):
            n_other_type[etype] = n_other_type.get(etype, 0) + 1
            continue
        netid = _int(f, "NETID")
        seg = nets.get(netid)
        if seg is None or seg[0] not in nodes or seg[1] not in nodes:
            notes.append("构件 %s（TYPE=%s）的 NETID=%s 找不到可解析线段，已跳过"
                         % (eid, etype, netid))
            continue
        a, b = nodes[seg[0]], nodes[seg[1]]
        if etype == TYPE_COLUMN:
            # 契约 §b.4：柱的 start 在下端、end 在上端
            start, end = (a, b) if a[2] <= b[2] else (b, a)
            mtype = "column"
        elif etype == TYPE_BRACE:
            # §0.4-5/§j.4.5/§12#15：TYPE=3 冻结为支撑；start = $NET.NODES 端
            start, end, mtype = a, b, "brace"
            n_brace += 1
        else:
            start, end, mtype = a, b, "beam"
        lv = level_of(start[2])
        if lv is None:
            notes.append("构件 %s 的起点 Z=%g 找不到 Level，已跳过" % (eid, start[2]))
            continue
        ecc6 = tuple(_num(f, k) for k in ("ECS1", "ECS2", "ECS3",
                                          "ECE1", "ECE2", "ECE3"))
        if any(ecc6):
            ecc_members.append((eid, mtype, ecc6))
        per_level_no[lv] = per_level_no.get(lv, 0) + 1
        matid = _int(f, "MATID1", default=-9999)
        model.members.append(Member(
            id=eid, type=mtype, level=lv, section=_int(f, "SECTID"),
            start=start, end=end, rotation=_num(f, "ANG"),
            # §0.4-10（R3 复核发现④）：原始 (ECS1..ECE3) 记进 Member.ecc（**仅记录**，
            # 方向语义未证实 ⇒ 仍不并入 start/end，§a.2/§12#6）；全 0 时留空。
            # write_pdt 对 6 元组原样写回 ⇒ .pdt→.pdt 往返不再丢偏心字段。
            ecc=ecc6 if any(ecc6) else (), no=per_level_no[lv], grid_id=None,
            node_id=None, jydef="", hdiff_start=0.0, hdiff_end=0.0,
            material=materials.get(matid, ("", 0))[0], jusl="", meml=""))
    if n_brace:
        notes.append("$SETELEMENT 有 %d 条 TYPE=3 记录 ⇒ 按 §0.4-5/§j.4.5/§12#15 冻结为 "
                     "Member.type='brace'（水平/竖向支撑由几何 |ΔZ|≤1e-6 在 PDMS 侧再分，"
                     "§d.4-2）；样本无支撑，此映射**待实机确认**" % n_brace)
    if n_other_type:
        notes.append("$SETELEMENT 有 TYPE 不在 {1=柱,2=梁,3=支撑} 的记录 %s，"
                     "按契约 §b.4 不进 members（$SETWALL/$SETSLAB 的 5/6 走各自的段，"
                     "不在此处）" % sorted(n_other_type.items()))

    # 契约 §a.2/§12#6：偏心正负方向未证实 ⇒ 不并入几何，逐条回流到报告；
    # 原始值已记进 Member.ecc（6 元组，仅记录，§0.4-10），write_pdt 会原样写回
    if ecc_members:
        by_type: Dict[str, int] = {}
        for _, mt, _ in ecc_members:
            by_type[mt] = by_type.get(mt, 0) + 1
        dist: Dict[Tuple[float, ...], int] = {}
        for _, _, v in ecc_members:
            dist[v] = dist.get(v, 0) + 1
        notes.append("非零偏心（ECS1/2/3+ECE1/2/3 任一非 0）构件 %d 根，按类型 %s；"
                     "取值分布（ECS1,ECS2,ECS3,ECE1,ECE2,ECE3）=%s。"
                     "**实测**：TYPE=1（柱）121 根全部为 0，非零的 121 根全部是 "
                     "TYPE=2（梁，两端等高）——与 pdt_format.md §2.9 的"
                     "\"925 梁全 0 / 121 柱全部 ECS1=ECE1≠0\"**相反**（该节的勘误见"
                     " test/_r3_probe_ecc_fact 输出与 docs）；"
                     "本文以原文实测为准（正则直扫 $SETELEMENT 复核，见 "
                     "test/pdt_secmap_selfcheck.py 的 C 段）。"
                     "方向语义未证实（jwd_format.md §9.3#6），按契约 §a.2 "
                     "**未**并入 start/end；原始值记 Member.ecc（§0.4-10）"
                     % (len(ecc_members), by_type, sorted(dist.items())))
        notes.append("非零偏心构件 ID：%s"
                     % ",".join(str(e) for e, _, _ in ecc_members))

    # NET 中未被 $SETELEMENT 引用的部分 = 墙/板环边（pdt_format.md §3.2 次级结论 2）
    used_net = {_int(f, "NETID") for f in recs("$SETELEMENT") if f.get("ID")}
    panel_edges = sorted(set(nets) - used_net)
    if panel_edges:
        notes.append("有 %d 条 $NET 不被任何 $SETELEMENT 引用（= 墙/板环的边，"
                     "pdt_format.md §3.2）：%s" % (len(panel_edges), panel_edges))

    # -------------------------------------------------------------- §6 板
    slab_source_data: List[Tuple[int, float, str]] = []   # (slab_id, thickness, 说明)
    walls_source: List[Tuple[int, float, float, str]] = []
    for f in recs("$SETSLAB"):
        if not f.get("ID"):
            continue
        sid = _int(f, "ID")
        secid = _int(f, "SECTID")
        if secid not in panel_sec:
            notes.append("板 %s 的 SECTID=%s 不在 $DEFWASLABSECTION，厚度按 0 处理"
                         % (sid, secid))
        thickness = panel_sec.get(secid, ("", 0.0))[1]
        netids = [_int(f, "NETID", i) for i in range(len(f.get("NETID", [])))]
        if _int(f, "NUB", default=len(netids)) != len(netids):
            notes.append("板 %s 的 NUB=%s 与 NETID 个数 %d 不一致（pdt_format.md §2.10）"
                         % (sid, _raw(f, "NUB"), len(netids)))
        order = _ring_order(netids, nets)
        if order is None:
            notes.append("板 %s 的 NETID 环不是单环/未闭合，已跳过（%s）" % (sid, netids))
            continue
        pts = [nodes[n] for n in order]
        z0 = pts[0][2]
        if any(abs(p[2] - z0) > TOL for p in pts):
            notes.append("板 %s 的环顶点 Z 不一致（%s），按首顶点 %g 处理"
                         % (sid, sorted({p[2] for p in pts}), z0))
        lv = level_of(z0)
        if lv is None:
            notes.append("板 %s 的 Z=%g 找不到 Level，已跳过" % (sid, z0))
            continue
        hole = _int(f, "HOLEID", default=NO_HOLE) != NO_HOLE
        model.slabs.append(Slab(
            id=sid, level=lv, polygon=[(p[0], p[1]) for p in pts], z=z0,
            thickness=thickness, is_hole=hole, dead=0.0, live=0.0,
            grid_edges=[], no=0, spec_path="", ori=PANE_ORI, sjus=PANE_SJUS))
        slab_source_data.append((sid, thickness, ""))

    # 层内编号（同 Member.no 的口径）
    for lv in levels:
        ss = [s for s in model.slabs if s.level == lv.stdflr_id]
        for i, s in enumerate(ss, 1):
            s.no = i

    # -------------------------------------------------------------- §7 墙
    for f in recs("$SETWALL"):
        if not f.get("ID"):
            continue
        wid = _int(f, "ID")
        secid = _int(f, "SECTID")
        pname, thickness = panel_sec.get(secid, ("", 0.0))
        netids = [_int(f, "NETID", i) for i in range(len(f.get("NETID", [])))]
        if _int(f, "NUB", default=len(netids)) != len(netids):
            notes.append("墙 %s 的 NUB=%s 与 NETID 个数 %d 不一致（pdt_format.md §2.10）"
                         % (wid, _raw(f, "NUB"), len(netids)))
        order = _ring_order(netids, nets)
        if order is None:
            notes.append("墙 %s 的 NETID 环不是单环/未闭合，已跳过（%s）" % (wid, netids))
            continue
        loop = [nodes[n] for n in order]
        z_bot = min(p[2] for p in loop)
        z_top = max(p[2] for p in loop)
        lv = level_of(z_bot)
        if lv is None:
            notes.append("墙 %s 的底标高 %g 找不到 Level，已跳过" % (wid, z_bot))
            continue
        model.walls.append(Wall(id=wid, level=lv, thickness=thickness,
                                z_bot=z_bot, z_top=z_top, loop=loop,
                                section=-1, no=0, name=pname, spec_path="",
                                sjus=WALL_DEFAULT_SJUS))
        walls_source.append((wid, z_bot, z_top, pname))

    for lv in levels:
        ws = [w for w in model.walls if w.level == lv.stdflr_id]
        for i, w in enumerate(ws, 1):
            w.no = i

    # ------------------------------------------------------------ §8 荷载
    _attach_loads(model, records, notes)
    _apply_panel_loads(model, records, notes)

    if slab_source_data:
        notes.append("板厚来自 $DEFWASLABSECTION.T1（%d 块板）；墙 %d 面（%s），"
                     "板/墙的 PDMS 规格由 SectionMap 用 T<厚度> 键解析（契约 §e.3 末行）"
                     % (len(slab_source_data), len(walls_source),
                        ", ".join("ID=%d z=%g..%g(%s)" % w for w in walls_source)))

    # ------------------------------------------------------------ §9 其余
    if recs("$DESIGNPARA"):
        notes.append("$DESIGNPARA 共 %d 条记录（样本 50 行 × 20 列 = 1000 个无字段名浮点数），"
                     "逐项含义未确证（pdt_format.md §4），**未**进入 Model"
                     % len(recs("$DESIGNPARA")))
    rigid = []
    for f in recs("$RIGID"):
        ids = [_int(f, "SLABID", i) for i in range(len(f.get("SLABID", [])))]
        rigid.append((_int(f, "ID"), _int(f, "FLOORID"), _int(f, "NUB", default=len(ids)),
                      len(ids)))
    if rigid:
        notes.append("$RIGID 刚性楼板 %d 组（Model 无对应字段）：%s；"
                     "注意层 3 有**两个**刚性组（22800 夹层平台是独立刚性楼板，"
                     "pdt_format.md §2.11），按 FLOORID 归并会错"
                     % (len(rigid), rigid))
    for group in LOAD_GROUPS:
        n = sum(phys.get((group, s), 0) for s in LOAD_SUBSECTIONS)
        if n:
            notes.append("%s 工况子节物理行数：%s"
                         % (group, ", ".join("%s=%d" % (s, len(recs(s, group)))
                                             for s in LOAD_SUBSECTIONS
                                             if recs(s, group))))
    notes.append("EXI/EXR 属性袋（pdt_format.md §1.3/§6）本模块只用于折行解析，未解码"
                 "任何属性 ID（除 $SETSLABLOAD 的 LOADID 符号规则外）；"
                 "Model 无对应字段，故不搬运")
    model.notes = notes          # 契约 §a.9：读取期问题/假设的唯一回流通道
    return model


# ==========================================================================
# 荷载搬运（契约 §b.4 的可选部分；语义未证实的部分一律进 notes）
# ==========================================================================

def _attach_loads(model: Model,
                  records: Dict[Tuple[Optional[str], str], List[Dict[str, List[str]]]],
                  notes: List[str]) -> None:
    """``$SETNODELOAD`` → ``joint-point``、``$SETLINELOAD`` → ``beam-line``。

    只搬运力/弯矩分量（``NODE_FORCES`` / ``LINE_FORCES``），``values`` 与 ``raw`` 等长；
    目标不可解析时记 ``notes`` 并跳过（**不**制造 ``E-LOAD-TARGET``）。
    """
    def recs(name: str, group: Optional[str] = None):
        return records.get((group, name), [])

    # ---- 节点荷载
    def_node: Dict[int, Dict[str, List[str]]] = {}
    for group in LOAD_GROUPS:
        for f in recs("$DEFNODELOAD", group):
            if f.get("ID"):
                def_node[_int(f, "ID")] = f
    n_node_load = 0
    for group in LOAD_GROUPS:
        for f in recs("$SETNODELOAD", group):
            if not f.get("ID"):
                continue
            tgt = _int(f, "ID")
            if tgt not in model.joints:
                notes.append("%s 的 $SETNODELOAD 目标节点 %s 不存在，已跳过" % (group, tgt))
                continue
            for i in range(len(f.get("LOADID", []))):
                lid = _int(f, "LOADID", i)
                src = def_node.get(lid)
                if src is None:
                    notes.append("%s 的 $SETNODELOAD LOADID=%s 在 $DEFNODELOAD 里不存在"
                                 % (group, lid))
                    continue
                raw = [_raw(src, k) for k in NODE_FORCES]
                model.loads.append(Load(
                    id=lid, kind="joint-point", target_id=tgt,
                    values=tuple(_parse_or_none(v) for v in raw),
                    raw=list(raw), load_sect_id=lid,
                    level=model.joints[tgt].level))
                n_node_load += 1

    # ---- 线荷载
    def_line: Dict[int, Dict[str, List[str]]] = {}
    for group in LOAD_GROUPS:
        for f in recs("$DEFLINELOAD", group):
            if not f.get("ID"):
                continue
            lid = _int(f, "ID")
            if lid in def_line:
                notes.append("$DEFLINELOAD ID=%s 在两个工况里重复（后者覆盖前者）" % lid)
            def_line[lid] = f
    member_ids = {m.id for m in model.members}
    n_line_load = 0
    types: Dict[str, int] = {}
    ucs: Dict[str, int] = {}
    n_missing_target = 0
    for group in LOAD_GROUPS:
        for f in recs("$SETLINELOAD", group):
            if not f.get("ID"):
                continue
            tgt = _int(f, "ID")
            if tgt not in member_ids:
                n_missing_target += 1
                continue
            lvl = next(m.level for m in model.members if m.id == tgt)
            for i in range(len(f.get("LOADID", []))):
                lid = _int(f, "LOADID", i)
                src = def_line.get(lid)
                if src is None:
                    notes.append("%s 的 $SETLINELOAD LOADID=%s 在 $DEFLINELOAD 里不存在"
                                 % (group, lid))
                    continue
                keys = [k for k in LINE_FORCES if k in src]
                raw = [_raw(src, k) for k in keys]
                vals = tuple(_parse_or_none(v) for v in raw)
                model.loads.append(Load(
                    id=lid, kind="beam-line", target_id=tgt, values=vals,
                    raw=list(raw), load_sect_id=lid, level=lvl))
                n_line_load += 1
                t = _raw(src, "TYPE") or "?"
                types[t] = types.get(t, 0) + 1
                u = _raw(src, "UCS") or "?"
                ucs[u] = ucs.get(u, 0) + 1
    if n_missing_target:
        notes.append("$SETLINELOAD 有 %d 条的目标构件不在 members 里，已跳过" % n_missing_target)
    if n_node_load or n_line_load:
        notes.append("荷载只做**原样搬运 + 计数**（契约 §12#8/§9.3#8 冻结）："
                     "joint-point %d 条（%s）、beam-line %d 条（TYPE 分布 %s、UCS 分布 %s）；"
                     "类型码含义与单位未证实，不参与几何。"
                     "线荷载的 DS/S（位置/长度，**单位 m**，pdt_format.md §2.15/§9.11）"
                     "在 Model.Load 里无字段，已丢弃并在本注记说明"
                     % (n_node_load, ", ".join(NODE_FORCES), n_line_load, types, ucs))


def _parse_or_none(s: str) -> Optional[float]:
    if s is None or str(s).strip() == "":
        return None
    try:
        return float(str(s).strip())
    except ValueError:
        return None


def _apply_panel_loads(model: Model,
                       records: Dict[Tuple[Optional[str], str], List[Dict[str, List[str]]]],
                       notes: List[str]) -> None:
    """``$SETSLABLOAD`` → ``Slab.dead/Slab.live``（恒载/活载面荷载，kN/m²）。

    ``LOADID`` 的符号规则（pdt_format.md §2.18，本格式最关键的发现之一）：
    **正号** ⇒ 引用同名 ``$DEFSLABLOAD``；**负号** ⇒ 跨表引用 ``$DEFLINELOAD``
    （样本里只有 4 面墙的恒载走这条负号路径，是沿墙的均布线荷载）。
    """
    def recs(name: str, group: Optional[str] = None):
        return records.get((group, name), [])

    def_slab: Dict[Tuple[str, int], float] = {}
    for group in LOAD_GROUPS:
        for f in recs("$DEFSLABLOAD", group):
            if f.get("ID"):
                def_slab[(group, _int(f, "ID"))] = _num(f, "FZ")
    def_line: Dict[int, Dict[str, List[str]]] = {}
    for group in LOAD_GROUPS:
        for f in recs("$DEFLINELOAD", group):
            if f.get("ID"):
                def_line[_int(f, "ID")] = f

    slabs = {s.id: s for s in model.slabs}
    walls = {w.id: w for w in model.walls}
    hit_slab = {"$DEADLOAD": 0, "$LIVELOAD": 0}
    wall_line: List[Tuple[int, int, float, float]] = []
    n_missing = 0
    for group in LOAD_GROUPS:
        attr = "dead" if group == "$DEADLOAD" else "live"
        for f in recs("$SETSLABLOAD", group):
            if not f.get("ID"):
                continue
            tgt = _int(f, "ID")
            value: Optional[float] = None
            for i in range(len(f.get("LOADID", []))):
                lid = _int(f, "LOADID", i)
                if lid > 0:
                    if (group, lid) in def_slab:
                        value = def_slab[(group, lid)]
                    else:
                        n_missing += 1
                else:
                    src = def_line.get(-lid)
                    if src is None:
                        n_missing += 1
                        continue
                    if tgt in walls:
                        wall_line.append((tgt, -lid, _num(src, "FZ"), _num(src, "S")))
                    elif tgt in slabs:
                        # 面荷载跨表引用线荷载：本格式未出现，保守按"未使用"处理
                        n_missing += 1
                    else:
                        n_missing += 1
            if value is not None:
                if tgt in slabs:
                    setattr(slabs[tgt], attr, value)
                    hit_slab[group] += 1
                elif tgt not in walls:
                    n_missing += 1
    if hit_slab["$DEADLOAD"] or hit_slab["$LIVELOAD"]:
        notes.append("$SETSLABLOAD → Slab.dead/Slab.live（面荷载，kN/m²，"
                     "pdt_format.md §2.17【推断-高】）：恒载 %d 块、活载 %d 块"
                     % (hit_slab["$DEADLOAD"], hit_slab["$LIVELOAD"]))
    if wall_line:
        notes.append("**墙的恒载**走 $SETSLABLOAD 的负号 LOADID → 跨表引用 $DEFLINELOAD，"
                     "是沿墙的均布线荷载（pdt_format.md §2.18）：%s；"
                     "Model.Wall 无恒载字段，故未搬运，PDMS 侧如需荷载须另行处理"
                     % ", ".join("墙 %d ← 线荷载 %d (FZ=%g kN/m, S=%g m)" % w
                                 for w in wall_line))
    if n_missing:
        notes.append("$SETSLABLOAD 有 %d 处 LOADID 未能解析（含跨表/缺定义），"
                     "对应荷载未搬运" % n_missing)
