# -*- coding: utf-8 -*-
"""查证两个"对不上"的指纹：匹配文件的行数/缺斜杠行号、1_PM.pdt 的首行。"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
PLUG = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件'

p = PLUG + r'\PKPM转PDMS截面匹配文件.txt'
raw = open(p, 'rb').read()
print('匹配文件：%d 字节，前 8 字节 %r，末 8 字节 %r' % (len(raw), raw[:8], raw[-8:]))
txt = raw.decode('gbk')
print('  split("\\r\\n")  元素数 =', len(txt.split('\r\n')))
print('  splitlines()     行数 =', len(txt.splitlines()))
print('  纯 "\\n" 个数 =', txt.count('\n'), ' "\\r" 个数 =', txt.count('\r'))
lines = txt.split('\r\n')
if lines and lines[-1] == '':
    lines.pop()
blank = sum(1 for l in lines if not l.strip())
comm = sum(1 for l in lines if l.strip().startswith('//') or set(l.strip()) <= {'/'})
data = [i for i, l in enumerate(lines) if l.strip() and not l.strip().startswith('//')
        and not set(l.strip()) <= {'/'} and ',' in l]
other = [(i + 1, l) for i, l in enumerate(lines)
         if l.strip() and not l.strip().startswith('//') and not set(l.strip()) <= {'/'}
         and ',' not in l]
print('  空行 %d / 注释 %d / 数据 %d / 其他 %d' % (blank, comm, len(data), len(other)))
print('  其他行:', other[:5])
print('  第一条数据行是物理第 %d 行' % (data[0] + 1))
m = [i for i in data if not ' '.join(lines[i].split(',', 1)[1].split()).startswith('/')]
print('  右值缺前导 "/" 的数据行（0 基）%s ⇒ 物理行号 %s'
      % (m, [i + 1 for i in m]))
print('  前 3 个缺斜杠行的左值/右值:',
      [(lines[i].split(',', 1)[0].strip(), lines[i].split(',', 1)[1].strip())
       for i in m[:3]])
print('  第 2979-2982 行的内容:')
for i in range(2978, 2982):
    if i < len(lines):
        print('    L%d: %r' % (i + 1, lines[i]))

p2 = PLUG + r'\1_PM.pdt'
raw2 = open(p2, 'rb').read()
print('\n1_PM.pdt：%d 字节，前 40 字节 %r' % (len(raw2), raw2[:40]))
t2 = raw2.decode('gbk')
print('  前 3 行:', [x for x in t2.split('\r\n')[:3]])
print('  splitlines 行数 =', len(t2.splitlines()))
