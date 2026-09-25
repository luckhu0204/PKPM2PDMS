# -*- coding: utf-8 -*-
"""PKPM-JWD导入导出 —— 截面转化核心：四向编解码 + 随包转化表（契约 §k 的唯一实现）。

契约：``spec/CONTRACT.md`` §(k)（R2），引用 ``§a.4``（dims 解码的唯一规则）、
``§e.3/§e.5``（族与 unresolved 措辞）、``§j.4.7``（``$DEFFRAMESECTION`` 的 5 行模板）、
``§l.6``（目录宏 → ``.jwd``/``.pdt`` 的覆盖范围）。契约版本常量沿用 ``canonical.CONTRACT_VERSION``。

本模块做四件事
------------------------------------------------

1. **内置转化表** ``engine/section_table.csv``（3,176 行 × 15 列，§k.2 冻结布局，
   UTF-8 **带 BOM** + CRLF）的**只读**装载（:func:`load_builtin_table` / :class:`SectionTable`）；
2. **两套编解码四件套**（§k.3）：``ShapeVal``（``.jwd``）与 ``$DEFFRAMESECTION``（``.pdt``），
   每种都同时给出 ``decode`` 与 ``encode``，方向可逆；
3. **数据库侧**（§k.4）：``to_pdms`` / ``from_pdms`` —— 与 ``secmap.SectionMap`` 的四级优先级
   串接（不在本模块另立一套优先级）；
4. **信息损失申报**（§k.5）：``SectionTable.loss_report(direction)`` 返回冻结清单；
   另附**未解码项登记表** :data:`UNKNOWN_DECODE_ITEMS`（每条 ``confidence='unknown'`` +
   ``how_to_confirm``），供报告与自检逐条打印。

不猜原则（本模块最高纪律）
------------------------------------------------

* 未解码的东西**一律**标 ``confidence='unknown'`` 并给出"怎么才能确认"
  （:data:`UNKNOWN_DECODE_ITEMS`，机器可读：``how_to_confirm`` 字段）；
* 凡是无法唯一确定的编码，``encode_*`` **抛** ``ValueError("unencodable: …")``，
  消息里写明缺什么证据 —— **禁止**降级成空串、0 或"照抄同类样本"以外的任何猜测；
* ``.pdt`` 与 ``.jwd`` 之间、PKPM 与 PDMS 之间的**每一处**有损/未知，都必须能在
  ``loss_report()`` 里查到（§k.5 的冻结清单）。

未解码项登记（``confidence='unknown'``，**逐条给出确认途径**）
------------------------------------------------

================================= ==== ==================================================================
id                                对象  怎么才能确认
================================= ==== ==================================================================
``family-19``                     UNEQUEAL_T（推断族码 19）  在 DLL 里找到独立于 .NET #US 堆的引用（IL 的 ldstr token 顺序），
                                                            或对同一截面做一次 PDMS→PKPM 真实导出后读 ``Kind``/族码
``family-TRAPEZOID``              族码 TRAPEZOID             同上；或看 Add-in 的 ``CA2PDMS`` 分支实现
``family-DOUBLE_C``               族码 DOUBLE_C              同上
``family-RECT``                   族码 RECT                  同上；`RECT` 已知对应 ``/USER_RECT-SPEC/Rectangle_Profile``，
                                                            但**族码值**未知（本包只按名走 Kind=1 模板，见 §l.6）
``kind-2``                        ``.jwd`` Kind=2 的 6 尺寸槽 取一个含多条**不对称**焊接 H 的 ``.jwd`` 样本（B1≠B2 或 T1≠T2），
                                                            与 ``.pdt`` 的 ``B1,B2,H1,H2,B3,H3`` 逐项对齐
``kind-26-slot-order``            Kind=26 族码≠39 的槽序    导出含槽钢/工字钢的多条样本，与 GB706/GB707 表值逐项对齐
``kind-303-slot27``               Kind=303 槽 27            导出更多不同族码/形状的 Kind=303 截面做交叉
``kind-303-slot32``               Kind=303 槽 32            同上（现按"方矩 16672 / 圆 16640"的规则推，【推断-中】）
================================= ==== ==================================================================

已知边界（照实报告，不"修表"）
------------------------------------------------

* 内置表里 **256 条右值在目录宏里不存在**（Double-L 三族缩写不一致，``conflicts.md`` §2.2）、
  **4 条**右值原本缺前导 ``/``（源表已补齐）、**759 处**大小写差异 —— 均只做归类报告，不改用户原件；
* ``RECT``/``TRAPEZOID``/``DOUBLE_C``/``UNEQUEAL_T`` 四行的 ``family_code=0``、
  ``source='macro+match+dll_carry_rejected'``：族码在 DLL 里被 .NET #US 串堆去重、交叉校验拒绝，
  **未解**（§k.2 明确"原样保留"，本模块**不改写** ``confidence``/``source`` 列）。

本模块只依赖标准库与 ``canonical``（契约 §b.5：不得 import 其它引擎模块；``secmap`` 由**调用方**
注入，本模块不 import 它，避免环状依赖）。
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:                                     # 直接运行 / 测试把 engine/ 加进 sys.path
    from canonical import (INFERRED, PARAMETRIC, RESOLVED, UNRESOLVED, Section)
except ImportError:                      # pragma: no cover - 作为包导入（python -m engine.cli）
    from .canonical import (INFERRED, PARAMETRIC, RESOLVED, UNRESOLVED, Section)

__all__ = [
    "CONFIDENCE_LEVELS", "CSV_COLUMNS", "BUILTIN_TABLE", "BUILTIN_META", "TABLE_SCHEMA",
    "STEEL_LIB_FAMILIES", "PARAM_FAMILIES", "FAMILY_KIND_303", "FAMILY_KIND_26",
    "RECT_TEMPLATE_DEFAULT_BH", "CIRCLE_TEMPLATE_DEFAULT_D",
    "UNKNOWN_DECODE_ITEMS", "unknown_items", "loss_items",
    "ParamDef", "SectionRec", "SectionTable",
    "load_builtin_table", "verify_builtin_table",
    "table_from_jwd", "table_from_pdt", "rec_from_section",
    "decode_shapeval", "encode_shapeval",
    "decode_defframesection", "encode_defframesection",
    "rec_from_defframesection", "placeholder_defframesection",
    "effective_kind", "output_kind", "family_of", "group_tables_of",
    "unencodable_item_ids",
    "to_pdms", "from_pdms", "spec_str_of", "lib_family_of",
    "LOSS_DIRECTIONS",
]

# --------------------------------------------------------------------------
# 常量（§k.2 冻结）
# --------------------------------------------------------------------------

#: 契约 §k.2 冻结的 15 列列序（**不得**增删改序）
CSV_COLUMNS = ["key", "pkpm_name", "family_code", "family_name_cn", "kind", "shapeval",
               "dims_json", "mat", "pdms_spec_path", "pdms_catalogue", "is_parametric",
               "params_json", "confidence", "source", "extra_json"]

#: 内部/JSON 序列化的模式串
TABLE_SCHEMA = "section_table/1.0"

#: ``confidence`` 词表（§k.1 冻结）
CONFIDENCE_LEVELS = ("high", "medium", "low", "unknown")

#: 随包转化表与元数据（§k.2）
_HERE = os.path.dirname(os.path.abspath(__file__))
BUILTIN_TABLE = os.path.join(_HERE, "section_table.csv")
BUILTIN_META = os.path.join(_HERE, "section_table.meta.json")

#: ``loss_report(direction)`` 允许的方向（§k.5 冻结）
LOSS_DIRECTIONS = ("jwd2db", "db2jwd", "pdt2db", "db2pdt")

#: DLL 里的**型钢库族码**：``.jwd`` 以 ``Kind=26`` 包装、族码放在第 2 个字段
#: （``jwd_format.md`` §3.2：``26,39,1,450,0,200,14,9,0,…`` / ``26,32,2,180,0,74,9,5,…``）
STEEL_LIB_FAMILIES = (31, 32, 33, 36, 37, 38, 39, 40, 66, 71, 72, 73)

#: **用户参数化族**：``.jwd`` 的 ``Kind`` 就是族码本身（``.pdt`` 侧同理：
#: ``SHAPE=3``/``KIND=3`` = CIRCLE 族、``SHAPE=39`` = 族码 39；见 ``db_pkpm_sections.md`` §4.5）
PARAM_FAMILIES = (2, 3, 15, 16, 17, 18, 20, 21, 22, 23, 24)

#: 族码 77（方矩管/圆管/圆钢）在 ``.jwd`` 里落 ``Kind=303``（3 条样本实证：``303,77,…``）
FAMILY_KIND_303 = 77
#: 型钢库族在 ``.jwd`` 里落 ``Kind=26`` 包装
FAMILY_KIND_26 = 26

#: ``Kind=303`` 的**槽 32**（形状码）：方矩 ``16672`` / 圆 ``16640``
#: ——【推断-中】，仅 3 条样本；规则按 C11 的参考实现（``lib_family >= 4`` 为方矩管/方管族）
SHAPE_CODE_RECT = 16672
SHAPE_CODE_ROUND = 16640
SHAPE_CODE_RECT_MIN_LIB = 4          #: lib_family ≥ 该值 ⇒ 方矩（16672），否则圆（16640）

#: ``Kind=303`` 的**槽 27**（冷弯薄壁型钢库族码）= 规格名首数字前缀（§12#20）
#: 该值由 :func:`lib_family_of` 从 ``pkpm_name``（``6-B250*10.00``）或 ``dims['lib_family']`` 取。

#: 打包 ASCII 规格串的容量：槽 2..7 共 6 槽 × 2 字符
_PACKED_SLOTS = 6
_PACKED_CHARS = 2 * _PACKED_SLOTS

#: §l.6 的**模板族默认值**（仅用于 :meth:`SectionTable.to_jwd_sections`；
#: 不是"猜"——出处：``/USER_RECT`` 的 DTSET ``DPRO ( 500 )``、``/USER_CIRCLE`` 的
#: ``DPRO ( 300 )``，见 CONTRACT 附录 D.4 与 §e.3 的 Kind=3 行）
RECT_TEMPLATE_DEFAULT_BH = (500.0, 500.0)
CIRCLE_TEMPLATE_DEFAULT_D = 300.0
#: 触发模板补参的两个族键（内置表里就是这两个 ``pkpm_name``；族码分别是 0 与 3）
TEMPLATE_RECT_KEY = "RECT"
TEMPLATE_CIRCLE_KEY = "CIRCLE"

# --------------------------------------------------------------------------
# 未解码项登记表（§k.1 的 ``confidence='unknown'``；每条**必须**能回答"怎么才能确认"）
# --------------------------------------------------------------------------

#: 每项：``confidence`` 恒为 ``'unknown'``；``how_to_confirm`` 是**可执行**的确认途径；
#: ``affects`` 列出受影响的函数/方向；``evidence`` 是可复核的出处。
UNKNOWN_DECODE_ITEMS: List[Dict[str, Any]] = [
    {
        "id": "family-19",
        "subject": "族码 19（UNEQUEAL_T）",
        "confidence": "unknown",
        "what": "族码值 19 本身是**推断**：DLL 尾部相邻块的族名列表里它紧跟 TEE(18) 但没有配到数字，"
                "15..24 连续块唯一缺号才是 19；未互证。内置表里 UNEQUEAL_T 行的 family_code 因此为 0、"
                "source='macro+match+dll_carry_rejected'（原样保留，未改写）。",
        "why": ".NET #US 字符串堆对相同字面量去重 ⇒ 该编码串在字节里不可见；匹配文件里也没有可反查的实例。",
        "how_to_confirm": "① 在 DLL 里找到独立于 .NET #US 堆的引用（IL 指令的 ldstr token 顺序）；"
                          "或 ② 对同一个 UNEQUEAL_T 截面做一次真实的 PDMS→PKPM 导出（Add-in 的 "
                          "PKPM.PDMSxCA.PDMS2CA 类），读回 .jwd 的 Kind 与族码。",
        "affects": ["from_pdms", "to_jwd_sections", "encode_shapeval"],
        "evidence": "db_pkpm_sections.md §2.3/§8.3；conflicts §4.2；CONTRACT §12#18",
    },
    {
        "id": "family-TRAPEZOID",
        "subject": "族码 TRAPEZOID",
        "confidence": "unknown",
        "what": "族码值未解（DLL 里看不到、匹配文件里没有实例）。内置表 RECT/TRAPEZOID/DOUBLE_C 三行的 "
                "family_code 均为 0，source='macro+match+dll_carry_rejected'（原样保留，未改写）。",
        "why": "编码串被 .NET #US 去重；-- 无交叉验证样本。",
        "how_to_confirm": "① 在 DLL 里找独立于 #US 堆的引用；或 ② 反汇编/观察 Add-in 的 CA2PDMS 分支；"
                          "或 ③ 从 PDMS 侧反查（建一个 TRAPEZOID 规格再导出）。",
        "affects": ["from_pdms", "to_jwd_sections"],
        "evidence": "db_pkpm_sections.md §2.3/§8.3；conflicts §4.3；CONTRACT §12#18",
    },
    {
        "id": "family-DOUBLE_C",
        "subject": "族码 DOUBLE_C",
        "confidence": "unknown",
        "what": "族码值未解；内置表该行 family_code=0、source='macro+match+dll_carry_rejected'（原样保留）。",
        "why": "编码串被 .NET #US 去重；无交叉验证样本。",
        "how_to_confirm": "同 family-TRAPEZOID：在 DLL 里找独立引用 / 看 CA2PDMS 分支 / 从 PDMS 侧反查。",
        "affects": ["from_pdms", "to_jwd_sections"],
        "evidence": "db_pkpm_sections.md §2.3/§8.3；conflicts §4.3；CONTRACT §12#18",
    },
    {
        "id": "family-RECT",
        "subject": "族码 RECT",
        "confidence": "unknown",
        "what": "族码值未解。名字 → 规格路径是**已知的**（``RECT, /USER_RECT-SPEC/Rectangle_Profile``，"
                "匹配文件第 29 行），但 PKPM 侧的**族码值**未知 ⇒ 无法由族码判定 RECT 族的截面。"
                "本包按 §l.6 只提供\"仅模板\"路径：``Kind=1`` + DTSET 的 DPRO 默认值。",
        "why": "编码串被 .NET #US 去重；匹配文件里无 `RECT` 的实例（只有类名映射）。",
        "how_to_confirm": "同 family-TRAPEZOID；另可用 PKPM 建一个矩形用户截面并导出 .jwd，"
                          "看它的 Kind/族码。",
        "affects": ["from_pdms", "to_jwd_sections"],
        "evidence": "db_pkpm_sections.md §2.3/§8.3；conflicts §4.3；CONTRACT §12#18；§l.6 的 RECT 行",
    },
    {
        "id": "kind-2",
        "subject": ".jwd Kind=2（焊接工字形）的 6 个尺寸槽语义",
        "confidence": "unknown",
        "what": "字段**集合**可解（最细的 10=腹板厚 Tw、两个 16=翼缘厚、500=高、250×2=翼缘宽），"
                "但 **B 与 T 的交错顺序**未证（样本 B1=B2、T1=T2，两种读法同解）⇒ 不可生成 ShapeVal。",
        "why": "样本只有 2 条且内容完全相同（``2,10,500,250,16,250,16,5,4080,`` / ``…,30619,``）。",
        "how_to_confirm": "取一个含 B1≠B2 或 T1≠T2（变截面/不等翼缘）的 PKPM 模型导出 .jwd，"
                          "与 .pdt 的 ``B1,B2,H1,H2,B3,H3`` 逐项对齐（jwd_format.md §9.3#5 建议的做法）。",
        "affects": ["decode_shapeval", "encode_shapeval", "to_jwd_sections"],
        "evidence": "jwd_format.md §3.2/§9.3#5；conflicts §3；CONTRACT §12#18",
    },
    {
        "id": "kind-26-slot-order",
        "subject": "Kind=26 的族码 ≠ 39 时 6 个尺寸槽的顺序",
        "confidence": "unknown",
        "what": "只有族码 39（HN/HW/HM）能靠名称反推 H/B 并已 7/8 截面独立验证；"
                "族码 32 的 ``180,0,74,9,5,0`` 与 GB707 表值不能逐项对上 ⇒ 槽序未知 ⇒ **不可生成**。",
        "why": "样本只覆盖族码 32/39，且族码 32 的那一条与规范表值不一致（轻型槽钢 [18a 的 b/t 取值差异）。",
        "how_to_confirm": "导出含槽钢(32)/工字钢(31)/角钢(33)/欧日美标 H(36/37/38)/高频 H(40)/"
                          "T 型钢(66)/冷弯(71/72/73) 各若干条 .jwd，与对应规范表值逐项对齐。",
        "affects": ["encode_shapeval", "to_jwd_sections"],
        "evidence": "db_pkpm_sections.md §4.2/§8.3；CONTRACT §12#19；§l.6 的族码 31–73 行",
    },
    {
        "id": "kind-303-slot27",
        "subject": "Kind=303 的槽 27（冷弯薄壁型钢库族码）",
        "confidence": "unknown",
        "what": "**语义**已知为\"冷弯薄壁型钢库族码\"（1=热轧无缝圆管、6=方管 GB6728…），取值规则按"
                "\"规格名首数字前缀\"推（``6-B250*10.00`` → 6）——在 3 条样本上自洽，但没有第 4 个"
                "独立观测点，故按要求标 unknown。**回算时该槽必写**（不写就与样本不一致）。",
        "why": "只有 3 条样本（槽值 6/6/1），且与形状相关但无法与 PDMS 侧独立对齐。",
        "how_to_confirm": "导出更多不同族码/形状的 Kind=303 截面（尤其 3/4/5/7/8/9 号库族）做交叉，"
                          "或在 PKPM 里逐族建一个截面并读回 ShapeVal 的第 28 个字段。",
        "affects": ["encode_shapeval"],
        "evidence": "jwd_format.md §3.2 第 2 点；本次 C10/C11 复核（3 条样本逐字段一致）；CONTRACT §12#20",
    },
    {
        "id": "kind-303-slot32",
        "subject": "Kind=303 的槽 32（形状码 16672/16640）",
        "confidence": "unknown",
        "what": "现按\"方矩 = 16672 / 圆 = 16640\"的规则推（【推断-中】，只有 3 条样本）。"
                "回算时按 ``lib_family >= 4`` 取 16672，否则 16640。",
        "why": "3 条样本里方管两条 16672、圆管一条 16640，与形状相关但含义未定。",
        "how_to_confirm": "同 kind-303-slot27；重点验证 lib_family ∈ {3,4,7,8,9}（冷弯角钢/矩形管）时"
                          "槽 32 的取值是否仍按方/圆二分。",
        "affects": ["encode_shapeval"],
        "evidence": "jwd_format.md §3.2 第 3 点；CONTRACT §12#20；本次 C11 的参考实现",
    },
    {
        "id": "kind-303-packed-capacity",
        "subject": "Kind=303 的**打包串容量**（槽 2..7 = 6 槽 = 12 字符是否就是全部）",
        "confidence": "unknown",
        "what": "§a.4/§k.3 冻结的读取范围是 ``params[1:7]``（6 槽、12 字符，遇 NUL 截断），3 条样本的"
                "串长 ≤ 10 字符、槽 8..17 全 0，两种读法都自洽。但内置表 77 族 1,199 行里有 **324 行**"
                "的规格串长 13–14 字符（``B150*100*10.00`` 等），**超出 6 槽容量** ⇒ 打包区到底是"
                "6 槽（2..7）还是 16 槽（2..17，尺寸槽从 18 开始）未观测。本包按契约**不**擅自扩展到"
                "16 槽：这 324 行 ``encode_shapeval`` 抛 ``unencodable`` 并进报告，**不写截断串**"
                "（截断会静默产出一个错误的截面）。",
        "why": "样本的最长串是 ``B250*10.00``（10 字符，占 5 槽 + 1 个 NUL），区分不了 6 槽与 16 槽。",
        "how_to_confirm": "取一个矩形管截面（如内置表的 ``7-B150*100*10.00``）在 PKPM 里导出 .jwd，"
                          "读它的 ShapeVal：若槽 8..17 非 0（继续打包）⇒ 区间是 16 槽，按 §a.4 的"
                          "``params[1:17]`` 改写解码/编码；若仍为 0 ⇒ 串在 PKPM 侧被截断，需另找表达。",
        "affects": ["decode_shapeval", "encode_shapeval"],
        "evidence": "内置表 77 族行长度分布（7..12 共 875 行、13 字符 125 行、14 字符 199 行）；"
                    "jwd_format.md §3.2；CONTRACT §a.4/§k.3",
    },
    {
        "id": "kind-303-slot20-rect",
        "subject": "Kind=303 的槽 20（矩形管的\"另一边长\"）",
        "confidence": "unknown",
        "what": "方管/圆管的槽 18 与槽 20 相同（3 条样本实证）；**矩形管**时两者应不同，但样本里"
                "没有矩形管 ⇒ §a.4/§k.3 冻结的写法是\"记 unknown 并**沿用 d**\"。本包照此执行："
                "槽 20 写 ``d``（即与槽 18 相同），并在报告里逐条留痕。**副作用**：一个 ``B150*100*10.00``"
                "的矩形管被回算后，槽 18/20 都写 150 ⇒ 若 PKPM 用这两个槽建截面，会得到方形截面。",
        "why": "3 条样本的串都是单尺寸（``B250*10.00``/``B200*10.00``/``D194X8.0``），槽 18 与 20 恒等。",
        "how_to_confirm": "导出含矩形管（``B<a>*<b>*<t>``，如内置表 158 行里的 ``4-B100X50X3.0``）的"
                          "截面 .jwd，读 ShapeVal 的槽 18 与槽 20：若为 (a, b) ⇒ 按两尺寸写；"
                          "若为 (a, a) ⇒ 确认契约的\"沿用 d\"。",
        "affects": ["encode_shapeval"],
        "evidence": "CONTRACT §a.4 的 Kind=303 行注、§k.3 的矩形管注（\"未观测 ⇒ 沿用 d\"）；"
                    "内置表 158 行矩形管的 dims 有 h≠b（如 ``4-B100X50X3.0`` → H=100/B=50）",
    },
    {
        "id": "unknown-kind",
        "subject": "未在 §a.4 的 dims 键表内的 Kind（含 ``.jwd``/``.pdt`` 尚未观测到的族）",
        "confidence": "unknown",
        "what": "契约 §a.4 只冻结了 ``Kind ∈ {1,2,3,26,303}`` 的 ``dims`` 键表；其它 Kind 的"
                "字段布局**无证据** ⇒ ``dims`` 留空（或原样保留文件字段名），不猜语义。",
        "why": "本次两个样本只出现 Kind ∈ {1,2,3,26,303}（jwd_format.md §3.2），其余只是推断。",
        "how_to_confirm": "① 找一份含该 Kind 的 .jwd/.pdt 样本，读它的 ShapeVal 与 .pdt 的 "
                          "KIND/B1..H3；② 与 PDMS 侧同一截面的 SPRFILE PARA（具名参数）逐项对齐；"
                          "③ 对齐成功后再把该 Kind 的键表按 §0.3 写进契约 §a.4。",
        "affects": ["decode_shapeval", "encode_shapeval", "to_jwd_sections", "rec_from_section"],
        "evidence": "jwd_format.md §3.2/§4.5；CONTRACT §a.4/§12#18",
    },
]

#: 未解码项 id 全集（便于按 id 引用）
UNKNOWN_ITEM_IDS = tuple(it["id"] for it in UNKNOWN_DECODE_ITEMS)


def unknown_items() -> List[Dict[str, Any]]:
    """未解码项登记表的**副本**（每条 ``confidence='unknown'`` 且 ``how_to_confirm`` 非空）。"""
    return [dict(it) for it in UNKNOWN_DECODE_ITEMS]


def _unknown_item(item_id: str) -> Dict[str, Any]:
    for it in UNKNOWN_DECODE_ITEMS:
        if it["id"] == item_id:
            return it
    raise KeyError(item_id)


# --------------------------------------------------------------------------
# §k.5 信息损失冻结清单
# --------------------------------------------------------------------------

def _li(field_: str, severity: str, reason: str, evidence: str) -> Dict[str, str]:
    return {"field": field_, "severity": severity, "reason": reason, "evidence": evidence}


#: §k.5 的**冻结清单**（逐条照抄契约；``reason`` 里对 ``severity='unknown'`` 的条目
#: 追加了该未解码项的 ``how_to_confirm``，保证"未解码必须写清怎么确认"）
LOSS_REPORT_ITEMS: Dict[str, List[Dict[str, str]]] = {
    "jwd2db": [
        _li("工程自定义截面（Kind=1/2/3 的具体尺寸）只能落参数化模板", "partial",
            "尺寸变 DESP 参数",
            "db_pkpm_sections.md §7.1（.pdt 30 个 矩* 均落 /USER_RECT-SPEC/Rectangle_Profile）"),
        _li(".jwd 无力学量（A/g/Ix/Wx…）", "loss",
            "PARA 只有目录里有；样本 $DEFFRAMESECTION 只有 6 尺寸 + 6 厚度",
            "db_pkpm_sections.md §5.1 边 C；pdt_format.md §2.6"),
        _li("Kind=1 的 B/H 先后为【推断-中】", "unknown",
            "v1 §12#3 冻结为 B 前 H 后；不猜 —— 确认途径：用一件非对称的工程实测（PDMS /USER_XI 的"
            "参数名序为 B,H,Tw,T1,T2，与\"B 在前\"一致，但仍是推断）",
            "jwd_format.md §3.2；CONTRACT §12#3"),
    ],
    "db2jwd": [
        _li("族码 19/TRAPEZOID/DOUBLE_C/RECT 的族码值未解", "unknown",
            "不猜 —— 确认途径：" + _unknown_item("family-19")["how_to_confirm"],
            "db_pkpm_sections.md §2.3/§8.3；conflicts §4.3；CONTRACT §12#18"),
        _li("Kind=26 的族码 ≠ 39 时 6 尺寸槽顺序未知 ⇒ 不可生成", "unknown",
            "不猜 —— 确认途径：" + _unknown_item("kind-26-slot-order")["how_to_confirm"],
            "db_pkpm_sections.md §4.2；CONTRACT §12#19"),
        _li("Kind=2 字段语义未知 ⇒ 不可生成", "unknown",
            "不猜 —— 确认途径：" + _unknown_item("kind-2")["how_to_confirm"],
            "jwd_format.md §9.3#5；conflicts §3；CONTRACT §12#18"),
        _li("Kind=303 的槽 27/32 只能按规则推（27=名前缀、32=方/圆）", "partial",
            "规则在 3 条样本上自洽但不是事实（槽 27/32 单列为 unknown 项；见 UNKNOWN_DECODE_ITEMS）",
            "3 条样本 + 本次 C10/C11；CONTRACT §12#20"),
        _li("目录宏 PARA 的数值精度高于 PKPM 自己的取整", "partial",
            "HN300X150 的 tw：PARA 6.5 vs .jwd 6 —— 两者都映射到同一规格名 ⇒ 记为数值取整差异，不算失败",
            "本次 C10 实测；jwd_format.md §3.2 的取整表；CONTRACT §l.6 闭环判据 2"),
    ],
    "db2pdt": [
        _li("PARA 的 13–27 项（力学量/截面特性）在 .pdt 无字段", "loss",
            ".pdt 的 $DEFFRAMESECTION 只有 6 尺寸 + 6 厚度 + NAME1",
            "pdt_format.md §2.6；db_pkpm_sections.md §5.1 边 C"),
        _li("型钢 tf/tw 不进 T1..T6（样本恒 0）", "loss",
            "型钢按 NAME1 查库取厚度（设计意图，不是缺失）",
            "样本 32/32 条 T1..T6=0；db_pkpm_sections.md §3.3"),
        _li("M 的规则只有 3 个观测点（SHAPE=1/3→6、39→5）", "unknown",
            "§0.4-10 起 M 按 SHAPE 取（1/3→6、39→mat=5，与样本全部观测一致）；"
            "其它 SHAPE 仍未知 —— 确认途径：真机导出含其它 Kind 的 .pdt，读回 M 字段",
            "1_PM.pdt:2370(M=6,SHAPE=1)/:2515(M=5,SHAPE=39)；db_pkpm_sections.md §3.3；"
            "CONTRACT §12#17/§0.4-10"),
        _li("RI/RJ/UA 全 0、语义未证", "unknown",
            "本包一律写 0.000（样本如此）；不猜 —— 确认途径：找一个带倒角截面的 .pdt 样本",
            "样本 32/32 条为 0.000；db_pkpm_sections.md §3.6"),
        _li("EXI 第 2 个数 10011 语义未证（照抄）", "unknown",
            "本包照抄 10011；不猜 —— 确认途径：查 PDMS 元素类型码表",
            "样本 32/32 条恒定；db_pkpm_sections.md §3.3"),
    ],
    "pdt2db": [
        _li("型钢 tf/tw 缺失 ⇒ PARA 的 tw/tf 只能取自目录宏", "partial",
            ".pdt 不含型钢板厚",
            "db_pkpm_sections.md §7.1；CONTRACT §l.6 覆盖范围"),
        _li("$DESIGNPARA/EXR 语义未证 ⇒ 不进数据库", "loss",
            "50×20 无字段名；EXR 键集语义未证 —— 只写最小自洽集，不解释语义",
            "pdt_format.md §4/§6；CONTRACT §12#23"),
    ],
}


def loss_items(direction: str) -> List[Dict[str, str]]:
    """§k.5：按方向取信息损失清单（**副本**）。"""
    d = (direction or "").strip()
    if d not in LOSS_DIRECTIONS:
        raise ValueError("direction 必须 ∈ %s，收到 %r" % (list(LOSS_DIRECTIONS), direction))
    return [dict(x) for x in LOSS_REPORT_ITEMS[d]]


# --------------------------------------------------------------------------
# 小工具
# --------------------------------------------------------------------------

def _num(v: Any, default: Optional[float] = None) -> Optional[float]:
    """任意标量 → ``float``；整数保持 ``int``（与内置表的 JSON 投影一致）。"""
    if v is None or v == "":
        return default
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, (int, float)):
        f = float(v)
    else:
        try:
            f = float(str(v).strip())
        except (TypeError, ValueError):
            return default
    return int(f) if f.is_integer() else f


def _num_str(v: Any) -> str:
    """数值 → 契约要求的文本：**整数写整数、小数用 ``repr(float)``**（§k.3）。"""
    f = _num(v)
    if f is None:
        raise ValueError("非数值：%r" % (v,))
    if isinstance(f, int):
        return str(f)
    return repr(float(f))


def _norm_ws(s: Any) -> str:
    """空白归一化（**不改大小写**，§e.2/§k.1）。"""
    return " ".join(str(s or "").split())


def _norm_path(s: Any) -> str:
    """规格路径归一化：空白归一化 + 补前导 ``/``（§e.2/§k.1）。"""
    t = _norm_ws(s)
    if t and not t.startswith("/"):
        t = "/" + t
    return t


def _json_dumps(obj: Any) -> str:
    """§k.2 冻结的 JSON 列格式（确定性：``sort_keys`` + 紧凑分隔符）。"""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _read_text_or_path(text_or_path: Any, encoding: str = "utf-8-sig") -> str:
    """``from_csv``/``from_json`` 的入参判定：含换行 ⇒ 当文本；否则当路径（存在时读文件）。"""
    if isinstance(text_or_path, bytes):
        return text_or_path.decode(encoding)
    s = str(text_or_path)
    if "\n" in s or "\r" in s:
        return s
    if os.path.exists(s):
        with open(s, "r", encoding=encoding, newline="") as f:
            return f.read()
    return s


# --------------------------------------------------------------------------
# §k.1 数据类
# --------------------------------------------------------------------------

@dataclass
class ParamDef:
    """具名参数（§k.1 冻结）。

    :param name: 参数名原样（含单位括号，如 ``'h(mm)'``、``'B1'``、``'Parameter 1'``）
    :param desp_index: ``is_parametric=True`` ⇒ 1..N（= ``DESP[n]`` 的下标）；否则 0
    :param default: 默认值**原文**（来自 ``SPRFILE.PARA`` / ``DTSET.DPRO``）；无 ⇒ ``''``
    """

    name: str = ""
    desp_index: int = 0
    default: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "desp_index": int(self.desp_index),
                "default": self.default}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ParamDef":
        return cls(name=str(d.get("name", "")), desp_index=int(d.get("desp_index", 0) or 0),
                   default=str(d.get("default", "")))


@dataclass
class SectionRec:
    """一条截面记录（§k.1 冻结）。键序固定见 :meth:`to_dict`。"""

    key: str = ""
    pkpm_name: str = ""
    family_code: int = 0
    family_name_cn: str = ""
    kind: int = 0
    shapeval: str = ""
    dims: Dict[str, Any] = field(default_factory=dict)
    mat: int = 5
    pdms_spec_path: str = ""
    pdms_catalogue: str = ""
    is_parametric: bool = False
    params: List[ParamDef] = field(default_factory=list)
    confidence: str = "unknown"
    source: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    # ---------------------------------------------------------------- JSON
    def to_dict(self) -> Dict[str, Any]:
        """JSON 友好（**键序固定**：与 §k.2 的 15 列同序）。"""
        return {
            "key": self.key,
            "pkpm_name": self.pkpm_name,
            "family_code": int(self.family_code or 0),
            "family_name_cn": self.family_name_cn,
            "kind": int(self.kind or 0),
            "shapeval": self.shapeval,
            "dims": dict(self.dims or {}),
            "mat": int(self.mat or 0),
            "pdms_spec_path": self.pdms_spec_path,
            "pdms_catalogue": self.pdms_catalogue,
            "is_parametric": bool(self.is_parametric),
            "params": [p.to_dict() for p in self.params],
            "confidence": self.confidence,
            "source": self.source,
            "extra": dict(self.extra or {}),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SectionRec":
        rec = cls(
            key=str(d.get("key", "")),
            pkpm_name=str(d.get("pkpm_name", "")),
            family_code=int(d.get("family_code", 0) or 0),
            family_name_cn=str(d.get("family_name_cn", "")),
            kind=int(d.get("kind", 0) or 0),
            shapeval=str(d.get("shapeval", "")),
            dims=dict(d.get("dims") or {}),
            mat=int(d.get("mat", 0) or 0),
            pdms_spec_path=str(d.get("pdms_spec_path", "")),
            pdms_catalogue=str(d.get("pdms_catalogue", "")),
            is_parametric=bool(d.get("is_parametric", False)),
            params=[ParamDef.from_dict(x) if isinstance(x, dict) else ParamDef(*x)
                    for x in (d.get("params") or [])],
            confidence=str(d.get("confidence", "unknown")),
            source=str(d.get("source", "")),
            extra=dict(d.get("extra") or {}),
        )
        if not rec.key:
            rec.key = rec.pkpm_name or rec.pdms_spec_path
        return rec

    # ---------------------------------------------------------------- 便捷
    def copy(self) -> "SectionRec":
        return SectionRec.from_dict(self.to_dict())

    @property
    def unknown_item_ids(self) -> List[str]:
        """本条记录触到的未解码项 id（来自 ``extra['unknown_items']``，保序去重）。"""
        out: List[str] = []
        for x in (self.extra or {}).get("unknown_items", []) or []:
            if x not in out:
                out.append(x)
        return out

    def section(self, table: str = "") -> Section:
        """转成 ``canonical.Section``（几何/规格之外的证据留在 ``note``）。"""
        note = []
        if self.is_parametric:
            note.append("参数化族：DESP 参数见 params[]（desp_index 1..n）")
        ids = self.unknown_item_ids
        if ids:
            note.append("未解码项 %s（confidence=%s）：%s"
                        % (",".join(ids), self.confidence,
                           (self.extra or {}).get("reason", "")))
        return Section(id=int((self.extra or {}).get("jwd_id")
                              or (self.extra or {}).get("pdt_id") or 0),
                       kind=effective_kind(self), mat=int(self.mat or 0),
                       name=self.pkpm_name, dims=dict(self.dims or {}), table=table,
                       no=int((self.extra or {}).get("no") or 0),
                       shapeval=self.shapeval, params=[], note="；".join(note))


# --------------------------------------------------------------------------
# §k.1 SectionTable
# --------------------------------------------------------------------------

class SectionTable:
    """截面转化表（§k.1）。``recs`` 视为**只读**：内部索引按 ``len(recs)`` 失效重建。"""

    def __init__(self, recs: Optional[Iterable[SectionRec]] = None,
                 source: str = "") -> None:
        self.recs: List[SectionRec] = list(recs or [])
        self.source: str = source
        self._idx: Optional[Tuple[int, Dict[str, SectionRec], Dict[str, SectionRec],
                                  Dict[str, SectionRec]]] = None

    # ---------------------------------------------------------------- 容器协议
    def __len__(self) -> int:
        return len(self.recs)

    def __iter__(self):
        return iter(self.recs)

    def __getitem__(self, i):
        return self.recs[i]

    # ---------------------------------------------------------------- 索引
    def _index(self):
        if self._idx is None or self._idx[0] != len(self.recs):
            by_key: Dict[str, SectionRec] = {}
            by_name: Dict[str, SectionRec] = {}
            by_path: Dict[str, SectionRec] = {}
            for r in self.recs:
                by_key.setdefault(_norm_ws(r.key), r)
                if r.pkpm_name:
                    by_name.setdefault(_norm_ws(r.pkpm_name), r)
                if r.pdms_spec_path:
                    by_path.setdefault(_norm_path(r.pdms_spec_path), r)
            self._idx = (len(self.recs), by_key, by_name, by_path)
        return self._idx

    # ---------------------------------------------------------------- 查询
    def get(self, key: Optional[str] = None, pkpm_name: Optional[str] = None,
            pdms_spec_path: Optional[str] = None) -> Optional[SectionRec]:
        """按 ``key`` / ``pkpm_name`` / ``pdms_spec_path`` 查一条（§k.1）。

        * 匹配规则：**空白归一化、不改大小写**（同 §e.2）；``pdms_spec_path`` 查询时**补前导 ``/``**；
        * 优先级：``key`` → ``pkpm_name`` → ``pdms_spec_path``；
        * 三者全为 ``None`` ⇒ ``ValueError``（这是编程错误，不是"查不到"）；
        * 查不到返回 ``None``（**禁止**返回编造的记录）。
        """
        if key is None and pkpm_name is None and pdms_spec_path is None:
            raise ValueError("get() 至少要给 key / pkpm_name / pdms_spec_path 之一")
        _, by_key, by_name, by_path = self._index()
        if key is not None:
            hit = by_key.get(_norm_ws(key))
            if hit is not None:
                return hit
        if pkpm_name is not None:
            hit = by_name.get(_norm_ws(pkpm_name))
            if hit is not None:
                return hit
        if pdms_spec_path is not None:
            return by_path.get(_norm_path(pdms_spec_path))
        return None

    def by_family(self, family_code: int) -> List[SectionRec]:
        """同一族码的全部记录（保序）。``family_code=0`` ⇒ 取族码未解的记录。"""
        want = int(family_code or 0)
        return [r for r in self.recs if int(r.family_code or 0) == want]

    def unknown_rows(self) -> List[Tuple[str, SectionRec]]:
        """返回 ``[(未解码项 id, 记录)]``：内置表里触到未解码项的行（按 :func:`effective_kind` 判定）。

        判定（**只依据记录自身的数据，不猜**）：

        * ``family_code == 0`` 且 ``pkpm_name`` ∈ {``RECT``, ``TRAPEZOID``, ``DOUBLE_C``} ⇒
          ``family-RECT`` / ``family-TRAPEZOID`` / ``family-DOUBLE_C``；
        * ``family_code == 0`` 且 ``pdms_spec_path == /USER_UT-SPEC/UT_Profile`` ⇒ ``family-19``；
        * 有效 ``Kind == 303`` ⇒ ``kind-303-slot27`` + ``kind-303-slot32``（取值规则是【推断-中】），
          串长 > 12 ⇒ 再加 ``kind-303-packed-capacity``，串有 2 个尺寸（矩形管）⇒ 再加
          ``kind-303-slot20-rect``；
        * 有效 ``Kind == 26`` 且族码 ≠ 39 ⇒ ``kind-26-slot-order``；
        * 有效 ``Kind == 2`` ⇒ ``kind-2``。
        """
        out: List[Tuple[str, SectionRec]] = []
        for r in self.recs:
            name = _name_leaf(r.pkpm_name)
            if int(r.family_code or 0) == 0 and name in ("RECT", "TRAPEZOID", "DOUBLE_C"):
                out.append(("family-" + name, r))
            if int(r.family_code or 0) == 0 and _norm_path(r.pdms_spec_path) == "/USER_UT-SPEC/UT_Profile":
                out.append(("family-19", r))
            for iid in unencodable_item_ids(effective_kind(r), r):
                if iid != "unknown-kind":
                    out.append((iid, r))
        return out
        return out

    # ---------------------------------------------------------------- 序列化
    def to_csv(self, bom: bool = True) -> str:
        """→ §k.2 的 15 列 CSV 文本（CRLF）。

        ``bom=True``（缺省）时返回值以 ``'\\ufeff'`` 开头，与 §k.2 的冻结文件**逐字节一致**：
        ``t.to_csv().encode('utf-8') == open('engine/section_table.csv','rb').read()``。
        """
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, lineterminator="\r\n")
        w.writeheader()
        for r in self.recs:
            w.writerow({
                "key": r.key,
                "pkpm_name": r.pkpm_name,
                "family_code": int(r.family_code or 0),
                "family_name_cn": r.family_name_cn,
                "kind": int(r.kind or 0),
                "shapeval": r.shapeval,
                "dims_json": _json_dumps(r.dims or {}),
                "mat": int(r.mat or 0),
                "pdms_spec_path": r.pdms_spec_path,
                "pdms_catalogue": r.pdms_catalogue,
                "is_parametric": "true" if r.is_parametric else "false",
                "params_json": _json_dumps([p.to_dict() for p in r.params]),
                "confidence": r.confidence,
                "source": r.source,
                "extra_json": _json_dumps(r.extra or {}),
            })
        text = buf.getvalue()
        return ("\ufeff" + text) if bom else text

    @classmethod
    def from_csv(cls, text_or_path: Any) -> "SectionTable":
        """读 §k.2 的表（``utf-8-sig``，兼容无 BOM）；入参可以是文本或路径。"""
        text = _read_text_or_path(text_or_path, encoding="utf-8-sig")
        if text.startswith("\ufeff"):
            text = text[1:]
        rows = list(csv.DictReader(io.StringIO(text)))
        recs: List[SectionRec] = []
        for row in rows:
            dims = json.loads(row.get("dims_json") or "{}")
            params = json.loads(row.get("params_json") or "[]")
            extra = json.loads(row.get("extra_json") or "{}")
            name = (row.get("pkpm_name") or "").strip()
            path = (row.get("pdms_spec_path") or "").strip()
            recs.append(SectionRec(
                key=(row.get("key") or "").strip() or name or path,
                pkpm_name=name,
                family_code=int(float(row.get("family_code") or 0)),
                family_name_cn=row.get("family_name_cn") or "",
                kind=int(float(row.get("kind") or 0)),
                shapeval=(row.get("shapeval") or "").strip(),
                dims=dims,
                mat=int(float(row.get("mat") or 0)),
                pdms_spec_path=path,
                pdms_catalogue=(row.get("pdms_catalogue") or "").strip(),
                is_parametric=(row.get("is_parametric") or "").strip().lower() == "true",
                params=[ParamDef.from_dict(x) for x in (params or [])],
                confidence=(row.get("confidence") or "").strip(),
                source=(row.get("source") or "").strip(),
                extra=extra,
            ))
        src = "" if ("\n" in str(text_or_path)) else str(text_or_path)
        return cls(recs, source=src)

    def to_json(self) -> str:
        """确定性 JSON（``ensure_ascii=False`` + ``sort_keys`` + 紧凑分隔符）。"""
        return _json_dumps({"schema": TABLE_SCHEMA, "recs": [r.to_dict() for r in self.recs]})

    @classmethod
    def from_json(cls, text_or_path: Any) -> "SectionTable":
        """还原 :meth:`to_json` 的结果；也接受**裸列表**。"""
        raw = _read_text_or_path(text_or_path, encoding="utf-8-sig")
        d = json.loads(raw)
        items = d.get("recs") if isinstance(d, dict) else d
        return cls([SectionRec.from_dict(x) for x in (items or [])])

    # ---------------------------------------------------------------- 校验
    def validate(self) -> List[str]:
        """问题清单（空 = 通过）。

        * ``E-`` **硬问题**：空键/重复键、空规格路径、非法 ``confidence``、
          ``confidence='unknown'`` 却缺 ``extra['reason']``、``desp_index`` 与
          ``is_parametric`` 不符、重复的 ``pkpm_name`` / ``pdms_spec_path``；
        * ``W-`` **数据缺口**（不阻断，属已知现状）：族码未解、无 ``shapeval``、无 ``dims``、
          右值不在目录宏里（256 条已知）、触到未解码项的行。

        **只读**：本方法不改写任何记录（§k.2：``sectionlib`` 只读内置表）。
        """
        out: List[str] = []
        seen_key: Dict[str, int] = {}
        seen_name: Dict[str, int] = {}
        seen_path: Dict[str, int] = {}
        for i, r in enumerate(self.recs):
            where = "rec[%d]" % i
            if not r.key:
                out.append("E-KEY-EMPTY %s" % where)
            elif r.key in seen_key:
                out.append("E-KEY-DUP %s key=%r 与 rec[%d] 重复" % (where, r.key, seen_key[r.key]))
            else:
                seen_key[r.key] = i
            if not r.pdms_spec_path:
                out.append("E-SPEC-EMPTY %s key=%r 无 pdms_spec_path" % (where, r.key))
            elif r.pdms_spec_path in seen_path:
                out.append("E-SPEC-DUP %s key=%r 规格路径与 rec[%d] 重复"
                           % (where, r.key, seen_path[r.pdms_spec_path]))
            else:
                seen_path[r.pdms_spec_path] = i
            if r.pkpm_name:
                if r.pkpm_name != r.pkpm_name.strip():
                    out.append("W-NAME-WS %s key=%r pkpm_name 含首尾空白" % (where, r.key))
                if r.pkpm_name.startswith("/"):
                    out.append("W-NAME-SLASH %s key=%r pkpm_name 以 '/' 开头（§k.1/§k.2："
                               "pkpm_name 与 pdms_spec_path 取值域不相交、名字不以 / 开头）——"
                               "本模块按叶子名解析，但请上游修正（本次集成实测 engine/dbparse.py:946 "
                               "对 secmap.reverse() 的结果又做了一次路径归一化）" % (where, r.key))
                if r.pkpm_name in seen_name:
                    out.append("E-NAME-DUP %s key=%r pkpm_name 与 rec[%d] 重复"
                               % (where, r.key, seen_name[r.pkpm_name]))
                else:
                    seen_name[r.pkpm_name] = i
            if r.confidence not in CONFIDENCE_LEVELS:
                out.append("E-CONF-VOCAB %s key=%r confidence=%r 不在 %s"
                           % (where, r.key, r.confidence, list(CONFIDENCE_LEVELS)))
            if r.confidence == "unknown" and not (r.extra or {}).get("reason"):
                out.append("E-CONF-REASON %s key=%r confidence='unknown' 但缺 extra['reason']"
                           % (where, r.key))
            if int(r.mat or 0) not in (0, 5, 6):
                out.append("W-MAT %s key=%r mat=%r 不在 {0,5,6}" % (where, r.key, r.mat))
            for p in r.params:
                if r.is_parametric and p.desp_index < 1:
                    out.append("E-DESP-IDX %s key=%r 参数 %r 的 desp_index=%r（参数化族必须 ≥1）"
                               % (where, r.key, p.name, p.desp_index))
                if (not r.is_parametric) and p.desp_index != 0:
                    out.append("E-DESP-IDX %s key=%r 参数 %r 的 desp_index=%r（非参数化族必须 0）"
                               % (where, r.key, p.name, p.desp_index))
            if not r.shapeval and not r.dims:
                out.append("W-SEC-NOIDENT %s key=%r 既无 shapeval 也无 dims" % (where, r.key))
            elif not r.shapeval:
                out.append("W-NO-SHAPEVAL %s key=%r 无 PKPM 编码串（family_code=%r）"
                           % (where, r.key, r.family_code))
            if str((r.extra or {}).get("in_pdms_macro", "x")) == "":
                out.append("W-NOT-IN-MACRO %s key=%r 右值不在目录宏的 SPCOMPONENT 集合里"
                           "（§k.2 已知 256 条 Double-L 缩写不一致）" % (where, r.key))
            for iid in r.unknown_item_ids:
                if iid not in UNKNOWN_ITEM_IDS:
                    out.append("E-UNKNOWN-ID %s key=%r 引用了未登记的未解码项 id %r"
                               % (where, r.key, iid))
        agg: Dict[str, int] = {}
        for iid, r in self.unknown_rows():
            agg[iid] = agg.get(iid, 0) + 1
        for iid in sorted(agg):
            it = _unknown_item(iid)
            out.append("W-UNKNOWN-ITEM %s × %d 行：%s —— 怎么确认：%s"
                       % (iid, agg[iid], it["subject"], it["how_to_confirm"]))
        return out
    # ---------------------------------------------------------------- 损失申报
    def loss_report(self, direction: str) -> List[Dict[str, str]]:
        """§k.5：``direction ∈ {'jwd2db','db2jwd','pdt2db','db2pdt'}`` → 冻结清单（副本）。"""
        return loss_items(direction)

    # ---------------------------------------------------------------- 生成 .jwd 截面
    def to_jwd_sections(self, tables: Optional[Sequence[str]] = None,
                        report: Optional[Dict[str, Any]] = None) -> Dict[str, List[Section]]:
        """→ ``{"beam":[Section,…],"col":[…],"brace":[…]}`（§k.1 / §l.6，canonical 对象）。

        规则（**逐条有出处，不猜**）：

        1. **可反算的族**（§l.6）：族码 39 → ``Kind=26``；族码 77 → ``Kind=303``；
           ``RECT``/``CIRCLE`` 两个模板族 → ``Kind=1``/``Kind=3``（缺尺寸时用
           :data:`RECT_TEMPLATE_DEFAULT_BH` / :data:`CIRCLE_TEMPLATE_DEFAULT_D` 的 DTSET 默认值，
           并在 ``Section.note`` 与 ``report['unknown']`` 里标记 ``confidence='unknown'``）。
           其余族（31/32/33/36/37/38/40/66/71/72/73 与 Kind=2）⇒ **跳过 + 报告**（``unencodable``）。
        2. **回算后自校验**：对每条产出的 ``ShapeVal`` 立刻 :func:`decode_shapeval` 复算一次，
           两次 ``dims`` 不一致 ⇒ 视为失败，进 ``report['skipped']``（不允许悄悄发出）。
        3. **分组**：目录里**没有**构件类别信息（``.jwd`` 的三张截面表是 PKPM 侧用法，PDMS 不记）。
           分组按样本实证的 :data:`JWD_TABLE_BY_KIND`；``kind`` 推不出时（0）⇒ 三个组都放
           （不分类、不丢、不猜），并在 ``report['group_basis']`` 里标 ``'no-evidence'``。
        4. ``Section.id``：优先 ``extra['jwd_id']``，否则从 `max(已知 jwd_id)+1` 起顺序发号
           （批内唯一；避免与样本 ID 相撞）。``Section.no`` 是组内 1..n 的序号。

        :param tables: ``None`` ⇒ 三个组都要；给 ``('beam',)`` 等可只取需要的组（**契约冻结的
            零参调用行为不变**）。
        :param report: 可选输出字典，函数写入
            ``skipped``/``unknown``/``tables``/``id_base``/``group_basis``/``unknown_items``；
            CLI 可直接并入 ``report.json`` 的 ``db.closure``（§l.6 闭环判据 3）。

        :returns: **恰好** ``beam``/``col``/``brace`` 三个键（与 §k.1 的冻结返回类型一致）。
        """
        want = tuple(tables) if tables else ("beam", "col", "brace")
        for t in want:
            if t not in ("beam", "col", "brace"):
                raise ValueError("tables 只能取 beam/col/brace，收到 %r" % (t,))
        out: Dict[str, List[Section]] = {t: [] for t in ("beam", "col", "brace")}
        skipped: List[Dict[str, Any]] = []
        unknown: List[Dict[str, Any]] = []
        group_basis: Dict[str, str] = {}

        known_ids = [int(r.extra.get("jwd_id")) for r in self.recs
                     if str(r.extra.get("jwd_id") or "").strip().isdigit()]
        next_id = (max(known_ids) + 1) if known_ids else 1
        seq = 0
        for r in self.recs:
            rec = r.copy()
            kind0 = effective_kind(rec)
            templated = ""
            if kind0 == 0 and _name_leaf(rec.pkpm_name) == TEMPLATE_RECT_KEY:
                # §l.6：RECT 族"仅模板" —— Kind=1 + DTSET DPRO 默认值（500/500）
                rec.kind = 1
                rec.dims = dict(rec.dims or {})
                rec.dims.setdefault("B", RECT_TEMPLATE_DEFAULT_BH[0])
                rec.dims.setdefault("H", RECT_TEMPLATE_DEFAULT_BH[1])
                templated = "RECT"
            elif effective_kind(rec) == 3 and _num((rec.dims or {}).get("d")) is None:
                # §l.6：CIRCLE 族"仅模板" —— Kind=3 + DPRO（300）
                rec.dims = dict(rec.dims or {})
                rec.dims.setdefault("d", CIRCLE_TEMPLATE_DEFAULT_D)
                templated = "CIRCLE"
            kind = output_kind(rec)
            sid = int(rec.extra.get("jwd_id") or 0)
            if not sid:
                sid = next_id
                next_id += 1
            try:
                sv = encode_shapeval(rec, sec_id=sid, mat=int(rec.mat or 0) or None)
            except ValueError as e:
                ids = _unencodable_items(kind, rec)
                skipped.append({
                    "what": "section-shapeval",
                    "key": rec.key,
                    "pkpm_name": rec.pkpm_name,
                    "kind": kind,
                    "family_code": int(rec.family_code or 0),
                    "spec_path": rec.pdms_spec_path,
                    "why": str(e),
                    "unknown_items": ids,
                })
                continue
            try:
                back = decode_shapeval(kind, sv)
            except ValueError as e:                       # 自校验：回算必须自洽
                skipped.append({
                    "what": "section-shapeval-roundtrip",
                    "key": rec.key, "pkpm_name": rec.pkpm_name, "kind": kind,
                    "family_code": int(rec.family_code or 0),
                    "spec_path": rec.pdms_spec_path,
                    "why": "回算结果无法解码：%s" % e,
                    "unknown_items": _unencodable_items(kind, rec),
                })
                continue
            # 规则 2 的自校验：把编码结果**再编一次**，两次 decode 必须逐键相同
            # （比的是编解码器自己的键空间，避免把"目录宏具名参数"与"§a.4 的 dims 键"混为一谈）
            rec_out = SectionRec(key=rec.key, pkpm_name=rec.pkpm_name, kind=kind,
                                 family_code=int(rec.family_code or 0), dims=back,
                                 mat=rec.mat, shapeval=sv)
            try:
                sv2 = encode_shapeval(rec_out, sec_id=sid, mat=int(rec.mat or 0) or None)
                back2 = decode_shapeval(kind, sv2)
            except ValueError as e:
                skipped.append({
                    "what": "section-shapeval-roundtrip",
                    "key": rec.key, "pkpm_name": rec.pkpm_name, "kind": kind,
                    "family_code": int(rec.family_code or 0),
                    "spec_path": rec.pdms_spec_path,
                    "why": "回算结果二次编码失败：%s" % e,
                    "unknown_items": _unencodable_items(kind, rec),
                })
                continue
            if not (sv2 == sv and _dims_equal(back, back2)):
                skipped.append({
                    "what": "section-shapeval-roundtrip",
                    "key": rec.key, "pkpm_name": rec.pkpm_name, "kind": kind,
                    "family_code": int(rec.family_code or 0),
                    "spec_path": rec.pdms_spec_path,
                    "why": "decode→encode→decode 不一致：%r → %r（串一致=%s）"
                           % (back, back2, sv2 == sv),
                    "unknown_items": _unencodable_items(kind, rec),
                })
                continue

            note = []
            ids = _unencodable_items(kind, rec)
            if kind == 1:
                note.append("Kind=1 的 B/H 先后为【推断-中】（jwd_format.md §9.3#4，§12#3）")
            if kind == 3:
                note.append("Kind=3 的族别是 inferred（圆形，§e.3/§12#5）")
            if kind == 26:
                note.append("Kind=26 只支持族码 39；尺寸槽按 (H,B,tf,tw)（§12#19）")
            if kind == 303:
                note.append("Kind=303 的槽 27/32 按规则推（§12#20）；"
                            "槽值见 UNKNOWN_DECODE_ITEMS")
                if "kind-303-slot20-rect" in ids:
                    r = ("矩形管（串 %r 有两个尺寸）：槽 20 按 §a.4/§k.3 的冻结写法**沿用 d**"
                         "（= %s），未观测项 kind-303-slot20-rect ⇒ 若 PKPM 用槽 18/20 建截面，"
                         "回读会变成方形；确认途径见 UNKNOWN_DECODE_ITEMS"
                         % (spec_str_of(rec), primary_dim_of(rec)))
                    note.append(r)
                    unknown.append({"key": rec.key, "spec_path": rec.pdms_spec_path,
                                    "confidence": "unknown", "reason": r,
                                    "unknown_items": ["kind-303-slot20-rect"]})
            if templated:
                conf = "unknown"
                vals = ("B=500 / H=500" if templated == "RECT" else "d=300")
                reason = ("%s 族在内置表里只是**模板行**（无具体尺寸）⇒ 按 §l.6 只出模板："
                          "尺寸取目录宏 DTSET 的 DPRO 默认值（%s）。族码值本身未解 ⇒ "
                          "confidence=unknown；确认途径见 UNKNOWN_DECODE_ITEMS"
                          % (templated, vals))
                note.append(reason)
                unknown.append({"key": rec.key, "spec_path": rec.pdms_spec_path,
                                "confidence": "unknown", "reason": reason,
                                "unknown_items": [_templated_item_id(templated)]})
            sec = Section(id=sid, kind=kind, mat=int(rec.mat or 0), name=rec.pkpm_name,
                          dims=dict(rec.dims or {}), table="", no=0, shapeval=sv,
                          params=[], note="；".join(note))
            for t in group_tables_of(kind):
                if t not in want:
                    continue
                seq += 1
                s2 = Section(id=sid, kind=kind, mat=int(rec.mat or 0), name=rec.pkpm_name,
                             dims=dict(rec.dims or {}), table=t, no=seq, shapeval=sv,
                             params=[], note=sec.note)
                out[t].append(s2)
                group_basis.setdefault(t, "kind=%d" % kind)
        if report is not None:
            report.setdefault("skipped", []).extend(skipped)
            report.setdefault("unknown", []).extend(unknown)
            report.setdefault("tables", {}).update({t: len(out[t]) for t in out})
            report["id_base"] = (max(known_ids) + 1) if known_ids else 1
            report.setdefault("group_basis", {}).update(group_basis)
            report.setdefault("unknown_items", []).append(
                "族 31/32/33/36/37/38/40/66/71/72/73（Kind=26 族码 ≠ 39）与 Kind=2 不可生成"
                "（§12#19/#18）⇒ 已逐条列入 skipped")
            bad_names = [r.key for r in self.recs if (r.pkpm_name or "").startswith("/")]
            if bad_names:
                report.setdefault("warnings", []).append(
                    "%d 条记录的 pkpm_name 以 '/' 开头（§k.1/§k.2：pkpm_name 不以 '/' 开头）；"
                    "本模块按**叶子名**解析（能正确推出规格串/库族码），但写出的 NAME 仍是原值 —— "
                    "请上游修正（本次集成实测 engine/dbparse.py 的 secmap.reverse 结果被路径归一化）。"
                    "样例：%s" % (len(bad_names), bad_names[:3]))
        return out


#: ``.jwd`` 三张截面表的**分组依据**（样本实证；``.jwd`` 的三张表是 PKPM 侧用法，PDMS 不记）
#:   * ``Kind=1`` → 样本 12 条在 ``pkpmBeamSect``、2 条在 ``pkpmColSect``
#:   * ``Kind=2/26`` → 样本 10 条全在 ``pkpmBeamSect``
#:   * ``Kind=3`` → 样本 1 条在 ``pkpmBraceSect``
#:   * ``Kind=303`` → 样本 2 条在 ``pkpmColSect``、1 条在 ``pkpmBraceSect``
#:   * 其余/未知 ⇒ 三组都放（**没有证据就不分类**）
JWD_TABLE_BY_KIND: Dict[int, Tuple[str, ...]] = {
    1: ("beam", "col"),
    2: ("beam",),
    3: ("brace",),
    26: ("beam",),
    303: ("col", "brace"),
}


def group_tables_of(kind: int) -> Tuple[str, ...]:
    """:data:`JWD_TABLE_BY_KIND` 的查询（未登记的 kind ⇒ 三组都放，见 ``to_jwd_sections`` 规则 3）。"""
    return JWD_TABLE_BY_KIND.get(int(kind or 0), ("beam", "col", "brace"))


def _templated_item_id(name: str) -> str:
    return "family-" + name if name in ("RECT", "TRAPEZOID", "DOUBLE_C") else "family-19"


# --------------------------------------------------------------------------
# §k.1 模块级装载
# --------------------------------------------------------------------------

_BUILTIN_CACHE: List[Any] = []           # [(key, SectionTable)]


def load_builtin_table(path: Optional[str] = None) -> SectionTable:
    """读 ``engine/section_table.csv``（§k.2 冻结数据文件，**只读**）。

    * 编码 ``utf-8-sig``（带/不带 BOM 都接受）、CRLF；
    * 结果按 ``(绝对路径, mtime, size)`` 缓存（同一进程内只解析一次）；
      **调用方不得修改返回对象的记录**（``to_jwd_sections`` 会自行 ``copy()``）。
    """
    p = os.path.abspath(path or BUILTIN_TABLE)
    if not os.path.exists(p):
        raise FileNotFoundError("内置转化表不存在：%s（见 §k.2）" % p)
    key = (p, os.path.getmtime(p), os.path.getsize(p))
    if _BUILTIN_CACHE and _BUILTIN_CACHE[0][0] == key:
        return _BUILTIN_CACHE[0][1]
    table = SectionTable.from_csv(p)
    _BUILTIN_CACHE[:] = [(key, table)]
    return table


def verify_builtin_table(path: Optional[str] = None,
                         meta_path: Optional[str] = None) -> List[str]:
    """拿 ``section_table.meta.json`` 核对内置表（计划 §9.4-14 的验收项）。

    返回问题清单（空 = 通过）：行数、列序、**去 BOM 后的 sha256**、编码/换行。
    """
    p = os.path.abspath(path or BUILTIN_TABLE)
    mp = os.path.abspath(meta_path or BUILTIN_META)
    out: List[str] = []
    raw = open(p, "rb").read()
    if raw[:3] != b"\xef\xbb\xbf":
        out.append("E-BOM %s 无 UTF-8 BOM（§k.2 冻结为带 BOM）" % p)
    text = raw.decode("utf-8-sig")
    if text.count("\n") != text.count("\r\n"):
        out.append("E-EOL %s 含孤立 LF（§k.2 冻结为 CRLF）" % p)
    if not os.path.exists(mp):
        out.append("E-META 缺少 %s" % mp)
        return out
    meta = json.load(open(mp, encoding="utf-8"))
    rows = list(csv.DictReader(io.StringIO(text)))
    if len(rows) != int(meta.get("output_rows", -1)):
        out.append("E-ROWS 行数 %d != meta.output_rows %s" % (len(rows), meta.get("output_rows")))
    if list(rows[0].keys()) != CSV_COLUMNS:
        out.append("E-COLS 列序与 §k.2 的 15 列不符：%r" % (list(rows[0].keys()),))
    if meta.get("output_columns") != CSV_COLUMNS:
        out.append("E-COLS-META meta.output_columns 与 §k.2 不符")
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if sha != meta.get("output_sha256_no_bom"):
        out.append("E-SHA 去 BOM 后的 sha256 %s != meta %s" % (sha, meta.get("output_sha256_no_bom")))
    t = load_builtin_table(p)
    if t.to_csv().encode("utf-8") != raw:
        out.append("E-CSV-TEXT SectionTable.to_csv() 与文件字节不一致（序列化不对称）")
    return out


# --------------------------------------------------------------------------
# §k.3 编解码四件套 —— ShapeVal（.jwd）
# --------------------------------------------------------------------------

#: Kind → ``dims`` 的键序（§a.4 的冻结表；诊断/打印用）
KIND_DIMS_KEYS: Dict[int, Tuple[str, ...]] = {
    1: ("B", "H"),
    2: ("Tw", "H", "B1", "T1", "B2", "T2"),
    3: ("d",),
    26: ("family", "subtype", "H", "B", "tf", "tw"),
    303: ("family", "spec_str", "d", "b", "lib_family"),
}


def decode_shapeval(kind: int, shapeval: str) -> Dict[str, Any]:
    """``ShapeVal`` → ``dims``（**§a.4 的唯一实现**，其它模块不得另写一份）。

    语法（``jwd_format.md`` §3.1【事实】）::

        "<Kind>, <p1>, ..., <pN>, <Mat>, <本行 ID>,"     # 末尾恒有一个逗号

    步骤：按逗号切 → 去掉尾部空串 → 校验首字段 == ``kind`` → ``body = parts[1:-2]``。
    ``body`` 的**下标从 0 起**（== ``split`` 下标 − 1），与 §a.4 的写法一致。

    Kind → ``dims``（键与类型）：

    * ``1``：``{"B": float, "H": float}`` —— B/H **先后为【推断-中】**（§12#3）
    * ``2``：``{"Tw","H","B1","T1","B2","T2"}`` —— 值集合【推断-高】，**B/T 交错序【未知】**（§9.3#5）
    * ``3``：``{"d": float}`` —— 族别见 §e.3/§12#5（inferred：圆形）
    * ``26``：``{"family":int,"subtype":int,"H","B","tf","tw"}``；族码 39 的字段分配由 7/8 截面独立验证
    * ``303``：``{"family":int,"spec_str":str,"d":float,"b":float,"lib_family":int}``
      —— 槽位：``body[0]``=族码(77)、``body[1..6]``=打包 ASCII 规格串（每槽 2 字符、低字节在前、
      遇 ``0x00`` 截断）、``body[17]``=d、``body[19]``=b、``body[26]``=库族码、``body[29]``=Mat、
      ``body[31]``=形状码（未解码项 ``kind-303-slot32``）

    :raises ValueError: ``ShapeVal`` 为空 / 字段数不足 / 首字段与 ``kind`` 不符 /
        ``Kind=303`` 的打包串不是 ASCII。**不返回"猜的"缺省值**。
        契约 §a.4 之外（键表未冻结）的 ``kind`` ⇒ 返回 ``{}``（调用方**必须**记 unknown，见
        :func:`table_from_jwd`），这不是"空截面"。
    """
    sv = str(shapeval or "").strip()
    if not sv:
        raise ValueError("decode_shapeval: ShapeVal 为空")
    parts = [t.strip() for t in sv.split(",")]
    while parts and parts[-1] == "":
        parts.pop()
    if len(parts) < 3:
        raise ValueError("decode_shapeval: 字段数 < 3（%r）" % shapeval)
    try:
        head = int(float(parts[0]))
    except (TypeError, ValueError):
        raise ValueError("decode_shapeval: 首字段不是整数（%r）" % parts[0])
    k = int(kind)
    if head != k:
        raise ValueError("decode_shapeval: ShapeVal 首字段 %d != Kind %d（%r）" % (head, k, shapeval))
    body = parts[1:-2]                                   # §a.4：去掉首字段(Kind) 与尾部 (Mat, 自身ID)

    def need(n: int, what: str) -> None:
        if len(body) < n:
            raise ValueError("decode_shapeval: Kind=%d 的 %s 需要 body 至少 %d 项，实为 %d（%r）"
                             % (k, what, n, len(body), shapeval))

    if k == 1:
        need(2, "B/H")
        return {"B": float(_num(body[0])), "H": float(_num(body[1]))}
    if k == 2:
        need(6, "Tw,H,B1,T1,B2,T2")
        return {"Tw": _num(body[0]), "H": _num(body[1]), "B1": _num(body[2]),
                "T1": _num(body[3]), "B2": _num(body[4]), "T2": _num(body[5])}
    if k == 3:
        need(1, "d")
        return {"d": float(_num(body[0]))}
    if k == 26:
        need(7, "族码/子类型/H/B/tf/tw")
        return {"family": int(_num(body[0])), "subtype": int(_num(body[1])),
                "H": _num(body[2]), "B": _num(body[4]),
                "tf": _num(body[5]), "tw": _num(body[6])}
    if k == 303:
        need(32, "族码/打包串/尺寸槽")
        buf = bytearray()
        for t in body[1:7]:
            v = int(_num(t) or 0) & 0xFFFF
            buf.append(v & 0xFF)
            buf.append((v >> 8) & 0xFF)
        packed = bytes(buf).split(b"\x00")[0]
        try:
            spec = packed.decode("ascii")
        except UnicodeDecodeError:
            raise ValueError("decode_shapeval: Kind=303 的槽 2..7 不是 ASCII 规格串（%r）"
                             % buf.hex())
        return {"family": int(_num(body[0])), "spec_str": spec,
                "d": float(_num(body[17])), "b": float(_num(body[19])),
                "lib_family": int(_num(body[26]))}
    return {}


def effective_kind(rec: SectionRec) -> int:
    """:attr:`SectionRec.kind` 为 0（内置表未记）时，由族码推出的 ``.jwd`` Kind。

    * 族码 ``77`` → ``303``（3 条样本实证 ``303,77,…``）
    * 族码 ∈ :data:`STEEL_LIB_FAMILIES` → ``26``（型钢库包装；族码放在第 2 字段）
    * 族码 ∈ :data:`PARAM_FAMILIES` → 族码本身（``.pdt`` 的 ``SHAPE=KIND=族码``，§4.5）
    * 其它 → ``0``（**推不出来，调用方必须当 unknown 处理**）
    """
    if int(rec.kind or 0):
        return int(rec.kind)
    fam = int(rec.family_code or 0)
    if not fam:
        return 0
    if fam == FAMILY_KIND_303:
        return 303
    if fam in STEEL_LIB_FAMILIES:
        return FAMILY_KIND_26
    if fam in PARAM_FAMILIES:
        return fam
    return 0


def output_kind(rec: SectionRec) -> int:
    """:func:`encode_shapeval` **实际写出**的 ``Kind``。

    ``.pdt`` 的 ``SHAPE=KIND=39``（族码直接充当 SHAPE）在 ``.jwd`` 侧必须落成 ``Kind=26`` 的
    "型钢库引用"包装（§l.6：族码 39 → ``Kind=26``；``jwd_format.md`` §4.5 的【推断】）
    ⇒ 输入 39 时输出 26；其余原样。
    """
    k = effective_kind(rec)
    return FAMILY_KIND_26 if k == 39 else k


def family_of(rec: SectionRec) -> int:
    """记录的有效族码：``family_code`` 优先；``.pdt`` 的 ``Kind=39`` ⇒ 39；其次 ``dims['family']``。"""
    fam = int(rec.family_code or 0)
    if fam:
        return fam
    if int(rec.kind or 0) == 39:          # .pdt 的 SHAPE=KIND=39 就是族码（§4.5）
        return 39
    return int(_num((rec.dims or {}).get("family")) or 0)


#: 兼容内部旧名（模块内仍按私有名调用，语义与 :func:`family_of` 一致）
_family_of = family_of


def unencodable_item_ids(kind: int, rec: SectionRec) -> List[str]:
    """某记录在**回算**时触到的未解码项 id（供报告逐条留痕；就是 :data:`UNKNOWN_DECODE_ITEMS` 的 id）。"""
    out: List[str] = []
    if kind == 303:
        out += ["kind-303-slot27", "kind-303-slot32"]
        if len(spec_str_of(rec)) > _PACKED_CHARS:
            out.append("kind-303-packed-capacity")
        if _spec_dims(spec_str_of(rec))[1] is not None:
            out.append("kind-303-slot20-rect")
    if kind == 26 and family_of(rec) != 39:
        out.append("kind-26-slot-order")
    if kind == 2:
        out.append("kind-2")
    fam = family_of(rec)
    if fam == 0 and _name_leaf(rec.pkpm_name) in ("RECT", "TRAPEZOID", "DOUBLE_C"):
        out.append("family-" + _name_leaf(rec.pkpm_name))
    if kind == 0:
        if fam == 19:
            out.append("family-19")
        elif not out:
            out.append("unknown-kind")
    return out


_unencodable_items = unencodable_item_ids


_RE_NUM = re.compile(r"[0-9]+(?:\.[0-9]+)?")


def _spec_dims(spec: str) -> Tuple[Optional[Any], Optional[Any], Optional[Any]]:
    """规格串的数字部分 → ``(第 1 个数, 第 2 个数|None, 最后 1 个数)``。

    串格式（``jwd_format.md`` §3.2 第 3 点【事实】）：``B<边长>*<壁厚>``（方管）、
    ``B<a>*<b>*<壁厚>``（矩形管）、``D<直径>X<壁厚>``（圆管）。内置表 77 族 **1,199 行全部**
    满足"第 1 个数 == ``dims['d']``（无 ``d`` 时为 ``dims['H']``）、第 2 个数 == ``dims['B']``、
    末个数 == ``dims['t']``"（本次自检实测 0 处不符）⇒ 这里的解析是**数据互证过的**，不是猜。
    """
    ns = _RE_NUM.findall(str(spec or ""))
    if not ns:
        return None, None, None
    n1 = _num(ns[0])
    n2 = _num(ns[1]) if len(ns) > 1 else None
    return n1, n2, _num(ns[-1])


def primary_dim_of(rec: SectionRec) -> Any:
    """``Kind=303`` 的**主尺寸**（槽 18）：``dims['d']``，缺失时取 ``dims['H']``。

    证据：内置表 77 族 1,199 行里，规格串第 1 个数与 ``dims['d']``（有 ``d`` 时）/``dims['H']``
    （矩形管、无 ``d`` 时）**逐行相等**（本次自检 0 处不符）；矩形管的 DTSET 具名参数是
    ``h(mm)``/``b(mm)``（没有 ``d``），故这不是猜而是数据互证。
    """
    d = _num((rec.dims or {}).get("d"))
    if d is not None:
        return d
    return _num((rec.dims or {}).get("H"))


def _name_leaf(name: Any) -> str:
    """截面名的**叶子名**：去首尾空白、去前导 ``/``。

    §k.2 规定 ``pkpm_name`` 不以 ``/`` 开头（与 ``pdms_spec_path`` 取值域不相交）；但别的模块
    可能把**路径形态**的名字传进来（本次集成实测：``dbparse`` 对 ``secmap.reverse()`` 的结果
    又做了一次路径归一化 ⇒ ``pkpm_name='/6-B250*10.00'``）。这里只把名字当叶子名解析，
    **不修改记录本身**，也不改变任何语义。
    """
    return _norm_ws(name).lstrip("/")


def spec_str_of(rec: SectionRec) -> str:
    """``Kind=303`` 的规格串：``dims['spec_str']`` 优先，否则按 §l.6 从名去 ``<N>-`` 前缀
    （``6-B250*10.00`` → ``B250*10.00``；内置表的 1,199 条 77 族行都走这条路）。"""
    spec = (rec.dims or {}).get("spec_str")
    if spec:
        return str(spec)
    name = _name_leaf(rec.pkpm_name)
    if "-" in name:
        tail = name.split("-", 1)[1].strip()
        if tail:
            return tail
    return name


def lib_family_of(rec: SectionRec) -> int:
    """``Kind=303`` 的库族码（**槽 27**）：``dims['lib_family']`` 优先，否则按 §12#20 取规格名首数字前缀。"""
    v = _num((rec.dims or {}).get("lib_family"))
    if v is not None:
        return int(v)
    head = _name_leaf(rec.pkpm_name).split("-", 1)[0].strip()
    if head.isdigit():
        return int(head)
    return 0


def _dims_equal(a: Dict[str, Any], b: Dict[str, Any], keys: Optional[Sequence[str]] = None) -> bool:
    """dims 比较（只比双方都有的键；数值容差 1e-9）。用于回算自校验。"""
    if not a or not b:
        return False
    for k in (keys or sorted(set(a) | set(b))):
        if k not in a or k not in b:
            return False
        va, vb = a[k], b[k]
        na, nb = _num(va), _num(vb)
        if na is not None and nb is not None:
            if abs(float(na) - float(nb)) > 1e-9:
                return False
        elif str(va) != str(vb):
            return False
    return True


def encode_shapeval(rec: SectionRec, sec_id: int = 0, mat: Optional[int] = None) -> str:
    """``SectionRec`` → ``ShapeVal``（§k.3 的四种模板；其余 ⇒ ``ValueError('unencodable: …')``）。

    ``id`` = ``sec_id``（给定时）或 ``rec.extra['jwd_id']``；``mat`` 缺省用 ``rec.mat``。
    数值格式：整数写整数、小数用 ``repr(float)``；**末字段后保留 ``,``**（样本如此）。

    ======== ==================================================================================
    Kind     模板 / 前置条件
    ======== ==================================================================================
    ``1``    ``1,<B>,<H>,<mat>,<id>,``（``dims`` 有 ``B``/``H``）
    ``3``    ``3,<d>,<mat>,<id>,``（``dims`` 有 ``d``）
    ``26``   ``26,<family>,<subtype>,<H>,0,<B>,<tf>,<tw>,0,<mat>,<id>,`` —— **仅 ``family==39``**
    ``303``  ``303,77,<打包串 6 槽>,…,<d>,0,<d|b>,0,…<槽27>…,<mat>,…<槽32>…,-1,<id>,``
             （``dims`` 有 ``spec_str``/``d``/``lib_family``；``spec_str``/``lib_family`` 缺省时
             按 §l.6 从 ``pkpm_name`` 推 —— ``6-B250*10.00`` → ``B250*10.00`` / 6）
    ``其它``  **抛** ``ValueError("unencodable: …")``（不得降级成空串；调用方必须记报告）
    ======== ==================================================================================

    ``Kind=303`` 的槽位（``split`` 下标，本次 C12 实测 3/3 条样本）：
    ``0=303``、``1=77``、``2..7``=打包串（每槽 2 字符、低字节在前、遇 0 结束）、
    **``18``=d、``20``=d|b**、``27``=库族码、``30``=mat、``32``=形状码、``81``=``-1``、``82``=自身 ID，
    其余 0；末尾还有一个空字段 ⇒ ``split_len=84``。**矩形管**（``B<a>*<b>*<t>``）的槽 20 应为另一边长
    —— **未观测**（``kind-303-slot32``/本函数按 ``d`` 沿用），见 §12#20。
    """
    kind = effective_kind(rec)
    sid = int(sec_id) or int(rec.extra.get("jwd_id") or 0)
    m = int(rec.mat or 0) if mat is None else int(mat)
    d = rec.dims or {}

    def req(*names: str) -> Any:
        for n in names:
            if n in d and d[n] is not None and d[n] != "":
                return d[n]
        raise ValueError("unencodable: Kind=%d 缺 dims[%s]（key=%r）"
                         % (kind, "/".join(names), rec.key))

    if kind == 1:
        return "1,%s,%s,%d,%d," % (_num_str(req("B")), _num_str(req("H")), m, sid)
    if kind == 3:
        return "3,%s,%d,%d," % (_num_str(req("d")), m, sid)
    if kind in (26, 39):
        # kind==39 是 .pdt 侧的族码写法；.jwd 侧一律落成 Kind=26 包装（§l.6）
        fam = family_of(rec)
        if fam != 39:
            raise ValueError("unencodable: Kind=26 的族码 %s ≠ 39 —— 6 个尺寸槽的顺序未解"
                             "（UNKNOWN_DECODE_ITEMS['kind-26-slot-order']；§12#19）" % fam)
        sub = int(_num(d.get("subtype"), 1) or 1)
        return "26,39,%d,%s,0,%s,%s,%s,0,%d,%d," % (
            sub, _num_str(req("H")), _num_str(req("B")), _num_str(req("tf")),
            _num_str(req("tw")), m, sid)
    if kind == 303:
        spec = spec_str_of(rec)
        if not spec:
            raise ValueError("unencodable: Kind=303 缺 dims[spec_str]（key=%r）" % rec.key)
        try:
            packed = spec.encode("ascii")
        except UnicodeEncodeError:
            raise ValueError("unencodable: Kind=303 的规格串含非 ASCII（%r）" % spec)
        if len(packed) > _PACKED_CHARS:
            raise ValueError(
                "unencodable: Kind=303 的规格串 %d 字符 > %d（6 槽容量）—— 打包区的真实上限未观测，"
                "**不写截断串**（截断会静默产出错误截面）；见 "
                "UNKNOWN_DECODE_ITEMS['kind-303-packed-capacity']（key=%r）"
                % (len(packed), _PACKED_CHARS, rec.key))
        lib = lib_family_of(rec)
        if not lib:
            raise ValueError("unencodable: Kind=303 缺 dims[lib_family] 且名字无 <N>- 前缀（key=%r）"
                             % rec.key)
        # 槽 18 = 主尺寸 d：dims['d'] 优先，缺失时取 dims['H']（矩形管；内置表 1,199 行互证，见
        # :func:`primary_dim_of`）。槽 20 按 §a.4/§k.3 的**冻结写法**"沿用 d"，并把"矩形管时
        # 槽 20 应为另一边长"列为未解码项 kind-303-slot20-rect（不猜、不擅自改契约）。
        dv = _num((rec.dims or {}).get("d"))
        if dv is None:
            dv = primary_dim_of(rec)
        if dv is None:
            raise ValueError("unencodable: Kind=303 缺 dims[d]（也没有 dims[H] 可代；key=%r）"
                             % rec.key)
        slots = []
        for i in range(0, _PACKED_CHARS, 2):
            lo = packed[i] if i < len(packed) else 0
            hi = packed[i + 1] if i + 1 < len(packed) else 0
            slots.append(str(lo | (hi << 8)))
        body = ["0"] * 75                                   # 下标 8..82
        body[18 - 8] = _num_str(dv)
        body[20 - 8] = _num_str(dv)                         # §a.4：矩形管"沿用 d"（见 slot20-rect）
        body[27 - 8] = "%d" % lib
        body[30 - 8] = "%d" % m
        body[32 - 8] = "%d" % (SHAPE_CODE_RECT if lib >= SHAPE_CODE_RECT_MIN_LIB
                               else SHAPE_CODE_ROUND)
        body[81 - 8] = "-1"
        body[82 - 8] = "%d" % sid
        return ",".join(["303", "77"] + slots + body) + ","
    raise ValueError("unencodable: Kind=%s 没有 §k.3 的编码模板（UNKNOWN_DECODE_ITEMS：%s）"
                     % (kind, ",".join(_unencodable_items(kind, rec)) or "无"))


# --------------------------------------------------------------------------
# §k.3 编解码四件套 —— $DEFFRAMESECTION（.pdt）
# --------------------------------------------------------------------------

#: ``$DEFFRAMESECTION`` 的 5 行模板（逐字，来自样本 ``1_PM.pdt:2367-2371`` 与
#: DLL 格式串 ``0x033B1C/0x033B81/0x033C05/0x033C75/0x0202DB``；CONTRACT §j.4.7）
_DEFFRAME_TEMPLATES = (
    "    ID=%s, NAME=%s, SHAPE=%s",
    "       KIND=%s, B1=%s, B2=0, H1=%s, H2=0, B3=0, H3=0",
    "       T1=0, T2=0, T3=0, T4=0, T5=0, T6=0",
    "       M=%s, RI=0.000, RJ=0.000, UA=0.000, NAME1=%s",
    "       EXI=1, 10011, %s",
)

#: 每行需要消化的 KEY 名（解析用；行序不敏感）
_DEFFRAME_KEYS = (
    ("ID", "NAME", "SHAPE"),
    ("KIND", "B1", "B2", "H1", "H2", "B3", "H3"),
    ("T1", "T2", "T3", "T4", "T5", "T6"),
    ("M", "RI", "RJ", "UA", "NAME1"),
    ("EXI",),
)


def _defframe_shape(rec: SectionRec) -> int:
    """``SectionRec`` → ``$DEFFRAMESECTION`` 的 ``SHAPE``（= ``KIND``）。

    * ``Kind=1`` → ``1``；``Kind=3`` → ``3``；
    * ``Kind=39`` → ``39``（``.pdt`` 侧族码直接充当 SHAPE，``db_pkpm_sections.md`` §3.3【事实】）；
    * ``Kind=26`` 且族码 39 → ``39``（内置表的 ``HN450X200`` 走这条）；
    * 其余 ⇒ ``ValueError('unencodable: …')``（§j.7.1：调用方写占位块，见
      :func:`placeholder_defframesection`）。
    """
    kind = effective_kind(rec)
    if kind == 1:
        return 1
    if kind == 3:
        return 3
    if kind == 39:
        return 39
    if kind == 26 and _family_of(rec) == 39:
        return 39
    raise ValueError("unencodable: Kind=%s（族码 %s）不可回算到 $DEFFRAMESECTION"
                     "（§j.7.1/§k.3；UNKNOWN_DECODE_ITEMS：%s）"
                     % (kind, _family_of(rec), ",".join(_unencodable_items(kind, rec)) or "无"))


def placeholder_defframesection(rec: SectionRec, sec_id: int = 0,
                                mat: Optional[int] = None) -> List[str]:
    """**占位块**（§k.3 的"其它"行 / §j.7.1）：数值全 0、``M=<mat 或 5>``、
    ``NAME=<pkpm_name 或 "<kind>#<原样>" 或 "<kind>#">``、``SHAPE=<kind>``。

    ``encode_defframesection`` 对不可回算的截面**抛** ``unencodable``；调用方（``pdt_write``）
    捕获后用它写占位块并记 ``skipped``。数值一律 0 是"**不猜**"：占位块里不能出现编造的尺寸。
    """
    kind = effective_kind(rec)
    sid = int(sec_id) or int(rec.extra.get("pdt_id") or rec.extra.get("jwd_id") or 0)
    m = int(rec.mat or 0) if mat is None else int(mat)
    if m not in (5, 6):
        m = 5
    name = rec.pkpm_name or ("%d#" % kind)
    return [
        _DEFFRAME_TEMPLATES[0] % ("%d" % sid, name, "%d" % kind),
        _DEFFRAME_TEMPLATES[1] % ("%d" % kind, "0", "0"),
        _DEFFRAME_TEMPLATES[2],
        _DEFFRAME_TEMPLATES[3] % ("%d" % m, ""),
        _DEFFRAME_TEMPLATES[4] % ("%d" % sid),
    ]


def encode_defframesection(rec: SectionRec, sec_id: int = 0, mat: Optional[int] = None,
                           notes: Optional[List[str]] = None) -> List[str]:
    """``SectionRec`` → ``$DEFFRAMESECTION`` 的 **5 行**（§j.4.7 模板逐字；§k.3 的编码表）。

    ====================== ============================================================
    rec                    输出
    ====================== ============================================================
    ``Kind=1``             ``SHAPE=1``，``B1=B`` / ``H1=H``，``T1..T6=0``，``M=6``，``NAME1=``
    ``Kind=3``             ``SHAPE=3``，``B1=d`` / ``H1=0``，``T*=0``，``M=6``，``NAME1=``
    ``Kind=26`` 且族码 39  ``SHAPE=39``，``B1=B`` / ``H1=H``，``T*=0``，``M=mat(=5)``，``NAME1=pkpm_name``
    ``Kind=39``（.pdt 侧）  同上一行
    其它                   **抛** ``ValueError('unencodable: …')``（§j.7.1）
    ====================== ============================================================

    ``M`` 的规则（§12#17 / §0.4-10 修订）：**按 SHAPE 取**——``SHAPE=1/3 ⇒ M=6``、
    ``SHAPE=39 ⇒ M=mat``（5=钢）；``mat ∉ {5,6}`` ⇒ 写 5 并把 ``"unknown"`` 提示追加进
    ``notes``（给定时）。依据（样本 1_PM.pdt 的全部观测点）：SHAPE=1 的 29 条与 SHAPE=3 的
    1 条记录全部 ``M=6``（如 :2370 ``M=6``），SHAPE=39 的 2 条全部 ``M=5``（如 :2515）；
    旧规则（M=mat）会让目录宏模板的 SHAPE=1/3 行写 M=5，与样本全部观测相悖
    （R3 复核发现⑧：实测 db2pdt.pdt 的 M 分布 {5: 1845}，其中含 SHAPE=1/3）。
    ``RI/RJ/UA`` 恒 ``0.000``、``EXI=1, 10011, <id>``（样本 32/32 条如此；§k.5 的
    ``db2pdt`` 未知项）。
    """
    shape = _defframe_shape(rec)
    sid = int(sec_id) or int(rec.extra.get("pdt_id") or rec.extra.get("jwd_id") or 0)
    m = int(rec.mat or 0) if mat is None else int(mat)
    if shape in (1, 3):
        if m != 6 and notes is not None:
            notes.append("unknown: SHAPE=%d 按 §12#17/§0.4-10 写 M=6（样本 SHAPE=1/3 全部 "
                         "M=6；表内 mat=%r 未采用）" % (shape, mat))
        m = 6
    elif m not in (5, 6):
        if notes is not None:
            notes.append("unknown: mat=%r ∉ {5,6} ⇒ 按 §12#17 写 M=5（不猜钢号）" % (mat,))
        m = 5
    d = rec.dims or {}

    def req(*names: str) -> Any:
        for n in names:
            if n in d and d[n] is not None and d[n] != "":
                return d[n]
        raise ValueError("unencodable: Kind=%d/$DEFFRAMESECTION 缺 dims[%s]（key=%r）"
                         % (effective_kind(rec), "/".join(names), rec.key))

    if shape in (1, 39):
        b1, h1 = req("B", "B1"), req("H", "H1")
    else:                                     # shape == 3
        b1, h1 = req("d", "B1"), 0
    name1 = rec.pkpm_name if shape == 39 else ""
    return [
        _DEFFRAME_TEMPLATES[0] % ("%d" % sid, rec.pkpm_name, "%d" % shape),
        _DEFFRAME_TEMPLATES[1] % ("%d" % shape, _num_str(b1), _num_str(h1)),
        _DEFFRAME_TEMPLATES[2],
        _DEFFRAME_TEMPLATES[3] % ("%d" % m, name1),
        _DEFFRAME_TEMPLATES[4] % ("%d" % sid),
    ]


def decode_defframesection(block: Sequence[str]) -> Dict[str, Any]:
    """``$DEFFRAMESECTION`` 的 5 行 → 字段字典（§k.3）。

    返回键（固定）：``id, name, shape, kind, b1, b2, h1, h2, b3, h3, t1..t6,
    m, ri, rj, ua, name1, exi``。``exi`` 是整数列表（样本 ``EXI=1, 10011, <id>`` ⇒ ``[1, 10011, id]``）。
    数值一律 ``int``（样本里这 5 行全是整数，除 ``RI/RJ/UA`` 为 3 位小数 ⇒ 用 ``_num`` 归一）。

    **容错**（§k.3）：``KEY=value`` 的**顺序任意**、``RI/RJ/UA`` 的 3 位小数、``T1..T6`` 为 0、
    ``NAME1`` 为空、行尾空白随意、行数 ≥ 1 且每行可含多个 ``KEY=value``（逗号分隔）。

    :raises ValueError: 行数不是 5 / 缺 ``ID``/``NAME``/``SHAPE``/``KIND``。
    """
    lines = [str(x).rstrip() for x in (block or []) if str(x).strip()]
    if len(lines) != 5:
        raise ValueError("decode_defframesection: 期望 5 行，收到 %d 行" % len(lines))
    f: Dict[str, str] = {}
    for ln in lines:
        chunks = ln.split(",")
        i = 0
        while i < len(chunks):
            chunk = chunks[i]
            if "=" not in chunk:
                i += 1
                continue
            k, v = chunk.split("=", 1)
            k, v = k.strip(), v.strip()
            if k.upper() == "EXI":
                # ``EXI=1, 10011, <id>`` 是**位置字段**（不是 KEY=value 序列）：
                # 它后面的 token 没有 ``=``，必须一起吃掉（否则 exi 只剩第一个数）
                vals = [v]
                j = i + 1
                while j < len(chunks) and "=" not in chunks[j]:
                    t = chunks[j].strip()
                    if t:
                        vals.append(t)
                    j += 1
                f["EXI"] = ",".join(vals)
                i = j
                continue
            f[k] = v
            i += 1
    for must in ("ID", "NAME", "SHAPE", "KIND"):
        if must not in f:
            raise ValueError("decode_defframesection: 缺字段 %s（%r）" % (must, lines[:1]))
    exi = []
    for t in (f.get("EXI") or "").split(","):
        t = t.strip()
        if t:
            exi.append(int(_num(t) or 0))
    out: Dict[str, Any] = {
        "id": int(_num(f["ID"]) or 0),
        "name": f["NAME"],
        "shape": int(_num(f["SHAPE"]) or 0),
        "kind": int(_num(f["KIND"]) or 0),
    }
    for k in ("B1", "B2", "B3", "H1", "H2", "H3", "T1", "T2", "T3", "T4", "T5", "T6"):
        out[k.lower()] = int(_num(f.get(k)) or 0)
    for k in ("M",):
        out[k.lower()] = int(_num(f.get(k)) or 0)
    for k in ("RI", "RJ", "UA"):
        out[k.lower()] = float(_num(f.get(k)) or 0.0)
    out["name1"] = f.get("NAME1", "")
    out["exi"] = exi
    return out


def rec_from_defframesection(d: Dict[str, Any], table: str = "pdt") -> SectionRec:
    """:func:`decode_defframesection` 的字段字典 → :class:`SectionRec`（**decode→encode→decode** 的桥）。

    ``dims`` 按 ``SHAPE`` 落到 §a.4 的键空间：``1`` → ``{B,H}``；``3`` → ``{d}``；
    ``39`` → ``{B,H,family:39}``；其它 → **原字段名**（``B1``/``H1``…，因为族别未解 ⇒ 不换名）。
    ``extra`` 带上 ``pdt_id`` / ``pdt_name1`` / ``pdt_shape`` / ``pdt_m`` 与
    ``unknown_items``（形状未解时）。
    """
    shape = int(d.get("shape", 0) or 0)
    dims: Dict[str, Any] = {}
    ids: List[str] = []
    if shape == 1:
        dims = {"B": float(_num(d.get("b1"), 0.0)), "H": float(_num(d.get("h1"), 0.0))}
    elif shape == 3:
        dims = {"d": float(_num(d.get("b1"), 0.0))}
    elif shape == 39:
        dims = {"B": _num(d.get("b1"), 0), "H": _num(d.get("h1"), 0), "family": 39}
    else:
        for k in ("B1", "B2", "B3", "H1", "H2", "H3", "T1", "T2", "T3", "T4", "T5", "T6"):
            if d.get(k.lower()) is not None:
                dims[k] = d[k.lower()]
        ids.append("kind-2" if shape == 2 else "unknown-kind")
    name = str(d.get("name") or "")
    m = int(d.get("m", 0) or 0)
    extra: Dict[str, Any] = {"pdt_id": int(d.get("id", 0) or 0),
                             "pdt_shape": shape, "pdt_m": m,
                             "pdt_name1": str(d.get("name1") or ""),
                             "pdt_table": table,
                             "pdt_exi": list(d.get("exi") or [])}
    if ids:
        extra["unknown_items"] = ids
        extra["reason"] = ("$DEFFRAMESECTION 的 SHAPE=%d 未在本契约的键表内（§a.4）⇒ dims 只保留"
                           "文件字段名；确认途径见 UNKNOWN_DECODE_ITEMS" % shape)
    return SectionRec(key=name or "%d#%s" % (shape, d.get("id", 0)),
                      pkpm_name=name, family_code=39 if shape == 39 else 0,
                      family_name_cn="", kind=shape, shapeval="", dims=dims,
                      mat=m if m in (5, 6) else (5 if m else 0),
                      pdms_spec_path="", pdms_catalogue="", is_parametric=False,
                      params=[], confidence=("unknown" if ids else "high"),
                      source="pdt-defframesection", extra=extra)


# --------------------------------------------------------------------------
# 由模型建表（§k.1）
# --------------------------------------------------------------------------

def rec_from_section(sec: Section, table: str = "",
                     builtin: Optional[SectionTable] = None) -> SectionRec:
    """``canonical.Section`` → :class:`SectionRec`（``table_from_jwd``/``table_from_pdt`` 的公共实现）。

    证据优先级（**样本自身优先**，绝不为了"好看"而改样本数据）：

    1. ``kind``/``name``/``shapeval``/``mat`` 直接取自 ``Section``；
    2. ``dims``：有 ``shapeval`` ⇒ :func:`decode_shapeval` 的结果为准（**唯一解码**）；
       解不出（未冻结的 kind 或畸形串）⇒ 退回 ``Section.dims`` 并记 ``confidence='unknown'`` +
       ``extra['reason']``；
    3. **内置表只做加法**：按 ``pkpm_name`` 命中内置表时，补 ``pdms_spec_path`` /
       ``pdms_catalogue`` / ``family_code``（记录自身为 0 时）/ ``params`` / ``is_parametric``，
       并把内置表的 ``confidence``/``source`` 记进 ``extra['builtin_*']``；**尺寸以样本为准**，
       两者不等时记 ``extra['sample_vs_builtin']``（§k.5 的 ``db2jwd`` 取整差异）。
    """
    bt = builtin if builtin is not None else load_builtin_table()
    kind = int(sec.kind or 0)
    dims: Dict[str, Any] = {}
    ids: List[str] = []
    reason = ""
    confidence = "high"
    if sec.shapeval:
        try:
            dims = decode_shapeval(kind, sec.shapeval)
        except ValueError as e:
            dims = dict(sec.dims or {})
            confidence = "unknown"
            reason = "ShapeVal 解码失败：%s" % e
            if kind not in KIND_DIMS_KEYS:
                ids.append("unknown-kind")           # 未登记的 id 会让 validate() 报 E-UNKNOWN-ID
    else:
        dims = dict(sec.dims or {})
        if kind not in KIND_DIMS_KEYS:
            confidence = "unknown"
            reason = ("Kind=%s 不在 §a.4 的 dims 键表内（无 shapeval 可解码）⇒ dims 原样保留；"
                      "确认途径见 UNKNOWN_DECODE_ITEMS" % kind)
            ids.append("unknown-kind")
    # Kind 自身的证据等级（§a.4 / §12）
    if kind == 1:
        confidence = _min_conf(confidence, "medium")
        reason = reason or "Kind=1 的 B/H 先后为【推断-中】（§12#3）"
    elif kind == 2:
        confidence = "unknown"
        reason = ("Kind=2 的 B/T 交错序未证实（jwd_format.md §9.3#5）⇒ 不可回算"
                  "（UNKNOWN_DECODE_ITEMS['kind-2']）")
        ids.append("kind-2")
    elif kind == 3:
        reason = reason or "Kind=3 的族别是 inferred（圆形，§e.3/§12#5）"
    elif kind == 26:
        fam = int(_num(dims.get("family")) or 0)
        if fam != 39:
            confidence = "unknown"
            reason = ("Kind=26 的族码 %s ≠ 39：6 个尺寸槽顺序未解 ⇒ 不可回算"
                      "（UNKNOWN_DECODE_ITEMS['kind-26-slot-order']）" % fam)
            ids.append("kind-26-slot-order")
    elif kind == 303:
        confidence = _min_conf(confidence, "medium")
        ids += ["kind-303-slot27", "kind-303-slot32"]
        reason = reason or ("Kind=303 的槽 27/32 按规则推（§12#20），"
                            "槽值语义见 UNKNOWN_DECODE_ITEMS")
    name = sec.name or ""
    #: 无名截面用 §e.1 的**兜底候选键 5** `<Kind>#<params 逗号连接>`（jwd_read 已把 params
    #: 存成 §a.4 的参数体）——可复现、不含猜测。
    fallback_key = "%d#%s" % (kind, ",".join(str(x) for x in (sec.params or [])))
    rec = SectionRec(
        key=name or fallback_key,
        pkpm_name=name, family_code=int(_num(dims.get("family")) or 0),
        family_name_cn="", kind=kind, shapeval=sec.shapeval, dims=dims,
        mat=int(sec.mat or 0), pdms_spec_path="", pdms_catalogue="",
        is_parametric=False, params=[], confidence=confidence, source="jwd-section",
        extra={"jwd_id": int(sec.id or 0), "jwd_table": sec.table, "jwd_no": int(sec.no or 0),
               "jwd_params": list(sec.params or []), "unknown_items": ids},
    )
    if reason:
        rec.extra["reason"] = reason
    # ---- 内置表只做加法
    hit = None
    if rec.pkpm_name:
        hit = bt.get(pkpm_name=rec.pkpm_name)
    if hit is not None:
        rec.pdms_spec_path = hit.pdms_spec_path
        rec.pdms_catalogue = hit.pdms_catalogue
        if not rec.family_code:
            rec.family_code = int(hit.family_code or 0)
        rec.params = [p for p in hit.params]
        rec.is_parametric = bool(hit.is_parametric)
        rec.extra["builtin_key"] = hit.key
        rec.extra["builtin_confidence"] = hit.confidence
        rec.extra["builtin_source"] = hit.source
        if hit.dims and dims:
            bad = []
            for k in sorted(set(hit.dims) & set(dims)):
                va, vb = _num(hit.dims[k]), _num(dims[k])
                if va is None or vb is None:
                    continue
                if abs(float(va) - float(vb)) > 1e-9:
                    bad.append("%s: 样本=%s 目录宏=%s" % (k, dims[k], hit.dims[k]))
            if bad:
                rec.extra["sample_vs_builtin"] = "mismatch: " + "; ".join(bad)
    else:
        rec.extra["builtin_miss"] = True
    return rec


