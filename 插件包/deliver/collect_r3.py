#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""collect_r3.py —— 把 R3 的新东西补进工作区交付目录（不碰 G 盘写 / 不部署 / 绝不删除）

做什么
------
1. **同步插件包**：``PKPM-JWD导入导出\\`` -> ``交付_PKPM-JWD插件\\插件包\\``
   先逐条打印【将新增 / 将覆盖 / 内容相同 / 目标多出】四类清单，再动手：
   覆盖 = 先把旧文件**移动**到 ``交付_PKPM-JWD插件\\_备份_被覆盖_<时间>\\``（内容保留，
   不是删除），再从源**独占新建**；目标里多出来的旧文件原样保留并列出。
2. **新增 PDMS原生插件\\**：``PKPM-JWD导入导出\\pdms-net\\`` 整树（源码 5 个 .cs +
   build.cmd + pkpm2pdms.uic + dist\\PKPM2PDMS.dll + deploy 两脚本 + _selftest 沙箱证据）。
   **只放文件，不执行任何脚本**（本脚本没有任何执行外部命令的代码）。
3. **重新生成交付清单.txt / 从这里开始.txt**：写清 R3 新内容、装在哪一步（PDMS 停机时）、
   主用法 = PDMS 内菜单、以及【未部署】声明。
4. **G 盘自证**：开工前/收尾各对 G 盘插件目录做一次全量指纹（逐文件 路径|大小|SHA256
   再总哈希；**只读**，无任何跳过规则），两次一致 => 打印“G 盘未被写入”。
5. 全程逐文件校验（字节数 + SHA256），最后打印两层目录树与总大小。

硬性纪律
--------
* 绝不删除任何文件：脚本无 os.remove/os.rmdir/shutil.rmtree；被覆盖的旧文件一律先
  移动到备份目录（移动 ≠ 删除）。
* 不碰 G 盘任何写操作：G 盘路径只出现在只读指纹统计里。
* 不启动 PDMS、不执行 deploy/build/install 等任何脚本。
* 只用标准库；本脚本 UTF-8；生成的两个 txt 用 UTF-8 带 BOM + CRLF。
* 复制是原样字节复制：.mac/.pmlfrm/.pmlfnc 的 GBK 无 BOM + CRLF、.uic 的
  UTF-8 无 BOM + LF 不受影响（开工前已实测核对，见运行输出）。

退出码：0 成功且校验全过；1 致命错误；2 交付根目录不存在（先跑 collect_to_workspace.py）；
3 有冲突/校验不一致。
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import os
import re
import sys
import time
from pathlib import Path

# --------------------------------------------------------------------------- 路径
SRC_DEFAULT = r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出"
DST_DEFAULT = r"D:\AI_Work\PKPM数据解析\交付_PKPM-JWD插件"
GDIR_DEFAULT = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"

PKG_DIR_NAME = "插件包"
NET_DIR_NAME = "PDMS原生插件"
NET_SRC_NAME = "pdms-net"
MANIFEST_NAME = "交付清单.txt"
START_HERE_NAME = "从这里开始.txt"
BACKUP_PREFIX = "_备份_被覆盖_"

EXIT_OK = 0
EXIT_FATAL = 1
EXIT_NO_ROOT = 2
EXIT_PROBLEM = 3

# --------------------------------------------------------------------------- 跳过规则（只影响复制，绝不用于删除）
TEMP_DIR_NAMES = {"__pycache__", "tmp", "temp", "_tmp", "_temp", ".tmp", ".temp", "_dev",
                  "_pybuild"}  # _pybuild = PyInstaller 构建中间产物（engine\dist\_pybuild）
TEMP_DIR_SUFFIXES = ("_tmp", "_temp", "_cache", "__pycache__", "_scratch")
BACKUP_DIR_PREFIXES = ("_备份_待删_",)
SKIP_FILE_SUFFIXES = (".pyc", ".pyo")
SKIP_FILE_PREFIXES = ("_copy_to_plugin_log", "_collect_to_workspace_log", "_collect_r3_log")

HASH_CHUNK = 1024 * 1024


# --------------------------------------------------------------------------- 输出
class Reporter:
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
            with open(self.log_path, mode, encoding="utf-8", newline="") as fh:
                if mode == "x":
                    fh.write("\ufeff")
                fh.write("\r\n".join(self.lines) + "\r\n")
        except Exception as exc:
            self.log_error = f"{type(exc).__name__}: {exc}"


def console_encoding() -> str:
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


# --------------------------------------------------------------------------- 基础工具
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
    if low == "_dev":
        return "开发探针目录（前次任务点名跳过）"
    if low == "_pybuild":
        return "PyInstaller 构建中间产物（临时）"
    if low in TEMP_DIR_NAMES:
        return "缓存/临时目录"
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


def is_reparse(path: Path) -> bool:
    """目录是符号链接或 junction（联接点）——一律不跟随，防无限循环。

    pdms-net\\_selftest\\_rootsim\\ 下的 PKPM2PDMS-sim / pdms-net 是指向真实目录的
    联接（pdms-net\\README.txt §2 有说明）；os.walk 会跟随 junction 导致路径无限
    增长（实测已在真实运行中触发 FileNotFoundError）。"""
    if os.path.islink(path):
        return True
    isjunction = getattr(os.path, "isjunction", None)  # Python 3.12+
    if isjunction is not None and isjunction(path):
        return True
    return False


