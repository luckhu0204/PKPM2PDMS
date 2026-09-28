# -*- coding: utf-8 -*-
"""构建辅助：把 PDMS 侧产物统一转换为 GBK 无 BOM + CRLF。

覆盖两组文件：
  1) pdms\\*.pmlfnc / *.pmlfrm / *.pmlobj / *.mac  —— CONTRACT §g 要求（否则 PDMS 报 CP Syntax error）
  2) install\\*.ps1  —— 本机 Windows PowerShell 5.1 无 BOM 时按 ANSI(GBK) 解析脚本，
                       含中文的 .ps1 若存成 UTF-8 无 BOM 会整篇变成乱码而报语法错；
                       存成 GBK 既能被 5.1 正确解析，又满足契约 §g「不得写 BOM」。

用法：
    python PKPM2PDMS导入导出\\test\\make_gbk.py            # 转换 pdms/ 与 install/ 下全部文件
    python PKPM2PDMS导入导出\\test\\make_gbk.py --check    # 只检查（门禁用），不写文件

只改写包内 pdms/ 与 install/ 的文件，不触碰样本与 PDMS 安装内任何文件。
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
GROUPS = [
    (os.path.join(PKG, 'pdms'), ('.pmlfnc', '.pmlfrm', '.pmlobj', '.mac')),
    (os.path.join(PKG, 'install'), ('.ps1',)),
]


def read_text(path):
    with open(path, 'rb') as f:
        raw = f.read()
    if raw.startswith(b'\xef\xbb\xbf'):
        raw = raw[3:]
    try:
        return raw.decode('utf-8'), 'utf-8'
    except UnicodeDecodeError:
        return raw.decode('gbk'), 'gbk'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='只检查，不写文件')
    args = ap.parse_args()

    bad = 0
    total = 0
    for folder, exts in GROUPS:
        files = sorted(f for f in os.listdir(folder) if f.lower().endswith(exts))
        print('===== %s（%d 个）' % (os.path.relpath(folder, PKG), len(files)))
        for name in files:
            total += 1
            path = os.path.join(folder, name)
            text, enc = read_text(path)
            text = text.replace('\r\n', '\n').replace('\r', '\n')
            data = text.replace('\n', '\r\n').encode('gbk')     # GBK 失败即抛错（禁止 replace）
            with open(path, 'rb') as f:
                old = f.read()
            if old == data:
                print('  OK     %-28s 已是 GBK 无 BOM + CRLF（%d 字节）' % (name, len(data)))
                continue
            if args.check:
                print('  FAIL   %-28s 需要转换（来源编码 %s，%d → %d 字节）' % (name, enc, len(old), len(data)))
                bad += 1
                continue
            with open(path, 'wb') as f:
                f.write(data)
            print('  WROTE  %-28s %s → GBK 无 BOM + CRLF（%d 字节）' % (name, enc, len(data)))
    print('合计 %d 个文件，需转换 %d 个' % (total, bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
