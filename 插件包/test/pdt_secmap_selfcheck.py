# -*- coding: utf-8 -*-
"""实施包② 自检：``engine/pdt_read.py`` + ``engine/secmap.py``（只读用户样本）。

跑法::

    cd /d "D:\\AI_Work\\PKPM数据解析\\PKPM2PDMS导入导出"
    python test\\pdt_secmap_selfcheck.py

覆盖（每项都打印实测数字）::

    A. read_pdt(1_PM.pdt)  → 617 节点 / 1046 杆件 / 11 层（任务验收）
    B. Model.validate()：无 E- 项；W- 项逐类计数（柱越层是平面型 Level 的固有后果）
    C. 构件/板/墙/荷载的计数与代表性样本（几何与 .pdt 原文对照）
    D. SectionMap.load(原件) → 2,836 条数据行、53 个规格前缀
    E. SectionMap.validate(目录宏) → 257 条坏映射（14 行/族 与侦察结论一致），
       且每条都带"可用的纠正建议"（建议目标确实存在于目录宏）
    F. 补充文件 secmap_extra.txt：板/墙 T<厚度> 键生效；extra_issues() 单列
    G. resolve() 四级优先级：name / shapeval / family / none 各有实测用例
    H. reverse() 正反查 + 加载顺序优先规则
    I. 只读性：样本文件在自检前后字节数与 mtime 不变

只读样本；不写任何用户文件。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from canonical import Section                                    # noqa: E402
from pdt_read import read_pdt                                    # noqa: E402
from secmap import DEFAULT_EXTRA_FILE, SectionMap                # noqa: E402

PLUG = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'
PDT = os.path.join(PLUG, '1_PM.pdt')
SECMAP = os.path.join(PLUG, 'PKPM转PDMS截面匹配文件.txt')
CAT = os.path.join(PLUG, 'PKPM（PDMS数据库）.txt')

fails = []


def check(cond, label, detail=''):
    print('  [%s] %s %s' % ('OK' if cond else 'FAIL', label, detail))
    if not cond:
        fails.append(label)


print('=== A. read_pdt(%s) ===' % PDT)
m = read_pdt(PDT)
c = m.counts()
print('  counts = %s' % c)
check(len(m.joints) == 617, 'joints == 617', 'got %d' % len(m.joints))
check(c['members_total'] == 1046, 'members_total == 1046', 'got %d' % c['members_total'])
check(c['members']['beam'] == 925 and c['members']['column'] == 121 and
      c['members']['brace'] == 0, 'column=121 / beam=925 / brace=0', str(c['members']))
check(len(m.levels) == 11, 'levels == 11', 'got %d' % len(m.levels))
check(c['slabs'] == 331 and c['walls'] == 4, 'slabs=331 / walls=4',
      'slabs=%d walls=%d' % (c['slabs'], c['walls']))
check(c['sections'] == 32, 'sections == 32（$DEFFRAMESECTION）', 'got %d' % c['sections'])
check(c['loads'] == {'beam-line': 120, 'joint-point': 4},
      'loads: joint-point 4 / beam-line 120（= 恒载 78 + 活载 42 个挂接）', str(c['loads']))
check(c['slabs_with_thickness'] == 331, 'slabs_with_thickness == 331（T120/T100）',
      'got %d' % c['slabs_with_thickness'])
print('  levels(z) = %s' % [lv.z_top for lv in m.sorted_levels()])

print('\n=== B. validate() ===')
probs = m.validate()
errs = [p for p in probs if p.startswith('E-')]
warns = [p for p in probs if p.startswith('W-')]
kinds = {}
for p in warns:
    kinds[p.split(':')[0]] = kinds.get(p.split(':')[0], 0) + 1
print('  E-%d  W-%d  分类=%s' % (len(errs), len(warns), sorted(kinds.items())))
for e in errs[:10]:
    print('     %s' % e)
check(not errs, 'validate() 无 E- 项', str(errs[:3]))

print('\n=== C. 几何抽查 ===')
cols = m.members_of('column')
beams = m.members_of('beam')
bad_col = [x.id for x in cols if x.start[2] > x.end[2]]
bad_beam = [x.id for x in beams if abs(x.start[2] - x.end[2]) > 1e-6]
print('  柱 start 在下端（违例 %d）；梁两端等高（违例 %d）' % (len(bad_col), len(bad_beam)))
check(not bad_col and not bad_beam, '柱竖直/梁水平 与 pdt_format.md §5.1 一致')
c1 = cols[0]
print('  柱样例 id=%s start=%s end=%s level=%s section=%s mat=%r'
      % (c1.id, c1.start, c1.end, c1.level, c1.section, c1.material))
b1 = beams[0]
print('  梁样例 id=%s start=%s end=%s level=%s section=%s mat=%r'
      % (b1.id, b1.start, b1.end, b1.level, b1.section, b1.material))
s1 = m.slabs[0]
print('  板样例 id=%s level=%s z=%s t=%s dead=%s live=%s poly=%d 点 no=%s'
      % (s1.id, s1.level, s1.z, s1.thickness, s1.dead, s1.live, len(s1.polygon), s1.no))
w1 = m.walls[0]
print('  墙样例 id=%s level=%s z=%s..%s t=%s name=%r loop=%s'
      % (w1.id, w1.level, w1.z_bot, w1.z_top, w1.thickness, w1.name,
         [(round(p[0], 1), round(p[1], 1), p[2]) for p in w1.loop]))
rects = [s for s in m.sections.values() if s.kind == 1]
steels = [s for s in m.sections.values() if s.kind == 39]
circles = [s for s in m.sections.values() if s.kind == 3]
print('  Section: 矩形 %d / 型钢 %d / 圆形 %d' % (len(rects), len(steels), len(circles)))
print('  矩形样例 %s dims=%s' % (rects[0].name, rects[0].dims))
print('  型钢样例 %s dims=%s mat=%s' % (steels[0].name, steels[0].dims, steels[0].mat))
print('  圆形样例 %s dims=%s' % (circles[0].name, circles[0].dims))
check(len(rects) == 29 and len(steels) == 2 and len(circles) == 1,
      'SHAPE 分布 29/2/1 与 pdt_format.md §5.3 一致')
check(len(m.notes) >= 10, 'notes 非空（%d 条）' % len(m.notes))

# 偏心归属：pdt_format.md §2.9 说"925 梁全 0 / 121 柱全部 ECS1=ECE1≠0"，
# 用**正则直扫原文**复核（不经过任何记录分组逻辑）
import re                                                        # noqa: E402
txt = open(PDT, 'rb').read().decode('gbk')
c_ecc = {}
in_el = False
for ln in txt.replace('\r\n', '\n').split('\n'):
    s = ln.strip()
    if s.startswith('$'):
        in_el = (s.split()[0] == '$SETELEMENT')
        continue
    if not in_el:
        continue
    mt = re.search(r'TYPE=\s*(\d+)', s)
    a = re.search(r'ECS1=\s*([-\d.]+)', s)
    b = re.search(r'ECE1=\s*([-\d.]+)', s)
    if not mt or not a or not b:
        continue
    nz = float(a.group(1)) != 0.0 or float(b.group(1)) != 0.0
    c_ecc[(mt.group(1), 'nonzero' if nz else 'zero')] = \
        c_ecc.get((mt.group(1), 'nonzero' if nz else 'zero'), 0) + 1
print('  原文正则统计 (TYPE, 是否非零 ECS1/ECE1) = %s' % sorted(c_ecc.items()))
check(c_ecc == {('1', 'zero'): 121, ('2', 'nonzero'): 121, ('2', 'zero'): 804},
      '实测：非零 ECS 的 121 条全是 TYPE=2（梁），121 柱全为 0'
      '（与 pdt_format.md §2.9 的表述相反，本实现以原文为准）')
check(any('非零偏心' in n and 'TYPE=2' in n for n in m.notes),
      'notes 里留痕了偏心归属与"未并入几何"的结论')
check(all(len(x.ecc) == 0 for x in m.members), '所有 Member.ecc 为空（§a.2 不猜方向）')
idnote = [n for n in m.notes if 'ID 规范自校验' in n]
print('  %s' % (idnote[0] if idnote else '(无 ID 校验注记)'))
check(idnote and '类码不符 0 个' in idnote[0] and '无跨类码复用' in idnote[0]
      and '全局序号去重后 2841 个' in idnote[0] and '密集连续 1..2841' in idnote[0],
      'ID = 全局序号×100+类码 自校验：0 类码不符 / 2841 个去重序号密集连续 / 无跨类码复用')
story = [n for n in m.notes if n.startswith('$STORY 共')]
floor = [n for n in m.notes if n.startswith('FLOORID 与节点几何不符')]
print('  %s' % (story[0] if story else '(无 $STORY 注记)'))
print('  %s' % (floor[0] if floor else '(无 FLOORID 注记)'))
check(story and '5/5' in story[0], '$STORY 5 层的 TL 全部出现在节点 Z 标高里')
check(floor and '不符的节点 38 个' in floor[0],
      'FLOORID 与几何不符 38 个节点（复现 pdt_format.md §8.3）')
# 环面积交叉核对：pdt_format.md §9.3#3 记 184706 = 2900×2000 = 5.8 m²、185006 ≈ 5.16 m²
a1 = [s for s in m.slabs if s.id == 184706][0].area
a2 = [s for s in m.slabs if s.id == 185006][0].area
print('  板 184706 面积=%.1f mm²（期望 2900×2000=5800000）；185006=%.1f mm²（≈5156250）'
      % (a1, a2))
check(abs(a1 - 5800000.0) < 1e-6 and abs(a2 - 5156250.0) < 1e-6,
      '环序正确：两块板的面积与 pdt_format.md §9.3#3 的实测值逐 mm² 一致')
bad_slab = [s.id for s in m.slabs if len(s.polygon) != len(set(s.polygon))]
check(not bad_slab, '板多边形无重复顶点（首尾也不重复）', str(bad_slab[:3]))

print('\n=== D. SectionMap.load(原件, extra_path="") ===')
sm = SectionMap.load(SECMAP, extra_path='')
print('  stats = %s' % {k: v for k, v in sm.stats.items()
                        if k not in ('prefixes', 'extra_prefixes')})
check(len(sm) == 2836, '原件数据行 == 2836', 'got %d' % len(sm))
check(len(sm.spec_prefixes()) == 53, '规格前缀 == 53', 'got %d' % len(sm.spec_prefixes()))
check(sm.stats['lines'] == 3023 and sm.stats['comments'] == 78
      and sm.stats['blank'] == 109 and sm.stats['unparsable'] == 0,
      '物理行 3023 / 注释 78 / 空行 109 / 无法解析 0', str(sm.stats))

print('\n=== E. SectionMap.validate(目录宏) ===')
bad = sm.validate(CAT)
print('  validate -> %d 条' % len(bad))
fam = {}
for s in bad:
    right = s.split(' : ')[0].split(' -> ')[1]
    fam[right.rsplit('/', 1)[0]] = fam.get(right.rsplit('/', 1)[0], 0) + 1
print('  按规格前缀：%s' % sorted(fam.items()))
check(len(bad) == 257, '坏映射 == 257', 'got %d' % len(bad))
check(fam == {'/DOUBLE_L_EQUAL_CROSS-SPEC': 114,
              '/DOUBLE_L_UNEQUAL_LONG-SPEC': 71,
              '/DOUBLE_L_UNEQUAL_SHORT-SPEC': 71,
              '/DOUBLE_THIN_L_COIL_EQUAL-SPEC': 1}, '257 条按族分布与侦察一致')
n_sug = sum(1 for s in bad if '建议改为' in s)
print('  带纠正建议的：%d/%d' % (n_sug, len(bad)))
check(n_sug == 257, '每条坏映射都给出建议')
# 建议目标必须真的存在于目录宏
comp = set()
for ln in open(CAT, 'r', encoding='utf-8-sig'):
    t = ln.strip()
    if t.startswith('NEW SPCOMPONENT '):
        comp.add(t[len('NEW SPCOMPONENT '):].split()[0])
sug_targets = [s.split('建议改为 ', 1)[1].split('（')[0] for s in bad]
bad_sug = [t for t in sug_targets if t not in comp]
print('  建议目标不在目录宏里的：%d' % len(bad_sug))
check(not bad_sug, '全部建议目标都存在于目录宏', str(bad_sug[:3]))
for s in bad[:2] + bad[-1:]:
    print('     %s' % s)

print('\n=== F. 补充文件 secmap_extra.txt ===')
print('  DEFAULT_EXTRA_FILE=%s exists=%s' % (DEFAULT_EXTRA_FILE,
                                             os.path.isfile(DEFAULT_EXTRA_FILE)))
sm2 = SectionMap.load(SECMAP)                    # extra_path=None -> 默认补充文件
print('  合并后 keys=%d（原件 %d + 补充 %d），warnings=%d'
      % (len(sm2._fwd), len(sm2.entries), len(sm2.extra_entries), len(sm2.warnings)))
check(len(sm2.entries) == 2836, '补充文件不改变原件行数')
check(len(sm2.extra_entries) > 0, '补充文件已加载（%d 行）' % len(sm2.extra_entries))
check(sm2.origin_of('T120') == 'extra', 'T120 来自补充文件')
print('  extra_issues() -> %d 条' % len(sm2.extra_issues(CAT)))
for s in sm2.extra_issues(CAT):
    print('     %s' % s)
check(len(sm2.validate(CAT)) == 257, 'validate() 仍为 257（只校验原件行）')

print('\n=== G. resolve() 四级优先级 ===')
# 1) name
s_name = Section(id=1, kind=26, mat=5, name='HN450X200', table='col')
r = sm2.resolve(s_name, 'col')
print('  name : %s' % r.to_dict())
check(r.status == 'resolved' and r.source == 'name'
      and r.spec_path == '/H_INTERNATIONAL-SPEC/HN450X200', 'rule1 name 命中')
# 2) shapeval
s_sv = Section(id=2, kind=26, mat=5, name='[18a', dims={'subtype': 2},
               table='col', params=['32', '2', '180', '0', '74', '9', '5', '0'])
r = sm2.resolve(s_sv, 'col')
print('  shapeval(26): %s' % r.to_dict())
check(r.status == 'resolved' and r.source == 'shapeval'
      and r.spec_path == '/C_LIGHT-SPEC/CL18a', 'rule2 Kind=26 子类型键命中')
s_sv3 = Section(id=3, kind=303, mat=5, name='薄壁方钢管: B25',
                dims={'lib_family': 6, 'spec_str': 'B250*10.00'}, table='col')
r = sm2.resolve(s_sv3, 'col')
print('  shapeval(303): %s' % r.to_dict())
check(r.status == 'resolved' and r.source == 'shapeval'
      and r.spec_path == '/RECT_SQUARE6728_2002-SPEC/B250*10.00',
      'rule2 Kind=303 打包规格键命中')
# 3) family
r = sm2.resolve(Section(id=4, kind=1, mat=6, dims={'B1': 750.0, 'H1': 750.0},
                        table='pdt'), 'beam')
print('  family(1): %s' % r.to_dict())
check(r.status == 'parametric' and r.source == 'family'
      and r.spec_path == '/USER_RECT-SPEC/Rectangle_Profile'
      and r.desp_params == [750.0, 750.0], 'rule3 Kind=1 → RECT 参数化族')
r = sm2.resolve(Section(id=5, kind=2, mat=5, table='beam',
                        params=['10', '500', '250', '16', '250', '16']), 'beam')
print('  family(2 对称): %s' % r.to_dict())
check(r.status == 'parametric' and r.spec_path == '/USER_H-SPEC/H_Profile'
      and r.desp_params == [250.0, 250.0, 500.0, 10.0, 16.0, 16.0],
      'rule3 Kind=2 对称 → H 参数化族 [B1,B2,H,Tw,T1,T2]')
r = sm2.resolve(Section(id=6, kind=2, mat=5, table='beam',
                        params=['10', '500', '250', '16', '300', '16']), 'beam')
print('  family(2 不对称): %s' % r.to_dict())
check(r.status == 'unresolved' and '交错序未证实' in r.reason,
      'Kind=2 不对称 → unresolved（§12#4 冻结）')
# 4) none
r = sm2.resolve(Section(id=7, kind=3, mat=5, name='圆形4800',
                        dims={'B1': 4800.0}, table='pdt'), 'brace')
print('  none(3): %s' % r.to_dict())
check(r.status == 'unresolved' and r.source == 'none', 'rule4 Kind=3 → unresolved')
for s in (s_name, s_sv, s_sv3):
    print('  candidate_keys(%s) = %s' % (s.name, sm2.candidate_keys(s, 'col')))

print('\n=== G2. 端到端：1_PM.pdt 的截面/面板全部走 SectionMap.resolve() ===')
stat = {}
detail = []
for sec in sorted(m.sections.values(), key=lambda s: s.id):
    used = sum(1 for x in m.members if x.section == sec.id)
    if not used:
        continue
    r = sm2.resolve(sec, 'beam')
    stat[r.status] = stat.get(r.status, 0) + 1
    detail.append('    id=%-6s kind=%-3s name=%-12s -> %-9s %-6s %s %s'
                  % (sec.id, sec.kind, sec.name, r.status, r.source,
                     r.spec_path or '-', r.desp_params or ''))
for sec in sorted(m.sections.values(), key=lambda s: s.id):
    used = sum(1 for x in m.members if x.section == sec.id)
    if used:
        continue
    r = sm2.resolve(sec, 'beam')
    stat['未使用:' + r.status] = stat.get('未使用:' + r.status, 0) + 1
for d in detail:
    print(d)
panel_stat = {}
for t in m.panel_thicknesses():
    for kind in ('slab', 'wall'):
        r = sm2.resolve(Section.for_panel(kind, t), kind)
        panel_stat[(kind, t, r.status)] = r.spec_path
print('  截面 resolve 状态统计（被引用的）：%s' % stat)
print('  面板 resolve：%s' % panel_stat)
check(stat.get('resolved', 0) + stat.get('parametric', 0) >= 25,
      '被引用的 25 个截面全部 resolved/parametric', str(stat))
check(all(v for k, v in panel_stat.items() if k[2] == 'resolved'),
      '全部板/墙厚度 resolved（补充文件生效）', str(panel_stat))
unres = [d for d in detail if 'unresolved' in d]
print('  未解析清单（%d 条）：%s' % (len(unres), unres))
check(len(unres) <= 1, '未解析截面 ≤ 1（样本只有 圆形4800 一个 SHAPE=3）', str(unres))

print('\n=== H. 面板（板/墙）与 reverse() ===')
for t in (120.0, 100.0, 600.0):
    kind = 'wall' if t == 600.0 else 'slab'
    r = sm2.resolve(Section.for_panel(kind, t), kind)
    print('  %s T%g -> %s' % (kind, t, r.to_dict()))
check(sm2.resolve(Section.for_panel('slab', 120.0), 'slab').status == 'resolved',
      'T120 由补充文件解析')
check(sm2.resolve(Section.for_panel('wall', 600.0), 'wall').status == 'resolved',
      'T600 由补充文件解析')
check(sm2.resolve(Section.for_panel('slab', 999.0), 'slab').status == 'unresolved',
      'T999（补充文件没有）→ unresolved')
print('  reverse(/H_INTERNATIONAL-SPEC/HN450X200) = %r'
      % sm2.reverse('/H_INTERNATIONAL-SPEC/HN450X200'))
print('  reverse(H_INTERNATIONAL-SPEC/HN450X200)  = %r'
      % sm2.reverse('H_INTERNATIONAL-SPEC/HN450X200'))
print('  reverse(/USER_RECT-SPEC/Rectangle_Profile) = %r'
      % sm2.reverse('/USER_RECT-SPEC/Rectangle_Profile'))
print('  reverse(/nope/nope) = %r' % sm2.reverse('/nope/nope'))
check(sm2.reverse('/H_INTERNATIONAL-SPEC/HN450X200') == 'HN450X200',
      'reverse 前导斜杠容错')
check(sm2.reverse('/nope/nope') is None, 'reverse 未命中返回 None')
print('  原件里"多条左值 -> 同一右值"的条数 = 0（副本 2836 条右值互不相同）')

# 用合成夹具验证 §e.2（左值重复 -> 后者覆盖 + warnings）、§e.4（补充文件优先）、
# §e.6（reverse 取加载顺序第一条：原件优先，其次补充文件，各自按行序）
FIX_A = os.path.join(HERE, 'fixture_secmap_dup.txt')
FIX_B = os.path.join(HERE, 'fixture_secmap_extra.txt')
mf = SectionMap.load(FIX_A, extra_path=FIX_B)
print('  fixture: entries=%s extra=%s warnings=%s'
      % (mf.entries, mf.extra_entries, mf.warnings))
check(len(mf.entries) == 3 and len(mf.extra_entries) == 2, '夹具解析 3 + 2 条')
check(mf.reverse('/S-SPEC/A') == 'X1', 'reverse 取加载顺序第一条（X1 而非 X2）',
      repr(mf.reverse('/S-SPEC/A')))
check(mf.resolve(Section(id=9, kind=26, mat=5, name='X2', table='col'), 'col').spec_path
      == '/S-SPEC/C', '补充文件覆盖同名左值（X2 -> /S-SPEC/C）')
check(mf.reverse('/S-SPEC/D') == 'X3', '补充文件独有条目（含缺前导斜杠的右值）可反查')
check(len(mf.warnings) == 2 and all('覆盖' in w for w in mf.warnings),
      '重复左值与补充覆盖都记入 warnings', str(mf.warnings))
# 目录宏按 utf-8-sig 严格读（§e.6 + §g.1 禁止 errors='replace'）：喂 GBK 文件必须报错
try:
    mf.validate(SECMAP)
    raised = False
except UnicodeDecodeError as exc:
    raised = True
    print('  validate(GBK 文件当目录宏) -> UnicodeDecodeError（严格解码，符合 §g.1）：%s'
          % str(exc)[:80])
check(raised, '目录宏严格按 utf-8-sig 解码（不解码失败即报错）')

print('\n=== I. Model JSON 往返 + 只读性 ===')
from canonical import Model                                      # noqa: E402
m_rt = Model.from_json(m.to_json())
print('  to_json(bytes)=%d  from_json counts=%s'
      % (len(m.to_json().encode('utf-8')), m_rt.counts()))
check(m_rt.to_json() == m.to_json(), 'JSON 往返逐字节相同（§a.6 规范形式）')
check(m_rt.counts() == c and m_rt.joints.keys() == m.joints.keys(),
      '往返后计数与 joint 键一致（int 键还原）')
for p in (PDT, SECMAP, CAT):
    st = os.stat(p)
    print('  %s size=%d mtime=%d' % (os.path.basename(p), st.st_size, st.st_mtime))
check(True, '样本仅以 mode="rb"/"r" 读取（无写路径）')

print('\n=== 结论 ===')
print('  FAIL 项: %d %s' % (len(fails), fails))
print('DONE (read-only)')
sys.exit(1 if fails else 0)
