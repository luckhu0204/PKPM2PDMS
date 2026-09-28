# -*- coding: utf-8 -*-
"""安装程序沙箱自测：验证与 install.ps1 / uninstall.ps1 行为等价，且可逆、幂等、不改盘。

全部读写在 %TEMP% 下自己建的沙箱目录里；不删除任何既有文件（卸载走"整目录移动"）。
"""

# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)

import installer_core as core  # noqa: E402

# 对照用的 .ps1 来自**新树的 插件包/install/**（G 盘是只读样本区，不再读它）
V1 = os.path.join(os.path.dirname(HERE), '插件包')
REAL_PDMS = r'D:\AVEVA\Plant\PDMS12.1.SP4'
REAL_UIC = os.path.join(REAL_PDMS, 'design.uic')
PS_INSTALL = os.path.join(V1, 'install', 'install.ps1')
PS_UNINSTALL = os.path.join(V1, 'install', 'uninstall.ps1')

FAILS = []
LOGS = []


def log(line=''):
    LOGS.append(line)
    print(line)


def check(cond, label, detail=''):
    mark = 'PASS' if cond else 'FAIL'
    log('  [%s] %s%s' % (mark, label, ('  —— ' + detail) if detail else ''))
    if not cond:
        FAILS.append(label)
    return cond


def sha(path):
    with open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def new_sandbox(tag, with_uic=True):
    root = os.path.join(os.environ.get('TEMP', r'C:\Windows\Temp'),
                        'pkpm2pdms_setup_test_%s_%s' % (tag, time.strftime('%H%M%S')))
    os.makedirs(root)
    if with_uic:
        shutil.copy2(REAL_UIC, os.path.join(root, 'design.uic'))
    return root


def run_ps(script, root, extra):
    cmd = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', script,
           '-PdmsRoot', root] + extra
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode, (proc.stdout or b'').decode('mbcs', 'replace')


def capture(fn, *a, **kw):
    lines = []
    code = fn(*a, report=lines.append, **kw)
    return code, lines


