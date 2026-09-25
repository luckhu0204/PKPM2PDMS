# -*- coding: utf-8 -*-
"""实施包② 探针 5：.pdt 逐节样本 + 关键统计（只读）。

用法： python test\\pdt_secmap_probe5.py [topic]
"""
import io
import sys
from collections import Counter, defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PLUG = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'
PDT = PLUG + '\\1_PM.pdt'


def fields(text):
    """把一段（可能多行）文本按 KEY= value 拆成 dict[key]=[values]（保留原文）。"""
    out = Ordered = {}
    key = None
    last = None
    for raw in text.split('\n'):
        s = raw.strip()
        if not s:
            continue
        for tok in s.split(','):
            t = tok.strip()
            if not t:
                continue
            if '=' in t:
                k, v = t.split('=', 1)
                k = k.strip()
                last = k
                out.setdefault(k, []).append(v.strip())
            else:
                out.setdefault(last, []).append(t)
    return out


t = open(PDT, 'rb').read().decode('gbk')
L = t.split('\r\n')

topic = sys.argv[1] if len(sys.argv) > 1 else 'all'
print('=== STORY raw L58-68 ===')
for i in range(57, 69):
    print('%5d %r' % (i + 1, L[i]))
print('=== DEFFRAMESECTION first 2 + steel ===')
for i in range(2365, 2376):
    print('%5d %r' % (i + 1, L[i]))
print('=== DEFFRAMESECTION steel (SHAPE=39) ===')
for i, ln in enumerate(L, 1):
    if 'SHAPE=39' in ln:
        print('%5d %r' % (i, ln))
        for j in range(i, i + 4):
            print('%5d %r' % (j + 1, L[j]))
print('=== DEFWASLABSECTION ===')
for i in range(2527, 2534):
    print('%5d %r' % (i + 1, L[i]))
print('=== SETWALL full ===')
for i in range(6727, 6750):
    print('%5d %r' % (i + 1, L[i]))
print('=== SETSLAB first 1 ===')
for i in range(6749, 6754):
    print('%5d %r' % (i + 1, L[i]))
print('=== NET first 3 ===')
for i in range(1305, 1309):
    print('%5d %r' % (i + 1, L[i]))

# ---- stats over records
CUR = None
recs = defaultdict(list)
cur = None
for ln in L:
    if not ln.strip():
        continue
    lead = len(ln) - len(ln.lstrip(' '))
    s = ln.strip()
    if s.startswith('$'):
        CUR = s.split()[0]
        cur = None
        continue
    if s.startswith(';'):
        continue
    if lead <= 4:
        cur = [ln]
        recs[CUR].append(cur)
    else:
        if cur is None:
            print('!! continuation without record: %r' % ln)
        cur.append(ln)

print('\n=== record counts ===')
for k in ['$STORY', '$NODECOOR', '$NET', '$DEFFRAMESECTION', '$DEFWASLABSECTION',
          '$DEFMATERIAL', '$SETELEMENT', '$SETWALL', '$SETSLAB', '$RIGID',
          '$DEFNODELOAD', '$SETNODELOAD', '$DEFLINELOAD', '$SETLINELOAD',
          '$DEFSLABLOAD', '$SETSLABLOAD']:
    print('  %-20s %d records, physical lines=%d'
          % (k, len(recs[k]), sum(len(r) for r in recs[k])))

print('\n=== node Z distribution ===')
idx = {}
for r in recs['$NODECOOR']:
    f = fields('\n'.join(r))
    if 'ID' not in f:
        print('  ?? no ID: %r' % r)
        continue
    idx[int(f['ID'][0])] = f
hist = Counter(float(f['Z'][0]) for f in idx.values())
for z in sorted(hist):
    print('   z=%-10g n=%d' % (z, hist[z]))
print('nodes=%d' % len(idx))
print('floorid values=%s' % Counter(int(f['FLOORID'][0]) for f in idx.values()))

print('\n=== net edges ===')
net = {}
for r in recs['$NET']:
    f = fields('\n'.join(r))
    net[int(f['ID'][0])] = (int(f['NODES'][0]), int(f['NODEE'][0]))
print('nets=%d  dangling=%d' % (len(net), sum(1 for a, b in net.values()
                                              if a not in idx or b not in idx)))
deg = Counter()
for a, b in net.values():
    deg[a] += 1
    deg[b] += 1
iso = [n for n in idx if deg[n] == 0]
print('isolated nodes=%s' % iso)
print('degree histogram=%s' % sorted(Counter(deg.values()).items()))

print('\n=== element stats ===')
el = []
for r in recs['$SETELEMENT']:
    f = fields('\n'.join(r))
    el.append(f)
print('elements=%d' % len(el))
print('TYPE=%s' % Counter(f['TYPE'][0] for f in el))
print('ID==NETID: %d/%d' % (sum(1 for f in el if f['ID'][0] == f['NETID'][0]), len(el)))
netids_used = {int(f['NETID'][0]) for f in el}
print('unused nets (panel edges)=%d' % len(set(net) - netids_used))
print('SECTID set size=%d' % len({f['SECTID'][0] for f in el}))
print('MATID1=%s' % Counter(f['MATID1'][0] for f in el))
nz = [(f['ID'][0], f['ECS1'][0], f['ECE1'][0], f['ECS2'][0], f['ECE2'][0])
      for f in el if (f['ECS1'][0] not in ('0.000', '0') or f['ECE1'][0] not in ('0.000', '0'))]
print('nonzero ECS1/ECE1 elements=%d e.g. %s' % (len(nz), nz[:4]))
print('ANG nonzero=%d' % sum(1 for f in el if f['ANG'][0] not in ('0.000', '0')))

print('\n=== panels ===')
for tag in ('$SETWALL', '$SETSLAB'):
    print(tag, len(recs[tag]))
    f = fields('\n'.join(recs[tag][0]))
    print('   keys=%s' % sorted(f.keys()))
    print('   NUB=%s len(NETID)=%d' % (f['NUB'][0], len(f['NETID'])))
    for k in ('ID', 'TYPE', 'SECTID', 'EXR'):
        print('   %s=%s' % (k, f.get(k)))
# ring closure for all panels: NETID ring -> ordered vertices
print('\n=== ring closure check ===')
bad = 0
ringlen = Counter()
for tag in ('$SETWALL', '$SETSLAB'):
    for r in recs[tag]:
        f = fields('\n'.join(r))
        ids = [int(x) for x in f['NETID']]
        ringlen[len(ids)] += 1
        segs = [net[i] for i in ids]
        # is it a single cycle?
        adj = defaultdict(list)
        for a, b in segs:
            adj[a].append(b)
            adj[b].append(a)
        if any(len(v) != 2 for v in adj.values()) or len(adj) != len(ids):
            bad += 1
print('panel rings with |NETID|!=n_vertices or non-cycle: %d' % bad)
print('ring length histogram=%s' % sorted(ringlen.items()))

print('\n=== RIGID ===')
for r in recs['$RIGID']:
    f = fields('\n'.join(r))
    print('   ID=%s FLOORID=%s NUB=%s len=%d' % (f['ID'][0], f['FLOORID'][0],
                                                 f['NUB'][0], len(f['SLABID'])))
print('DONE')
