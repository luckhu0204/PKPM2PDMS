#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""collect_to_workspace.py —— 把成品归集到工作区交付目录（只新增 / 不覆盖 / 不删除）

做什么
------
把三样东西归集到一个目录，让用户在一个地方拿到全部东西::

    D:\\AI_Work\\PKPM数据解析\\交付_PKPM-JWD插件\\
        插件包\\          <- PKPM-JWD导入导出\\ 完整复制（跳过缓存/临时目录）
        安装程序\\        <- 安装包程序\\dist\\ 的两个 exe + 安装说明.txt（若存在）
        交付清单.txt      <- 自动生成：逐文件清单(SHA256) + 版本 + 怎么用
        从这里开始.txt    <- 自动生成：三五行快速上手

硬性纪律（代码里逐条对应）
--------------------------
1. **绝不删除任何文件**：本脚本没有删除/移动/改名调用（无 os.remove/os.rmdir/
   shutil.rmtree/move）；目标侧只做「创建目录」和「独占新建文件」。
2. **不碰 G 盘**：脚本所有默认路径都在 D 盘工作区内；没有任何 G: 路径。
3. **目标已存在且非空 = 拒绝执行**：打印现状后退出码 **2**，不强行覆盖。
4. **绝不覆盖既有文件**：所有文件用 ``open(..., "xb")`` 独占创建；同名已存在则记
   CONFLICT 跳过，最后以退出码 3 报告。
