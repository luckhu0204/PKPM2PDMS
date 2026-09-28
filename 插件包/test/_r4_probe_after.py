# -*- coding: utf-8 -*-
"""R3 探针 7：核对刷新后的交付目录（检查 19 的三个 MISS + 哈希清单 + docs 声明）。"""
import os

DEL = r"D:\AI_Work\PKPM数据解析\交付_PKPM2PDMS插件"
PKG_COPY = os.path.join(DEL, "插件包")
OUT = open(r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\test\_r4_probe_after.txt", "w",
           encoding="utf-8")
print("交付根：", sorted(os.listdir(DEL)), file=OUT)
for rel in ("pdms-net", os.path.join("pdms", "pkpm2pdmsuniquename.pmlfnc"),
            os.path.join("engine", "dist")):
    p = os.path.join(PKG_COPY, rel)
    ok = os.path.isdir(p) or os.path.isfile(p)
    print("整包副本含 %-40s : %s" % (rel, ok), file=OUT)
for f in sorted(os.listdir(DEL)):
    if "哈希" in f or "sha256" in f.lower():
        p = os.path.join(DEL, f)
        print("哈希清单文件：", f, os.path.getsize(p), "B", file=OUT)
        head = open(p, "rb").read().decode("utf-8-sig").splitlines()
        print("   前几行：", head[:6], file=OUT)
        print("   总行数：", len(head), file=OUT)
# docs 声明
for name in ("交付清单.md", "使用说明.md"):
    t = open(os.path.join(r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\docs", name),
             "rb").read().decode("utf-8")
    print("docs/%s 未部署+安装：%s" % (name, ("未部署" in t) and ("安装" in t)), file=OUT)
# 副本里的 docs 也应有声明
t = open(os.path.join(PKG_COPY, "docs", "使用说明.md"), "rb").read().decode("utf-8")
print("副本 docs/使用说明.md 未部署声明：", "未部署" in t, file=OUT)
# _selftest 不应被复制进交付副本
print("副本含 pdms-net/_selftest：", os.path.exists(os.path.join(PKG_COPY, "pdms-net", "_selftest")),
      file=OUT)
print("副本含 engine/dist/_pybuild：",
      os.path.exists(os.path.join(PKG_COPY, "engine", "dist", "_pybuild")), file=OUT)
OUT.close()
print("done")
