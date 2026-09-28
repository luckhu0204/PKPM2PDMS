# -*- coding: utf-8 -*-
"""R6 临时探针：在 test/ 与 engine/ 里找与 pml_func_path / 宏头尾 / TOOLS 相关的引用。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOTS = ["D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/插件包/test",
         "D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/插件包/engine",
         "D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/安装程序构建/src",
         "D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/插件包/pdms-net"]
NEEDLES = ["pml_func_path", "pkpm2pdmsFuncPath", "pkpm2pdmsFuncMissing",
           "pkpm2pdmsUniquename", "TOOLS", "jwd2pdms", "auto2pdms",
           "Synonym translation", "GOLABEL", "PDMS_MACRO_TOOLS"]
for root in ROOTS:
    for dirpath, _dirs, files in os.walk(root):
        if "__pycache__" in dirpath or "dist" in dirpath.split(os.sep):
            continue
        for fn in sorted(files):
            if not fn.endswith((".py", ".cs", ".txt", ".md", ".mac", ".pmlfrm",
                                ".pmlfnc", ".cmd", ".spec")):
                continue
            p = os.path.join(dirpath, fn)
            try:
                txt = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            hits = []
            for i, ln in enumerate(txt.splitlines(), 1):
                for n in NEEDLES:
                    if n in ln:
                        hits.append((i, n, ln.strip()[:150]))
                        break
            if hits:
                print("### %s  (%d hits)" % (p, len(hits)))
                for i, n, ln in hits[:40]:
                    print("   %5d [%s] %s" % (i, n, ln))
                if len(hits) > 40:
                    print("   … 其余 %d 条" % (len(hits) - 40,))