def _min_conf(a: str, b: str) -> str:
    order = {"high": 3, "medium": 2, "low": 1, "unknown": 0}
    return a if order.get(a, 0) <= order.get(b, 0) else b


def table_from_jwd(model) -> SectionTable:
    """``.jwd`` 装配出的 ``Model`` → :class:`SectionTable`（§k.1）。

    只取 ``model.sections``（读取器已按 §a.4/§a.5 填好 ``kind``/``shapeval``/``mat``）；
    ``extra['jwd_table']`` 记录该截面来自 ``beam``/``col``/``brace`` 哪张表。
    """
    bt = load_builtin_table()
    recs = [rec_from_section(model.sections[k], builtin=bt)
            for k in sorted(model.sections)]
    return SectionTable(recs, source=getattr(model, "source", "") or "jwd")


def table_from_pdt(model) -> SectionTable:
    """``.pdt`` 装配出的 ``Model`` → :class:`SectionTable`（§k.1）。

    ``.pdt`` 的 ``Section.table == 'pdt'``，``dims`` 是**文件字段名**（``B1``/``H1``/``T*``）；
    本函数把有证据的字段折算到 §a.4 的键空间（§3.3【事实】：``Kind=1`` 的 ``B1=B``/``H1=H``、
    ``Kind=3`` 的 ``B1=直径``、``Kind=39`` 的 ``B1=B``/``H1=H``），其余原样保留。
    """
    bt = load_builtin_table()
    recs: List[SectionRec] = []
    for k in sorted(model.sections):
        sec = model.sections[k]
        kind = int(sec.kind or 0)
        d = dict(sec.dims or {})
        dims: Dict[str, Any] = {}
        ids: List[str] = []
        confidence = "high"
        reason = ""
        if kind == 1:
            dims = {"B": _num(d.get("B1"), 0), "H": _num(d.get("H1"), 0)}
            confidence = "medium"
            reason = "Kind=1 的 B/H 先后为【推断-中】（§12#3）"
        elif kind == 3:
            dims = {"d": _num(d.get("B1"), 0)}
            reason = "Kind=3 的族别是 inferred（圆形，§e.3/§12#5）"
        elif kind == 39:
            dims = {"B": _num(d.get("B1"), 0), "H": _num(d.get("H1"), 0), "family": 39}
        else:
            dims = dict(d)
            confidence = "unknown"
            reason = ("$DEFFRAMESECTION 的 SHAPE/KIND=%s 不在 §a.4 的键表内 ⇒ dims 只保留文件字段名"
                      "（不猜语义）" % kind)
            ids.append("kind-2" if kind == 2 else "unknown-kind")
        name = sec.name or ""
        rec = SectionRec(
            key=name or "%d#%s" % (kind, sec.id),
            pkpm_name=name,
            family_code=39 if kind == 39 else int(_num(dims.get("family")) or 0),
            family_name_cn="", kind=kind, shapeval="", dims=dims,
            mat=int(sec.mat or 0), pdms_spec_path="", pdms_catalogue="",
            is_parametric=False, params=[], confidence=confidence, source="pdt-section",
            extra={"pdt_id": int(sec.id or 0), "pdt_table": sec.table,
                   "pdt_no": int(sec.no or 0), "pdt_dims_raw": dict(d),
                   "unknown_items": ids, "pdt_note": sec.note},
        )
        if reason:
            rec.extra["reason"] = reason
        hit = bt.get(pkpm_name=name) if name else None
        if hit is not None:
            rec.pdms_spec_path = hit.pdms_spec_path
            rec.pdms_catalogue = hit.pdms_catalogue
            rec.params = [p for p in hit.params]
            rec.is_parametric = bool(hit.is_parametric)
            rec.extra["builtin_key"] = hit.key
            rec.extra["builtin_confidence"] = hit.confidence
            if hit.dims:
                bad = []
                for kk in sorted(set(hit.dims) & set(dims)):
                    va, vb = _num(hit.dims[kk]), _num(dims[kk])
                    if va is None or vb is None:
                        continue
                    if abs(float(va) - float(vb)) > 1e-9:
                        bad.append("%s: pdt=%s 目录宏=%s" % (kk, dims[kk], hit.dims[kk]))
                if bad:
                    rec.extra["sample_vs_builtin"] = "mismatch: " + "; ".join(bad)
        else:
            rec.extra["builtin_miss"] = True
        recs.append(rec)
    return SectionTable(recs, source=getattr(model, "source", "") or "pdt")


