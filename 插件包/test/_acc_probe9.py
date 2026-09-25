# -*- coding: utf-8 -*-
"""临时探针 9：pdms 包编码 + install.ps1 -DryRun。"""
import hashlib
import io
import os
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
PKG = r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出"
for name in sorted(os.listdir(os.path.join(PKG, 'pdms'))):
    p = os.path.join(PKG, 'pdms', name)
    if not os.path.isfile(p):
        continue
    b = open(p, 'rb').read()
    lone = sum(1 for i, ch in enumerate(b) if ch == 0x0A and (i == 0 or b[i - 1] != 0x0D))
    try:
        b.decode('gbk')
        gbk = 'ok'
    except Exception as e:
        gbk = 'FAIL %s' % e
    print("%-28s bytes=%-7d bom=%-5s loneLF=%-3d gbk=%s" % (name, len(b), b[:3] == b'\xef\xbb\xbf', lone, gbk))

uic = r"D:\AVEVA\Plant\PDMS12.1.SP4\design.uic"
h0 = hashlib.sha256(open(uic, 'rb').read()).hexdigest()
print("uic sha256 before:", h0)
ps = [r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe", "-NoProfile",
      "-ExecutionPolicy", "Bypass", "-File", os.path.join(PKG, "install", "install.ps1"), "-DryRun"]
p = subprocess.run(ps, capture_output=True)
print("exit:", p.returncode)
out = p.stdout.decode('gbk', 'replace')
print("stdout bytes:", len(p.stdout), "lines:", len(out.splitlines()))
print(out[:2500])
print("--- stderr ---")
print(p.stderr.decode('gbk', 'replace')[:1500])
h1 = hashlib.sha256(open(uic, 'rb').read()).hexdigest()
print("uic sha256 after :", h1, "unchanged:", h0 == h1)
