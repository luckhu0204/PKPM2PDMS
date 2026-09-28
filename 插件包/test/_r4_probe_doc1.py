# -*- coding: utf-8 -*-
"""R3 探针 5：验证 交付清单.md 的声明已写入（且 UTF-8 完好）。"""
t = open(r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\docs\交付清单.md",
         "rb").read().decode("utf-8")
print("未部署 in:", "未部署" in t)
print("安装 in:", "安装" in t)
print("原文句 in:", "本包未部署，需要用户自己在 PDMS 停机时按 docs/使用说明.md 安装" in t)
print("交付副本行 in:", "交付_PKPM2PDMS插件" in t)
i = t.find("未部署声明")
print(t[i - 40:i + 420])
