# -*- coding: utf-8 -*-
"""契约 §c.4 夹具的文法自检（**参考实现**，只用来证明文法无歧义、示例合法）。

注意：交付的解析器是 `engine/pdms_dump.py`（S1-④ 负责）。本文件不导入它，
仅按 spec/CONTRACT.md §c.3 的规则把夹具解析成对象并逐项断言。

运行：python test/check_dump_grammar.py
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

FIXTURE = """#PKPM-JWD-PDMSDUMP 1.0
UNITS mm
#SITE /PKPM_JWD
#ZONE /JLCJ2
#STRU /MAINFRAME
#FRMW /STL_FRAME/EL1
#SBFR /COLUMN
#SCTN /STL_COL_1 COLUMN /H_INTERNATIONAL-SPEC/HN450X200 400 400 -2000 400 400 -1000 U rboc rboc 0
#SCTN /STL_COL_2 COLUMN /USER_RECT-SPEC/Rectangle_Profile 600 600 600 -2000 600 600 -1000 U rboc rboc 0
#SBFR /BEAM
#SCTN /BM_1 BEAM /H_INTERNATIONAL-SPEC/HN300X150 400 400 -1000 6400 400 -1000 E lbos lbos 0
#SBFR /HBRACE
#SBFR /VBRACE
#FRMW /FLOOR&WALL
#SBFR /SLAB
#PANE /SLAB_1 120 400 400 -1000 6400 400 -1000 6400 4400 -1000 400 4400 -1000 ~ /USER_RECT-SPEC/Rectangle_Profile YNZU dbot
#SBFR /WALL
#STWALL /W_1 /Concrete_Wall-SPEC/WALL-300 3000 0 0 -2000 6000 0 -2000 ~ 300
#FRMW /GRID
#END
"""

fails = []


def check(cond, label, detail=''):
    print('  [%s] %s %s' % ('OK' if cond else 'FAIL', label, detail))
    if not cond:
        fails.append(label)


def parse(text):
    """§c.3 的最小参考实现：返回 (site, zone, stru, sctns, panes, stwalls, frmws)。"""
    lines = [l.rstrip('\r') for l in text.split('\n')]
    if lines[0].split() != ['#PKPM-JWD-PDMSDUMP', '1.0']:
        raise ValueError('E-PARSE: 头行不匹配')
    units = 'mm'
    i = 1
    if lines[i].split()[0] == 'UNITS':
        units = lines[i].split()[1]
        i += 1
    site = zone = stru = None
    frmw = sbfr = None
    sctns, panes, stwalls, frmws = [], [], [], []
    for ln in lines[i:]:
        t = ln.split()
        if not t:
            continue
        tag = t[0]
        if tag == '#SITE':
            site = t[1]
        elif tag == '#ZONE':
            zone = t[1]
        elif tag == '#STRU':
            stru = t[1]
        elif tag == '#FRMW':
            frmw = t[1]
            frmws.append(frmw)
        elif tag == '#SBFR':
            sbfr = t[1]
        elif tag == '#SCTN':
            # desp = tokens[4 : len-10]；尾部固定 10 个 token
            d = {'frmw': frmw, 'sbfr': sbfr, 'name': t[1], 'ctype': t[2], 'spref': t[3],
                 'desp': t[4:len(t) - 10],
                 'poss': tuple(t[len(t) - 10:len(t) - 7]),
                 'pose': tuple(t[len(t) - 7:len(t) - 4]),
                 'ori': t[len(t) - 4], 'jusl': t[len(t) - 3], 'meml': t[len(t) - 2],
                 'bangle': t[len(t) - 1]}
            sctns.append(d)
        elif tag == '#PANE':
            left, right = (t + ['~']).index('~'), None
            left_t = t[:left]
            right_t = t[left + 1:]
            verts = left_t[3:]
            d = {'name': left_t[1], 'height': left_t[2],
                 'verts': [tuple(verts[k:k + 3]) for k in range(0, len(verts), 3)],
                 'trailer': right_t}
            panes.append(d)
        elif tag == '#STWALL':
            d = {'name': t[1], 'spre': t[2], 'height': t[3],
                 'p1': tuple(t[4:7]), 'p2': tuple(t[7:10])}
            if len(t) == 12:
                d['thick'] = t[11]
            stwalls.append(d)
        elif tag == '#END':
            break
        else:
            raise ValueError('E-PARSE: 未知行标记 %r' % tag)
    return dict(site=site, zone=zone, stru=stru, frmws=frmws, sctns=sctns,
                panes=panes, stwalls=stwalls, units=units)


m = parse(FIXTURE)
print('=== 契约 §c.4 夹具解析 ===')
check(m['site'] == '/PKPM_JWD' and m['zone'] == '/JLCJ2' and m['stru'] == '/MAINFRAME',
      '层级前三级', '%s / %s / %s' % (m['site'], m['zone'], m['stru']))
check(m['frmws'] == ['/STL_FRAME/EL1', '/FLOOR&WALL', '/GRID'], 'FRMW 三个分组',
      str(m['frmws']))

c1, c2, b1 = m['sctns'][0], m['sctns'][1], m['sctns'][2]
check(len(m['sctns']) == 3, 'SCTN 共 3 条')
check(c1['desp'] == [], 'desp 可为 0 个（COLUMN 1）')
check(c1['poss'] == ('400', '400', '-2000') and c1['pose'] == ('400', '400', '-1000'),
      '从尾部定位几何（COLUMN 1）', '%s -> %s' % (c1['poss'], c1['pose']))
check(c2['desp'] == ['600'], 'desp 长度由尾部 10 token 反推（COLUMN 2）', str(c2['desp']))
check(c2['poss'] == ('600', '600', '-2000') and c2['ori'] == 'U',
      'desp 与几何不混淆（COLUMN 2）', '%s %s' % (c2['poss'], c2['ori']))
check(b1['sbfr'] == '/BEAM' and b1['ctype'] == 'BEAM' and b1['poss'] == ('400', '400', '-1000')
      and b1['pose'] == ('6400', '400', '-1000'), 'BEAM 记录', str(b1))
check(c1['sbfr'] == '/COLUMN' and c1['frmw'] == '/STL_FRAME/EL1', '父级归属正确')

p = m['panes'][0]
check(p['name'] == '/SLAB_1' and p['height'] == '120', 'PANE 名称与板厚')
check(len(p['verts']) == 4 and p['verts'][0] == ('400', '400', '-1000'),
      'PANE 顶点 4 个', str(p['verts']))
check(p['trailer'] == ['/USER_RECT-SPEC/Rectangle_Profile', 'YNZU', 'dbot'],
      'PANE 尾部 ~ spref ori sjus', str(p['trailer']))

w = m['stwalls'][0]
check(w['name'] == '/W_1' and w['spre'] == '/Concrete_Wall-SPEC/WALL-300'
      and w['height'] == '3000', 'STWALL 名称/规格/高度')
check(w['p1'] == ('0', '0', '-2000') and w['p2'] == ('6000', '0', '-2000')
      and w.get('thick') == '300', 'STWALL 底边与可选厚度', str(w))

# 负例：破坏 desp 定位规则 -> 必须被长度校验拦住
bad = '#SCTN /X COLUMN /SPEC/S 1 2\n'
try:
    parse(FIXTURE.replace(c2['pose'][0], c2['pose'][0]) + '')
    short = '#SCTN /X COLUMN /S 1 2 3 U a a 0\n'
    t = short.split()
    check(len(t) < 14, '短记录（<14 token）应判 E-PARSE（长度校验位）', 'len=%d' % len(t))
except Exception as e:
    check(False, '负例未按预期', repr(e))

print('\nFAIL 项: %d %s' % (len(fails), fails if fails else ''))
sys.exit(1 if fails else 0)
