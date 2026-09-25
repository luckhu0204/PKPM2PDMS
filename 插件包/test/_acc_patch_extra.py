# -*- coding: utf-8 -*-
"""临时补丁脚本（本会话自建）：把 engine/secmap_extra.txt 的尾部换成推断族说明（GBK+CRLF 写回）。

只改本包自己的文件 engine/secmap_extra.txt；不碰任何用户原件。
"""
import io
import os

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(PKG, "engine", "secmap_extra.txt")

MARKER = "// ===== 点名任何一个截面"

TAIL = u"""// ===== 点名任何一个截面：候选键 5「<Kind>#<ShapeVal 参数体>」（契约 §e.1）=====
// 原件确实没有条目的截面，可以用它复现（只需 ShapeVal 原文）：
//   圆形4800, /USER_CIRCLE-SPEC/Circle_Profile
//        ^ 1_PM.pdt 的 SHAPE=3（B1=4800=直径，pdt_format.md §5.3）。原件无此名；
//          它走的是下面的 @FAMILY 推断（KIND=3 已是圆形），此处只留模板备查。

// ===== 推断族指令行（契约 §e.4a / §e.1a；本文件是唯一可改的地方）=============
// 语法：@FAMILY <Kind> = <族键|none>     （注意：这一行没有逗号，不是"左值,右值"）
//   @FAMILY 3 = CIRCLE   启用：Kind=3 的单尺寸截面按圆形族解析
//                        → SPREF /USER_CIRCLE-SPEC/Circle_Profile + DESP <直径>
//                        → 报告里 status='inferred'（不是 resolved）并带 evidence
//   @FAMILY 3 = none     停用：回到 status='unresolved'（宏里只留 -- UNRESOLVED SECTION 标记）
//
// 为什么是 CIRCLE（证据，详见 spec/CONTRACT.md §e.3 的 Kind=3 行与 §0.4-1 变更记录）：
//   ① 1_PM.pdt:2387-2388  ID=1009, NAME=圆形4800, SHAPE=3 / KIND=3, B1=4800
//      → Shape/Kind=3 就是"圆形"，B1 承载直径；
//   ② 同一 JLCJ2 模型把「薄壁方钢管: B20」归 Kind=303（pkpmBraceSect ID=62965）→ 排除方管；
//   ③ PKPM（PDMS数据库）.txt:2502-2513  /USER_CIRCLE 的 DTSET 只有一个参数
//      DKEY D / PTYP DIST / PPRO ( ATTRIB DESP[1] ) / NUMB 1 → DESP 只有一个数=直径；
//   ④ PKPM转PDMS截面匹配文件.txt:27  CIRCLE, /USER_CIRCLE-SPEC/Circle_Profile（原件自己的约定）。
// 残余风险（必须随交付物一起给用户）：不能 100% 排除 d=20 是别的单尺寸族；影响面仅本样本
//   12 根屋面水平支撑（pkpmBraceSect ID=32335，ShapeVal='3,20,5,32335,'）。
//   注意：若把本行改成 none，宏里这 12 根构件将不再有 SPREF/DESP（验收标准 1「每构件有 SPREF 或
//     DESP」会随之不成立）——那是故意的：宁可少写规格，也不写没证据的规格。
@FAMILY 3 = CIRCLE
"""

data = open(P, "rb").read()


def _try(ch):
    try:
        ch.encode("gbk")
        return True
    except UnicodeEncodeError:
        return None


old = data.decode("gbk")
assert "\r\n" in old, "原文件不是 CRLF"
body = old.replace("\r\n", "\n")
i = body.find(MARKER)
assert i > 0, "找不到标记行"
new_body = body[:i] + TAIL.replace("\r\n", "\n")
bad = sorted({c for c in new_body if _try(c) is None})
new = new_body.replace("\n", "\r\n").encode("gbk")

with open(P, "wb") as fh:
    fh.write(new)

# 回读校验
raw = open(P, "rb").read()
txt = raw.decode("gbk")
print("bytes %d -> %d" % (len(data), len(raw)))
print("BOM:", raw[:3] == b"\xef\xbb\xbf")
print("lone LF:", raw.replace(b"\r\n", b"").count(b"\n"))
print("lines:", len(txt.split("\r\n")))
print("has @FAMILY 3 = CIRCLE:", "@FAMILY 3 = CIRCLE" in txt)
print("非 GBK 字符:", bad)
print("data lines (含逗号、非注释):", sum(1 for l in txt.splitlines()
                                           if l.strip() and not l.strip().startswith("//")
                                           and "," in l))
