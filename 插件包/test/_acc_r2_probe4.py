# -*- coding: utf-8 -*-
"""临时探针 R2-4：独立重算目录宏解析/交叉一致率/大小写差异（自带解析，不用 engine）。"""
import collections
import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
S = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
DB = os.path.join(S, "PKPM（PDMS数据库）.txt")
MAP = os.path.join(S, "PKPM转PDMS截面匹配文件.txt")
DLL = os.path.join(S, "P-TRANS", "PDMSxCA_Addin121.dll")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_acc_r2_out")

# ---- 1) 目录宏（自己的解析：$ 续行合并 + 只认 NEW SPCOMPONENT/SPRFILE）
raw = open(DB, "rb").read()
text = raw.decode("utf-8-sig")
print("macro bytes=%d bom=%s" % (len(raw), raw[:3] == b"\xef\xbb\xbf"))
lines = text.replace("\r\n", "\n").split("\n")
logical, buf = [], ""
for ln in lines:
    s = ln.rstrip()
    if s.endswith("$"):
        buf += s[:-1] + " "
        continue
    logical.append((buf + s).strip())
    buf = ""
if buf:
    logical.append(buf.strip())
spc = [l.split(None, 2)[2] for l in logical if l.startswith("NEW SPCOMPONENT")]
spr = [l.split(None, 2)[2] for l in logical if l.startswith("NEW SPRFILE")]
old_spc = [l.split(None, 2)[2] for l in logical if l.startswith("OLD SPCOMPONENT")]
cat = [l.split(None, 2)[2] for l in logical if l.startswith("NEW STCATEGORY")]
print("logical lines=%d  NEW SPCOMPONENT=%d unique=%d | NEW SPRFILE=%d unique=%d | OLD SPCOMPONENT=%d | STCATEGORY=%d"
      % (len(logical), len(spc), len(set(spc)), len(spr), len(set(spr)), len(old_spc), len(cat)))
S_set = set(spc)
P_set = set(spr)

# ---- 2) 匹配文件（自己的解析）
mtxt = open(MAP, "rb").read().decode("gbk")
rows = []
for i, ln in enumerate(mtxt.replace("\r\n", "\n").split("\n"), 1):
    s = ln.strip()
    if not s or s.startswith("//") or set(s) == {"/"} or "," not in s:
        continue
    left, right = s.split(",", 1)
    rows.append((i, left.strip(), " ".join(right.split())))
print("matching rows=%d" % len(rows))


def norm(r):
    return r if r.startswith("/") else "/" + r


exact = [r for r in rows if r[2] in S_set]
slash = [r for r in rows if not r[2].startswith("/")]
slash_found = [r for r in slash if norm(r[2]) in S_set]
broken_raw = [r for r in rows if r[2] not in S_set]
broken_norm = [r for r in rows if norm(r[2]) not in S_set]
owners = collections.Counter(r[2].lstrip("/").split("/")[0] for r in broken_norm)
print("exact=%d slash_rows=%d slash_found=%d broken_raw=%d broken_norm=%d"
      % (len(exact), len(slash), len(slash_found), len(broken_raw), len(broken_norm)))
print("broken_norm by owner: %s" % owners.most_common())
print("broken_norm lines (non-DoubleL): %s"
      % [(r[0], r[1], r[2]) for r in broken_norm if "DOUBLE_L_" not in r[2]][:8])
used = {norm(r[2]) for r in rows}
macro_only = sorted(S_set - used)
print("macro_only(SPCOMPONENT not used by matching file)=%d" % len(macro_only))

# ---- 3) 大小写差异：匹配文件左值 vs DLL 内嵌名（UTF-16LE 字符串）
dll = open(DLL, "rb").read()
try:
    dtxt = dll.decode("utf-16-le", "ignore")
except Exception:
    dtxt = ""
names = set(re.findall(r"[\x20-\x7e]{3,}", dtxt))
lefts = [r[1] for r in rows]
exact_in_dll = [l for l in lefts if l in names]
lower_map = collections.defaultdict(list)
for n in names:
    lower_map[n.lower()].append(n)
pairs = []
for l in lefts:
    if l in names:
        continue
    for v in lower_map.get(l.lower(), []):
        pairs.append((l, v))
print("dll utf16 names=%d  matching-left exact-in-dll=%d  case-variant pairs=%d"
      % (len(names), len(exact_in_dll), len(pairs)))
print("pairs sample:", pairs[:6])
print("pairs with differing-length spelling (not pure case): %d"
      % sum(1 for a, b in pairs if a.lower() == b.lower() and len(a) == len(b)))
json.dump({"case_pairs": len(pairs), "dll_names": len(names)}, open(os.path.join(OUT, "_probe4.json"), "w"))
