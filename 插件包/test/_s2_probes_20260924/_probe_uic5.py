# -*- coding: utf-8 -*-
"""临时侦察脚本 5：在框架文档 XML 里找 Macro / 命令类型相关段落（只读）。"""
import os, re

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_probe_macro_out.txt')

lines = []
for f in ['ApplicationFramework.Presentation.xml', 'Aveva.Pdms.Design.xml']:
    p = os.path.join(ROOT, f)
    if not os.path.exists(p):
        lines.append('MISSING ' + f)
        continue
    t = open(p, 'rb').read().decode('utf-8-sig', 'replace')
    lines.append('===== %s len=%d macro_hits=%d' % (f, len(t), len(re.findall(r'(?i)macro', t))))
    for m in list(re.finditer(r'(?i)macro', t))[:10]:
        a = max(0, m.start() - 250)
        lines.append(repr(t[a:m.start() + 250]))
        lines.append('---')

open(OUT, 'w', encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines)[:6000])
