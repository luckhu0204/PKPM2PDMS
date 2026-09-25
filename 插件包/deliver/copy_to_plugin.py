#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""copy_to_plugin.py —— 把工作区成品包复制到 PDMS 插件目录（只新增，绝不删除/覆盖）

用途
----
把工作区的 ``PKPM-JWD导入导出\\`` 整包复制到插件目录下的同名单层子文件夹::

    D:\\AI_Work\\PKPM数据解析\\PKPM-JWD导入导出\\
        ->  G:\\工作\\PDMS相关\\00 PDMS插件\\02 实用插件\\PKPM导入导出插件\\PKPM-JWD导入导出\\

硬性纪律（本脚本的设计约束，代码里逐条对应）
--------------------------------------------
1. **不删除任何东西**：脚本内没有任何删除/移动/改名调用（无 ``os.remove`` / ``os.rmdir`` /
   ``shutil.rmtree`` / ``move``）。目标侧只做「创建目录」和「独占新建文件」。
2. **已存在且非空的目标目录 = 拒绝执行**：打印现状后用退出码 **2** 结束，交人来判断，
   不强行覆盖。目标不存在（或存在但为空）才继续。
3. **绝不覆盖既有文件**：每个目标文件用 ``open(..., "xb")`` 独占创建；一旦同名文件已存在，
   记 CONFLICT 并**跳过该文件**，绝不覆盖，最后以退出码 3 报告。
4. **逐文件校验**：复制完成后对每个文件比对源/目标的**字节数**与 **SHA256**，输出清单与结论。
5. **跳过缓存与临时目录**（详见 ``--help`` 与输出里的 SKIP 段）：
   ``__pycache__``、``tmp``/``temp``/``_tmp``/``_temp``/``*_tmp``/``*_temp``/``*_cache``，
   以及 ``_备份_待删_*``（工作区的"待删备份暂存区"，不属于交付物）。
   用 ``--include-temp`` / ``--include-backup`` 可放开。
6. **控制台不乱码**：优先按**当前控制台代码页**（``GetConsoleOutputCP``，本机 cmd 默认 936/GBK）
   输出——终端直看、管道重定向、被别的脚本捕获，都不会乱码；没有控制台时才退回 UTF-8。
   同时把完整记录以 **UTF-8（新建时带 BOM）** 写到 ``deliver\\_copy_to_plugin_log.txt``，
   记事本直接可读；重复运行是**追加**，不覆盖、不删除旧日志。

只用标准库。

退出码
------
===  ============================================================
 0   复制完成，且逐文件大小/SHA256 全部一致
 1   致命错误（源目录不存在、目标不可写、磁盘满等）
 2   目标目录已存在且非空 —— 拒绝执行（未做任何改动）
 3   复制完成但有冲突/校验不一致（逐条已打印，未覆盖任何文件）
===  ============================================================
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import os
import sys
import time
from pathlib import Path

# --------------------------------------------------------------------------- 默认路径
SRC_DEFAULT = r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出"
DST_DEFAULT = (
    r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\PKPM-JWD导入导出"
)

# --------------------------------------------------------------------------- 退出码
EXIT_OK = 0
EXIT_FATAL = 1
EXIT_REFUSED = 2
EXIT_PROBLEM = 3

# --------------------------------------------------------------------------- 跳过规则
# 目录名精确匹配（小写比较）
TEMP_DIR_NAMES = {"__pycache__", "tmp", "temp", "_tmp", "_temp", ".tmp", ".temp"}
# 目录名后缀匹配
TEMP_DIR_SUFFIXES = ("_tmp", "_temp", "_cache", "__pycache__")
# 目录名前缀匹配：工作区"待删备份暂存区"，不是交付物
BACKUP_DIR_PREFIXES = ("_备份_待删_",)
# 本脚本自己的日志（避免二次运行时把日志当交付物复制进去）
SELF_LOG_PREFIX = "_copy_to_plugin_log"

HASH_CHUNK = 1024 * 1024


