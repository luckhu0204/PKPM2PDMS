# -*- coding: utf-8 -*-
"""deploy PKPMJWD addin into PDMS 12.1 SP4 (CONTRACT §p.6).

**本脚本属于交付物；本轮绝不执行、绝不部署（契约 §p.10-1）。**
安装必须由用户在 PDMS **停机** 时自行执行（见 ../README.txt）。

步骤（§p.6 冻结表；骨架照 D:\\AI_Work\\PDMS三维文字程序\\TGTEXT\\deploy_tgtext.py，
      行号出处：备份 :21-26 / DesignAddins 追加 :28-38 / DesignCustomization 追加
      :41-51 / 复制 :54-58；v3 在其上硬化）：

  0  **缺省 dry-run**：只打印"将要改变的全部对象"完整清单（逐条绝对路径），不落盘；
     带 --execute 才真正修改（对应安全红线 6「先打印完整清单再执行」）。
  1  备份 <root>\\DesignAddins.xml / DesignCustomization.xml 各一次（.pkpmjwd-bak）。
  2  DesignAddins.xml 的 </ArrayOfString> 前插 `  <string>PKPMJWD</string>`；幂等。
  3  DesignCustomization.xml 的 </UICustomizationFiles> 前插
     `  <CustomizationFile Name="PKPMJWD" Path="pkpmjwd.uic" />`；幂等。
  4  复制 dist\\PKPMJWD.dll、dist\\pkpmjwd.uic 到 <PDMS根>。
  5  写 <PDMS根>\\PKPMJWD\\engine_path.txt（引擎入口绝对路径，UTF-8 无 BOM 单行）；
     复制 pdms\\pkpmjwduniquename.pmlfnc 到 <PDMS根>\\PKPMJWD\\pml\\（GBK+CRLF 原样复制）。

纪律：只加不删、幂等、可回滚（恢复用同目录 undeploy_pkpmjwd.py）；
     两个 XML 用 utf-8-sig 读写并保留 BOM 与 CRLF（§p.6 实测两者均 UTF-8 带 BOM + CRLF）；
     PDMS 安装目录以外不落任何文件；引擎本体不复制进 PDMS 目录（engine_path.txt 指回工作区）。

用法：
  python deploy_pkpmjwd.py                         # dry-run（缺省，只打印清单）
  python deploy_pkpmjwd.py --execute               # 真正安装（PDMS 停机时！）
  python deploy_pkpmjwd.py --pdms-root <DIR>       # 指向沙箱副本（验收 17 用）
  python deploy_pkpmjwd.py --engine-entry <PATH>   # 显式指定引擎入口
  python deploy_pkpmjwd.py --pmlfnc <PATH>         # 显式指定 .pmlfnc 源（测试钩子）
"""
import argparse
import io
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent               # pdms-net/deploy/
PKG = HERE.parents[1]                                # PKPM-JWD导入导出/
SRC = HERE.parent                                    # pdms-net/
DEFAULT_ROOT = Path(r"D:\AVEVA\Plant\PDMS12.1.SP4")

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 动作种类（执行分支按此精确分发；kind 一律简单字符串，附注走 note 列）
K_BACKUP = "backup"            # a=原文件, b=.pkpmjwd-bak
K_INS_ADDINS = "insert-addins"     # a=插入行, b=xml 路径
K_INS_CUST = "insert-cust"         # a=插入行, b=xml 路径
K_COPY = "copy"                # a=源, b=目标
K_WRITE = "write"              # a=engine 入口文本, b=engine_path.txt


def parse_args():
    p = argparse.ArgumentParser(description="deploy PKPMJWD addin（缺省 dry-run）")
    p.add_argument("--execute", action="store_true",
                   help="真正修改（缺省只打印清单，不落盘）")
    p.add_argument("--pdms-root", default=None, metavar="DIR",
                   help="PDMS 安装根（缺省 %s；测试可指向沙箱副本）" % DEFAULT_ROOT)
    p.add_argument("--engine-entry", default=None, metavar="PATH",
                   help="engine_path.txt 的内容（缺省依次取 engine/dist/pkpmjwd_engine.exe、"
                        "run_engine.cmd）")
    p.add_argument("--pmlfnc", default=None, metavar="PATH",
                   help="pkpmjwduniquename.pmlfnc 源路径（缺省 <包根>\\pdms\\pkpmjwduniquename.pmlfnc）")
    return p.parse_args()


def backup_once(p: Path, acts):
    """§p.6 步骤 1；同 deploy_tgtext.py:21-26 的 backup_once（后缀改 .pkpmjwd-bak）。"""
    bak = p.with_suffix(p.suffix + ".pkpmjwd-bak")
    if bak.exists():
        acts.append((K_BACKUP, str(p), str(bak), False, "备份已存在，跳过（只备一次）"))
    else:
        acts.append((K_BACKUP, str(p), str(bak), True, ""))


def xml_read(p: Path):
    """utf-8-sig 读（去 BOM，统一换行为 \\n）；写回时恢复 BOM + CRLF。"""
    with io.open(str(p), "r", encoding="utf-8-sig") as f:
        return f.read()


