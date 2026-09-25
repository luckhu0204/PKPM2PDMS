# -*- coding: utf-8 -*-
"""实施包⑧ 自检：pdt_write.py（契约 §(j)）。

跑法::

    cd /d "D:\\AI_Work\\PKPM数据解析\\PKPM-JWD导入导出"
    python test\\pdt_write_selfcheck.py

覆盖（任务验收 ①–④ + §j.10 的行式/计数自洽）::

    ① JLCJ2.jwd → canonical → .pdt' → 读回：层标高/构件数/包围盒等价
    ② 生成的 .pdt 能被 pdt_read.read_pdt 读回（同格式自证）+ 无 E- 项
    ③ 段名/行式与 PDMSxCA_Addin121.dll 格式串的逐字核对（本脚本自己从 DLL 提取）
    ④ db2pdt 闭环：目录宏 → 规格 → $DEFFRAMESECTION → pdt_write → 读回（依赖 sectionlib/dbparse）
    §j.10-1 行式静态一致（逐行模板比对）、§j.10-2 计数自洽（EXI/EXR 的 k、NUB）

只读用户样本；产物只写 test\\out\\ 与本脚本自己建的临时目录。
"""
import io
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PKG, 'engine'))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import canonical                                              # noqa: E402
import pdt_read                                               # noqa: E402
import pdt_write                                              # noqa: E402

PLUG = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'
JWD = os.path.join(PLUG, 'JLCJ2.jwd')
SAMPLE_PDT = os.path.join(PLUG, '1_PM.pdt')
CAT = os.path.join(PLUG, 'PKPM（PDMS数据库）.txt')
DLL = os.path.join(PLUG, 'P-TRANS', 'PDMSxCA_Addin121.dll')
OUT = os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)

fails = []
external = []          # 外部依赖（其他实施包）的问题，单列，不算本包的 FAIL


def check(cond, label, detail=''):
    print('  [%s] %s %s' % ('OK' if cond else 'FAIL', label, detail))
    if not cond:
        fails.append(label)


def external_check(cond, label, detail=''):
    """外部依赖（其他实施包）的断言：不通过时只记 external，不计本包 FAIL。"""
    print('  [%s] %s %s' % ('OK' if cond else 'EXTERNAL', label, detail))
    if not cond:
        external.append('%s %s' % (label, detail))


print('=== 0. 环境 ===')
print('  pdt_write at %s' % pdt_write.__file__)
try:
    import sectionlib
    print('  sectionlib: 有（%s）' % os.path.basename(sectionlib.__file__))
except Exception as exc:
    print('  sectionlib: **无**（%s）⇒ 截面将按 §j.7.1 写占位块' % exc)
try:
    import dbparse
    print('  dbparse   : 有（%s）' % os.path.basename(dbparse.__file__))
except Exception as exc:
    print('  dbparse   : **无**（%s）⇒ 验收 ④ 无法按契约路径跑' % exc)

# ---------------------------------------------------------------- ① 往返
print('\n=== ① JLCJ2.jwd → canonical → .pdt\' → 读回 ===')
from jwd_read import read_jwd                                  # noqa: E402
m0 = read_jwd(JWD)
print('  read_jwd counts = %s' % m0.counts())
out_pdt = os.path.join(OUT, 'jwd2pdt_roundtrip.pdt')
opts = pdt_write.PdtOptions(file_note=r'I:\roundtrip\JLCJ2.pdt', time_text='3/19/2025 8:4:27')
rep = pdt_write.write_pdt(m0, out_pdt, opts)
print('  write_pdt: rows=%d ids=%s' % (rep['rows'], rep['ids']))
print('  segments(%d) = %s' % (len(rep['segments']), rep['segments']))
print('  skipped=%d warnings=%d assumptions=%d'
      % (len(rep['skipped']), len(rep['warnings']), len(rep['assumptions'])))
for s in rep['skipped'][:6]:
    print('     skipped: %s' % s)
for w in rep['warnings'][:6]:
    print('     warn   : %s' % w)
raw = open(out_pdt, 'rb').read()
print('  bytes=%d  BOM=%s  CRLF=%d  bareLF=%d  gbk=%s'
      % (len(raw), raw[:3] == b'\xef\xbb\xbf', raw.count(b'\r\n'),
         raw.count(b'\n') - raw.count(b'\r\n'), bool(raw.decode('gbk'))))
check(raw[:3] != b'\xef\xbb\xbf', 'GBK 无 BOM')
check(raw.count(b'\n') == raw.count(b'\r\n'), '全部 CRLF（无裸 LF）')
check(raw.decode('gbk'), 'GBK 严格可解码')

m1 = pdt_read.read_pdt(out_pdt)
c0, c1 = m0.counts(), m1.counts()
print('  readback counts = %s' % c1)
check(c1['members_total'] == c0['members_total'], '构件数等价',
      '%d -> %d' % (c0['members_total'], c1['members_total']))
check(c1['members'] == c0['members'], '构件类型分布等价', '%s -> %s' % (c0['members'], c1['members']))

# 构件几何多重集（type + 端点四舍五入 0.01）
def mem_multiset(m):
    return sorted((x.type, tuple(round(v, 2) for v in x.start),
                   tuple(round(v, 2) for v in x.end)) for x in m.members)


ms0, ms1 = mem_multiset(m0), mem_multiset(m1)
check(ms0 == ms1, '构件 (type, 起点, 终点) 多重集逐条相同', '%d vs %d 条' % (len(ms0), len(ms1)))

# 「应当写出」的那批板/墙（§j.7.3/§j.7.4 的过滤规则，与 pdt_write 内部一致）
m_written = canonical.Model(
    members=[x for x in m0.members],
    slabs=[s for s in m0.slabs if not s.is_hole and s.thickness > 0],
    walls=[w for w in m0.walls if len(w.loop) >= 3])

