# -*- coding: utf-8 -*-
"""临时探针 4（验收测试编写用，跑完即删）：raw .pdt 事实 + 两样本坐标交叠。"""
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ENG = r"D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\engine"
sys.path.insert(0, ENG)
import jwd_read, pdt_read  # noqa: E402

PDT = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\1_PM.pdt"
JWD = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\JLCJ2.jwd"

raw = open(PDT, 'rb').read().decode('gbk')
lines = raw.replace('\r\n', '\n').replace('\r', '\n').split('\n')
print("pdt physical lines:", len(lines))
sec = None
counts = {}
nz = []
types = {}
for ln in lines:
    s = ln.strip()
    if s.startswith('$'):
        sec = s.split()[0]
        counts[sec] = counts.get(sec, 0) + 1
        continue
    if not s or s.startswith(';'):
        continue
    if sec == '$NODECOOR':
        m = re.search(r'Z=\s*(-?\d+(?:\.\d+)?)', s)
        if m:
            nz.append(float(m.group(1)))
    if sec == '$SETELEMENT':
        m = re.search(r'TYPE=\s*(\d+)', s)
        if m:
            types[m.group(1)] = types.get(m.group(1), 0) + 1
print("section header counts:", sorted(counts.items())[:20])
print("distinct node Z:", len(set(nz)), sorted(set(nz)))
print("$SETELEMENT TYPE distribution:", sorted(types.items()))
print("story lines:")
for ln in lines:
    if ln.strip().startswith('$STORY'):
        print("   ", ln.strip()[:200])

mj = jwd_read.read_jwd(JWD)
mp = pdt_read.read_pdt(PDT)
pj = {(round(m.start[0], 1), round(m.start[1], 1), round(m.start[2], 1)) for m in mj.members}
pp = {(round(m.start[0], 1), round(m.start[1], 1), round(m.start[2], 1)) for m in mp.members}
print("member start points: jwd=%d pdt=%d common=%d" % (len(pj), len(pp), len(pj & pp)))
xs_j = [p[0] for p in pj]; ys_j = [p[1] for p in pj]
xs_p = [p[0] for p in pp]; ys_p = [p[1] for p in pp]
print("jwd x range", min(xs_j), max(xs_j), " pdt x range", min(xs_p), max(xs_p))
print("jwd y range", min(ys_j), max(ys_j), " pdt y range", min(ys_p), max(ys_p))
print("jwd level tops:", sorted(l.z_top for l in mj.levels))
print("pdt level z set:", sorted(l.z_bot for l in mp.levels))
print("intersection:", sorted(set(l.z_top for l in mj.levels) & set(l.z_bot for l in mp.levels)))
print("pdt section count:", len(mp.sections), "jwd:", len(mj.sections))