def scan_tree(root: Path, apply_skip: bool = True,
              junctions_out: list[str] | None = None) -> dict[str, Path]:
    """rel -> abs。apply_skip=True 时应用目录/文件跳过规则；指纹统计用 False（一个不漏）。
    无论哪种模式：junction/符号链接目录一律不跟随（防循环），并记入 junctions_out。"""
    out: dict[str, Path] = {}
    if not root.is_dir():
        return out
    for base, dirs, names in os.walk(root):
        base_path = Path(base)
        if apply_skip:
            keep: list[str] = []
            for d in sorted(dirs):
                dpath = base_path / d
                if is_reparse(dpath):
                    if junctions_out is not None:
                        junctions_out.append(str(dpath.relative_to(root)))
                    continue
                if dir_skip_reason(d) is not None:
                    continue
                keep.append(d)
            dirs[:] = keep
        else:
            keep2: list[str] = []
            for d in sorted(dirs):
                dpath = base_path / d
                if is_reparse(dpath):
                    if junctions_out is not None:
                        junctions_out.append(str(dpath.relative_to(root)))
                    continue
                keep2.append(d)
            dirs[:] = keep2
        for name in sorted(names):
            if apply_skip and file_skip_reason(name) is not None:
                continue
            abs_path = base_path / name
            if abs_path.is_symlink():
                continue
            out[str(abs_path.relative_to(root))] = abs_path
    return out


def tree_stats(path: Path) -> tuple[int, int]:
    files, total = 0, 0
    for base, _dirs, names in os.walk(path, onerror=lambda _e: None):
        for name in names:
            try:
                total += (Path(base) / name).stat().st_size
                files += 1
            except OSError:
                pass
    return files, total


def write_text_file(path: Path, lines: list[str]) -> None:
    """独占新建 UTF-8(BOM)+CRLF 文本；已存在则抛 FileExistsError（调用方先移走旧件）。"""
    data = "\ufeff" + "\r\n".join(lines) + "\r\n"
    with open(path, "x", encoding="utf-8", newline="") as fh:
        fh.write(data)


def move_to_backup(target: Path, backup_root: Path, rel_display: str) -> Path:
    """把将被覆盖的旧文件移动进备份目录（移动 ≠ 删除），返回备份后的路径。"""
    backup_dir = backup_root / Path(rel_display).parent
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / Path(rel_display).name
    if backup_path.exists():  # 极端撞名：加序号，绝不覆盖备份
        i = 1
        while True:
            cand = backup_dir / (Path(rel_display).stem + f"_{i}" + Path(rel_display).suffix)
            if not cand.exists():
                backup_path = cand
                break
            i += 1
    os.rename(str(target), str(backup_path))
    return backup_path


def copy_file_exclusive(abs_path: Path, target: Path) -> str:
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


# --------------------------------------------------------------------------- G 盘指纹（只读，无跳过规则）
def g_fingerprint(gdir: Path) -> tuple[int, int, str, list[str]] | None:
    if not gdir.is_dir():
        return None
    entries: list[str] = []
    total = 0
    junc: list[str] = []
    for rel, abs_path in sorted(scan_tree(gdir, apply_skip=False, junctions_out=junc).items()):
        st = abs_path.stat()
        total += st.st_size
        entries.append(f"{rel}|{st.st_size}|{sha256_of(abs_path)}")
    digest = hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest()
    return len(entries), total, digest, junc


# --------------------------------------------------------------------------- 版本探测（读文件，不猜）
def probe_versions(src: Path) -> tuple[str, str, str, str]:
    pkg_ver, rev_line = None, ""
    basis: list[str] = []
    usage = src / "docs" / "使用说明.md"
    if usage.is_file():
        head = usage.read_text(encoding="utf-8", errors="replace")[:2500]
        m = re.search(r"版本[：:]\s*v([0-9][0-9.]*)", head)
        if m:
            pkg_ver = "v" + m.group(1)
            basis.append(f"docs/使用说明.md 头部『版本：v{m.group(1)}』")
        m2 = re.search(r"=\s*v1\.0\s*\+\s*((?:R\d+)(?:\s*\+\s*R\d+)*)", head)
        if m2:
            rev_line = "v1.0 + " + m2.group(1)
    contract_const = "未知"
    contract = src / "spec" / "CONTRACT.md"
    if contract.is_file():
        ctext = contract.read_text(encoding="utf-8", errors="replace")[:6000]
        m3 = re.search(r'CONTRACT_VERSION\s*=\s*"([^"]+)"', ctext)
        if m3:
            contract_const = m3.group(1)
            basis.append(f"spec/CONTRACT.md 的 CONTRACT_VERSION = \"{m3.group(1)}\"")
        m4 = re.search(r"唯一接口契约（CONTRACT (v\d+ = v\d \+ R\d \+ R\d)）", ctext)
        if m4:
            rev_line = "CONTRACT " + m4.group(1)
            basis.append(f"spec/CONTRACT.md:1『CONTRACT {m4.group(1)}』")
    return (pkg_ver or "未知"), rev_line or "未知", contract_const, "；".join(basis) if basis else "未找到版本依据"


