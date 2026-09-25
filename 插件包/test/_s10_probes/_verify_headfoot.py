# -*- coding: utf-8 -*-
"""核对：pkpmjwddbexport.pmlfnc 里写的头/尾字面量，与用户样本 PKPM（PDMS数据库）.txt 的头尾是否逐字一致
（日期与 ONERROR 标号按已知差异归一化后比较）。"""
import os
import re

PKG = r'D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出'
SAMPLE = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\PKPM（PDMS数据库）.txt'
PML = os.path.join(PKG, 'pdms', 'pkpmjwddbexport.pmlfnc')

s = open(SAMPLE, 'rb').read().decode('utf-8-sig').splitlines()
t = open(PML, 'rb').read().decode('gbk')

# 从 PML 里抠出 writealphafile 的字面量（按出现顺序）
lits = [m.group(1).replace("''", "'") for m in re.finditer(r"writealphafile '((?:[^']|'')*)'", t)]
print('PML 内 writealphafile 字面量 %d 条：' % len(lits))
for l in lits:
    print('    %r' % l)

head_lits = lits[:6]
foot_lits = lits[6:]

DATE = re.compile(r"Date : .*")


def norm(x):
    x = DATE.sub('Date : <D>', x)
    x = re.sub(r'^ONERROR GOLABEL /\w+$', 'ONERROR GOLABEL <L>', x)
    return x


print()
print('=== 头 6 行（样本 L1..L6） vs PML 头字面量')
ok = 0
for i in range(6):
    a = norm(s[i])
    b = norm(head_lits[i])
    same = (a == b)
    ok += same
    print('  %-4s 样本=%r' % ('OK' if same else 'DIFF', s[i]))
    if not same:
        print('       PML =%r' % head_lits[i])

print()
print('=== 尾（样本 L70290..L70300，11 行） vs PML 尾字面量 %d 条' % len(foot_lits))
tail = s[70289:70300]
for i in range(max(len(tail), len(foot_lits))):
    a = norm(tail[i]) if i < len(tail) else '<缺>'
    b = norm(foot_lits[i]) if i < len(foot_lits) else '<缺>'
    same = (a == b)
    ok += same
    print('  %-4s 样本=%r' % ('OK' if same else 'DIFF', a))
    if not same:
        print('       PML =%r' % b)

print()
print('=== 逐字一致的行数： %d' % ok)
