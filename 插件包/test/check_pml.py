# -*- coding: utf-8 -*-
"""PKPM-JWD导入导出 —— PDMS 侧 PML 源静态检查（编码 / 换行 / 括号 / 块配对）

用法：
    python PKPM-JWD导入导出\\test\\check_pml.py                     # 检查包内 pdms/ 全部 PML
    python PKPM-JWD导入导出\\test\\check_pml.py <文件或目录> [...]    # 检查指定目标
    python PKPM-JWD导入导出\\test\\check_pml.py --selftest           # 用本机 PDMS 安装内的
                                                                     # 既有 PML 反测检查器本身

检查项（每项逐文件打印 PASS/FAIL）：
  E1 编码：GBK 可解码（严格 decode，不用 errors='replace'）
  E2 BOM ：文件不得以 UTF-8 BOM 开头（CONTRACT §g）
  E3 换行：只有 CRLF，不得出现裸 LF（CR 后必须紧跟 LF）
  S1 圆括号 ()、方括号 [] 配对（先剥离 -- 注释与字符串字面量）
  S2 块配对：if/endif、do/enddo、handle/endhandle、define function|method|object/end*
  S3 结构：*.pmlfrm 必须含 'setup form'；*.pmlfnc 必须含 'define function'；
           *.mac 不得含 'define function'

说明（这是静态检查，不是 PML 语法解析器，也不实机运行 PDMS）：
  * `--` 注释、`'...'` 与 `|...|` 字符串内的内容先被剥掉，再统计括号与关键字；
  * PML1 允许单行 `IF (cond) stmt`（无 ENDIF），本机既有宏里存在这种写法，
    `--selftest` 就是用来看清检查器在真实文件上的表现，出现 FAIL 不等于被检文件有错。

退出码：0 = 全部 PASS；1 = 有 FAIL；2 = 用法/路径错误。
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
DEFAULT_DIR = os.path.join(PKG, 'pdms')
PDMS_ROOT = r'D:\AVEVA\Plant\PDMS12.1.SP4'
EXTS = ('.pmlfnc', '.pmlfrm', '.pmlobj', '.mac')

SELFTEST = [
    r'mypml\forms\StlGrating.pmlfrm',
    r'mypml\forms\GRIDDESIGN.pmlfrm',
    r'mypml\forms\order.pmlfrm',
    r'common\forms\runmacro.pmlfrm',
    r'common\functions\findfirstmember.pmlfnc',
    r'common\functions\comunitsconvert.pmlfnc',
    r'common\functions\collectmembersof.pmlfnc',
    r'common\objects\comunits.pmlobj',
    r'TIANGONG\forms\tgmain.pmlfrm',
    r'TIANGONG\functions\tginjectdesignmenu.pmlfnc',
    r'TIANGONG\tiangong_v2.mac',
    r'mypml\forms\scale-STRU.mac',
]

BLOCKS = [
    # (开始关键字, 结束关键字)
    (r'\bif\b', r'\bendif\b'),
    (r'\bdo\b', r'\benddo\b'),
    (r'\bhandle\b', r'\bendhandle\b'),
    (r'\bdefine\s+function\b', r'\bendfunction\b'),
    (r'\bdefine\s+method\b', r'\bendmethod\b'),
    (r'\bdefine\s+object\b', r'\bendobject\b'),
]


def strip_code(text):
    """剥掉注释（`--` 与宏注释 `$*`）与字符串字面量内容，返回可计数的代码文本。"""
    out = []
    i = 0
    n = len(text)
    quote = None                      # 当前字符串定界符：' 或 | 或 "
    while i < n:
        ch = text[i]
        if quote is None:
            if text.startswith('--', i) or text.startswith('$*', i):
                j = text.find('\n', i)
                i = n if j < 0 else j
                continue
            if ch in ("'", '|', '"'):
                quote = ch
                i += 1
                continue
            out.append(ch)
            i += 1
        else:
            if ch == quote:
                quote = None
            elif ch == '\n':
                # 字符串里出现换行属于异常，保留换行以免行号错乱
                out.append('\n')
            i += 1
    return ''.join(out)


def check_file(path, selftest=False):
    """返回 (fail 列表, warn 列表, 统计 dict)。"""
    fails, warns = [], []
    with open(path, 'rb') as f:
        raw = f.read()
    ext = os.path.splitext(path)[1].lower()
    name = os.path.basename(path)

    # E1/E2/E3：编码与换行（selftest 模式跳过，因为本机既有文件有 LF-only 的）
    if not selftest:
        if raw.startswith(b'\xef\xbb\xbf'):
            fails.append('E2 BOM：文件以 UTF-8 BOM 开头（CONTRACT §g 禁止）')
            body = raw[3:]
        else:
            body = raw
        try:
            text = body.decode('gbk')
        except UnicodeDecodeError as exc:
            fails.append('E1 编码：GBK 严格解码失败（%s）' % exc)
            text = body.decode('gbk', 'replace')
        lone_lf = 0
        for m in re.finditer(rb'\n', body):
            if m.start() == 0 or body[m.start() - 1] != 0x0D:
                lone_lf += 1
        if lone_lf:
            fails.append('E3 换行：存在 %d 处非 CRLF 的 LF' % lone_lf)
    else:
        try:
            text = raw.decode('gbk')
        except UnicodeDecodeError:
            text = raw.decode('gbk', 'replace')
        lone_lf = None

    code = strip_code(text)
    stats = {'bytes': len(raw), 'lines': text.count('\n') + 1, 'lone_lf': lone_lf}

    # S1 括号
    for o, c, label in (('(', ')', '圆括号'), ('[', ']', '方括号')):
        no, nc = code.count(o), code.count(c)
        stats['%s%s%s' % (label, o, c)] = (no, nc)
        if no != nc:
            fails.append('S1 %s不配对：%s=%d，%s=%d' % (label, o, no, c, nc))

    # S2 块配对
    for start, end in BLOCKS:
        ns = len(re.findall(start, code, re.I))
        ne = len(re.findall(end, code, re.I))
        if ns != ne:
            fails.append('S2 块不配对：%s=%d，%s=%d' % (start.replace('\\b', ''), ns,
                                                       end.replace('\\b', ''), ne))
        elif start == r'\bif\b':
            stats['if/endif'] = ns

    # S3 结构
    if ext == '.pmlfrm' and not re.search(r'\bsetup\s+form\b', code, re.I):
        fails.append('S3 *.pmlfrm 内没有 setup form')
    if ext == '.pmlfnc' and not re.search(r'\bdefine\s+function\b', code, re.I):
        fails.append('S3 *.pmlfnc 内没有 define function')
    if ext == '.mac' and re.search(r'\bdefine\s+function\b', code, re.I):
        fails.append('S3 *.mac 内出现 define function（宏里只能有命令/过程码）')

    # W1 软提示：if/elseif 行是否带 then
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if re.match(r'(?i)^(if|elseif)\s*\(', s) and 'then' not in s.lower():
            warns.append('W1 第 %d 行 if/elseif 无 then：%s' % (i, s[:70]))
    return fails, warns, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('targets', nargs='*', help='文件或目录（默认包内 pdms/）')
    ap.add_argument('--selftest', action='store_true',
                    help='用本机 PDMS 安装内既有 PML 反测检查器（只读）')
    args = ap.parse_args()

    if args.selftest:
        files = [os.path.join(PDMS_ROOT, 'PMLLIB', rel) for rel in SELFTEST]
        selftest = True
        missing = [f for f in files if not os.path.exists(f)]
        if missing:
            print('本机缺少这些文件（跳过）：')
            for m in missing:
                print('   ', m)
        files = [f for f in files if os.path.exists(f)]
    else:
        targets = args.targets or [DEFAULT_DIR]
        files = []
        for t in targets:
            if os.path.isdir(t):
                files += [os.path.join(t, f) for f in sorted(os.listdir(t))
                          if f.lower().endswith(EXTS)]
            elif os.path.isfile(t):
                files.append(t)
            else:
                print('路径不存在：%s' % t)
                return 2
        selftest = False

    if not files:
        print('没有可检查的 PML 文件')
        return 2

    nfail = 0
    nwarn = 0
    print('=' * 78)
    print('%s：%d 个文件' % ('--selftest（本机既有 PML，只读）' if selftest else 'PKPM-JWD导入导出 静态检查', len(files)))
    print('=' * 78)
    for path in files:
        fails, warns, stats = check_file(path, selftest)
        nfail += len(fails)
        nwarn += len(warns)
        head = '%-34s %6d 字节 %5d 行' % (os.path.basename(path), stats['bytes'], stats['lines'])
        if stats.get('lone_lf'):
            head += '  裸LF=%d' % stats['lone_lf']
        print(head)
        if stats.get('if/endif') is not None:
            print('        if/endif=%d  括号()=%s 方括号[]=%s' % (
                stats['if/endif'], stats.get('圆括号()', ''), stats.get('方括号[]', '')))
        if not fails:
            print('        PASS')
        for f in fails:
            print('        FAIL %s' % f)
        for w in warns:
            print('        warn %s' % w)

    print('-' * 78)
    print('汇总：文件 %d 个，FAIL %d 项，warn %d 项' % (len(files), nfail, nwarn))
    print('结论：%s' % ('全部通过' if nfail == 0 else '存在 FAIL，需修复'))
    return 1 if nfail else 0


if __name__ == '__main__':
    sys.exit(main())
