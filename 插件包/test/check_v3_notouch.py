# -*- coding: utf-8 -*-
r"""v3 无接触核验（验收 17/19 的可执行部分）：
对两个"本轮绝不改动"的区域建立清单并核对：
  A) G:\工作\PDMS相关\00 PDMS插件\02 用法插件\PKPM导入导出插件（含 P-TRANS 子目录，递归）
  B) D:\AVEVA\Plant\PDMS12.1.SP4 根目录的**顶层文件**（不递归：部署脚本会动的
     DesignAddins.xml / DesignCustomization.xml / design.uic / *.dll 都在这里）

用法：
  python test\check_v3_notouch.py snapshot    # 建基准（写成 _v3_csc_check/_baseline/*.json）
  python test\check_v3_notouch.py verify      # 与基准比对（size+mtime+sha256），0 差异=通过

只读；不写 G 盘与 D:\AVEVA。
"""
import hashlib
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, '_v3_csc_check', '_baseline')

AREAS = {
    'g_plugin': (r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件', True),
    'aveva_root': (r'D:\AVEVA\Plant\PDMS12.1.SP4', False),
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def manifest(root, recursive):
    rows = []
    if recursive:
        for dirpath, dirnames, filenames in os.walk(root):
            for name in filenames:
                p = os.path.join(dirpath, name)
                st = os.stat(p)
                rows.append({'path': os.path.relpath(p, root), 'size': st.st_size,
                             'mtime': st.st_mtime, 'sha256': sha256(p)})
    else:
        for name in os.listdir(root):
            p = os.path.join(root, name)
            if os.path.isfile(p):
                st = os.stat(p)
                rows.append({'path': name, 'size': st.st_size, 'mtime': st.st_mtime,
                             'sha256': sha256(p)})
    return rows


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'verify'
    os.makedirs(BASE, exist_ok=True)
    fails = []
    for key, (root, rec) in sorted(AREAS.items()):
        if not os.path.isdir(root):
            print('[FAIL] 区域不存在: %s' % root)
            fails.append(key)
            continue
        rows = manifest(root, rec)
        out = os.path.join(BASE, key + '.json')
        print('%s: %s  %d 个文件' % (mode, root, len(rows)))
        if mode == 'snapshot':
            with open(out, 'w', encoding='utf-8') as f:
                json.dump({'root': root, 'n': len(rows), 'rows': rows}, f,
                          ensure_ascii=False)
            print('  基准已写: %s' % out)
            continue
        if not os.path.exists(out):
            print('  [FAIL] 无基准，先跑 snapshot')
            fails.append(key)
            continue
        old = json.load(open(out, encoding='utf-8'))
        om = {r['path']: r for r in old['rows']}
        nm = {r['path']: r for r in rows}
        added = sorted(set(nm) - set(om))
        removed = sorted(set(om) - set(nm))
        changed = sorted(p for p in set(nm) & set(om)
                         if (nm[p]['size'], nm[p]['mtime'], nm[p]['sha256'])
                         != (om[p]['size'], om[p]['mtime'], om[p]['sha256']))
        print('  added=%d removed=%d changed=%d' % (len(added), len(removed), len(changed)))
        for tag, lst in (('added', added), ('removed', removed), ('changed', changed)):
            for p in lst[:10]:
                print('    %s: %s' % (tag, p))
        if added or removed or changed:
            fails.append(key)
    print('\nFAIL 项: %d %s' % (len(fails), fails if fails else ''))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
