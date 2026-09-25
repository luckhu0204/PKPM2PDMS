# -*- coding: utf-8 -*-
"""只读探针 3b：EXI/EXR/NETID/SLABID 的行长与折行规则（冻结 pdt_write 折行阈值用）。"""
import io
import re
import sys
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
PDT = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\1_PM.pdt'
lines = open(PDT, 'rb').read().decode('gbk').split('\r\n')


def pairs_of(s):
    return len(re.findall(r'(-?\d+)\s*,\s*(-?[\d.eE+-]+)', s))


def indent(s):
    return len(s) - len(s.lstrip())


def stats(label, sel, ncounter):
    v = [l for l in lines if sel(l.strip())]
    if not v:
        print('%-26s (无)' % label)
        return
    lens = [len(l) for l in v]
    print('%-26s n=%-5d len min=%-4d max=%-4d  缩进=%s  %s=%s' % (
        label, len(v), min(lens), max(lens),
        sorted({indent(l) for l in v}), ncounter, sorted(Counter(ncounter(l) for l in v).items())[:8]))


print('== EXR 行 ==')
for tag, sel in (('首行(缩进7)', lambda s: s.startswith('EXR=')),
                 ('续行(缩进8/11)', lambda s: False)):
    pass
exr = [(i + 1, l) for i, l in enumerate(lines) if l.lstrip().startswith('EXR=')]
print('n=%d' % len(exr))
first = [(n, l, pairs_of(l)) for n, l in exr]
print('首行 对数 min=%d max=%d；行长 max=%d' %
      (min(p for _, _, p in first), max(p for _, _, p in first),
       max(len(l) for _, l, _ in first)))
# 续行：EXR 行的下一行（非关键字行）
cont = []
for i, l in enumerate(lines):
    if l.lstrip().startswith('EXR=') and i + 1 < len(lines):
        nxt = lines[i + 1]
        if nxt.startswith(' ') and re.match(r'^\s+-?\d+,', nxt):
            cont.append((i + 2, nxt, pairs_of(nxt)))
print('续行 n=%d 对数 min=%d max=%d 行长 max=%d 缩进=%s' % (
    len(cont), min(p for _, _, p in cont), max(p for _, _, p in cont),
    max(len(l) for _, l, _ in cont), sorted({indent(l) for _, l, _ in cont})))
print('首行+续行 的合并对数（每记录的 EXR 总对数）分布（前 12）:')
tot = Counter()
for n, l, p in first:
    q = p
    if n < len(lines) and re.match(r'^\s+-?\d+,', lines[n]):
        q += pairs_of(lines[n])
    tot[q] += 1
print('   %r' % sorted(tot.items()))
print('超长行（>150）: %d' % len([1 for _, l in exr if len(l) > 150]))

print('\n== 其它行的行长上限 ==')
for label, pat in (('EXI 首行', r'^EXI='), ('NUB..NETID 行', r'^NUB=\d+, NETID='),
                   ('SLABID 行', r'^SLABID='), ('SLABID 续行', r'^\s+\d{5,6},.*\d$')):
    v = [l for l in lines if re.match(pat, l)]
    if not v:
        print('%-16s (无)' % label)
        continue
    ids = [len(re.findall(r'\d{4,6}', l)) for l in v]
    print('%-16s n=%-5d len max=%-4d 元素数 min=%d max=%d 缩进=%s' %
          (label, len(v), max(len(l) for l in v), min(ids), max(ids),
           sorted({indent(l) for l in v})))

print('\n== 各段"数据行 + 1 空行"规则核对 ==')
heads = [i for i, l in enumerate(lines) if l.startswith('$')]
for h in heads:
    nxt = lines[h + 1] if h + 1 < len(lines) else ''
    print('  L%-6d %-18s 下一行=%r' % (h + 1, lines[h], nxt[:40]))

print('\n== 文件尾 ==')
for n in range(len(lines) - 5, len(lines)):
    print('  L%-6d %r' % (n + 1, lines[n]))
print('\nDONE')