# --------------------------------------------------------------------------
# §k.4 PDMS 侧
# --------------------------------------------------------------------------

#: §e.3 的**用户参数化族模板**（不含 Kind=3：它是**推断族**，由 secmap 的 @FAMILY 指令控制，
#: §e.1a 明令"启用/停用只由补充文件的指令行决定" ⇒ 本模块不擅自启用）
FAMILY_TEMPLATES: Dict[int, Dict[str, Any]] = {
    1: {"family": "RECT", "spec_path": "/USER_RECT-SPEC/Rectangle_Profile",
        "order": ("B", "H"), "status": PARAMETRIC},
    2: {"family": "H", "spec_path": "/USER_H-SPEC/H_Profile",
        "order": ("B1", "B2", "H", "Tw", "T1", "T2"), "status": PARAMETRIC},
}


def _section_of(rec: SectionRec, table: str = "") -> Section:
    return Section(id=int(rec.extra.get("jwd_id") or rec.extra.get("pdt_id") or 0),
                   kind=effective_kind(rec), mat=int(rec.mat or 0), name=rec.pkpm_name,
                   dims=dict(rec.dims or {}), table=table, no=0, shapeval=rec.shapeval,
                   params=[], note="")


def _numeric_defaults(rec: SectionRec) -> Tuple[List[float], str]:
    """参数化族的 ``desp_params``：``params[i].default`` **数值化**（§k.4 第 1 条）。

    任一项非数值 ⇒ 返回 ``([], 原因)``：**不允许**跳过某一项后继续（那会让 DESP 位置错位）。
    """
    out: List[float] = []
    for p in rec.params:
        v = _num(p.default)
        if v is None:
            return [], ("参数 %r 的默认值 %r 不是数值 ⇒ 无法给出 DESP 顺序"
                        "（param_nonnumeric，见 §k.2 的 extra）" % (p.name, p.default))
        out.append(float(v))
    return out, ""


