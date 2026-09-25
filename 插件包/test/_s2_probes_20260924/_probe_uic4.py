# -*- coding: utf-8 -*-
"""临时侦察脚本 4：列出 design.uic 内全部工具与其 Command（只读）。"""
import os, re

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
p = os.path.join(ROOT, 'design.uic')
t = open(p, 'rb').read().decode('utf-8-sig')

# 去掉 base64 图片正文，便于打印
t2 = re.sub(r'<Image>[^<]*</Image>', '<Image>...base64...</Image>', t)
print('---- design.uic (image bodies elided) ----')
print(t2)