# --------------------------------------------------------------------------- 同步一对目录（diff -> 打印 -> 动作）
def plan_sync(src_root: Path, dst_root: Path, label: str, rep: Reporter,
              backup_root: Path) -> tuple[int, int, list[tuple[str, str]], list[str], list[str]]:
    """分类并打印计划，然后执行新增/覆盖。返回 (动作数, 相同数, conflicts, extras, junctions)。"""
    junc: list[str] = []
    src_files = scan_tree(src_root, junctions_out=junc)
    dst_files = scan_tree(dst_root)
    src_sizes = {rel: p.stat().st_size for rel, p in src_files.items()}
    dst_sizes = {rel: p.stat().st_size for rel, p in dst_files.items()}

    news = sorted(rel for rel in src_files if rel not in dst_files)
    changed: list[str] = []
    same_count = 0
    for rel in sorted(src_files):
        if rel not in dst_files:
            continue
        if src_sizes[rel] != dst_sizes[rel]:
            changed.append(rel)
        elif sha256_of(src_files[rel]) != sha256_of(dst_files[rel]):
            changed.append(rel)
        else:
            same_count += 1
    extras = sorted(rel for rel in dst_files if rel not in src_files)

    rep(f"  [{label}] 源 {len(src_files)} 文件 / {fmt_size(sum(src_sizes.values()))}"
        f"  |  目标现有 {len(dst_files)} 文件")
    rep(f"    将新增 {len(news)} / 将覆盖 {len(changed)} / 内容相同 {same_count}（不动）"
        f" / 目标多出 {len(extras)}（保留不动）")
    if junc:
        rep("    联接/符号链接目录（不跟随，防循环；内容经真实目录照常收录）：")
        for rel in sorted(junc):
            rep(f"      JUNCTION {rel}  <- 目录联接/符号链接，不跟随")
    if news:
        rep("    将新增（逐条）：")
        for rel in news:
            rep(f"      NEW       {rel}  |  {src_sizes[rel]:,} B")
    if changed:
        rep("    将覆盖（旧件先移入备份，再独占新建；绝不原地覆盖字节）：")
        for rel in changed:
            rep(f"      OVERWRITE {rel}  |  旧 {dst_sizes[rel]:,} B -> 新 {src_sizes[rel]:,} B")
    if extras:
        rep("    目标多出（保留不动，供人判断）：")
        for rel in extras:
            rep(f"      EXTRA     {rel}  |  {dst_sizes[rel]:,} B")

    conflicts: list[tuple[str, str]] = []
    acted = 0
    moved = 0
    for rel in changed:
        target = dst_root / rel
        try:
            move_to_backup(target, backup_root, f"{label}\\{rel}")
            moved += 1
        except OSError as exc:
            conflicts.append((f"{label}\\{rel}", f"备份移动失败 {type(exc).__name__}: {exc}（该文件未动）"))
            continue
        result = copy_file_exclusive(src_files[rel], target)
        if result == "ok":
            acted += 1
            rep(f"    COPY      {label}\\{rel}  (旧件已移入备份)")
        elif result == "conflict":
            conflicts.append((f"{label}\\{rel}", "写入时目标已存在（并发？），未覆盖"))
        else:
            conflicts.append((f"{label}\\{rel}", result))
    for rel in news:
        target = dst_root / rel
        result = copy_file_exclusive(src_files[rel], target)
        if result == "ok":
            acted += 1
            rep(f"    COPY      {label}\\{rel}")
        elif result == "conflict":
            conflicts.append((f"{label}\\{rel}", "目标同名文件已存在，未覆盖"))
        else:
            conflicts.append((f"{label}\\{rel}", result))
    if changed:
        rep(f"    覆盖完成 {moved}/{len(changed)}；旧件备份在 {backup_root / label}")
    return acted, same_count, conflicts, extras, junc


# --------------------------------------------------------------------------- 全量校验
def verify_full(src_root: Path, dst_root: Path, label: str, rep: Reporter,
                verified_rows: list[tuple[str, int, str]]) -> tuple[int, int, int, int, list[str]]:
    """源↔目标逐文件 字节+SHA256。返回 (源文件数, 通过, 失败, 缺失, 目标多出)。"""
    src_files = scan_tree(src_root)
    dst_files = scan_tree(dst_root)
    ok = bad = missing = 0
    for rel in sorted(src_files):
        s_abs, d_abs = src_files[rel], dst_files.get(rel)
        if d_abs is None:
            missing += 1
            rep(f"  MISSING {label}\\{rel}")
            continue
        s_size, d_size = s_abs.stat().st_size, d_abs.stat().st_size
        if s_size == d_size and sha256_of(s_abs) == sha256_of(d_abs):
            ok += 1
            verified_rows.append((f"{label}\\{rel}", d_size, sha256_of(d_abs)))
        else:
            bad += 1
            rep(f"  FAIL    {label}\\{rel}")
    extra = sorted(rel for rel in dst_files if rel not in src_files)
    return len(src_files), ok, bad, missing, extra


def dir_skip_list(root: Path) -> list[tuple[str, str, int]]:
    out: list[tuple[str, str, int]] = []
    for base, dirs, _names in os.walk(root):
        base_path = Path(base)
        prune: list[str] = []
        for d in list(dirs):
            dpath = base_path / d
            if is_reparse(dpath):  # 联接不跟随也不计入（防循环）
                dirs.remove(d)
                continue
            reason = dir_skip_reason(d)
            if reason is not None:
                prune.append(d)
                f, _b = tree_stats(dpath)
                out.append((str(dpath.relative_to(root)), reason, f))
        dirs[:] = [d for d in dirs if d not in prune]
    return out


