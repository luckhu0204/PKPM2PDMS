# -*- coding: utf-8 -*-
"""R6 临时探针：读参考 DB Output 宏的头/尾形态（只读 G:）。"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"G:/工作/PDMS相关/00 PDMS插件/02 实用插件/PKPM导入导出插件/P-TRANS/pkpm_section_DBOutput.txt"
import os

print("exists", os.path.isfile(p), os.path.getsize(p) if os.path.isfile(p) else "")
raw = open(p, "rb").read()
print("BOM", raw[:3] == b"\xef\xbb\xbf")
print("CRLF", raw.count(b"\r\n"), "LF_total", raw.count(b"\n"))
try:
    t = raw.decode("gbk")
    print("decode: gbk ok")
except UnicodeDecodeError as e:
    t = raw.decode("gbk", errors="replace")
    print("decode gbk fail", e)
    try:
        t = raw.decode("utf-8")
        print("decode: utf-8 ok")
    except UnicodeDecodeError as e2:
        print("decode utf-8 fail", e2)
        t = raw.decode("utf-8", errors="replace")
lines = t.split("\r\n")
print("total lines", len(lines))
print("=== HEAD 20 ===")
for i in range(0, min(20, len(lines))):
    print("%5d|%s" % (i + 1, lines[i]))
print("=== TAIL 30 ===")
for i in range(max(0, len(lines) - 30), len(lines)):
    print("%5d|%s" % (i + 1, lines[i]))