def to_pdms(rec: SectionRec, secmap: Any = None, kind: str = "beam",
            section: Optional[Section] = None) -> Dict[str, Any]:
    """``SectionRec`` → PDMS 规格（§k.4 的**唯一优先级**，与 §e 的语义一致）。

    1. ``rec.pdms_spec_path`` 非空 ⇒ ``status='resolved'``、``source='builtin'``；
       ``desp_params`` = ``is_parametric`` 时取 ``params[i].default``（数值化）否则 ``[]``；
    2. 否则 ``secmap`` 给定时调它的 ``resolve(section, kind)``（**复用 §e 的四级优先级**，
       含 ``inferred``；本模块**不自立一套**）⇒ ``source='secmap'``；
    3. 否则按 §e.3 的**用户参数化族模板**（``Kind=1``→``RECT``、对称 ``Kind=2``→``H``）⇒
       ``status='parametric'``、``source='family'``；
    4. 全失败 ⇒ ``status='unresolved'``、``source='none'``、``reason`` 必填（写法同 §e.5）。

    :param secmap: ``secmap.SectionMap`` 实例（**也接受 secmap 模块本身**，取其 ``SectionMap``）。
        契约 §b.6 把 ``secmap`` 当实例传；这里做兼容，避免调用方两套写法。
    :param kind: ``'beam'|'col'|'brace'|'slab'|'wall'``，透传给 ``SectionMap.resolve``；
        缺省 ``'beam'``（记录里没有构件类别信息 ⇒ 与 :func:`group_tables_of` 同样"不猜"，
        用最通用的类别）。
    :param section: 直接给定 canonical ``Section``（板/墙请传 ``Section.for_panel(...)``）。

    :returns: ``{"spec_path","desp_params","status","source","reason"}``（§k.4 冻结的 5 键）。
    """
    reason = ""
    if rec.pdms_spec_path:
        desp, why = _numeric_defaults(rec) if rec.is_parametric else ([], "")
        if why:
            reason = "已按内置表解析到规格，但 DESP 参数无法数值化：%s" % why
        return {"spec_path": rec.pdms_spec_path, "desp_params": desp,
                "status": RESOLVED, "source": "builtin", "reason": reason}

    sm = _as_section_map(secmap)
    if sm is not None:
        sec = section if section is not None else _section_of(rec, kind)
        res = sm.resolve(sec, kind)
        return {"spec_path": res.spec_path, "desp_params": list(res.desp_params or []),
                "status": res.status, "source": "secmap", "reason": res.reason}

    # ---- 3) §e.3 的用户参数化族模板（只含有证据的 RECT / 对称 H）
    k = effective_kind(rec)
    tpl = FAMILY_TEMPLATES.get(k)
    if tpl is not None:
        dims = rec.dims or {}
        if k == 2:
            b1, b2 = _num(dims.get("B1")), _num(dims.get("B2"))
            t1, t2 = _num(dims.get("T1")), _num(dims.get("T2"))
            if b1 is None or b2 is None or t1 is None or t2 is None or b1 != b2 or t1 != t2:
                return {"spec_path": "", "desp_params": [], "status": UNRESOLVED,
                        "source": "none",
                        "reason": ("Kind=2 的 B1/T1 交错序未证实（jwd_format.md §9.3#5），"
                                   "无法确定 DESP 顺序 —— 只有 B1==B2 且 T1==T2 才能按 "
                                   "/USER_H-SPEC/H_Profile 的 [B1,B2,H,Tw,T1,T2] 出参")}
        vals = []
        miss = []
        for key in tpl["order"]:
            v = _num(dims.get(key))
            if v is None:
                miss.append(key)
            else:
                vals.append(float(v))
        if miss:
            return {"spec_path": "", "desp_params": [], "status": UNRESOLVED, "source": "none",
                    "reason": ("Kind=%d 走用户参数化族 %s 需要 dims%s，缺 %s（§e.3）"
                               % (k, tpl["family"], list(tpl["order"]), miss))}
        return {"spec_path": tpl["spec_path"], "desp_params": vals,
                "status": tpl["status"], "source": "family", "reason": ""}

    if k == 3:
        return {"spec_path": "", "desp_params": [], "status": UNRESOLVED, "source": "none",
                "reason": ("Kind=3 的族别是**推断族**（§e.1a：CIRCLE），启用/停用只由补充文件的 "
                           "@FAMILY 指令决定 ⇒ 未传 secmap 时无法判定，按 unresolved 处理"
                           "（不猜；UNKNOWN_DECODE_ITEMS 见 §e.3 的 Kind=3 行）")}

    cands = rec.extra.get("candidate_keys") or []
    return {"spec_path": "", "desp_params": [], "status": UNRESOLVED, "source": "none",
            "reason": ("Kind=%s（族码 %s）没有可用的候选键（%s）⇒ 需在 secmap_extra.txt 补条目，"
                       "或按 §e.1 的候选键规则补键（§e.5）"
                       % (k, _family_of(rec), cands or "无"))}


