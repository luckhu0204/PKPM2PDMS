# -*- coding: utf-8 -*-
"""Sandbox test for deploy/undeploy (acceptance 17): never touches real D:\\AVEVA.

〔R7 更新（2026-09-28）〕deploy 清单随命名方案改造而变化，本脚本同步改写对照：
  * DO 项 = 1~2 备份 + 2 插入(XML) + 2 复制(DLL/uic) + 1 写(engine_path.txt) + N 个 PML 文件；
  * **退役族**（唯一化 / 改名记录 / 运行入口；deploy 脚本的 RETIRED_PML 逐条列出）不部署、
    不出现在清单里 —— 只按"逐条精确文件名"排除，不用通配符（安全红线 7）。

Steps:
  1. build sandbox in _selftest\\_sandbox: copy REAL DesignAddins.xml /
     DesignCustomization.xml from D:\\AVEVA (read-only source).
  2. deploy dry-run (default) -> planned actions as above, no writes,
     no retired-file name in the printed list.
  3. deploy --execute -> entries inserted, BOM+CRLF kept, files in place,
     retired files NOT created.
  4. deploy --execute again -> all inserts skipped (idempotent), count still 1.
  5. undeploy dry-run -> restores + moves planned, no "delete" wording.
  6. undeploy --execute -> XML byte-equal to .pkpm2pdms-bak; deployed files moved to
     _uninstalled_*; backup files kept.
  7. undeploy --execute again -> moves skipped (idempotent).
"""
import io
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PKG = Path(__file__).resolve().parents[2]                    # 插件包/
DEPLOY = PKG / "pdms-net" / "deploy" / "deploy_pkpm2pdms.py"
UNDEPLOY = PKG / "pdms-net" / "deploy" / "undeploy_pkpm2pdms.py"
SB = PKG / "pdms-net" / "_selftest" / "_sandbox"
PDMS = Path(r"D:\AVEVA\Plant\PDMS12.1.SP4")
FAILS = []

#: 〔R7〕退役族（与 deploy/undeploy 脚本里的 RETIRED_PML 同一份清单，测试独立抄一份：
#: 若两边不一致，本脚本的断言就会失败 —— 这正是要守的东西）
RETIRED = (
    "pkpm2pdmsuniquename.pmlfnc",
    "pkpm2pdmsrenamescount.pmlfnc",
    "pkpm2pdmsrenamesfailcount.pmlfnc",
    "pkpm2pdmsrenamesshow.pmlfnc",
    "pkpm2pdmsrunmac.pmlfnc",
)

#: 应部署的 PML 文件（源目录 插件包\\pdms\\ 下除退役族以外的全部文件）
PML_FILES = sorted(p.name for p in (PKG / "pdms").iterdir()
                   if p.is_file() and p.name.lower() not in RETIRED)


def run(script, *extra):
    cmd = [sys.executable, str(script)] + list(extra)
    r = subprocess.run(cmd, capture_output=True)
    out = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
    return r.returncode, out


def check(name, cond, detail=""):
    print("  [%s] %s %s" % ("OK" if cond else "FAIL", name, detail))
    if not cond:
        FAILS.append(name)


def crlf_count(b):
    return b.count(b"\r\n")


