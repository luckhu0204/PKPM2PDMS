# -*- coding: utf-8 -*-
"""Final encoding audit for pdms-net deliverables (contract g / p.2 / F.3)."""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parents[1]

CS = ["PKPM2PDMSAddin.cs", "PKPM2PDMSForm.cs", "PmlBridge.cs", "SiteProber.cs",
      "EngineRunner.cs", "PKLog.cs", "AssemblyInfo.cs"]
PY = ["deploy/deploy_pkpm2pdms.py", "deploy/undeploy_pkpm2pdms.py",
      "_selftest/read_gbk.py", "_selftest/write_static.py",
      "_selftest/sandbox_test.py", "_selftest/audit_files.py"]

fails = []
for f in CS + PY + ["README.txt", "pkpm2pdms.uic"]:
    p = HERE / f
    b = p.read_bytes()
    bom = b[:3] == b"\xef\xbb\xbf"
    try:
        b.decode("utf-8")
        utf8 = True
    except UnicodeDecodeError:
        utf8 = False
    ok = utf8 and not bom
    print("%-40s %7d B  UTF-8:%s  BOM:%s  CRLF:%4d" %
          (f, len(b), "yes" if utf8 else "NO!", bom, b.count(b"\r\n")))
    if not ok:
        fails.append(f)

bc = (HERE / "build.cmd").read_bytes()
print("%-40s %7d B  ASCII:%s  CRLF:%d/%d" % ("build.cmd", len(bc),
      "yes" if all(c < 128 for c in bc) else "NO!",
      bc.count(b"\r\n"), bc.count(b"\n")))
if not all(c < 128 for c in bc) or bc.count(b"\r\n") != bc.count(b"\n"):
    fails.append("build.cmd")

u1 = (HERE / "pkpm2pdms.uic").read_bytes()
u2 = (HERE / "dist/pkpm2pdms.uic").read_bytes()
print("pkpm2pdms.uic == dist/pkpm2pdms.uic:", u1 == u2)
if u1 != u2:
    fails.append("uic copy drift")

d = (HERE / "dist/PKPM2PDMS.dll").stat()
print("dist/PKPM2PDMS.dll:", d.st_size, "bytes, mtime", d.st_mtime)
if d.st_size <= 0:
    fails.append("dll missing")

# assembly / plugin version (RENAME_MAP §4.2/§4.4): 2.1.0.0 / 2.1.0, NEVER 1.0-as-plugin
ai = (HERE / "AssemblyInfo.cs").read_text(encoding="utf-8")
for key in ('AssemblyVersion("2.1.0.0")', 'AssemblyFileVersion("2.1.0.0")',
            'AssemblyInformationalVersion("2.1.0")'):
    if key not in ai:
        fails.append("AssemblyInfo " + key)
print("AssemblyInfo version attributes (2.1.0.0 / 2.1.0):",
      all(k in ai for k in ('AssemblyVersion("2.1.0.0")',
                            'AssemblyFileVersion("2.1.0.0")',
                            'AssemblyInformationalVersion("2.1.0")')))

# key strings that must exist (acceptance 18-2 control names, 16 keys)
form = (HERE / "PKPM2PDMSForm.cs").read_text(encoding="utf-8")
need = ["cmbOp", "txtSource", "btnBrowseSource", "txtSecmap", "btnBrowseSecmap",
        "chkUseExtra", "txtExtra", "numBaseE", "numBaseN", "numBaseU", "numAngle",
        "cmbUnit", "chkColumn", "chkBeam", "chkHBrace", "chkVBrace", "chkSlab",
        "chkWall", "chkGrid", "chkHole", "txtOut", "btnBrowseOut", "btnRun",
        "progressBar1", "txtSummary", "btnOpenReport"]
missing = [n for n in need if n not in form]
print("form control names present:", "ALL" if not missing else missing)
if missing:
    fails.append("controls")

addin = (HERE / "PKPM2PDMSAddin.cs").read_text(encoding="utf-8")
for key in ['"PKPM2PDMS"', '"PKPM2PDMS.OpenTools"']:
    if key not in addin:
        fails.append("addin key " + key)
uic = u1.decode("utf-8")
for key in ("PKPM2PDMS.Open", "PKPM2PDMS.OpenTools", "PKPM2PDMS.Menu"):
    if key not in uic:
        fails.append("uic key " + key)
print("Key consistency (.uic / Addin / Command):",
      all(k in uic for k in ("PKPM2PDMS.OpenTools",)) and '"PKPM2PDMS.OpenTools"' in addin)

print("FAILS:", len(fails), fails)
sys.exit(0 if not fails else 1)
