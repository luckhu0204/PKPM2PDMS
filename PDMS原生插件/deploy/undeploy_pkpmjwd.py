# -*- coding: utf-8 -*-
"""uninstall PKPMJWD addin from PDMS 12.1 SP4 (CONTRACT §p.6 卸载行).

**本脚本属于交付物；本轮绝不执行（契约 §p.10-1）。**
卸载必须由用户在 PDMS **停机** 时自行执行（见 ../README.txt）。

卸载策略（§p.6 冻结：**恢复优先**，比 TGTEXT 的"删条目+unlink"更符合安全红线 3——
用移动代替删除，全脚本没有任何删除动作）：

  1  从 <root>\\DesignAddins.xml.pkpmjwd-bak / DesignCustomization.xml.pkpmjwd-bak
     复原两个 XML（恢复后两 XML 与备份逐字节相等，验收 17-③）。
  2  把安装的 4 个文件**移动**到 <root>\\PKPMJWD\\_uninstalled_<时间戳>\\（不删除）：
        <root>\\PKPMJWD.dll
        <root>\\pkpmjwd.uic
        <root>\\PKPMJWD\\engine_path.txt
        <root>\\PKPMJWD\\pml\\pkpmjwduniquename.pmlfnc
  3  .pkpmjwd-bak 备份文件保留（不删，便于再次核对/人工回滚）。

缺省 dry-run：只打印"将要改变的全部对象"完整清单；--execute 才真正修改。
--pdms-root 可指向沙箱副本（验收 17 用）。
"""
import argparse
import io
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = Path(r"D:\AVEVA\Plant\PDMS12.1.SP4")

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

INSTALLED = ("PKPMJWD.dll", "pkpmjwd.uic",
             r"PKPMJWD\engine_path.txt", r"PKPMJWD\pml\pkpmjwduniquename.pmlfnc")


def main():
    p = argparse.ArgumentParser(description="undeploy PKPMJWD addin（缺省 dry-run；恢复+移动，无任何删除）")
    p.add_argument("--execute", action="store_true", help="真正修改（缺省只打印清单）")
    p.add_argument("--pdms-root", default=None, metavar="DIR",
                   help="PDMS 安装根（缺省 %s；测试可指向沙箱副本）" % DEFAULT_ROOT)
    args = p.parse_args()
    root = Path(args.pdms_root) if args.pdms_root else DEFAULT_ROOT

    stamp = time.strftime("%Y%m%d-%H%M%S")
    undir = root / "PKPMJWD" / ("_uninstalled_" + stamp)

    # ---- 组清单：将要改变的全部对象（红线 6/8） ----
    acts = []
    for name in ("DesignAddins.xml", "DesignCustomization.xml"):
        xml = root / name
        bak = root / (name + ".pkpmjwd-bak")
        if bak.exists():
            acts.append(("restore", str(bak), str(xml), True, "恢复到安装前状态（逐字节）"))
        else:
            acts.append(("restore", str(bak), str(xml), False,
                         "跳过：无备份（未装过或已卸过）；如需人工回滚请对照包内说明"))
    for rel in INSTALLED:
        f = root / rel
        if f.exists():
            acts.append(("move", str(f), str(undir / f.name), True,
                         "移动到 _uninstalled_*（原文件保留，可随时人工取回）"))
        else:
            acts.append(("move", str(f), str(undir / f.name), False, "跳过：文件不存在"))

    print("=" * 72)
    print("undeploy PKPMJWD <- %s" % root)
    print("模式：%s" % ("EXECUTE（将真正修改）" if args.execute
                        else "DRY-RUN（不落盘；加 --execute 才修改）"))
    print("将要改变的全部对象（%d 项）：" % len(acts))
    for kind, a, b, will, note in acts:
        print("  [%s] %-7s %s" % ("DO  " if will else "skip", kind, a))
        print("        -> %s" % b)
        if note:
            print("        %s" % note)
    print("=" * 72)

    if not args.execute:
        print("DRY-RUN 完成：未写入任何文件。确认清单无误后加 --execute 执行（PDMS 停机时）。")
        return 0

    done = 0
    for kind, a, b, will, note in acts:
        if not will:
            continue
        if kind == "restore":
            shutil.copy2(a, b)          # 备份 -> 原位，逐字节恢复
        elif kind == "move":
            Path(b).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(a, b)           # 移动，绝不 unlink
        done += 1
    print("EXECUTE 完成：%d 项改动。被移动的文件保留在 %s（可人工核对后处理）。" % (done, undir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