# 包围盒
def bbox(m):
    pts = [p for x in m.members for p in (x.start, x.end)]
    pts += [(x, y, s.z) for s in m.slabs for (x, y) in s.polygon]
    pts += [p for w in m.walls for p in w.loop]
    return (min(p[0] for p in pts), min(p[1] for p in pts), min(p[2] for p in pts),
            max(p[0] for p in pts), max(p[1] for p in pts), max(p[2] for p in pts))


b0, b1 = bbox(m0), bbox(m1)
print('  bbox0=%s' % (b0,))
print('  bbox1=%s' % (b1,))
check(b0 == b1, '包围盒等价')

# 层标高：$STORY 段逐字保留 + 读回层标高集合 ⊇ 模型的 {z_bot,z_top}
txt = raw.decode('gbk')
story_lines = [l for l in txt.split('\r\n') if l.startswith('       NO=1, HI=')]
print('  $STORY 段（%d 条）: %s' % (len(story_lines), story_lines[:2]))
want = set()
for lv in m0.levels:
    want.add(round(lv.z_bot, 2))
    want.add(round(lv.z_top, 2))
got = {round(lv.z_top, 2) for lv in m1.levels}
print('  模型层标高 {%s…} n=%d；读回层标高 n=%d' % (sorted(want)[:3], len(want), len(got)))
check(want <= got, '模型的每个层标高都出现在读回的平面层里',
      '缺 %s' % sorted(want - got))
story_txt = [re.match(r'       NO=1, HI=([-\d.]+), BL=([-\d.]+), TL=([-\d.]+)', l).groups()
             for l in story_lines]
check(len(story_txt) == len(m0.levels), '$STORY 条数 == 模型层数',
      '%d vs %d' % (len(story_txt), len(m0.levels)))
check(all(abs(float(t[2]) - float(t[1])) - 0.0 >= 0 for t in story_txt), '$STORY BL/TL 可解析')

err1 = m1.errors()
print('  读回模型 errors=%d warnings=%d' % (len(err1), len(m1.warnings())))
for e in err1[:5]:
    print('     E: %s' % e)
check(not err1, '读回模型无 E- 项（§j.10-3）', str(err1[:3]))

# 板/墙顶点集合
def panel_pts(m):
    out = set()
    for s in m.slabs:
        out |= {(round(x, 2), round(y, 2)) for (x, y) in s.polygon}
    for w in m.walls:
        out |= {(round(p[0], 2), round(p[1], 2)) for p in w.loop}
    return out


check(panel_pts(m_written) == panel_pts(m1), '板/墙顶点集合相同（§j.10-3）',
      '%d vs %d 个点' % (len(panel_pts(m_written)), len(panel_pts(m1))))
check(len(m1.slabs) == len(m_written.slabs) and len(m1.walls) == len(m_written.walls),
      '板/墙数量等价（对照「按 §j.7.3/§j.7.4 应当写出」的那批）',
      'slabs %d/%d walls %d/%d' % (len(m_written.slabs), len(m1.slabs),
                                   len(m_written.walls), len(m1.walls)))
n_skip_hole = sum(1 for s in rep['skipped'] if s['what'] == 'slab-hole')
n_skip_no = sum(1 for s in rep['skipped'] if s['what'] == 'slab-nothick')
print('  skipped: slab-hole=%d slab-nothick=%d 合计=%d（原模型 slabs=%d）'
      % (n_skip_hole, n_skip_no, len(rep['skipped']), len(m0.slabs)))
check(n_skip_hole == sum(1 for s in m0.slabs if s.is_hole),
      '板洞逐条进 skipped（§j.7.3）', '%d' % n_skip_hole)
check(n_skip_hole + n_skip_no + len(m_written.slabs) == len(m0.slabs),
      '板「写出 + 跳过」覆盖全部 Slab（不静默丢）')

# ---------------------------------------------------------------- ② 同格式自证
print('\n=== ② 1_PM.pdt → read_pdt → write_pdt → read_pdt（.pdt 源的同格式自证 + 幂等） ===')
m_p = pdt_read.read_pdt(SAMPLE_PDT)
print('  样本读入 counts = %s' % m_p.counts())
out2 = os.path.join(OUT, 'pdt2pdt_roundtrip.pdt')
rep2 = pdt_write.write_pdt(m_p, out2, pdt_write.PdtOptions(
    file_note=r'I:\roundtrip\1_PM.pdt', time_text='3/19/2025 8:4:27'))
print('  write_pdt: rows=%d ids=%s' % (rep2['rows'], rep2['ids']))
print('  segments = %s' % rep2['segments'])
print('  skipped=%d（%s）warnings=%d'
      % (len(rep2['skipped']), Counter(x['what'] for x in rep2['skipped']), len(rep2['warnings'])))
for w in rep2['warnings'][:4]:
    print('     warn: %s' % w)
m_p2 = pdt_read.read_pdt(out2)
c_p, c_p2 = m_p.counts(), m_p2.counts()
print('  读回 counts = %s' % c_p2)
check(c_p2['joints'] == c_p['joints'] and c_p2['members_total'] == c_p['members_total'],
      '.pdt 往返：节点/构件数**完全**等价（节点含孤立节点 55907/59507）',
      '%d/%d 节点, %d/%d 构件' % (c_p['joints'], c_p2['joints'],
                                  c_p['members_total'], c_p2['members_total']))
check(c_p2['walls'] == c_p['walls'] and c_p2['slabs'] == c_p['slabs'],
      '.pdt 往返：墙/板数等价', '%d/%d walls, %d/%d slabs'
      % (c_p['walls'], c_p2['walls'], c_p['slabs'], c_p2['slabs']))
