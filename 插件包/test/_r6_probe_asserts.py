# -*- coding: utf-8 -*-
"""R6 临时探针：活测试里对宏头/宏尾文本的具体断言。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = "D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/插件包/test"
NEEDLES = ["自动生成", "基点", "构件 %d", "创建元素", "命名约定", "Synonym", "分隔",
           "lines[0]", "lines[1]", "lines[2]", "lines[-1]", "lines[-2]", "头 12", "尾",
           "UNRESOLVED", "$S-", "$S+", "ONERROR", "handle ANY", "RETURN ERROR"]
for fn in sorted(os.listdir(HERE)):
    if not fn.endswith(".py") or fn.startswith("_"):
        continue
    txt = open(os.path.join(HERE, fn), encoding="utf-8", errors="replace").read()
    hits = []
    for i, ln in enumerate(txt.splitlines(), 1):
        for n in NEEDLES:
            if n in ln:
                hits.append((i, n, ln.strip()[:170]))
                break
    if hits:
        print("### %s (%d)" % (fn, len(hits)))
        for i, n, ln in hits:
            print("   %5d [%s] %s" % (i, n, ln))
