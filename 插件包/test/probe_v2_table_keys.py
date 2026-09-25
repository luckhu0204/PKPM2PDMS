# -*- coding: utf-8 -*-
"""只读探针 2：转化表的键与重复分析（决定 SectionRec.key 的冻结规则）。"""
import csv
import io
import sys
from collections import Counter, defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
CSV = r'D:\AI_Work\PKPM数据解析\_recon\dbsect\pkpm_pdms_section_table.csv'

with open(CSV, 'r', encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
print('rows=%d cols=%d' % (len(rows), len(rows[0])))

by_name = defaultdict(list)
for i, r in enumerate(rows):
    by_name[r['pkpm_name']].append((i + 2, r))          # +2: 1-based 行号 + 表头
dups = {k: v for k, v in by_name.items() if len(v) > 1}
print('pkpm_name 重复的键: %d 个；涉及行 %d' % (len(dups), sum(len(v) for v in dups.values())))
for k, v in list(dups.items())[:6]:
    print('  %r x%d' % (k, len(v)))
    for ln, r in v:
        print('     L%-5d fam=%-3s cat=%-11s spec=%-42s conf=%-6s src=%s conf_conflict=%r' %
              (ln, r['family_code'] or '-', r['pdms_catalogue'] or '-', r['pdms_spec_path'],
               r['confidence'], r['source'][:34], r['conflict'][:40]))

print('\n--- 重复键的归类 ---')
same_spec = [k for k, v in dups.items() if len({r['pdms_spec_path'] for _, r in v}) == 1]
diff_spec = [k for k, v in dups.items() if len({r['pdms_spec_path'] for _, r in v}) > 1]
print('  同名同规格（纯重复行）: %d' % len(same_spec))
print('  同名不同规格（真冲突）: %d' % len(diff_spec))
for k in diff_spec[:8]:
    print('    %r -> %s' % (k, [(r['pdms_spec_path'], r['family_code'], r['confidence']) for _, r in dups[k]]))
print('  同名同规格示例:', same_spec[:5])

print('\n--- family_code 空值的分布 ---')
empty = [r for r in rows if not r['family_code']]
print('  n=%d；catalogue 分布=%r' % (len(empty), Counter(r['pdms_catalogue'] for r in empty)))
print('  confidence 分布=%r' % Counter(r['confidence'] for r in empty))
print('  is_parametric 分布=%r' % Counter(r['is_parametric'] for r in empty))
print('  source 分布=%r' % Counter(r['source'] for r in empty))

print('\n--- in_pdms_macro / in_matching_file / in_dll_table ---')
for c in ('in_pdms_macro', 'in_matching_file', 'in_dll_table', 'in_userstl_lib',
          'in_pdt_sample', 'in_jwd_sample'):
    print('  %-16s %r' % (c, Counter(r[c] for r in rows)))

print('\n--- 规格路径形态 ---')
import re
bad = [r['pdms_spec_path'] for r in rows if not re.match(r'^/[^/]+/[^/]+$', r['pdms_spec_path'])]
print('  非 /SPEC/NAME 形态: %d %r' % (len(bad), bad[:5]))
owners = Counter(r['pdms_spec_path'].rsplit('/', 1)[0] for r in rows)
print('  规格属主数=%d；前 5: %r' % (len(owners), owners.most_common(5)))

print('\n--- 参数列形态 ---')
for c in ('param_count', 'param_names', 'para_values', 'stcategory_param_count', 'stcategory_params'):
    n_empty = len([r for r in rows if not r[c]])
    print('  %-22s 空=%d；样例=%r' % (c, n_empty, next((r[c] for r in rows if r[c]), '')))
p = [r for r in rows if r['is_parametric'] == 'true']
print('  is_parametric=true 的行数=%d' % len(p))
for r in p[:3]:
    print('    %-12s count=%-3s names=%-28r para=%r stcat_names=%r' %
          (r['pkpm_name'], r['param_count'], r['param_names'], r['para_values'],
           r['stcategory_params'][:60]))
n = [r for r in rows if r['is_parametric'] == 'false']
print('  is_parametric=false 的行数=%d' % len(n))
for r in n[:2]:
    print('    %-12s count=%-3s names=%r' % (r['pkpm_name'], r['param_count'], r['param_names'][:70]))
    print('       para=%r' % r['para_values'][:90])
    print('       stcat=%r' % r['stcategory_params'][:90])

print('\n--- 样本截面在表内的命中（.jwd 28 行 / .pdt 32 条）---')
for name in ('HN450X200', 'HN300X150', '[18a', '2-[18a', 'H', 'RECT', 'CIRCLE',
             'TUBE', 'H', '3-B25X1.5', '6-B250*10.00'):
    hit = [(ln, r['pdms_spec_path']) for ln, r in by_name.get(name, [])]
    print('  %-14r -> %s' % (name, hit[:2]))
print('\nDONE')