ms_p, ms_p2 = mem_multiset(m_p), mem_multiset(m_p2)
check(ms_p == ms_p2, '.pdt 往返：构件 (type, 起点, 终点) 多重集逐条相同',
      '%d vs %d' % (len(ms_p), len(ms_p2)))
check(not m_p2.errors(), '.pdt 往返：读回无 E- 项', str(m_p2.errors()[:3]))
# 幂等（模 10012 的层内序号）：把读回的模型再写一次，除 10012 外应逐字节相同
out3 = os.path.join(OUT, 'pdt2pdt_idempotent.pdt')
pdt_write.write_pdt(m_p2, out3, pdt_write.PdtOptions(
    file_note=r'I:\roundtrip\1_PM.pdt', time_text='3/19/2025 8:4:27'))


def _norm_seq(path):
    txt = open(path, 'rb').read().decode('gbk')
    return re.sub(r'10012, \d+\.000', '10012, <seq>', txt)


a2, a3 = _norm_seq(out2), _norm_seq(out3)
diffs = sum(1 for x, y in zip(a2.split('\r\n'), a3.split('\r\n')) if x != y)
print('  幂等（模 10012 层内序号）：归一后差分行 = %d；未归一 = %s'
      % (diffs, open(out2, 'rb').read() == open(out3, 'rb').read()))
check(diffs == 0 and len(a2) == len(a3),
      '除 10012 的层内序号外，两遍写出逐字节相同（该字段的语义见 assumptions）',
      '%d 行不同' % diffs)
check(open(out2, 'rb').read() != open(out3, 'rb').read(),
      '未归一化的两遍**确实**不同（= 10012 用了 Member.no，读回后按层内顺序重编）')

print('\n=== ②b 与样本同段序/同空行结构（§j.2） ===')
def seg_index(path):
    lines = open(path, 'rb').read().decode('gbk').replace('\r\n', '\n').split('\n')
    return lines


mine, sample = seg_index(out_pdt), seg_index(SAMPLE_PDT)
mine_heads = [l for l in mine if l.startswith('$')]
sample_heads = [l for l in sample if l.startswith('$')]
print('  mine   heads(%d): %s' % (len(mine_heads), mine_heads))
print('  sample heads(%d): %s' % (len(sample_heads), sample_heads))
check(mine_heads == sample_heads, '段头序列（含荷载分组头）与样本逐字一致')
check(mine[0].startswith(';File ') and ' saved ' in mine[0] and mine[1] == '' and mine[2] == '$VERSION',
      '第 1 行 `;File … saved …`、第 2 行空行、第 3 行 $VERSION（§j.2-3）', mine[0])
check(mine[3] == '   4.2.0', '$VERSION 段体 3 空格 + 4.2.0（§j.2-7）', repr(mine[3]))
check(mine[-1] == '' and mine[-2] == '$END' and mine[-3] == '' and mine[-4] == '',
      '$END 前 2 空行、$END 后 1 空行（§j.2-6）', repr(mine[-4:]))
check(raw[-6:] == b'$END\r\n', '文件以 $END + CRLF 结尾（与样本 bytes[-8:] 同形）',
      repr(raw[-8:]))
check(sample[-1] == '' and sample[-2] == '$END', '样本自身同构（对照）')

# ---------------------------------------------------------------- ①b 逐行模板比对
print('\n=== ①b 逐行模板（§j.4/§j.5，rstrip 后正则比对） ===')
PATS = [
    (r'^;File .+ saved \d+/\d+/\d+ \d+:\d+:\d+$', '首行注释'),
    (r'^   4\.2\.0$', '$VERSION 体'),
    (r'^    (-?[\d.]+, ){19}-?[\d.]+$', '$DESIGNPARA 行（4 空格 + 20 值）'),
    (r'^    ID=\d+, NUB=1$', '$STORY 行1'),
    (r'^       NO=1, HI=-?\d+, BL=-?\d+, TL=-?\d+, WID=-?[\d.]+, LEN=-?[\d.]+, HEI=-?[\d.]+$',
     '$STORY 行2'),
    (r'^    ID= \d+, X= -?[\d.]+, Y= -?[\d.]+, Z= -?[\d.]+, FLOORID= \d+$', '$NODECOOR 行'),
    (r'^       EXR= \d+ ,10005, \d+ ,10012, [\d.e+]+$', '节点 EXR'),
    (r'^    ID=\d+, NODES=\d+, NODEE=\d+$', '$NET 行'),
    (r'^    ID=\d+, NAME=.+, SHAPE=\d+$', '截面行1'),
    (r'^       KIND=\d+, B1=-?[\d.]+, B2=-?[\d.]+, H1=-?[\d.]+, H2=-?[\d.]+, B3=-?[\d.]+, H3=-?[\d.]+$',
     '截面行2'),
    (r'^       T1=-?[\d.]+, T2=-?[\d.]+, T3=-?[\d.]+, T4=-?[\d.]+, T5=-?[\d.]+, T6=-?[\d.]+$',
     '截面行3'),
    (r'^       M=\d+, RI=[\d.]+, RJ=[\d.]+, UA=[\d.]+, NAME1=.*$', '截面行4'),
    (r'^       EXI=1, 10011, \d+$', '截面 EXI'),
    (r'^    ID=\d+, NAME=T-?[\d.g+]+, TYPE=1, T1=[\d.]+, T2=0\.00$', '$DEFWASLABSECTION 行'),
    (r'^    ID=\d+, NAME=\S+, TYPE=2\d\d, ES=\S+, PR=\S+, EXC=\S+, DS=\S+$', '$DEFMATERIAL 行'),
    (r'^    ID=\d+, TYPE=[123], NETID=\d+, SECTID=\d+, MATID1=\d+, MATID2=-9999, '
     r'ECS1=0\.000, ECS2=0\.000, ECS3=0\.000, ECE1=0\.000, ECE2=0\.000, ECE3=0\.000, '
     r'ANG=-?[\d.]+$', '$SETELEMENT 行'),
    (r'^       EXI=3, 10011, \d+, 10013, \d+, 10014, \d+$', '构件/墙板 EXI'),
    (r'^       EXR=\d+(, -?\d+, \S+)+$', '构件/墙板 EXR 首行'),
    (r'^        (-?\d+, \S+(, )?)+$', 'EXR 续行（缩进 8）'),
    (r'^    ID=\d+, TYPE=[56], SECTID=\d+, MATID=\d+, MATID2=0, HOLEID=-9999, EC=0\.0$',
     '墙/板行'),
    (r'^       NUB=\d+, NETID= \d+(, \d+)*$', '墙/板 NUB/NETID'),
    (r'^    ID=\d+, FLOORID=\d+, NUB=\d+$', '$RIGID 组行'),
    (r'^       SLABID= \d+(, \d+)*$', '$RIGID SLABID 首行'),
    (r'^           \d+(, \d+)*$', '$RIGID SLABID 续行（缩进 11）'),
]
body = [l.rstrip() for l in mine]
unmatched = []
for i, l in enumerate(body, 1):
    if l == '' or l.startswith('$') or l.startswith(';'):
        continue
    if not any(re.match(p, l) for p, _ in PATS):
        unmatched.append((i, l))