# --------------------------------------------------------------------------- 输出
class Reporter:
    """同时打印到控制台（按控制台代码页/UTF-8）并写一份 UTF-8 日志。"""

    def __init__(self, log_path: Path | None) -> None:
        self.lines: list[str] = []
        self.log_path = log_path
        self.log_error: str | None = None

    def __call__(self, text: str = "") -> None:
        self.lines.append(text)
        try:
            print(text)
        except UnicodeEncodeError:  # 极端情况下再兜一层
            enc = getattr(sys.stdout, "encoding", None) or "ascii"
            print(text.encode(enc, "replace").decode(enc, "replace"))

    def blank(self) -> None:
        self("")

    def flush_log(self) -> None:
        if self.log_path is None:
            return
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            # 独占创建（"x"）：日志文件默认不存在；已存在（上次运行的日志）则追加，绝不删旧文件。
            # BOM 只在新建时写一次：utf-8-sig 在追加模式下不会重复写 BOM，这里手工保证一致性。
            mode = "a" if self.log_path.exists() else "x"
            with open(self.log_path, mode, encoding="utf-8", newline="\r\n") as fh:
                if mode == "x":
                    fh.write("\ufeff")
                fh.write("\r\n".join(self.lines) + "\r\n")
        except Exception as exc:  # 日志写不了不影响主流程
            self.log_error = f"{type(exc).__name__}: {exc}"


def console_encoding() -> str:
    """本机控制台的输出代码页（cmd 默认 936/GBK）；拿不到就退回 UTF-8。

    刻意**不看** ``isatty()``：被管道/别的程序捕获时，读走这批字节的通常还是同一个
    控制台环境（cmd.exe），所以照样按控制台代码页写才不乱码。"""
    if os.name == "nt":
        try:
            code_page = int(ctypes.windll.kernel32.GetConsoleOutputCP())  # type: ignore[attr-defined]
        except Exception:
            code_page = 0
        if code_page:
            try:
                "测试".encode("cp%d" % code_page)
                return "cp%d" % code_page
            except (LookupError, UnicodeEncodeError):
                return "utf-8"
    return "utf-8"


def setup_console() -> None:
    """避免控制台乱码：按当前控制台代码页输出。"""
    enc = console_encoding()
    for stream in (sys.stdout, sys.stderr):
        if not hasattr(stream, "reconfigure"):
            continue
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


def dir_skip_reason(name: str, include_temp: bool, include_backup: bool) -> str | None:
    low = name.lower()
    if not include_temp:
        if low in TEMP_DIR_NAMES:
            return "缓存/临时目录"
        if low.endswith(TEMP_DIR_SUFFIXES):
            return "缓存/临时目录"
    if not include_backup:
        if name.startswith(BACKUP_DIR_PREFIXES):
            return "待删备份暂存区（非交付物）"
    return None


def file_skip_reason(name: str) -> str | None:
    low = name.lower()
    if low.endswith(".pyc") or low.endswith(".pyo"):
        return "Python 字节码"
    if low.startswith(SELF_LOG_PREFIX):
        return "本脚本自己的运行日志"
    return None


def describe_dir(path: Path, max_items: int = 25) -> tuple[int, int, bool]:
    """返回 (子项数, 文件数, 是否还有更深层内容) —— 只读，用于"现状说明"。

    ``max_items`` 只限制**打印**，计数始终是完整递归。"""
    items: list[str] = []
    child_count = 0
    file_count = 0
    truncated = False
    for root, dirs, files in os.walk(path, onerror=lambda _e: None):
        dirs.sort()
        files.sort()
        for d in dirs:
            child_count += 1
            if len(items) < max_items:
                items.append(f"[DIR ] {os.path.join(root, d)}")
        for f in files:
            child_count += 1
            file_count += 1
            if len(items) < max_items:
                items.append(f"[FILE] {os.path.join(root, f)}")
        if child_count >= max_items:
            truncated = True
    return child_count, file_count, truncated


def fmt_size(n: int) -> str:
    kb = n / 1024.0
    if kb < 1024:
        return f"{n:,} B ({kb:,.1f} KiB)"
    return f"{n:,} B ({kb / 1024.0:,.2f} MiB)"


