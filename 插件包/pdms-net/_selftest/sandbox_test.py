# -*- coding: utf-8 -*-
"""Sandbox test for deploy/undeploy (acceptance 17): never touches real D:\AVEVA.

Steps:
  1. build sandbox in %TEMP%\\pkpmjwd_sandbox: copy REAL DesignAddins.xml /
     DesignCustomization.xml from D:\\AVEVA (read-only source), fake pmlfnc source.
  2. deploy dry-run (default) -> expect 8 planned actions, no writes.
  3. deploy --execute -> entries inserted, BOM+CRLF kept, files in place.
  4. deploy --execute again -> all inserts skipped (idempotent), count still 1.
  5. undeploy dry-run -> restore 2 + move 4, no "delete" wording.
  6. undeploy --execute -> XML byte-equal to .pkpmjwd-bak; 4 files moved to
     _uninstalled_*; backup files kept.
"""
import io
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "deploy_pkpmjwd.py"
UNDEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "undeploy_pkpmjwd.py"
SB = Path(__file__).resolve().parents[1] / "_selftest" / "_sandbox"
PDMS = Path(r"D:\AVEVA\Plant\PDMS12.1.SP4")
FAILS = []


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
    srcdir = SB.parent / "_sandbox_src"
    srcdir.mkdir(exist_ok=True)
    pmlfnc = srcdir / "pkpmjwduniquename.pmlfnc"
    pmlfnc.write_bytes("-- fake pmlfnc for sandbox test\r\n".encode("gbk"))
    fake_engine = srcdir / "fake_engine.exe"
    fake_engine.write_bytes(b"MZ fake")

    addins = SB / "DesignAddins.xml"
    cust = SB / "DesignCustomization.xml"
    a0, c0 = addins.read_bytes(), cust.read_bytes()

    print("== step 2: deploy dry-run (default) ==")
    code, out = run(DEPLOY, "--pdms-root", str(SB), "--engine-entry", str(fake_engine),
                    "--pmlfnc", str(pmlfnc))
    print(out)
    check("dry-run exit 0", code == 0)
    check("dry-run prints 8 DO items", out.count("[DO ]") == 8 or out.count("[DO  ]") == 8,
          "DO=%d" % out.count("[DO"))
    check("dry-run: no write", addins.read_bytes() == a0 and cust.read_bytes() == c0)
    check("dry-run: no delete wording", ("删除" not in out) and ("DELETE" not in out.upper()))

    print("== step 3: deploy --execute ==")
    code, out = run(DEPLOY, "--pdms-root", str(SB), "--execute", "--engine-entry",
                    str(fake_engine), "--pmlfnc", str(pmlfnc))
    print(out)
    check("execute exit 0", code == 0)
    at, ct = addins.read_text(encoding="utf-8-sig"), cust.read_text(encoding="utf-8-sig")
    check("addins has PKPMJWD entry", "<string>PKPMJWD</string>" in at)
    check("addins entry count == 1", at.count("<string>PKPMJWD</string>") == 1)
    check("cust has CustomizationFile", 'Name="PKPMJWD" Path="pkpmjwd.uic"' in ct)
    check("cust entry count == 1", ct.count('Name="PKPMJWD"') == 1)
    ab, cb = addins.read_bytes(), cust.read_bytes()
    check("BOM kept (addins/cust)", ab[:3] == b"\xef\xbb\xbf" and cb[:3] == b"\xef\xbb\xbf")
    check("CRLF kept & grew by 1 line", crlf_count(ab) == crlf_count(a0) + 1
          and crlf_count(cb) == crlf_count(c0) + 1,
          "addins %d->%d, cust %d->%d" % (crlf_count(a0), crlf_count(ab),
                                          crlf_count(c0), crlf_count(cb)))
    check("DLL copied", (SB / "PKPMJWD.dll").exists())
    check("uic copied", (SB / "pkpmjwd.uic").exists())
    check("engine_path.txt written",
          (SB / "PKPMJWD" / "engine_path.txt").read_text(encoding="utf-8").strip()
          == str(fake_engine))
    ep = (SB / "PKPMJWD" / "engine_path.txt").read_bytes()
    check("engine_path.txt no BOM", ep[:3] != b"\xef\xbb\xbf")
    check("pmlfnc copied", (SB / "PKPMJWD" / "pml" / "pkpmjwduniquename.pmlfnc")
          .read_bytes() == pmlfnc.read_bytes())
    check("backups created", (SB / "DesignAddins.xml.pkpmjwd-bak").exists()
          and (SB / "DesignCustomization.xml.pkpmjwd-bak").exists())
    bak_a = (SB / "DesignAddins.xml.pkpmjwd-bak").read_bytes()
    check("backup == pre-install bytes", bak_a == a0)

    print("== step 4: deploy --execute again (idempotent) ==")
    code, out = run(DEPLOY, "--pdms-root", str(SB), "--execute", "--engine-entry",
                    str(fake_engine), "--pmlfnc", str(pmlfnc))
    print(out)
    check("2nd execute exit 0", code == 0)
    check("2nd execute: inserts skipped", out.count("skip") >= 2, "skip=%d" % out.count("skip"))
    at2 = addins.read_text(encoding="utf-8-sig")
    check("entry count still 1", at2.count("<string>PKPMJWD</string>") == 1)
    check("bytes unchanged by 2nd run (XML)",
          addins.read_bytes() == ab and cust.read_bytes() == cb)

    print("== step 5: undeploy dry-run ==")
    code, out = run(UNDEPLOY, "--pdms-root", str(SB))
    print(out)
    check("undeploy dry-run exit 0", code == 0)
    check("undeploy: 2 restore + 4 move planned",
          out.count("restore") >= 2 and out.count("move") >= 4)
    check("undeploy: no delete wording", "删除" not in out)

    print("== step 6: undeploy --execute ==")
    code, out = run(UNDEPLOY, "--pdms-root", str(SB), "--execute")
    print(out)
    check("undeploy execute exit 0", code == 0)
    check("XML restored byte-equal to backup",
          addins.read_bytes() == bak_a
          and cust.read_bytes() == (SB / "DesignCustomization.xml.pkpmjwd-bak").read_bytes())
    undirs = list((SB / "PKPMJWD").glob("_uninstalled_*"))
    check("_uninstalled_* created", len(undirs) == 1, str(undirs))
    if undirs:
        moved = sorted(p.name for p in undirs[0].iterdir())
        check("4 installed files moved", moved ==
              ["PKPMJWD.dll", "engine_path.txt", "pkpmjwd.uic",
               "pkpmjwduniquename.pmlfnc"], str(moved))
    check("backup files kept (not deleted)",
          (SB / "DesignAddins.xml.pkpmjwd-bak").exists()
          and (SB / "DesignCustomization.xml.pkpmjwd-bak").exists())

    print("== step 7: undeploy --execute again (idempotent) ==")
    code, out = run(UNDEPLOY, "--pdms-root", str(SB), "--execute")
    check("2nd undeploy exit 0", code == 0)
    check("2nd undeploy: 4 moves skipped (backups kept -> 2 restores re-run harmlessly)",
          out.count("[skip") == 4, "skip=%d" % out.count("[skip"))
    check("2nd undeploy: XML bytes still == backup",
          addins.read_bytes() == bak_a
          and cust.read_bytes() == (SB / "DesignCustomization.xml.pkpmjwd-bak").read_bytes())

    print("=" * 60)
    print("FAILS:", len(FAILS), FAILS)
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