print('  非空非段头行 %d 条；不匹配任何模板 %d 条'
      % (len([l for l in body if l and not l.startswith('$')]), len(unmatched)))
for i, l in unmatched[:8]:
    print('     L%d %r' % (i, l[:110]))
check(not unmatched, '所有数据行都匹配 §j.4/§j.5 的模板')
check(not any(l != l.rstrip() for l in mine), '无行尾空白（§j.2-8）')

# 缩进检查
inds = Counter(len(l) - len(l.lstrip(' ')) for l in mine if l.strip() and not l.startswith('$'))
print('  缩进分布：%s' % sorted(inds.items()))
check(set(inds) <= {0, 3, 4, 5, 7, 8, 11},
      '缩进只用样本实测的取值集合 {0,3,4,5,7,8,11}', str(sorted(inds)))

# ---------------------------------------------------------------- ③ DLL 逐字核对
print('\n=== ③ 段名/行式 vs PDMSxCA_Addin121.dll 格式串 ===')
data = open(DLL, 'rb').read()
rx = re.compile(rb'(?:[\x20-\x7e]\x00){4,}')
strings = {}
for mm in rx.finditer(data):
    s = mm.group(0).decode('utf-16-le')
    strings.setdefault(s, mm.start())
DLL_EXPECT = {                     # 契约附录 D.1 的关键串 → 本模块对应产物
    '$VERSION': '$VERSION', '$DESIGNPARA': '$DESIGNPARA', '$STORY': '$STORY',
    '$NODECOOR': '$NODECOOR', '$NET': '$NET', '$DEFFRAMESECTION': '$DEFFRAMESECTION',
    '$DEFWASLABSECTION': '$DEFWASLABSECTION', '$DEFMATERIAL': '$DEFMATERIAL',
    '$SETELEMENT': '$SETELEMENT', '$SETWALL': '$SETWALL', '$SETSLAB': '$SETSLAB',
    '$END': '$END',
    '    ID={0}, NAME={1}, SHAPE={2}': '截面行1',
    '       KIND={0}, B1={1}, B2={2}, H1={3}, H2={4}, B3={5}, H3={6}': '截面行2',
    '       T1={0}, T2={1}, T3={2}, T4={3}, T5={4}, T6={5}': '截面行3',
    '       M={0}, RI={1}, RJ={2}, UA={3}, NAME1={4}': '截面行4',
    '       EXI= {0} ': 'EXI 前缀',
    '       EXR= {0} ': 'EXR 前缀（节点形）',
    '    {0:F3},': 'ECS/ECE/ANG 的 3 位小数',
    '    ID={0}, NAME={1}, TYPE={2}, ES={3:G2}, PR={4:G2}, EXC={5:G5}, DS={6:G5}':
        '$DEFMATERIAL',
    '    ID={0}, NODES={1}, NODEE={2}': '$NET',
    '    ID= {0}, X= {1:F2}, Y= {2:F2}, Z= {3:F2}, FLOORID= {4}': '$NODECOOR',
    '    ID={0}, TYPE={1}, NETID={2}, SECTID={3}, MATID1={4}, MATID2={5}, ECS1={6}, '
    'ECS2={7}, ECS3={8}, ECE1={9}, ECE2={10}, ECE3={11}, ANG={12}': '$SETELEMENT',
    '    ID={0}, TYPE={1}, SECTID={2}, MATID={3}, MATID2={4}, HOLEID={5}, EC={6:F1}':
        '$SETWALL/$SETSLAB',
    '       NUB={0}, NETID=': '墙板 NUB/NETID',
    '    ID={0}, NUB={1}': '$RIGID 行（DLL 无 FLOORID，§j.8 裁定以样本为准）',
    '       NO={0}, HI={1}, BL={2}, TL={3}, WID={4:G2}, LEN={5:G2}, HEI={6:G2}': '$STORY',
    '    ID={0}, NAME={1}, TYPE={2}, T1={3:F2}, T2={4:F2}': '$DEFWASLABSECTION',
}
miss = [k for k in DLL_EXPECT if k not in strings]
print('  DLL 里逐字命中的关键串：%d/%d' % (len(DLL_EXPECT) - len(miss), len(DLL_EXPECT)))
for k in miss:
    print('     ** 未命中: %r' % k)
