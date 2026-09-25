# -*- coding: utf-8 -*-
"""实施包② 探针 3：JLCJ2.jwd 的三张截面表 + 用原件匹配文件判定哪些会 unresolved（只读）。

用法： python test\\pdt_secmap_probe3.py
"""
import io
import sqlite3
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PLUG = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'
JWD = PLUG + '\\JLCJ2.jwd'
SECMAP = PLUG + '\\PKPM转PDMS截面匹配文件.txt'


def dec(b):
    if not isinstance(b, bytes):
        return b
    for enc in ('ascii', 'utf-8'):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode('gbk', 'replace')


con = sqlite3.connect('file:' + JWD.replace('\\', '/') + '?mode=ro', uri=True)
con.text_factory = dec

# original match file
keys = {}
for i, ln in enumerate(open(SECMAP, 'rb').read().decode('gbk').split('\r\n'), 1):
    s = ln.strip()
    if not s or s.startswith('//') or ',' not in s:
        continue
    l, r = s.split(',', 1)
    l = l.strip()
    r = ' '.join(r.split())
    if not r.startswith('/'):
        r = '/' + r
    keys[l] = r

used = {}
for tab, col in (('pkpmBeamSect', 'beam'), ('pkpmColSect', 'col'),
                 ('pkpmBraceSect', 'brace')):
    print('=== %s ===' % tab)
    for row in con.execute('SELECT ID, No_, Name, Mat, Kind, ShapeVal FROM "%s"' % tab):
        sid, no, name, mat, kind, sv = row
        params = [t for t in sv.split(',')]
        while params and params[-1] == '':
            params.pop()
        body = params[1:-2] if len(params) >= 3 else []
        cks = []
        if name:
            cks.append(name)
        if kind == 26:
            sub = body[1] if len(body) > 1 else ''
            cks.append('%s-%s' % (sub, name))
        if kind == 303 and len(body) >= 6:
            buf = bytearray()
            for t in body[0:6]:
                v = int(float(t or 0))
                buf.append(v & 0xFF)
                buf.append((v >> 8) & 0xFF)
            spec = bytes(buf).split(b'\x00')[0].decode('ascii')
            lib = body[25] if len(body) > 25 else ''
            cks.append('%s-%s' % (lib, spec))
        cks.append('%s#%s' % (kind, ','.join(body)))
        hit = None
        for c in cks:
            if c and c in keys:
                hit = (c, keys[c])
                break
        print('  %6d No_=%-4s kind=%-4s mat=%-3s name=%-24s' % (sid, no, kind, mat, name or ''))
        print('         body=%s' % (body,))
        print('         cand=%s' % (cks,))
        print('         -> %s' % (hit,))
        used.setdefault(hit[0] if hit else 'MISS-%d' % kind, []).append((tab, sid, name, cks))
print('\n=== summary ===')
for k in sorted(used):
    print('  %-40s %d' % (k, len(used[k])))
con.close()
print('DONE')
