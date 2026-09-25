# -*- coding: utf-8 -*-
"""探针 R3-2：build.cmd 编译 + PE 解析 + PMLLIB 出处核对 + pkpmjwdrun.mac 预载 + 沙箱幂等/卸载。"""
import hashlib
import io
import os
import shutil
import subprocess
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = r"D:\AI_Work\PKPM数据解析"
PKG = os.path.join(ROOT, "PKPM-JWD导入导出")
OUT3 = os.path.join(PKG, "test", "_acc_r3_out")

# ---- 1) build.cmd
t0 = time.time()
p = subprocess.run([os.path.join(PKG, "pdms-net", "build.cmd")], capture_output=True, cwd=os.path.join(PKG, "pdms-net"))
print("build.cmd exit=%d  %.1fs" % (p.returncode, time.time() - t0))
print("stdout:", p.stdout.decode("gbk", "replace")[:300])
print("stderr:", p.stderr.decode("gbk", "replace")[:300])
dll = os.path.join(PKG, "pdms-net", "dist", "PKPMJWD.dll")
print("dll exists:", os.path.isfile(dll), os.path.getsize(dll) if os.path.isfile(dll) else -1)
b = open(dll, "rb").read()
print("literal v2.0.50727 in dll:", b"v2.0.50727" in b, "at", b.find(b"v2.0.50727"))
pe = int.from_bytes(b[0x3C:0x40], "little")
print("PE sig ok:", b[pe:pe + 4] == b"PE\x00\x00")
machine = int.from_bytes(b[pe + 4:pe + 6], "little")
nsec = int.from_bytes(b[pe + 6:pe + 8], "little")
opt_size = int.from_bytes(b[pe + 20:pe + 22], "little")
magic = int.from_bytes(b[pe + 24:pe + 26], "little")
print("machine=0x%x sections=%d optmagic=0x%x" % (machine, nsec, magic))
# CLI header（数据目录 14）
ddoff = pe + 24 + (96 if magic == 0x10B else 112)
cli_rva = int.from_bytes(b[ddoff + 14 * 8:ddoff + 14 * 8 + 4], "little")
cli_size = int.from_bytes(b[ddoff + 14 * 8 + 4:ddoff + 14 * 8 + 8], "little")
print("CLI dir rva=0x%x size=%d" % (cli_rva, cli_size))
# RVA -> file offset
sec0 = pe + 24 + opt_size
foff = None
for i in range(nsec):
    s = sec0 + i * 40
    va = int.from_bytes(b[s + 12:s + 16], "little")
    rawsz = int.from_bytes(b[s + 16:s + 20], "little")
    rawptr = int.from_bytes(b[s + 20:s + 24], "little")
    if va <= cli_rva < va + max(rawsz, 1):
        foff = rawptr + (cli_rva - va)
        break
print("CLI header file offset:", hex(foff) if foff else None)
if foff:
    rt_major = int.from_bytes(b[foff + 4:foff + 6], "little")
    rt_minor = int.from_bytes(b[foff + 6:foff + 8], "little")
    print("runtime version = %d.%d" % (rt_major, rt_minor))
tg = r"D:\AI_Work\pmds三维文字程序-备份\TGTEXT\TGTEXT.dll"
if os.path.isfile(tg):
    bt = open(tg, "rb").read()
    print("TGTEXT.dll literal:", b"v2.0.50727" in bt, "size", len(bt))

# ---- 2) PMLLIB 出处核对
PD = r"D:\AVEVA\Plant\PDMS12.1.SP4\PMLLIB"
checks = [
    (r"aba\Forms\abaarealib.pmlfrm", 100, 120, ["EXIST", "2,109"]),
    (r"assembly\functions\assybuildname.pmlfnc", 40, 80, ["EXIST", "FALSEA"]),
    (r"TIANGONG\functions\tgautonum.pmlfnc", 30, 45, ["EXIST"]),
    (r"aba\Forms\abaarea.pmlfrm", 518, 532, ["41,12"]),
    (r"Building_Design\pmllib\concrete_design\TRADUCTEUR\nucdesogwall.pmlobj", 200, 210, ["$M", "defined"]),
    (r"mypml\forms\GRIDDESIGN.pmlfrm", 980, 990, [".APPEND", ".string()"]),
]
for rel, a, z, needles in checks:
    pth = os.path.join(PD, rel.replace("/", os.sep))
    if not os.path.isfile(pth):
        print("MISSING", rel)
        continue
    lines = open(pth, "rb").read().decode("gbk", "replace").replace("\r\n", "\n").split("\n")
    seg = lines[a - 1:z]
    print("%s :%d-%d -> %s" % (rel, a, z,
          {n: any(n in l for l in seg) for n in needles}))

