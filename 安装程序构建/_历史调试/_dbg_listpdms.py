# -*- coding: utf-8 -*-
"""诊断 exe 的 --list-pdms：把 stdout/stderr 分别重定向到文件，绕开 shell 管道。"""
import os
import subprocess
import sys
import tempfile

EXE = r'D:\AI_Work\PKPM数据解析\安装包程序\dist\PKPM-JWD_安装程序_v1.exe'
work = tempfile.mkdtemp(prefix='pdmslist_')
out = os.path.join(work, 'out.txt')
err = os.path.join(work, 'err.txt')

with open(out, 'wb') as fo, open(err, 'wb') as fe:
    p = subprocess.Popen([EXE, '--list-pdms'], stdout=fo, stderr=fe,
                         stdin=subprocess.DEVNULL)
    rc = p.wait(timeout=120)

print('退出码:', rc)
for name, path in (('stdout', out), ('stderr', err)):
    data = open(path, 'rb').read()
    print('--- %s (%d 字节) ---' % (name, len(data)))
    for enc in ('utf-8', 'gbk', 'mbcs'):
        try:
            print('[%s] %s' % (enc, data.decode(enc).strip()[:400]))
            break
        except Exception:
            continue
    else:
        print('[raw]', data[:200])
print('真实 design.uic 存在:', os.path.isfile(r'D:\AVEVA\Plant\PDMS12.1.SP4\design.uic'))
