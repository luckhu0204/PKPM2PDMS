# -*- coding: utf-8 -*-
"""只读探针（架构包，v2 契约取证用）：
  A) 1_PM.pdt 的逐段行式（repr，保留空白）——用于冻结 pdt_write 的写出格式
  B) PDMSxCA_Addin121.dll 内 .pdt 的格式串（UTF-16，按偏移提取）
  C) _recon/dbsect/pkpm_pdms_section_table.csv 的规模/列/唯一性/取值词表

运行：python test/probe_v2_shapes.py
"""
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PLUG = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'
PDT = os.path.join(PLUG, '1_PM.pdt')
DLL = os.path.join(PLUG, 'P-TRANS', 'PDMSxCA_Addin121.dll')
CSV = r'D:\AI_Work\PKPM数据解析\_recon\dbsect\pkpm_pdms_section_table.csv'


def sec(t):
    print('\n=== %s ===' % t)


# ---------------------------------------------------------------- A) .pdt lines
sec('A. 1_PM.pdt 逐段行式（repr）')
raw = open(PDT, 'rb').read()
print('bytes=%d  CRLF=%d  LF=%d  BOM=%s' % (
    len(raw), raw.count(b'\r\n'), raw.count(b'\n'), raw.startswith(b'\xef\xbb\xbf')))
txt = raw.decode('gbk')
lines = txt.split('\r\n')
print('physical_lines=%d (split 后 %d)' % (len(lines), len(lines)))


def show(a, b, label=''):
    print('--- L%d..L%d %s' % (a, b, label))
    for n in range(a, b + 1):
        if n - 1 < len(lines):
            print('%5d|%s' % (n, repr(lines[n - 1])))


show(1, 8, '文件头')
show(56, 61, '$STORY 头两条')
show(68, 76, '$STORY 尾 + $NODECOOR 头两条')
show(2364, 2372, '$DEFFRAMESECTION 头')
show(2526, 2546, '$DEFWASLABSECTION/$DEFMATERIAL/$SETELEMENT 头')
show(2552, 2562, '柱构件（TYPE=1）与 EXI/EXR')
show(6726, 6736, '$SETWALL 头')
show(6748, 6756, '$SETSLAB 头')
show(8074, 8082, '$RIGID 头')
show(8102, 8114, '$DEADLOAD 分组头与 $DEFNODELOAD')
show(9675, 9677, '$END')

# 空行统计：每个节的数据区末尾恰好 1 个空行？
sec('A2. 空行/节头位置')
heads = [(i + 1, l) for i, l in enumerate(lines) if l.startswith('$')]
print('节头 %d 个：' % len(heads))
for n, l in heads:
    print('  L%-6d %s' % (n, l))

# ---------------------------------------------------------------- B) DLL formats
sec('B. PDMSxCA_Addin121.dll 内的 .pdt 格式串（按偏移取 UTF-16LE，NUL 截断）')
dll = open(DLL, 'rb').read()
print('dll bytes=%d' % len(dll))
OFFS = [0x02029F, 0x020344, 0x0203DC, 0x02041E, 0x033B1C, 0x033B81, 0x033C05,
        0x033C75, 0x033D24, 0x033E3D, 0x0202DB, 0x0202C1, 0x020183, 0x02012E,
        0x020154, 0x02007E, 0x020042]
for off in OFFS:
    chunk = dll[off:off + 400]
    # UTF-16LE 解码到第一个 NUL（偶数对齐）
    end = 0
    while end + 1 < len(chunk) and not (chunk[end] == 0 and chunk[end + 1] == 0):
        end += 2
    s = chunk[:end].decode('utf-16-le', 'replace')
    print('  0x%06X  %r' % (off, s))

# ---------------------------------------------------------------- C) recon CSV
sec('C. pkpm_pdms_section_table.csv')
craw = open(CSV, 'rb').read()
print('bytes=%d  BOM=%s  CRLF=%d' % (len(craw), craw[:3].hex(), craw.count(b'\r\n')))
import csv  # noqa: E402

with open(CSV, 'r', encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
print('rows=%d  cols=%d' % (len(rows), len(rows[0])))
print('columns=%s' % list(rows[0].keys()))


def uniq(col):
    vals = [r[col] for r in rows]
    return len(vals), len(set(vals))


for c in ('pkpm_name', 'pdms_spec_path', 'family_code', 'pdms_catalogue',
          'is_parametric', 'confidence', 'source', 'pdms_stcategory'):
    n, u = uniq(c)
    print('  %-18s n=%d unique=%d' % (c, n, u))

print('family_code=0/empty rows: %d' % len([r for r in rows if not r['family_code']]))
print('pdms_spec_path empty rows: %d' % len([r for r in rows if not r['pdms_spec_path']]))
print('pdms_spec_path starts with "/": %d' % len(
    [r for r in rows if r['pdms_spec_path'].startswith('/')]))
print('is_parametric values: %r' % sorted({r['is_parametric'] for r in rows}))
print('confidence values: %r' % sorted({r['confidence'] for r in rows}))
print('source values (top 15): %r' % sorted({r['source'] for r in rows})[:15])
print('pdms_catalogue values: %r' % sorted({r['pdms_catalogue'] for r in rows}))
print('family_code values: %r' % sorted({r['family_code'] for r in rows}, key=lambda s: (len(s), s)))
print('\n组合唯一性：')
pairs = [(r['family_code'], r['pkpm_name']) for r in rows]
print('  (family_code, pkpm_name) unique=%d / %d' % (len(set(pairs)), len(pairs)))
paths = {}
for r in rows:
    paths.setdefault(r['pdms_spec_path'], []).append(r['pkpm_name'])
multi = {k: v for k, v in paths.items() if len(v) > 1 and k}
print('  同一 pdms_spec_path 对应多个 PKPM 名: %d 组，例如 %r' %
      (len(multi), list(multi.items())[:3]))
print('\n样例行（挑 3 条）：')
for want in ('H', 'RECT', 'HN400X200'):
    for r in rows:
        if r['pkpm_name'] == want:
            print('  ' + json.dumps(r, ensure_ascii=False)[:600])
            break
print('\nDONE')