# ---- 3) pkpmjwdrun.mac 预载 + Addin 预载
run_mac = open(os.path.join(PKG, "pdms", "pkpmjwdrun.mac"), "rb").read().decode("gbk")
print("pkpmjwdrun.mac has $M uniquename:", "pkpmjwduniquename" in run_mac)
ad = open(os.path.join(PKG, "pdms-net", "PKPMJWDAddin.cs"), encoding="utf-8").read()
print("Addin preloads pmlfnc:", "pkpmjwduniquename" in ad, "| Start() has $M:", "$M" in ad)

# ---- 4) 沙箱幂等 + 卸载恢复
sand = os.path.join(OUT3, "sandbox_idem")
if os.path.isdir(sand):
    pass  # 不删除；直接覆盖写需要的文件
os.makedirs(sand, exist_ok=True)
open(os.path.join(sand, "DesignAddins.xml"), "wb").write(
    ('<?xml version="1.0"?>\r\n<ArrayOfString>\r\n  <string>TGTEXT</string>\r\n</ArrayOfString>\r\n').encode("utf-8-sig"))
open(os.path.join(sand, "DesignCustomization.xml"), "wb").write(
    ('<?xml version="1.0"?>\r\n<UICustomizationFiles>\r\n'
     '  <CustomizationFile Name="TGTEXT" Path="tgtext.uic" />\r\n</UICustomizationFiles>\r\n').encode("utf-8-sig"))
dep = [sys.executable, os.path.join(PKG, "pdms-net", "deploy", "deploy_pkpmjwd.py"),
       "--pdms-root", sand, "--engine-entry", r"C:\nonexistent\engine.exe"]
r1 = subprocess.run(dep + ["--execute"], capture_output=True)
print("deploy#1 exit", r1.returncode)
a1 = open(os.path.join(sand, "DesignAddins.xml"), "rb").read()
c1 = open(os.path.join(sand, "DesignCustomization.xml"), "rb").read()
print("after#1 addins BOM:", a1[:3] == b"\xef\xbb\xbf", "CRLF-only:", b"\n" not in a1.replace(b"\r\n", b""))
r2 = subprocess.run(dep + ["--execute"], capture_output=True)
print("deploy#2 exit", r2.returncode)
a2 = open(os.path.join(sand, "DesignAddins.xml"), "rb").read()
c2 = open(os.path.join(sand, "DesignCustomization.xml"), "rb").read()
print("idempotent:", a2 == a1 and c2 == c1, "| addins occurrences:", a2.count(b"PKPMJWD"))
d1 = subprocess.run([sys.executable, os.path.join(PKG, "pdms-net", "deploy", "undeploy_pkpmjwd.py"),
                     "--pdms-root", sand, "--execute"], capture_output=True)
print("undeploy exit", d1.returncode)
bak1 = open(os.path.join(sand, "DesignAddins.xml.pkpmjwd-bak"), "rb").read()
bak2 = open(os.path.join(sand, "DesignCustomization.xml.pkpmjwd-bak"), "rb").read()
now1 = open(os.path.join(sand, "DesignAddins.xml"), "rb").read()
now2 = open(os.path.join(sand, "DesignCustomization.xml"), "rb").read()
print("restore byte-equal:", now1 == bak1, now2 == bak2)
und = os.path.join(sand, "PKPMJWD")
moved = []
for dp, dn, fn in os.walk(und):
    for x in fn:
        moved.append(os.path.relpath(os.path.join(dp, x), und))
print("moved files:", moved)
print("root leftovers:", sorted(x for x in os.listdir(sand)))
