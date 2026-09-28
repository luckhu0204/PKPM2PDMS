# -*- coding: utf-8 -*-
"""定位"插入块 vs 生成器内容"的差异到底在哪（只读诊断）。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'src'))
import installer_core as core  # noqa: E402

SB = r'C:\Users\Administrator\AppData\Local\Temp\pkpmjwd_setup_test_A3_092933'
uic = os.path.join(SB, 'design.uic')
if not os.path.isfile(uic):
    cands = [d for d in os.listdir(os.environ['TEMP']) if d.startswith('pkpmjwd_setup_test_A3_')]
    print('候选沙箱:', cands)
    if cands:
        uic = os.path.join(os.environ['TEMP'], sorted(cands)[-1], 'design.uic')
print('读:', uic)

text = open(uic, 'rb').read().decode('utf-8-sig')
expect = core._menu_block('\n').replace('\n', '\r\n')
print('生成器块: %d 行, %d 字节' % (expect.count('\r\n') + 1, len(expect)))
start = text.find('<MenuTool Name="PKPMJWD.Menu">')
print('MenuTool 位置:', start)
got = text[start - 4:start - 4 + len(expect)]
print('期望前 60 :', repr(expect[:60]))
print('实际前 60 :', repr(got[:60]))
for i, (a, b) in enumerate(zip(expect, got)):
    if a != b:
        print('首个差异在偏移 %d: 期望 %r 实际 %r' % (i, expect[i:i + 40], got[i:i + 40]))
        break
else:
    print('前 %d 字节完全相同；长度 期望=%d 实际=%d' % (min(len(expect), len(got)), len(expect), len(got)))

textn = text.replace('\r\n', '\n')
expn = core._menu_block('\n')
s2 = textn.find('<MenuTool Name="PKPMJWD.Menu">')
gotn = textn[s2 - 4:s2 - 4 + len(expn)]
print('按 LF 规范化后完全一致 =', gotn == expn, ' (%d 字节)' % len(expn))
if gotn != expn:
    for i, (a, b) in enumerate(zip(expn, gotn)):
        if a != b:
            print('  首个差异 %d: %r vs %r' % (i, expn[i:i + 50], gotn[i:i + 50]))
            break
