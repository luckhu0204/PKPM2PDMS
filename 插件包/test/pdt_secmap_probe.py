# -*- coding: utf-8 -*-
"""实施包② 侦察探针：.pdt 与截面匹配文件的字节级事实（只读样本）。

仅供本包自检/取证使用；引擎代码不得引用本文件。
用法： python test\\pdt_secmap_probe.py [section]
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PLUG = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'
PDT = PLUG + r'\1_PM.pdt'
SECMAP = PLUG + r'\PKPM转PDMS截面匹配文件.txt'
CAT = PLUG + r'\PKPM（PDMS数据库）.txt'

WHAT = sys.argv[1] if len(sys.argv) > 1 else 'all'


def hr(t):
    print('\n===== %s =====' % t)


def probe_pdt_raw():
    hr('pdt raw')
    b = open(PDT, 'rb').read()
    print('bytes=%d bom=%r' % (len(b), b[:3]))
    print('CRLF=%d LF=%d CR=%d' % (b.count(b'\r\n'), b.count(b'\n'), b.count(b'\r')))
    t = b.decode('gbk')
    L = t.split('\r\n')
    print('lines=%d' % len(L))
    for i in list(range(0, 10)) + list(range(len(L) - 4, len(L))):
        print('%5d %r' % (i + 1, L[i][:130]))


def probe_pdt_sections():
    hr('pdt sections / indent')
    t = open(PDT, 'rb').read().decode('gbk')
    L = t.split('\r\n')
    from collections import Counter
    ind = Counter()
    secs = []
    for i, ln in enumerate(L, 1):
        if not ln.strip():
            continue
        lead = len(ln) - len(ln.lstrip(' '))
        ind[lead] += 1
        s = ln.strip()
        if s.startswith('$'):
            secs.append((i, s.split()[0] if s.split() else s))
        elif s.startswith(';'):
            print('comment L%d %r' % (i, ln))
    print('indent distribution: %s' % sorted(ind.items()))
    print('sections (%d):' % len(secs))
    for i, n in secs:
        print('   L%-6d %s' % (i, n))


def probe_pdt_continuation():
    hr('pdt continuation lines (indent>4) samples')
    t = open(PDT, 'rb').read().decode('gbk')
    L = t.split('\r\n')
    cur = None
    n = 0
    for i, ln in enumerate(L, 1):
        if not ln.strip():
            continue
        lead = len(ln) - len(ln.lstrip(' '))
        s = ln.strip()
        if s.startswith('$'):
            cur = s.split()[0]
            continue
        if cur in ('$SETELEMENT', '$SETWALL', '$SETSLAB', '$RIGID',
                   '$NODECOOR', '$STORY', '$DEFLINELOAD', '$SETLINELOAD',
                   '$DEFSLABLOAD', '$SETSLABLOAD', '$DEFNODELOAD', '$SETNODELOAD'):
            if n < 40 and (i < 2600 or cur in ('$RIGID',)):
                print('%5d ind=%d %s' % (i, lead, ln[:150]))
                n += 1


def probe_pdt_multiline():
    hr('pdt multi-physical-line records ($SETELEMENT/$RIGID)')
    t = open(PDT, 'rb').read().decode('gbk')
    L = t.split('\r\n')
    # $RIGID block raw
    start = None
    for i, ln in enumerate(L, 1):
        s = ln.strip()
        if s.startswith('$RIGID'):
            start = i
        if start and i >= start and i < start + 22:
            print('%5d ind=%d %r' % (i, len(ln) - len(ln.lstrip(' ')), ln[:160]))
    print('--- EXR wrap in $SETELEMENT (first 3 records) ---')
    n = 0
    for i, ln in enumerate(L, 1):
        s = ln.strip()
        if s.startswith('$SETELEMENT'):
            n = i
            break
    for i in range(n, n + 8):
        print('%5d ind=%d %r' % (i + 1, len(L[i]) - len(L[i].lstrip(' ')), L[i][:200]))


def probe_secmap():
    hr('secmap file')
    b = open(SECMAP, 'rb').read()
    print('bytes=%d bom=%r' % (len(b), b[:3]))
    print('CRLF=%d LF=%d CR=%d' % (b.count(b'\r\n'), b.count(b'\n'), b.count(b'\r')))
    txt = b.decode('gbk')
    lines = txt.split('\r\n')
    print('lines=%d' % len(lines))
    data = []
    comments = 0
    blanks = 0
    slashes = 0
    bad = []
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if not s:
            blanks += 1
            continue
        if s.startswith('//'):
            comments += 1
            continue
        if set(s) <= set('/'):
            slashes += 1
            continue
        if ',' not in s:
            bad.append((i, s))
            continue
        l, r = s.split(',', 1)
        data.append((i, l.strip(), r))
    print('data=%d comments=%d blanks=%d slashsep=%d unparsable=%d'
          % (len(data), comments, blanks, slashes, len(bad)))
    for x in bad[:10]:
        print('  BAD %r' % (x,))
    nospace = [(i, l, r) for i, l, r in data if not r.strip().startswith('/')]
    print('right values missing leading slash: %d' % len(nospace))
    for x in nospace:
        print('   L%d %r -> %r' % x)
    # normalization
    norm = []
    for i, l, r in data:
        rr = ' '.join(r.split())
        if not rr.startswith('/'):
            rr = '/' + rr
        norm.append((i, l, rr))
    keys = {}
    for i, l, r in norm:
        keys.setdefault(l, []).append((i, r))
    dup = {k: v for k, v in keys.items() if len(v) > 1}
    print('unique left=%d duplicate left=%d' % (len(keys), len(dup)))
    for k, v in list(dup.items())[:10]:
        print('   DUP %r %s' % (k, v))
    pref = {}
    for i, l, r in norm:
        p = r.rsplit('/', 1)[0]
        pref[p] = pref.get(p, 0) + 1
    print('spec prefixes=%d' % len(pref))
    for k in sorted(pref):
        print('   %-34s %d' % (k, pref[k]))
    # case-sensitive duplicates
    lower = {}
    for k in keys:
        lower.setdefault(k.lower(), set()).add(k)
    print('left keys differing only by case: %d'
          % len([v for v in lower.values() if len(v) > 1]))
    for v in list(lower.values()):
        if len(v) > 1 and len(sys.argv) > 2:
            print('   %s' % sorted(v))


def probe_cat():
    hr('catalogue macro')
    b = open(CAT, 'rb').read()
    print('bytes=%d bom=%r' % (len(b), b[:3]))
    txt = b.decode('utf-8-sig')
    lines = txt.splitlines()
    print('lines=%d' % len(lines))
    print('first=%r' % lines[0])
    print('last=%r' % lines[-1])
    comp = set()
    ref = set()
    own = set()
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if s.startswith('NEW SPCOMPONENT '):
            nm = s[len('NEW SPCOMPONENT '):].split()[0]
            comp.add(nm)
        elif s.startswith('NEW SPRFILE '):
            ref.add(s[len('NEW SPRFILE '):].split()[0])
        if '-SPEC' in s and s.startswith('NEW SPCOMPONENT'):
            pass
    print('SPCOMPONENT=%d SPRFILE=%d' % (len(comp), len(ref)))
    print('sample SPCOMPONENT: %s' % sorted(comp)[:6])
    print('sample SPRFILE: %s' % sorted(ref)[:6])


def probe_validate_preview():
    hr('validate preview (secmap right values vs SPCOMPONENT set)')
    b = open(SECMAP, 'rb').read()
    txt = b.decode('gbk')
    pairs = []
    for i, ln in enumerate(txt.split('\r\n'), 1):
        s = ln.strip()
        if not s or s.startswith('//') or set(s) <= set('/') or ',' not in s:
            continue
        l, r = s.split(',', 1)
        l = l.strip()
        r = ' '.join(r.split())
        if not r.startswith('/'):
            r = '/' + r
        pairs.append((i, l, r))
    comp = set()
    owners = set()
    for ln in open(CAT, 'rb').read().decode('utf-8-sig').splitlines():
        s = ln.strip()
        if s.startswith('NEW SPCOMPONENT '):
            nm = s[len('NEW SPCOMPONENT '):].split()[0]
            comp.add(nm)
            seg = nm.lstrip('/').split('/')
            if len(seg) >= 2:
                owners.add(seg[0])
    miss = [(i, l, r) for i, l, r in pairs if r not in comp]
    print('pairs=%d missing=%d' % (len(pairs), len(miss)))
    fam = {}
    for i, l, r in miss:
        fam.setdefault(r.rsplit('/', 1)[0], 0)
        fam[r.rsplit('/', 1)[0]] += 1
    for k in sorted(fam):
        print('   MISS %-36s %d' % (k, fam[k]))
    bowner = sorted({r.lstrip('/').split('/')[0] for _, _, r in miss if len(
        r.lstrip('/').split('/')) >= 2})
    print('missing owners=%s' % bowner)
    print('sample missing:' + str(miss[:3]))


if WHAT in ('all', 'pdt'):
    probe_pdt_raw()
    probe_pdt_sections()
    probe_pdt_multiline()
if WHAT in ('all', 'secmap'):
    probe_secmap()
if WHAT in ('all', 'cat'):
    probe_cat()
if WHAT in ('all', 'missing'):
    probe_validate_preview()
print('\nDONE (read-only)')
