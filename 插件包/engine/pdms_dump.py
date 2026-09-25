# -*- coding: utf-8 -*-
"""PKPM-JWD导入导出 —— PDMS 中性导出文本 ``#PKPM-JWD-PDMSDUMP 1.0`` → 规范模型。实施包④。

契约条款（``spec/CONTRACT.md``）：§c（格式与解析规则，逐条对应）、§a.3（平面型 Level）、
§a.4（ShapeVal 编码，本模块只解出 kind/dims，编码由 ``jwd_write.shapeval_for`` 统一完成）、
§a.9（``Model.notes`` 是读取期信息的唯一回流通道）、§e.3 / §e.6（截面族与逆映射）、§g（编码纪律）。

实现要点（与 §c.3 的编号一一对应）::

    1  层级：#SBFR←#FRMW←#STRU←#ZONE←#SITE，缺父级 ⇒ ``DumpSyntaxError``（"E-PARSE"）。
    2  ``#SCTN`` 用"从尾部定位"法：``desp = tokens[4:len-10]``、尾部 10 个 token 是
       ``e1 n1 u1 e2 n2 u2 ori jusl meml bangle``；``len(tokens) >= 14``。
    3  ``#PANE`` 先找**第一个** ``~``：``(len(left)-3) % 3 == 0``、顶点 ≥ 3；
       尾部恰 3 个 token ``spref orient2 card``；无 ``~`` ⇒ ``spec_path=''`` + ``W-DUMP-NOSPEC``。
    4  ``#STWALL``：token 数 ∈ {10, 12}；``t[10] == '~'``、``t[11]`` = 墙厚（随单位换算）。
    5  ``spref``/``spre`` == ``'-'`` 是"无规格"哨兵，**不是**名字叫 ``-`` 的规格。
    6  ``ctype`` 与 ``ori``/``orient2`` 是冗余自校验位：按 ``ctype`` 归类，几何从坐标算；
       不一致只记 note（``W-DUMP-TYPE`` / ``W-DUMP-ORI``）。
    7  ``#PANE`` ⇒ ``Slab``（多边形不闭合；顶点 U 必须一致，误差 ≤ 1e-6，否则 E-PARSE）。
    8  ``#STWALL`` ⇒ ``Wall``（4 点直立回路，``z_top = z_bot + height``）。
    9  ``FRMW /GRID`` 下的 ``#SCTN`` 是轴网线，**忽略**并计数进 notes。
    10 ``#END`` 必须存在，其后只允许空行。
    11 层归并：全部出现过的 Z 升序去重 ⇒ 平面型 ``Level``（``stdflr_id`` 从 1 起编号，
       ``height = 0``，契约 §a.3）；交给 ``jwd_write`` 时再按 §b.3 归并成楼层。

单位（§c.1）：``UNITS`` 行缺失 ⇒ 按 ``mm`` 并处一条 note；``mm/cm/m`` 只换算**长度量**
（``E/N/U``、``#PANE.height``、``#STWALL.height`` 与尾部厚度、``#SCTN.desp``）；
``bangle`` 恒为度，不换算。``Model.units`` 恒为 ``mm``（§a.1：模块之间不再换算）。

截面（§e）：``SPREF`` 先经 ``section_map.reverse()``（§e.6）逆查 PKPM 名；命中
``RECT``/``H`` 两个**有证据**的用户参数化族（§e.3）时按 DESP 参数建 kind=1/2；
命中型钢库名/``<库族码>-<规格串>`` 时按 jwd_format.md §3.2/§3.3 鉴定 kind=26/303；
全不命中 ⇒ ``name=''``、``kind=0`` 并落 note（**不猜**）。
**ShapeVal 的编码只有一份实现**（§b.1 共同纪律 1）：``jwd_write.shapeval_for``，
本模块只产出 ``kind/dims/params``。
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from canonical import (TOL, Joint, Level, Member, Model, Section, Slab, Wall)

#: 契约 §c.2 的文件头与版本
HEADER = '#PKPM-JWD-PDMSDUMP'
FORMAT_VERSION = '1.0'

#: 契约 §c.1：单位换算（只有长度量）
UNIT_FACTOR = {'mm': 1.0, 'cm': 10.0, 'm': 1000.0}

#: 契约 §c.2：ctype / orient 词表
CTYPES = {'COLUMN': 'column', 'BEAM': 'beam', 'HBRACE': 'brace', 'VBRACE': 'brace'}
ORIENTS = ('E', 'N', 'U', 'S')
ORIENT2 = 'YNZU'

#: 契约 §e.3 的**有证据的**用户参数化族：(族键, spec_path, kind, mat, DESP 顺序)
PARAM_FAMILIES: Tuple[Tuple[str, str, int, int, Tuple[str, ...]], ...] = (
    ('RECT', '/USER_RECT-SPEC/Rectangle_Profile', 1, 6, ('B', 'H')),
    ('H', '/USER_H-SPEC/H_Profile', 2, 5, ('B1', 'B2', 'H', 'Tw', 'T1', 'T2')),
)

_NUM_RE = re.compile(r'^-?[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?$')
_NAME_RE = re.compile(r'^[\x21-\x7e]+$')
#: jwd_format.md §3.2/§3.3：HN/HW/HM 型钢库名的族码 = 39（国标热轧 H 型钢）
_H_NAME_RE = re.compile(r'^(HN|HW|HM)([0-9]+)X([0-9]+)$')
#: 插件 DLL 键表（jwd_format.md §3.3）：``1-[18a`` → 族 32、子类型 1；``2-I18a`` → 族 31、子类型 2
_LIB_PREFIX_RE = re.compile(r'^([12])-(\[|I)(.+)$')
#: 契约 §e.1 候选键 2：Kind=303 的 ``<库族码>-<规格串>``（如 ``6-B250*10.00``）
_K303_RE = re.compile(r'^([1-9])-(.+)$')
#: jwd_format.md §3.2：打包规格串 ``B<边长>*<壁厚>`` / ``B<a>*<b>*<壁厚>`` / ``D<直径>X<壁厚>``
_SPEC_B_RE = re.compile(r'^B([0-9.]+)\*([0-9.]+)(?:\*([0-9.]+))?$')
_SPEC_D_RE = re.compile(r'^D([0-9.]+)X([0-9.]+)$')

_NOTE_LIMIT = 400          # notes 条目上限（防止病态文件刷爆报告）


class DumpSyntaxError(ValueError):
    """契约 §c.3 的 ``E-PARSE``：dump 文法错误 ⇒ CLI 按 §f.2 以退出码 2 结束。"""

    def __init__(self, lineno: int, msg: str):
        super().__init__('E-PARSE: 第 %d 行：%s' % (lineno, msg))
        self.lineno = lineno


#: 若无显式注入，``parse_dump(text)``（契约冻结签名）用这个截面匹配器做逆映射。
DEFAULT_SECTION_MAP: Any = None


def set_default_section_map(section_map: Any) -> None:
    """给冻结签名的 ``parse_dump(text)`` 注入 ``SectionMap``（契约 §e.6，只需 ``.reverse()``）。

    CLI/GUI 在没有第 2 个参数可传时用这个入口（见 ``parse_dump`` 的说明）。
    """
    global DEFAULT_SECTION_MAP
    DEFAULT_SECTION_MAP = section_map


def load_dump(path: str) -> str:
    """按契约 §c.1 读 dump 文本：**GBK、不吞解码错误**（失败即 ``UnicodeDecodeError``）。"""
    with open(path, 'r', encoding='gbk', newline='') as f:
        return f.read()


# ---------------------------------------------------------------------------
# 内部：解析器
# ---------------------------------------------------------------------------
def _num(tok: str, lineno: int, what: str) -> float:
    if not _NUM_RE.match(tok):
        raise DumpSyntaxError(lineno, '%s 不是合法十进制数：%r（契约 §c.1 的 num）' % (what, tok))
    return float(tok)


def _name(tok: str, lineno: int, what: str) -> str:
    if (not tok) or (not _NAME_RE.match(tok)) or ('~' in tok):
        raise DumpSyntaxError(lineno, '%s 非法：%r（可见 ASCII 0x21-0x7E，且不含 ~，契约 §c.1）'
                              % (what, tok))
    return tok


class _Parser:
    def __init__(self, text: str, section_map: Any):
        self.text = text
        self.smap = section_map
        self.notes: List[str] = []
        self.unit = 'mm'
        self.factor = 1.0
        # 层级游标
        self.site = self.zone = self.stru = self.frmw = self.sbfr = ''
        self.frmw_is_grid = False
        self.grid_sctn = 0
        # 实体
        self.sec_by_key: Dict[Tuple[str, Tuple[str, ...]], Section] = {}
        self.members: List[Dict[str, Any]] = []
        self.slabs: List[Dict[str, Any]] = []
        self.walls: List[Dict[str, Any]] = []
        self.next_sec_id = 1
        self.next_mem_id = 1
        self.next_slab_id = 1
        self.next_wall_id = 1
        self.type_seq: Dict[str, int] = {}

    # ---------------------------------------------------------------- 工具
    def note(self, s: str) -> None:
        if len(self.notes) < _NOTE_LIMIT:
            self.notes.append(s)
        elif len(self.notes) == _NOTE_LIMIT:
            self.notes.append('（notes 已达 %d 条上限，其余同类信息不再逐条列出）' % _NOTE_LIMIT)

    def tail_no(self, name: str, seq: int) -> int:
        """``No_``：取元素名尾部的十进制数字（契约 §d.2 的命名模板），否则用批内序号。"""
        m = re.search(r'([0-9]+)$', name)
        return int(m.group(1)) if m else seq

    # ------------------------------------------------------------ 截面
    def make_section(self, spref: str, desp: Sequence[str], lineno: int) -> Section:
        sid = self.next_sec_id
        self.next_sec_id += 1
        note = ''
        if (not spref) or spref == '-':
            self.note('截面 %s：SPREF %s（契约 §c.3.5 的 "-" 哨兵 / 无规格）—— 按"无规格截面"处理，'
                      '不猜族别；写回 .jwd 时该构件仍建几何（契约 §d.4-2）'
                      % (sid, '缺失' if not spref else "'-'"))
            return Section(sid, 0, 0, '', {}, 'dump', sid, '', [], note='无规格（SPREF 缺失或 "-" 哨兵）')

        d: Dict[str, Any] = {}
        kind, mat, name = 0, 0, ''
        rev = None
        rev_fn: Optional[Callable[[str], Optional[str]]] = getattr(self.smap, 'reverse', None)
        if rev_fn is not None:
            try:
                rev = rev_fn(spref)
            except Exception as exc:                      # SectionMap 内部问题不应吞掉
                self.note('截面 %s：section_map.reverse(%r) 抛异常 %s（按未命中处理）'
                          % (sid, spref, exc))
                rev = None
        else:
            self.note('截面 %s：未注入 SectionMap（契约 §e.6），SPREF %r 无法逆查 PKPM 名；'
                      '调用方可用 parse_dump(text, section_map) 或 set_default_section_map()'
                      % (sid, spref))

        # ① 用户参数化族（契约 §e.3）：按 spec_path（主）或逆查名（辅）识别
        fam = None
        for key, path, k, mm, keys in PARAM_FAMILIES:
            if spref == path or (rev is not None and rev == key):
                fam = (key, path, k, mm, keys)
                break
        if fam is not None:
            key, path, kind, mat, keys = fam
            if len(desp) < len(keys):
                self.note('截面 %s：参数化族 %s 需要 %d 个 DESP 参数（%s），dump 只给了 %d 个 '
                          '—— dims 不全，写回 .jwd 时 ShapeVal 将留空（契约 §e.3）'
                          % (sid, key, len(keys), ','.join(keys), len(desp)))
            for i, k in enumerate(keys):
                if i < len(desp):
                    d[k] = float(desp[i]) * self.factor
            note = ('参数化族 %s（spec %s，契约 §e.3）：Kind=%s、dims=%s、DESP=%s'
                    % (key, path, kind, sorted(d), list(desp)))
            self.note('dump 截面 %s：SPREF %s → %s' % (sid, spref, note))
            # 注意：``Section.params`` 的语义是 **ShapeVal 参数体原文**（canonical §a.4），
            # 而 DESP 是**另一个序**（族参数序）⇒ 只写进 dims + note，**不**塞进 params
            # （否则 jwd_write 的"原文搬运"分支会把 DESP 序当 ShapeVal 序输出）。
            return Section(sid, kind, mat, name, d, 'dump', sid, '', [], note=note)
        if rev:
            mo = _H_NAME_RE.match(rev)
            if mo:
                kind, mat, name = 26, 5, rev
                d = {'family': 39, 'subtype': 1, 'H': float(mo.group(2)),
                     'B': float(mo.group(3))}
                note = ('型钢库名 %r → Kind=26、族 39（国标热轧 H 型钢，jwd_format.md §3.3 的键表）；'
                        'H/B 取自名称，**tf/tw 不在 dump 里**（PDMS 库存截面无 DESP）'
                        % rev)
            else:
                mo = _LIB_PREFIX_RE.match(rev)
                if mo:
                    kind, mat, name = 26, 5, rev
                    d = {'family': 32 if mo.group(2) == '[' else 31,
                         'subtype': int(mo.group(1))}
                    note = ('型钢库名 %r → Kind=26、族 %s、子类型 %s（jwd_format.md §3.3 的键表）；'
                            '尺寸不在名称里，ShapeVal 将在写回时留空'
                            % (rev, d['family'], d['subtype']))
                else:
                    mo = _K303_RE.match(rev)
                    if mo:
                        lib = int(mo.group(1))
                        spec = mo.group(2)
                        kind, mat, name = 303, 5, rev
                        d = {'lib_family': lib, 'spec_str': spec}
                        m2 = _SPEC_B_RE.match(spec)
                        m3 = _SPEC_D_RE.match(spec)
                        if m2:
                            # 规格串来自匹配文件（PKPM 侧目录名），其尺寸**恒为 mm**，
                            # 不随 dump 的 UNITS 换算（jwd_format.md §3.2 的串格式）
                            d['d'] = float(m2.group(1))
                            d['b'] = float(m2.group(3) or m2.group(1))
                        elif m3:
                            d['d'] = float(m3.group(1))
                            d['b'] = float(m3.group(1))
                        note = ('匹配文件键 %r → Kind=303（契约 §e.1 候选键 2 = '
                                '<库族码>-<规格串>）：lib_family=%s、spec_str=%r、'
                                'd/%s（jwd_format.md §3.2 的打包串格式）；'
                                'Kind=303 的 ShapeVal 槽 32 语义未解（契约 §a.4 禁止使用），'
                                '写回时若缺该槽则留空'
                                % (rev, lib, spec, 'b=%g' % d['b'] if 'b' in d else 'b 未知'))
        if not note:
            note = ('SPREF %s 未在截面匹配文件里逆查命中（契约 §e.6 的 reverse 返回 %s）'
                    '—— 按无识别依据处理（name 空、Kind=0、dims 空），'
                    '写回 .jwd 时该截面将落 unresolved' % (spref, rev))
            self.note('dump 截面 %s：%s' % (sid, note))
        else:
            self.note('dump 截面 %s：SPREF %s → %s' % (sid, spref, note))
        # 同上：DESP 是族参数序，不是 ShapeVal 参数体 ⇒ 不写进 ``params``（见 ① 的注释）
        return Section(sid, kind, mat, name, d, 'dump', sid, '', [], note=note)

    # ------------------------------------------------------------ 记录
    def sctn(self, toks: List[str], lineno: int) -> None:
        if len(toks) < 14:
            raise DumpSyntaxError(lineno, '#SCTN 至少 14 个 token（契约 §c.3.2），收到 %d：%r'
                                  % (len(toks), ' '.join(toks)))
        name = _name(toks[1], lineno, '#SCTN 的 name')
        ctype = toks[2]
        if ctype not in CTYPES:
            raise DumpSyntaxError(lineno, '#SCTN 的 ctype=%r 不在 %s（契约 §c.2）'
                                  % (ctype, '/'.join(sorted(CTYPES))))
        spref = toks[3]
        if spref != '-':
            _name(spref, lineno, '#SCTN 的 spref')
        desp = toks[4:len(toks) - 10]
        rest = toks[len(toks) - 10:]
        for x in desp:
            _num(x, lineno, '#SCTN 的 desp 参数')
        e1, n1, u1, e2, n2, u2 = (_num(rest[i], lineno, '几何分量') for i in range(6))
        ori, jusl, meml, bang = rest[6], rest[7], rest[8], rest[9]
        if ori not in ORIENTS:
            raise DumpSyntaxError(lineno, '#SCTN 的 ori=%r 不在 %s（契约 §c.2）'
                                  % (ori, '/'.join(ORIENTS)))
        bang_v = _num(bang, lineno, 'bangle（度，不随单位换算）')
        for tag, v in (('jusl', jusl), ('meml', meml)):
            if v != '-':
                _name(v, lineno, '#SCTN 的 %s' % tag)
        if self.frmw_is_grid:                      # §c.3.9：/GRID 下的是轴网线，忽略
            self.grid_sctn += 1
            return
        if not self.sbfr:
            raise DumpSyntaxError(lineno, '#SCTN 之前没有 #SBFR（契约 §c.3.1 的父子层级）')
        f = self.factor
        start = (e1 * f, n1 * f, u1 * f)
        end = (e2 * f, n2 * f, u2 * f)
        sec = self.sec_by_key.get((spref, tuple(desp)))
        if sec is None:
            sec = self.make_section(spref, desp, lineno)
            self.sec_by_key[(spref, tuple(desp))] = sec
        mtype = CTYPES[ctype]
        self.type_seq[mtype] = self.type_seq.get(mtype, 0) + 1
        mid = self.next_mem_id
        self.next_mem_id += 1
        # §c.3.6：type/ori 只是自校验位，几何以坐标为准
        d_e, d_n, d_u = end[0] - start[0], end[1] - start[1], end[2] - start[2]
        run = (d_e * d_e + d_n * d_n) ** 0.5
        if abs(d_u) > TOL and run <= TOL:
            geo_ori, geo_cls = 'U', 'column'
        elif abs(d_n) <= TOL < abs(d_e):
            geo_ori, geo_cls = 'E', 'beam'
        elif abs(d_e) <= TOL < abs(d_n):
            geo_ori, geo_cls = 'N', 'beam'
        else:
            geo_ori, geo_cls = 'S', 'brace'
        if geo_ori != ori:
            self.note('W-DUMP-ORI: #SCTN %s（第 %d 行）：文件写 ori=%s，几何算得 %s '
                      '—— 不改变几何（契约 §c.3.6）' % (name, lineno, ori, geo_ori))
        if geo_cls != mtype:
            self.note('W-DUMP-TYPE: #SCTN %s（第 %d 行）：ctype=%s 与几何分类 %s 不一致 '
                      '—— 仍按 ctype 归类（契约 §c.3.6）' % (name, lineno, ctype, geo_cls))
        self.members.append({
            'id': mid, 'type': mtype, 'name': name, 'no': self.tail_no(name, self.type_seq[mtype]),
            'section': sec.id, 'start': start, 'end': end, 'rotation': bang_v,
            'jusl': '' if jusl == '-' else jusl, 'meml': '' if meml == '-' else meml,
            'oriented': ori,
        })

    def pane(self, toks: List[str], lineno: int) -> None:
        if '~' in toks:
            i = toks.index('~')
            left, right = toks[1:i], toks[i + 1:]
        else:
            left, right = toks[1:], []
            self.note('W-DUMP-NOSPEC: #PANE %s（第 %d 行）无 "~" 尾部 ⇒ 板规格缺失 '
                      '（spec_path='')' % (left[0] if left else '?', lineno))
        if len(left) < 11 or (len(left) - 2) % 3:
            raise DumpSyntaxError(lineno, '#PANE 必须是 [标记, name, height, 顶点×3]：'
                                           '(len(left)-2) %% 3 == 0 且顶点 ≥ 3（契约 §c.3.3）：%r'
                                  % ' '.join(toks))
        name = _name(left[0], lineno, '#PANE 的 name')
        height = _num(left[1], lineno, '#PANE 的 height') * self.factor
        verts = [_num(x, lineno, '#PANE 顶点分量') * self.factor for x in left[2:]]
        if len(verts) % 3 or len(verts) // 3 < 3:
            raise DumpSyntaxError(lineno, '#PANE 顶点数 %d < 3（契约 §c.3.3）' % (len(verts) // 3))
        pts = [(verts[j], verts[j + 1], verts[j + 2]) for j in range(0, len(verts), 3)]
        us = set(round(p[2], 6) for p in pts)
        if len(us) > 1:
            raise DumpSyntaxError(lineno, '#PANE 各顶点 U 不一致 %s（契约 §c.3.7）'
                                  % sorted(us))
        spref, ori2, sjus = '', ORIENT2, 'dbot'
        if right or ('~' in toks):            # 有 ~ 就必须恰好 3 个 token（契约 §c.2 的 [ ] 组）
            if len(right) != 3:
                raise DumpSyntaxError(lineno, '#PANE 的 "~" 之后必须恰 3 个 token '
                                               '（spref orient2 card，契约 §c.3.3），收到 %d'
                                      % len(right))
            spref, ori2, sjus = right[0], right[1], right[2]
            if right[1] != ORIENT2:
                raise DumpSyntaxError(lineno, '#PANE 的 orient2=%r，契约冻结为 %r（§12#12）'
                                      % (right[1], ORIENT2))
            sjus = right[2]
            if spref != '-':
                _name(spref, lineno, '#PANE 的 spref')
            _name(sjus, lineno, '#PANE 的 card')
            if spref == '-':
                self.note('W-DUMP-NOSPEC: #PANE %s 的 spref="-"（无规格哨兵，契约 §c.3.5）'
                          % name)
                spref = ''
        sid = self.next_slab_id
        self.next_slab_id += 1
        self.slabs.append({'id': sid, 'name': name, 'no': self.tail_no(name, sid),
                           'polygon': [(p[0], p[1]) for p in pts], 'z': pts[0][2],
                           'thickness': height, 'spec_path': spref, 'ori': ori2, 'sjus': sjus})

    def stwall(self, toks: List[str], lineno: int) -> None:
        if len(toks) not in (10, 12):
            raise DumpSyntaxError(lineno, '#STWALL 的 token 数必须是 10 或 12（契约 §c.3.4），'
                                           '收到 %d：%r' % (len(toks), ' '.join(toks)))
        name = _name(toks[1], lineno, '#STWALL 的 name')
        spre = toks[2]
        if spre != '-':
            _name(spre, lineno, '#STWALL 的 spre')
        else:
            self.note('W-DUMP-NOSPEC: #STWALL %s 的 spre="-"（无规格哨兵，契约 §c.3.5）' % name)
        height = _num(toks[3], lineno, '#STWALL 的 height') * self.factor
        p1 = [_num(toks[4 + i], lineno, '#STWALL 底边起点分量') * self.factor for i in range(3)]
        p2 = [_num(toks[7 + i], lineno, '#STWALL 底边终点分量') * self.factor for i in range(3)]
        if len(toks) == 12:
            if toks[10] != '~':
                raise DumpSyntaxError(lineno, '#STWALL 第 11 个 token 应为 "~"，收到 %r'
                                      % toks[10])
            thick = _num(toks[11], lineno, '#STWALL 的厚度') * self.factor
        else:
            thick = 0.0
            self.note('W-DUMP-NOTHICK: #STWALL %s（第 %d 行）无厚度尾部 ⇒ thickness=0'
                      '（契约 §c.3.8）' % (name, lineno))
        if height <= 0:
            self.note('W-DUMP-NOTHICK: #STWALL %s 的 height=%g ≤ 0（契约 §c.3.8 要求 z_top > z_bot）'
                      % (name, height))
        wid = self.next_wall_id
        self.next_wall_id += 1
        z_bot = min(p1[2], p2[2])
        loop = [(p1[0], p1[1], p1[2]), (p2[0], p2[1], p2[2]),
                (p2[0], p2[1], p2[2] + height), (p1[0], p1[1], p1[2] + height)]
        self.walls.append({'id': wid, 'name': name, 'no': self.tail_no(name, wid),
                           'loop': loop, 'z_bot': z_bot, 'z_top': z_bot + height,
                           'thickness': thick, 'spec_path': '' if spre == '-' else spre})

    # ---------------------------------------------------------------- 主循环
    def parse(self) -> Model:
        lines = self.text.splitlines()
        idx = 0
        while idx < len(lines) and not lines[idx].strip():
            idx += 1
        if idx >= len(lines):
            raise DumpSyntaxError(1, '空文件：缺少首行 %s %s' % (HEADER, FORMAT_VERSION))
        t = lines[idx].lstrip('\ufeff').split()
        if not t or t[0] != HEADER:
            raise DumpSyntaxError(idx + 1, '首行必须是 "%s %s"，收到 %r'
                                  % (HEADER, FORMAT_VERSION, lines[idx]))
        if len(t) > 1 and t[1] != FORMAT_VERSION:
            self.note('dump 头部版本 %r != %r —— 按 1.0 的规则解析（契约 §c.2）'
                      % (t[1], FORMAT_VERSION))
        idx += 1

        # UNITS（契约 §c.1：缺失 ⇒ mm + 一条 note）
        while idx < len(lines) and not lines[idx].strip():
            idx += 1
        if idx < len(lines) and lines[idx].split()[0] == 'UNITS':
            toks = lines[idx].split()
            if len(toks) != 2 or toks[1] not in UNIT_FACTOR:
                raise DumpSyntaxError(idx + 1, 'UNITS 行必须是 "UNITS mm|cm|m"（契约 §c.1），收到 %r'
                                      % lines[idx])
            self.unit = toks[1]
            self.factor = UNIT_FACTOR[toks[1]]
            idx += 1
        else:
            self.note('dump 缺 UNITS 行 ⇒ 按契约 §c.1 视为 mm（需在报告 warnings 里留痕）')

        seen_end = False
        while idx < len(lines):
            raw = lines[idx]
            lineno = idx + 1
            idx += 1
            s = raw.strip()
            if not s:
                continue                               # §c.1：空行一律忽略
            toks = s.split()
            tag = toks[0]
            if tag == '#END':
                if len(toks) != 1:
                    raise DumpSyntaxError(lineno, '#END 行不能带参数：%r' % s)
                seen_end = True
                break
            if tag in ('#SITE', '#ZONE', '#STRU'):
                if len(toks) != 2:
                    raise DumpSyntaxError(lineno, '%s 需要恰好一个 name（契约 §c.2）' % tag)
                nm = _name(toks[1], lineno, '%s 的 name' % tag)
                if tag == '#SITE':
                    self.site = nm
                elif tag == '#ZONE':
                    if not self.site:
                        raise DumpSyntaxError(lineno, '#ZONE 之前没有 #SITE（契约 §c.3.1）')
                    self.zone = nm
                else:
                    if not self.zone:
                        raise DumpSyntaxError(lineno, '#STRU 之前没有 #ZONE（契约 §c.3.1）')
                    self.stru = nm
            elif tag in ('#FRMW', '#SBFR'):
                if len(toks) != 2:
                    raise DumpSyntaxError(lineno, '%s 需要恰好一个 name（契约 §c.2）' % tag)
                nm = _name(toks[1], lineno, '%s 的 name' % tag)
                if tag == '#FRMW':
                    if not self.stru:
                        raise DumpSyntaxError(lineno, '#FRMW 之前没有 #STRU（契约 §c.3.1）')
                    self.frmw = nm
                    self.frmw_is_grid = (nm.lstrip('/') == 'GRID')
                else:
                    if not self.frmw:
                        raise DumpSyntaxError(lineno, '#SBFR 之前没有 #FRMW（契约 §c.3.1）')
                    self.sbfr = nm
            elif tag == '#SCTN':
                self.sctn(toks, lineno)
            elif tag == '#PANE':
                if not self.sbfr:
                    raise DumpSyntaxError(lineno, '#PANE 之前没有 #SBFR（契约 §c.3.1）')
                self.pane(toks, lineno)
            elif tag == '#STWALL':
                if not self.sbfr:
                    raise DumpSyntaxError(lineno, '#STWALL 之前没有 #SBFR（契约 §c.3.1）')
                self.stwall(toks, lineno)
            else:
                raise DumpSyntaxError(lineno, '未知记录 %r（契约 §c.2 的 record 只有 '
                                              '#SITE/#ZONE/#STRU/#FRMW/#SBFR/#SCTN/#PANE/'
                                              '#STWALL/#END）' % tag)
        if not seen_end:
            raise DumpSyntaxError(len(lines), '缺少 #END（契约 §c.3.10）')
        for rest in lines[idx:]:
            if rest.strip():
                raise DumpSyntaxError(len(lines), '#END 之后只允许空行，收到 %r' % rest.strip())

        if self.grid_sctn:
            self.note('FRMW /GRID 下有 %d 条 #SCTN 是轴网线，按契约 §c.3.9 忽略'
                      '（jwd2pdms 生成的 dump 不写轴网；轴网由宏/合成轴网负责）' % self.grid_sctn)
        if not self.members and not self.slabs and not self.walls:
            self.note('dump 里没有任何 #SCTN/#PANE/#STWALL 记录（模型为空）')

        # -------------------- 平面型 Level（契约 §a.3 / §c.3.11）
        zs: List[float] = []
        for m in self.members:
            zs += [m['start'][2], m['end'][2]]
        for s in self.slabs:
            zs.append(s['z'])
        for w in self.walls:
            zs += [w['z_bot'], w['z_top']]
        zz: List[float] = []
        for v in sorted(zs):
            if not zz or abs(v - zz[-1]) > TOL:
                zz.append(v)
        levels = [Level(stdflr_id=i + 1, floor_id=0, no=i + 1, z_bot=z, z_top=z,
                        height=0.0, name='') for i, z in enumerate(zz)]
        at = {round(l.z_bot, 6): l.stdflr_id for l in levels}

        def level_of(z: float) -> int:
            return at[round(z, 6)]

        # -------------------- 节点（dump 没有节点表：由构件端点去重合成）
        joints: Dict[int, Joint] = {}
        pt_id: Dict[Tuple[float, float, float], int] = {}
        seq = 0
        for m in self.members:
            for p in (m['start'], m['end']):
                k = (round(p[0], 3), round(p[1], 3), round(p[2], 3))
                if k in pt_id:
                    continue
                seq += 1
                pt_id[k] = seq
                joints[seq] = Joint(seq, level_of(p[2]), p[0], p[1], p[2], 0, 0.0)
        per_level: Dict[int, List[int]] = {}
        for j in joints.values():
            per_level.setdefault(j.level, []).append(j.id)
        for lk, ids in per_level.items():
            for i, jid in enumerate(sorted(ids, key=lambda k: (joints[k].y, joints[k].x, k)), 1):
                joints[jid].no = i
        if joints:
            self.note('dump 不含节点表：%d 个节点由 #SCTN 端点按 (E,N,U) 去重合成'
                      '（No_ 按层内 (y, x) 升序；契约 §c 未定义节点表，'
                      '写回 .jwd 的 pkpmJoint 需要它）' % len(joints))

        # -------------------- 构件 / 板 / 墙
        members: List[Member] = []
        for m in self.members:
            lk = level_of(m['start'][2])
            lv = [l for l in levels if l.stdflr_id == lk][0]
            base_z = lv.z_bot if m['type'] == 'column' else lv.z_top
            h0 = m['start'][2] - base_z
            h1 = 0.0 if m['type'] == 'column' else m['end'][2] - lv.z_top
            # node_id = 柱的 pkpmColSeg.JtID（契约 §a.2）；梁用 grid_id、支撑用两端点，
            # 都在写回时按 (层, x, y) 匹配（本 dump 无这些列）
            node = (pt_id[(round(m['start'][0], 3), round(m['start'][1], 3),
                           round(m['start'][2], 3))] if m['type'] == 'column' else None)
            members.append(Member(
                m['id'], m['type'], lk, m['section'], m['start'], m['end'],
                m['rotation'], (), m['no'], None, node, '',
                0.0 if abs(h0) <= TOL else h0, 0.0 if abs(h1) <= TOL else h1,
                '', m['jusl'], m['meml']))
        slabs = [Slab(s['id'], level_of(s['z']), s['polygon'], s['z'], s['thickness'],
                      False, 0.0, 0.0, [], s['no'], s['spec_path'], s['ori'], s['sjus'])
                 for s in self.slabs]
        walls = [Wall(w['id'], level_of(w['z_bot']), w['thickness'], w['z_bot'], w['z_top'],
                      w['loop'], -1, w['no'], w['name'], w['spec_path'])
                 for w in self.walls]

        sections = {s.id: s for s in self.sec_by_key.values()}
        model = Model(levels=levels, joints=joints, sections=sections, members=members,
                      slabs=slabs, loads=[], walls=walls, source='', source_format='pdmsdump',
                      units='mm', notes=[])
        if self.site or self.zone or self.stru:
            self.note('dump 层级：#SITE %s → #ZONE %s → #STRU %s（FRMW/SBFR 只影响分组，'
                      '几何不带层级信息）' % (self.site or '?', self.zone or '?',
                                              self.stru or '?'))
        self.note('dump 不含荷载记录（契约 §c.2 的记录集没有荷载项）⇒ Model.loads 为空；'
                  '写回 .jwd 时 pkpmLoadSeg 写 0 行')
        self.note('单位：UNITS %s（换算系数 %g）→ 规范模型内部恒为 mm（契约 §a.1）'
                  % (self.unit, self.factor))
        model.notes.extend(self.notes)
        return model


# ---------------------------------------------------------------------------
# 公开入口
# ---------------------------------------------------------------------------
def parse_dump(text: str, section_map: Any = None) -> Model:
    """契约签名 ``parse_dump(text: str) -> Model``（纯函数，收文本不收路径）。

    追加的**可选**第 2 参数 ``section_map``：契约 §e.6 的 ``SectionMap``（只需 ``.reverse()``），
    用于"``SPREF`` → PKPM 截面名"的逆查。省略时取 ``set_default_section_map()`` 注入的值；
    两者都没有时仍能解析，只是截面只落 SPREF 事实、不落 PKPM 名（记 note）。
    CLI 走冻结签名时用 ``set_default_section_map(SectionMap.load(...))`` 注入。
    """
    if isinstance(text, (bytes, bytearray)):
        raise TypeError('parse_dump 收 str（契约 §b.1）；请在调用方按契约 §c.1 用 GBK 解码'
                        '（可用 load_dump(path)），不要传 bytes')
    if not isinstance(text, str):
        raise TypeError('parse_dump 需要 str，收到 %r' % type(text))
    p = _Parser(text, section_map if section_map is not None else DEFAULT_SECTION_MAP)
    return p.parse()
