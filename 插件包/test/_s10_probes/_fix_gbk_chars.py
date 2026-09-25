# -*- coding: utf-8 -*-
"""找出 pdms/ 下 PML 文件里 GBK 编不出来的字符，并就地替换成 GBK 安全写法。"""
import os

PDMS = r'D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\pdms'
REPL = {
    '\u21d2': '=>',    # ⇒
    '\u21d0': '<=',    # ⇐
    '\u2713': 'OK',    # ✓
    '\u2717': 'x',     # ✗
    '\u2260': '!=',    # ≠
}
for name in sorted(os.listdir(PDMS)):
    if not name.lower().endswith(('.pmlfnc', '.pmlfrm', '.pmlobj', '.mac')):
        continue
    p = os.path.join(PDMS, name)
    raw = open(p, 'rb').read()
    try:
        text = raw.decode('utf-8')
        src = 'utf-8'
    except UnicodeDecodeError:
        text = raw.decode('gbk')
        src = 'gbk'
    bad = []
    for c in sorted(set(text)):
        try:
            c.encode('gbk')
        except UnicodeEncodeError:
            bad.append(c)
    if not bad:
        print('OK   %-26s (来源 %s)' % (name, src))
        continue
    print('FIX  %-26s %s' % (name, ['%s(U+%04X)' % (c, ord(c)) for c in bad]))
    for c in bad:
        text = text.replace(c, REPL.get(c, '?'))
    data = text.encode('gbk')
    open(p, 'wb').write(data)
    print('     已替换并写回（%d 字节）' % len(data))
