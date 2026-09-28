# -*- coding: utf-8 -*-
"""PKPM2PDMS导入导出 v2.1.0 —— PDMS 侧安装 / 卸载核心逻辑（供 exe 与命令行共用）。

行为与包内 ``install/install.ps1``、``install/uninstall.ps1`` 等价，用纯 Python 重写，
以便打包成单文件 exe 使用（不依赖 PowerShell 执行策略，也不需要命令行）。

相对 ``.ps1`` 的一处**安全性改进**（交付说明里已注明）：
    ``.ps1`` 的顺序是「先复制 PML → 再备份 design.uic」；备份失败时提示"未做任何改动"，
    但此时 PML 其实已经复制进去了（半安装状态，措辞与实际不符）。
    本程序改为「校验 → 备份设计文件 → 复制 PML → 写回」，与 ``.ps1`` 头部注释所
    描述的顺序一致，也不再出现措辞与状态不符的问题。

纪律（与 ``.ps1`` 完全一致）：
    * **不删除任何既有文件**；卸载默认「整目录移动」到 ``PMLLIB\\_removed_<包名>_<时间>``。
    * 不动 ``DesignAddins.xml``（本包是纯 PML，没有 .NET add-in 可登记）。
    * 不重排、不改写 ``design.uic`` 里既有的条目（TGTEXT / PDCOPILOT 等原样保留）。
    * 只动本包自己的三处菜单条目与 ``PMLLIB\\<包名>`` 目录，不碰 ``pml.index``。
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from typing import Callable, List, Optional, Sequence, Tuple

__all__ = [
    "VERSION", "DEFAULT_PDMS_ROOT", "PACKAGE_NAME_DEFAULT", "REQUIRED_FILES",
    "ExitCode", "InstallError", "detect_pdms_roots", "pdms_running",
    "check_source_encoding", "resource_dir", "source_files",
    "icon_path", "apply_window_icon",
    "do_install", "do_uninstall", "Sink", "make_printer",
]

VERSION = "2.1.0"
DEFAULT_PDMS_ROOT = r"D:\AVEVA\Plant\PDMS12.1.SP4"
PACKAGE_NAME_DEFAULT = "pkpm2pdms"
#: 安装时必须复制进 PMLLIB 的 PML。与 插件包/install/install.ps1:67 的 $required
#: 逐字一致 —— exe 安装路线与 .ps1 路线装的文件清单必须相同。
#: 注意 pkpm2pdmsuniquename.pmlfnc 不在其中：install.ps1 也不装它，
#: 它由原生 .NET 路线的 deploy_pkpm2pdms.py 装配（见交付回报的"未解决项"）。
REQUIRED_FILES = ("pkpm2pdms.pmlfrm", "pkpm2pdmsexport.pmlfnc",
                  "pkpm2pdmsdbexport.pmlfnc", "pkpm2pdmsrun.mac")

#: Tool Key 必须**全局唯一**（PDMS 的 RootTools 集合跨 uic 文件）：
#: 原生路线 pkpm2pdms.uic 已占用 PKPM2PDMS.Menu / PKPM2PDMS.Open，
#: 本（legacy PML）路线一律加 .PML. 前缀，否则后加载的那份 uic 会被整份拒载
#: （2026-09-28 实机 P3 复现：'Key ... already exists in the RootTools collection'）。
MENU_ID = "PKPM2PDMS.PML.Menu"
BUTTON_ID = "PKPM2PDMS.PML.Open"
#: 菜单/按钮标题 —— 必须与 插件包/install/install.ps1:132,146 逐字一致。
#: legacy PML 路线用「PKPM2PDMS PML」，与原生 .NET 路线的菜单「PKPM2PDMS」区分开
#: （TEST_PLAN P3 的判据就是两个菜单名都要出现）。
MENU_CAPTION = "PKPM2PDMS PML"
BUTTON_CAPTION = "PKPM2PDMS PML 导入导出"
MENU_COMMAND = "show !!pkpm2pdms"

BOM_UTF8 = b"\xef\xbb\xbf"
GBK = "gbk"
COLLISION_LIMIT = 100

Sink = Callable[[str], None]


class ExitCode(object):
    OK = 0
    ARGS = 2
    CHECK = 3
    RUNNING = 4
    WRITE = 5


class InstallError(Exception):
    """带退出码的失败；由 :func:`do_install` / :func:`do_uninstall` 抛出。"""

    def __init__(self, message: str, code: int = ExitCode.ARGS) -> None:
        Exception.__init__(self, message)
        self.code = code


# ---------------------------------------------------------------- 工具

def make_printer(stream=None) -> Sink:
    """返回一个把日志写到 stdout / stderr 的 sink；中文在 cp936 控制台不会炸。"""
    out = stream if stream is not None else sys.stdout

    def _say(message: str) -> None:
        text = message if isinstance(message, str) else str(message)
        try:
            out.write(text + "\n")
        except UnicodeEncodeError:
            enc = getattr(out, "encoding", None) or "gbk"
            out.write(text.encode(enc, "replace").decode(enc, "replace") + "\n")
        try:
            out.flush()
        except Exception:
            pass

    return _say


def icon_path() -> Optional[str]:
    """返回窗口图标 ``pkpm2pdms.ico`` 的绝对路径；找不到返回 ``None``。

    PyInstaller onefile 下资源在解包目录 ``sys._MEIPASS``（**不能**用 ``__file__`` 的上级目录）：
    ``build_exe.py`` 用 ``--add-data <ico>;ico`` 把它放到 ``<_MEIPASS>/ico/``。
    源码模式下按 ``<自身目录>/assets/ico``、再向上找 ``assets/ico`` 与工作树的 ``图标/``。
    """
    name = "pkpm2pdms.ico"
    cands: List[str] = []
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
        cands += [os.path.join(base, "ico"), base]
    here = os.path.dirname(os.path.abspath(__file__))
    cands.append(os.path.join(here, "assets", "ico"))
    parent = here
    for _ in range(3):
        parent = os.path.dirname(parent)
        cands.append(os.path.join(parent, "assets", "ico"))
        cands.append(os.path.join(parent, "图标"))
    for cand in cands:
        for probe in (cand, os.path.join(cand, name)):
            if os.path.isfile(probe) and probe.lower().endswith(".ico"):
                return probe
    return None


def apply_window_icon(root) -> Optional[str]:
    """给 tk 窗口设标题栏图标：``root.iconbitmap(<ico>)``，路径按 ``sys._MEIPASS`` 兼容。

    exe 的 PE 图标（PyInstaller ``--icon``）与 Tk 的窗口图标是两回事，所以
    ``build_exe.py`` 额外把 .ico 作为数据文件打进包，这里再显式 ``iconbitmap``。
    任何失败都只提示一行、绝不抛异常 —— 图标是装饰，不能挡住安装/转换。
    返回用到的 .ico 路径（没设上则 ``None``）。
    """
    path = icon_path()
    if not path:
        return None
    try:
        root.iconbitmap(path)
        return path
    except Exception as exc:  # noqa: BLE001
        try:
            sys.stderr.write("（窗口图标设置失败，已忽略：%s）\n" % exc)
        except Exception:
            pass
        return None


def resource_dir() -> str:
    """返回内嵌资源（pdms 包）所在目录。

    exe（PyInstaller 单文件）里是解包目录 ``sys._MEIPASS\\pdms``；
    源码模式下按 ``<自身目录>/assets/pdms``、``<自身目录>/pdms``、再向上找
    ``assets/pdms`` 与 v2.1.0 工作树的 ``插件包/pdms``（后者是改名后的唯一真源）。
    """
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
        cand = os.path.join(base, "pdms")
        if os.path.isdir(cand):
            return cand
        return base

    here = os.path.dirname(os.path.abspath(__file__))
    cands = [os.path.join(here, "assets", "pdms"), os.path.join(here, "pdms")]
    parent = here
    for _ in range(3):
        parent = os.path.dirname(parent)
        cands.append(os.path.join(parent, "assets", "pdms"))
        cands.append(os.path.join(parent, "插件包", "pdms"))
    for cand in cands:
        if os.path.isdir(cand):
            return cand
    return cands[0]


def source_files(source_dir: Optional[str] = None) -> List[str]:
    """返回随程序内嵌（或指定目录下）的三个 PML 源文件绝对路径。"""
    base = source_dir or resource_dir()
    return [os.path.join(base, name) for name in REQUIRED_FILES]


def detect_pdms_roots() -> List[str]:
    """探测本机可能的 PDMS 安装根目录（存在 design.uic 的才算）。"""
    cands: List[str] = [DEFAULT_PDMS_ROOT]

    # 常见盘符 + 常见相对路径
    for drive in ("D:", "C:", "E:", "F:"):
        for tail in (r"\AVEVA\Plant\PDMS12.1.SP4", r"\AVEVA\Plant\PDMS12.1",
                     r"\AVEVA\Plant", r"\AVEVA"):
            cands.append(drive + tail)

    # 环境变量
    for key in ("PDMSROOT", "PDMS_ROOT", "PDMSDIR", "PDMS"):
        val = os.environ.get(key)
        if val:
            cands.append(val)

    # 从 PMLLIB 反推：扫 AVEVA 目录下的 Plant\* 
    for drive in ("D:", "C:", "E:", "F:"):
        plant = drive + r"\AVEVA\Plant"
        if os.path.isdir(plant):
            try:
                for name in sorted(os.listdir(plant)):
                    cands.append(os.path.join(plant, name))
            except OSError:
                pass

    seen = set()
    found: List[str] = []
    for path in cands:
        if not path:
            continue
        norm = os.path.normpath(path)
        key = norm.lower()
        if key in seen:
            continue
        seen.add(key)
        if os.path.isfile(os.path.join(norm, "design.uic")):
            found.append(norm)
    return found


def pdms_running() -> List[str]:
    """返回正在运行的 PDMS 相关进程名（小写）；查不到就返回空列表，绝不因此报错。"""
    names = ("des.exe", "pdmsconsole.exe", "mon.exe", "pdms.exe")
    try:
        proc = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20,
        )
    except Exception:
        return []
    raw = proc.stdout or b""
    try:
        text = raw.decode("mbcs", "replace").lower()
    except Exception:
        text = raw.decode("latin-1", "replace").lower()
    return [n for n in names if ('"%s"' % n) in text]


def check_source_encoding(paths: Sequence[str]) -> List[str]:
    """校验 PDMS 侧产物纪律：GBK 可往返、无 BOM、纯 CRLF。返回问题清单（空 = 通过）。"""
    problems: List[str] = []
    for path in paths:
        leaf = os.path.basename(path)
        with open(path, "rb") as fh:
            data = fh.read()
        if data[:3] == BOM_UTF8:
            problems.append("UTF-8 BOM：" + leaf)
            continue
        lone_lf = 0
        for i, byte in enumerate(data):
            if byte == 0x0A and (i == 0 or data[i - 1] != 0x0D):
                lone_lf += 1
        if lone_lf > 0:
            problems.append("非 CRLF 换行 %d 处：%s" % (lone_lf, leaf))
        try:
            roundtrip = data.decode(GBK).encode(GBK)
        except Exception as exc:
            problems.append("GBK 解码失败（%s）：%s" % (exc, leaf))
            continue
        if roundtrip != data:
            problems.append("GBK 往返字节不一致：" + leaf)
    return problems


def _menu_block(nl: str) -> str:
    """与 install.ps1 的 ``$menuBlock`` 逐字节等价（每行前置 4 空格，行间用原换行符）。"""
    inner = [
        '<MenuTool Name="%s">' % MENU_ID,
        "  <Image />",
        "  <Caption>%s</Caption>" % MENU_CAPTION,
        "  <DisplayStyle>Default</DisplayStyle>",
        "  <Tools>",
        '    <Tool Name="%s" />' % BUTTON_ID,
        "  </Tools>",
        "  <IsContextMenu>false</IsContextMenu>",
        "</MenuTool>",
        '<ButtonTool Name="%s">' % BUTTON_ID,
        "  <Command>",
        "    <Type>Macro</Type>",
        "    <Macro>%s</Macro>" % MENU_COMMAND,
        "    <Arguments />",
        "  </Command>",
        "  <Image />",
        "  <Caption>%s</Caption>" % BUTTON_CAPTION,
        "  <DisplayStyle>Default</DisplayStyle>",
        "</ButtonTool>",
    ]
    return nl.join("    " + line for line in inner)


def _bar_line() -> str:
    return '    <Tool Name="%s" />' % MENU_ID


def _line_no(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _last_index_of_before(text: str, needle: str, start: int) -> int:
    """等价于 .NET ``LastIndexOf(value, startIndex)``：匹配起点必须 ≤ start。"""
    return text.rfind(needle, 0, start + len(needle))


def _find_tools_insert(text: str) -> int:
    """顶层 ``</Tools>``——其后（忽略空白）紧跟 ``<InstanceTools`` 的那一个。找不到返回 -1。"""
    from_pos = 0
    while True:
        pos = text.find("</Tools>", from_pos)
        if pos < 0:
            return -1
        if re.match(r"\s*<InstanceTools", text[pos + 8:]):
            return pos
        from_pos = pos + 1


def _xml_ok(text: str) -> Tuple[bool, str]:
    try:
        ET.fromstring(text.encode("utf-8"))
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _unique_backup_path(candidate: str, dry_run: bool) -> str:
    if dry_run:
        return candidate
    path = candidate
    k = 1
    while os.path.exists(path) and k <= COLLISION_LIMIT:
        path = "%s_%d" % (candidate, k)
        k += 1
    return path


def _timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


# ---------------------------------------------------------------- 安装

def do_install(pdms_root: str = DEFAULT_PDMS_ROOT,
               source_dir: Optional[str] = None,
               package_name: str = PACKAGE_NAME_DEFAULT,
               dry_run: bool = False,
               force: bool = False,
               skip_encoding_check: bool = False,
               report: Optional[Sink] = None) -> int:
    """安装 PDMS 侧集成。返回退出码；失败抛 :class:`InstallError`。"""
    say = report or make_printer()

    if not os.path.isdir(pdms_root):
        raise InstallError("PDMS 根目录不存在：" + pdms_root, ExitCode.ARGS)
    uic_path = os.path.join(pdms_root, "design.uic")
    if not os.path.isfile(uic_path):
        raise InstallError("找不到 " + uic_path, ExitCode.ARGS)

    sources = source_files(source_dir)
    for path in sources:
        if not os.path.isfile(path):
            raise InstallError("源包缺少 " + os.path.basename(path), ExitCode.ARGS)
    src_dir_used = os.path.dirname(sources[0])
    target_dir = os.path.join(pdms_root, "PMLLIB", package_name)

    # --- 1) 源文件编码校验
    if not skip_encoding_check:
        problems = check_source_encoding(sources)
        if problems:
            say("源包编码检查未通过（PDMS 侧产物必须 GBK 无 BOM + CRLF）：")
            for item in problems:
                say("   - " + item)
            raise InstallError("源包编码检查未通过", ExitCode.CHECK)

    # --- 2) PDMS 是否在运行
    if not dry_run and not force:
        running = pdms_running()
        if running:
            raise InstallError(
                "PDMS 正在运行（%s）：请先完全退出 PDMS 再安装；确要强行安装请勾选『跳过 PDMS 运行检查』"
                % ", ".join(running), ExitCode.RUNNING)

    # --- 3) 读设计文件并做内存中的 XML 变换
    with open(uic_path, "rb") as fh:
        uic_bytes = fh.read()
    has_bom = uic_bytes[:3] == BOM_UTF8
    try:
        uic_text = uic_bytes.decode("utf-8-sig" if has_bom else "utf-8")
    except UnicodeDecodeError as exc:
        raise InstallError("design.uic 不是合法 UTF-8：%s" % (exc,), ExitCode.CHECK)

    nl = "\r\n" if "\r\n" in uic_text else "\n"
    orig_parses, orig_err = _xml_ok(uic_text)
    already = MENU_ID in uic_text

    menu_block = _menu_block(nl)
    bar_line = _bar_line()
    new_text = uic_text
    ins_tools_line = -1
    ins_bar_line = -1

    if not already:
        if not orig_parses:
            raise InstallError("design.uic 现在就不是合法 XML，拒绝改动：" + orig_err, ExitCode.CHECK)

        idx = _find_tools_insert(uic_text)
        if idx < 0:
            raise InstallError("设计文件里找不到顶层 </Tools>（其后应为 <InstanceTools），拒绝猜测插入点",
                               ExitCode.CHECK)
        bar_count = len(re.findall(r"</MenuBar>", uic_text))
        if bar_count != 1:
            raise InstallError("design.uic 里 </MenuBar> 出现 %d 次，无法唯一定位，拒绝改动" % bar_count,
                               ExitCode.CHECK)
        bar_idx = uic_text.find("</MenuBar>")
        ins_tools_line = _line_no(uic_text, idx)
        ins_bar_line = _line_no(uic_text, bar_idx)

        # 插到 </Tools> 所在行的行首，保留既有缩进
        p = _last_index_of_before(uic_text, nl, max(idx - 1, 0))
        tools_line_start = p + len(nl)
        tools_indent = uic_text[tools_line_start:idx]
        new_text = (uic_text[:tools_line_start] + menu_block + nl + tools_indent
                    + uic_text[idx:])

        bar_idx2 = new_text.find("</MenuBar>")
        q = _last_index_of_before(new_text, nl, max(bar_idx2 - 1, 0))
        bar_line_start = q + len(nl)
        bar_indent = new_text[bar_line_start:bar_idx2]
        new_text = (new_text[:bar_line_start] + bar_line + nl + bar_indent
                    + new_text[bar_idx2:])

        new_parses, new_err = _xml_ok(new_text)
        if not new_parses:
            raise InstallError("追加菜单后 XML 校验失败，未写盘：" + new_err, ExitCode.CHECK)
    else:
        new_parses = True

    # --- 4) 变更清单
    ts = _timestamp()
    bak_path = _unique_backup_path(uic_path + ".bak_pkpm2pdms_" + ts, dry_run)

    say("=" * 62)
    say(" PKPM2PDMS导入导出 安装程序 v%s%s" % (VERSION, "（仅预览，不落盘）" if dry_run else ""))
    say("=" * 62)
    say("PDMS 根      : " + pdms_root)
    say("源包目录     : " + src_dir_used + ("（内嵌于安装程序）" if getattr(sys, "frozen", False) else ""))
    say("目标包目录   : " + target_dir)
    say("")
    say("【1】将新增/覆盖的文件（逐条）：")
    for path in sources:
        leaf = os.path.basename(path)
        dst = os.path.join(target_dir, leaf)
        action = "覆盖" if os.path.exists(dst) else "新增"
        say("   %s  %s" % (action, dst))
        say("         ← %s   (%d 字节)" % (path, os.path.getsize(path)))
    say("")
    say("【2】design.uic 追加菜单项：")
    say("   文件       : " + uic_path)
    say("   当前状态   : " + ("已含 %s —— 本次跳过注入（幂等）" % MENU_ID if already else
                            "未含 %s，将追加" % MENU_ID))
    say("   原文件     : %d 字节，%d 行，BOM=%s，换行=%s"
        % (len(uic_bytes), uic_text.count("\n") + 1,
           "True" if has_bom else "False", "CRLF" if nl == "\r\n" else "LF"))
    say("   现在即可解析 XML : %s" % ("True" if orig_parses else "False"))
    if not already:
        say("   备份为     : " + bak_path)
        say("   插入点 1   : 第 %d 行 </Tools> 之前（<Tools> 段的末尾）" % ins_tools_line)
        say("   插入点 2   : 第 %d 行 </MenuBar> 之前（菜单栏末尾）" % ins_bar_line)
        say("   追加内容   :")
        for line in menu_block.split("\n"):
            say("      " + line)
        say("      " + bar_line)
        say("   写回后     : %d 字节，%d 行，UTF-8%s + 原换行风格"
            % (len(new_text.encode("utf-8")) + (3 if has_bom else 0),
               new_text.count("\n") + 1, " 带 BOM" if has_bom else " 无 BOM"))
        say("   写前校验   : 追加后 XML 解析 %s" % ("通过" if new_parses else "失败"))
        say("   写后校验   : 回读并重新解析 design.uic；失败则用上面的 .bak 回滚")
    say("")
    say("【3】不做的事：")
    say("   - 不改 DesignAddins.xml（本包是纯 PML，没有 .NET add-in 可登记）")
    say("   - 不删除、不重排、不改写 design.uic 既有条目（TGTEXT / PDCOPILOT 等原样保留）")
    say("   - 不动 P-TRANS 目录、不动任何样本原件、不动 PMLLIB\\pml.index")
    say("")

    if dry_run:
        say("预览完成：以上为将要发生的全部改动，未写入任何文件。")
        return ExitCode.OK

    # --- 5) 执行：备份 → 复制 PML → 写回设计文件（失败即回滚）
    say("【4】开始安装 …")
    rolled_back = False
    if not already:
        try:
            shutil.copy2(uic_path, bak_path)
            say("   已备份 design.uic → " + bak_path)
        except Exception as exc:
            raise InstallError("备份 design.uic 失败，未做任何改动：%s" % (exc,), ExitCode.WRITE)

    try:
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)
            say("   已创建目录 " + target_dir)
        for path in sources:
            dst = os.path.join(target_dir, os.path.basename(path))
            shutil.copy2(path, dst)
            say("   已复制 " + dst)
    except Exception as exc:
        raise InstallError("复制 PML 失败：%s（design.uic 未被改动，已备份于 %s）" % (exc, bak_path),
                           ExitCode.WRITE)

    if not already:
        out_bytes = new_text.encode("utf-8")
        if has_bom:
            out_bytes = BOM_UTF8 + out_bytes
        try:
            with open(uic_path, "wb") as fh:
                fh.write(out_bytes)
            say("   已写回 design.uic（%d 字节）" % len(out_bytes))
        except Exception as exc:
            say("   写 design.uic 失败：%s —— 尝试回滚" % (exc,))
            with open(uic_path, "wb") as fh:
                fh.write(uic_bytes)
            rolled_back = True

        if not rolled_back:
            try:
                with open(uic_path, "rb") as fh:
                    verify = fh.read()
                verify_text = verify.decode("utf-8-sig" if has_bom else "utf-8")
                ok, err = _xml_ok(verify_text)
                if not ok:
                    raise ValueError("XML 解析失败：" + err)
                if MENU_ID not in verify_text:
                    raise ValueError("回读内容里没有 " + MENU_ID)
                say("   写后校验通过（XML 可解析，菜单项存在）")
            except Exception as exc:
                say("   写后校验失败：%s —— 用备份回滚" % (exc,))
                with open(uic_path, "wb") as fh:
                    fh.write(uic_bytes)
                rolled_back = True

        if rolled_back:
            try:
                with open(uic_path, "rb") as fh:
                    text = fh.read().decode("utf-8-sig" if has_bom else "utf-8")
                ok, err = _xml_ok(text)
                if not ok:
                    raise ValueError(err)
                say("   回滚完成：design.uic 已恢复为安装前内容（XML 可解析）")
            except Exception as exc:
                raise InstallError("回滚后 design.uic 仍不可解析（%s）！请手动用 %s 覆盖恢复"
                                   % (exc, bak_path), ExitCode.WRITE)
            return ExitCode.WRITE
    else:
        say("   design.uic 已含 %s，跳过注入与备份（幂等）" % MENU_ID)

    say("")
    say("【5】安装结果：")
    say("   包目录     : " + target_dir)
    for path in sources:
        leaf = os.path.basename(path)
        dst = os.path.join(target_dir, leaf)
        say("     %s  %d 字节  %s" % (leaf, os.path.getsize(dst),
                                     time.strftime("%Y-%m-%d %H:%M:%S",
                                                   time.localtime(os.path.getmtime(dst)))))
    final_ok = False
    try:
        with open(uic_path, "rb") as fh:
            final = fh.read().decode("utf-8-sig")
        ok, _ = _xml_ok(final)
        final_ok = ok and (MENU_ID in final)
    except Exception:
        pass
    say("   design.uic : 可解析且含菜单项 = %s" % ("True" if final_ok else "False"))
    say("")
    say("接下来：完全退出并重启 PDMS（新 PML 文件需要重启后才会被索引；")
    say("        不要手工运行 pmlscan.exe，也不要改 PMLLIB\\pml.index）。")
    say("        进入 DESIGN 后菜单栏应出现「PKPM2PDMS」，或命令行执行")
    say('        $m "%PMLLIB%/pkpm2pdms/pkpm2pdmsrun.mac" 打开窗体。')
    return ExitCode.OK


# ---------------------------------------------------------------- 卸载

_UNINSTALL_PATTERNS = (
    ("ButtonTool PKPM2PDMS.PML.Open",
     re.compile(r'[ \t]*<ButtonTool Name="PKPM2PDMS\.(?:PML\.)?Open">.*?</ButtonTool>\r?\n', re.S)),
    ("MenuTool PKPM2PDMS.PML.Menu",
     re.compile(r'[ \t]*<MenuTool Name="PKPM2PDMS\.(?:PML\.)?Menu">.*?</MenuTool>\r?\n', re.S)),
    ("MenuBar Tool PKPM2PDMS.PML.Menu",
     re.compile(r'^[ \t]*<Tool Name="PKPM2PDMS\.(?:PML\.)?Menu" />[ \t]*\r?\n', re.M)),
)


def do_uninstall(pdms_root: str = DEFAULT_PDMS_ROOT,
                 package_name: str = PACKAGE_NAME_DEFAULT,
                 dry_run: bool = False,
                 purge: bool = False,
                 restore_backup: bool = False,
                 report: Optional[Sink] = None) -> int:
    """卸载 PDMS 侧集成。默认「整目录移动」，不删除任何文件。"""
    say = report or make_printer()

    if not os.path.isdir(pdms_root):
        raise InstallError("PDMS 根目录不存在：" + pdms_root, ExitCode.ARGS)

    uic_path = os.path.join(pdms_root, "design.uic")
    target_dir = os.path.join(pdms_root, "PMLLIB", package_name)
    ts = _timestamp()
    has_uic = os.path.isfile(uic_path)

    say("=" * 62)
    say(" PKPM2PDMS导入导出 卸载程序 v%s%s" % (VERSION, "（仅预览，不落盘）" if dry_run else ""))
    say("=" * 62)
    say("PDMS 根     : " + pdms_root)
    say("包目录      : " + target_dir)
    say("")

    baks: List[str] = []
    if has_uic:
        try:
            for name in os.listdir(pdms_root):
                if name.startswith("design.uic.bak_pkpm2pdms_"):
                    baks.append(os.path.join(pdms_root, name))
        except OSError:
            pass
        baks.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    say("【1】已有的安装前备份 design.uic.bak_pkpm2pdms_* ：%d 个" % len(baks))
    for path in baks:
        say("      %s   %s   %d 字节"
            % (os.path.basename(path),
               time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(path))),
               os.path.getsize(path)))
    uninstall_bak = uic_path + ".bak_uninstall_" + ts
    say("      本次卸载前备份为： " + uninstall_bak)
    say("")

    uic_bytes = b""
    uic_text = ""
    new_text = ""
    changed = False
    counts = []
    has_bom = False
    if has_uic:
        with open(uic_path, "rb") as fh:
            uic_bytes = fh.read()
        has_bom = uic_bytes[:3] == BOM_UTF8
        try:
            uic_text = uic_bytes.decode("utf-8-sig" if has_bom else "utf-8")
        except UnicodeDecodeError as exc:
            raise InstallError("design.uic 不是合法 UTF-8：%s" % (exc,), ExitCode.CHECK)
        new_text = uic_text
        for label, pattern in _UNINSTALL_PATTERNS:
            hits = len(pattern.findall(new_text))
            counts.append((label, hits))
            if hits > 0:
                changed = True
                new_text = pattern.sub("", new_text)
        orphan = len(re.findall(r"PKPM2PDMS", new_text))
        say("【2】design.uic 内本包条目的移除计划：")
        for label, hits in counts:
            say("      %s ： 命中 %d 处" % (label, hits))
        say("      移除后残留 PKPM2PDMS 字样 ： %d 处（应为 0）" % orphan)
        say("      是否需要写回 ： %s" % ("True" if changed else "False"))
        if changed:
            ok, err = _xml_ok(new_text)
            if not ok:
                raise InstallError("移除条目后 XML 校验失败，未写盘：" + err, ExitCode.CHECK)
    else:
        say("【2】找不到 design.uic：跳过菜单条目移除")
    say("")

    dir_files: List[str] = []
    if os.path.isdir(target_dir):
        try:
            dir_files = sorted(os.path.join(target_dir, n) for n in os.listdir(target_dir))
        except OSError:
            dir_files = []
    moved_to = os.path.join(pdms_root, "PMLLIB", "_removed_%s_%s" % (package_name, ts))
    say("【3】包目录处理：")
    if not dir_files and not os.path.isdir(target_dir):
        say("      不存在： %s （无需处理）" % target_dir)
    else:
        say("      目录内文件 %d 个（逐条列出，不用通配符）：" % len(dir_files))
        for path in dir_files:
            say("        %s   %d 字节" % (path, os.path.getsize(path)))
        if purge:
            say("      模式：清除 —— 按上面列出的确切路径逐条删除该目录内文件")
        else:
            say("      模式：默认 —— 整目录移动为 %s （不删文件）" % moved_to)
    say("")
    if restore_backup:
        say("【4】整份恢复：将用最新的 design.uic.bak_pkpm2pdms_* 覆盖 design.uic")
        if not baks:
            say("      没有可用备份 → 该项跳过")
        else:
            say("      使用： " + os.path.basename(baks[0]))
        say("")

    if dry_run:
        say("预览完成：以上为将要发生的全部改动，未写入/未移动任何文件。")
        return ExitCode.OK

    say("【5】开始卸载 …")
    rolled_back = False
    if restore_backup and baks:
        try:
            shutil.copy2(uic_path, uninstall_bak)
            say("   已备份 design.uic → " + uninstall_bak)
        except Exception as exc:
            raise InstallError("备份 design.uic 失败，未做任何改动：%s" % (exc,), ExitCode.WRITE)
        try:
            with open(baks[0], "rb") as fh:
                shutil.copyfileobj(fh, open(uic_path, "wb"))
            with open(uic_path, "rb") as fh:
                text = fh.read().decode("utf-8-sig" if has_bom else "utf-8", "replace")
            ok, err = _xml_ok(text)
            if not ok:
                raise ValueError(err)
            say("   已按备份整份恢复： " + os.path.basename(baks[0]))
        except Exception as exc:
            say("   恢复失败：%s —— 回滚本次改动" % (exc,))
            with open(uic_path, "wb") as fh:
                fh.write(uic_bytes)
            raise InstallError("恢复备份失败，已回滚；请人工检查 design.uic", ExitCode.WRITE)
    elif changed:
        try:
            shutil.copy2(uic_path, uninstall_bak)
            say("   已备份 design.uic → " + uninstall_bak)
        except Exception as exc:
            raise InstallError("备份 design.uic 失败，未做任何改动：%s" % (exc,), ExitCode.WRITE)
        out_bytes = new_text.encode("utf-8")
        if has_bom:
            out_bytes = BOM_UTF8 + out_bytes
        try:
            with open(uic_path, "wb") as fh:
                fh.write(out_bytes)
            with open(uic_path, "rb") as fh:
                verify = fh.read().decode("utf-8-sig" if has_bom else "utf-8")
            ok, err = _xml_ok(verify)
            if not ok:
                raise ValueError("XML 解析失败：" + err)
            if "PKPM2PDMS" in verify:
                raise ValueError("回读内容里仍有 PKPM2PDMS 字样")
            say("   已移除本包条目，写后校验通过（XML 可解析、无 PKPM2PDMS 残留）")
        except Exception as exc:
            say("   写后校验失败：%s —— 用备份回滚" % (exc,))
            with open(uic_path, "wb") as fh:
                fh.write(uic_bytes)
            rolled_back = True
        if rolled_back:
            try:
                with open(uic_path, "rb") as fh:
                    text = fh.read().decode("utf-8-sig" if has_bom else "utf-8")
                ok, err = _xml_ok(text)
                if not ok:
                    raise ValueError(err)
                say("   回滚完成：design.uic 已恢复为卸载前内容")
            except Exception as exc:
                raise InstallError("回滚后 design.uic 仍不可解析（%s）！请手动用 %s 覆盖恢复"
                                   % (exc, uninstall_bak), ExitCode.WRITE)
            return ExitCode.WRITE
    else:
        say("   design.uic 无本包条目：跳过（幂等）")

    if os.path.isdir(target_dir):
        if purge:
            say("   删除包目录内已列出的文件：")
            for path in dir_files:
                say("     删 " + path)
            failures = []
            for path in dir_files:
                try:
                    os.remove(path)
                except Exception as exc:
                    failures.append("%s（%s）" % (path, exc))
            left = []
            for root, _dirs, files in os.walk(target_dir):
                for name in files:
                    left.append(os.path.join(root, name))
            if left or failures:
                say("   目录内仍有 %d 项（子目录或删除失败），保留目录： %s" % (len(left), target_dir))
                for path in left:
                    say("     保留 " + path)
                for item in failures:
                    say("     删除失败 " + item)
            else:
                try:
                    os.rmdir(target_dir)
                    say("   已删除空目录 " + target_dir)
                except Exception as exc:
                    say("   删除空目录失败（保留）：%s" % (exc,))
        else:
            if os.path.exists(moved_to):
                raise InstallError("目标备份目录已存在，请改名后重试： " + moved_to, ExitCode.WRITE)
            shutil.move(target_dir, moved_to)
            say("   已把包目录移动到 %s （未删除任何文件；确认无误后可自行清理）" % moved_to)
    else:
        say("   包目录不存在，跳过： " + target_dir)

    say("")
    say("【6】卸载结果：")
    uic_ok = False
    if os.path.isfile(uic_path):
        try:
            with open(uic_path, "rb") as fh:
                text = fh.read().decode("utf-8-sig", "replace")
            ok, _ = _xml_ok(text)
            uic_ok = ok and ("PKPM2PDMS" not in text)
        except Exception:
            pass
    say("   design.uic : 可解析且无本包条目 = %s" % ("True" if uic_ok else "False"))
    say("   包目录     : 存在 = %s" % ("True" if os.path.isdir(target_dir) else "False"))
    say("")
    say("提示：卸载后完全退出并重启 PDMS 生效；不要手工运行 pmlscan.exe、不要改 PMLLIB\\pml.index。")
    return ExitCode.OK