check(not miss, 'DLL 里能逐字找到全部关键格式串（自己提取，非转述）')
for k in ('$NODECOOR', '    ID={0}, NODES={1}, NODEE={2}',
          '    ID={0}, TYPE={1}, SECTID={2}, MATID={3}, MATID2={4}, HOLEID={5}, EC={6:F1}'):
    print('     0x%06X %r' % (strings[k], k))
# DLL 没有的（段名只能以样本为据，§j.8）
absent = [n for n in ('$RIGID', '$DEADLOAD', '$LIVELOAD', '$DEFNODELOAD', '$SETNODELOAD',
                      '$DEFLINELOAD', '$SETLINELOAD', '$DEFSLABLOAD', 'SLABID')
          if data.find(n.encode('utf-16-le')) < 0 and data.find(n.encode('ascii')) < 0]
print('  DLL 中确实**不存在**的名字：%s' % absent)
check(set(absent) == {'$RIGID', '$DEADLOAD', '$LIVELOAD', '$DEFNODELOAD', '$SETNODELOAD',
                      '$DEFLINELOAD', '$SETLINELOAD', '$DEFSLABLOAD', 'SLABID'},
      'DLL 里没有 $RIGID/荷载子段名/SLABID ⇒ 这些以样本 1_PM.pdt 为据（§j.8 留痕）')

# 本模块产出的段头集合 vs 样本段头集合
check(set(mine_heads) == set(sample_heads), '产出段头集合 == 样本段头集合')

# ---- ③b KEY 名与顺序：逐段把 DLL 模板里的 KEY 序列与产物里的 KEY 序列对齐（§j.8 裁定原则）
print('\n=== ③b KEY 名/顺序 逐段对齐 DLL 模板 ===')
DLL_TPL = {
    '$NODECOOR': '    ID= {0}, X= {1:F2}, Y= {2:F2}, Z= {3:F2}, FLOORID= {4}',
    '$NET': '    ID={0}, NODES={1}, NODEE={2}',
    '$DEFFRAMESECTION.1': '    ID={0}, NAME={1}, SHAPE={2}',
    '$DEFFRAMESECTION.2': '       KIND={0}, B1={1}, B2={2}, H1={3}, H2={4}, B3={5}, H3={6}',
    '$DEFFRAMESECTION.3': '       T1={0}, T2={1}, T3={2}, T4={3}, T5={4}, T6={5}',
    '$DEFFRAMESECTION.4': '       M={0}, RI={1}, RJ={2}, UA={3}, NAME1={4}',
    '$DEFWASLABSECTION': '    ID={0}, NAME={1}, TYPE={2}, T1={3:F2}, T2={4:F2}',
    '$DEFMATERIAL': '    ID={0}, NAME={1}, TYPE={2}, ES={3:G2}, PR={4:G2}, EXC={5:G5}, DS={6:G5}',
    '$SETELEMENT': ('    ID={0}, TYPE={1}, NETID={2}, SECTID={3}, MATID1={4}, MATID2={5}, '
                    'ECS1={6}, ECS2={7}, ECS3={8}, ECE1={9}, ECE2={10}, ECE3={11}, ANG={12}'),
    '$SETWALL/$SETSLAB': ('    ID={0}, TYPE={1}, SECTID={2}, MATID={3}, MATID2={4}, '
                          'HOLEID={5}, EC={6:F1}'),
    '$STORY': '       NO={0}, HI={1}, BL={2}, TL={3}, WID={4:G2}, LEN={5:G2}, HEI={6:G2}',
    # $RIGID 不进这张表：DLL 模板只有 ID/NUB、样本还有 FLOORID ⇒ §j.8 冻结「以样本为准」，
    # 下面单独断言（这是**已知差异**，不是失败）。
    '$SETWALL/$SETSLAB.NUB': '       NUB={0}, NETID=',
}
SEL = {
    '$NODECOOR': lambda l: re.match(r'^    ID= \d+, X= ', l),
    '$NET': lambda l: re.match(r'^    ID=\d+, NODES=\d+, NODEE=\d+$', l),
    '$DEFFRAMESECTION.1': lambda l: re.match(r'^    ID=\d+, NAME=.*, SHAPE=\d+$', l),
    '$DEFFRAMESECTION.2': lambda l: l.startswith('       KIND='),
    '$DEFFRAMESECTION.3': lambda l: l.startswith('       T1='),
    '$DEFFRAMESECTION.4': lambda l: l.startswith('       M='),
    '$DEFWASLABSECTION': lambda l: re.match(r'^    ID=\d+, NAME=T', l),
    '$DEFMATERIAL': lambda l: re.match(r'^    ID=\d+, NAME=\S+, TYPE=2\d\d, ES=', l),
    '$SETELEMENT': lambda l: re.match(r'^    ID=\d+, TYPE=[123], NETID=', l),
    '$SETWALL/$SETSLAB': lambda l: re.match(r'^    ID=\d+, TYPE=[56], SECTID=', l),
    '$STORY': lambda l: l.startswith('       NO=1, HI='),
    '$RIGID': lambda l: re.match(r'^    ID=\d+, FLOORID=\d+, NUB=\d+$', l),
    '$SETWALL/$SETSLAB.NUB': lambda l: l.startswith('       NUB=') and 'NETID=' in l,
}
for tag, tpl in DLL_TPL.items():
    dll_keys = re.findall(r'([A-Z][A-Z0-9_]*)=', tpl)
    dll_keys = [k for k in dll_keys if k not in ('F2', 'G2', 'G5', 'F3')]
    lines = [l for l in body if SEL[tag](l)]
    if not lines:
        print('  %-24s DLL keys=%-46s 产物里没有这种行（空段）' % (tag, dll_keys))
        check(tag in ('$SETWALL/$SETSLAB', '$SETWALL/$SETSLAB.NUB'), '%s: 产物无该行' % tag)
        continue
    seqs = {tuple(re.findall(r'([A-Z][A-Z0-9_]*)=', l)) for l in lines}
    ok = all(s[:len(dll_keys)] == tuple(dll_keys) for s in seqs)
    print('  %-24s DLL keys=%s' % (tag, dll_keys))
    for s in sorted(seqs)[:2]:
        print('  %-24s 产物 keys=%s' % ('', list(s)))
    check(ok, '%s: 产物 KEY 名/顺序与 DLL 模板一致' % tag)
