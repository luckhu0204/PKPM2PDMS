# -*- coding: utf-8 -*-
"""只读探针 2：截面匹配文件的键重复/冲突统计 + jwd 表清单，供 CONTRACT.md 引用。"""
import io
import os
import sqlite3
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
PLUG = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'
SECMAP = os.path.join(PLUG, 'PKPM转PDMS截面匹配文件.txt')

txt = open(SECMAP, 'rb').read().decode('gbk')
lines = txt.split('\r\n')
pairs = []
for i, ln in enumerate(lines, 1):
    s = ln.strip()
    if not s or s.startswith('//'):
        continue
    if s.startswith('/') and ',' not in s:
        continue
    if ',' not in s:
        continue
    l, r = s.split(',', 1)
    l = l.strip()
    r = ' '.join(r.split())
    if not r.startswith('/'):
        r = '/' + r
    pairs.append((i, l, r))

print('pairs=%d' % len(pairs))
key2 = {}
for i, l, r in pairs:
    key2.setdefault(l, []).append((i, r))
dups = {k: v for k, v in key2.items() if len(v) > 1}
print('unique left keys=%d  duplicated keys=%d' % (len(key2), len(dups)))
for k, v in list(dups.items())[:20]:
    print('  DUP %r -> %s' % (k, v))
same = [k for k, v in dups.items() if len({r for _, r in v}) == 1]
print('  of which identical right value: %d' % len(same))
diff = [k for k, v in dups.items() if len({r for _, r in v}) > 1]
print('  conflicting (different right values): %d' % len(diff))
for k in diff[:10]:
    print('    CONFLICT %r -> %s' % (k, dups[k]))

print('\nspec prefixes: %d' % len({r.rsplit('/', 1)[0] for _, _, r in pairs}))
print('sample reversed map entries:')
for l, r in [('HN450X200', None), ('RECT', None)]:
    print('  %s -> %s' % (l, key2.get(l)))

# ---- check that no right-value leaf contains whitespace after normalization
bad_leaf = [p for p in pairs if ' ' in p[2]]
print('right values containing whitespace after normalize: %d' % len(bad_leaf))
for p in bad_leaf[:5]:
    print('   L%d %r' % p)

print('\n=== jwd sqlite_master tables (full) ===')
con = sqlite3.connect('file:' + os.path.join(PLUG, 'JLCJ2.jwd').replace('\\', '/') + '?mode=ro', uri=True)
for (n,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
    c = con.execute('SELECT COUNT(*) FROM "%s"' % n).fetchone()[0]
    print('  %-26s %d' % (n, c))
print('indexes=%d' % con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'").fetchone()[0])
print('user_version=%s' % con.execute('PRAGMA user_version').fetchone()[0])
print('encoding=%s' % con.execute('PRAGMA encoding').fetchone()[0])
con.close()
print('DONE (read-only)')
