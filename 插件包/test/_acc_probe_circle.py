# -*- coding: utf-8 -*-
"""临时探针 9（本会话自建）：目录宏里 USER_CIRCLE 族的完整定义（参数名/DTSET/DPRO）。"""
import os, re

SD = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_acc_probe_circle.txt"),
           "w", encoding="utf-8")


def read(p):
    data = open(p, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return data.decode(enc)
        except Exception:
            pass
    return data.decode("gbk", "replace")


for name in ("PKPM（PDMS数据库）.txt", os.path.join("P-TRANS", "pkpm_section_DBOutput.txt")):
    p = os.path.join(SD, name)
    t = read(p)
    lines = t.splitlines()
    print("=" * 78, file=out)
    print("FILE", name, "lines", len(lines), file=out)
    # 1) STCATEGORY /USER_CIRCLE 块
    idx = [i for i, l in enumerate(lines) if l.strip().startswith("NEW STCATEGORY /USER_CIRCLE")]
    print("STCATEGORY /USER_CIRCLE at", idx, file=out)
    for i0 in idx:
        j = i0
        while j < len(lines) and not (j > i0 and lines[j].startswith("NEW STCATEGORY")):
            print("   ", j + 1, lines[j].rstrip()[:170], file=out)
            j += 1
            if j - i0 > 40:
                break
    # 2) Circle_Profile 的 SPCOMPONENT 前后
    for i, l in enumerate(lines):
        if "/USER_CIRCLE-SPEC/Circle_Profile" in l:
            a, b = max(0, i - 30), min(len(lines), i + 30)
            print("---- around line", i + 1, "----", file=out)
            for j in range(a, b):
                print("   ", j + 1, lines[j].rstrip()[:170], file=out)
    # 3) USER_RECT 的同区域（作对照，RECT 的 DESP 顺序是契约冻结的）
    for i, l in enumerate(lines):
        if "/USER_RECT-SPEC/Rectangle_Profile" in l:
            a, b = max(0, i - 14), min(len(lines), i + 14)
            print("---- RECT around line", i + 1, "----", file=out)
            for j in range(a, b):
                print("   ", j + 1, lines[j].rstrip()[:170], file=out)
            break
out.close()
print("done")
