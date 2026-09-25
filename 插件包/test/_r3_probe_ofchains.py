# -*- coding: utf-8 -*-
"""R3 探针（本会话自建）：在用户目录宏与 PMLLIB 里找 of-链语法证据（用于第二遍引用限定）。"""
import os
import re

OUT = open(r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\test\_r3_probe_ofchains.txt", "w",
           encoding="utf-8")
DB = (r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
      r"\PKPM（PDMS数据库）.txt")
t = open(DB, "rb").read().decode("utf-8-sig")
lines = t.splitlines()
print("lines", len(lines), file=OUT)
pats = {
    "OLD PTSSET": r"^\s*OLD\s+PTSSET\s",
    "NARE ... of PTSSET": r"^\s*NARE\s+PLINE\s+\d+\s+of\s+PTSSET\s",
    "PSTR": r"^\s*PSTR\s+PTSSET\s",
    "GSTR": r"^\s*GSTR\s+GMSSET\s",
    "DTRE": r"^\s*DTRE\s+DTSET\s",
    "CATR": r"^\s*CATR\s+SPRFILE\s",
    "OLD SPRFILE": r"^\s*OLD\s+SPRFILE\s",
    "OLD SPCOMPONENT": r"^\s*OLD\s+SPCOMPONENT\s",
    "OLD 裸名": r"^\s*OLD\s+/\S",
    "多级链 of.*of": r"\bof\s+\S+.*\bof\s+\S+",
    "of STSECTION": r"\bof\s+STSECTION\b",
    "of CATALOGUE": r"\bof\s+CATALOGUE\b",
    "of SPECIFICATION": r"\bof\s+SPECIFICATION\b",
    "of SELEC": r"\bof\s+SELEC\b",
}
for tag, pat in pats.items():
    rx = re.compile(pat, re.IGNORECASE)
    hits = [(i + 1, l.strip()) for i, l in enumerate(lines) if rx.search(l)]
    print("== %-24s %d 条" % (tag, len(hits)), file=OUT)
    for i, l in hits[:4]:
        print("   L%-7d %s" % (i, l[:150]), file=OUT)

# 本机 PMLLIB 里找 OLD + of 链
PM = r"D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB"
cnt = 0
for root, _dirs, files in os.walk(PM):
    for fn in files:
        if os.path.splitext(fn)[1].lower() not in (".mac", ".pmlfnc", ".pmlobj", ".pmlfrm", ".dat"):
            continue
        p = os.path.join(root, fn)
        try:
            tt = open(p, "rb").read().decode("latin-1", "replace")
        except OSError:
            continue
        for m in re.finditer(r"(?im)^\s*(OLD\s+\S.*?\bof\s+\S.*)$", tt):
            ln = tt[:m.start()].count("\n") + 1
            print("PMLLIB %s:%d %s" % (os.path.relpath(p, PM), ln, m.group(1).strip()[:150]),
                  file=OUT)
            cnt += 1
            if cnt > 25:
                break
        if cnt > 25:
            break
    if cnt > 25:
        break
print("PMLLIB OLD-of 命中（截断至 25）:", cnt, file=OUT)
OUT.close()
print("done")