def xml_write(p: Path, text: str):
    """保留 BOM（utf-8-sig）与 CRLF（\\n -> \\r\\n）；同 deploy_tgtext.py:37 的写法。"""
    with io.open(str(p), "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.write(text)


def resolve_engine_entry(explicit):
    """§p.6 步骤 5 的 engine_path.txt 内容：显式参数 -> 包内 engine/dist 既有入口。"""
    if explicit:
        return Path(explicit), True
    exe = PKG / "engine" / "dist" / "pkpmjwd_engine.exe"
    if exe.exists():
        return exe, True
    wrap = PKG / "engine" / "dist" / "run_engine.cmd"
    if wrap.exists():
        return wrap, True
    return exe, False        # 返回预期路径并标 MISSING（S9 未交付时如实报出）


def main():
    args = parse_args()
    root = Path(args.pdms_root) if args.pdms_root else DEFAULT_ROOT
    addins = root / "DesignAddins.xml"
    cust = root / "DesignCustomization.xml"
    dist = SRC / "dist"
    dll = dist / "PKPMJWD.dll"
    uic_src = dist / "pkpmjwd.uic"
    pmlfnc_src = Path(args.pmlfnc) if args.pmlfnc else PKG / "pdms" / "pkpmjwduniquename.pmlfnc"
    pmlfnc_dst = root / "PKPMJWD" / "pml" / "pkpmjwduniquename.pmlfnc"
    engine_entry, engine_ok = resolve_engine_entry(args.engine_entry)
    engine_flag = root / "PKPMJWD" / "engine_path.txt"

    # ---- 预检：目标与构建产物必须齐备 ----
    pre_fail = []
    for p in (addins, cust):
        if not p.exists():
            pre_fail.append("目标不是 PDMS 安装根？缺 %s" % p)
    for p in (dll, uic_src):
        if not p.exists():
            pre_fail.append("缺构建产物 %s（先在 pdms-net 下跑 build.cmd）" % p)
    if pre_fail:
        for m in pre_fail:
            print("[FAIL] " + m)
        return 2

    # ---- 组清单：将要改变的全部对象（红线 6/8） ----
    acts = []
    backup_once(addins, acts)
    backup_once(cust, acts)

    addins_text = xml_read(addins)
    cust_text = xml_read(cust)
    if ">PKPMJWD<" in addins_text:                    # 幂等判据，同 deploy_tgtext.py:32
        acts.append((K_INS_ADDINS, "  <string>PKPMJWD</string>", str(addins), False,
                     "条目已存在，跳过"))
    else:
        acts.append((K_INS_ADDINS, "  <string>PKPMJWD</string>", str(addins), True,
                     "插到 </ArrayOfString> 之前"))
    if 'Path="pkpmjwd.uic"' in cust_text:             # 幂等判据，同 deploy_tgtext.py:45
        acts.append((K_INS_CUST, '  <CustomizationFile Name="PKPMJWD" Path="pkpmjwd.uic" />',
                     str(cust), False, "条目已存在，跳过"))
    else:
        acts.append((K_INS_CUST, '  <CustomizationFile Name="PKPMJWD" Path="pkpmjwd.uic" />',
                     str(cust), True, "插到 </UICustomizationFiles> 之前"))

    acts.append((K_COPY, str(dll), str(root / "PKPMJWD.dll"), True, ""))
    acts.append((K_COPY, str(dist / "pkpmjwd.uic"), str(root / "pkpmjwd.uic"), True, ""))
    acts.append((K_WRITE, str(engine_entry), str(engine_flag), True,
                 "" if engine_ok else "注意：该引擎入口尚不存在（S9 未交付），仍按预期路径写入"))
    if pmlfnc_src.exists():
        acts.append((K_COPY, str(pmlfnc_src), str(pmlfnc_dst), True, ""))
    else:
        acts.append((K_COPY, str(pmlfnc_src), str(pmlfnc_dst), False,
                     "跳过：源 .pmlfnc 尚未交付（S2）"))

    # ---- 打印完整清单 ----
    print("=" * 72)
    print("deploy PKPMJWD -> %s" % root)
    print("模式：%s" % ("EXECUTE（将真正修改）" if args.execute
                        else "DRY-RUN（不落盘；加 --execute 才修改）"))
    print("将要改变的全部对象（%d 项）：" % len(acts))
    for kind, a, b, will, note in acts:
        tag = "DO  " if will else "skip"
        print("  [%s] %-13s %s" % (tag, kind, a))
        print("        -> %s" % b)
        if note:
            print("        %s" % note)
    print("=" * 72)

    if not args.execute:
        print("DRY-RUN 完成：未写入任何文件。确认清单无误后加 --execute 执行（PDMS 停机时）。")
        return 0

    # ---- 真正执行（与上面清单一一对应，不多不少、只加不删） ----
    for kind, a, b, will, note in acts:
        if not will:
            continue
        if kind == K_BACKUP:
            shutil.copy2(a, b)
        elif kind == K_INS_ADDINS:
            text = xml_read(Path(b))
            text = text.replace("</ArrayOfString>", a + "\n</ArrayOfString>")
            xml_write(Path(b), text)
        elif kind == K_INS_CUST:
            text = xml_read(Path(b))
            text = text.replace("</UICustomizationFiles>", a + "\n</UICustomizationFiles>")
            xml_write(Path(b), text)
        elif kind == K_COPY:
            Path(b).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(a, b)
        elif kind == K_WRITE:
            Path(b).parent.mkdir(parents=True, exist_ok=True)
            with io.open(b, "w", encoding="utf-8", newline="") as f:
                f.write(a + "\n")          # UTF-8 无 BOM 单行（§p.6 步骤 5）

    done = sum(1 for x in acts if x[3])
    print("EXECUTE 完成：%d 项改动（清单同上）。重启 PDMS DESIGN 后生效。" % done)
    if not engine_ok:
        print("注意：engine_path.txt 指向的引擎入口尚未交付（S9），"
              "窗体执行前需补齐或设环境变量 PKPMJWD_ENGINE。")
    if not pmlfnc_src.exists():
        print("注意：pkpmjwduniquename.pmlfnc 尚未交付（S2），§o 唯一化函数暂不可 $M 预载。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
