# -*- coding: utf-8 -*-
"""最终核对：真实 PDMS 安装内 design.uic 未被改动 + 关键位置行号清单。"""
import hashlib
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = r'D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出'
SB_ORIG = os.path.join(PKG, 'test', '_s2_probes_20260924', '_sandbox', 'design.uic.orig')
REAL = r'D:\AVEVA\Plant\PDMS12.1.SP4\design.uic'

a = open(SB_ORIG, 'rb').read()
b = open(REAL, 'rb').read()
print('真实 design.uic：%d 字节  sha256=%s' % (len(b), hashlib.sha256(b).hexdigest()[:16]))
print('沙箱留存的原件副本：%d 字节  sha256=%s' % (len(a), hashlib.sha256(a).hexdigest()[:16]))
print('逐字节相同 = %s   （说明本次会话没有改动 PDMS 安装内的 design.uic）' % (a == b))
print('真实 design.uic 含 PKPMJWD 字样 = %s' % ('PKPMJWD' in b.decode('utf-8-sig')))
print('真实安装内存在 PMLLIB\\pkpmjwd = %s' % os.path.isdir(r'D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB\pkpmjwd'))
print('真实安装内 design.uic.bak_pkpmjwd_* 数量 = %d' % len(
    [f for f in os.listdir(r'D:\AVEVA\Plant\PDMS12.1.SP4') if f.startswith('design.uic.bak_pkpmjwd_')]))
print()

paths = [
    os.path.join(PKG, 'pdms', 'pkpmjwdexport.pmlfnc'),
    os.path.join(PKG, 'pdms', 'pkpmjwd.pmlfrm'),
    os.path.join(PKG, 'pdms', 'pkpmjwdrun.mac'),
    os.path.join(PKG, 'install', 'install.ps1'),
    os.path.join(PKG, 'install', 'uninstall.ps1'),
    os.path.join(PKG, 'test', 'check_pml.py'),
    os.path.join(PKG, 'test', 'make_gbk.py'),
]
keys = ('define function', 'define method', 'setup form', 'show !!pkpmjwd',
        '$menuInner', 'menuBlock = (', 'newText = $uicText.Substring(0, $toolsLineStart)',
        'RestoreBackup', 'function Fail', 'def main', 'def check_file')
for p in paths:
    raw = open(p, 'rb').read()
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        text = raw.decode('gbk')
    print('===== %s（%d 字节，%d 行，BOM=%s）' % (
        os.path.relpath(p, PKG), len(raw), text.count('\n') + 1, raw[:3] == b'\xef\xbb\xbf'))
    for i, l in enumerate(text.split('\n'), 1):
        s = l.strip()
        if any(s.startswith(k) or k in s for k in keys):
            print('   %4d| %s' % (i, s[:110]))
