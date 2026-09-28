# -*- coding: utf-8 -*-
"""PKPM2PDMS导入导出 —— 规范模型（唯一契约的数据结构）。

契约版本：CONTRACT_VERSION = "1.0"；条文见 ``spec/CONTRACT.md`` §a。

**注意区分两个版本号**：``CONTRACT_VERSION`` 是**规范模型 schema 版本**（出现在
``.jwd``/``report.json`` 的 ``contract_version`` 字段里，被契约与多个测试引用），
本版（插件 v2.1.0）**不动它，恒为 "1.0"**；插件的发行版本是 **v2.1.0**（见
``docs/使用说明.md`` §0 与 ``engine/README.txt``）。两者是两回事，不要互相推导。

单位与坐标系（全项目统一，模块之间**不得**再做换算）::

    * 长度  mm ；角度  度 ；荷载  kN / kN/m / kN/m² ；面荷载 kN/m²
    * X = E(east) ；Y = N(north) ；Z = U(up)    右手系，Z 向上
    * 平面坐标 (x, y) 与 PDMS 的 (E, N) 一一对应；Z 与 U 一一对应

设计约定（与 jwd_format.md §8 的差异只在"引用方式"与"补充字段"，均已在契约中逐条写明）::

    * Level      —— 楼层/标高平面；``stdflr_id`` 是它的唯一键（int）。
    * Joint.level / Member.level / Slab.level / Wall.level
                 —— 存 ``Level.stdflr_id``（int），不再内嵌 Level 对象；
                    取 Level 对象用 ``Model.level(key)``。理由：JSON 往返与 5 个实施包
                    之间的比较需要一个稳定、可排序的键（见 CONTRACT §a.2）。
    * 所有 ``*_start`` / ``*_end`` / ``ecc`` 之类的字段都是**原始出处值**，
      仅供报表与写回 .jwd 使用；几何真值一律看 ``start`` / ``end`` / ``polygon`` /
      ``loop``（它们已把偏心、高差全部并入）。

本文件只依赖标准库；禁止引入任何第三方包。
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

#: 规范模型 **schema** 版本（**不是**插件版本；插件版本见 docs/使用说明.md §0）。
#: 本常量被 spec/CONTRACT.md 与多个测试引用，插件 v2.1.0 里**保持 "1.0" 不变**。
CONTRACT_VERSION = "1.0"

# --------------------------------------------------------------------------
# 契约常量（模块必须引用这里的值，不得各自硬编码）
# --------------------------------------------------------------------------

TOL = 1e-6            # 长度/标高比较容差（mm）
ANGLE_TOL = 1e-9      # 角度比较容差（度）
Z_SLACK_MM = 10.0     # 构件端点超出所属层区间多少 mm 才算"可疑"（报告阈值）
SHORT_MEMBER_MM = 300.0   # 短于该长度的构件进"几何异常"报告（报告阈值）

MEMBER_TYPES = ("beam", "column", "brace")
MEMBER_TYPE_CN = {"beam": "梁", "column": "柱", "brace": "支撑"}

SECTION_TABLES = ("beam", "col", "brace", "pdt", "dump", "panel")

RESOLVED = "resolved"
PARAMETRIC = "parametric"
INFERRED = "inferred"          # 契约 §e.1a/§e.3/§0.4-1：有证据的族别判定（不是原件里写明的映射）
UNRESOLVED = "unresolved"
RESOLUTION_STATUS = (RESOLVED, PARAMETRIC, INFERRED, UNRESOLVED)

LOAD_KINDS = ("beam-line", "joint-point")

#: 板的 DUMP/宏 约定：PANE 的 ORI 与 SJUS（出处见 CONTRACT §c 引用的 StlGrating.pmlfrm:46/48）
PANE_ORI = "YNZU"        # == PDMS 的 ``ORI Y IS N AND Z IS U``
PANE_SJUS = "dbot"
WALL_DEFAULT_SJUS = "na"  # 墙不写 SJUS 时用 na（不适用）


def _f(x: Any, default: float = 0.0) -> float:
    """把任意标量安全转成 float（None / '' -> default）。"""
    if x is None:
        return default
    if isinstance(x, bool):
        return float(int(x))
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if not s:
        return default
    return float(s)


def _vec3(v: Any) -> Tuple[float, float, float]:
    if v is None:
        return (0.0, 0.0, 0.0)
    if len(v) != 3:
        raise ValueError("需要 3 个分量，收到 %r" % (v,))
    return (_f(v[0]), _f(v[1]), _f(v[2]))


def _vec2(v: Any) -> Tuple[float, float]:
    if v is None:
        return (0.0, 0.0)
    if len(v) != 2:
        raise ValueError("需要 2 个分量，收到 %r" % (v,))
    return (_f(v[0]), _f(v[1]))


def dist3(a, b) -> float:
    return math.sqrt(sum((_f(a[i]) - _f(b[i])) ** 2 for i in range(3)))


# --------------------------------------------------------------------------
# 数据类
# --------------------------------------------------------------------------


@dataclass
class Level:
    """楼层 / 标高平面。

    两种形态（同一数据类，用 ``height`` 区分，见 CONTRACT §a.2）::

        * 楼层型（.jwd）：z_bot = pkpmFloor.LevelB，z_top = LevelB + Height，
          height > 0；标准层平面画在 **层顶 z_top**。
        * 平面型（.pdt / .pdmsdump 推导）：z_bot == z_top == 该标高，height == 0。
    """

    stdflr_id: int                    # 唯一键（.jwd: pkpmStdFlr.ID）
    floor_id: int                     # .jwd: pkpmFloor.ID；平面型填 0
    no: int                           # 层号（.jwd: pkpmFloor.No_，1 起）
    z_bot: float                      # 层底绝对标高 mm
    z_top: float                      # 层顶绝对标高 mm（= 该层平面所在标高）
    height: float                     # 层高 mm（= z_top - z_bot）
    name: str = ""                    # .jwd: pkpmFloor.Name（样本为空）

    @property
    def key(self) -> int:
        return self.stdflr_id

    @property
    def is_plane(self) -> bool:
        return abs(self.height) <= TOL

    def contains_z(self, z: float, slack: float = 0.0) -> bool:
        return (self.z_bot - slack) <= z <= (self.z_top + slack)

    def to_dict(self) -> Dict[str, Any]:
        return {"stdflr_id": self.stdflr_id, "floor_id": self.floor_id, "no": self.no,
                "z_bot": self.z_bot, "z_top": self.z_top, "height": self.height,
                "name": self.name}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Level":
        return cls(stdflr_id=int(d["stdflr_id"]), floor_id=int(d.get("floor_id", 0)),
                   no=int(d.get("no", 0)), z_bot=_f(d["z_bot"]), z_top=_f(d["z_top"]),
                   height=_f(d.get("height", _f(d["z_top"]) - _f(d["z_bot"]))),
                   name=str(d.get("name", "")))


@dataclass
class Joint:
    """节点。``z = level.z_top + hdiff``（hdiff 为原始 HDiff，mm，可为负）。"""

    id: int
    level: int                        # Level.stdflr_id
    x: float
    y: float
    z: float
    no: int = 0                       # .jwd: pkpmJoint.No_（层内编号）
    hdiff: float = 0.0                # .jwd: pkpmJoint.HDiff（相对层顶，mm）

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "level": self.level, "x": self.x, "y": self.y,
                "z": self.z, "no": self.no, "hdiff": self.hdiff}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Joint":
        return cls(id=int(d["id"]), level=int(d["level"]), x=_f(d["x"]), y=_f(d["y"]),
                   z=_f(d["z"]), no=int(d.get("no", 0)), hdiff=_f(d.get("hdiff", 0.0)))


@dataclass
class Section:
    """截面定义。

    ``dims`` 的键由本契约规定（CONTRACT §a.4），只写**有证据**的键；
    证据不足的字段名一律带进 ``note``，禁止把推断当事实。
    """

    id: int
    kind: int                         # .jwd: *Sect.Kind；.pdt: $DEFFRAMESECTION.KIND
    mat: int                          # 5=钢 6=混凝土（.jwd *Sect.Mat；.pdt 由材料表折算）
    name: str = ""                    # 型钢库名称 / "矩750X750" / "薄壁方钢管: B25"
    dims: Dict[str, Any] = field(default_factory=dict)
    table: str = ""                   # 'beam'|'col'|'brace'|'pdt'|'dump'|'panel'
    no: int = 0
    shapeval: str = ""                # .jwd 原始 ShapeVal 文本（写回用）
    params: List[str] = field(default_factory=list)  # 参数体原文（已去掉尾部 Mat,ID）
    note: str = ""                    # 证据等级 / 不确定项

    @classmethod
    def for_panel(cls, kind: str, thickness: float, name: str = "") -> "Section":
        """为板/墙合成一个 Section（供 ``SectionMap.resolve(sec, 'slab'|'wall')`` 使用）。

        ``name`` 缺省为 ``T<厚度>``（与 .pdt ``$DEFWASLABSECTION.NAME`` 同构，
        见 pdt_format.md §2.7）。
        """
        t = _f(thickness)
        return cls(id=-1, kind=0, mat=6, name=name or ("T%g" % t),
                   dims={"T": t}, table="panel", no=0, shapeval="", params=[],
                   note="板/墙合成截面（厚度 -> PKPM 名 T<厚度>，见 pdt_format.md §2.7）")

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "kind": self.kind, "mat": self.mat, "name": self.name,
                "dims": dict(self.dims), "table": self.table, "no": self.no,
                "shapeval": self.shapeval, "params": list(self.params),
                "note": self.note}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Section":
        return cls(id=int(d["id"]), kind=int(d.get("kind", 0)), mat=int(d.get("mat", 0)),
                   name=str(d.get("name", "")), dims=dict(d.get("dims") or {}),
                   table=str(d.get("table", "")), no=int(d.get("no", 0)),
                   shapeval=str(d.get("shapeval", "")),
                   params=list(d.get("params") or []), note=str(d.get("note", "")))


@dataclass
class Member:
    """线性构件（梁 / 柱 / 支撑）。``start`` / ``end`` 是**最终几何**（已并入偏心与高差）。

    偏心布局（``ecc``，仅记录原始值）::

        beam   : (Ecc,)                     —— 沿梁的横向偏移（方向约定未证实，见 §9.3#6）
        column : (EccX, EccY)
        brace  : (EccX1, EccY1, EccX2, EccY2)
    """

    id: int
    type: str                         # 'beam' | 'column' | 'brace'
    level: int                        # Level.stdflr_id（start 端所在层）
    section: int                      # Section.id
    start: Tuple[float, float, float]
    end: Tuple[float, float, float]
    rotation: float = 0.0             # 度，绕构件自身轴（.jwd Rotation / PDMS BANG）
    ecc: Tuple[float, ...] = ()
    no: int = 0
    grid_id: Optional[int] = None     # .jwd: pkpmBeamSeg.GridID
    node_id: Optional[int] = None     # .jwd: pkpmColSeg.JtID
    jydef: str = ""                   # .jwd: pkpmBeamSeg.JYDef 原文
    hdiff_start: float = 0.0          # 原始高差：柱取 HDiffB，梁/支撑取 HDiff1
    hdiff_end: float = 0.0            # 原始高差：梁/支撑取 HDiff2，柱取 0
    material: str = ""                # 'C30' / 'Q235' / ...（可选，来自 property / 材料表）
    jusl: str = ""                    # PDMS 卡点（可选，往返保真用）
    meml: str = ""

    @property
    def length(self) -> float:
        return dist3(self.start, self.end)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "type": self.type, "level": self.level,
                "section": self.section, "start": list(self.start),
                "end": list(self.end), "rotation": self.rotation,
                "ecc": list(self.ecc), "no": self.no, "grid_id": self.grid_id,
                "node_id": self.node_id, "jydef": self.jydef,
                "hdiff_start": self.hdiff_start, "hdiff_end": self.hdiff_end,
                "material": self.material, "jusl": self.jusl, "meml": self.meml}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Member":
        return cls(id=int(d["id"]), type=str(d["type"]), level=int(d["level"]),
                   section=int(d["section"]), start=_vec3(d["start"]),
                   end=_vec3(d["end"]), rotation=_f(d.get("rotation", 0.0)),
                   ecc=tuple(_f(v) for v in (d.get("ecc") or ())),
                   no=int(d.get("no", 0)),
                   grid_id=None if d.get("grid_id") is None else int(d["grid_id"]),
                   node_id=None if d.get("node_id") is None else int(d["node_id"]),
                   jydef=str(d.get("jydef", "")),
                   hdiff_start=_f(d.get("hdiff_start", 0.0)),
                   hdiff_end=_f(d.get("hdiff_end", 0.0)),
                   material=str(d.get("material", "")), jusl=str(d.get("jusl", "")),
                   meml=str(d.get("meml", "")))


@dataclass
class Slab:
    """楼板 / 板洞（.jwd: pkpmSlab；.pdt/.pdmsdump: 水平面板）。

    ``polygon`` **不闭合**（首尾不重复），单位 mm；``z`` 为板面标高。
    """

    id: int
    level: int                        # Level.stdflr_id
    polygon: List[Tuple[float, float]] = field(default_factory=list)
    z: float = 0.0
    thickness: float = 0.0            # mm；0 = 未建板（.jwd 语义）
    is_hole: bool = False             # .jwd: pkpmSlab.RoomIsHole == 1
    dead: float = 0.0                 # 恒载 kN/m²
    live: float = 0.0                 # 活载 kN/m²
    grid_edges: List[int] = field(default_factory=list)   # .jwd: pkpmSlab.GridsID 有序
    no: int = 0
    spec_path: str = ""               # 板规格（PDMS SPREF，来自 SectionMap）
    ori: str = PANE_ORI               # PANE 的 ORI 码
    sjus: str = PANE_SJUS             # PLOOP 的 SJUS 码

    @property
    def area(self) -> float:
        """多边形面积（mm²，取绝对值；顶点顺序未规范化，符号不可用）。"""
        pts = self.polygon
        if len(pts) < 3:
            return 0.0
        a = 0.0
        n = len(pts)
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            a += x1 * y2 - x2 * y1
        return abs(a) / 2.0

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "level": self.level,
                "polygon": [list(p) for p in self.polygon], "z": self.z,
                "thickness": self.thickness, "is_hole": self.is_hole,
                "dead": self.dead, "live": self.live,
                "grid_edges": list(self.grid_edges), "no": self.no,
                "spec_path": self.spec_path, "ori": self.ori, "sjus": self.sjus}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Slab":
        return cls(id=int(d["id"]), level=int(d["level"]),
                   polygon=[_vec2(p) for p in (d.get("polygon") or [])],
                   z=_f(d.get("z", 0.0)), thickness=_f(d.get("thickness", 0.0)),
                   is_hole=bool(d.get("is_hole", False)), dead=_f(d.get("dead", 0.0)),
                   live=_f(d.get("live", 0.0)),
                   grid_edges=[int(v) for v in (d.get("grid_edges") or [])],
                   no=int(d.get("no", 0)), spec_path=str(d.get("spec_path", "")),
                   ori=str(d.get("ori", PANE_ORI)), sjus=str(d.get("sjus", PANE_SJUS)))


@dataclass
class Wall:
    """墙（PDMS STWALL）。

    .. note::
       jwd_format.md §8 未列出此类；本契约新增它，因为 (d)(e) 要求 PDMS 侧建 STWALL，
       而 .pdt 有 4 面墙、.jwd 有 ``pkpmWallSeg``（样本为空，语义**未解码**）。
       v1.0 规定：``read_jwd`` **不得**从 ``pkpmWallSeg`` 臆造墙——遇到非空行必须
       记入报告（status=unresolved / skipped），见 CONTRACT §a.9。
    """

    id: int
    level: int
    thickness: float = 0.0
    z_bot: float = 0.0
    z_top: float = 0.0
    loop: List[Tuple[float, float, float]] = field(default_factory=list)
    section: int = -1
    no: int = 0
    name: str = ""
    spec_path: str = ""               # PDMS SPRE
    sjus: str = WALL_DEFAULT_SJUS

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "level": self.level, "thickness": self.thickness,
                "z_bot": self.z_bot, "z_top": self.z_top,
                "loop": [list(p) for p in self.loop], "section": self.section,
                "no": self.no, "name": self.name, "spec_path": self.spec_path,
                "sjus": self.sjus}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Wall":
        return cls(id=int(d["id"]), level=int(d["level"]),
                   thickness=_f(d.get("thickness", 0.0)),
                   z_bot=_f(d.get("z_bot", 0.0)), z_top=_f(d.get("z_top", 0.0)),
                   loop=[_vec3(p) for p in (d.get("loop") or [])],
                   section=int(d.get("section", -1)), no=int(d.get("no", 0)),
                   name=str(d.get("name", "")), spec_path=str(d.get("spec_path", "")),
                   sjus=str(d.get("sjus", WALL_DEFAULT_SJUS)))


@dataclass
class Load:
    """荷载（.jwd: pkpmLoadSect + pkpmLoadSeg）。

    ``values`` 是 ``ShapeVal`` 的逐字段数值，**无法解析为 float 的字段为 None**；
    ``raw`` 是同一位置的原始字段串，两者**等长**。
    字段语义（类型码 1/2/3、单位 kN vs kN/m）在 jwd_format.md §1.6 中标注为未证实。
    """

    id: int
    kind: str                         # 'beam-line' | 'joint-point'
    target_id: int                    # Member.id 或 Joint.id
    values: Tuple[Optional[float], ...] = ()
    raw: List[str] = field(default_factory=list)
    load_sect_id: int = 0
    level: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "kind": self.kind, "target_id": self.target_id,
                "values": list(self.values), "raw": list(self.raw),
                "load_sect_id": self.load_sect_id, "level": self.level}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Load":
        vals = []
        for v in (d.get("values") or []):
            vals.append(None if v is None else _f(v))
        return cls(id=int(d["id"]), kind=str(d["kind"]),
                   target_id=int(d["target_id"]), values=tuple(vals),
                   raw=[str(s) for s in (d.get("raw") or [])],
                   load_sect_id=int(d.get("load_sect_id", 0)),
                   level=int(d.get("level", 0)))


@dataclass
class Resolution:
    """截面解析结果（``engine/secmap.py`` 的返回值，契约 §e 唯一裁决）。"""

    spec_path: str = ""               # PDMS 规格路径；未解析为 ""
    desp_params: List[float] = field(default_factory=list)
    status: str = UNRESOLVED          # 'resolved' | 'parametric' | 'inferred' | 'unresolved'
    reason: str = ""
    pkpm_name: str = ""               # 命中的 PKPM 截面名 / 候选键 / 族键
    source: str = ""                  # 'name' | 'shapeval' | 'family' | 'extra' | 'none'
    evidence: str = ""                # 仅 status='inferred'：证据链文本（契约 §e.5a）

    @property
    def ok(self) -> bool:
        return self.status in (RESOLVED, PARAMETRIC, INFERRED)

    @property
    def use_desp(self) -> bool:
        """是否写出 ``DESP`` 行：**只要**有 ``desp_params`` 就写（契约 §d.4-3 / §0.4-2）。"""
        return bool(self.desp_params)

    def to_dict(self) -> Dict[str, Any]:
        return {"spec_path": self.spec_path,
                "desp_params": list(self.desp_params), "status": self.status,
                "reason": self.reason, "pkpm_name": self.pkpm_name,
                "source": self.source, "evidence": self.evidence}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Resolution":
        return cls(spec_path=str(d.get("spec_path", "")),
                   desp_params=[_f(v) for v in (d.get("desp_params") or [])],
                   status=str(d.get("status", UNRESOLVED)),
                   reason=str(d.get("reason", "")),
                   pkpm_name=str(d.get("pkpm_name", "")),
                   source=str(d.get("source", "")),
                   evidence=str(d.get("evidence", "")))


# --------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------


@dataclass
class Model:
    """规范模型 —— 三条管线（.jwd / .pdt / .pdmsdump）唯一的交换结构。"""

    levels: List[Level] = field(default_factory=list)
    joints: Dict[int, Joint] = field(default_factory=dict)
    sections: Dict[int, Section] = field(default_factory=dict)
    members: List[Member] = field(default_factory=list)
    slabs: List[Slab] = field(default_factory=list)
    loads: List[Load] = field(default_factory=list)
    walls: List[Wall] = field(default_factory=list)
    source: str = ""                  # 输入文件路径
    source_format: str = ""           # 'jwd' | 'pdt' | 'pdmsdump'
    units: str = "mm"
    contract_version: str = CONTRACT_VERSION
    notes: List[str] = field(default_factory=list)   # 读取期的非致命问题/假设

    # ---------------------------------------------------------------- 查询
    def level(self, key: int) -> Level:
        for l in self.levels:
            if l.stdflr_id == key:
                return l
        raise KeyError("Level %r 不存在" % (key,))

    def level_map(self) -> Dict[int, Level]:
        return {l.stdflr_id: l for l in self.levels}

    def sorted_levels(self) -> List[Level]:
        return sorted(self.levels, key=lambda l: (l.z_bot, l.z_top, l.stdflr_id))

    def members_of(self, mtype: str) -> List[Member]:
        return [m for m in self.members if m.type == mtype]

    def used_sections(self) -> List[Section]:
        """被构件/墙引用到的 Section（按 id 排序）。

        板/墙的"截面"不是 Section 表里的行，而是由厚度合成的
        （``Section.for_panel``，名称键为 ``T<厚度>``）；调用方按去重厚度自行合成。
        """
        ids = {m.section for m in self.members}
        ids |= {w.section for w in self.walls if w.section >= 0}
        return [self.sections[i] for i in sorted(ids) if i in self.sections]

    def panel_thicknesses(self) -> List[float]:
        """本模型出现过的去重板厚/墙厚（升序），供合成板/墙截面用。"""
        ts = {s.thickness for s in self.slabs if not s.is_hole and s.thickness}
        ts |= {w.thickness for w in self.walls if w.thickness}
        return sorted(ts)

    def counts(self) -> Dict[str, Any]:
        """报告用计数（CONTRACT §h 的 ``report.counts``，唯一出处）。"""
        mem = {t: 0 for t in MEMBER_TYPES}
        for m in self.members:
            if m.type in mem:
                mem[m.type] += 1
        ld = {k: 0 for k in LOAD_KINDS}
        for x in self.loads:
            if x.kind in ld:
                ld[x.kind] += 1
        return {
            "levels": len(self.levels),
            "joints": len(self.joints),
            "sections": len(self.sections),
            "members": mem,
            "members_total": len(self.members),
            "slabs": len(self.slabs),
            "slabs_holes": sum(1 for s in self.slabs if s.is_hole),
            "slabs_with_thickness": sum(1 for s in self.slabs
                                        if s.thickness and not s.is_hole),
            "walls": len(self.walls),
            "loads": ld,
            "loads_total": len(self.loads),
        }

    # ------------------------------------------------------------ 序列化
    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "source": self.source,
            "source_format": self.source_format,
            "units": self.units,
            "notes": list(self.notes),
            "levels": [l.to_dict() for l in self.levels],
            "joints": {str(k): v.to_dict() for k, v in self.joints.items()},
            "sections": {str(k): v.to_dict() for k, v in self.sections.items()},
            "members": [m.to_dict() for m in self.members],
            "slabs": [s.to_dict() for s in self.slabs],
            "loads": [x.to_dict() for x in self.loads],
            "walls": [w.to_dict() for w in self.walls],
        }

    def to_json(self, indent: Optional[int] = None) -> str:
        """UTF-8 文本。

        ``indent=None``（默认）为**规范形式**：``sort_keys=True``、紧凑分隔符，
        同内容必得同字节，供跨模块测试比对；``indent=1`` 只用于人工 diff。
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True,
                          indent=indent,
                          separators=(",", ":") if indent is None else None)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Model":
        m = cls(
            levels=[Level.from_dict(x) for x in (d.get("levels") or [])],
            joints={int(k): Joint.from_dict(v) for k, v in (d.get("joints") or {}).items()},
            sections={int(k): Section.from_dict(v)
                      for k, v in (d.get("sections") or {}).items()},
            members=[Member.from_dict(x) for x in (d.get("members") or [])],
            slabs=[Slab.from_dict(x) for x in (d.get("slabs") or [])],
            loads=[Load.from_dict(x) for x in (d.get("loads") or [])],
            walls=[Wall.from_dict(x) for x in (d.get("walls") or [])],
            source=str(d.get("source", "")),
            source_format=str(d.get("source_format", "")),
            units=str(d.get("units", "mm")),
            contract_version=str(d.get("contract_version", CONTRACT_VERSION)),
            notes=[str(s) for s in (d.get("notes") or [])],
        )
        return m

    @classmethod
    def from_json(cls, s: str) -> "Model":
        return cls.from_dict(json.loads(s))

    def save_json(self, path: str, indent: Optional[int] = None) -> str:
        """写 UTF-8（无 BOM）JSON，返回路径。"""
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(self.to_json(indent=indent))
        return path

    @classmethod
    def load_json(cls, path: str) -> "Model":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_json(f.read())

    # -------------------------------------------------------------- 校验
    def validate(self) -> List[str]:
        """契约 §a.7 的检查项（外键可解析、Z 与层标高一致、多边形顶点数≥3、截面可解析…）。

        返回问题清单（空 = 通过）。前缀语义固定：

        * ``E-`` 致命：引用不可解析 / 建模所依据的等式不成立 —— CLI 必须中止（退出码 3）。
        * ``W-`` 可疑：可继续建模，但必须全部写入 ``report.geometry_anomalies``。

        本方法**不做**截面到 PDMS 规格的解析（那属于 ``SectionMap``），只检查
        "该截面是否有可用识别依据"。
        """
        p: List[str] = []
        lv = self.level_map()
        if len(lv) != len(self.levels):
            p.append("E-LEVEL-DUP: Level.stdflr_id 有重复（%d 个 Level，%d 个唯一键）"
                     % (len(self.levels), len(lv)))

        for l in self.sorted_levels():
            if l.z_top < l.z_bot - TOL:
                p.append("E-LEVEL-NEG: Level %s: z_top(%g) < z_bot(%g)"
                         % (l.stdflr_id, l.z_top, l.z_bot))
            elif not l.is_plane and abs((l.z_top - l.z_bot) - l.height) > TOL:
                p.append("W-LEVEL-H: Level %s: z_top-z_bot(%g) != height(%g)"
                         % (l.stdflr_id, l.z_top - l.z_bot, l.height))

        # ---- joints
        for j in self.joints.values():
            L = lv.get(j.level)
            if L is None:
                p.append("E-JOINT-LEVEL: Joint %s: level %s 不存在（外键不可解析）"
                         % (j.id, j.level))
                continue
            dz = j.z - (L.z_top + j.hdiff)
            if abs(dz) > TOL:
                p.append("E-JOINT-Z: Joint %s: z=%g != level.z_top+hdiff=%g（差 %g）"
                         % (j.id, j.z, L.z_top + j.hdiff, dz))

        # ---- sections
        for s in self.sections.values():
            if s.mat not in (0, 5, 6):
                p.append("W-SEC-MAT: Section %s: mat=%s 不在 {5=钢,6=混凝土,0=未知}"
                         % (s.id, s.mat))
            if not s.name and not s.dims and not s.params:
                p.append("W-SEC-NOIDENT: Section %s: 无 name、无 dims、无 params，"
                         "截面不可解析（将落入 unresolved）" % s.id)
            elif not s.dims and s.kind in (1, 2, 3, 26, 303):
                p.append("W-SEC-DIMS: Section %s: Kind=%s 属已解码族但 dims 为空"
                         % (s.id, s.kind))

        # ---- members
        for m in self.members:
            tag = "Member %s(%s)" % (m.id, m.type)
            if m.type not in MEMBER_TYPES:
                p.append("E-MEM-TYPE: %s: type 非法（须为 %s）"
                         % (tag, "/".join(MEMBER_TYPES)))
                continue
            L = lv.get(m.level)
            if L is None:
                p.append("E-MEM-LEVEL: %s: level %s 不存在（外键不可解析）"
                         % (tag, m.level))
            if m.section not in self.sections:
                p.append("E-MEM-SEC: %s: section %s 不存在（外键不可解析）"
                         % (tag, m.section))
            ln = m.length
            if ln <= TOL:
                p.append("E-MEM-ZERO: %s: start == end（零长度杆件）" % tag)
            elif ln < SHORT_MEMBER_MM:
                p.append("W-MEM-SHORT: %s: 长度 %g mm < %g mm（PDMS 结构建模可能报错）"
                         % (tag, ln, SHORT_MEMBER_MM))
            if L is not None:
                base = L.z_bot if m.type == "column" else L.z_top
                d0 = m.start[2] - (base + m.hdiff_start)
                if abs(d0) > TOL:
                    p.append("E-MEM-Z: %s: start.z=%g != %s(%g)+hdiff_start(%g)=%g"
                             % (tag, m.start[2],
                                "level.z_bot" if m.type == "column" else "level.z_top",
                                base, m.hdiff_start, base + m.hdiff_start))
                d1 = m.end[2] - (L.z_top + m.hdiff_end)
                if abs(d1) > TOL:
                    p.append("W-MEM-Z-END: %s: end.z=%g != level.z_top(%g)+hdiff_end(%g)"
                             "（梁/支撑跨层或斜置；柱越层正常）"
                             % (tag, m.end[2], L.z_top, m.hdiff_end))
                for which, z in (("start", m.start[2]), ("end", m.end[2])):
                    if not L.contains_z(z, Z_SLACK_MM):
                        p.append("W-MEM-ZRANGE: %s: %s.z=%g 超出层区间 [%g, %g] 超过 %g mm"
                                 % (tag, which, z, L.z_bot, L.z_top, Z_SLACK_MM))
            need = {"beam": 1, "column": 2, "brace": 4}.get(m.type)
            if need and m.ecc and len(m.ecc) != need:
                p.append("W-MEM-ECC: %s: ecc 有 %d 个分量，%s 约定为 %d 个"
                         % (tag, len(m.ecc), m.type, need))

        # ---- slabs
        for s in self.slabs:
            tag = "Slab %s" % s.id
            L = lv.get(s.level)
            if L is None:
                p.append("E-SLAB-LEVEL: %s: level %s 不存在（外键不可解析）"
                         % (tag, s.level))
            if len(s.polygon) < 3:
                p.append("E-SLAB-POLY: %s: 多边形顶点数 %d < 3"
                         % (tag, len(s.polygon)))
            else:
                for i in range(len(s.polygon)):
                    a = s.polygon[i]
                    b = s.polygon[(i + 1) % len(s.polygon)]
                    if abs(a[0] - b[0]) <= TOL and abs(a[1] - b[1]) <= TOL:
                        p.append("W-SLAB-DUP: %s: 相邻顶点重复（第 %d 与 %d 点）"
                                 % (tag, i + 1, (i + 1) % len(s.polygon) + 1))
                        break
            if s.thickness < -TOL:
                p.append("E-SLAB-THICK: %s: thickness=%g < 0" % (tag, s.thickness))
            if L is not None and abs(s.z - L.z_top) > TOL:
                p.append("E-SLAB-Z: %s: z=%g != level.z_top=%g" % (tag, s.z, L.z_top))

        # ---- walls
        for w in self.walls:
            tag = "Wall %s" % w.id
            if w.level not in lv:
                p.append("E-WALL-LEVEL: %s: level %s 不存在（外键不可解析）"
                         % (tag, w.level))
            if len(w.loop) < 3:
                p.append("E-WALL-LOOP: %s: 回路顶点数 %d < 3" % (tag, len(w.loop)))
            if w.z_top <= w.z_bot + TOL:
                p.append("W-WALL-Z: %s: z_top(%g) <= z_bot(%g)" % (tag, w.z_top, w.z_bot))
            for i, v in enumerate(w.loop):
                if (abs(v[2] - w.z_bot) > TOL) and (abs(v[2] - w.z_top) > TOL):
                    p.append("W-WALL-LOOPZ: %s: 第 %d 个顶点 U=%g 不在 {z_bot=%g, z_top=%g}"
                             % (tag, i + 1, v[2], w.z_bot, w.z_top))
                    break
            if w.section >= 0 and w.section not in self.sections:
                p.append("E-WALL-SEC: %s: section %s 不存在（外键不可解析）"
                         % (tag, w.section))

        # ---- loads
        for x in self.loads:
            tag = "Load %s" % x.id
            if x.kind not in LOAD_KINDS:
                p.append("E-LOAD-KIND: %s: kind=%r 非法（须为 %s）"
                         % (tag, x.kind, "/".join(LOAD_KINDS)))
                continue
            if x.kind == "joint-point":
                if x.target_id not in self.joints:
                    p.append("E-LOAD-TARGET: %s: 节点 %s 不存在" % (tag, x.target_id))
            else:
                tgt = [m for m in self.members if m.id == x.target_id]
                if not tgt:
                    p.append("E-LOAD-TARGET: %s: 构件 %s 不存在" % (tag, x.target_id))
            if len(x.values) != len(x.raw):
                p.append("W-LOAD-VALUES: %s: values(%d) 与 raw(%d) 长度不一致"
                         % (tag, len(x.values), len(x.raw)))
        return p

    def errors(self) -> List[str]:
        return [s for s in self.validate() if s.startswith("E-")]

    def warnings(self) -> List[str]:
        return [s for s in self.validate() if s.startswith("W-")]
