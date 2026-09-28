# -*- coding: utf-8 -*-
"""R3 修复脚本（本会话自建）：pkpm2pdmsuniquename.pmlfnc 的探测行与头注释（GBK+CRLF 写回）。

只改本包自己的 pdms/pkpm2pdmsuniquename.pmlfnc。
"""
import os

P = r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\pdms\pkpm2pdmsuniquename.pmlfnc"

raw = open(P, "rb").read()
t = raw.decode("gbk")
assert "\r\n" in t

# ① 探测行 + 行尾注释（§o.3/§0.4-12：base 自带前导 /，探成 //名 是全库 0 例的未证实形态）
old_probe = (
    "      -- 探测写法①（§o.3）：VAR EXIST + handle (2,109)（abaarealib.pmlfrm:107-114）\r\n"
    "      !probeSet = FALSE\r\n"
    "      var !probe EXIST /$!cand\r\n"
)
new_probe = (
    "      -- 探测写法①（§o.3）：VAR EXIST + handle (2,109)。\r\n"
    "      -- 形态 = EXIST $!cand（!cand 自带前导 / ，插值后就是 /名）——带斜杠名字的本机\r\n"
    "      -- 惯用法（62 处：tgautonum.pmlfnc:33-41、abauserview.pmlfrm:859-860 等）；旧形\r\n"
    "      -- EXIST /$!... 会探成 //名（全库 0 例的未证实形态，R3 复核发现(13)后禁用，\r\n"
    "      -- 契约 §o.3/§0.4-12）。(2,109) 双结局语义出处不变（abaarealib.pmlfrm:107-114）。\r\n"
    "      !probeSet = FALSE\r\n"
    "      var !probe EXIST $!cand\r\n"
)
assert old_probe in t, "探测行锚点缺失"
t = t.replace(old_probe, new_probe, 1)

# ② 头注释：TYPE 通道说明补记 R3 修正（保留 'TYPE 通道' 字样供验收检查）
old_type = (
    "-- == TYPE 通道（与 F.1 的一处必要偏差，如实说明）==\r\n"
    "--   F.1/§o.4 写 `!pkpm2pdmsType = 'SCTN'`（单 !）。PML 里单 ! 变量只在定义它的\r\n"
    "--   宏/函数作用域内可见，跨作用域传递须用双 ! 全局（!!CE 等同理）。\r\n"
    "--   本函数读取双 ! 全局 !!pkpm2pdmsType（undefined 时记 '?'）；调用方（宏/窗体）\r\n"
    "--   两个名字都赋值，兼容两种作用域模型。defined()/undefined() 的出处：\r\n"
)
new_type = (
    "-- == TYPE 通道（与 F.1 的一处必要偏差，如实说明）==\r\n"
    "--   F.1/§o.4 原文写 `!pkpm2pdmsType = 'SCTN'`（单 !）。PML 里单 ! 变量只在定义它的\r\n"
    "--   宏/函数作用域内可见，跨作用域传递须用双 ! 全局（!!CE 等同理）。\r\n"
    "--   本函数读取双 ! 全局 !!pkpm2pdmsType（undefined 时记 '?'）；调用方（宏/窗体）\r\n"
    "--   两个名字都赋值，兼容两种作用域模型。R3 复核修正（§0.4-12）：生成器\r\n"
    "--   （engine/macgen.py）此前误赋单 ! ， defined(!!pkpm2pdmsType) 恒假、改名记录\r\n"
    "--   TYPE 恒 '?'；已改为赋双 ! 全局，与本函数一致。defined()/undefined() 的出处：\r\n"
)
assert old_type in t, "TYPE 注释锚点缺失"
t = t.replace(old_type, new_type, 1)

new = t.encode("gbk")
with open(P, "wb") as fh:
    fh.write(new)

back = open(P, "rb").read()
txt = back.decode("gbk")
print("bytes %d -> %d" % (len(raw), len(back)))
print("BOM:", back[:3] == b"\xef\xbb\xbf")
print("lone LF:", back.replace(b"\r\n", b"").count(b"\n"))
print("probe 行：", [l.strip() for l in txt.splitlines() if "EXIST $!cand" in l])
print("旧 //名 探测残留：", "EXIST /$!cand" in txt)
print("TYPE 通道/两种都写 字样在：", "TYPE 通道" in txt, "两种都写" in txt)
