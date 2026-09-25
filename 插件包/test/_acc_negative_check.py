# -*- coding: utf-8 -*-
"""负向验证（本会话自建）：把**修复前**的宏喂给验收测试新增的判定逻辑，确认新断言不是空转。

用 test/_acc_tmp/JLCJ2.mac（上一轮修复前的产物，239399 字节）跑与 acceptance.py check_1
相同的块扫描，看：① 字面判定会不会失败；② 新增的 DESP/注释断言会不会报出来。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
OLD = os.path.join(HERE, "_acc_tmp", "JLCJ2.mac")
NEW = os.path.join(HERE, "_acceptance_out", "JLCJ2.mac")


def scan(path):
    text = open(path, "rb").read().decode("gbk")
    blocks, cur = [], None
    pending_infer = False
    for ln in text.split("\r\n"):
        s = ln.strip()
        if s.startswith("NEW SCTN") or s.startswith("NEW PANE") or s.startswith("NEW STWALL"):
            cur = {"what": s.split()[1], "head": s, "spec": False, "desp": [],
                   "infer_comment": pending_infer}
            pending_infer = False
            blocks.append(cur)
        elif cur is not None:
            if s.startswith("SPREF") or s.startswith("SPRE "):
                cur["spec"] = True
            elif s.startswith("DESP"):
                cur["desp"].append([float(v) for v in s.split()[1:]])
        if s.startswith("--") and "推断截面" in s:
            pending_infer = True
    members = [b for b in blocks if b["what"] == "SCTN"]
    no_spec = [b for b in members if not b["spec"]]
    inf = [b for b in members if b["spec"] and b["desp"]]
    return members, no_spec, inf


for tag, path in (("修复前 _acc_tmp/JLCJ2.mac", OLD), ("修复后 _acceptance_out/JLCJ2.mac", NEW)):
    if not os.path.isfile(path):
        print("%-28s 缺文件 %s" % (tag, path))
        continue
    members, no_spec, inferred = scan(path)
    print("%-28s 构件块 %d；无 SPREF/DESP = %d；带 DESP 的构件 = %d；"
          "带 -- 推断截面 注释的构件 = %d"
          % (tag, len(members), len(no_spec), len(inferred),
             sum(1 for b in inferred if b["infer_comment"])))
    print("      字面判定「每构件有 SPREF 或 DESP」= %s"
          % ("通过" if not no_spec else "不通过（%d 根缺）" % len(no_spec)))
    if inferred:
        print("      DESP 取值多重集 = %s" % (sorted(x for b in inferred for x in b["desp"][0]),))
