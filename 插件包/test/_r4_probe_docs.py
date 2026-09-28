# -*- coding: utf-8 -*-
"""R3 探针 4：看 docs/交付清单.md 与 使用说明.md 的头部与章节结构。"""
OUT = open(r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\test\_r4_probe_docs.txt", "w",
           encoding="utf-8")
for name in ("交付清单.md", "使用说明.md"):
    p = r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\docs" + "\\" + name
    t = open(p, "rb").read().decode("utf-8").splitlines()
    print("==== %s (%d 行) ====" % (name, len(t)), file=OUT)
    for i, l in enumerate(t[:40], 1):
        print("%4d %s" % (i, l[:150]), file=OUT)
    print("   ……", file=OUT)
    print("---- 章节标题 ----", file=OUT)
    for i, l in enumerate(t, 1):
        if l.startswith("#"):
            print("%4d %s" % (i, l[:120]), file=OUT)
OUT.close()
print("done")
