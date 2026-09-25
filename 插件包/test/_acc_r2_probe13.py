# -*- coding: utf-8 -*-
"""探针 R2-13：样本 1_PM.pdt 的文件尾字节（契约 §j.2-6 的权威）。"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
S = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
for name in ("1_PM.pdt",):
    b = open(os.path.join(S, name), "rb").read()
    print(name, "size", len(b))
    print("  tail 16 bytes =", repr(b[-16:]))
    print("  ends with $END\\r\\n\\r\\n ?", b.endswith(b"$END\r\n\r\n"))
    print("  ends with $END\\r\\n ?", b.endswith(b"$END\r\n"))
t = open(os.path.join(S, "1_PM.pdt"), "rb").read().decode("gbk").replace("\r\n", "\n")
lines = t.split("\n")
for i in range(len(lines) - 6, len(lines)):
    print("  L%d = %r" % (i + 1, lines[i]))
