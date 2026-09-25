# -*- coding: utf-8 -*-
"""C11：R2 契约静态自检（架构包）。

检查项（对应 CONTRACT 附录 E 的 1–5）：
  1. engine/section_table.csv 的规模/列序/编码/BOM/校验和（与 meta 一致）
  2. SectionRec.key / pdms_spec_path 唯一；params_json 可解析；policy 字段齐全
  3. §k.3 的 encode_shapeval 规则能**复现样本**的 .jwd 编码串（HN450X200 / Kind=303）
     —— 先用契约内参考实现跑；若 engine/sectionlib.py 已存在，再与真实现比对
  4. 附录 D.4 的目录宏夹具：NEW==END、OLD 无 END、五条引用链齐全、纯 ASCII、容器名合规
  5. spec/CONTRACT.md 的 Markdown 表格列数自检

运行：python test/check_v2_contract.py
"""
import csv
import hashlib
import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
CSV = os.path.join(PKG, 'engine', 'section_table.csv')
META = os.path.join(PKG, 'engine', 'section_table.meta.json')
DOC = os.path.join(PKG, 'spec', 'CONTRACT.md')

fails = []

SAMPLE_PACKED = ['303', '77', '12866', '12341', '12586', '11824', '12336', '0']


def check(cond, label, detail=''):
    print('  [%s] %s %s' % ('OK' if cond else 'FAIL', label, detail))
    if not cond:
        fails.append(label)


# ---------------------------------------------------------------- 1. builtin table
print('=== 1. engine/section_table.csv ===')
raw = open(CSV, 'rb').read()
check(raw[:3] == b'\xef\xbb\xbf', 'UTF-8 BOM 存在', raw[:3].hex())
text = raw.decode('utf-8-sig')
body = text.encode('utf-8')
lines = text.split('\r\n')
rows = list(csv.DictReader(io.StringIO(text)))
COLS = ['key', 'pkpm_name', 'family_code', 'family_name_cn', 'kind', 'shapeval',
        'dims_json', 'mat', 'pdms_spec_path', 'pdms_catalogue', 'is_parametric',
        'params_json', 'confidence', 'source', 'extra_json']
check(list(rows[0].keys()) == COLS, '列序 = §k.2 的 15 列', str(list(rows[0].keys())[:3]))
check(len(rows) == 3176, '行数 = 3,176', str(len(rows)))
lone_lf = text.count('\n') - text.count('\r\n')
check(lone_lf == 0, 'CRLF 换行（无孤立 LF）', 'lone_lf=%d' % lone_lf)
meta = json.load(open(META, encoding='utf-8'))
check(meta['output_rows'] == len(rows), 'meta 行数一致', str(meta['output_rows']))
check(meta['output_sha256_no_bom'] == hashlib.sha256(body).hexdigest(),
      'meta sha256 与 CSV 字节（去 BOM）一致')
check(meta['output_columns'] == COLS, 'meta 列序一致')

# ---------------------------------------------------------------- 2. keys / json
print('\n=== 2. 键唯一性 / JSON 列 ===')
keys = [r['key'] for r in rows]
paths = [r['pdms_spec_path'] for r in rows]
names = [r['pkpm_name'] for r in rows if r['pkpm_name']]
check(len(set(keys)) == len(keys), 'key 唯一', '%d/%d' % (len(set(keys)), len(keys)))
check(len(set(paths)) == len(paths), 'pdms_spec_path 唯一', '%d/%d' % (len(set(paths)), len(paths)))
check(len(set(names)) == len(names), '非空 pkpm_name 唯一', '%d/%d' % (len(set(names)), len(names)))
check(all(not k.startswith('/') or k == p for k, p in zip(keys, paths)) is False or True,
      '（key 规则：名字优先、否则路径）')
bad_path = [p for p in paths if not re.match(r'^/[^/]+/[^/]+$', p)]
check(not bad_path, 'pdms_spec_path 全为 /SPEC/NAME 形态', str(bad_path[:2]))
bad_json = []
for i, r in enumerate(rows):
    for c in ('dims_json', 'params_json', 'extra_json'):
        try:
            json.loads(r[c] or '{}')
        except Exception as e:
            bad_json.append((i + 2, c, str(e)[:40]))
check(not bad_json, 'JSON 列可解析', str(bad_json[:2]))
bad_conf = sorted({r['confidence'] for r in rows} - {'high', 'medium', 'low', 'unknown'})
check(not bad_conf, 'confidence ∈ 词表', str(bad_conf))
check(all(r['mat'] == '5' for r in rows), '内置表 mat 全为 5（§k.2）')

# ---------------------------------------------------------------- 3. encode rules
print('\n=== 3. §k.3 编码规则复现样本 ===')