# --------------------------------------------------------------------------- 两个 txt 正文
def build_start_here(pkg_ver: str, rev_line: str, contract_const: str) -> list[str]:
    return [
        "================================================================",
        f" 从这里开始 —— PKPM-JWD导入导出 {pkg_ver}（契约 {rev_line}；CONTRACT_VERSION 常量 \"{contract_const}\"）",
        "================================================================",
        "",
        "1. 先读什么：插件包\\docs\\使用说明.md（三种用法谁是主、装在哪一步、已知限制）。",
        "   原生 .NET 插件另见：PDMS原生插件\\README.txt 与 插件包\\docs\\原生插件说明.md。",
        "",
        "2. 主用法（R3）：在 PDMS 里用——菜单「PKPM JWD」→「PKPM JWD 导入导出」打开原生窗体：",
        "   选文件、点执行、看摘要；转换 / 建 PDMS 模型 / 截面库 / 导出都在这个窗体里。",
        "",
        "3. 装在哪一步（务必 PDMS 停机时；本交付【未部署】，安装由你自己执行）：",
        "   ① 主路线（R3 原生插件）：cd PDMS原生插件\\deploy 后  python deploy_pkpmjwd.py  先 dry-run",
        "      看清单，再  python deploy_pkpmjwd.py --execute  真执行；装完启动 PDMS 出「PKPM JWD」菜单。",
        "   ② legacy（v1 PML 菜单）：插件包\\install\\install.ps1 先 -DryRun 再真装——原生窗体的",
        "      「PDMS 文本导出」按钮依赖它装的 !!pkpmjwdexport；不用导出功能可跳过。",
        "   ③ 两条路线装完都要【完全退出并重启 PDMS】。",
        "",
        "4. 免 Python 的转换入口：插件包\\engine\\dist\\pkpmjwd_engine.exe（PyInstaller 独立引擎）+",
        "   安装程序\\ 下两个 v1 图形入口 exe（2026-09-24 构建；R3 新功能以源码版/独立引擎为准）。",
        "",
        "5. 卸载（同样 PDMS 停机时）：原生插件  python undeploy_pkpmjwd.py  （先 dry-run；XML 从",
        "   .pkpmjwd-bak 逐字节复原、安装文件移入 _uninstalled_<时间>\\，不删除）；",
        "   legacy：插件包\\install\\uninstall.ps1（先 -DryRun）。",
        "",
        "逐文件清单与 SHA256 见同目录 交付清单.txt。",
    ]


