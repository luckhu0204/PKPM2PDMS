# -*- coding: utf-8 -*-
"""探针 ⑧-2：在 DLL 里直查 $RIGID / 荷载段名 / FLOORID 相关串（UTF-16LE 与 ASCII 两种编码）。"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DLL = (r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'
       r'\P-TRANS\PDMSxCA_Addin121.dll')
data = open(DLL, 'rb').read()

NEEDLES = ['$RIGID', 'RIGID', '$DEADLOAD', '$LIVELOAD', 'DEADLOAD', 'LIVELOAD',
           'NODELOAD', 'LINELOAD', 'SLABLOAD', '$DEFNODELOAD', '$SETNODELOAD',
           '$DEFLINELOAD', '$SETLINELOAD', '$DEFSLABLOAD', '$DEFFRAMESECTION',
           'FLOORID', 'SLABID', 'NUB', '$END']
for n in NEEDLES:
    u = data.find(n.encode('utf-16-le'))
    a = data.find(n.encode('ascii'))
    print('%-18s utf16le=%-8s ascii=%-8s'
          % (n, ('0x%06X' % u) if u >= 0 else '-', ('0x%06X' % a) if a >= 0 else '-'))