def _as_section_map(secmap: Any):
    """接受 ``SectionMap`` 实例 / ``secmap`` 模块 / ``None``（§k.4 的 ``secmap`` 参数）。"""
    if secmap is None:
        return None
    if hasattr(secmap, "resolve"):
        return secmap
    cls = getattr(secmap, "SectionMap", None)      # 传进来的可能是模块
    if cls is not None and hasattr(cls, "load"):
        raise ValueError("to_pdms/from_pdms 需要 SectionMap **实例**；"
                         "请先 SectionMap.load(path, extra_path)")
    return None


def from_pdms(spec_path: str, secmap: Any = None) -> Optional[SectionRec]:
    """PDMS 规格路径 → :class:`SectionRec`（§k.4；**禁止 fabricated 记录**）。

    归一化（去空白、补前导 ``/``、**不改大小写**）后依次查：
    ① 内置表 ``pdms_spec_path`` → ② ``secmap.reverse()`` 得 PKPM 名再查内置表 ``pkpm_name``
    → ③ 都没有 ⇒ ``None``。

    命中时返回**记录副本**；当查询路径与该记录的 ``pdms_spec_path`` 不同（例如走的是
    ``secmap.reverse`` 且原件右值写错）时，在 ``extra['queried_spec_path']`` 留痕。
    """
    q = _norm_path(spec_path)
    if not q:
        return None
    bt = load_builtin_table()
    hit = bt.get(pdms_spec_path=q)
    if hit is None:
        sm = _as_section_map(secmap)
        if sm is not None:
            name = sm.reverse(q)
            if name:
                hit = bt.get(pkpm_name=name)
    if hit is None:
        return None
    rec = hit.copy()
    if _norm_path(rec.pdms_spec_path) != q:
        rec.extra["queried_spec_path"] = q
    return rec
