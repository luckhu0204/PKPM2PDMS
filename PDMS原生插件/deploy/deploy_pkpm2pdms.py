# -*- coding: utf-8 -*-
"""deploy PKPM2PDMS addin into PDMS 12.1 SP4 (CONTRACT §p.6).

**本脚本属于交付物；本轮绝不执行、绝不部署（契约 §p.10-1）。**
安装必须由用户在 PDMS **停机** 时自行执行（见 ../README.txt）。

步骤（§p.6 冻结表；骨架照 D:\\AI_Work\\PDMS三维文字程序\\TGTEXT\\deploy_tgtext.py，
      行号出处：备份 :21-26 / DesignAddins 追加 :28-38 / DesignCustomization 追加
      :41-51 / 复制 :54-58；v3 在其上硬化；〔R7〕清单见下）：

  0  **缺省 dry-run**：只打印"将要改变的全部对象"完整清单（逐条绝对路径），不落盘；
     带 --execute 才真正修改（对应安全红线 6「先打印完整清单再执行」）。
  1  备份 <root>\\DesignAddins.xml / DesignCustomization.xml 各一次（.pkpm2pdms-bak）。
  2  DesignAddins.xml 的 </ArrayOfString> 前插 `  <string>PKPM2PDMS</string>`；幂等。
  3  DesignCustomization.xml 的 </UICustomizationFiles> 前插
     `  <CustomizationFile Name="PKPM2PDMS" Path="pkpm2pdms.uic" />`；幂等。
  4  复制 dist\\PKPM2PDMS.dll、dist\\pkpm2pdms.uic 到 <PDMS根>。
  5  写 <PDMS根>\\PKPM2PDMS\\engine_path.txt（引擎入口绝对路径，UTF-8 无 BOM 单行）。
     〔R7〕**不再**往 <PDMS根>\\PKPM2PDMS\\pml\\ 复制任何 .pmlfnc（旧版这一步复制的是
     唯一化函数；该族已整体退役，见 RETIRED_PML）。
  6  复制 插件包\\pdms\\ 下**除退役族以外**的全部文件（.pmlfrm/.pmlfnc/.mac/.txt）到
     <PDMS根>\\PMLLIB\\pkpm2pdms\\，逐字节原样（PDMS 侧文件是 GBK 无 BOM + CRLF）。
     R6 起 PML 包一函数一文件：PMLLIB 的自动加载规则 = 文件名（忽略大小写）= 函数名，
     所以必须整目录搬过去、不能只搬几个入口文件；装完要重启 PDMS 重新索引。
     〔R7〕RETIRED_PML 列出的文件**不再部署**（工作树里仍保留，不删除）。
     （原文：验收\\实机日志_R4\\E_series.txt/F_series.txt/P7_export_1.txt；
       pdms\\README.txt「R6 运行入口与文件拆分」）

纪律：只加不删、幂等、可回滚（恢复用同目录 undeploy_pkpm2pdms.py）；
     两个 XML 用 utf-8-sig 读写并保留 BOM 与 CRLF（§p.6 实测两者均 UTF-8 带 BOM + CRLF）；
     PDMS 安装目录以外不落任何文件；引擎本体不复制进 PDMS 目录（engine_path.txt 指回工作区）。

用法：
  python deploy_pkpm2pdms.py                         # dry-run（缺省，只打印清单）
  python deploy_pkpm2pdms.py --execute               # 真正安装（PDMS 停机时！）
  python deploy_pkpm2pdms.py --pdms-root <DIR>       # 指向沙箱副本（验收 17 用）
  python deploy_pkpm2pdms.py --engine-entry <PATH>   # 显式指定引擎入口
"""
import argparse
import io
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent               # pdms-net/deploy/
PKG = HERE.parents[1]                                # PKPM2PDMS导入导出/
SRC = HERE.parent                                    # pdms-net/
DEFAULT_ROOT = Path(r"D:\AVEVA\Plant\PDMS12.1.SP4")

#: 〔R7〕**不再部署**的 PML 文件（逐条精确文件名，不用通配符 —— 安全红线 7）。
#: 退役族 = 运行期"重名唯一化 + 改名记录 + 运行入口"：改名责任已整体移交给
#: .NET 侧 SITE 名探测（SiteProber）+ 引擎生成期查重，宏里不再调用任何 PML 函数，
#: 故这些文件不再需要进 PDMS（工作树里仍保留，不删）。
RETIRED_PML = (
    "pkpm2pdmsuniquename.pmlfnc",        # 唯一化主函数
    "pkpm2pdmsrenamescount.pmlfnc",      # 改名记录条数（R6 从主函数拆出）
    "pkpm2pdmsrenamesfailcount.pmlfnc",  # FAIL 条数（同上）
    "pkpm2pdmsrenamesshow.pmlfnc",       # 改名清单 $P（同上）
    "pkpm2pdmsrunmac.pmlfnc",            # 运行入口函数（预载 + $M + 回传状态）
)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 动作种类（执行分支按此精确分发；kind 一律简单字符串，附注走 note 列）
K_BACKUP = "backup"            # a=原文件, b=.pkpm2pdms-bak
K_INS_ADDINS = "insert-addins"     # a=插入行, b=xml 路径
K_INS_CUST = "insert-cust"         # a=插入行, b=xml 路径
K_COPY = "copy"                # a=源, b=目标
K_WRITE = "write"              # a=engine 入口文本, b=engine_path.txt


