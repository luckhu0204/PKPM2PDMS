# -*- coding: utf-8 -*-
"""只读探针：核对样例文件的事实，供 spec/CONTRACT.md 引用。

运行：python test/probe_samples.py
不写入任何被探针文件的目录（仅打印）。
"""
import io
import os
import sqlite3
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PLUG = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'
SECMAP = os.path.join(PLUG, 'PKPM转PDMS截面匹配文件.txt')
JWD = os.path.join(PLUG, 'JLCJ2.jwd')


def section(t):
    print('\n=== %s ===' % t)


# --------------------------------------------------------------- secmap
section('secmap file')
raw = open(SECMAP, 'rb').read()
print('bytes=%d' % len(raw))
print('has_bom=%s' % raw.startswith(b'\xef\xbb\xbf'))
crlf = raw.count(b'\r\n')
lf = raw.count(b'\n')
print('CRLF=%d LF_total=%d (CRLF==LF means all-CRLF: %s)' % (crlf, lf, crlf == lf))
try:
    txt = raw.decode('gbk')
    print('gbk_strict_decode=OK')
except Exception as e:
    print('gbk_strict_decode=FAIL %s' % e)
    txt = raw.decode('gbk', 'replace')
lines = txt.split('\r\n')
print('physical_lines=%d' % len(lines))

data = 0
comments = 0
blank = 0
bad = 0
noneed = []
for i, ln in enumerate(lines, 1):
    s = ln.strip()
    if not s:
        blank += 1
    elif s.startswith('//'):
        comments += 1
    elif s.startswith('/') and ',' not in s:
        comments += 1  # 整行分隔线 '/'
    elif ',' in s:
        data += 1
        l, r = s.split(',', 1)
        r = r.strip()
        if not r.startswith('/'):
            noneed.append((i, s))
    else:
        bad += 1
        print('  UNPARSED line %d: %r' % (i, s))
print('data=%d comments/sep=%d blank=%d unparsed=%d' % (data, comments, blank, bad))
print('right-values lacking leading slash: %d' % len(noneed))
for i, s in noneed[:8]:
    print('   L%d: %s' % (i, s))

print('--- first 8 lines (1-based) ---')
for i in range(8):
    print('%4d|%s' % (i + 1, lines[i]))
print('--- selected lines ---')
for n in (29, 281, 323, 634, 643, 2842):
    print('%4d|%s' % (n, lines[n - 1]))

# --------------------------------------------------------------- jwd
section('jwd file')
con = sqlite3.connect('file:' + JWD.replace('\\', '/') + '?mode=ro', uri=True)


def dec(b):
    if not isinstance(b, bytes):
        return b
    try:
        return b.decode('ascii')
    except Exception:
        pass
    try:
        return b.decode('utf-8')
    except Exception:
        return b.decode('gbk', 'replace')


con.text_factory = dec
tables = [r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
print('tables=%d' % len(tables))
nonempty = []
for t in tables:
    n = con.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0]
    if n:
        nonempty.append((t, n))
print('nonempty tables=%d rows=%d' % (len(nonempty), sum(n for _, n in nonempty)))
for t, n in nonempty:
    print('  %-24s %d' % (t, n))

section('Z derivation spot-check (pkpmFloor)')
for r in con.execute('SELECT ID, No_, StdFlrID, LevelB, Height FROM pkpmFloor '
                     'ORDER BY LevelB'):
    print('  Floor %s No %s StdFlr %s z_bot=%s z_top=%s' %
          (r[0], r[1], r[2], r[3], r[3] + r[4]))

section('raw byte encoding of pkpmColSect.Name')
con.text_factory = bytes
for r in con.execute('SELECT ID, Name FROM pkpmColSect'):
    nm = r[1]
    if isinstance(nm, bytes) and nm:
        tag = []
        try:
            nm.decode('ascii'); tag.append('ascii-ok')
        except Exception:
            tag.append('not-ascii')
        try:
            nm.decode('utf-8'); tag.append('utf8-ok')
        except Exception:
            tag.append('utf8-fail')
        try:
            nm.decode('gbk'); tag.append('gbk-ok')
        except Exception:
            tag.append('gbk-fail')
        print('  ColSect %s raw=%s %s -> gbk=%r' %
              (r[0], nm.hex(), ','.join(tag), nm.decode('gbk', 'replace')))
for r in con.execute('SELECT ID, Loadname FROM pkpmLoadSect LIMIT 3'):
    nm = r[1]
    print('  LoadSect %s raw=%s' % (r[0], nm.hex() if isinstance(nm, bytes) else nm))

con.close()
print('\nDONE (read-only)')
