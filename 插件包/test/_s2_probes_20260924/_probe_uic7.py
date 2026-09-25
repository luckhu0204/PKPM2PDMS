# -*- coding: utf-8 -*-
"""临时侦察脚本 7：从框架文档 XML 列出 CommandType 枚举成员与 MacroCommand 相关成员（只读）。"""
import os, re

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_probe_cmdtype_out.txt')

t = open(os.path.join(ROOT, 'ApplicationFramework.Presentation.xml'), 'rb').read().decode('utf-8-sig', 'replace')
lines = []
for m in re.finditer(r'<member name="([^"]+)"', t):
    nm = m.group(1)
    if re.search(r'(?i)commandtype|macrocommand|commandmanager|Command$', nm):
        lines.append(nm)

# 把 MacroCommand / CommandManager 段落完整打印
for key in ['CommandManager.MacroCommand', 'CommandManager.CommandTypes', 'CommandType']:
    for m in re.finditer(re.escape(key), t):
        a = max(0, m.start() - 100)
        seg = t[a:m.start() + 700]
        lines.append('===== around %s =====' % key)
        lines.append(seg)
        break

open(OUT, 'w', encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines)[:8000])
