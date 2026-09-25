# -*- coding: utf-8 -*-
"""实施包② 探针 7：**跨包联调** —— 用 S1 的 ``jwd_read.read_jwd`` 产出真实 Model，
再喂给本包的 ``secmap.SectionMap``，核对是否复现契约附录 C 的 C4 基线
（Kind=26 按 Name 命中 7 个 + 补 ``<子类型>-<名字>`` 后 8/8；Kind=303 3/3 命中）。

只读样本；不写任何文件。若 ``jwd_read.py`` 尚未就绪/接口未对齐，本脚本会打印原因并退出 0。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from secmap import SectionMap                                  # noqa: E402
import secmap                                                  # noqa: E402

PLUG = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'
JWD = os.path.join(PLUG, 'JLCJ2.jwd')
SECMAP = os.path.join(PLUG, 'PKPM转PDMS截面匹配文件.txt')
CAT = os.path.join(PLUG, 'PKPM（PDMS数据库）.txt')

try:
    from jwd_read import read_jwd
except Exception as exc:                                       # pragma: no cover
    print('SKIP：engine/jwd_read.py 不可用（%s: %s）' % (type(exc).__name__, exc))
    sys.exit(0)

try:
    m = read_jwd(JWD)
except Exception as exc:                                       # pragma: no cover
    print('SKIP：read_jwd(%s) 抛 %s: %s' % (JWD, type(exc).__name__, exc))
    sys.exit(0)

print('read_jwd: counts = %s' % m.counts())
sm = SectionMap.load(SECMAP)          # 原件 + 默认补充文件（= 契约 §f.1 的缺省行为）
print('SectionMap: 原件 %d 行 + 补充 %d 行；warnings=%d'
      % (len(sm), len(sm.extra_entries), len(sm.warnings)))

used = m.used_sections()
print('used_sections = %d' % len(used))
cnt = {}
detail = []
for s in used:
    kind = 'col' if s.table == 'col' else ('brace' if s.table == 'brace' else 'beam')
    r = sm.resolve(s, kind)
    cnt[r.status] = cnt.get(r.status, 0) + 1
    detail.append('   id=%-6s kind=%-4s table=%-6s name=%-18r -> %-10s %-8s %s %s'
                  % (s.id, s.kind, s.table, s.name, r.status, r.source,
                     r.spec_path or '-', r.desp_params or ''))
for d in detail:
    print(d)
print('resolve 状态统计（被引用截面）: %s' % cnt)

k26 = [s for s in used if s.kind == 26]
k303 = [s for s in used if s.kind == 303]
print('Kind=26: %d 个；Name 命中 %d'
      % (len(k26), sum(1 for s in k26 if s.name in sm)))
print('Kind=303: %d 个；全部命中 %s'
      % (len(k303), all(sm.resolve(s, 'col').status == 'resolved' for s in k303)))
unres = [(s.id, s.kind, s.name, sm.candidate_keys(s, 'col'))
         for s in used if sm.resolve(s, 'col').status == 'unresolved']
print('unresolved（被引用）: %s' % unres)
print('DONE (read-only)')