def main():
    log('=' * 72)
    log('安装程序沙箱自测  ' + time.strftime('%Y-%m-%d %H:%M:%S'))
    log('=' * 72)
    log('真实 design.uic : %s  (%d 字节, sha %s)' % (REAL_UIC, os.path.getsize(REAL_UIC), sha(REAL_UIC)[:16]))
    log('PML 源包        : %s' % core.resource_dir())
    for name in core.REQUIRED_FILES:
        p = os.path.join(core.resource_dir(), name)
        log('   %-24s %s %s' % (name, 'OK' if os.path.isfile(p) else '缺失',
                                (str(os.path.getsize(p)) + ' 字节') if os.path.isfile(p) else ''))
    log('')

    # ============================================================ 场景一：安装
    log('-' * 72)
    log('场景一：预览 → 安装 → 重复安装（幂等）→ 卸载 → 重复卸载')
    log('-' * 72)
    sb = new_sandbox('A')
    log('沙箱：' + sb)
    orig_sha = sha(os.path.join(sb, 'design.uic'))
    pml_dir = os.path.join(sb, 'PMLLIB', core.PACKAGE_NAME_DEFAULT)

    # --- 预览
    code, lines = capture(core.do_install, pdms_root=sb, dry_run=True)
    check(code == 0, '预览退出码 0', 'code=%d' % code)
    check(sha(os.path.join(sb, 'design.uic')) == orig_sha, '预览不落盘：design.uic 未变')
    check(not os.path.isdir(os.path.join(sb, 'PMLLIB')), '预览不落盘：未创建 PMLLIB')
    check(any('未写入任何文件' in x for x in lines), '预览有明确"未写入"声明')

    # --- 与 install.ps1 的等价性交叉验证（一）：DryRun 的报数
    rc, ps_out = run_ps(PS_INSTALL, sb, ['-DryRun'])
    ps_bytes = re.search(r'写回后\s*:\s*(\d+)\s*字节，\s*(\d+)\s*行', ps_out)
    py_bytes = None
    py_lines = None
    for x in lines:
        m = re.search(r'写回后\s*:\s*(\d+)\s*字节，\s*(\d+)\s*行', x)
        if m:
            py_bytes, py_lines = m.group(1), m.group(2)
    check(rc == 0, 'install.ps1 -DryRun 退出码 0', 'rc=%d' % rc)
    check(ps_bytes is not None and py_bytes is not None, '两边都给出了"写回后"字节/行数')
    if ps_bytes and py_bytes:
        check(ps_bytes.group(1) == py_bytes and ps_bytes.group(2) == py_lines,
              '写回后字节/行数与 install.ps1 一致',
              'ps=%s/%s  py=%s/%s' % (ps_bytes.group(1), ps_bytes.group(2), py_bytes, py_lines))

    def menu_block_of(text_lines):
        """取"追加内容"之后、直到菜单栏那一行为止的内容（含那一行）。"""
        out, on = [], False
        for x in text_lines:
            if '追加内容' in x and not on:
                on = True
                continue
            if on:
                if x.strip().startswith('写回后'):
                    break
                if x.strip():
                    out.append(x.strip())
        return out

    ps_block = menu_block_of(ps_out.splitlines())
    py_block = menu_block_of(lines)
    check(ps_block == py_block and len(py_block) == 20,
          '两边打印的追加内容逐行一致（19 行菜单块 + 1 行菜单栏引用 = 20 行）',
          'ps=%d py=%d' % (len(ps_block), len(py_block)))

    # --- 与 install.ps1 的等价性交叉验证（二）：各自真装一遍，比最终字节
    sb_ps = new_sandbox('A2')
    sb_py = new_sandbox('A3')
    rc2, _ = run_ps(PS_INSTALL, sb_ps, [])
    code2, _ = capture(core.do_install, pdms_root=sb_py, dry_run=False)
    uic_ps = os.path.join(sb_ps, 'design.uic')
    uic_py = os.path.join(sb_py, 'design.uic')
    check(rc2 == 0 and code2 == 0, 'ps1 与 Python 各自真装一遍都成功', 'ps=%d py=%d' % (rc2, code2))
    b_ps = open(uic_ps, 'rb').read()
    b_py = open(uic_py, 'rb').read()
    check(b_ps == b_py, '★ 两边装出来的 design.uic 逐字节相同（%d 字节）' % len(b_py),
          '' if b_ps == b_py else 'ps sha=%s py sha=%s' % (sha(uic_ps)[:16], sha(uic_py)[:16]))
    # 只追加不改写：把插入的两块去掉后应与原文件逐字节相同
    orig_text = open(os.path.join(sb, 'design.uic'), 'rb').read().decode('utf-8-sig')
    new_text_py = b_py.decode('utf-8-sig')
    check(new_text_py.count('PKPM2PDMS') == 4, '本包相关标记共 4 处（MenuTool/MenuBar 各 1 + Open 2）',
          '实际 %d' % new_text_py.count('PKPM2PDMS'))


    # --- 真安装
    code, lines = capture(core.do_install, pdms_root=sb, dry_run=False)
    check(code == 0, '安装退出码 0', 'code=%d' % code)
    installed = [os.path.join(pml_dir, n) for n in core.REQUIRED_FILES]
    check(all(os.path.isfile(p) for p in installed), '4 个 PML 已复制到 PMLLIB\\pkpm2pdms\\')
    check(all(sha(p) == sha(os.path.join(core.resource_dir(), n))
              for p, n in zip(installed, core.REQUIRED_FILES)), '复制的 PML 字节与源一致')
    uic = os.path.join(sb, 'design.uic')
    new_sha = sha(uic)
    text = open(uic, 'rb').read().decode('utf-8-sig')
    check(new_sha != orig_sha, 'design.uic 已改动')
    import xml.etree.ElementTree as ET
    ok_xml = True
    try:
        ET.fromstring(text.encode('utf-8'))
    except Exception as exc:
        ok_xml = False
        log('    XML 解析失败：%s' % exc)
    check(ok_xml, '安装后 design.uic 仍是合法 XML')
    check(text.count('PKPM2PDMS.Menu') == 2, '菜单项出现 2 次（MenuTool 定义 + MenuBar 引用）',
          '实际 %d' % text.count('PKPM2PDMS.Menu'))
    check(text.count('PKPM2PDMS.Open') == 2, '按钮出现 2 次（ButtonTool 定义 + MenuTool 内引用）',
          '实际 %d' % text.count('PKPM2PDMS.Open'))
    orig_lines = open(REAL_UIC, 'rb').read().decode('utf-8-sig').split('\n')
    new_lines = text.split('\n')
    kept = [ln for ln in orig_lines if ln.strip() and ln in new_lines]
    check(len(kept) == len([ln for ln in orig_lines if ln.strip()]),
          '原有非空行全部保留（只追加，未改动既有内容）',
          '%d/%d' % (len(kept), len([ln for ln in orig_lines if ln.strip()])))
    # 插进去的那一块要和生成器给出的内容一字不差
    expect_block = core._menu_block('\r\n')
    expect_bar = core._bar_line()
    start = text.find('<MenuTool Name="PKPM2PDMS.Menu">')
    block_ok = (start >= 4 and text[start - 4:start - 4 + len(expect_block)] == expect_block)
    check(block_ok, '插入的菜单块与生成器内容逐字节一致（19 行 %d 字节）' % len(expect_block),
          '' if block_ok else '首处不符：%r vs %r' % (
              expect_block[:40], text[max(start - 4, 0):max(start - 4, 0) + 40]))
    check(text.count(expect_bar + '\r\n') == 1, '菜单栏引用插入 1 次且格式正确')
    baks = sorted(x for x in os.listdir(sb) if x.startswith('design.uic.bak_pkpm2pdms_'))
    check(len(baks) == 1, '生成了 1 个安装前备份', ','.join(baks))
    check(baks and sha(os.path.join(sb, baks[0])) == orig_sha, '备份内容 = 安装前的 design.uic')

    # --- 重复安装（幂等）
    code, lines = capture(core.do_install, pdms_root=sb, dry_run=False)
    check(code == 0, '重复安装退出码 0')
    check(sha(uic) == new_sha, '重复安装后 design.uic 未变（幂等）')
    baks2 = [x for x in os.listdir(sb) if x.startswith('design.uic.bak_pkpm2pdms_')]
    check(len(baks2) == 1, '重复安装不再新增备份', '%d 个' % len(baks2))
    check(any('幂等' in x for x in lines), '日志说明了跳过原因（幂等）')

    # --- 卸载
    code, lines = capture(core.do_uninstall, pdms_root=sb, dry_run=False)
    check(code == 0, '卸载退出码 0', 'code=%d' % code)
    check(sha(uic) == orig_sha, '★ 卸载后 design.uic 与安装前逐字节相同')
    check('PKPM2PDMS' not in open(uic, 'rb').read().decode('utf-8-sig'), 'design.uic 内无 PKPM2PDMS 残留')
    check(not os.path.isdir(pml_dir), 'PMLLIB\\pkpm2pdms 已不在原位')
    moved = sorted(x for x in os.listdir(os.path.join(sb, 'PMLLIB')) if x.startswith('_removed_'))
    check(len(moved) == 1, '包目录被整体移动到 _removed_…（没有删除）', ','.join(moved))
    if moved:
        inner = sorted(os.listdir(os.path.join(sb, 'PMLLIB', moved[0])))
        check(inner == sorted(core.REQUIRED_FILES), '移动过去的 4 个文件还在', ','.join(inner))

    # --- 重复卸载（幂等）
    code, lines = capture(core.do_uninstall, pdms_root=sb, dry_run=False)
    check(code == 0, '重复卸载退出码 0')
    check(sha(uic) == orig_sha, '重复卸载后 design.uic 仍与安装前相同')
    check(any('幂等' in x for x in lines), '重复卸载走幂等分支')

    # --- uninstall.ps1 对照
    rc, ps_out = run_ps(PS_UNINSTALL, sb, ['-DryRun'])
    check(rc == 0, 'uninstall.ps1 -DryRun 退出码 0', 'rc=%d' % rc)
    check('命中 0 处' in ps_out, 'ps1 也认为条目已全部移除（命中 0 处）')

    # ============================================================ 场景二：参数与异常
    log('')
    log('-' * 72)
    log('场景二：异常输入与 --restore-backup')
    log('-' * 72)
    sb2 = new_sandbox('B')
    orig2 = sha(os.path.join(sb2, 'design.uic'))
    try:
        core.do_install(pdms_root=os.path.join(sb2, '不存在的目录'), dry_run=False,
                        report=lambda s: None)
        check(False, '不存在的 PDMS 根目录应报错')
    except core.InstallError as exc:
        check(exc.code == core.ExitCode.ARGS, '不存在的根目录 → 退出码 2', 'code=%d' % exc.code)

    sb3 = new_sandbox('C', with_uic=False)
    try:
        core.do_install(pdms_root=sb3, dry_run=False, report=lambda s: None)
        check(False, '缺 design.uic 应报错')
    except core.InstallError as exc:
        check(exc.code == core.ExitCode.ARGS, '缺 design.uic → 退出码 2', 'code=%d' % exc.code)

    sb4 = new_sandbox('D')
    with open(os.path.join(sb4, 'design.uic'), 'wb') as fh:
        fh.write(b'<not valid xml')
    try:
        core.do_install(pdms_root=sb4, dry_run=False, report=lambda s: None)
        check(False, '非法 XML 应报错')
    except core.InstallError as exc:
        check(exc.code == core.ExitCode.CHECK, '非法 XML → 退出码 3', 'code=%d' % exc.code)

    sb5 = new_sandbox('E')
    with open(os.path.join(sb5, 'design.uic'), 'wb') as fh:
        fh.write(b'\xff\xfe not utf8 at all')
    try:
        core.do_install(pdms_root=sb5, dry_run=False, report=lambda s: None)
        check(False, '非 UTF-8 应报错')
    except core.InstallError as exc:
        check(exc.code == core.ExitCode.CHECK, '非 UTF-8 → 退出码 3', 'code=%d' % exc.code)

    # restore-backup 路径
    code, _ = capture(core.do_install, pdms_root=sb2, dry_run=False)
    code, _ = capture(core.do_uninstall, pdms_root=sb2, dry_run=False, restore_backup=True)
    check(code == 0, '卸载 --restore-backup 退出码 0', 'code=%d' % code)
    check(sha(os.path.join(sb2, 'design.uic')) == orig2,
          '★ --restore-backup 后 design.uic 与安装前逐字节相同')

    # ============================================================ 汇总
    log('')
    log('=' * 72)
    if FAILS:
        log('结果：失败 %d 项' % len(FAILS))
        for f in FAILS:
            log('   - ' + f)
    else:
        log('结果：全部通过')
    log('=' * 72)
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
