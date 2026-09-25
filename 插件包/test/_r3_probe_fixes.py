# -*- coding: utf-8 -*-
"""R3 探针（本会话自建）：验证本轮各修复的行为。

A) 混合族 PPRO/NUMB 下标（R3 发现③）：构造 DESP 在前、PARA 在后的族。
B) jwd2pdt 全局流水号（发现①b）：N 跨类不复用。
C) jwd2pdt 段序（发现①a）与 db2pdt 段序 + (NAME,SHAPE) 去重（发现⑨）。
D) pdt→pdt 往返的 ECS 保存（发现④）。
E) dbmacro 第二遍引用链（发现·high）：宏内不再有裸名 OLD SPRFILE/SPCOMPONENT/PTSSET。
F) --clean：清场段在 ONERROR 之后；重建容器带运行戳、不复用清场名（发现⑤a/c）。
"""
import importlib.util
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
ROOT = os.path.dirname(PKG)
sys.path.insert(0, os.path.join(PKG, "engine"))
sys.path.insert(0, os.path.join(PKG, "test"))

import sectionlib  # noqa: E402
import dbmacro     # noqa: E402
import dbparse     # noqa: E402
import pdt_write   # noqa: E402
import pdt_read    # noqa: E402
import jwd_read    # noqa: E402

TMP = os.path.join(HERE, "_acc_tmp")
os.makedirs(TMP, exist_ok=True)
OUT = open(os.path.join(HERE, "_r3_probe_fixes.txt"), "w", encoding="utf-8")

# ---------- A) 混合族 PPRO/NUMB ----------
class _Rec:
    def __init__(self, name, spec, params, parametric=True):
        self.key = name
        self.pkpm_name = name
        self.family_code = 16          # /USER_H 对应的参数化族码（来自 recon §4.1）
        self.family_name_cn = "H"
        self.kind = 0
        self.shapeval = ""
        self.dims = {}
        self.mat = 5
        self.pdms_spec_path = spec
        self.pdms_catalogue = ""
        self.is_parametric = parametric
        self.params = params
        self.confidence = "high"
        self.source = "probe"
        self.extra = {"pdms_specification": "/PKPM_SECTION_USER",
                      "pdms_stsection": "/USER_SECTION",
                      "pdms_sprfile": spec.rsplit("/", 1)[-1],
                      "family_desc_en": "Probe H",
                      "pdms_stcategory": "/" + name.split("-")[0],
                      }

# 构造两条记录：同族 /USER_H，参数 DESP1 在前（占位名 P1）、PARA 参数 h/b 在后
p1 = {"name": "P1", "default": "10", "desp_index": 1}
p2 = {"name": "h(mm)", "default": "500", "desp_index": 0}
p3 = {"name": "b(mm)", "default": "250", "desp_index": 0}
recs = [
    _Rec("USER_H", "/USER_H-SPEC/H_Profile", [p1, p2, p3]),
    _Rec("USER_H", "/USER_H-SPEC/H_Profile", [p1, p2, p3]),
]
table = type("T", (), {"recs": recs})()
opts = dbmacro.DbOptions(source_note="probe", suffix="_PROBE", report={})
text = dbmacro.generate_db_macro(table, opts)
dpro = re.findall(r"PPRO \( ATTRIB (PARA\[\d+ \]|DESP\[\d+ \]) \)", text)
numb = re.findall(r"NUMB (\d+)", text)
dtit = re.findall(r"DTIT '([^']+)'", text)
print("A) DATA 行序列：", list(zip(dtit, dpro, numb)), file=OUT)
ok_a = ("PARA[1 ]" in text and "NUMB 1" in text and "DESP[1 ]" in text)
print("   PPRO PARA[n] 与 NUMB 同用 PARA 组内序号：", ok_a, file=OUT)

# ---------- E) 第二遍引用链（用上面的宏即可） ----------
bare = [l for l in text.splitlines()
        if re.match(r"^\s*OLD\s+(SPRFILE|SPCOMPONENT|PTSSET)\s+\S+\s*$", l)]
qualified = [l for l in text.splitlines()
             if re.match(r"^\s*OLD\s+(SPRFILE|SPCOMPONENT|PTSSET)\s+", l)]
print("E) OLD 引用行 %d 条，其中裸名（无 of 链）%d 条" % (len(qualified), len(bare)), file=OUT)
for l in qualified[:3]:
    print("   ", l.strip()[:160], file=OUT)

