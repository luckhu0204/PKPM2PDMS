# -*- coding: utf-8 -*-
"""契约文档的 Markdown 表格自检：找出列数与表头不一致的行（只读，不修改文档）。"""
import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
path = sys.argv[1] if len(sys.argv) > 1 else 'spec/CONTRACT.md'
lines = open(path, encoding='utf-8').read().split('\n')

bad = []
SEP = re.compile(r'^\|[\s:\-|]+\|$')


def ncols_of(s):
    """列数 = 未转义的 '|' 个数 - 1（`\\|` 是转义，不算分隔符）。"""
    return s.replace('\\|', '').count('|') - 1


i = 0
while i < len(lines):
    ln = lines[i].strip()
    if ln.startswith('|') and ln.endswith('|') and i + 1 < len(lines) \
            and SEP.match(lines[i + 1].strip()):
        want = ncols_of(ln)
        j = i
        while j < len(lines):
            s = lines[j].strip()
            if not (s.startswith('|') and s.endswith('|')):
                break
            got = ncols_of(s)
            if got != want and not SEP.match(s):
                bad.append((j + 1, want, got, s[:90]))
            j += 1
        i = j
    else:
        i += 1

print('%s: 表头列数不一致的行 %d 处' % (path, len(bad)))
for ln, want, got, s in bad:
    print('  L%-5d 期望 %d 列，实际 %d 列: %s' % (ln, want, got, s))
sys.exit(1 if bad else 0)