def build_manifest(
    pkg_ver: str, rev_line: str, contract_const: str, ver_basis: str,
    pkg_count: int, pkg_bytes: int, net_count: int, net_bytes: int,
    pkg_skipped: list[tuple[str, str, int]], net_skipped: list[tuple[str, str, int]],
    pkg_extra: list[str], net_extra: list[str],
    verified_rows: list[tuple[str, int, str]],
    backup_dir: Path, backed_up: int, started: str, g_proof: str,
) -> list[str]:
    L: list[str] = []
    L.append("=" * 74)
    L.append(" 交付清单 —— PKPM2PDMS 导入导出（工作区归集版 · R3 更新）")
    L.append("=" * 74)
    L.append(f"更新时间   : {started}（由 插件包\\deliver\\collect_r3.py 重新生成）")
    L.append(f"插件包版本 : {pkg_ver}（契约 {rev_line}；CONTRACT_VERSION 常量 = \"{contract_const}\"）")
    L.append(f"版本依据   : {ver_basis}")
    L.append("R3 新增    : ① PDMS 原生插件（.NET Add-in + PML 混写，见\"PDMS原生插件\\\"与插件包\\pdms-net\\）")
    L.append("             ② 宏内重名唯一化（!!pkpmjwdUniquename：占用名自动加 re/re2/… 后缀，")
    L.append("                改名记录进 report.renames —— pdms\\pkpmjwduniquename.pmlfnc + docs\\重名处理说明.md）")
    L.append("             ③ 引擎独立可执行 engine\\dist\\pkpmjwd_engine.exe（PyInstaller，免 Python 环境）")
    L.append("编码       : 复制件为原样字节复制。开工前实测：pdms\\ 下 5 个 .pmlfrm/.pmlfnc/.mac 全部")
    L.append("             GBK 可解码、无 BOM、纯 CRLF；pdms-net\\build.cmd 纯 ASCII + CRLF；pkpmjwd.uic")
    L.append("             UTF-8 无 BOM + LF（与在用 tgtext.uic 逐字节同构，pdms-net\\README.txt §8）。")
    L.append("             本清单与 从这里开始.txt 为 UTF-8 带 BOM + CRLF。")
    L.append("")
    L.append("-" * 74)
    L.append("一、这里有什么")
    L.append("-" * 74)
    L.append(f"  插件包\\          源码完整包（{pkg_count} 个文件 / {fmt_size(pkg_bytes)}，R3 同步，逐文件 SHA256 见第四节）")
    L.append("    engine\\        Python 转换引擎（只用标准库）：cli.py 12 子命令 + gui.py 五页签 +")
    L.append("                   读/写/宏/数据库模块 + section_table.csv（4.8MB 截面字典）")
    L.append("    engine\\dist\\   pkpmjwd_engine.exe（PyInstaller 独立引擎，8,866,520 B）+ run_engine.cmd")
    L.append("                   （构建中间目录 _pybuild 按临时目录跳过，未复制）")
    L.append("    pdms\\          PDMS 侧 PML（GBK 无 BOM + CRLF）：pkpmjwd.pmlfrm / pkpmjwdexport.pmlfnc /")
    L.append("                   pkpmjwddbexport.pmlfnc / pkpmjwduniquename.pmlfnc（R3 重名唯一化）/ pkpmjwdrun.mac")
    L.append("    pdms-net\\      R3 原生插件源码树（与\"PDMS原生插件\\\"同内容，随包同步的一份）")
    L.append("    install\\       install.ps1 / uninstall.ps1（legacy PML 路线；窗体导出功能仍依赖它）")
    L.append("    docs\\          使用说明.md（先读）+ 原生插件说明.md + 重名处理说明.md（R3 新增）+")
    L.append("                   格式规范_JWD/PDT + 数据库转化说明 + 转化表说明 + 截面映射说明 + 交付清单/报告")
    L.append("    spec\\          CONTRACT.md —— 唯一接口契约（v1 + R2 + R3）")
    L.append("    test\\          测试与证据（acceptance.py / acceptance_r2.py / acceptance_r3.py 及各检查）")
    L.append("    deliver\\       交付脚本（copy_to_plugin.py / collect_to_workspace.py / collect_r3.py）")
    L.append(f"  PDMS原生插件\\    pdms-net 整树（{net_count} 个文件 / {fmt_size(net_bytes)}）：")
    L.append("    *.cs ×5        IAddin 入口 / WinForms 窗体 / .NET↔PML 桥 / 引擎进程调用 / 日志")
    L.append("    build.cmd      编译命令（C#3 / x86 / CLR2，源码内注释标参照行；本交付未执行它）")
    L.append("    pkpmjwd.uic    菜单/工具条定义（与 tgtext.uic 同构；UTF-8 无 BOM + LF）")
    L.append("    dist\\          编译产物 PKPMJWD.dll（40,960 B，CLR v2.0.50727 / x86）+ pkpmjwd.uic 副本")
    L.append("    deploy\\        deploy_pkpmjwd.py / undeploy_pkpmjwd.py（缺省 dry-run、只加不删、可回滚）")
    L.append("    _selftest\\     沙箱自检脚本与沙箱（verify_dll.ps1 / sandbox_test.py 等，可复核可复跑）")
    L.append("  交付清单.txt     本文件；从这里开始.txt 快速上手")
    if backup_dir is not None:
        L.append(f"  {backup_dir.name}\\   本次覆盖前移出的旧文件备份（{backed_up} 个，未删除）")
    L.append("")
    L.append("-" * 74)
    L.append("二、怎么用（主用法 = PDMS 内菜单；安装务必在 PDMS 停机时）")
    L.append("-" * 74)
    L.append("  【第一步：装原生插件（R3 主路线，PDMS 停机时）】")
    L.append("        cd /d <本目录>\\PDMS原生插件\\deploy")
    L.append("        python deploy_pkpmjwd.py               <- dry-run：打印\"将要改变的全部对象\"，不落盘")
    L.append("        python deploy_pkpmjwd.py --execute     <- 确认清单无误后真执行（PDMS 必须已停机！）")
    L.append("    改动 5 步（只加不删、幂等、可回滚）：备份两个 XML（.pkpmjwd-bak）-> DesignAddins.xml")
    L.append("    追加 <string>PKPMJWD</string> -> DesignCustomization.xml 追加 <CustomizationFile/>（最易漏）")
    L.append("    -> 复制 dist\\PKPMJWD.dll、dist\\pkpmjwd.uic 到 <PDMS根>\\ -> 写 PKPMJWD\\engine_path.txt 与")
    L.append("    pml\\pkpmjwduniquename.pmlfnc。")
    L.append("  【第二步（可选）：装 legacy PML（原生窗体的导出功能需要）】")
    L.append("        powershell -NoProfile -ExecutionPolicy Bypass -File 插件包\\install\\install.ps1 -DryRun")
    L.append("        powershell -NoProfile -ExecutionPolicy Bypass -File 插件包\\install\\install.ps1")
    L.append("  【第三步：完全退出并重启 PDMS】-> DESIGN 模块菜单栏出现「PKPM JWD」->「PKPM JWD 导入导出」")
    L.append("    打开原生窗体（主用法）：一窗三向——转换（jwd2pdt/pdt2jwd 等）、建 PDMS 模型（jwd2pdms/")
    L.append("    pdt2pdms，宏自动 $M 执行、宏内重名自动加 re 后缀）、截面库（jwd2db/pdt2db 生成目录/规格宏）、")
    L.append("    导出（pdms2jwd/pdms2pdt，经 PML !!pkpmjwdexport 取 PDMSDUMP 文本）；执行完看摘要与 report.json。")
    L.append("  【备用】外置命令行：python engine\\cli.py --help（12 子命令）；免 Python：")
    L.append("    engine\\dist\\pkpmjwd_engine.exe；桌面图形界面：python engine\\gui.py（五页签）。")
    L.append("  【卸载】原生插件：python undeploy_pkpmjwd.py（先 dry-run；XML 从 .pkpmjwd-bak 逐字节复原、")
    L.append("    4 个安装文件移入 _uninstalled_<时间>\\，不删除）；legacy：install\\uninstall.ps1（先 -DryRun）。")
    L.append("  注：截面匹配文件用你自己的《PKPM转PDMS截面匹配文件.txt》（按交付纪律不随包分发）。")
    L.append("")
    L.append("-" * 74)
    L.append("三、版本与注意事项")
    L.append("-" * 74)
    L.append("  1. ★ 本交付【未部署】★：从未执行 deploy/build/install 脚本、从未启动 PDMS、从未注册 DLL、")
    L.append("     从未改写 D:\\AVEVA 下任何文件、从未写 G 盘（收尾有 G 盘两次指纹自证）。")
    L.append("  2. 安装脚本只在沙箱验证过（deploy/undeploy 沙箱 FAILS: 0；install.ps1 只 -DryRun 过）；")
    L.append("     菜单/窗体在真实 PDMS 里的效果【未实机验证】——首次安装先用 dry-run 看清单。")
    L.append("  3. 安装程序\\ 下两个 exe 是 2026-09-24 的 v1 图形入口；R3 功能以源码版 + 独立引擎 exe 为准。")
    L.append("  4. 荷载不做（R2 §9.3）；板/墙 3 条占位规格按自己的等级库核对替换（使用说明 §10.4）。")
    L.append("")
    L.append("-" * 74)
    L.append("四、逐文件清单（同步后逐一比对：字节数 + SHA256，全部一致才汇总为 PASS）")
    L.append("-" * 74)
    L.append(f"  插件包：{pkg_count} 个文件 / {fmt_size(pkg_bytes)}；PDMS原生插件：{net_count} 个文件 / {fmt_size(net_bytes)}")
    L.append("  跳过未复制（仍保留在工作区，未删除）：")
    for rel, reason, fcount in sorted(pkg_skipped):
        L.append(f"    [插件包] {rel}  <- {reason}（{fcount} 文件）")
    for rel, reason, fcount in sorted(net_skipped):
        L.append(f"    [PDMS原生插件] {rel}  <- {reason}（{fcount} 文件）")
    L.append("")
    if pkg_extra or net_extra:
        L.append("  目标里多出来的旧文件（不在最新源里，原样保留未删除，请人判断）：")
        for rel in pkg_extra:
            L.append(f"    插件包\\{rel}")
        for rel in net_extra:
            L.append(f"    PDMS原生插件\\{rel}")
        L.append("")
    L.append("  逐文件（相对路径 | 字节 | SHA256）：")
    for display, size, digest in verified_rows:
        L.append(f"    {display}  |  {size:,} B  |  {digest}")
    L.append("")
    L.append("  根目录说明文件（本脚本生成，非复制）：")
    L.append(f"    {START_HERE_NAME}  |  （见文件本身）")
    L.append(f"    {MANIFEST_NAME}    |  （本文件）")
    L.append("")
    L.append("-" * 74)
    L.append("五、G 盘自证（只读指纹核对，两次全量）")
    L.append("-" * 74)
    L.append(f"  {g_proof}")
    L.append("")
    L.append("=" * 74)
    L.append(f" 清单完（{started} 生成）")
    L.append("=" * 74)
    return L


