# -*- coding: utf-8 -*-
"""把本次侦察/一次性修复用的脚本集中搬到 test\\_s2_probes_20260924\\（只移动，不删除）。

只处理本会话自己创建的、名字列在下面的文件；不碰其它实施包的文件
（例如 _grammar_out.txt / _selfcheck_out.txt / _dump_chain_out.txt 属于别的包）。
"""
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ARCH = os.path.join(HERE, '_s2_probes_20260924')
os.makedirs(ARCH, exist_ok=True)

MINE = [
    '_probe_uic.py', '_probe_uic2.py', '_probe_uic3.py', '_probe_uic3.txt',
    '_probe_uic4.py', '_probe_uic4.txt', '_probe_uic5.py', '_probe_uic6.py',
    '_probe_uic7.py', '_probe_uic8.py', '_probe_uic9.py', '_probe_uic10.py',
    '_probe_uic11.py', '_probe_uic12.py', '_probe_uic13.py', '_probe_uic14.py',
    '_probe_uic15.py', '_probe_uic16.py', '_probe_uic17.py', '_probe_uic18.py',
    '_probe_uic19.py', '_probe_uic20.py', '_probe_uic21.py', '_probe_uic22.py',
    '_probe_uic23.py', '_probe_uic24.py', '_probe_uic25.py', '_probe_uic26.py',
    '_probe_uic27.py',
    '_probe_macro_out.txt', '_probe_cmdtype_out.txt', '_probe_io_out.txt',
    '_probe_io2_out.txt', '_probe_nav_out.txt',
    '_norm_cmp.py', '_show_ops.py', '_fix_ops.py', '_fix_pathtype.py',
    '_fix_indent.py', '_fix_unset.py', '_dump_pml.py',
    '_sandbox_verify.py', '_sandbox_after_uninstall.py', '_tidy.py',
]

moved, absent = [], []
for name in MINE:
    src = os.path.join(HERE, name)
    if not os.path.exists(src):
        absent.append(name)
        continue
    dst = os.path.join(ARCH, name)
    if os.path.exists(dst):
        absent.append(name + '（目标已存在）')
        continue
    try:
        shutil.move(src, dst)
        moved.append(name)
    except PermissionError as exc:
        absent.append('%s（占用：%s）' % (name, exc))

d = os.path.join(HERE, '_sandbox')
if os.path.isdir(d):
    dst = os.path.join(ARCH, '_sandbox')
    if os.path.exists(dst):
        absent.append('_sandbox（目标已存在）')
    else:
        shutil.move(d, dst)
        moved.append('_sandbox/')

print('已移动 %d 项 → %s' % (len(moved), os.path.relpath(ARCH, os.path.dirname(HERE))))
for m in moved:
    print('   ' + m)
print('未移动： %s' % absent)
print('剩余在 test\\ 下：')
for n in sorted(os.listdir(HERE)):
    print('   ' + n)