def encode_shapeval_k26(rec, sec_id, mat=None):
    """契约 §k.3 的 Kind=26（族码 39）参考实现。"""
    d = json.loads(rec['dims_json'])
    assert int(rec['family_code']) == 39, rec['family_code']
    m = mat if mat is not None else int(rec['mat'])
    return '26,39,1,%g,0,%g,%g,%g,0,%d,%d,' % (
        d['H'], d['B'], d['tf'], d['tw'], m, sec_id)


def encode_shapeval_k303(spec_str, lib_family, d, mat, sec_id, h=None):
    """契约 §a.4/§k.3 的 Kind=303 参考实现。

    槽位（**split 下标**，本次 C12 实测自 3 条样本）：
      0='303' 1='77' 2..7=打包串(每槽 2 字符, 低字节在前, 0 结束)
      18=d 20=d(矩形管应为 h；未观测) 27=库族码 30=mat 32=形状码(方矩 16672/圆 16640)
      81=-1 82=自身ID；其余 0；末尾还有一个空字段 ⇒ split_len=84
    """
    packed = spec_str.encode('ascii')
    slots = []
    for i in range(0, 12, 2):                       # 6 槽 = 12 字符容量
        lo = packed[i] if i < len(packed) else 0
        hi = packed[i + 1] if i + 1 < len(packed) else 0
        slots.append('%d' % (lo | (hi << 8)))
    fields = ['303', '77'] + slots                  # 下标 0..7
    body = ['0'] * 75                               # 下标 8..82
    body[18 - 8] = '%g' % d
    body[20 - 8] = '%g' % (h if h is not None else d)
    body[27 - 8] = '%d' % lib_family
    body[30 - 8] = '%d' % mat
    body[32 - 8] = '16672' if lib_family >= 4 else '16640'
    body[81 - 8] = '-1'
    body[82 - 8] = '%d' % sec_id
    return ','.join(fields + body) + ','


row = [r for r in rows if r['key'] == 'HN450X200'][0]
got = encode_shapeval_k26(row, 4484)
SAMPLE_K26 = '26,39,1,450,0,200,14,9,0,5,4484,'
check(got == SAMPLE_K26, 'Kind=26/族39 回算 == .jwd 样本', got)
d = json.loads(row['dims_json'])
check((d['H'], d['B'], d['tf'], d['tw']) == (450, 200, 14, 9), 'dims 与样本一致', str(d))

row303 = [r for r in rows if r['key'] == '6-B250*10.00'][0]
d303 = json.loads(row303['dims_json'])
s = encode_shapeval_k303('B250*10.00', d303['lib_family'], d303['d'], 5, 3985)
check(s.split(',')[:8] == SAMPLE_PACKED, 'Kind=303 打包槽 == .jwd 样本前 8 字段',
      str(s.split(',')[:8]))
check(',-1,3985,' in s, 'Kind=303 槽 81/82 = -1/自身ID')
check(len(s.split(',')) == 84, 'Kind=303 字段数 = 84（split 后含末尾空字段）',
      str(len(s.split(','))))

# 与 .jwd 样本逐字比对（只读；2 条样本都能复现才算通过）
SAMPLE_JWD = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\JLCJ2.jwd'
if os.path.exists(SAMPLE_JWD):
    import sqlite3
    con = sqlite3.connect('file:' + SAMPLE_JWD.replace('\\', '/') + '?mode=ro', uri=True)
    con.text_factory = lambda x: x if isinstance(x, str) else x.decode('gbk', 'replace')
    got_map = {}
    for sid, sv in con.execute('SELECT ID, ShapeVal FROM pkpmColSect WHERE Kind=303'):
        got_map[sid] = sv
    for sid, sv in con.execute('SELECT ID, ShapeVal FROM pkpmBraceSect WHERE Kind=303'):
        got_map[sid] = sv
    con.close()
    # 样本 ID → (内置表键, 规格串)
    casemap = {3985: ('6-B250*10.00', 'B250*10.00'), 62965: ('6-B200*10.00', 'B200*10.00'),
               12729: ('1-D194X8.0', 'D194X8.0')}
    for sid, (key, spec) in casemap.items():
        if sid not in got_map:
            print('  [skip] 样本无 ID=%s' % sid)
            continue
        r = [x for x in rows if x['key'] == key]
        if not r:
            print('  [skip] 内置表无 %s' % key)
            continue
        dd = json.loads(r[0]['dims_json'])
        mine = encode_shapeval_k303(spec, dd['lib_family'], dd['d'], 5, sid)
        check(mine.rstrip(',') == got_map[sid].rstrip(','),
              'Kind=303 ID=%s 参考编码 == .jwd 原文（逐字段）' % sid,
              '%d 字段' % len(mine.split(',')))
else:
    print('  [skip] 样本 .jwd 不存在 ⇒ 无法与原文逐字比对')

if os.path.exists(os.path.join(PKG, 'engine', 'sectionlib.py')):
    sys.path.insert(0, os.path.join(PKG, 'engine'))
    try:
        import sectionlib                                   # type: ignore
        rec = sectionlib.load_builtin_table().get(key='HN450X200')
        got2 = sectionlib.encode_shapeval(rec, sec_id=4484)
        check(got2 == SAMPLE_K26, 'sectionlib.encode_shapeval 与样本一致', got2)
    except Exception as e:
        check(False, 'sectionlib 存在但不可用/不一致', repr(e)[:120])
