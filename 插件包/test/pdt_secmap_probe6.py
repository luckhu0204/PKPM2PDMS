# -*- coding: utf-8 -*-
"""实施包② 探针 6：.pdt 荷载节（分组/正负号/NUB）与材料表（只读）。

用法： python test\\pdt_secmap_probe6.py
"""
import io
import sys
from collections import Counter, defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PLUG = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'
PDT = PLUG + '\\1_PM.pdt'


def fields(rec):
    out = {}
    last = None
    for raw in rec:
        s = raw.strip()
        if not s:
            continue
        for tok in s.split(','):
            t = tok.strip()
            if not t:
                continue
            if '=' in t:
                k, v = t.split('=', 1)
                last = k.strip()
                out.setdefault(last, []).append(v.strip())
            else:
                out.setdefault(last, []).append(t)
    return out


t = open(PDT, 'rb').read().decode('gbk')
L = t.split('\r\n')
CUR = None
GROUP = None
recs = defaultdict(list)   # (group, section) -> list of records
for ln in L:
    if not ln.strip():
        continue
    lead = len(ln) - len(ln.lstrip(' '))
    s = ln.strip()
    if s.startswith('$'):
        CUR = s.split()[0]
        if CUR in ('$DEADLOAD', '$LIVELOAD'):
            GROUP = CUR
        cur = None
        continue
    if s.startswith(';'):
        continue
    if lead <= 4:
        cur = [ln]
        recs[(GROUP, CUR)].append(cur)
    else:
        cur.append(ln)

print('=== grouped record counts ===')
for k in sorted(recs, key=lambda x: (str(x[0]), x[1])):
    print('   %-12s %-16s %d' % (k[0], k[1], len(recs[k])))

print('\n=== DEFMATERIAL ===')
for r in recs[(None, '$DEFMATERIAL')]:
    print('   %s' % ' | '.join(r))

print('\n=== DEFNODELOAD ===')
for r in recs[('$DEADLOAD', '$DEFNODELOAD')]:
    print('   %s' % ' | '.join(r))
print('=== SETNODELOAD ===')
for r in recs[('$DEADLOAD', '$SETNODELOAD')]:
    print('   %s' % ' | '.join(r))

print('\n=== DEFLINELOAD keys/type distribution ===')
st = Counter()
for g in ('$DEADLOAD', '$LIVELOAD'):
    for r in recs[(g, '$DEFLINELOAD')]:
        f = fields(r)
        st[(g, f['TYPE'][0], f['UCS'][0])] += 1
print('   (group, TYPE, UCS) -> %s' % sorted(st.items()))
f = fields(recs[('$DEADLOAD', '$DEFLINELOAD')][0])
print('   sample keys=%s' % list(f.keys()))
for k, v in f.items():
    print('      %-6s len=%d %s' % (k, len(v), v[:4]))
f = fields([r for r in recs[('$DEADLOAD', '$DEFLINELOAD')]
            if fields(r)['TYPE'][0] == '1'][0])
print('   TYPE=1 sample keys=%s' % list(f.keys()))

print('\n=== SETLINELOAD NUB histogram + target check ===')
nub = Counter()
for g in ('$DEADLOAD', '$LIVELOAD'):
    for r in recs[(g, '$SETLINELOAD')]:
        f = fields(r)
        nub[(g, f['NUB'][0], len(f['LOADID']))] += 1
print('   (group, NUB, len) -> %s' % sorted(nub.items()))

print('\n=== DEFSLABLOAD ===')
for g in ('$DEADLOAD', '$LIVELOAD'):
    f = fields(recs[(g, '$DEFSLABLOAD')][0])
    print('   %s keys=%s' % (g, list(f.keys())))

print('\n=== SETSLABLOAD sign/NUB ===')
sign = Counter()
nub = Counter()
lo = []
for g in ('$DEADLOAD', '$LIVELOAD'):
    for r in recs[(g, '$SETSLABLOAD')]:
        f = fields(r)
        ids = [int(x) for x in f['LOADID']]
        sign[(g, tuple(sorted({('neg' if i < 0 else 'pos') for i in ids})))] += 1
        nub[(g, f['NUB'][0], len(ids))] += 1
        lo.append((g, f['ID'][0], ids))
    print('   %s sign=%s' % (g, sorted(k for k in sign if k[0] == g)))
print('   nub=%s' % sorted(nub.items()))
neg = [x for x in lo if x[2] and x[2][0] < 0]
print('   negative-LOADID rows=%s' % neg)

print('\n=== EXR -42 (层内序号) for slabs/walls ===')
for tag in ('$SETWALL', '$SETSLAB'):
    vals = []
    for r in recs[(None, tag)]:
        f = fields(r)
        exr = f['EXR']
        d = {}
        i = 1
        while i + 1 < len(exr) + 1:
            if i + 1 < len(exr):
                d[exr[i]] = exr[i + 1]
            i += 2
        vals.append((f['ID'][0], d.get('-42'), d.get('10005'), d.get('-41')))
    print('   %s: n=%d  first5=%s' % (tag, len(vals), vals[:5]))
    print('      -41 distinct=%s' % sorted({v[3] for v in vals}))
    print('      -42 distinct count=%d min=%s max=%s'
          % (len({v[1] for v in vals}), min(v[1] for v in vals),
             max(v[1] for v in vals)))
print('DONE')
