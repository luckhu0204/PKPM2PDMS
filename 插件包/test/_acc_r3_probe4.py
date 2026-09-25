# -*- coding: utf-8 -*-
"""探针 R3-4：docs 的部署相关语句（验收 19-③ 的证据）。"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
for n in ("交付清单.md", "使用说明.md"):
    t = open("docs/" + n, encoding="utf-8", errors="replace").read()
    print("=====", n, len(t))
    for kw in ("部署", "安装", "停机", "deploy", "生效"):
        i = 0
        shown = 0
        while shown < 2:
            i = t.find(kw, i)
            if i < 0:
                break
            print("   [%s] ...%s..." % (kw, t[max(0, i - 70):i + 90].replace("\n", " ")))
            i += len(kw)
            shown += 1
        if shown == 0:
            print("   [%s] 无" % kw)