# --------------------------------------------------------------------------- 主流程
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="把工作区成品包复制到 PDMS 插件目录（只新增，不覆盖，不删除）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="退出码：0=成功且校验通过；1=致命错误；2=目标已存在且非空（拒绝执行）；3=有冲突/校验不一致",
    )
    parser.add_argument("--src", default=SRC_DEFAULT, help="源目录（默认：%s）" % SRC_DEFAULT)
    parser.add_argument("--dst", default=DST_DEFAULT, help="目标目录（默认：%s）" % DST_DEFAULT)
    parser.add_argument(
        "--include-temp",
        action="store_true",
        help="连缓存/临时目录（__pycache__、*_tmp 等）一起复制",
    )
    parser.add_argument(
        "--include-backup",
        action="store_true",
        help="连 _备份_待删_* 暂存区一起复制",
    )
    parser.add_argument(
        "--log",
        default=None,
        help="日志文件路径（默认：<源目录>\\deliver\\_copy_to_plugin_log.txt；传 - 表示不写日志）",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="只列出将要复制的文件与校验和，不写任何东西",
    )
    args = parser.parse_args(argv)

    src = Path(args.src).expanduser()
    dst = Path(args.dst).expanduser()

    if args.log == "-":
        log_path: Path | None = None
    elif args.log:
        log_path = Path(args.log).expanduser()
    else:
        log_path = src / "deliver" / f"{SELF_LOG_PREFIX}.txt"

    rep = Reporter(log_path)
    started = time.strftime("%Y-%m-%d %H:%M:%S")

    rep("=" * 78)
    rep("copy_to_plugin.py —— 工作区成品包 -> PDMS 插件目录（只新增 / 不覆盖 / 不删除）")
    rep("=" * 78)
    rep(f"开始时间   : {started}")
    rep(f"源目录     : {src}")
    rep(f"目标目录   : {dst}")
    rep(f"本次参数   : include_temp={args.include_temp} include_backup={args.include_backup} "
        f"list_only={args.list_only}")
    rep("纪律       : 目标目录已存在且非空 -> 打印现状并退出码 2；任何既有文件都不覆盖；无删除动作")
    rep("")

    # ------------------------------------------------------------------ 1. 源目录
    if not src.is_dir():
        rep(f"[致命] 源目录不存在或不是目录：{src}")
        rep.flush_log()
        return EXIT_FATAL

    # ------------------------------------------------------------------ 2. 目标现状
    dst_exists = dst.exists()
    dst_nonempty = False
    dst_child_count = dst_file_count = 0
    dst_items: list[str] = []

    rep("-" * 78)
    rep("【1】目标现状")
    rep("-" * 78)
    if dst_exists and not dst.is_dir():
        rep(f"[致命] 目标路径存在但不是目录：{dst}")
        rep.flush_log()
        return EXIT_FATAL
    if not dst_exists:
        rep(f"目标目录不存在：{dst}")
        rep("  -> 将逐文件创建（含目录层级），不覆盖任何东西。")
    else:
        dst_child_count, dst_file_count, truncated = describe_dir(dst)
        dst_nonempty = dst_child_count > 0
        # 重新取前若干项用于"现状说明"（describe_dir 只为计数，这里再取一次展示用）
        shown = 0
        for root, dirs, files in os.walk(dst):
            dirs.sort()
            files.sort()
            for d in dirs:
                if shown < 25:
                    dst_items.append(f"[DIR ] {os.path.join(root, d)}")
                    shown += 1
            for f in files:
                if shown < 25:
                    dst_items.append(f"[FILE] {os.path.join(root, f)}")
                    shown += 1
            if shown >= 25:
                break
        rep(f"目标目录已存在：{dst}")
        rep(f"  子项（递归，含目录与文件）：{dst_child_count} 项；其中文件 {dst_file_count} 个")
        for line in dst_items:
            rep("    " + line)
        if dst_child_count > shown:
            rep(f"    ...（共 {dst_child_count} 项，此处仅列前 {shown} 项）")

    if dst_nonempty:
        rep("")
        rep("【拒绝执行】目标目录已存在且非空 —— 不覆盖、不动它，交人来判断。")
        rep("  三个可选做法（本脚本一个都不替你做）：")
        rep("    1) 自己看过上面清单后，把该目录改名/移走，再重跑本脚本；")
        rep("    2) 换一个 --dst 指向新的空目录；")
        rep("    3) 用 --list-only 只查看将要复制的文件与校验和。")
        rep("  本次未创建、未修改、未删除任何文件。")
        rep("")
        rep(f"结论：REFUSED（目标已存在且非空）  |  退出码 {EXIT_REFUSED}")
        rep.flush_log()
        return EXIT_REFUSED

    # ------------------------------------------------------------------ 3. 扫描源目录
    rep("")
    rep("-" * 78)
    rep("【2】扫描源目录（跳过缓存/临时目录）")
    rep("-" * 78)

    files: list[tuple[Path, str]] = []  # (绝对源文件, 相对路径)
    skipped_dirs: list[tuple[str, str, int, int]] = []  # (相对目录, 原因, 文件数, 子项数)
    skipped_files: list[tuple[str, str]] = []

    for root, dirs, names in os.walk(src):
        root_path = Path(root)
        dirs.sort()
        names.sort()

        # 剪枝：把要跳过的子目录从递归里摘掉（只影响遍历，不做任何删除）
        keep: list[str] = []
        for d in dirs:
            reason = dir_skip_reason(d, args.include_temp, args.include_backup)
            if reason is None:
                keep.append(d)
                continue
            sub = root_path / d
            child_count, file_count, _ = describe_dir(sub)
            rel = str(sub.relative_to(src))
            skipped_dirs.append((rel, reason, file_count, child_count))
        dirs[:] = keep

        for name in names:
            reason = file_skip_reason(name)
            if reason is not None:
                skipped_files.append((str((root_path / name).relative_to(src)), reason))
                continue
            abs_path = root_path / name
            if abs_path.is_symlink():
                skipped_files.append(
                    (str(abs_path.relative_to(src)), "符号链接（不跟随）")
                )
                continue
            files.append((abs_path, str(abs_path.relative_to(src))))

    files.sort(key=lambda item: item[1].replace("\\", "/").lower())
    total_bytes = sum(p.stat().st_size for p, _ in files)

    rep(f"待复制文件数：{len(files)} 个；合计 {fmt_size(total_bytes)}")
    rep(f"源目录中其他内容：跳过目录 {len(skipped_dirs)} 个，跳过文件 {len(skipped_files)} 个")
    if skipped_dirs:
        rep("  跳过的目录：")
        for rel, reason, fcount, ccount in sorted(skipped_dirs):
            rep(f"    SKIP-DIR  {rel}  <- {reason}（{fcount} 文件 / {ccount} 子项）")
    if skipped_files:
        rep("  跳过的文件：")
        for rel, reason in sorted(skipped_files):
            rep(f"    SKIP-FILE {rel}  <- {reason}")

    # ------------------------------------------------------------------ 4. 计算源哈希
    rep("")
    rep("-" * 78)
    rep("【3】源文件清单与 SHA256")
    rep("-" * 78)
    src_info: dict[str, tuple[int, str]] = {}
    for abs_path, rel in files:
        try:
            size = abs_path.stat().st_size
            digest = sha256_of(abs_path)
        except OSError as exc:
            rep(f"[致命] 读源文件失败：{rel} -> {type(exc).__name__}: {exc}")
            rep.flush_log()
            return EXIT_FATAL
        src_info[rel] = (size, digest)
        rep(f"  SRC  {rel}  |  {size:,} B  |  {digest}")

    if args.list_only:
        rep("")
        rep("--list-only：未写入任何文件。")
        rep(f"结论：LIST-ONLY  |  将复制 {len(files)} 个文件，{fmt_size(total_bytes)}")
        rep.flush_log()
        return EXIT_OK

    # ------------------------------------------------------------------ 5. 复制
    rep("")
    rep("-" * 78)
    rep("【4】复制（逐文件独占新建；已存在则记 CONFLICT 并跳过，绝不覆盖）")
    rep("-" * 78)

    created_dirs: list[str] = []
    copied: list[str] = []
    conflicts: list[tuple[str, str]] = []
    errors: list[tuple[str, str]] = []

    planned_dirs = set()
    for _abs_path, rel in files:
        parent = str(Path(rel).parent)
        if parent not in (".", ""):
            planned_dirs.add(parent)
    for rel_dir in sorted(planned_dirs):
        target_dir = dst / rel_dir
        existed = target_dir.exists()
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            rep(f"[致命] 创建目录失败：{target_dir} -> {type(exc).__name__}: {exc}")
            rep.flush_log()
            return EXIT_FATAL
        if not existed:
            created_dirs.append(rel_dir)

    for abs_path, rel in files:
        target = dst / rel
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            errors.append((rel, f"建目录失败 {type(exc).__name__}: {exc}"))
            rep(f"  ERR      {rel}  <- 建目录失败：{exc}")
            continue

        try:
            # 独占创建：目标已存在 -> FileExistsError，绝不覆盖
            with open(abs_path, "rb") as fsrc, open(target, "xb") as fdst:
                while True:
                    chunk = fsrc.read(HASH_CHUNK)
                    if not chunk:
                        break
                    fdst.write(chunk)
            try:  # 保留时间戳（便于事后审计），失败不影响正确性
                st = abs_path.stat()
                os.utime(target, (st.st_atime, st.st_mtime))
            except OSError:
                pass
            copied.append(rel)
            rep(f"  COPY     {rel}")
        except FileExistsError:
            conflicts.append((rel, "目标同名文件已存在，未覆盖"))
            rep(f"  CONFLICT {rel}  <- 目标同名文件已存在，未覆盖（保持原样）")
        except OSError as exc:
            errors.append((rel, f"{type(exc).__name__}: {exc}"))
            rep(f"  ERR      {rel}  <- {type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------ 6. 校验
    rep("")
    rep("-" * 78)
    rep("【5】逐文件校验（字节数 + SHA256）")
    rep("-" * 78)
    rep(f"  {'相对路径':<58} {'源字节':>10} {'目标字节':>10}  SHA256匹配")

    verified = 0
    mismatches: list[tuple[str, str]] = []
    missing: list[str] = []

    for rel in copied:
        src_size, src_hash = src_info[rel]
        target = dst / rel
        try:
            dst_size = target.stat().st_size
            dst_hash = sha256_of(target)
        except OSError as exc:
            missing.append(rel)
            mismatches.append((rel, f"读目标失败 {type(exc).__name__}: {exc}"))
            rep(f"  {rel:<58} {src_size:>10,} {'-':>10}  读目标失败：{exc}")
            continue
        size_ok = dst_size == src_size
        hash_ok = dst_hash == src_hash
        if size_ok and hash_ok:
            verified += 1
            rep(f"  {rel:<58} {src_size:>10,} {dst_size:>10,}  OK")
        else:
            why = []
            if not size_ok:
                why.append(f"字节数不一致 源={src_size} 目标={dst_size}")
            if not hash_ok:
                why.append(f"SHA256 不一致 源={src_hash} 目标={dst_hash}")
            mismatches.append((rel, "；".join(why)))
            rep(f"  {rel:<58} {src_size:>10,} {dst_size:>10,}  FAIL（{'；'.join(why)}）")

    for rel, why in conflicts:
        mismatches.append((rel, "冲突未复制：" + why))
    for rel, why in errors:
        mismatches.append((rel, "错误：" + why))

    # ------------------------------------------------------------------ 7. 结论
    rep("")
    rep("=" * 78)
    rep("【6】结论")
    rep("=" * 78)
    rep(f"复制到        : {dst}")
    rep(f"新建目录      : {len(created_dirs)} 个" + (f" -> {', '.join(created_dirs[:10])}"
                                                    + (" ..." if len(created_dirs) > 10 else "")
                                                    if created_dirs else ""))
    rep(f"计划复制      : {len(files)} 个文件 / {fmt_size(total_bytes)}")
    rep(f"实际复制      : {len(copied)} 个文件")
    rep(f"跳过目录      : {len(skipped_dirs)} 个（缓存/临时/暂存，未复制）")
    rep(f"跳过文件      : {len(skipped_files)} 个")
    rep(f"冲突未覆盖    : {len(conflicts)} 个")
    rep(f"复制错误      : {len(errors)} 个")
    rep(f"校验通过      : {verified} / {len(copied)}")
    rep(f"校验不一致    : {len(mismatches)} 个")
    if mismatches:
        rep("  逐条：")
        for rel, why in mismatches:
            rep(f"    ! {rel}  <- {why}")
    rep("删除动作      : 无（脚本不含任何删除/移动/改名调用）")

    if conflicts or errors or mismatches:
        verdict = "PROBLEM（有冲突/错误/校验不一致，未覆盖任何既有文件）"
        code = EXIT_PROBLEM
    else:
        verdict = "PASS（全部文件大小与 SHA256 一致）"
        code = EXIT_OK
    rep(f"校验结论      : {verdict}")
    rep(f"退出码        : {code}")

    if log_path is not None:
        rep(f"日志          : {log_path}")
    rep(f"结束时间      : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    rep("=" * 78)

    rep.flush_log()
    if rep.log_error:
        print(f"[提示] 日志写入失败（不影响复制结果）：{rep.log_error}")
    return code


if __name__ == "__main__":
    sys.exit(main())
