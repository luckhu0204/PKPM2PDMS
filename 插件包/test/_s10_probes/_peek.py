# -*- coding: utf-8 -*-
"""通用只读查看器：按行号区间打印文件（自动判编码），并可选列出 Markdown 标题。

用法：
    python _peek.py <文件> [起始行] [结束行] [编码]
    python _peek.py <文件> --toc          # 只列 Markdown 标题行
    python _peek.py <文件> --grep <关键词>  # 只列含关键词的行（区分大小写，纯子串）
"""
import re
import sys


def load(path, enc=None):
    raw = open(path, 'rb').read()
    if enc:
        return raw.decode(enc), enc
    for e in ('utf-8-sig', 'utf-8', 'gbk'):
        try:
            return raw.decode(e), e
        except UnicodeDecodeError:
            continue
    return raw.decode('gbk', 'replace'), 'gbk/replace'


path = sys.argv[1]
args = sys.argv[2:]
text, enc = load(path, args[3] if len(args) >= 4 else None)
lines = text.splitlines()
print('### %s  %d 行  编码判定=%s' % (path, len(lines), enc))

if args and args[0] == '--toc':
    for i, l in enumerate(lines, 1):
        if re.match(r'^#{1,6} ', l) or re.match(r'^#{1,6}[^#]', l):
            print('%5d %s' % (i, l))
    sys.exit(0)
if args and args[0] == '--grep':
    needle = args[1]
    for i, l in enumerate(lines, 1):
        if needle in l:
            print('%5d| %s' % (i, l[:240]))
    sys.exit(0)

a = int(args[0]) if len(args) >= 1 else 1
b = int(args[1]) if len(args) >= 2 else len(lines)
for i, l in enumerate(lines[a - 1:b], a):
    print('%5d| %s' % (i, l))
