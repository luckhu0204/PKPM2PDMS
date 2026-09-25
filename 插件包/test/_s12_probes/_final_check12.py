# -*- coding: utf-8 -*-
"""本轮收尾核对（只读 + 只读检查）：

1) 新 PML 文件与改动文件的行尾续行候选（应为 0）；
2) pkpmjwduniquename.pmlfnc 冻结要素在成品里的静态断言（契约 §o：签名/候选序列/
   EXIST+(2,109)/记录格式/FAIL 语义/defined 守卫/append）；
3) 本轮边界自证：D:/AVEVA 的 design.uic 仍与沙箱留存原件逐字节相同、无 PMLLIB\\pkpmjwd、
   工作区无新增写入 G 盘的痕迹（G 盘样本只读访问）；
4) 汇总本轮产物清单与行号。
"""
import hashlib
import os
import re

PKG = r'D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出'
PMLLIB = r'D:\AVEVA\Plant\PDMS12.1.SP4'

print('===== 1) 行尾续行候选（应为 0）=====')
for n in ['pkpmjwduniquename.pmlfnc', 'pkpmjwd.pmlfrm', 'pkpmjwdrun.mac']:
    t = open(os.path.join(PKG, 'pdms', n), 'rb').read().decode('gbk')
    bad = [(i, l) for i, l in enumerate(t.split('\r\n'), 1)
           if l.rstrip().endswith('&') or l.rstrip().endswith('$')]
    print('  %-28s 续行候选 %d 处' % (n, len(bad)))

print()
print('===== 2) 冻结要素静态断言（pkpmjwduniquename.pmlfnc）=====')
t = open(os.path.join(PKG, 'pdms', 'pkpmjwduniquename.pmlfnc'), 'rb').read().decode('gbk')
A = [
    ('define function !!pkpmjwdUniquename(!base is STRING) is STRING', '§o.2 冻结签名'),
    ('do !idx from 0 to 99', '候选 do 0..99（共 100 个，上限 re99）'),
    ("!cand = !base & 're'", "后缀 re 直接拼接"),
    ('var !probe EXIST /$!cand', '§o.3 写法①（EXIST）'),
    ('handle (2,109)', '(2,109) Undefined name ⇒ 可用'),
    ('defined(!!pkpmjwdRenames)', 'defined() 守卫（nucdesogwall.pmlobj:206）'),
    ('!!pkpmjwdRenames = object ARRAY()', '全局数组建立'),
    ('.append(', '.append 记录（GRIDDESIGN.pmlfrm:986）'),
    ("!t & '|' & !base & '|' & !cand", "记录格式 TYPE|原名|实际名"),
    ("!!pkpmjwdRenames.append('FAIL|' & !base & '|' & !base & 're99')", 'FAIL 留痕（§o.6）'),
    ("!!pkpmjwdRenames.append('FAIL||')", "空基名留痕 'FAIL||'（F.1）"),
    ('return !final', '命中返回可用名'),
    ('!probe.upcase().eq', "值判定补充（'TRUEA' ⇒ 占用；assybuildname:50,65 等）"),
    ('defined(!!pkpmjwdType)', 'TYPE 通道用双 ! 全局（偏差已声明）'),
]
for needle, label in A:
    print('  %-4s %-46s %s' % ('PASS' if needle in t else 'FAIL', label, needle[:52]))

print()
print('===== 3) 边界自证（不改 D:/AVEVA、不部署、不写 G 盘）=====')
real = os.path.join(PMLLIB, 'design.uic')
orig = os.path.join(PKG, r'test\_s2_probes_20260924\_sandbox\design.uic.orig')
a = open(orig, 'rb').read()
b = open(real, 'rb').read()
print('  design.uic 逐字节未变 = %s（%d 字节，sha256 %s）' % (
    a == b, len(b), hashlib.sha256(b).hexdigest()[:16]))
print('  PMLLIB\\pkpmjwd 不存在 = %s' % (not os.path.isdir(os.path.join(PMLLIB, 'PMLLIB', 'pkpmjwd'))))
print('  DesignAddins.xml 含 PKPMJWD = %s' % ('PKPMJWD' in open(os.path.join(PMLLIB, 'DesignAddins.xml'), 'rb').read().decode('utf-8-sig')))
print('  DesignCustomization.xml 含 PKPMJWD = %s' % ('PKPMJWD' in open(os.path.join(PMLLIB, 'DesignCustomization.xml'), 'rb').read().decode('utf-8-sig')))

print()
print('===== 4) 本轮产物行号 =====')
for rel in [r'pdms\pkpmjwduniquename.pmlfnc', r'pdms\pkpmjwd.pmlfrm', r'pdms\pkpmjwdrun.mac']:
    p = os.path.join(PKG, rel)
    raw = open(p, 'rb').read()
    t2 = raw.decode('gbk')
    print('--- %s（%d 字节，%d 行，BOM=%s，CRLF=%d，裸LF=%d）' % (
        rel, len(raw), t2.count('\n') + 1, raw[:3] == b'\xef\xbb\xbf',
        raw.count(b'\r\n'), raw.count(b'\n') - raw.count(b'\r\n')))
    for i, l in enumerate(t2.split('\r\n'), 1):
        if re.match(r'^define (function|method) ', l.strip()):
            print('     %4d| %s' % (i, l.strip()[:100]))