# ---------- F) --clean 顺序与容器名 ----------
opts2 = dbmacro.DbOptions(source_note="probe", suffix="_ACCCLEAN", clean_first=True, report={})
text2 = dbmacro.generate_db_macro(table, opts2)
lines2 = text2.splitlines()
i_on = next(i for i, l in enumerate(lines2) if l.startswith("ONERROR"))
i_clean = next(i for i, l in enumerate(lines2) if "OLD CATALOGUE" in l)
print("F) ONERROR 行号 %d，第一条清场 OLD 行号 %d（ONERROR 在前 = %s）"
      % (i_on + 1, i_clean + 1, i_on < i_clean), file=OUT)
clean_old = [l.strip() for l in lines2 if l.startswith("OLD CATALOGUE")]
new_cat = [l.strip() for l in lines2 if l.startswith("NEW CATALOGUE")]
print("   清场目标：", clean_old, file=OUT)
print("   重建容器：", new_cat, file=OUT)
print("   清场名 != 重建名（不复用）：",
      not (set(n.split(None, 1)[1] for n in new_cat)
           & set(o.split(None, 1)[1] for o in clean_old)), file=OUT)

# ---------- B/C/D) pdt 侧 ----------
model = jwd_read.read_jwd(
    r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\JLCJ2.jwd")
p1_path = os.path.join(TMP, "r3_jwd2pdt.pdt")
pdt_write.write_pdt(model, p1_path, pdt_write.PdtOptions(skeleton="full"))
t = open(p1_path, "rb").read().decode("gbk")
heads = [l.strip() for l in t.splitlines() if l.strip().startswith("$")]
print("C1) jwd2pdt 段头序列：", heads, file=OUT)
want = ["$" + s for s in pdt_write.SEGMENT_ORDER]
print("   与 SEGMENT_ORDER 一致：", [h for h in heads if h in want] == want, file=OUT)

ids = [int(m.group(1)) for m in re.finditer(r"^\s+ID=\s*(\d+),", t, re.M)]
ns = sorted(i // 100 for i in ids)
reuse = len(ns) - len(set(ns))
print("B) 主记录 N 总数 %d，跨类复用 %d（应为 0）" % (len(ns), reuse), file=OUT)

# ECS 保存（发现④）：pdt 读回 → 再写 → ECS 应保留
m2 = pdt_read.read_pdt(p1_path)
print("D) jwd2pdt 读回 Member.ecc 非零个数（jwd 源应为 0）：",
      sum(1 for m in m2.members if m.ecc), file=OUT)
pdt_src = pdt_read.read_pdt(
    r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\1_PM.pdt")
n_ecc = sum(1 for m in pdt_src.members if m.ecc)
print("D) 样本 1_PM.pdt 读回 Member.ecc 非零个数（应为 121）：", n_ecc, file=OUT)
p2_path = os.path.join(TMP, "r3_pdt2pdt.pdt")
pdt_write.write_pdt(pdt_src, p2_path, pdt_write.PdtOptions(skeleton="full"))
t2 = open(p2_path, "rb").read().decode("gbk")
ecs_vals = sorted({m.group(1) for m in re.finditer(r"ECS1=([0-9.]+)", t2)})
print("D) pdt→pdt 产物 ECS1 取值（应含 225.000/250.000 等）：", ecs_vals, file=OUT)

# db2pdt：段序 + 去重
secs = sectionlib.load_builtin_table().to_jwd_sections()
p3_path = os.path.join(TMP, "r3_db2pdt.pdt")
pdt_write.write_pdt_sections(secs, p3_path, pdt_write.PdtOptions(skeleton="full"))
t3 = open(p3_path, "rb").read().decode("gbk")
heads3 = [l.strip() for l in t3.splitlines() if l.strip().startswith("$")]
print("C2) db2pdt 段头序列：", heads3, file=OUT)
want3 = ["$" + s for s in pdt_write.SEGMENT_ORDER]
print("   与 SEGMENT_ORDER 一致：", [h for h in heads3 if h in want3] == want3, file=OUT)
rec_heads = re.findall(r"^\s+ID=\d+, NAME=([^,]*), SHAPE=(\S+)", t3, re.M)
print("   记录数 %d，唯一 (NAME,SHAPE) %d（应相等）"
      % (len(rec_heads), len(set(rec_heads))), file=OUT)
mm = sorted({int(x) for x in re.findall(r"^\s+M=(\d+),", t3, re.M)})
shape_m = sorted({(sh, mid) for (_, sh), mid in
                  zip(re.findall(r"^\s+ID=\d+, NAME=([^,]*), SHAPE=(\S+)", t3, re.M),
                      re.findall(r"^\s+M=(\d+),", t3, re.M))})
print("   (SHAPE,M) 组合：", shape_m, file=OUT)
OUT.close()
print("done")
