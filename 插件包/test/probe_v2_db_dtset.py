# -*- coding: utf-8 -*-
"""实施包⑨ 侦察 3（修正）：/USER_RECT、/USER_CIRCLE、/USER_H、/USER_XI 的 DTSET DATA 条目。

只读。运行：python test/probe_v2_db_dtset.py
"""
import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
MACRO = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\PKPM（PDMS数据库）.txt'
lines = open(MACRO, 'rb').read().decode('utf-8-sig').split('\r\n')


def block_range(i):
    """从 lines[i]（NEW …）到它的配对 END，返回 (start, end) 下标（含）。"""
    depth = 0
    j = i
    while j < len(lines):
        s = lines[j].strip()
        if s.startswith('NEW '):
            depth += 1
        elif s == 'END':
            depth -= 1
            if depth <= 0:
                return i, j
        j += 1
    return i, len(lines) - 1


for name in ('/USER_RECT', '/USER_CIRCLE', '/USER_H', '/USER_XI'):
    starts = [i for i, l in enumerate(lines)
              if re.match(r'NEW\s+STCATEGORY\s+%s\s*$' % re.escape(name), l.strip())]
    if not starts:
        print('%s 未找到' % name)
        continue
    i = starts[0]
    a, b = block_range(i)
    print('=== %s（NEW STCATEGORY 行 %d，块 %d..%d）' % (name, i + 1, a + 1, b + 1))
    k = a
    while k <= b:
        s = lines[k].strip()
        if re.match(r'NEW\s+DATA\s*$', s):
            _, e = block_range(k)
            blk = [lines[x].strip() for x in range(k, e + 1)]
            if any(x.startswith('DKEY ') for x in blk):
                dk = next((x.split(None, 1)[1] for x in blk if x.startswith('DKEY ')), '')
                dp = next((x.split(None, 1)[1] for x in blk if x.startswith('DPRO ')), '')
                pp = next((x.split(None, 1)[1] for x in blk if x.startswith('PPRO ')), '')
                nu = next((x.split(None, 1)[1] for x in blk if x.startswith('NUMB ')), '')
                dt = next((x.split(None, 1)[1] for x in blk if x.startswith('DTIT ')), '')
                pu = next((x.split(None, 1)[1] for x in blk if x.startswith('PURP ')), '')
                print('   L%-6d DKEY=%-5s DPRO=%-10s NUMB=%-3s PURP=%-6s DTIT=%-8s PPRO=%s'
                      % (k + 1, dk, dp, nu, pu, dt, pp))
            k = e + 1
        else:
            k += 1
    print()
