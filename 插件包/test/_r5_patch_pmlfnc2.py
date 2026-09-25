# -*- coding: utf-8 -*-
"""R3 修复脚本 v2（本会话自建）：幂等重跑 pmlfnc 修补（探测行/注释/TYPE 通道说明）。

前一次运行已把探测行换成 EXIST $!cand；本版把注释里的旧形字样换成 `EXIST /$!...`
（避免与代码形态混淆），其余幂等。
"""
import os

P = r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\pdms\pkpmjwduniquename.pmlfnc"

raw = open(P, "rb").read()
t = raw.decode("gbk")

# 注释里的旧形字样换成省略形（避免与代码形态字面相同）
t = t.replace("EXIST /$!cand 会探成 //名", "EXIST /$!... 会探成 //名")

new = t.encode("gbk")
with open(P, "wb") as fh:
    fh.write(new)

back = open(P, "rb").read()
txt = back.decode("gbk")
print("bytes", len(back))
print("BOM:", back[:3] == b"\xef\xbb\xbf")
print("lone LF:", back.replace(b"\r\n", b"").count(b"\n"))
print("代码探测行：", [l.strip() for l in txt.splitlines() if l.strip().startswith("var !probe")])
print("残留代码形 EXIST /$!cand：", "var !probe EXIST /$!cand" in txt)
print("TYPE 通道/两种都写：", "TYPE 通道" in txt, "两种都写" in txt)
