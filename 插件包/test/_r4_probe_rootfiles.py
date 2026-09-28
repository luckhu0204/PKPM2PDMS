# -*- coding: utf-8 -*-
"""R3 探针 3：读交付根的两份说明文件头部。"""
DEL = r"D:\AI_Work\PKPM数据解析\交付_PKPM2PDMS插件"
OUT = open(r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\test\_r4_probe_rootfiles.txt",
           "w", encoding="utf-8")
for name in ("交付清单.txt", "从这里开始.txt"):
    p = os.path.join(DEL, name) if (os := __import__("os")) else ""
    raw = open(p, "rb").read()
    t = raw.decode("utf-8", "replace")
    print("==== %s (%d bytes) ====" % (name, len(raw)), file=OUT)
    print(t[:2200], file=OUT)
    print("……（尾部 600 字）……", file=OUT)
    print(t[-600:], file=OUT)
OUT.close()
print("done")