5. **所有路径先打印后动手**：复制前把每个源路径、每个目标路径、跳过项逐条打印。
6. **逐文件校验**：复制后对每个文件比对**字节数 + SHA256**，输出清单与结论。
7. **跳过临时/缓存**：``__pycache__``、``test/_dev``、``test/_acc_tmp`` 及同类
   （tmp/temp/*_tmp/*_temp/*_cache/*_scratch）、``_备份_待删_*``、``*.pyc``、
   本脚本与 copy_to_plugin.py 的运行日志。

只用标准库。PDMS 侧产物（.mac/.pmlfrm/.pmlfnc）是**原样字节复制**，编码不受本脚本
影响；本脚本自己生成的两个 txt 用 **UTF-8 带 BOM + CRLF**（记事本双击即可正确打开，
不会猜成 GBK 乱码）；Python 源码 UTF-8。

退出码：0 成功且校验全过；1 致命错误；2 目标已存在且非空（拒绝）；3 有冲突/校验不一致。
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import os
import re
import stat
import sys
import time
from pathlib import Path

# --------------------------------------------------------------------------- 默认路径（全部在 D 盘工作区内，不涉及 G:）
SRC_DEFAULT = r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出"
DST_DEFAULT = r"D:\AI_Work\PKPM数据解析\交付_PKPM-JWD插件"
EXE_SRC_DEFAULT = r"D:\AI_Work\PKPM数据解析\安装包程序"

PKG_DIR_NAME = "插件包"
EXE_DIR_NAME = "安装程序"
MANIFEST_NAME = "交付清单.txt"
START_HERE_NAME = "从这里开始.txt"
#: §q-19① 的哈希清单（文件名含"哈希"；由本脚本生成/刷新，UTF-8 带 BOM + CRLF）
HASH_LIST_NAME = "SHA256哈希清单.txt"

# --------------------------------------------------------------------------- 退出码
EXIT_OK = 0
EXIT_FATAL = 1
EXIT_REFUSED = 2
EXIT_PROBLEM = 3

# --------------------------------------------------------------------------- 跳过规则（只用于"跳过复制"，绝不用于删除）
# 目录名精确匹配（小写比较）。_dev：本次任务点名跳过 test/_dev。
# _selftest：deploy 脚本的沙箱（验收检查 17 的产物，含 junction，非交付物，R3 §0.4-9）；
# _pybuild / _rootsim：PyInstaller 工作目录与同名沙箱残留（构建/测试产物，非交付物）。
TEMP_DIR_NAMES = {"__pycache__", "tmp", "temp", "_tmp", "_temp", ".tmp", ".temp", "_dev",
                  "_selftest", "_pybuild", "_rootsim"}
# 目录名后缀匹配
TEMP_DIR_SUFFIXES = ("_tmp", "_temp", "_cache", "__pycache__", "_scratch")
# 目录名前缀匹配：工作区"待删备份暂存区"，不属于交付物
BACKUP_DIR_PREFIXES = ("_备份_待删_",)
# 文件：跳过字节码与本工具自己的运行日志
SKIP_FILE_SUFFIXES = (".pyc", ".pyo")
SKIP_FILE_PREFIXES = ("_copy_to_plugin_log", "_collect_to_workspace_log")

HASH_CHUNK = 1024 * 1024


# --------------------------------------------------------------------------- 输出
class Reporter:
    """打印到控制台（按控制台代码页，避免乱码）并把全文留作日志。"""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.log_path: Path | None = None
        self.log_error: str | None = None

    def __call__(self, text: str = "") -> None:
        self.lines.append(text)
        try:
            print(text)
        except UnicodeEncodeError:
            enc = getattr(sys.stdout, "encoding", None) or "ascii"
            print(text.encode(enc, "replace").decode(enc, "replace"))

    def flush_log(self) -> None:
        if self.log_path is None:
            return
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if self.log_path.exists() else "x"
            # newline=""：\r\n 原样落盘，绝不再翻译（避免上个脚本 0D 0D 0A 的问题）
            with open(self.log_path, mode, encoding="utf-8", newline="") as fh:
                if mode == "x":
                    fh.write("\ufeff")
                fh.write("\r\n".join(self.lines) + "\r\n")
        except Exception as exc:
            self.log_error = f"{type(exc).__name__}: {exc}"


def console_encoding() -> str:
    """本机控制台输出代码页（cmd 默认 936/GBK）；拿不到退回 UTF-8。"""
    if os.name == "nt":
        try:
            cp = int(ctypes.windll.kernel32.GetConsoleOutputCP())  # type: ignore[attr-defined]
        except Exception:
            cp = 0
        if cp:
            try:
                "测试".encode("cp%d" % cp)
                return "cp%d" % cp
            except (LookupError, UnicodeEncodeError):
                return "utf-8"
    return "utf-8"


def setup_console() -> None:
    enc = console_encoding()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding=enc, errors="replace")
            except Exception:
                pass


# --------------------------------------------------------------------------- 工具
def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(HASH_CHUNK)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def fmt_size(n: int) -> str:
    if n < 1024 * 1024:
        return f"{n:,} B ({n / 1024.0:,.1f} KiB)"
    return f"{n:,} B ({n / 1024.0 / 1024.0:,.2f} MiB)"


def dir_skip_reason(name: str) -> str | None:
    low = name.lower()
    if low in TEMP_DIR_NAMES:
        return "缓存/临时目录（本次任务点名跳过）" if low == "_dev" else "缓存/临时目录"
    if low.endswith(TEMP_DIR_SUFFIXES):
        return "缓存/临时目录"
    if name.startswith(BACKUP_DIR_PREFIXES):
        return "待删备份暂存区（非交付物）"
    return None


def file_skip_reason(name: str) -> str | None:
    low = name.lower()
    if low.endswith(SKIP_FILE_SUFFIXES):
        return "Python 字节码"
    if low.startswith(SKIP_FILE_PREFIXES):
        return "交付脚本自己的运行日志"
    return None


def tree_stats(path: Path) -> tuple[int, int]:
    """递归统计 (文件数, 字节总数)。"""
    files = 0
    total = 0
    for root, _dirs, names in os.walk(path, onerror=lambda _e: None):
        for name in names:
            try:
                total += (Path(root) / name).stat().st_size
                files += 1
            except OSError:
                pass
    return files, total


def write_text_file(path: Path, lines: list[str]) -> None:
    """独占新建一个 UTF-8(BOM) + CRLF 文本文件；已存在则抛 FileExistsError。"""
    data = "\ufeff" + "\r\n".join(lines) + "\r\n"
    with open(path, "x", encoding="utf-8", newline="") as fh:
        fh.write(data)


def write_text_file_refresh(path: Path, lines: list[str]) -> None:
    """刷新模式的写法：本脚本**自己生成**的文件允许覆盖（仍是生成物，不是用户数据）。"""
    data = "\ufeff" + "\r\n".join(lines) + "\r\n"
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(data)


def copy_file_update(abs_path: Path, target: Path) -> tuple[str, str]:
    """刷新模式的复制：added（新建）/ updated（存在但字节或 SHA 不同 → 覆盖）/ same。

    返回 ``(动作, 说明)``；**从不删除**任何目标文件。
    """
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return "error", f"建目录失败 {type(exc).__name__}: {exc}"
    try:
        existed = target.exists()
        if existed:
            t_size, t_hash = target.stat().st_size, sha256_of(target)
            s_size, s_hash = abs_path.stat().st_size, sha256_of(abs_path)
            if t_size == s_size and t_hash == s_hash:
                return "same", ""
        with open(abs_path, "rb") as fsrc, open(target, "wb") as fdst:
            while True:
                chunk = fsrc.read(HASH_CHUNK)
                if not chunk:
                    break
                fdst.write(chunk)
        try:
            st = abs_path.stat()
            os.utime(target, (st.st_atime, st.st_mtime))
        except OSError:
            pass
        return ("updated" if existed else "added"), ""
    except OSError as exc:
        return "error", f"{type(exc).__name__}: {exc}"


# --------------------------------------------------------------------------- 版本探测（有据可查：读文件，不猜）
def probe_versions(src: Path) -> tuple[str, str, str]:
    """返回 (包版本, 契约版本, 依据)。读不到就如实写"未找到"。"""
    pkg_ver = None
    contract_ver = None
    basis: list[str] = []
    usage = src / "docs" / "使用说明.md"
    if usage.is_file():
        try:
            head = usage.read_text(encoding="utf-8", errors="replace")[:2000]
            m = re.search(r"版本[：:]\s*v([0-9][0-9.]*)", head)
            if m:
                pkg_ver = "v" + m.group(1)
                basis.append(f"docs/使用说明.md 头部『版本：v{m.group(1)}』")
        except OSError:
            pass
    for rel in ("spec/CONTRACT.md", "engine/canonical.py"):
        p = src / rel
        if contract_ver is None and p.is_file():
            try:
                text = p.read_text(encoding="utf-8", errors="replace")[:8000]
                m = re.search(r'CONTRACT_VERSION\s*=\s*"([^"]+)"', text)
                if m:
                    contract_ver = m.group(1)
                    basis.append(f"{rel} 的 CONTRACT_VERSION = \"{m.group(1)}\"")
            except OSError:
                pass
    ver = pkg_ver or "未知（未能在 docs/使用说明.md 定位版本串）"
    cv = contract_ver or "未知"
    return ver, cv, "；".join(basis) if basis else "未找到版本依据"


# --------------------------------------------------------------------------- 扫描插件包
def is_reparse_dir(path: Path) -> bool:
    """目录是否为符号链接/junction（reparse point）——一律不跟随、不复制（R3）。"""
    try:
        st = os.lstat(path)
    except OSError:
        return True
    attrs = getattr(st, "st_file_attributes", 0)
    if attrs and attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        return True
    try:
        return bool(path.is_symlink())
    except OSError:
        return True


def scan_package(src: Path, rep: Reporter) -> tuple[list[tuple[Path, str]], list[tuple[str, str, int, int]], list[tuple[str, str]]]:
    files: list[tuple[Path, str]] = []
    skipped_dirs: list[tuple[str, str, int, int]] = []
    skipped_files: list[tuple[str, str]] = []
    for root, dirs, names in os.walk(src):
        root_path = Path(root)
        dirs.sort()
        names.sort()
        keep: list[str] = []
        for d in dirs:
            reason = dir_skip_reason(d)
            sub = root_path / d
            if reason is None and is_reparse_dir(sub):
                reason = "符号链接/junction（不跟随、不复制，R3）"
            if reason is None:
                keep.append(d)
                continue
            fcount, _bytes = tree_stats(sub) if not is_reparse_dir(sub) else (0, 0)
            rel = str(sub.relative_to(src))
            skipped_dirs.append((rel, reason, fcount, fcount))
        dirs[:] = keep
        for name in names:
            reason = file_skip_reason(name)
            abs_path = root_path / name
            rel = str(abs_path.relative_to(src))
            if reason is not None:
                skipped_files.append((rel, reason))
                continue
            if abs_path.is_symlink() or (abs_path.exists() is False):
                skipped_files.append((rel, "符号链接/断链（不跟随）"))
                continue
            files.append((abs_path, rel))
    files.sort(key=lambda item: item[1].replace("\\", "/").lower())
    return files, skipped_dirs, skipped_files


# --------------------------------------------------------------------------- 找安装程序
def find_installer_files(exe_src: Path, rep: Reporter) -> tuple[list[tuple[Path, str]], list[str]]:
    """返回 ([(源绝对路径, 目标文件名)], 说明)。只枚举，不复制。"""
    found: list[tuple[Path, str]] = []
    notes: list[str] = []
    if not exe_src.is_dir():
        notes.append(f"安装包程序目录不存在：{exe_src}（『若存在』条件不成立，跳过安装程序部分）")
        return found, notes
    dist = exe_src / "dist"
    scan_dirs = [dist] if dist.is_dir() else [exe_src]
    if not dist.is_dir():
        notes.append(f"未找到 dist 子目录，退回扫描 {exe_src}")
    for scan in scan_dirs:
        for entry in sorted(scan.iterdir()):
            if not entry.is_file():
                continue
            name = entry.name
            if name.lower().endswith(".exe") and ".备份_" not in name:
                found.append((entry, name))
            elif ".备份_" in name:
                notes.append(f"发现但【未复制】（备份）：{entry}")
    readme: Path | None = None
    for cand in (exe_src / "安装说明.txt", exe_src / "dist" / "安装说明.txt"):
        if cand.is_file():
            readme = cand
            break
    if readme is not None:
        found.append((readme, readme.name))
        if readme.parent != scan_dirs[0]:
            notes.append(f"安装说明.txt 不在 dist 下，取自其实际位置：{readme}")
    else:
        notes.append("未找到 安装说明.txt（已检查 安装包程序\\ 与 安装包程序\\dist\\）")
    return found, notes


# --------------------------------------------------------------------------- 复制
def copy_file_exclusive(abs_path: Path, target: Path) -> str:
    """独占新建复制。返回 'ok' / 'conflict' / 错误消息。"""
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return f"建目录失败 {type(exc).__name__}: {exc}"
    try:
        with open(abs_path, "rb") as fsrc, open(target, "xb") as fdst:
            while True:
                chunk = fsrc.read(HASH_CHUNK)
                if not chunk:
                    break
                fdst.write(chunk)
        try:
            st = abs_path.stat()
            os.utime(target, (st.st_atime, st.st_mtime))
        except OSError:
            pass
        return "ok"
    except FileExistsError:
        return "conflict"
    except OSError as exc:
        return f"{type(exc).__name__}: {exc}"


# --------------------------------------------------------------------------- 目录树（两层深）
def print_tree(dst: Path, rep: Reporter) -> int:
    rep("")
    rep("=" * 78)
    rep(f"【最终目录树（两层深）】{dst}")
    rep("=" * 78)
    grand_files, grand_bytes = 0, 0
    try:
        level1 = sorted(dst.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except OSError as exc:
        rep(f"  [无法列出目标目录：{exc}]")
        return 0
    for i, child in enumerate(level1):
        branch = "└─" if i == len(level1) - 1 else "├─"
        if child.is_dir():
            f, b = tree_stats(child)
            grand_files += f
            grand_bytes += b
            rep(f"{branch} {child.name}\\   <- {f} 个文件 / {fmt_size(b)}（递归）")
            prefix = "   " if i == len(level1) - 1 else "│  "
            try:
                level2 = sorted(child.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            except OSError:
                continue
            for j, sub in enumerate(level2):
                leaf = "└─" if j == len(level2) - 1 else "├─"
                if sub.is_dir():
                    sf, sb = tree_stats(sub)
                    rep(f"{prefix}  {leaf} {sub.name}\\   ({sf} 文件 / {fmt_size(sb)} 递归)")
                else:
                    try:
                        size = sub.stat().st_size
                    except OSError:
                        size = -1
                    rep(f"{prefix}  {leaf} {sub.name}   {'' if size < 0 else format(size, ',') + ' B'}")
        else:
            try:
                size = child.stat().st_size
                grand_files += 1
                grand_bytes += size
                rep(f"{branch} {child.name}   {size:,} B")
            except OSError:
                rep(f"{branch} {child.name}   [无法读取]")
    rep("-" * 78)
    rep(f"合计：{grand_files} 个文件 / {fmt_size(grand_bytes)}")
    return grand_bytes


# --------------------------------------------------------------------------- 主流程
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="把成品归集到工作区交付目录（只新增 / 不覆盖 / 不删除 / 不碰 G 盘）",
        epilog="退出码：0=成功且校验通过；1=致命错误；2=目标已存在且非空（拒绝）；3=有冲突/校验不一致",
    )
    parser.add_argument("--src", default=SRC_DEFAULT, help="插件包源目录")
    parser.add_argument("--dst", default=DST_DEFAULT, help="交付目录（将新建）")
    parser.add_argument("--exe-src", default=EXE_SRC_DEFAULT, help="安装包程序目录（找 dist 下 exe 与 安装说明.txt）")
    parser.add_argument("--list-only", action="store_true", help="只打印计划，不写任何东西")
    parser.add_argument("--refresh", action="store_true",
                        help="R3：目标已存在时**刷新**（新增缺失文件 + 覆盖与源不一致的本包生成物/副本文件；"
                             "从不删除，目标多出的文件记 STALE 留待人工处理）。缺省仍是不覆盖、拒绝执行。")
    parser.add_argument("--log", default=None, help="日志文件（默认 <src>\\deliver\\_collect_to_workspace_log.txt；- 表示不写）")
    args = parser.parse_args(argv)

    src = Path(args.src).expanduser()
    dst = Path(args.dst).expanduser()
    exe_src = Path(args.exe_src).expanduser()

    rep = Reporter()
    if args.log != "-":
        rep.log_path = Path(args.log).expanduser() if args.log else src / "deliver" / "_collect_to_workspace_log.txt"

    started = time.strftime("%Y-%m-%d %H:%M:%S")
    rep("=" * 78)
    rep("collect_to_workspace.py —— 成品归集到工作区（只新增 / 不覆盖 / 不删除 / 不碰 G 盘）")
    rep("=" * 78)
    rep(f"开始时间       : {started}")
    rep(f"插件包源目录   : {src}")
    rep(f"交付目录(目标) : {dst}")
    rep(f"安装程序源目录 : {exe_src}（exe 在其 dist\\ 下，安装说明.txt 在其根下）")
    rep(f"本次参数       : list_only={args.list_only}")
    rep("跳过规则       : __pycache__/test\\_dev/test\\_acc_tmp 及同类临时目录、_备份_待删_*、")
    rep("                 *.pyc/*.pyo、交付脚本运行日志（只影响复制，不做任何删除）")
    rep("写入的文件     : <目标>\\插件包\\...、<目标>\\安装程序\\...、交付清单.txt、从这里开始.txt")
    rep("                 两个 txt 由本脚本生成，UTF-8 带 BOM + CRLF")
    rep("")

    # ---------------- 1. 源检查
    if not src.is_dir():
        rep(f"[致命] 插件包源目录不存在：{src}")
        rep.flush_log()
        return EXIT_FATAL

    pkg_ver, contract_ver, ver_basis = probe_versions(src)

    # ---------------- 2. 目标现状
    rep("-" * 78)
    rep("【1】目标现状")
    rep("-" * 78)
    if dst.exists() and not dst.is_dir():
        rep(f"[致命] 目标路径存在但不是目录：{dst}")
        rep.flush_log()
        return EXIT_FATAL
    if not dst.exists():
        rep(f"目标目录不存在：{dst}")
        rep("  -> 将创建该目录及下列子目录（逐文件创建，不覆盖任何东西）。")
        nonempty = False
    else:
        f, b = tree_stats(dst)
        nonempty = f > 0
        rep(f"目标目录已存在：{dst}   （{f} 个文件 / {fmt_size(b)}）")
        shown = 0
        for root, dirs, files in os.walk(dst):
            dirs.sort()
            files.sort()
            for name in dirs + files:
                if shown < 25:
                    rep("    " + os.path.join(root, name))
                shown += 1
            if shown >= 25:
                break
        if shown > 25:
            rep(f"    ...（共 {shown} 项，仅列前 25 项）")
    if nonempty and not args.refresh:
        rep("")
        rep("【拒绝执行】目标目录已存在且非空 —— 不覆盖、不动它，交人来判断。")
        rep("  可选做法（本脚本一个都不替你做）：")
        rep("    1) 自己看过上面清单后把该目录改名/移走，再重跑；")
        rep("    2) 换 --dst 指向新的空目录；")
        rep("    3) 用 --list-only 只查看计划；")
        rep("    4) R3 起：加 --refresh 刷新既有交付目录（新增缺失文件、覆盖与源不一致的文件；")
        rep("       从不删除，目标多出的文件记 STALE 留待人工处理）。")
        rep("  本次未创建、未修改、未删除任何文件。")
        rep(f"结论：REFUSED（目标已存在且非空，未给 --refresh）  |  退出码 {EXIT_REFUSED}")
        rep.flush_log()
        return EXIT_REFUSED
    refresh_mode = bool(nonempty and args.refresh)
    stale: list[str] = []
    if refresh_mode:
        rep("")
        rep("【刷新模式 --refresh】目标已存在：新增缺失文件、覆盖与源不一致的文件；")
        rep("  从不删除——目标多出的文件逐条记 STALE，留待人工处理。")

    # ---------------- 3. 扫描插件包
    rep("")
    rep("-" * 78)
    rep("【2】扫描插件包（将逐字节复制；先列清单再动手）")
    rep("-" * 78)
    files, skipped_dirs, skipped_files = scan_package(src, rep)
    total_bytes = sum(p.stat().st_size for p, _ in files)
    rep(f"待复制文件数：{len(files)} 个；合计 {fmt_size(total_bytes)}")
    rep(f"跳过目录 {len(skipped_dirs)} 个 / 跳过文件 {len(skipped_files)} 个（详见下方与交付清单）")
    for rel, reason, fcount, _ in sorted(skipped_dirs):
        rep(f"    SKIP-DIR  {rel}  <- {reason}（{fcount} 文件）")
    for rel, reason in sorted(skipped_files):
        rep(f"    SKIP-FILE {rel}  <- {reason}")
    sizes = {rel: p.stat().st_size for p, rel in files}
    rep("  将复制的文件（源相对路径 | 字节 -> 目标 <交付目录>\\插件包\\<同相对路径>）：")
    for _abs_path, rel in files:
        rep(f"    {rel}  |  {sizes[rel]:,} B")
    if args.list_only:
        rep("")
        rep("--list-only：未写入任何文件。")
        rep(f"结论：LIST-ONLY  |  将复制 {len(files)} 个文件，{fmt_size(total_bytes)}")
        rep.flush_log()
        return EXIT_OK

    # ---------------- 4. 找安装程序
    rep("")
    rep("-" * 78)
    rep("【3】安装程序文件（先列清单再动手）")
    rep("-" * 78)
    exe_files, exe_notes = find_installer_files(exe_src, rep)
    for note in exe_notes:
        rep("    " + note)
    for abs_path, name in exe_files:
        rep(f"    COPY {abs_path}")
        try:
            size_text = f"({abs_path.stat().st_size:,} B)"
        except OSError:
            size_text = "(大小未知)"
        rep(f"      -> {dst / EXE_DIR_NAME / name}  {size_text}")
    if not exe_files:
        rep("    （未找到任何 exe / 安装说明.txt —— 安装程序部分跳过）")

    # ---------------- 5. 复制插件包
    rep("")
    rep("-" * 78)
    rep("【4】复制插件包" + ("（刷新模式：added/updated/same，从不删除）" if refresh_mode
                        else "（逐文件独占新建；已存在记 CONFLICT 跳过，绝不覆盖）"))
    rep("-" * 78)
    pkg_dst = dst / PKG_DIR_NAME
    copied: list[tuple[Path, str]] = []
    conflicts: list[tuple[str, str]] = []
    errors: list[tuple[str, str]] = []
    pkg_copied = 0
    exe_copied = 0
    n_added = n_updated = n_same = 0
    for abs_path, rel in files:
        target = pkg_dst / rel
        if refresh_mode:
            action, why = copy_file_update(abs_path, target)
            if action == "added":
                copied.append((target, "插件包\\" + rel))
                pkg_copied += 1
                n_added += 1
                rep(f"  ADDED    插件包\\{rel}")
            elif action == "updated":
                copied.append((target, "插件包\\" + rel))
                pkg_copied += 1
                n_updated += 1
                rep(f"  UPDATED  插件包\\{rel}  <- {why}")
            elif action == "same":
                n_same += 1
            else:
                errors.append(("插件包\\" + rel, why))
                rep(f"  ERR      插件包\\{rel}  <- {why}")
        else:
            result = copy_file_exclusive(abs_path, target)
            if result == "ok":
                copied.append((target, "插件包\\" + rel))
                pkg_copied += 1
                rep(f"  COPY     插件包\\{rel}")
            elif result == "conflict":
                conflicts.append(("插件包\\" + rel, "目标同名文件已存在，未覆盖"))
                rep(f"  CONFLICT 插件包\\{rel}  <- 已存在，未覆盖")
            else:
                errors.append(("插件包\\" + rel, result))
                rep(f"  ERR      插件包\\{rel}  <- {result}")

    # ---------------- 6. 复制安装程序
    rep("")
    rep("-" * 78)
    rep("【5】复制安装程序")
    rep("-" * 78)
    exe_dst = dst / EXE_DIR_NAME
    for abs_path, name in exe_files:
        target = exe_dst / name
        if refresh_mode:
            action, why = copy_file_update(abs_path, target)
            if action == "added":
                copied.append((target, EXE_DIR_NAME + "\\" + name))
                exe_copied += 1
                n_added += 1
                rep(f"  ADDED    {EXE_DIR_NAME}\\{name}")
            elif action == "updated":
                copied.append((target, EXE_DIR_NAME + "\\" + name))
                exe_copied += 1
                n_updated += 1
                rep(f"  UPDATED  {EXE_DIR_NAME}\\{name}  <- {why}")
            elif action == "same":
                n_same += 1
            else:
                errors.append((EXE_DIR_NAME + "\\" + name, why))
                rep(f"  ERR      {EXE_DIR_NAME}\\{name}  <- {why}")
        else:
            result = copy_file_exclusive(abs_path, target)
            if result == "ok":
                copied.append((target, EXE_DIR_NAME + "\\" + name))
                exe_copied += 1
                rep(f"  COPY     {EXE_DIR_NAME}\\{name}")
            elif result == "conflict":
                conflicts.append((EXE_DIR_NAME + "\\" + name, "目标同名文件已存在，未覆盖"))
                rep(f"  CONFLICT {EXE_DIR_NAME}\\{name}  <- 已存在，未覆盖")
            else:
                errors.append((EXE_DIR_NAME + "\\" + name, result))
                rep(f"  ERR      {EXE_DIR_NAME}\\{name}  <- {result}")

    # ---------------- 6b. 刷新模式：目标多出的文件记 STALE（不删除）
    if refresh_mode:
        src_rels = {"插件包\\" + rel for _p, rel in files}
        src_rels |= {EXE_DIR_NAME + "\\" + name for _p, name in exe_files}
        for root, dirs, names in os.walk(dst):
            root_path = Path(root)
            dirs[:] = [d for d in sorted(dirs)
                       if not is_reparse_dir(root_path / d)]
            for name in sorted(names):
                p = root_path / name
                rel = str(p.relative_to(dst))
                if rel in (MANIFEST_NAME, START_HERE_NAME, HASH_LIST_NAME):
                    continue
                display = rel
                if display not in src_rels:
                    stale.append(display)
        if stale:
            rep("")
            rep(f"  STALE    {len(stale)} 个目标文件在源里已不存在（**未删除**，留待人工处理）：")
            for rel in stale[:30]:
                rep(f"    - {rel}")
            if len(stale) > 30:
                rep(f"    ...（其余 {len(stale) - 30} 项见 SHA256哈希清单.txt 的 STALE 节）")

    # ---------------- 7. 逐文件校验
    rep("")
    rep("-" * 78)
    rep("【6】逐文件校验（字节数 + SHA256，源 vs 目标）")
    rep("-" * 78)
    src_root = Path(src)
    exe_src_map = {name: abs_path for abs_path, name in exe_files}
    verified = 0
    mismatches: list[tuple[str, str]] = []
    verified_rows: list[tuple[str, int, str]] = []  # (显示路径, 字节, sha256)
    for target, display in copied:
        if display.startswith("插件包\\"):
            source = src_root / display[len("插件包\\"):]
        else:
            source = exe_src_map[display.split("\\", 1)[1]]
        try:
            s_size, s_hash = source.stat().st_size, sha256_of(source)
            d_size, d_hash = target.stat().st_size, sha256_of(target)
        except OSError as exc:
            mismatches.append((display, f"读文件失败 {type(exc).__name__}: {exc}"))
            rep(f"  {display}  <- 读文件失败：{exc}")
            continue
        if s_size == d_size and s_hash == d_hash:
            verified += 1
            verified_rows.append((display, d_size, d_hash))
            rep(f"  OK   {display}  |  {d_size:,} B  |  {d_hash}")
        else:
            why = []
            if s_size != d_size:
                why.append(f"字节数不一致 源={s_size} 目标={d_size}")
            if s_hash != d_hash:
                why.append(f"SHA256不一致 源={s_hash} 目标={d_hash}")
            mismatches.append((display, "；".join(why)))
            rep(f"  FAIL {display}  <- {'；'.join(why)}")

    # ---------------- 8. 生成两个 txt + 哈希清单
    rep("")
    rep("-" * 78)
    rep("【7】生成交付清单.txt / 从这里开始.txt / %s（UTF-8 带 BOM + CRLF；"
        "%s）" % (HASH_LIST_NAME,
                  "刷新模式覆盖本脚本自己的生成物" if refresh_mode else "已存在则跳过不覆盖"))
    rep("-" * 78)
    txt_created: list[tuple[Path, str]] = []

    def _emit_txt(path: Path, lines: list[str], name: str) -> None:
        if refresh_mode:
            write_text_file_refresh(path, lines)
            txt_created.append((path, name))
            rep(f"  REFRESH  {path}  ({path.stat().st_size:,} B)")
            return
        try:
            write_text_file(path, lines)
            txt_created.append((path, name))
            rep(f"  CREATED  {path}  ({path.stat().st_size:,} B)")
        except FileExistsError:
            conflicts.append((name, "目标同名文件已存在，未覆盖"))
            rep(f"  CONFLICT {name}  <- 已存在，未覆盖")
        except OSError as exc:
            errors.append((name, f"{type(exc).__name__}: {exc}"))
            rep(f"  ERR      {name}  <- {exc}")

    start_here_lines = build_start_here(pkg_ver, contract_ver)
    start_path = dst / START_HERE_NAME
    _emit_txt(start_path, start_here_lines, START_HERE_NAME)

    manifest_lines = build_manifest(
        pkg_ver, contract_ver, ver_basis, exe_files, files, skipped_dirs, skipped_files,
        verified_rows, total_bytes, started, refresh_mode,
        {"added": n_added, "updated": n_updated, "same": n_same, "stale": stale},
    )
    manifest_path = dst / MANIFEST_NAME
    _emit_txt(manifest_path, manifest_lines, MANIFEST_NAME)

    # §q-19①：独立哈希清单（文件名含"哈希"）；覆盖**交付目录整棵树**（不含本清单自身）
    hash_lines = build_hash_list(dst, started, refresh_mode,
                                 {"added": n_added, "updated": n_updated,
                                  "same": n_same, "stale": stale})
    hash_path = dst / HASH_LIST_NAME
    _emit_txt(hash_path, hash_lines, HASH_LIST_NAME)

    for path, name in txt_created:
        try:
            rep(f"  校验     {name}  |  {path.stat().st_size:,} B  |  SHA256 {sha256_of(path)}")
        except OSError as exc:
            rep(f"  校验失败 {name}: {exc}")

    # ---------------- 9. 目录树与结论
    print_tree(dst, rep)

    rep("")
    rep("=" * 78)
    rep("【8】结论")
    rep("=" * 78)
    rep(f"插件包        : 复制 {pkg_copied} 个文件"
        f"（跳过目录 {len(skipped_dirs)}、跳过文件 {len(skipped_files)}）"
        + (f"；added={n_added} updated={n_updated} same={n_same}" if refresh_mode else ""))
    rep(f"安装程序      : 复制 {exe_copied} 个文件"
        + ("" if exe_files else "（未找到 exe/安装说明.txt，跳过）"))
    rep(f"生成的说明    : 交付清单.txt、从这里开始.txt、{HASH_LIST_NAME}")
    rep(f"校验通过      : {verified} / {len(copied)}")
    rep(f"冲突未覆盖    : {len(conflicts)} 个；复制错误 {len(errors)} 个")
    for rel, why in conflicts + errors:
        rep(f"    ! {rel}  <- {why}")
    rep(f"校验不一致    : {len(mismatches)} 个")
    for rel, why in mismatches:
        rep(f"    ! {rel}  <- {why}")
    rep("删除动作      : 无（脚本不含任何删除/移动/改名调用；未写 G 盘任何路径）")
    if conflicts or errors or mismatches:
        verdict, code = "PROBLEM（有冲突/错误/校验不一致，未覆盖任何既有文件）", EXIT_PROBLEM
    else:
        verdict, code = "PASS（全部文件大小与 SHA256 一致）", EXIT_OK
    rep(f"校验结论      : {verdict}")
    rep(f"退出码        : {code}")
    if rep.log_path is not None:
        rep(f"日志          : {rep.log_path}")
    rep(f"结束时间      : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    rep("=" * 78)
    rep.flush_log()
    if rep.log_error:
        print(f"[提示] 日志写入失败（不影响归集结果）：{rep.log_error}")
    return code


# --------------------------------------------------------------------------- 三个 txt 的正文
def build_hash_list(dst: Path, started: str, refresh_mode: bool,
                    counters: dict) -> list[str]:
    """§q-19① 的哈希清单：交付目录整棵树（不含本清单自身）的逐文件 SHA256。"""
    rows: list[tuple[str, int, str]] = []
    for root, dirs, names in os.walk(dst):
        root_path = Path(root)
        dirs[:] = [d for d in sorted(dirs) if not is_reparse_dir(root_path / d)]
        for name in sorted(names):
            p = root_path / name
            rel = str(p.relative_to(dst)).replace("\\", "/")
            if rel == HASH_LIST_NAME:
                continue
            try:
                rows.append((sha256_of(p), p.stat().st_size, rel))
            except OSError as exc:
                rows.append(("<不可读 %s>" % exc, 0, rel))
    rows.sort(key=lambda r: r[2])
    lines: list[str] = []
    lines.append("=" * 74)
    lines.append(" SHA256 哈希清单 —— PKPM2PDMS 导入导出（交付目录整棵树，§q-19①）")
    lines.append("=" * 74)
    lines.append(f"生成时间   : {started}（由 插件包\\deliver\\collect_to_workspace.py 自动生成"
                 f"{'，刷新模式' if refresh_mode else ''}）")
    lines.append(f"文件数     : {len(rows)}（不含本清单自身）")
    if refresh_mode:
        lines.append("本次刷新   : added=%(added)d updated=%(updated)d same=%(same)d "
                     "stale=%(stale)d（STALE 文件**未删除**，见交付清单.txt 的 STALE 节）"
                     % {"added": counters["added"], "updated": counters["updated"],
                        "same": counters["same"], "stale": len(counters["stale"])})
    lines.append("校验方法   : CertUtil -hashfile <文件> SHA256 或 python hashlib；")
    lines.append("             本清单自带的哈希在生成时逐文件计算（SHA256，十六进制小写）。")
    lines.append("")
    for digest, size, rel in rows:
        lines.append(f"{digest}  {size:>12,}  {rel}")
    lines.append("")
    lines.append("=" * 74)
    lines.append(f" 哈希清单完（{started} 生成）")
    lines.append("=" * 74)
    return lines


def build_start_here(pkg_ver: str, contract_ver: str) -> list[str]:
    return [
        "================================================================",
        f" 从这里开始 —— PKPM-JWD导入导出 {pkg_ver}（契约 v{contract_ver} + R3）",
        "================================================================",
        "",
        "0. 未部署声明（契约 §p.10-5）：**本包未部署，需要用户自己在 PDMS 停机时按",
        "   docs/使用说明.md 安装。** 本工作流没有在真实 D:\\AVEVA 上执行过任何安装。",
        "",
        "1. 先读什么：插件包\\docs\\使用说明.md —— 安装/导入/导出/参数/界面/卸载/已知限制全在里面。",
        "",
        "2. 在哪装（R3 路线，先预览再执行；需要 Python 3.12）：",
        '   python pdms-net\\deploy\\deploy_pkpm2pdms.py                （缺省 dry-run：只打印清单）',
        '   python pdms-net\\deploy\\deploy_pkpm2pdms.py --execute      （真做：备份+复制+注册，幂等）',
        '   python pdms-net\\deploy\\undeploy_pkpm2pdms.py --execute    （卸载/回滚，恢复 .pkpm2pdms-bak）',
        "   装完【完全退出并重启 PDMS】，进 DESIGN 模块，菜单栏出现「PKPM2PDMS」即成。",
        "   安装程序\\ 里的两个 v1 exe 是旧方案（v1 遗留，§p.8；只装 PML 菜单，不含 R3 的 .NET 插件），",
        "   要装 R3 的 .NET 插件请走上面的 deploy 脚本。",
        "",
        "3. 装完怎么用（转换）：双击 安装程序\\PKPM2PDMS_引擎_v2.1.0.exe 出转换界面，或",
        "   engine\\dist\\pkpm2pdms_engine.exe（独立引擎，功能与源码版一致）；不用 exe 也可以：",
        "   python engine\\cli.py --help（12 个子命令）；python engine\\gui.py（图形界面）。",
        "",
        "4. 怎么卸载：python pdms-net\\deploy\\undeploy_pkpm2pdms.py --execute（恢复 .pkpm2pdms-bak，",
        "   4 个安装文件移入 _uninstalled_<时刻>\\，不删除）；或 v1 方式（同上）。",
        "",
        "5. 版本注意：宏/PML/.NET 插件均未在 PDMS 实机验证（acceptance_r3.py 各检查的",
        "   『待实机确认』条目），首次上机先用小工程试跑（详见 插件包\\docs\\使用说明.md §10）。",
        "",
        "逐文件清单与 SHA256：交付清单.txt（带说明）与 SHA256哈希清单.txt（纯哈希，交付目录整棵树）。",
    ]


def build_manifest(
    pkg_ver: str,
    contract_ver: str,
    ver_basis: str,
    exe_files: list[tuple[Path, str]],
    pkg_files: list[tuple[Path, str]],
    skipped_dirs: list[tuple[str, str, int, int]],
    skipped_files: list[tuple[str, str]],
    verified_rows: list[tuple[str, int, str]],
    pkg_total_bytes: int,
    started: str,
    refresh_mode: bool = False,
    counters: dict | None = None,
) -> list[str]:
    counters = counters or {"added": 0, "updated": 0, "same": 0, "stale": []}
    lines: list[str] = []
    lines.append("=" * 74)
    lines.append(" 交付清单 —— PKPM2PDMS 导入导出（工作区归集版）")
    lines.append("=" * 74)
    lines.append(f"生成时间   : {started}（由 插件包\\deliver\\collect_to_workspace.py 自动生成"
                 f"{'，--refresh 刷新' if refresh_mode else ''}）")
    lines.append(f"插件包版本 : {pkg_ver}（契约 CONTRACT_VERSION = v{contract_ver} + R3 修订 §0.4-11）")
    lines.append(f"版本依据   : {ver_basis}")
    if refresh_mode:
        lines.append("本次刷新   : added=%(added)d updated=%(updated)d same=%(same)d；"
                     "STALE（目标多出、**未删除**）= %(stale)d 个"
                     % {"added": counters["added"], "updated": counters["updated"],
                        "same": counters["same"], "stale": len(counters["stale"])})
    lines.append("")
    lines.append("**未部署声明（契约 §p.10-5）**：**本包未部署，需要用户自己在 PDMS 停机时按")
    lines.append(" docs/使用说明.md 安装。** 本工作流没有执行过任何部署脚本；D:\\AVEVA 注册三件套")
    lines.append(" 与 G 盘插件目录在验收前后零变化（acceptance_r3.py 检查 19 的 C14 基线核对）。")
    if exe_files:
        exe_names = "、".join(name for _p, name in exe_files if name.lower().endswith(".exe"))
        lines.append(f"安装程序   : {exe_names}（**v1 遗留**，§p.8：只装 PML 菜单，不含 R3 的 .NET")
        lines.append("             插件；说明见 安装程序\\安装说明.txt。R3 安装路线 = 插件包\\pdms-net\\deploy\\）")
    else:
        lines.append("安装程序   : 未找到 exe / 安装说明.txt（『若存在』条件不成立，本次未包含）")
    lines.append("编码       : 复制件为原样字节复制（.mac/.pmlfrm/.pmlfnc 保持 GBK 无 BOM + CRLF，")
    lines.append("             Python/文档保持 UTF-8）；本清单、从这里开始.txt 与 SHA256哈希清单.txt")
    lines.append("             为 UTF-8 带 BOM + CRLF（本脚本生成）。")
    lines.append("")
    lines.append("-" * 74)
    lines.append("一、这里有什么")
    lines.append("-" * 74)
    lines.append("  插件包\\          源码完整包（跳过临时/缓存/自测目录后逐字节复制，逐文件 SHA256")
    lines.append("                   见 SHA256哈希清单.txt）")
    lines.append("    engine\\        Python 转换引擎（只用标准库）：cli.py 共 12 个子命令（jwd2pdms/pdt2pdms/")
    lines.append("                   pdms2jwd/pdms2pdt/jwd2db/pdt2db/db2jwd/db2pdt/jwd2pdt/pdt2jwd/dbsections/")
    lines.append("                   pdt2model）+ gui.py 五页签界面 + 读/写/宏/数据库模块 +")
    lines.append("                   section_table.csv 截面字典（约 4.8 MB）")
    lines.append("    engine\\dist\\   〔R3〕独立引擎：pkpmjwd_engine.exe（PyInstaller --onefile）+")
    lines.append("                   run_engine.cmd 回退包装器")
    lines.append("    pdms\\          PDMS 侧 PML（GBK 无 BOM + CRLF）：pkpmjwd.pmlfrm 操作窗体、")
    lines.append("                   pkpmjwdexport.pmlfnc 模型导出、pkpmjwddbexport.pmlfnc 目录/规格导出、")
    lines.append("                   pkpmjwdrun.mac 命令行入口宏、")
    lines.append("                   pkpmjwduniquename.pmlfnc 〔R3〕重名唯一化函数（§o.2）")
    lines.append("    pdms-net\\      〔R3〕.NET 插件（x86 / CLR v2.0.50727）：PKPMJWDAddin.cs /")
    lines.append("                   PKPMJWDForm.cs / PmlBridge.cs / EngineRunner.cs / PKLog.cs /")
    lines.append("                   build.cmd（编译命令，已实测退出码 0）/ pkpmjwd.uic /")
    lines.append("                   dist\\PKPMJWD.dll + pkpmjwd.uic / deploy\\（deploy_pkpmjwd.py 安装、")
    lines.append("                   undeploy_pkpmjwd.py 卸载；缺省 dry-run，本轮只交付未执行）")
    lines.append("    install\\       install.ps1 / uninstall.ps1（v1 遗留方案，§p.8：文件保留不删）")
    lines.append("    docs\\          使用说明.md（先读这篇）+ 格式规范_JWD/PDT + 数据库转化说明 + 转化表说明 +")
    lines.append("                   截面映射说明 + 交付清单/交付报告 等文档")
    lines.append("    spec\\          CONTRACT.md —— 唯一接口契约")
    lines.append("    test\\          测试与证据（acceptance.py / acceptance_r2.py / acceptance_r3.py 及")
    lines.append("                   各检查脚本、产物、日志）")
    lines.append("    deliver\\       交付脚本（copy_to_plugin.py、collect_to_workspace.py 等）")
    lines.append("    计划\\          实施计划书")
    lines.append("  安装程序\\        〔v1 遗留〕两个免安装 exe + 安装说明.txt（不需要 Python 环境；不含 R3 功能）：")
    lines.append("    PKPM-JWD_安装程序_v1.exe   把 PML 装进 PDMS / 卸载（先「仅预览」再「安装」）")
    lines.append("    PKPM-JWD_引擎_v1.exe       转换引擎：双击=图形界面，--cli=命令行")
    lines.append("    安装说明.txt               exe 版用法原文")
    lines.append("  交付清单.txt     本文件")
    lines.append("  从这里开始.txt   快速上手（R3 安装路线 + 未部署声明）")
    lines.append("  " + HASH_LIST_NAME + "  交付目录整棵树的逐文件 SHA256（§q-19①）")
    lines.append("")
    lines.append("-" * 74)
    lines.append("二、怎么用（摘要；详细以 插件包\\docs\\使用说明.md 为准）")
    lines.append("-" * 74)
    lines.append("  【A. R3 路线（.NET 插件 + 部署脚本；需要 Python 3.12 跑脚本本身）】")
    lines.append("    预览：python 插件包\\pdms-net\\deploy\\deploy_pkpmjwd.py             （缺省 dry-run）")
    lines.append("    安装：python 插件包\\pdms-net\\deploy\\deploy_pkpmjwd.py --execute   （先备份再复制/注册，幂等）")
    lines.append("    卸载：python 插件包\\pdms-net\\deploy\\undeploy_pkpmjwd.py --execute （恢复 .pkpmjwd-bak）")
    lines.append("    装完【完全退出并重启 PDMS】进 DESIGN 模块，菜单栏「PKPM-JWD」打开窗体。")
    lines.append("  【B. 转换引擎（三选一）】")
    lines.append("    engine\\dist\\pkpmjwd_engine.exe            〔R3〕独立 exe，无需 Python")
    lines.append("    python engine\\cli.py --help               源码版 12 个子命令")
    lines.append("    python engine\\gui.py                      源码版五页签图形界面")
    lines.append("    例：python engine\\cli.py jwd2pdms \"<x.jwd>\" --out \"<x.mac>\" --secmap \"<PKPM转PDMS截面匹配文件.txt>\"")
    lines.append("  注：截面匹配文件用你自己的《PKPM转PDMS截面匹配文件.txt》（按交付纪律不随包分发，")
    lines.append("      不在本交付包里）。")
    lines.append("")
    lines.append("-" * 74)
    lines.append("三、版本与注意事项")
    lines.append("-" * 74)
    lines.append(f"  1. 插件包版本 {pkg_ver}（契约 {contract_ver} + R3 修订 §0.4-11）：在 R2（数据库转化、")
    lines.append("     格式互转、荷载不做）之上新增：.NET 插件 PKPMJWD.dll（x86/CLR2，真编译通过）、")
    lines.append("     deploy/undeploy 注册脚本（沙箱验证幂等可回滚）、重名唯一化函数、独立引擎 exe。")
    lines.append("  2. **未部署**：全部只在文件级与沙箱级验证过（acceptance_r3.py 检查 15-20；真实")
    lines.append("     D:\\AVEVA 与 G 盘零变化）。实机步骤与风险清单见 docs/使用说明.md §10。")
    lines.append("  3. 板/墙 3 条占位规格（T120/T100/T600）请按自己的等级库核对替换（使用说明 §10.4）。")
    lines.append("")
    lines.append("-" * 74)
    lines.append("四、逐文件清单（复制后逐一比对：字节数 + SHA256，全部一致才汇总为 PASS；")
    lines.append("    纯哈希版见 " + HASH_LIST_NAME + "）")
    lines.append("-" * 74)
    lines.append(f"  插件包：{len(pkg_files)} 个文件 / {fmt_size(pkg_total_bytes)}")
    lines.append("  跳过未复制（仍保留在工作区，未删除）：")
    for rel, reason, fcount, _ in sorted(skipped_dirs):
        lines.append(f"    [目录] {rel}  <- {reason}（{fcount} 文件）")
    for rel, reason in sorted(skipped_files):
        lines.append(f"    [文件] {rel}  <- {reason}")
    lines.append("")
    lines.append("  逐文件（相对路径 | 字节 | SHA256）：")
    for display, size, digest in verified_rows:
        if display.startswith("插件包\\"):
            lines.append(f"    {display}  |  {size:,} B  |  {digest}")
    exe_rows = [r for r in verified_rows if r[0].startswith(EXE_DIR_NAME + "\\")]
    if exe_rows:
        lines.append("")
        lines.append("  安装程序与说明文件（同上逐文件校验）：")
        for display, size, digest in exe_rows:
            lines.append(f"    {display}  |  {size:,} B  |  {digest}")
    if refresh_mode and counters["stale"]:
        lines.append("")
        lines.append("  STALE（交付目录里多出、源里已没有的文件——**未删除**，留待人工处理）：")
        for rel in counters["stale"]:
            lines.append(f"    [STALE] {rel}")
    lines.append("")
    lines.append("  根目录说明文件（本脚本生成，非复制）：")
    lines.append(f"    {START_HERE_NAME}  |  （见文件本身）")
    lines.append(f"    {MANIFEST_NAME}    |  （本文件）")
    lines.append(f"    {HASH_LIST_NAME}  |  （纯哈希清单）")
    lines.append("")
    lines.append("=" * 74)
    lines.append(f" 清单完（{started} 生成）")
    lines.append("=" * 74)
    return lines


if __name__ == "__main__":
    setup_console()
    sys.exit(main())