# $RIGID：DLL 无 FLOORID、样本有 ⇒ §j.8 裁定以样本为准（这里是"已知差异"，不是错误）
rigid_keys = {tuple(re.findall(r'([A-Z][A-Z0-9_]*)=', l)) for l in body
              if re.match(r'^    ID=\d+, FLOORID=\d+, NUB=\d+$', l)}
check(rigid_keys == {('ID', 'FLOORID', 'NUB')},
      '$RIGID 行含 FLOORID（DLL 模板只有 ID/NUB，§j.8 冻结以样本为准）', str(rigid_keys))

# ---- ③c 数值形态：DLL 的 {…:F2}/{…:F1}/{…:G2}/{…:G5} 与样本实测的小写 e（§j.8/j.9）
print('\n=== ③c 数值形态 vs DLL 的 {…:F2}/{…:F1}/{…:G2}/{…:G5} ===')
mat_line = [l for l in body if re.match(r'^    ID=\d+, NAME=C30, TYPE=262,', l)]
node_line = [l for l in body if re.match(r'^    ID= \d+, X= ', l)]
wall_line = [l for l in body if re.match(r'^    ID=\d+, TYPE=[56], ', l)]
print('  $DEFMATERIAL 样例 = %r' % (mat_line[0] if mat_line else None))
print('  $NODECOOR   样例 = %r' % (node_line[0] if node_line else None))
print('  $SETWALL/板 样例 = %r' % (wall_line[0] if wall_line else None))
check(bool(mat_line) and re.search(r'ES=3e\+04, PR=0\.2, EXC=1e-05, DS=25$', mat_line[0])
      is not None,
      '$DEFMATERIAL：G2/G2/G5/G5 + 小写 e（样本 1_PM.pdt:2535 逐字同形）', mat_line[:1])
check(bool(node_line) and '= ' in node_line[0] and re.search(r'X= -?[\d.]+', node_line[0]),
      '$NODECOOR：ID= / X= 后带空格（DLL 0x02041E 的 "{0}" 布局）', node_line[:1])
check(bool(wall_line) and wall_line[0].endswith('EC=0.0'),
      '墙/板：EC 一位小数（DLL 0x033D24 的 EC={6:F1}）', wall_line[:1])
check(all(re.search(r'ANG=-?\d+\.\d{3}$', l) for l in body if 'ANG=' in l),
      'ANG 三位小数（DLL 0x020154 的 {0:F3}）')
check(not [l for l in body if re.search(r'\b(nan|inf|NaN|Inf)\b', l)],
      '产物里没有 NaN/Inf 等非法数值文本')

# ---------------------------------------------------------------- §j.10-2 计数自洽
print('\n=== §j.10-2 计数自洽（EXI/EXR 的 k、NUB） ===')
bad_k, bad_nub = [], []
for i, l in enumerate(mine):                 # i 为 0-based；mine[i] 的 1-based 行号 = i+1
    mm = re.match(r'^       EXR=(\d+)(,| )', l)
    if mm:
        k = int(mm.group(1))
        pairs = len(re.findall(r'(-?\d+), (-?[\d.e+]+)', l.split('=', 1)[1]))
        j = i + 1
        while j < len(mine) and re.match(r'^        -?\d+,', mine[j]):
            pairs += len(re.findall(r'(-?\d+), (-?[\d.e+]+)', mine[j]))
            j += 1
        if pairs != k:
            bad_k.append((i + 1, k, pairs))
    mm = re.match(r'^       NUB=(\d+), NETID= (.*)$', l)
    if mm:
        n = int(mm.group(1))
        if len([x for x in mm.group(2).split(',') if x.strip()]) != n:
            bad_nub.append((i + 1, n, len(mm.group(2).split(','))))
    mm = re.match(r'^    ID=\d+, FLOORID=\d+, NUB=(\d+)$', l)
    if mm:
        n = int(mm.group(1))
        cnt, j = 0, i + 1
        mm2 = re.match(r'^       SLABID= (.*)$', mine[j]) if j < len(mine) else None
        if mm2:
            cnt += len([x for x in mm2.group(1).split(',') if x.strip()])
            j += 1
            while j < len(mine) and re.match(r'^           \d+(, \d+)*$', mine[j]):
                cnt += len([x for x in mine[j].split(',') if x.strip()])
                j += 1
        if cnt != n:
            bad_nub.append((i + 1, n, cnt))
print('  EXR k 不自治：%d 条 %s' % (len(bad_k), bad_k[:3]))
print('  NUB 不自治：%d 条 %s' % (len(bad_nub), bad_nub[:3]))
check(not bad_k, '每个 EXR 行的 k == 实际组数')
check(not bad_nub, '每个 NUB == 列表长度（墙板 NETID / RIGID SLABID）')

# ---------------------------------------------------------------- ④ db2pdt 闭环
print('\n=== ④a write_pdt_sections（db2pdt 入口，独立于 dbparse） ===')
secs_in = {"beam": [s for s in sorted(m0.sections.values(), key=lambda s: s.id)],
           "col": [], "brace": []}
