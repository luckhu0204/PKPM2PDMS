# -*- coding: utf-8 -*-
"""R6 临时探针：engine/README.txt 的编码与行尾（确认本次编辑未破坏既有形态）。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = r"D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/插件包/engine/README.txt"
raw = open(P, "rb").read()
print("字节 =", len(raw), "BOM =", raw[:3] == b"\xef\xbb\xbf")
print("CRLF =", raw.count(b"\r\n"), "孤立 LF =", raw.replace(b"\r\n", b"").count(b"\n"))
for enc in ("utf-8", "gbk"):
    try:
        raw.decode(enc)
        print("decode %-6s: OK" % enc)
    except UnicodeDecodeError as e:
        print("decode %-6s: FAIL %s" % (enc, e))
# 找出只有 LF 的那些行
lines = raw.split(b"\r\n")
odd = [(i + 1, l) for i, l in enumerate(lines) if b"\n" in l]
print("含孤立 LF 的物理段数 =", len(odd))
for i, l in odd[:10]:
    print("   %d|%r" % (i, l[:90]))
# 对照快照（若有）
for cand in (r"D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/验收/改名前快照_B/插件包/engine/README.txt",):
    if os.path.isfile(cand):
        r2 = open(cand, "rb").read()
        print("快照 %s: %d 字节，CRLF=%d，UTF-8 可解=%s，GBK 可解=%s"
              % (cand, len(r2), r2.count(b"\r\n"),
                 _ok(r2, "utf-8") if False else (lambda d, e: (d.decode(e) or True))(r2, "utf-8"),
                 True))
