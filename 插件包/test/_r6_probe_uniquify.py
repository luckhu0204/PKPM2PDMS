# -*- coding: utf-8 -*-
"""R6 临时探针：谁用 uniquify=False / MacOptions 构造点。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOTS = ["D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/插件包/test",
         "D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/插件包/engine",
         "D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/安装程序构建/src"]
for root in ROOTS:
    for fn in sorted(os.listdir(root)):
        if not fn.endswith(".py"):
            continue
        p = os.path.join(root, fn)
        txt = open(p, encoding="utf-8", errors="replace").read()
        hits = [(i, ln.strip()[:170]) for i, ln in enumerate(txt.splitlines(), 1)
                if "uniquify" in ln or "MacOptions(" in ln or "pml_func_path" in ln
                or "generate_macro" in ln or "build_plan" in ln]
        if hits:
            print("### %s/%s (%d)" % (os.path.basename(root), fn, len(hits)))
            for i, ln in hits:
                print("   %5d %s" % (i, ln))