out4a = os.path.join(OUT, 'db2pdt_sections.pdt')
rep4a = pdt_write.write_pdt_sections(secs_in, out4a, pdt_write.PdtOptions(
    file_note=r'I:\db\PKPMDATA.pdt', time_text='1/2/2026 3:4:5'))
print('  write_pdt_sections: rows=%d segments=%s' % (rep4a['rows'], rep4a['segments']))
print('  skipped=%d（%s）warnings=%d'
      % (len(rep4a['skipped']), Counter(x['what'] for x in rep4a['skipped']),
         len(rep4a['warnings'])))
for s in rep4a['skipped'][:4]:
    print('     skipped: %s' % s)
m4a = pdt_read.read_pdt(out4a)
c4a = m4a.counts()
print('  读回 counts = %s' % c4a)
check(c4a['sections'] == len(secs_in['beam']), '读回截面数 == 输入截面数',
      '%d vs %d' % (c4a['sections'], len(secs_in['beam'])))
check(c4a['members_total'] == 0 and c4a['slabs'] == 0 and c4a['joints'] == 0,
      '§j.7.6：skeleton=full 下几何段为空（0 条记录），$SETELEMENT 空段合法')
check(not m4a.errors(), '读回无 E- 项', str(m4a.errors()[:3]))
# 截面级往返：kind 一致、NAME 保留（或按 §e.1 补名）；
# 可回算的截面 B1/H1（或 d）必须与输入的 B/H（或 d）等值；
# 占位块（§j.7.1 里进 skipped 的那些）按契约**数值全 0**，只要求 kind/NAME 对得上。
skip_ids = {s['id'] for s in rep4a['skipped']}
# §k.3 的 encode_defframesection 表只对 kind ∈ {1, 3, 26(族码39), 39} 定义了 B1/H1；
# 其它 kind（2/303…）的尺寸本来就不在 $DEFFRAMESECTION 里 ⇒ 只要求 kind/NAME 一致。
VALUE_KINDS = (1, 3, 26, 39)
mism = []
for s_in, s_out in zip(secs_in['beam'], sorted(m4a.sections.values(), key=lambda s: s.id)):
    d_in, d_out = dict(s_in.dims or {}), dict(s_out.dims or {})
    b_in = d_in.get("B", d_in.get("B1"))
    h_in = d_in.get("H", d_in.get("H1"))
    d_in_d = d_in.get("d", d_in.get("B1"))
    name_ok = (s_in.name == s_out.name) or (not s_in.name and bool(s_out.name))
    # .pdt 的 SHAPE 与 .jwd 的 Kind 不同值的情形（§k.3）：可回算的 Kind=26（族码 39）
    # 在 .pdt 里是 SHAPE=39；而**占位块**按 §j.7.1 写 SHAPE=<Section.kind> 原样。
    if s_in.id in skip_ids:
        want_kind = int(s_in.kind or 0)
    else:
        want_kind = 39 if int(s_in.kind or 0) == 26 else int(s_in.kind or 0)
    kind_ok = want_kind == int(s_out.kind or 0)
    zeros = all(float(d_out.get(k, 0) or 0) == 0.0
                for k in ("B1", "H1", "d", "T1", "T2", "T3", "T4", "T5", "T6"))
    if int(s_in.kind or 0) not in VALUE_KINDS:
        ok = kind_ok and name_ok                    # 尺寸不在 .pdt 字段里（§k.3 表）
    elif s_in.id in skip_ids:
        ok = placeholder_ok = zeros and kind_ok and name_ok     # §j.7.1 占位块
    else:
        ok = (kind_ok and name_ok
              and (b_in is None or float(d_out.get("B1", 0) or 0) == float(b_in))
              and (h_in is None or float(d_out.get("H1", 0) or 0) == float(h_in))
              and (d_in_d is None or float(d_out.get("d", d_out.get("B1", 0)) or 0)
                   == float(d_in_d)))
    if not ok:
        mism.append((s_in.id, s_in.kind, s_out.kind, s_in.name, s_out.name,
                     dict((k, d_in[k]) for k in ("B", "H", "B1", "H1", "d")
                           if k in d_in), dict(d_out)))
print('  占位块截面（§j.7.1）= %d 个；截面级往返不一致：%d %s'
      % (len(skip_ids), len(mism), mism[:1]))
check(not mism, 'db2pdt：Kind/NAME 逐条保留（或按 §e.1 补名）；kind∈%s 的 B1/H1/d 等值；'
                '占位块数值全 0（§j.7.1）' % (VALUE_KINDS,))
# 行式模板/KEY 顺序对 ④a 的产物也成立
b4 = [l.rstrip() for l in open(out4a, 'rb').read().decode('gbk').replace('\r\n', '\n').split('\n')]
un4 = [l for l in b4 if l and not l.startswith('$') and not l.startswith(';')
       and not any(re.match(p, l) for p, _ in PATS)]
print('  §j.4/§j.5 模板不匹配行：%d %s' % (len(un4), un4[:2]))
check(not un4, '④a 产物同样满足 §j.4/§j.5 行式模板')

out4b = os.path.join(OUT, 'db2pdt_sections_only.pdt')
rep4b = pdt_write.write_pdt_sections(secs_in, out4b,
                                     pdt_write.PdtOptions(skeleton='sections-only'))
b4b = [l for l in open(out4b, 'rb').read().decode('gbk').replace('\r\n', '\n').split('\n')
       if l.startswith('$')]
print('  skeleton=sections-only 的段头 = %s' % b4b)
check(b4b == ['$VERSION', '$DESIGNPARA', '$DEFFRAMESECTION', '$END'],
      '§j.7.6：sections-only 只写 首行+$VERSION+$DESIGNPARA+$DEFFRAMESECTION+$END')
check(len(pdt_read.read_pdt(out4b).sections) == len(secs_in['beam']),
      'sections-only 产物读回截面数不变')