def parse_args():
    p = argparse.ArgumentParser(description="deploy PKPM2PDMS addin（缺省 dry-run）")
    p.add_argument("--execute", action="store_true",
                   help="真正修改（缺省只打印清单，不落盘）")
    p.add_argument("--pdms-root", default=None, metavar="DIR",
                   help="PDMS 安装根（缺省 %s；测试可指向沙箱副本）" % DEFAULT_ROOT)
    p.add_argument("--engine-entry", default=None, metavar="PATH",
                   help="engine_path.txt 的内容（缺省依次取 engine/dist/pkpm2pdms_engine.exe、"
                        "run_engine.cmd）")
    return p.parse_args()


def backup_once(p: Path, acts):
    """§p.6 步骤 1；同 deploy_tgtext.py:21-26 的 backup_once（后缀改 .pkpm2pdms-bak）。"""
    bak = p.with_suffix(p.suffix + ".pkpm2pdms-bak")
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
    exe = PKG / "engine" / "dist" / "pkpm2pdms_engine.exe"
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
    dll = dist / "PKPM2PDMS.dll"
    uic_src = dist / "pkpm2pdms.uic"
    engine_entry, engine_ok = resolve_engine_entry(args.engine_entry)
    engine_flag = root / "PKPM2PDMS" / "engine_path.txt"

    # ---- 预检：目标与构建产物必须齐备 ----
    pre_fail = []
    for p in (addins, cust):
        if not p.exists():
            pre_fail.append("目标不是 PDMS 安装根？缺 %s" % p)
    for p in (dll, uic_src):
        if not p.exists():
            pre_fail.append("缺构建产物 %s（先在 pdms-net 下跑 build.cmd）" % p)
    # R6：PML 权威落点 = <PDMS根>\\PMLLIB\\pkpm2pdms\\（PMLLIB 自动加载只认这里；
    #      一函数一文件，文件名 = 函数名，见 pdms\\README.txt）
    # R7：退役族（RETIRED_PML）逐条排除，不进部署清单也不打印文件名（清单里 0 命中）。
    pml_src_dir = PKG / "pdms"
    pml_dst_dir = root / "PMLLIB" / "pkpm2pdms"
    pml_all, pml_retired = [], []
    if not pml_src_dir.is_dir():
        pre_fail.append("缺 PML 源目录 %s" % pml_src_dir)
    else:
        for p in sorted((q for q in pml_src_dir.iterdir() if q.is_file()),
                        key=lambda q: q.name.lower()):
            (pml_retired if p.name.lower() in RETIRED_PML else pml_all).append(p)
        if not pml_all:
            pre_fail.append("PML 源目录里没有可部署文件：%s" % pml_src_dir)

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
    if ">PKPM2PDMS<" in addins_text:                    # 幂等判据，同 deploy_tgtext.py:32
        acts.append((K_INS_ADDINS, "  <string>PKPM2PDMS</string>", str(addins), False,
                     "条目已存在，跳过"))
    else:
        acts.append((K_INS_ADDINS, "  <string>PKPM2PDMS</string>", str(addins), True,
                     "插到 </ArrayOfString> 之前"))
    if 'Path="pkpm2pdms.uic"' in cust_text:             # 幂等判据，同 deploy_tgtext.py:45
        acts.append((K_INS_CUST, '  <CustomizationFile Name="PKPM2PDMS" Path="pkpm2pdms.uic" />',
                     str(cust), False, "条目已存在，跳过"))
    else:
        acts.append((K_INS_CUST, '  <CustomizationFile Name="PKPM2PDMS" Path="pkpm2pdms.uic" />',
                     str(cust), True, "插到 </UICustomizationFiles> 之前"))

    acts.append((K_COPY, str(dll), str(root / "PKPM2PDMS.dll"), True, ""))
    acts.append((K_COPY, str(dist / "pkpm2pdms.uic"), str(root / "pkpm2pdms.uic"), True, ""))
    acts.append((K_WRITE, str(engine_entry), str(engine_flag), True,
                 "" if engine_ok else "注意：该引擎入口尚不存在（S9 未交付），仍按预期路径写入"))

    for src in pml_all:
        dst = pml_dst_dir / src.name
        acts.append((K_COPY, str(src), str(dst), True,
                     "覆盖" if dst.exists() else "新增"))

    # ---- 打印完整清单 ----
    print("=" * 72)
    print("deploy PKPM2PDMS -> %s" % root)
    print("PML：%s  ->  %s   （部署 %d 个文件，逐条列在下面；另有 %d 个退役文件不部署）"
          % (pml_src_dir, pml_dst_dir, len(pml_all), len(pml_retired)))
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
              "窗体执行前需补齐或设环境变量 PKPM2PDMS_ENGINE。")
    if pml_retired:
        print("说明：%d 个退役 PML 文件按 R7 方案不再部署（工作树内保留，未删除）。"
              % len(pml_retired))
    return 0


if __name__ == "__main__":
    sys.exit(main())
