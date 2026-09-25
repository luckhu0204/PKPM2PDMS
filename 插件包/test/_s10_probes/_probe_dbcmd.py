# -*- coding: utf-8 -*-
"""侦察：DB Listing 相关语句在 PMLLIB 里的分布（只读）。

1) 哪些 .pmlfnc / .pmlobj / .mac / .pmlfrm 里出现 `alpha file` / `output pass` / `output tabulate` /
   `writealphafile`（命令式调用，且不在窗体里）；
2) 目录/规格元素的类型码写法（`.type eq |XXX|`、`HARDTYPE EQ |XXX|`、`TYPE EQ |XXX|`）。
"""
import os
import re

ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB'
EXTS = ('.pmlfnc', '.pmlfrm', '.pmlobj', '.mac')
CMD_PATTERNS = {
    'alpha file': re.compile(r'(?i)alpha\s+file\b'),
    'writealphafile': re.compile(r'(?i)\bwritealphafile\b'),
    'output pass': re.compile(r'(?i)\boutput\s+pass\b'),
    'output tabulate': re.compile(r'(?i)\boutput\s+tabulate\b'),
    'output (generic)': re.compile(r'(?i)^\s*output\s', re.M),
}
TYPE_WORDS = ['CATE', 'CATALOGUE', 'STSE', 'STSECTION', 'STCA', 'STCATEGORY',
              'SPRF', 'SPRFILE', 'SPWL', 'SPWLD', 'SPEC', 'SPECIFICATION',
              'SELE', 'SELEC', 'SPCO', 'SPCOMPONENT', 'DTSE', 'DTSET',
              'PTSE', 'PTSSET', 'GMSE', 'GMSSET', 'PLIN', 'PLINE']
TYPE_PATTERN = re.compile(r'(?i)(?:\btype\s+(?:eq|of)\s+|HARDTYPE\s+EQ\s+|\btype\s+inset\s*\()')

hits = {k: [] for k in CMD_PATTERNS}
typehits = {}
for dirpath, dirnames, filenames in os.walk(ROOT):
    for fn in filenames:
        if not fn.lower().endswith(EXTS):
            continue
        p = os.path.join(dirpath, fn)
        try:
            t = open(p, 'rb').read().decode('gbk', 'replace')
        except Exception:
            continue
        rel = os.path.relpath(p, ROOT)
        for k, pat in CMD_PATTERNS.items():
            if pat.search(t):
                hits[k].append(rel)
        for i, line in enumerate(t.splitlines(), 1):
            if TYPE_PATTERN.search(line):
                for w in TYPE_WORDS:
                    if re.search(r'(?i)\|\s*%s\s*\|' % re.escape(w), line):
                        key = w.upper()
                        if len(typehits.get(key, [])) < 4:
                            typehits.setdefault(key, []).append('%s:%d: %s' % (rel, i, line.strip()[:120]))
                        break

print('===== 命令式语句出现位置（非窗体的更值钱）')
for k, lst in hits.items():
    print('%-18s %d 个文件' % (k, len(lst)))
    for r in lst[:12]:
        print('     ' + r)

print()
print('===== 目录/规格类型码的写法样例')
for w in TYPE_WORDS:
    key = w.upper()
    if key in typehits:
        print('--- |%s|' % key)
        for s in typehits[key]:
            print('     ' + s)