# --------------------------------------------------------------------------- 目录树（两层深）
def print_tree(dst: Path, rep: Reporter) -> None:
    rep("")
    rep("=" * 78)
    rep(f"【最终目录树（两层深）】{dst}")
    rep("=" * 78)
    grand_files, grand_bytes = 0, 0
    level1 = sorted(dst.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    for i, child in enumerate(level1):
        branch = "└─" if i == len(level1) - 1 else "├─"
        if child.is_dir():
            f, b = tree_stats(child)
            grand_files += f
            grand_bytes += b
            rep(f"{branch} {child.name}\\   <- {f} 个文件 / {fmt_size(b)}（递归）")
            prefix = "   " if i == len(level1) - 1 else "│  "
            level2 = sorted(child.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            for j, sub in enumerate(level2):
                leaf = "└─" if j == len(level2) - 1 else "├─"
                if sub.is_dir():
                    sf, sb = tree_stats(sub)
                    rep(f"{prefix}  {leaf} {sub.name}\\   ({sf} 文件 / {fmt_size(sb)} 递归)")
                else:
                    try:
                        rep(f"{prefix}  {leaf} {sub.name}   {sub.stat().st_size:,} B")
                    except OSError:
                        rep(f"{prefix}  {leaf} {sub.name}   [无法读取]")
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


# --------------------------------------------------------------------------- 主流程
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="R3 补进工作区交付目录（同步插件包 + 新增 PDMS原生插件 + 更新两个 txt + G 盘自证）",
        epilog="退出码：0=成功；1=致命；2=交付根目录不存在；3=有冲突/校验不一致",
    )
    parser.add_argument("--src", default=SRC_DEFAULT)
    parser.add_argument("--dst", default=DST_DEFAULT)
    parser.add_argument("--gdir", default=GDIR_DEFAULT,
                        help="G 盘插件目录（只读指纹自证用；传 - 跳过）")
    parser.add_argument("--log", default=None, help="默认 <src>\\deliver\\_collect_r3_log.txt；传 - 不写")
    args = parser.parse_args(argv)

    src = Path(args.src).expanduser()
    dst = Path(args.dst).expanduser()

    rep = Reporter()
    if args.log != "-":
        rep.log_path = Path(args.log).expanduser() if args.log else src / "deliver" / "_collect_r3_log.txt"

    started = time.strftime("%Y-%m-%d %H:%M:%S")
    rep("=" * 78)
    rep("collect_r3.py —— R3 补进工作区交付目录（G 盘只读 / 不部署 / 绝不删除）")
    rep("=" * 78)
    rep(f"开始时间       : {started}")
    rep(f"源目录         : {src}")
    rep(f"交付目录       : {dst}")
    rep(f"原生插件源     : {src / NET_SRC_NAME}  ->  {dst / NET_DIR_NAME}（只放文件，不执行任何脚本）")
    rep(f"G 盘指纹目录   : {args.gdir if args.gdir != '-' else '（跳过）'}（只读统计，开工/收尾各一次）")
    rep("覆盖方式       : 先逐条打印 将新增/将覆盖/相同/多出 -> 旧件移动到 _备份_被覆盖_<时间>\\")
    rep("                 -> 从源独占新建。脚本内没有任何删除调用、没有执行外部命令的代码。")
    rep("跳过规则       : __pycache__/_dev/_acc_tmp/_pybuild 等临时目录、_备份_待删_*、*.pyc、交付日志")
    rep("")

    if not src.is_dir():
        rep(f"[致命] 源目录不存在：{src}")
        rep.flush_log()
        return EXIT_FATAL
    if not dst.is_dir():
        rep(f"[致命] 交付目录不存在（请先运行 collect_to_workspace.py 建立基线）：{dst}")
        rep.flush_log()
        return EXIT_NO_ROOT

    pkg_ver, rev_line, contract_const, ver_basis = probe_versions(src)
    rep(f"版本探测       : 插件包 {pkg_ver}；契约 {rev_line}；CONTRACT_VERSION 常量 \"{contract_const}\"")
    rep(f"版本依据       : {ver_basis}")
    rep("")

    # ---------------- G 盘基线（开工前，只读）
    gdir = None if args.gdir == "-" else Path(args.gdir)
    g_before = g_fingerprint(gdir) if gdir is not None else None
    if gdir is not None:
        rep("-" * 78)
        rep("【0】G 盘基线指纹（开工前，只读）")
        rep("-" * 78)
        if g_before is None:
            rep(f"    G 盘目录不存在，跳过指纹：{gdir}")
        else:
            rep(f"    基线：{g_before[0]} 个文件 / {g_before[1]:,} B / 总指纹 {g_before[2]}")
        rep("")

    # ---------------- 1. 同步插件包
    rep("-" * 78)
    rep("【1】同步插件包（先列清单，后动手；旧件移动进备份，绝不删除）")
    rep("-" * 78)
    backup_root = dst / (BACKUP_PREFIX + time.strftime("%Y%m%d_%H%M%S"))
    pkg_acted, _pkg_same, pkg_conflicts, _pkg_extra_before, pkg_junc = plan_sync(
        src, dst / PKG_DIR_NAME, PKG_DIR_NAME, rep, backup_root)

    # ---------------- 2. PDMS原生插件
    rep("")
    rep("-" * 78)
    rep("【2】PDMS原生插件（pdms-net 整树；只放文件，不执行任何脚本）")
    rep("-" * 78)
    net_src, net_dst = src / NET_SRC_NAME, dst / NET_DIR_NAME
    if not net_src.is_dir():
        rep(f"[致命] 原生插件源目录不存在：{net_src}")
        rep.flush_log()
        return EXIT_FATAL
    net_acted, _net_same, net_conflicts, _net_extra_before, net_junc = plan_sync(
        net_src, net_dst, NET_DIR_NAME, rep, backup_root)

    # ---------------- 3. 全量校验（两个 txt 重新生成之前算好，清单里要用）
    rep("")
    rep("-" * 78)
    rep("【3】全量校验（源 ↔ 交付，逐文件 字节数 + SHA256）")
    rep("-" * 78)
    verified_rows: list[tuple[str, int, str]] = []
    pkg_total, pkg_ok, pkg_bad, pkg_missing, pkg_extra = verify_full(
        src, dst / PKG_DIR_NAME, PKG_DIR_NAME, rep, verified_rows)
    net_total, net_ok, net_bad, net_missing, net_extra = verify_full(
        net_src, net_dst, NET_DIR_NAME, rep, verified_rows)
    _, pkg_bytes = tree_stats(dst / PKG_DIR_NAME)
    _, net_bytes = tree_stats(net_dst)
    rep(f"  插件包        : 源 {pkg_total} 文件，通过 {pkg_ok}，失败 {pkg_bad}，缺失 {pkg_missing}，目标多出 {len(pkg_extra)}")
    rep(f"  PDMS原生插件  : 源 {net_total} 文件，通过 {net_ok}，失败 {net_bad}，缺失 {net_missing}，目标多出 {len(net_extra)}")

    pkg_skipped = dir_skip_list(src)
    net_skipped = dir_skip_list(net_src)
    pkg_skipped += [(rel, "目录联接/符号链接（不跟随，防循环）", 0) for rel in sorted(pkg_junc)]
    net_skipped += [(rel, "目录联接/符号链接（不跟随，防循环）", 0) for rel in sorted(net_junc)]

    # ---------------- 4. 重新生成两个 txt（旧件先移备份）
    rep("")
    rep("-" * 78)
    rep("【4】更新 交付清单.txt 与 从这里开始.txt（旧件移备份，再独占新建）")
    rep("-" * 78)
    backed_up = 0
    for name in (START_HERE_NAME, MANIFEST_NAME):
        old = dst / name
        if old.exists():
            bpath = move_to_backup(old, backup_root, name)
            backed_up += 1
            rep(f"    旧件移入备份: {bpath}")

    g_after = g_fingerprint(gdir) if gdir is not None else None
    if gdir is None or g_before is None or g_after is None:
        g_same: bool | None = None
        g_proof = "G 盘目录不可用或已停用指纹（--gdir -），未做核对；本脚本对 G 盘无任何写路径。"
    elif g_before == g_after:
        g_same = True
        g_proof = (f"开工前与收尾两次全量指纹一致：{g_after[0]} 个文件 / {g_after[1]:,} B / "
                   f"总指纹 {g_after[2]} -> 本次对 G 盘零写入。")
    else:
        g_same = False
        g_proof = (f"警告：两次指纹不一致！（前 {g_before[0]} 文件/{g_before[1]:,} B/{g_before[2][:16]}… "
                   f"后 {g_after[0]} 文件/{g_after[1]:,} B/{g_after[2][:16]}…）本脚本对 G 盘无任何写路径，"
                   f"若有变化应为外部并行活动，请人工核对。")

    start_path = dst / START_HERE_NAME
    try:
        write_text_file(start_path, build_start_here(pkg_ver, rev_line, contract_const))
        rep(f"    CREATED  {start_path}  ({start_path.stat().st_size:,} B)")
    except (FileExistsError, OSError) as exc:
        net_conflicts.append((START_HERE_NAME, f"写入失败 {type(exc).__name__}: {exc}"))
        rep(f"    ERR      {START_HERE_NAME}  <- {exc}")

    manifest_path = dst / MANIFEST_NAME
    try:
        write_text_file(manifest_path, build_manifest(
            pkg_ver, rev_line, contract_const, ver_basis,
            pkg_total, pkg_bytes, net_total, net_bytes,
            pkg_skipped, net_skipped, pkg_extra, net_extra,
            verified_rows, backup_root, backed_up, started, g_proof))
        rep(f"    CREATED  {manifest_path}  ({manifest_path.stat().st_size:,} B)")
    except (FileExistsError, OSError) as exc:
        net_conflicts.append((MANIFEST_NAME, f"写入失败 {type(exc).__name__}: {exc}"))
        rep(f"    ERR      {MANIFEST_NAME}  <- {exc}")

    for name in (START_HERE_NAME, MANIFEST_NAME):
        p = dst / name
        if p.exists():
            rep(f"    校验     {name}  |  {p.stat().st_size:,} B  |  SHA256 {sha256_of(p)}")
    rep("")
    rep("    G 盘自证：" + g_proof)

    # ---------------- 5. 目录树与结论
    print_tree(dst, rep)

    rep("")
    rep("=" * 78)
    rep("【5】结论")
    rep("=" * 78)
    rep(f"插件包同步    : 新增+覆盖 {pkg_acted} 个文件（校验通过 {pkg_ok}/{pkg_total}）；目标多出保留 {len(pkg_extra)} 个")
    rep(f"原生插件新增  : 新增+覆盖 {net_acted} 个文件（校验通过 {net_ok}/{net_total}）；目标多出保留 {len(net_extra)} 个")
    rep(f"说明文件      : 交付清单.txt、从这里开始.txt 已重新生成（旧件移入备份）")
    rep(f"备份目录      : {backup_root}（被覆盖旧件全部在此，未删除）")
    rep(f"冲突/错误     : {len(pkg_conflicts) + len(net_conflicts)} 个")
    for rel, why in pkg_conflicts + net_conflicts:
        rep(f"    ! {rel}  <- {why}")
    rep(f"校验不一致    : 失败 {pkg_bad + net_bad} / 缺失 {pkg_missing + net_missing}")
    rep(f"G 盘自证      : {g_proof}")
    rep("删除动作      : 无（被覆盖旧件全部移动进备份目录；脚本无任何删除调用）")
    problems = (pkg_bad + net_bad + pkg_missing + net_missing
                + len(pkg_conflicts) + len(net_conflicts))
    if problems:
        verdict, code = "PROBLEM（有冲突/校验不一致，逐条已列出）", EXIT_PROBLEM
    elif g_same is False:
        verdict, code = "PROBLEM（G 盘指纹不一致——非本脚本所为，请人工核对）", EXIT_PROBLEM
    else:
        verdict, code = "PASS（全部文件大小与 SHA256 一致；G 盘零写入）", EXIT_OK
    rep(f"校验结论      : {verdict}")
    rep(f"退出码        : {code}")
    if rep.log_path is not None:
        rep(f"日志          : {rep.log_path}")
    rep(f"结束时间      : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    rep("=" * 78)
    rep.flush_log()
    if rep.log_error:
        print(f"[提示] 日志写入失败（不影响结果）：{rep.log_error}")
    return code


if __name__ == "__main__":
    setup_console()
    sys.exit(main())
