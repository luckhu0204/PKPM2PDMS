# -*- coding: utf-8 -*-
"""R6 临时探针：确认 exe 两份副本逐字节一致 + 引擎相关文件清单。"""
import hashlib
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TREE = r"D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


pairs = [("安装程序/PKPM2PDMS_引擎_v2.1.0.exe", "插件包/engine/dist/pkpm2pdms_engine.exe")]
for a, b in pairs:
    pa, pb = os.path.join(TREE, a), os.path.join(TREE, b)
    ha, hb = sha(pa), sha(pb)
    print("%s\n  %s  %d B  %s\n%s\n  %s  %d B  %s\n  一致 = %s"
          % (a, a, os.path.getsize(pa), ha, b, b, os.path.getsize(pb), hb, ha == hb))
