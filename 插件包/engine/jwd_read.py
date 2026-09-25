# -*- coding: utf-8 -*-
"""PKPM ``.jwd``（SQLite3）→ 规范模型 :class:`canonical.Model`。

契约：``spec/CONTRACT.md``
    * §a.2 数据结构、§a.3 Level 的两种形态（**.jwd = 楼层型**）、§a.4 ShapeVal 解码、
      §a.5 几何公式、§a.7 validate、§a.8 不得臆造墙、§a.9 ``notes`` 是唯一回流通道、
      §b.2 本函数的签名与纪律、§g 编码纪律。
证据：``_recon/jwd_format.md``（本文档注释里出现的 §1–§9 均指该文件）。

函数（契约 §b.1 冻结签名）::

    read_jwd(path: str) -> Model

纪律
----
1. **只读**：``sqlite3.connect('file:<path>?mode=ro', uri=True)``；不写任何文件，
   也不对用户原件做任何写操作（含 PRAGMA 写入）。
2. **文本列逐值解码**（契约 §b.2）：``ASCII -> UTF-8 -> GBK``，见 :func:`dec`。
   整体 ``text_factory=gbk`` 会得到乱码，整体 UTF-8 会丢 GBK 列（jwd_format.md §9.1）。
3. **层标高只用 ``pkpmFloor``**：``z_bot = LevelB``、``z_top = LevelB + Height``；
   ``pkpmStdFlr.Height`` 在本样本恒 0，**禁止**使用（契约 §a.3 / jwd_format.md §4.3）。
   标准层平面画在**层顶**（板 ``VertexZ`` 恒等于层高，柱自层底竖直贯穿本层）。
4. **禁止跨层按 ID 合并"同一物理构件"**（契约 §a.5；jwd_format.md §2.4：
   ``(StdFlrID, GridID)`` 恒 1 行，各层拥有独立节点/网格线/房间）。
5. 表不存在或列缺失 ⇒ 视为空，不报错（契约 §b.2）；未解码的非空表 ⇒ 写 ``notes``。
6. 仅 import ``canonical``（契约 §b.5，禁止环状依赖；禁止第三方包）。

``notes`` 行约定（``read_jwd`` 没有 report 参数，``notes`` 是唯一回流通道；本模块只写
``notes``，由 ``cli.py`` 汇总进 ``report.json`` —— 契约 §a.9/§h）::

    "工程名候选 PROJECT_NAME=<名字> ..."   -> CLI 的 --project 缺省值（契约 §b.2）
    "未解码表 <表名>：<行数> 行 ..."        -> report.skipped（未解码的非空表）
    "跳过 <对象>：..."                     -> report.skipped（被跳过的对象）
    其它                                   -> report.warnings / geometry_anomalies

``notes`` 的**顺序**是固定的（表名列表为模块常量），故 ``Model.to_json()`` 稳定可比对。
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:                                     # engine/ 在 sys.path 上（契约 C4 的用法）
    from canonical import (CONTRACT_VERSION, PANE_ORI, PANE_SJUS, Section, Joint,
                           Level, Load, Member, Model, Slab, TOL)
except ImportError:                      # 作为包导入：engine.jwd_read
    from .canonical import (CONTRACT_VERSION, PANE_ORI, PANE_SJUS, Section, Joint,
                            Level, Load, Member, Model, Slab, TOL)

__all__ = ["read_jwd", "dec", "SECTION_KIND_KNOWN", "kind_known"]

# --------------------------------------------------------------------------
# 表清单（实测 sqlite_master：46 张 pkpm* 表，契约 §0.2）
# --------------------------------------------------------------------------

#: read_jwd 真正消费的表（其余表只做"非空即留痕"）
CONSUMED_TABLES = (
    "pkpmStdFlr", "pkpmFloor", "pkpmJoint", "pkpmGrid",
    "pkpmBeamSect", "pkpmColSect", "pkpmBraceSect",
    "pkpmColSeg", "pkpmBeamSeg", "pkpmBraceSeg",
    "pkpmSlab", "pkpmLoadSect", "pkpmLoadSeg",
    "pkpmProperty", "pkpmSysInfo",
)

#: 语义**未解码**的对象表：非空时必须逐条留痕（契约 §a.8/§b.2，jwd_format.md §1.7）
UNDECODED_OBJECT_TABLES = (
    "pkpmWallSeg", "pkpmWallSect", "pkpmWallHole", "pkpmWallHoleDef",
    "pkpmStairSeg", "pkpmStairDef", "pkpmSubBeam",
    "pkpmCantiSlab", "pkpmCantiSlabDef", "pkpmColcapSect",
    "pkpmCraneDef", "pkpmCraneInfo",
    "pkpmDamperSect", "pkpmJointDamperSeg", "pkpmMemberDamperSeg",
    "pkpmMidBeamSeg", "pkpmMidSlab",
    "pkpmPetroDeviceSect", "pkpmPetroDeviceSeg",
    "pkpmULoadDef", "pkpmSlabJYDef", "pkpmBeamJYDef", "pkpmSlabHoleDef",
    "pkpmSatConstruct", "pkpmSatCover",
)

#: 语义已知、但规范模型里没有对应字段（读不出东西 ≠ 未解码）
NO_MODEL_FIELD_TABLES = (
    "pkpmAxis",          # 轴线：Model 无轴网字段；Name 全空（jwd_format.md §1.2）
    "pkpmSlabHole",      # 板洞索引记录；几何已在 RoomIsHole=1 的 pkpmSlab 行（§1.4）
    "pkpmStdFlrPara",    # 每标准层 26 项设计参数（§7.3）
    "pkpmSatTower", "pkpmSatTowPara", "pkpmSatTowReinInfo",   # 塔吊/施工（§7.4）
)

#: 每张未解码对象表在 notes 里最多列几个 ID（其余折叠成计数）
_MAX_LISTED_IDS = 20

# --------------------------------------------------------------------------
# ShapeVal 解码（契约 §a.4）
# --------------------------------------------------------------------------

#: Kind -> 字段布局是否已解码（False = ``dims`` 必须留空且 ``note`` 标 ``known=False``）
#: 依据：jwd_format.md §3.2 只给出 1/2/3/26/303 的布局（契约 §a.4 的冻结键表）
SECTION_KIND_KNOWN: Dict[int, bool] = {1: True, 2: True, 3: True, 26: True, 303: True}

_KIND_NOTE: Dict[int, str] = {
    1: "Kind=1 混凝土矩形：dims 的 B/H 先后为【推断-中】（jwd_format.md §9.3#4 / 契约 §12#3），"
       "需实机确认",
    2: "Kind=2 焊接工字形：值集合为【推断-高】；B/T 交错序【未知】（jwd_format.md §9.3#5），"
       "不得据此断定 DESP 顺序",
    3: "Kind=3 单尺寸钢截面：族别（圆钢/圆管/方管）与单位语义【未知】（jwd_format.md §9.3#1）",
    26: "Kind=26 型钢库：H/B/tf/tw 为【事实】（8 条中 7 条与 PDMS 截面库独立吻合，"
        "jwd_format.md §3.2）；ShapeVal 尺寸仅作校验，等级库映射以 Name 为准",
    303: "Kind=303 用户参数化截面：【事实】四重印证（jwd_format.md §3.2/§3.3）",
}


def kind_known(kind: int) -> bool:
    """该 Kind 的参数体布局是否已解码（契约 §a.4 的冻结键表只覆盖 1/2/3/26/303）。"""
    return bool(SECTION_KIND_KNOWN.get(int(kind), False))


def dec(b):
    """契约 §b.2 的文本列逐值解码：``ASCII -> UTF-8 -> GBK(replace)``。

    **事实**（jwd_format.md §9.1）：``pkpmColSect.Name``/``pkpmBraceSect.Name`` 是 GBK 字节
    （``b1a1b1da…`` = "薄壁…"），``pkpmLoadSect.Loadname`` 是 UTF-8 字节（``e697a0`` = "无"）；
    整体 gbk 或整体 utf-8 都会错。
    """
    if not isinstance(b, bytes):
        return b
    for enc in ('ascii', 'utf-8'):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode('gbk', 'replace')


def _text(v: Any) -> str:
    """TEXT 列取值：``None`` → ``''``；``bytes``（BLOB 型存储）走 :func:`dec` 解码。"""
    if v is None:
        return ''
    if isinstance(v, bytes):
        return dec(v)
    return str(v)


def _split_shapeval(sv: Any) -> List[str]:
    """``ShapeVal`` -> 字段列表（去掉尾部空串，**保留**中间的空字段）。"""
    toks = [t for t in _text(sv).split(',')]
    while toks and toks[-1].strip() == '':
        toks.pop()
    return toks


def _packed_spec_str(params: Sequence[str]) -> str:
    """Kind=303 的打包规格串（契约 §a.4）：``params[1:7]`` = 6 个 16 位整数，
    **低字节在前**拼两个 ASCII 字符，遇 ``0x00`` 截断。"""
    buf = bytearray()
    for t in list(params[1:7]):
        try:
            v = int(float(t or 0))
        except (TypeError, ValueError):
            v = 0
        buf.append(v & 0xFF)
        buf.append((v >> 8) & 0xFF)
    raw = bytes(buf).split(b"\x00")[0]
    try:
        return raw.decode("ascii")
    except UnicodeDecodeError:
        return raw.decode("ascii", "replace")


def decode_dims(kind: int, params: Sequence[str]) -> Tuple[Dict[str, Any], str]:
    """按契约 §a.4 的**冻结键表**解码 ``dims``，返回 ``(dims, 附加说明)``。

    只写**有证据**的键；未解码的 Kind 返回空 ``dims`` 并由调用方写 ``known=False``。
    """
    k = int(kind)
    p = list(params)
    extra = ""

    def f(i: int) -> float:
        return float(p[i])

    def i_(i: int) -> int:
        return int(float(p[i]))

    if k == 1 and len(p) >= 2:
        return {"B": f(0), "H": f(1)}, extra
    if k == 2 and len(p) >= 6:
        d = {"Tw": f(0), "H": f(1), "B1": f(2), "T1": f(3), "B2": f(4), "T2": f(5)}
        if not (d["B1"] == d["B2"] and d["T1"] == d["T2"]):
            extra = ("；本行 B1=%g B2=%g T1=%g T2=%g 不对称 ⇒ 契约 §e.3 判 unresolved"
                     "（无可信 DESP 顺序）" % (d["B1"], d["B2"], d["T1"], d["T2"]))
        return d, extra
    if k == 3 and len(p) >= 1:
        return {"d": f(0)}, extra
    if k == 26 and len(p) >= 7:
        d = {"family": i_(0), "subtype": i_(1), "H": f(2), "B": f(4),
             "tf": f(5), "tw": f(6)}
        if d["family"] == 32:      # 槽钢：子类型 1=普通 / 2=轻型（jwd_format.md §3.2）
            extra = ("；槽钢（family=32，子类型 %d）的 tf/tw 与 GB 表的对照未完成"
                     "（§9.3#2，轻型槽钢须查 GB/T 706 轻型表）" % d["subtype"])
        return d, extra
    if k == 303 and len(p) >= 27:
        return ({"family": i_(0), "spec_str": _packed_spec_str(p), "d": f(17),
                 "b": f(19), "lib_family": i_(26)}, extra)
    return {}, extra


# --------------------------------------------------------------------------
# 数值/文本工具
# --------------------------------------------------------------------------


def _int(v: Any, default: int = 0) -> int:
    if v is None:
        return default
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v
    try:
        return int(v)
    except (TypeError, ValueError):
        try:
            return int(float(str(v).strip()))
        except (TypeError, ValueError):
            return default


def _num(v: Any, default: float = 0.0, bad: Optional[List[Any]] = None) -> float:
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
        if bad is not None:
            bad.append(v)
        return default


def _floats(text: Any, bad: Optional[List[Any]] = None) -> List[float]:
    """逗号分隔的 TEXT 数值列 -> ``float`` 列表（跳过空字段，如 ``'1,2,'`` 的尾空）。"""
    out: List[float] = []
    for t in _text(text).split(','):
        s = t.strip()
        if not s:
            continue
        try:
            out.append(float(s))
        except ValueError:
            if bad is not None:
                bad.append(t)
    return out


def _ints(text: Any) -> List[int]:
    """``pkpmSlab.GridsID`` 一类的逗号分隔整数列表。"""
    out: List[int] = []
    for t in _text(text).split(','):
        s = t.strip()
        if not s:
            continue
        try:
            out.append(int(float(s)))
        except ValueError:
            continue
    return out


def _ro_uri(path: str) -> str:
    """契约 §b.2 的只读连接串。"""
    return 'file:' + str(path).replace('\\', '/') + '?mode=ro'


# --------------------------------------------------------------------------
# 读取器
# --------------------------------------------------------------------------


class _Stats:
    """读取期的统计（供 notes；解码失败**不得静默**，契约 §g.1）。"""

    def __init__(self) -> None:
        self.text_replaced = 0          # GBK 解码仍出现 U+FFFD 的文本值个数
        self.bad_num: List[Any] = []    # 数值列无法解析的原始值
        self.bad_xy: List[Any] = []     # 多边形 TEXT 列无法解析的原始片段

    def factory(self, b):
        if not isinstance(b, bytes):
            return b
        s = dec(b)
        if isinstance(s, str) and '\ufffd' in s:
            self.text_replaced += 1
        return s


class _Reader:
    """一次 ``read_jwd`` 的全部状态。"""

    def __init__(self, con: sqlite3.Connection, path: str, stats: _Stats) -> None:
        self.con = con
        self.path = path
        self.st = stats
        self._cols: Dict[str, List[str]] = {}
        self._tables: Optional[set] = None
        self.notes: List[str] = []
        self.model = Model(source=path, source_format='jwd', units='mm',
                           contract_version=CONTRACT_VERSION)
        self.lvm: Dict[int, Level] = {}
        self.grids: Dict[int, Tuple[int, int]] = {}
        self.load_sects: Dict[int, Tuple[Any, str]] = {}
        self.props: Dict[str, Dict[int, float]] = {}
        self.sec_mat: Dict[int, int] = {}

    # ------------------------------------------------------------- 库访问
    def _table_names(self) -> set:
        if self._tables is None:
            rows = self.con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            self._tables = {str(r[0]) for r in rows}
        return self._tables

    def cols(self, table: str) -> List[str]:
        if table not in self._cols:
            try:
                rows = self.con.execute('PRAGMA table_info(%s)' % table).fetchall()
            except sqlite3.Error:
                rows = []
            self._cols[table] = [str(r[1]) for r in rows]
        return self._cols[table]

    def exists(self, table: str) -> bool:
        return table in self._table_names() and bool(self.cols(table))

    def rows(self, table: str, cols: Sequence[str],
             order: Sequence[str] = ()) -> List[tuple]:
        """取列（缺列以 NULL 代替）；表不存在 ⇒ ``[]``（契约 §b.2，不报错）。"""
        have = self.cols(table)
        if not have:
            return []
        sel = ','.join(c if c in have else 'NULL AS %s' % c for c in cols)
        sql = 'SELECT %s FROM %s' % (sel, table)
        if order:
            sql += ' ORDER BY ' + ','.join(order)
        return self.con.execute(sql).fetchall()

    def count(self, table: str) -> int:
        if not self.exists(table):
            return 0
        return int(self.con.execute('SELECT COUNT(*) FROM %s' % table).fetchone()[0])

    def ids(self, table: str, limit: int = _MAX_LISTED_IDS) -> Tuple[List[int], int]:
        """``(前 limit 个 ID, 总行数)``；无 ID 列时返回 ``([], 行数)``。"""
        if not self.exists(table):
            return [], 0
        n = self.count(table)
        if 'ID' not in self.cols(table):
            return [], n
        got = [int(r[0]) for r in self.rows(table, ('ID',), order=('ID',))[:limit]]
        return got, n

    # ---------------------------------------------------------------- 层
    def _build_levels(self) -> None:
        floors = self.rows('pkpmFloor',
                           ('ID', 'No_', 'Name', 'StdFlrID', 'LevelB', 'Height'),
                           order=('LevelB', 'ID'))
        stdflr = self.rows('pkpmStdFlr', ('ID', 'No_', 'Height'), order=('ID',))
        std_ids = {_int(r[0]) for r in stdflr}
        std_h = {_int(r[0]): _num(r[2]) for r in stdflr}
        self._stdflr_h_nonzero = sorted(k for k, v in std_h.items()
                                        if k in {_int(r[3]) for r in floors}
                                        and abs(v) > TOL)

        seen: Dict[int, int] = {}
        for fid, no, name, sid, levelb, height in floors:
            z_bot = _num(levelb, bad=self.st.bad_num)
            h = _num(height, bad=self.st.bad_num)
            key = _int(sid)
            seen[key] = seen.get(key, 0) + 1
            self.model.levels.append(
                Level(stdflr_id=key, floor_id=_int(fid), no=_int(no),
                      z_bot=z_bot, z_top=z_bot + h, height=h,
                      name=_text(name)))
        self.lvm = self.model.level_map()

        # 事实核对（写 notes，不阻断；契约 §a.3）
        if not floors:
            self.notes.append("异常：pkpmFloor 缺失或为空 ⇒ Model 无 Level（契约 §b.2 视为空）")
        if stdflr and self._stdflr_h_nonzero:
            self.notes.append(
                "注意：pkpmStdFlr.Height 在本文件非全 0（%s 层非 0，如 %s）；按契约 §a.3 "
                "**仍以 pkpmFloor.LevelB/Height 为准**，未使用 pkpmStdFlr.Height"
                % (len(self._stdflr_h_nonzero),
                   sorted('%s=%g' % (k, std_h[k]) for k in self._stdflr_h_nonzero)[:3]))
        dup = {k: v for k, v in seen.items() if v > 1}
        if dup:
            self.notes.append(
                "异常：%d 个标准层被多个自然层共用（StdFlrID=%s）——契约 §a.2 用 "
                "stdflr_id 作 Level 唯一键，无法表达 n:1，validate() 将报 E-LEVEL-DUP；"
                "jwd_format.md §5 要求按自然层各复制一份构件" % (len(dup), sorted(dup)))
        miss = sorted(seen.keys() - std_ids) if std_ids else sorted(seen.keys())
        if std_ids and miss:
            self.notes.append("异常：pkpmFloor.StdFlrID=%s 在 pkpmStdFlr 里不存在" % (miss,))

    # ---------------------------------------------------------------- 节点
    def _build_joints(self) -> None:
        bad_lv = 0
        for jid, no, sid, x, y, hd in self.rows(
                'pkpmJoint', ('ID', 'No_', 'StdFlrID', 'X', 'Y', 'HDiff'),
                order=('ID',)):
            key = _int(sid)
            lv = self.lvm.get(key)
            if lv is None:
                bad_lv += 1
            hdiff = _num(hd, bad=self.st.bad_num)
            z = (lv.z_top if lv is not None else 0.0) + hdiff
            self.model.joints[_int(jid)] = Joint(
                id=_int(jid), level=key, x=_num(x, bad=self.st.bad_num),
                y=_num(y, bad=self.st.bad_num), z=z, no=_int(no), hdiff=hdiff)
        if bad_lv:
            self.notes.append("异常：%d 个 pkpmJoint.StdFlrID 指向不存在的层"
                              "（validate() 将报 E-JOINT-LEVEL；其 z 按层顶=0 计算）" % bad_lv)

    # ---------------------------------------------------------------- 截面
    def _build_sections(self) -> None:
        n_bad_tail = 0
        n_empty_sv = 0
        n_undecoded = 0
        for table, tag in (('pkpmBeamSect', 'beam'), ('pkpmColSect', 'col'),
                           ('pkpmBraceSect', 'brace')):
            for sid, no, name, mat, kind, sv in self.rows(
                    table, ('ID', 'No_', 'Name', 'Mat', 'Kind', 'ShapeVal'),
                    order=('ID',)):
                sid_i = _int(sid)
                k = _int(kind)
                toks = _split_shapeval(sv)
                # 契约 §a.4：先去掉首字段(Kind)与尾部 (Mat, 自身ID)
                params = toks[1:-2] if len(toks) >= 3 else []
                # jwd_format.md §3.1 的尾部自检（28/28 成立；失败只记 note，不阻断）
                if not toks:
                    n_empty_sv += 1
                elif len(toks) < 3 or _int(toks[-1], -1) != sid_i:
                    n_bad_tail += 1
                note = _KIND_NOTE.get(k, '')
                if kind_known(k):
                    dims, extra = decode_dims(k, params)
                else:
                    dims, extra = {}, ''
                    n_undecoded += 1
                    note = ("Kind=%d 未解码（known=False）：字段布局无证据"
                            "（jwd_format.md §3.2 只覆盖 1/2/3/26/303），dims 留空、"
                            "禁止猜测" % k)
                if not dims and kind_known(k):
                    extra += "；参数体仅 %d 项，不足该 Kind 的最小解码长度，dims 留空" % len(params)
                if len(toks) >= 3 and _int(toks[-1], -1) != sid_i:
                    extra += ("；⚠ ShapeVal 尾部与本行 ID 不符（末字段=%r，本行 ID=%d）"
                              "（jwd_format.md §3.1 称 28/28 成立）" % (toks[-1], sid_i))
                self.sec_mat[sid_i] = _int(mat)
                self.model.sections[sid_i] = Section(
                    id=sid_i, kind=k, mat=_int(mat), name=_text(name), dims=dims,
                    table=tag, no=_int(no), shapeval=_text(sv), params=params,
                    note=note + extra)
        if n_bad_tail:
            self.notes.append("异常：%d 个截面的 ShapeVal 尾部 (Mat, 自身ID) 自检不通过"
                              "（jwd_format.md §3.1 称 28/28 成立）" % n_bad_tail)
        if n_empty_sv:
            self.notes.append("异常：%d 个截面的 ShapeVal 为空（无法解码 dims）" % n_empty_sv)
        if n_undecoded:
            self.notes.append("未解码表 截面：%d 行的 Kind 不在已解码族 {1,2,3,26,303}，"
                              "dims 留空并标 known=False（契约 §a.4）" % n_undecoded)

    # ---------------------------------------------------------------- 网格线
    def _build_grids(self) -> None:
        for gid, sid, j1, j2 in self.rows('pkpmGrid', ('ID', 'StdFlrID', 'Jt1ID', 'Jt2ID'),
                                          order=('ID',)):
            self.grids[_int(gid)] = (_int(j1), _int(j2))

    # ---------------------------------------------------------------- 构件
    def _member(self, mid, mtype, sid, secid, start, end, rotation, ecc, no,
                grid_id=None, node_id=None, jydef='', h1=0.0, h2=0.0) -> Optional[Member]:
        key = _int(sid)
        if key not in self.lvm:
            self.notes.append("跳过 Member %d(%s)：StdFlrID=%s 无对应层"
                              % (_int(mid), mtype, sid))
            return None
        if _int(secid) not in self.model.sections:
            self.notes.append("异常：Member %d(%s) 的 SectID=%s 不在截面表"
                              "（validate() 将报 E-MEM-SEC）" % (_int(mid), mtype, secid))
        return Member(id=_int(mid), type=mtype, level=key, section=_int(secid),
                      start=start, end=end, rotation=rotation, ecc=ecc, no=_int(no),
                      grid_id=grid_id, node_id=node_id, jydef=_text(jydef),
                      hdiff_start=h1, hdiff_end=h2)

    def _build_members(self) -> None:
        self._build_grids()
        b = self.st.bad_num
        n_jhd = 0                     # 端点节点自带 HDiff 的构件（契约 §a.5 的公式不含它）
        # 柱：自层底竖直贯穿本层（契约 §a.5）
        for mid, no, sid, secid, jt, ex, ey, rot, hdb in self.rows(
                'pkpmColSeg',
                ('ID', 'No_', 'StdFlrID', 'SectID', 'JtID', 'EccX', 'EccY',
                 'Rotation', 'HDiffB'), order=('ID',)):
            lv = self.lvm.get(_int(sid))
            j = self.model.joints.get(_int(jt))
            if lv is None or j is None:
                self.notes.append("跳过 Member %d(column)：JtID=%s 或 StdFlrID=%s 不可解析"
                                  % (_int(mid), jt, sid))
                continue
            if abs(j.hdiff) > TOL:
                n_jhd += 1
            exf, eyf = _num(ex, bad=b), _num(ey, bad=b)
            h0 = _num(hdb, bad=b)
            x, y = j.x + exf, j.y + eyf
            m = self._member(mid, 'column', sid, secid, (x, y, lv.z_bot + h0),
                             (x, y, lv.z_top), _num(rot, bad=b), (exf, eyf), no,
                             None, _int(jt), '', h0, 0.0)
            if m is not None:
                self.model.members.append(m)

        # 梁：GridID -> pkpmGrid.Jt1ID/Jt2ID -> Joint.(x,y)（契约 §a.5）
        for mid, no, sid, secid, gid, ecc, h1, h2, rot, jy in self.rows(
                'pkpmBeamSeg',
                ('ID', 'No_', 'StdFlrID', 'SectID', 'GridID', 'Ecc', 'HDiff1',
                 'HDiff2', 'Rotation', 'JYDef'), order=('ID',)):
            lv = self.lvm.get(_int(sid))
            g = self.grids.get(_int(gid))
            a = self.model.joints.get(g[0]) if g else None
            c = self.model.joints.get(g[1]) if g else None
            if lv is None or a is None or c is None:
                self.notes.append("跳过 Member %d(beam)：GridID=%s 或其两端节点不可解析"
                                  % (_int(mid), gid))
                continue
            if abs(a.hdiff) > TOL or abs(c.hdiff) > TOL:
                n_jhd += 1
            h1f, h2f = _num(h1, bad=b), _num(h2, bad=b)
            m = self._member(mid, 'beam', sid, secid,
                             (a.x, a.y, lv.z_top + h1f), (c.x, c.y, lv.z_top + h2f),
                             _num(rot, bad=b), (_num(ecc, bad=b),), no,
                             _int(gid), None, jy, h1f, h2f)
            if m is not None:
                self.model.members.append(m)

        # 支撑：两端节点 + 两端偏心/高差（契约 §a.5）
        for (mid, no, sid, secid, j1, j2, ex1, ey1, h1, ex2, ey2, h2, rot) in self.rows(
                'pkpmBraceSeg',
                ('ID', 'No_', 'StdFlrID', 'SectID', 'Jt1ID', 'Jt2ID', 'EccX1', 'EccY1',
                 'HDiff1', 'EccX2', 'EccY2', 'HDiff2', 'Rotation'), order=('ID',)):
            lv = self.lvm.get(_int(sid))
            a = self.model.joints.get(_int(j1))
            c = self.model.joints.get(_int(j2))
            if lv is None or a is None or c is None:
                self.notes.append("跳过 Member %d(brace)：Jt1ID=%s/Jt2ID=%s 或 StdFlrID=%s "
                                  "不可解析" % (_int(mid), j1, j2, sid))
                continue
            if abs(a.hdiff) > TOL or abs(c.hdiff) > TOL:
                n_jhd += 1
            ex1f, ey1f = _num(ex1, bad=b), _num(ey1, bad=b)
            ex2f, ey2f = _num(ex2, bad=b), _num(ey2, bad=b)
            h1f, h2f = _num(h1, bad=b), _num(h2, bad=b)
            m = self._member(mid, 'brace', sid, secid,
                             (a.x + ex1f, a.y + ey1f, lv.z_top + h1f),
                             (c.x + ex2f, c.y + ey2f, lv.z_top + h2f),
                             _num(rot, bad=b), (ex1f, ey1f, ex2f, ey2f), no,
                             None, None, '', h1f, h2f)
            if m is not None:
                self.model.members.append(m)

        if n_jhd:
            self.notes.append(
                "异常：%d 根构件的端点节点带非零 HDiff（节点高差）——契约 §a.5 的梁/柱/支撑 "
                "Z 公式只含段表自己的 HDiff1/HDiff2/HDiffB，**不含** pkpmJoint.HDiff，"
                "故这些节点高差未并入构件几何（本样本 0 违例，此提示为他文件准备）" % n_jhd)

    # ---------------------------------------------------------------- 楼板
    def _build_slabs(self) -> None:
        b = self.st.bad_num
        n_hole = n_thick = n_zero = n_badpoly = n_vexz = n_neq = 0
        bad_poly_ids: List[int] = []
        vz_bad_ids: List[int] = []
        for (sid, no, sf, gids, vx, vy, vz, hole, th, dead, live) in self.rows(
                'pkpmSlab',
                ('ID', 'No_', 'StdFlrID', 'GridsID', 'VertexX', 'VertexY', 'VertexZ',
                 'RoomIsHole', 'Thickness', 'dead', 'live'), order=('ID',)):
            lv = self.lvm.get(_int(sf))
            if lv is None:
                self.notes.append("跳过 Slab %d：StdFlrID=%s 不可解析" % (_int(sid), sf))
                continue
            xs = _floats(vx, self.st.bad_xy)
            ys = _floats(vy, self.st.bad_xy)
            if len(xs) != len(ys) or len(xs) < 3:
                n_badpoly += 1
                bad_poly_ids.append(_int(sid))
            poly = [(xs[i], ys[i]) for i in range(min(len(xs), len(ys)))]
            # 契约 §a.3/§a.5：板面 = 层顶；等价于 LevelB + pkpmSlab.VertexZ（实测相等）
            zs = _floats(vz, self.st.bad_xy)
            if zs and any(abs(z - lv.height) > TOL for z in zs):
                n_vexz += 1
                vz_bad_ids.append(_int(sid))
            is_hole = _int(hole) == 1
            n_hole += 1 if is_hole else 0
            t = _num(th, bad=b)
            if t:
                n_thick += 1
            elif not is_hole:
                n_zero += 1
            if _int(hole) not in (0, 1):
                n_neq += 1
            self.model.slabs.append(Slab(
                id=_int(sid), level=_int(sf), polygon=poly, z=lv.z_top, thickness=t,
                is_hole=is_hole, dead=_num(dead, bad=b), live=_num(live, bad=b),
                grid_edges=_ints(gids), no=_int(no),
                spec_path='', ori=PANE_ORI, sjus=PANE_SJUS))
        self._slab_stats = (n_hole, n_thick, n_zero)
        if n_badpoly:
            self.notes.append("异常：%d 个 pkpmSlab 的多边形顶点数 <3 或 X/Y 个数不等"
                              "（如 ID=%s；validate() 将报 E-SLAB-POLY）"
                              % (n_badpoly, bad_poly_ids[:5]))
        if n_vexz:
            self.notes.append("异常：%d 个 pkpmSlab 的 VertexZ 与所在层层高不符"
                              "（如 ID=%s）——按契约 §a.5 仍取 Slab.z = level.z_top"
                              % (n_vexz, vz_bad_ids[:5]))
        if n_neq:
            self.notes.append("异常：%d 个 pkpmSlab 的 RoomIsHole 不在 {0,1}" % n_neq)

    # ---------------------------------------------------------------- 荷载
    def _build_loads(self) -> None:
        for lsid, _no, lname, ek, sv in self.rows(
                'pkpmLoadSect', ('ID', 'No', 'Loadname', 'ElementKind', 'ShapeVal'),
                order=('ID',)):
            self.load_sects[_int(lsid)] = (_int(ek), _text(sv))

        n_other = 0
        other_eks: List[int] = []
        n_nosect = 0
        n_badtarget = 0
        load_sfs: set = set()
        member_ids = {m.id for m in self.model.members}
        for (lid, no, secid, ty, eid, _p1, _npc, _px, _py, _pz, sf) in self.rows(
                'pkpmLoadSeg',
                ('ID', 'No', 'SectID', 'Type', 'ElementID', 'strParas1', 'nPtCnt',
                 'strParasX', 'strParasY', 'strParasZ', 'StdFlrID'), order=('ID',)):
            ek, sv = self.load_sects.get(_int(secid), (None, ''))
            if ek == 12:
                kind = 'beam-line'
            elif ek == -1:
                kind = 'joint-point'
            else:
                kind = ''
                n_other += 1
                other_eks.append(_int(ek))
                if _int(secid) not in self.load_sects:
                    n_nosect += 1
            raw = _split_shapeval(sv)
            vals: List[Optional[float]] = []
            for t in raw:
                try:
                    vals.append(float(t))
                except ValueError:
                    vals.append(None)
            tgt = _int(eid)
            if kind == 'beam-line' and tgt not in member_ids:
                n_badtarget += 1
            elif kind == 'joint-point' and tgt not in self.model.joints:
                n_badtarget += 1
            self.model.loads.append(Load(
                id=_int(lid), kind=kind, target_id=tgt, values=tuple(vals), raw=raw,
                load_sect_id=_int(secid), level=_int(sf)))
            load_sfs.add(_int(sf))
        self._load_sfs = sorted(load_sfs)
        if n_other:
            self.notes.append("异常：%d 条 pkpmLoadSeg 的 pkpmLoadSect.ElementKind 既非 12 "
                              "也非 -1（实测值 %s）——契约 §a.5 只定义这两种分流，"
                              "kind 置空串并交由 E-LOAD-KIND 报出"
                              % (n_other, sorted(set(other_eks))))
        if n_nosect:
            self.notes.append("异常：%d 条 pkpmLoadSeg.SectID 不在 pkpmLoadSect" % n_nosect)
        if n_badtarget:
            self.notes.append("异常：%d 条荷载的 ElementID 在其分流目标表里不存在"
                              "（validate() 将报 E-LOAD-TARGET）" % n_badtarget)

    # ---------------------------------------------------------------- 材料
    def _apply_materials(self) -> None:
        """契约 §b.2 的可选充实：``pkpmProperty`` 的 HNTDJ/GANGH -> ``Member.material``。

        证据：jwd_format.md §1.5/§7.1 —— ``*Sect.Mat`` 是材料大类（**5=钢 / 6=混凝土**），
        而 HNTDJ（混凝土强度等级）在样本里对**全部** 811 根构件（含 283 根钢梁、48 根钢柱、
        13 根钢支撑）都写 ``30.00``。若不分材料大类一律套 ``'C30'``，会把钢构件说成混凝土，
        故本实现按 ``Section.mat`` 分流：钢（5）只看 GANGH，混凝土/未知（6/0）只看 HNTDJ；
        两者的值 ≤ 0 时都不填（契约 §b.2 的"未指定时不填"）。
        """
        for pid, pname, ptype, pval in self.rows(
                'pkpmProperty', ('ID', 'Name', 'Type', 'ShapeVal'), order=('ID',)):
            nm = _text(pname)
            if nm not in ('HNTDJ', 'GANGH'):
                continue
            self.props.setdefault(nm, {})[_int(pid)] = _num(pval)
        n_c = n_q = 0
        for m in self.model.members:
            mat = self.sec_mat.get(m.section, 0)
            if mat == 5:                                   # 钢：GANGH -> Q<号>
                v = self.props.get('GANGH', {}).get(m.id, 0.0)
                if v > 0:
                    m.material = 'Q%d' % int(v)
                    n_q += 1
            else:                                          # 混凝土 / 未知：HNTDJ -> C<等级>
                v = self.props.get('HNTDJ', {}).get(m.id, 0.0)
                if v > 0:
                    m.material = 'C%d' % int(v)
                    n_c += 1
        self._mat_stats = (n_c, n_q)
        if self.props:
            steel = sum(1 for m in self.model.members
                        if self.sec_mat.get(m.section, 0) == 5)
            if self.props.get('HNTDJ') and steel:
                self.notes.append(
                    "材料：HNTDJ（混凝土强度等级）在本文件覆盖全部 %d 根构件（含 %d 根钢构件，"
                    "Section.Mat=5），按材料大类分流后只对混凝土构件写 material='C<等级>'；"
                    "钢构件的材料号在本文件 GANGH 全 0（未指定）⇒ material 留空"
                    "（契约 §b.2；jwd_format.md §1.5/§7.1）"
                    % (len(self.model.members), steel))

    # ------------------------------------------------------------ 未解码表
    def _scan_leftover_tables(self) -> None:
        consumed = set(CONSUMED_TABLES)
        und = [t for t in UNDECODED_OBJECT_TABLES if t not in consumed]
        nof = [t for t in NO_MODEL_FIELD_TABLES if t not in consumed]

        for t in und:
            got, n = self.ids(t)
            if not n:
                continue
            more = '' if n <= len(got) else '…（其余 %d 行省略）' % (n - len(got))
            self.notes.append(
                "未解码表 %s：%d 行，ID=%s%s；字段语义未解（jwd_format.md §1.7），"
                "本次未转换、未臆造几何（契约 §a.8/§b.2、§12#14）"
                % (t, n, got, more))
        for t in nof:
            n = self.count(t)
            if not n:
                continue
            why = {
                "pkpmAxis": "轴线（Name 全空，jwd_format.md §1.2）；规范模型无轴网字段",
                "pkpmSlabHole": "板洞索引记录；洞的几何已在 RoomIsHole=1 的 pkpmSlab 行里，"
                                "重复建洞会多出 29 个对象（jwd_format.md §1.4）",
                "pkpmStdFlrPara": "标准层设计参数（§7.3），与几何无关",
                "pkpmSatTower": "塔吊/场地范围（§7.4），与结构几何无关",
                "pkpmSatTowPara": "塔吊基础参数（§7.4）",
                "pkpmSatTowReinInfo": "塔吊配筋信息（§7.4）",
            }.get(t, "规范模型无对应字段")
            self.notes.append("未解码表 %s：%d 行，本次未转换（%s）" % (t, n, why))

        empty = sorted(t for t in (UNDECODED_OBJECT_TABLES + NO_MODEL_FIELD_TABLES)
                       if t not in consumed and self.count(t) == 0)
        if empty:
            self.notes.append("其余 %d 张未解码表为空或不存在（%s…）：本文件不含墙/楼梯/次梁/"
                              "吊车/阻尼器/悬挑板/柱帽/装配式等对象（jwd_format.md §1.7/§9.2#1）"
                              % (len(empty), '、'.join(empty[:6])))

    # ------------------------------------------------------------- 基础说明
    def _base_notes(self) -> None:
        n_hole, n_thick, n_zero = getattr(self, '_slab_stats', (0, 0, 0))
        n_c, n_q = getattr(self, '_mat_stats', (0, 0))
        self.notes.extend([
            "层标高取自 pkpmFloor.LevelB/Height（z_top = LevelB + Height；标准层平面画在层顶）；"
            "按契约 §a.3 未使用 pkpmStdFlr.Height（本样本该列恒 0，jwd_format.md §4.3/§9.4）",
            "构件 Z 公式（契约 §a.5）：柱 = 层底+HDiffB → 层顶；梁/支撑 = 层顶 + 端高差；"
            "板 z = 层顶",
            "楼板：%d 个多边形（含 %d 个 RoomIsHole=1 的洞）；有厚度（非洞）%d 个；"
            "非洞但 Thickness=0 的 %d 个是 PKPM 的'房间未建板'，已按原值 0 保留，"
            "下游不得据此生成实体板（jwd_format.md §1.4/§9.2#2）"
            % (len(self.model.slabs), n_hole, n_thick, n_zero),
            "荷载：ElementKind 12→beam-line、-1→joint-point（契约 §a.5）；"
            "Load.level 取 pkpmLoadSeg.StdFlrID（本文件该列取值 %s）；"
            "荷载数值语义（类型码 1/2/3、kN vs kN/m）未证实（jwd_format.md §1.6/§9.3#8），"
            "只做原样搬运" % (getattr(self, '_load_sfs', []) or '（无荷载行）',),
            "文本列逐值解码 ASCII→UTF-8→GBK（契约 §b.2）；本文件出现 U+FFFD 替换字符 %d 个"
            % self.st.text_replaced,
        ])
        if self.st.bad_num or self.st.bad_xy:
            self.notes.append("异常：数值/TEXT 数值列共 %d 处无法解析（如 %s），已按 0/跳过处理"
                              % (len(self.st.bad_num) + len(self.st.bad_xy),
                                 (self.st.bad_num + self.st.bad_xy)[:5]))
        if n_q:
            self.notes.append("材料：%d 根构件取 HNTDJ→'C<等级>'，%d 根取 GANGH→'Q<号>'"
                              % (n_c, n_q))
        elif n_c:
            self.notes.append("材料：%d 根构件取 HNTDJ→'C<等级>'；GANGH 在本文件全 0"
                              "（未指定）⇒ 钢构件的 material 留空" % n_c)
        # 未使用截面（jwd_format.md §9.2#9）
        used = {m.section for m in self.model.members}
        unused = sorted(set(self.model.sections) - used)
        if unused:
            self.notes.append("未使用截面 %d 个（ID=%s）：几何无影响，保留 ID 映射供导出用"
                              "（jwd_format.md §9.2#9）" % (len(unused), unused))
        # 非零偏心（契约 §a.2：方向未证实，必须能进报告）
        ne = [m for m in self.model.members
              if any(abs(v) > TOL for v in m.ecc)]
        if ne:
            vals: Dict[float, int] = {}
            for m in ne:
                for v in m.ecc:
                    if abs(v) > TOL:
                        vals[v] = vals.get(v, 0) + 1
            self.notes.append(
                "非零偏心构件 %d 根（梁 Ecc / 柱 EccX,EccY / 支撑两端）：分量取值 %s；"
                "正负方向未证实（jwd_format.md §9.3#6 / 契约 §12#6），"
                "几何按原值相加，逐条明细由 CLI 从 Member.ecc 生成"
                % (len(ne), sorted('%g×%d' % (k, v) for k, v in vals.items())))
        # 工程名候选（契约 §b.2；notes 是唯一回流通道）
        for sid, pv in self.rows('pkpmSysInfo', ('ID', 'ParaVal'), order=('ID',)):
            if _int(sid) == 2 and isinstance(pv, str) and pv.strip():
                self.notes.append("工程名候选 PROJECT_NAME=%s（pkpmSysInfo.ID=2；"
                                  "契约 §b.2 / jwd_format.md §7.2，供 CLI --project 缺省值）"
                                  % pv.strip())
                break

    # ---------------------------------------------------------------- 总装
    def assemble(self) -> Model:
        missing = [t for t in CONSUMED_TABLES if not self.exists(t)]
        if missing:
            self.notes.append("异常：%d 张被消费的表不存在（视为空，契约 §b.2）：%s"
                              % (len(missing), '、'.join(missing)))
        self._build_levels()
        self._build_joints()
        self._build_sections()
        self._build_members()
        self._build_slabs()
        self._build_loads()
        self._apply_materials()
        self._scan_leftover_tables()
        self._base_notes()
        self.model.notes = self.notes
        return self.model


# --------------------------------------------------------------------------
# 契约 §b.1 的唯一入口
# --------------------------------------------------------------------------


def read_jwd(path: str) -> Model:
    """把 ``.jwd``（SQLite3）读成规范模型（**只读**，不写任何文件）。

    :param path: ``.jwd`` 路径（Windows 反斜杠会被转成正斜杠进 URI）
    :raises FileNotFoundError: 输入文件不存在
    :raises sqlite3.Error: 不是 SQLite 库 / 无法以只读方式打开
    """
    if not os.path.isfile(path):
        raise FileNotFoundError("JWD 文件不存在：%s" % (path,))
    stats = _Stats()
    con = sqlite3.connect(_ro_uri(path), uri=True)
    try:
        con.text_factory = stats.factory
        return _Reader(con, os.path.abspath(path), stats).assemble()
    finally:
        con.close()
