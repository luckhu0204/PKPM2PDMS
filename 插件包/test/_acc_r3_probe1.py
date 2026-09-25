# -*- coding: utf-8 -*-
"""探针 R3-1：基准快照成本 + 交付目录 + docs 声明 + deploy dry-run + 宏唯一化计数。"""
import io
import os
import subprocess
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = r"D:\AI_Work\PKPM数据解析"
PKG = os.path.join(ROOT, "PKPM-JWD导入导出")

t0 = time.time()
tot = n = 0
root = r"D:\AVEVA\Plant\PDMS12.1.SP4"
for name in os.listdir(root):
    p = os.path.join(root, name)
    if os.path.isfile(p):
        tot += os.path.getsize(p)
        n += 1
print("AVEVA root files", n, "bytes", tot)
tot = n = 0
root = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
for dp, dn, fn in os.walk(root):
    for x in fn:
        tot += os.path.getsize(os.path.join(dp, x))
        n += 1
print("G plugin files", n, "bytes", tot, "walk %.1fs" % (time.time() - t0))

# hashing timing on AVEVA root
t0 = time.time()
h = 0
for name in os.listdir(root):
    p = os.path.join(root, name)
    if os.path.isfile(p):
        d = hashlib_sha = __import__("hashlib").sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                d.update(chunk)
        h += 1
print("hashed %d AVEVA files in %.1fs" % (h, time.time() - t0))

print("== delivery dir ==")
dd = os.path.join(ROOT, "交付_PKPM-JWD插件")
for dp, dn, fn in os.walk(dd):
    rel = os.path.relpath(dp, dd)
    for x in fn[:3] if len(fn) > 3 else fn:
        print("   ", os.path.join(rel, x))
    if len(fn) > 3:
        print("    ... (%d files in %s)" % (len(fn), rel))
    dn[:] = [d for d in dn if d not in ("__pycache__", "_pybuild")]

print("== docs 未部署声明 ==")
for name in ("交付清单.md", "使用说明.md", "交付报告.md"):
    p = os.path.join(PKG, "docs", name)
    if os.path.isfile(p):
        t = open(p, encoding="utf-8", errors="replace").read()
        hits = [k for k in ("未部署", "不部署", "未安装", "没有部署", "未生效")
                if k in t]
        print("   docs/%s: 关键词 %s" % (name, hits))

print("== deploy dry-run（沙箱）==")
sand = os.path.join(PKG, "test", "_acc_r3_out", "sandbox")
os.makedirs(sand, exist_ok=True)
# 造两个 XML（与真实文件同构的最小形状）
open(os.path.join(sand, "DesignAddins.xml"), "w", encoding="utf-8-sig", newline="").write(
    '<?xml version="1.0"?>\r\n<ArrayOfString>\r\n  <string>TGTEXT</string>\r\n</ArrayOfString>\r\n')
open(os.path.join(sand, "DesignCustomization.xml"), "w", encoding="utf-8-sig", newline="").write(
    '<?xml version="1.0"?>\r\n<UICustomizationFiles>\r\n'
    '  <CustomizationFile Name="TGTEXT" Path="tgtext.uic" />\r\n</UICustomizationFiles>\r\n')
p = subprocess.run([sys.executable, os.path.join(PKG, "pdms-net", "deploy", "deploy_pkpmjwd.py"),
                    "--pdms-root", sand], capture_output=True)
print("dry-run exit", p.returncode)
print(p.stdout.decode("utf-8", "replace")[:2600])

print("== 生成宏并数唯一化调用 ==")
OUTR3 = os.path.join(PKG, "test", "_acc_r3_out")
p = subprocess.run([sys.executable, os.path.join(PKG, "engine", "cli.py"), "jwd2pdms",
                    r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\JLCJ2.jwd",
                    "--out", os.path.join(OUTR3, "r3.mac"),
                    "--report", os.path.join(OUTR3, "r3.report.json")], capture_output=True)
print("jwd2pdms exit", p.returncode)
t = open(os.path.join(OUTR3, "r3.mac"), "rb").read().decode("gbk")
lines = t.split("\r\n")
print("calls !!pkpmjwdUniquename =", sum(1 for l in lines if "!!pkpmjwdUniquename('" in l))
print("NEW lines =", sum(1 for l in lines if l.strip().startswith("NEW ")))
print("literal NEW (not $!n) =", sum(1 for l in lines if l.strip().startswith("NEW ") and "$!n" not in l))
print("has ONERROR:", any("ONERROR GOLABEL /PKPMJWDERR" in l for l in lines))
print("has LABEL tail:", any(l.strip() == "LABEL /PKPMJWDERR" for l in lines))
print("has $M:", any(l.strip().startswith("$M") for l in lines))
print("func-missing guard:", any("defined(!!pkpmjwdUniquename)" in l for l in lines))