print('\n=== ④b db2pdt 全闭环（目录宏 → 规格 → $DEFFRAMESECTION → pdt_write → 读回） ===')
try:
    import dbparse
    import sectionlib                                          # noqa: F401
    have = True
except Exception as exc:
    have = False
    print('  **跳过**：%s（依赖其他实施包的 engine/dbparse.py）' % exc)
if have:
    try:
        import secmap
        sm = secmap.SectionMap.load(os.path.join(PLUG, 'PKPM转PDMS截面匹配文件.txt'))
        db_rep = {}
        table = dbparse.parse_db_macro_file(
            CAT, secmap=sm, builtin=sectionlib.load_builtin_table())
        recs = getattr(table, 'recs', [])
        print('  dbparse: %d 条规格（给了 secmap + builtin，§l.5 的 pkpm_name/family_code 反查）'
              % len(recs))
        secs4 = table.to_jwd_sections(report=db_rep)
        n4 = sum(len(v) for v in secs4.values())
        print('  to_jwd_sections: %d 条（%s）' % (n4, {k: len(v) for k, v in secs4.items()}))
        print('  sectionlib 报告：skipped=%d unknown=%d group_basis=%s'
              % (len(db_rep.get('skipped', [])), len(db_rep.get('unknown', [])),
                 db_rep.get('group_basis')))
        for s in db_rep.get('skipped', [])[:4]:
            print('     skipped: %s' % {k: s[k] for k in ('what', 'pkpm_name', 'kind', 'why')
                                        if k in s})
        out_db = os.path.join(OUT, 'db2pdt.pdt')
        rep4 = pdt_write.write_pdt_sections(secs4, out_db,
                                            pdt_write.PdtOptions(skeleton='full'))
        print('  write_pdt_sections: rows=%d segments=%s' % (rep4['rows'], rep4['segments']))
        m4 = pdt_read.read_pdt(out_db)
        print('  读回 counts = %s' % m4.counts())
        check(not m4.errors(), 'db2pdt 产物读回无 E- 项', str(m4.errors()[:3]))
        # §0.4-10（R3 复核发现⑤）：write_pdt_sections 按截面身份（Section.id）去重 ——
        # to_jwd_sections 把同一 Section 对象放进 col+brace 两表（n4 含同体复制），
        # 读回数应等于**唯一 sid 数**，不是 n4。
        n4_unique = len({s.id for v in secs4.values() for s in v})
        check(m4.counts()['sections'] == n4_unique, '读回截面数 == 反算输入的唯一截面数',
              '%d vs %d（含同体复制的输入 %d）'
              % (m4.counts()['sections'], n4_unique, n4))
        kinds = Counter(s.kind for s in m4.sections.values())
        print('  读回截面 Kind 分布 = %s' % sorted(kinds.items()))
        print('  读回截面名样例 = %s' % sorted(s.name for s in m4.sections.values()
                                                if s.name)[:6])
        # 闭环判据（§l.6-1）：反算结果再喂回 pdt2db（这里用 secmap 侧做等价性抽查）
        back_specs, back_specs_norm = set(), set()
        slash = [s.name for s in m4.sections.values() if (s.name or "").startswith("/")]
        for s in m4.sections.values():
            r = sm.resolve(s, 'col')
            if r.spec_path:
                back_specs.add(r.spec_path)
            s2 = canonical.Section(id=s.id, kind=s.kind, mat=s.mat,
                                   name=(s.name or "").lstrip("/"),
                                   dims=dict(s.dims), table=s.table, note=s.note)
            r2 = sm.resolve(s2, 'col')
            if r2.spec_path:
                back_specs_norm.add(r2.spec_path)
        print('  读回后用 secmap 反解出规格：原名 %d 个；名字去掉前导 "/" 后 %d 个'
              % (len(back_specs), len(back_specs_norm)))
        print('  **上游数据缺陷留痕**：dbparse 给的 pkpm_name 有 %d/%d 以 "/" 开头'
              '（§l.5 说它应是匹配文件逆查的名字，secmap.reverse 返回的**不带** "/"）；'
              '样例 %s' % (len(slash), len(m4.sections), slash[:3]))
        external.append(
            '外部依赖（engine/dbparse.py）：pkpm_name 全部带前导 "/"（%d 条；'
            'secmap.reverse 的正确结果是 %r），导致 db2pdt 反算出的 $DEFFRAMESECTION '
            'NAME 带 "/"、闭环（§l.6-1）无法逐个相等。证据：见本段上方 print。'
            % (len(slash), sm.reverse('/H_INTERNATIONAL-SPEC/HM148X100')))
        check(n4 > 0 and len(back_specs_norm) > 0,
              '④ 闭环：反算的截面名/尺寸能再解析回 PDMS 规格（名字按 §l.5 去掉上游多加的 "/" 后）',
              'sections=%d specs=%d（原名 %d）' % (n4, len(back_specs_norm), len(back_specs)))
        external_check(len(back_specs) == len(back_specs_norm),
                       '④ 闭环：**不改上游名字**时也应逐个相等（§l.6-1）',
                       '原名解析 %d vs 去 "/" 后 %d' % (len(back_specs), len(back_specs_norm)))
    except Exception as exc:
        import traceback
        traceback.print_exc()
        check(False, '④b db2pdt 闭环（见上方 traceback）')
else:
    print('  注：本项**未跑**（依赖其他实施包的 engine/dbparse.py）')

print('\n=== 结论 ===')
print('  本包 FAIL 项: %d %s' % (len(fails), fails))
print('  外部依赖问题（其他实施包，见上）: %d' % len(external))
for e in external:
    print('     ! %s' % e)
print('DONE (read-only on user samples)')
sys.exit(1 if fails else 0)
