# -*- coding: utf-8 -*-
"""R3 探针 2（本会话自建）：交付目录现状（junction 安全；不跟随 reparse point）。"""
import os
import stat

DEL = r"D:\AI_Work\PKPM数据解析\交付_PKPM2PDMS插件"
PKG = r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出"
OUT = open(r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\test\_r4_probe_delivery.txt",
           "w", encoding="utf-8")


def is_reparse(p):
    try:
        st = os.lstat(p)
        return bool(st.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except OSError:
        return True


def tree(root, depth=0, maxdepth=2):
    if depth > maxdepth:
        return
    try:
        entries = sorted(os.listdir(root))
    except OSError as e:
        print("  " * depth + "(不可读 %s)" % e, file=OUT)
        return
    for x in entries:
        p = os.path.join(root, x)
        if x == "__pycache__":
            print("  " * depth + x + "/（跳过显示）", file=OUT)
            continue
        if os.path.isdir(p) and not is_reparse(p):
            print("  " * depth + x + "/", file=OUT)
            tree(p, depth + 1, maxdepth)
        elif os.path.isdir(p):
            print("  " * depth + x + "/ [junction/reparse → 不跟随]", file=OUT)
        else:
            try:
                print("  " * depth + "%s (%d B)" % (x, os.path.getsize(p)), file=OUT)
            except OSError:
                print("  " * depth + x + " (不可读)", file=OUT)


print("==== 交付目录树（深度 2） ====", file=OUT)
tree(DEL, 0, 2)
print("", file=OUT)

print("==== 包内 pdms-net / engine\\dist 顶层（junction 安全） ====", file=OUT)
for rel in ("pdms-net", os.path.join("engine", "dist")):
    root = os.path.join(PKG, rel)
    print("-- %s" % rel, file=OUT)
    for x in sorted(os.listdir(root)):
        p = os.path.join(root, x)
        if is_reparse(p):
            print("   %s [reparse]" % x, file=OUT)
        elif os.path.isdir(p):
            n = sum(len(f) for _r, _d, f in os.walk(p))
            print("   %s/ (%d 文件)" % (x, n), file=OUT)
        else:
            print("   %s (%d B)" % (x, os.path.getsize(p)), file=OUT)

print("", file=OUT)
print("==== 包内 docs/ ====", file=OUT)
print(sorted(os.listdir(os.path.join(PKG, "docs"))), file=OUT)
print("", file=OUT)
print("==== docs 两份清单里是否已有 未部署/安装 字样 ====", file=OUT)
for name in ("交付清单.md", "使用说明.md"):
    p = os.path.join(PKG, "docs", name)
    t = open(p, "rb").read().decode("utf-8", "replace")
    print("%s: 未部署=%s 安装=%s" % (name, "未部署" in t, "安装" in t))
OUT.close()
print("done")
