# -*- coding: utf-8 -*-
"""交付前自查（实施包④）：产物编码/无 BOM、import 边界、
**用户原件内容指纹**（用内容而不是 mtime 证明未改写）、本包文件清单。

运行：python test/check_deliverables.py

为什么用内容指纹而不是 mtime：本工作流是**多实施包并行**跑的，工作区里
``_recon/*``、``engine/*`` 等文件同时被别的包读写，mtime 不能说明"谁改了"；
而且本机有一份"用户原件只读"的硬要求，能证明的方式只有"内容与契约/侦察报告
记载的字节数/行数/结构事实逐条一致"。
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PLUG = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'
mine = ['engine/jwd_write.py', 'engine/pdms_dump.py', 'test/check_jwd_write_roundtrip.py',
        'test/check_dump_to_jwd.py', 'test/check_db2jwd_sections.py',
        'test/_jwd_read_stub.py', 'test/probe_wr_sample.py',
        'test/probe_fixture_specs.py', 'test/probe_jwd_read_avail.py',
        'test/probe_fingerprint.py', 'test/probe_v2_db_source.py',
        'test/probe_v2_db_params.py', 'test/probe_v2_db_dtset.py',
        'test/probe_v2_slots.py']
fails = []


def check(cond, label, detail=''):
    print('  [%s] %s %s' % ('OK' if cond else 'FAIL', label, detail))
    if not cond:
        fails.append(label)


print('=== 1. Python 源码编码：UTF-8 无 BOM ===')
for rel in ('engine/jwd_write.py', 'engine/pdms_dump.py',
            'test/check_jwd_write_roundtrip.py', 'test/check_dump_to_jwd.py',
            'test/_jwd_read_stub.py', 'test/fixture_dump_min.txt',
            'test/fixture_dump_ext.txt'):
    p = os.path.join(PKG, rel)
    raw = open(p, 'rb').read()
    try:
        raw.decode('utf-8')
        dec = True
    except Exception:
        dec = False
    check((not raw.startswith(b'\xef\xbb\xbf')) and dec, '%s UTF-8 无 BOM' % rel,
          '%d 字节' % len(raw))

print('\n=== 2. import 边界（契约 §b.5）===')
src = io.open(os.path.join(PKG, 'engine', 'jwd_write.py'), encoding='utf-8').read()
imports = sorted(set(re.findall(r'^\s*(?:from|import)\s+([\w.]+)', src, re.M)))
check(set(imports) <= {'os', 're', 'sqlite3', 'tempfile', 'typing', '__future__',
                       'canonical'}, 'jwd_write.py 只 import 标准库 + canonical', str(imports))
src2 = io.open(os.path.join(PKG, 'engine', 'pdms_dump.py'), encoding='utf-8').read()
imports2 = sorted(set(re.findall(r'^\s*(?:from|import)\s+([\w.]+)', src2, re.M)))
check(set(imports2) <= {'re', 'typing', '__future__', 'canonical'},
      'pdms_dump.py 只 import 标准库 + canonical（SectionMap 走鸭子类型注入）', str(imports2))

print('\n=== 3. 用户原件内容指纹（证明"只读、未改写"；数字出自契约附录 B.2 / 侦察报告）===')
jwd = os.path.join(PLUG, 'JLCJ2.jwd')
sz = os.path.getsize(jwd)
check(sz == 1073152, 'JLCJ2.jwd = 1,073,152 字节（契约 B.2）', '%d' % sz)
head = open(jwd, 'rb').read(16)
check(head == b'SQLite format 3\x00', 'JLCJ2.jwd 是 SQLite3 文件（头 16 字节）', repr(head[:8]))
import sqlite3                                                          # noqa: E402
con = sqlite3.connect('file:' + jwd.replace('\\', '/') + '?mode=ro', uri=True)
n_tab = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
enc = con.execute('PRAGMA encoding').fetchone()[0]
uv = con.execute('PRAGMA user_version').fetchone()[0]
tot = sum(con.execute('SELECT COUNT(*) FROM "%s"' % r[0]).fetchone()[0]
          for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'"))
con.close()
check(n_tab == 46 and enc == 'UTF-8' and uv == 0 and tot == 6480,
      'JLCJ2.jwd：46 表 / PRAGMA encoding=UTF-8 / user_version=0 / 合计 6480 行（契约 §0.2）',
      '表 %d 编码 %s uv %d 行 %d' % (n_tab, enc, uv, tot))

txt = io.open(os.path.join(PLUG, 'PKPM转PDMS截面匹配文件.txt'), 'rb').read()
elems = txt.decode('gbk').split('\r\n')      # 契约的"3,023 物理行"= 这个元素数（含文件末尾 CRLF 后的空元素）
raw_lines = elems[:-1] if elems and elems[-1] == '' else elems
rows = [l for l in raw_lines if l.strip() and not l.strip().startswith('//')
        and not set(l.strip()) <= {'/'} and ',' in l]
lefts = [r.split(',', 1)[0].strip() for r in rows]
rights = [' '.join(r.split(',', 1)[1].split()) for r in rows]
missing_slash = [i for i, l in enumerate(raw_lines)
                 if l.strip() and not l.strip().startswith('//')
                 and not set(l.strip()) <= {'/'} and ','
                 and not ' '.join(l.split(',', 1)[1].split()).startswith('/')]
prefixes = set(r.split('/')[1] for r in rights if r.startswith('/'))
check(len(elems) == 3023 and not txt.startswith(b'\xef\xbb\xbf'),
      '匹配文件：3,023 物理行（split("\\r\\n") 元素数）、无 BOM（契约 B.2）', '%d' % len(elems))
check(len(rows) == 2836 and len(set(lefts)) == len(lefts),
      '匹配文件：2,836 条数据行、左值 0 重复（契约 C2）', '%d 条' % len(rows))
check([i + 1 for i in missing_slash] == [2979, 2980, 2981, 2982]
      and raw_lines[2978].startswith('组卷L40X15X2.0'),
      '匹配文件：右值缺前导 "/" 的 4 条正是 L2979–2982，内容与契约一致（契约 B.2）',
      str([i + 1 for i in missing_slash]))
print('        （附带信息：// 与整行 "/" 注释合计 %d 行、空行 %d 行、规格前缀 %d 个——'
      '契约 C2 的 78 只数 // 开头行）'
      % (sum(1 for l in raw_lines if l.strip().startswith('//') or
             set(l.strip()) <= {'/'}),
         sum(1 for l in raw_lines if not l.strip()), len(prefixes)))

pdtt = io.open(os.path.join(PLUG, '1_PM.pdt'), 'rb').read().decode('gbk')
plines = pdtt.split('\r\n')
n_pl = len(plines) - (1 if plines and plines[-1] == '' else 0)
check(n_pl == 9677 and plines[0].startswith(';') and '4.2.0' in '\r\n'.join(plines[:6]),
      '1_PM.pdt：9,677 行、首行是 ";" 注释、$VERSION 记录值为 4.2.0（契约 B.2 / pdt §2.1）',
      '%d 行；前 4 行=%r' % (n_pl, plines[:4]))
db = os.path.join(PLUG, 'PKPM（PDMS数据库）.txt')
raw_db = open(db, 'rb').read()
dlines = raw_db.decode('utf-8-sig').split('\r\n')
check(len(raw_db) == 1406051 and raw_db.startswith(b'\xef\xbb\xbf'),
      'PKPM（PDMS数据库）.txt：1,406,051 B、UTF-8 带 BOM（契约 B.2）', '%d B' % len(raw_db))
check(len(dlines) == 70301 and dlines[0].startswith('$S-'),
      'PKPM（PDMS数据库）.txt：70,301 行、首行 $S-（契约 B.2）', '%d 行' % len(dlines))

print('\n=== 4. 本包只以只读方式打开用户原件（代码级核对）===')
SAMPLE_HINT = ('PLUG', 'JLCJ2', '1_PM', 'MATCH', 'PDMS数据库')
for rel in mine:
    s = io.open(os.path.join(PKG, rel), encoding='utf-8').read()
    bad = []
    for m in re.finditer(r"open\(([^)]*)\)", s):
        args = m.group(1)
        if re.search(r"['\"](w|a|wb|ab|r\+|w\+|x)[^'\"]*['\"]", args) and \
                any(h in args for h in SAMPLE_HINT):
            bad.append(args.strip())
    if 'mode=rw' in s:
        bad.append('mode=rw')
    reads = len(re.findall(r"mode=ro", s)) + len(re.findall(r"open\([^)]*['\"]rb?['\"]", s))
    check(not bad, '%s：没有以写模式打开原件' % rel,
          str(bad) if bad else '（只读用法 %d 处）' % reads)

print('\n=== 5. 本包新增/改动的文件（固定清单）===')
FILES = ['engine/jwd_write.py', 'engine/pdms_dump.py',
         'test/check_jwd_write_roundtrip.py', 'test/_rt_out.txt',
         'test/_rt_out/JLCJ2.roundtrip.jwd', 'test/_rt_out/JLCJ2.real.jwd',
         'test/check_dump_to_jwd.py', 'test/_dump_chain_out.txt',
         'test/_rt_out/fixture_dump_min.gbk.txt', 'test/_rt_out/fixture_dump_ext.gbk.txt',
         'test/_rt_out/dump_min.jwd', 'test/_rt_out/dump_ext.jwd',
         'test/_rt_out/dump_ext_prop.jwd', 'test/_rt_out/dump_ext_nojoints.jwd',
         'test/fixture_dump_min.txt', 'test/fixture_dump_ext.txt',
         'test/_jwd_read_stub.py', 'test/probe_wr_sample.py', 'test/_wr_sample.txt',
         'test/probe_fixture_specs.py', 'test/_fixture_specs.txt',
         'test/probe_jwd_read_avail.py', 'test/_jwdread_avail.txt',
         'test/gen_ddl_block.py', 'test/splice_ddl.py',
         'test/probe_fingerprint.py', 'test/_fingerprint.txt',
         'test/check_db2jwd_sections.py', 'test/_db2jwd_out.txt',
         'test/probe_v2_db_source.py', 'test/_v2_db_source.txt',
         'test/probe_v2_db_params.py', 'test/_v2_db_params.txt',
         'test/probe_v2_db_dtset.py', 'test/_v2_db_dtset.txt',
         'test/probe_v2_slots.py', 'test/_v2_slots.txt',
         'test/_rt_out/db_sections.jwd', 'test/_rt_out/db_sections_split.jwd',
         'test/_rt_out/db_sections_empty.jwd', 'test/_rt_out/db_sections_dict.jwd',
         'test/_rt_out/db_sections_reid.jwd',
         'test/_rt_out/db2jwd_closure.json', 'test/_rt_out/db2jwd_losses.json',
         'test/check_deliverables.py', 'test/_deliverables_out.txt',
         'test/summary.py', 'test/_summary_out.txt',
         'test/summary_v2.py', 'test/_summary_v2_out.txt']
miss = [f for f in FILES if not os.path.isfile(os.path.join(PKG, f))]
for f in FILES:
    p = os.path.join(PKG, f)
    if os.path.isfile(p):
        print('   %-52s %9d B' % (f, os.path.getsize(p)))
check(not miss, '清单里 %d 个文件全部存在' % len(FILES), str(miss))

print('\n=== 结论 ===')
print('FAIL 项: %d %s' % (len(fails), fails if fails else ''))
sys.exit(1 if fails else 0)