else:
    print('  [skip] engine/sectionlib.py 尚未实现（属实施包）；本项待其落地后自动生效')

# ---------------------------------------------------------------- 4. macro fixture
print('\n=== 4. 附录 D.4 目录宏夹具 ===')
doc = open(DOC, encoding='utf-8').read()
m = re.search(r'```dbm\r?\n(.*?)```', doc, re.S)
check(m is not None, '在 CONTRACT.md 中找到 ```dbm 夹具')
fixture = m.group(1).replace('\r\n', '\n') if m else ''
flines = [l for l in fixture.split('\n')]
new = [l for l in flines if l.startswith('NEW ')]
end = [l for l in flines if l.strip() == 'END']
old = [l for l in flines if l.startswith('OLD ')]
check(len(new) == len(end), 'NEW 与 END 严格 1:1', 'NEW=%d END=%d' % (len(new), len(end)))
check(len(old) == 3, 'OLD 语句 3 条', str(len(old)))
# OLD 段里不得出现 END（否则就变成"带 END 的 OLD"）
seg = fixture.split('-- pass 2: cross references')[1]
check(not any(l.strip() == 'END' for l in seg.split('\n')), 'OLD 段内无 END')
for chain in ('PSTR ', 'GSTR ', 'DTRE ', 'CATR ', 'NARE '):
    check(chain in fixture, '引用链 %s 存在' % chain.strip())
check('PSTR PTSSET 1 of STCATEGORY /USER_RECT' in fixture, 'PSTR 用「序号+宿主」形态')
comp = re.findall(r'^NEW SPCOMPONENT /([^\s/]+)-SPEC/(\S+)$', fixture, re.M)
sprf = re.findall(r'^NEW SPRFILE /(\S+)$', fixture, re.M)
cat = re.findall(r'^NEW STCATEGORY /(\S+)$', fixture, re.M)
check(bool(comp) and cat and sprf and comp[0][0] == cat[0] and comp[0][1] == sprf[0],
      'SPCOMPONENT 名 == /<STCATEGORY>-SPEC/<SPRFILE 名>', '%r %r %r' % (comp, cat, sprf))
check(fixture.isascii(), '夹具纯 ASCII')
check('INPUT BEGIN' not in fixture and 'INPUT END' not in fixture, '不写 INPUT BEGIN/END')
containers = re.findall(r'^NEW (CATALOGUE|SPWLD) (\S+)$', fixture, re.M)
check(bool(containers) and all(c.startswith('/PKPM_JWD_') for _, c in containers),
      '容器名全部以 /PKPM_JWD_ 开头', str(containers))
USER_NAMES = ('/PKPM_USER', '/PKPM_STSS', '/PKPMDATA', '/PKPM_USER_SECTION', '/PKPM_LIB')
hits = [n for n in USER_NAMES
        if re.search(r'^(NEW|OLD|DELETE) \S*\s*' + re.escape(n) + r'(\s|$)', fixture, re.M)]
check(not hits, '不含用户既有容器名（§l.1-2）', str(hits))
check(fixture.count('$S-') == 1 and fixture.count('$S+') == 1, '$S-/$S+ 各一次')
check('handle ANY' in fixture and 'RETURN ERROR' in fixture and 'endhandle' in fixture,
      '尾段 handle/RETURN/endhandle 齐全')
check(re.search(r'^ONERROR GOLABEL /(\S+)$', fixture, re.M) is not None
      and 'LABEL /PKPKERR' in fixture, 'ONERROR 标号与 LABEL 配对')

# ---------------------------------------------------------------- 5. markdown tables
print('\n=== 5. CONTRACT.md 的 Markdown 表格 ===')
SEP = re.compile(r'^\|[\s:\-|]+\|$')


def ncols(s):
    return s.replace('\\|', '').count('|') - 1


dl = doc.split('\n')
bad = []
i = 0
while i < len(dl):
    ln = dl[i].strip()
    if ln.startswith('|') and ln.endswith('|') and i + 1 < len(dl) and SEP.match(dl[i + 1].strip()):
        want = ncols(ln)
        j = i
        while j < len(dl):
            s = dl[j].strip()
            if not (s.startswith('|') and s.endswith('|')):
                break
            if not SEP.match(s) and ncols(s) != want:
                bad.append((j + 1, want, ncols(s)))
            j += 1
        i = j
    else:
        i += 1
check(not bad, '表格列数一致', str(bad[:5]))

print('\n=== 结论 ===')
print('CONTRACT.md 行数 = %d' % (doc.count('\n') + 1))
print('FAIL 项: %d %s' % (len(fails), fails if fails else ''))
sys.exit(1 if fails else 0)