def main():
    # ---- 1. sandbox ----
    if SB.exists():
        print("[note] sandbox exists, reuse:", SB)
    else:
        SB.mkdir(parents=True)
    shutil.copy2(PDMS / "DesignAddins.xml", SB / "DesignAddins.xml")
    shutil.copy2(PDMS / "DesignCustomization.xml", SB / "DesignCustomization.xml")
    fake_engine = SB.parent / "_sandbox_src" / "fake_engine.exe"
    if not fake_engine.exists():
        fake_engine.write_bytes(b"MZ fake")

    addins = SB / "DesignAddins.xml"
    cust = SB / "DesignCustomization.xml"
    a0, c0 = addins.read_bytes(), cust.read_bytes()
    # 沙箱源是从真实 D:\\AVEVA 逐字节复制的只读副本；那里**可能已经装着**本插件
    # （本机 2026-09-28 就装着），所以"插入条目"这一步在两种源状态下都算通过：
    # 源里已有条目 ⇒ 幂等跳过；源里没有 ⇒ 插一行、CRLF 恰 +1。
    has_addins = ">PKPM2PDMS<" in a0.decode("utf-8-sig")
    has_cust = 'Path="pkpm2pdms.uic"' in c0.decode("utf-8-sig")
    exp_ins_a, exp_ins_c = (0 if has_addins else 1), (0 if has_cust else 1)
    bak_addins = SB / "DesignAddins.xml.pkpm2pdms-bak"
    bak_cust = SB / "DesignCustomization.xml.pkpm2pdms-bak"
    had_bak = bak_addins.exists() and bak_cust.exists()
    pml_dir = SB / "PMLLIB" / "pkpm2pdms"
    n_pml = len(PML_FILES)

    print("== step 2: deploy dry-run (default) ==")
    code, out = run(DEPLOY, "--pdms-root", str(SB), "--engine-entry", str(fake_engine))
    print(out)
    check("dry-run exit 0", code == 0)
    # 备份是"只备一次"：全新沙箱会 DO，已备过的沙箱会 skip —— 两种都接受，其余项必须齐全
    n_bak = out.count("[DO  ] backup")
    check("dry-run: backups planned 0 or 2", n_bak in (0, 2), "backup DO=%d" % n_bak)
    check("dry-run: inserts+copy+write planned",
          out.count("[DO  ] insert-addins") == exp_ins_a
          and out.count("[DO  ] insert-cust") == exp_ins_c
          and out.count("[DO  ] copy") == 2 + n_pml
          and out.count("[DO  ] write") == 1,
          "DO total=%d (expect %d)"
          % (out.count("[DO  ]"), n_bak + exp_ins_a + exp_ins_c + 3 + n_pml))
    check("dry-run: 退役族 0 命中（清单里不出现这些文件名）",
          all(name.lower() not in out.lower() for name in RETIRED))
    check("dry-run: PML 部署数 = %d" % n_pml,
          ("部署 %d 个文件" % n_pml) in out and ("%d 个退役文件不部署" % len(RETIRED)) in out)
    check("dry-run: no write", addins.read_bytes() == a0 and cust.read_bytes() == c0)
    check("dry-run: no delete wording", ("删除" not in out) and ("DELETE" not in out.upper()))

    print("== step 3: deploy --execute ==")
    code, out = run(DEPLOY, "--pdms-root", str(SB), "--execute", "--engine-entry",
                    str(fake_engine))
    print(out)
    check("execute exit 0", code == 0)
    at, ct = addins.read_text(encoding="utf-8-sig"), cust.read_text(encoding="utf-8-sig")
    check("addins has PKPM2PDMS entry", "<string>PKPM2PDMS</string>" in at)
    check("addins entry count == 1", at.count("<string>PKPM2PDMS</string>") == 1)
    check("cust has CustomizationFile", 'Name="PKPM2PDMS" Path="pkpm2pdms.uic"' in ct)
    check("cust entry count == 1", ct.count('Name="PKPM2PDMS"') == 1)
    ab, cb = addins.read_bytes(), cust.read_bytes()
    check("BOM kept (addins/cust)", ab[:3] == b"\xef\xbb\xbf" and cb[:3] == b"\xef\xbb\xbf")
    check("CRLF kept & grew by the inserted lines",
          crlf_count(ab) == crlf_count(a0) + exp_ins_a
          and crlf_count(cb) == crlf_count(c0) + exp_ins_c,
          "addins %d->%d, cust %d->%d" % (crlf_count(a0), crlf_count(ab),
                                          crlf_count(c0), crlf_count(cb)))
    check("DLL copied", (SB / "PKPM2PDMS.dll").exists())
    check("uic copied", (SB / "pkpm2pdms.uic").exists())
    check("engine_path.txt written",
          (SB / "PKPM2PDMS" / "engine_path.txt").read_text(encoding="utf-8").strip()
          == str(fake_engine))
    ep = (SB / "PKPM2PDMS" / "engine_path.txt").read_bytes()
    check("engine_path.txt no BOM", ep[:3] != b"\xef\xbb\xbf")
    check("PML 文件逐个到位（%d 个，逐字节相同）" % n_pml,
          all((pml_dir / name).exists()
              and (pml_dir / name).read_bytes() == (PKG / "pdms" / name).read_bytes()
              for name in PML_FILES))
    missing = [name for name in RETIRED if (pml_dir / name).exists()]
    check("退役族未被部署到 PMLLIB", not missing, str(missing))
    check("退役族未被写到 <root>\\PKPM2PDMS\\pml\\",
          not (SB / "PKPM2PDMS" / "pml").exists())
    check("backups exist", bak_addins.exists() and bak_cust.exists())
    if not had_bak:
        # 本运行刚建的备份必须等于改动前的字节（只备一次 ⇒ 已有备份时不重写，故不比对）
        check("backup == pre-install bytes", bak_addins.read_bytes() == a0)
    bak_a = bak_addins.read_bytes()

    print("== step 4: deploy --execute again (idempotent) ==")
    code, out = run(DEPLOY, "--pdms-root", str(SB), "--execute", "--engine-entry",
                    str(fake_engine))
    print(out)
    check("2nd execute exit 0", code == 0)
    check("2nd execute: inserts skipped", out.count("skip") >= 2, "skip=%d" % out.count("skip"))
    at2 = addins.read_text(encoding="utf-8-sig")
    check("entry count still 1", at2.count("<string>PKPM2PDMS</string>") == 1)
    check("bytes unchanged by 2nd run (XML)",
          addins.read_bytes() == ab and cust.read_bytes() == cb)

    exp_moves = 3 + n_pml          # dll + uic + engine_path.txt + 全部 PML 文件
    print("== step 5: undeploy dry-run ==")
    code, out = run(UNDEPLOY, "--pdms-root", str(SB))
    print(out)
    check("undeploy dry-run exit 0", code == 0)
    check("undeploy: 2 restore + %d move planned" % exp_moves,
          out.count("restore") >= 2 and out.count("move") >= exp_moves,
          "move=%d" % out.count("move"))
    check("undeploy: 退役族 0 命中", all(name.lower() not in out.lower() for name in RETIRED))
    check("undeploy: no delete wording", "删除" not in out)

    print("== step 6: undeploy --execute ==")
    code, out = run(UNDEPLOY, "--pdms-root", str(SB), "--execute")
    print(out)
    check("undeploy execute exit 0", code == 0)
    check("XML restored byte-equal to backup",
          addins.read_bytes() == bak_a
          and cust.read_bytes() == (SB / "DesignCustomization.xml.pkpm2pdms-bak").read_bytes())
    undirs = sorted((SB / "PKPM2PDMS").glob("_uninstalled_*"))
    check("_uninstalled_* created", len(undirs) >= 1, str(undirs))
    if undirs:
        moved = sorted(p.name for p in undirs[-1].iterdir())     # 最新一个（名字 = 时间戳）
        want = sorted(["PKPM2PDMS.dll", "pkpm2pdms.uic", "engine_path.txt"] + PML_FILES)
        check("%d 个已装文件移入最新 _uninstalled_*" % exp_moves, moved == want, str(moved))
    check("backup files kept (not deleted)",
          (SB / "DesignAddins.xml.pkpm2pdms-bak").exists()
          and (SB / "DesignCustomization.xml.pkpm2pdms-bak").exists())

    print("== step 7: undeploy --execute again (idempotent) ==")
    code, out = run(UNDEPLOY, "--pdms-root", str(SB), "--execute")
    print(out)
    check("2nd undeploy exit 0", code == 0)
    check("2nd undeploy: moves skipped (%d)" % exp_moves,
          out.count("[skip") == exp_moves, "skip=%d" % out.count("[skip"))
    check("2nd undeploy: XML bytes still == backup",
          addins.read_bytes() == bak_a
          and cust.read_bytes() == (SB / "DesignCustomization.xml.pkpm2pdms-bak").read_bytes())

    print("=" * 60)
    print("FAILS:", len(FAILS), FAILS)
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
