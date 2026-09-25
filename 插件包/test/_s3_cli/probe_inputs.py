# -*- coding: utf-8 -*-
"""S3（cli/gui 集成包）开发探针：先看清两个样本模型给 CLI 报告带来的量级。

只读样本；不做任何写入。跑法：
    python test\\_s3_cli\\probe_inputs.py
"""
from __future__ import annotations

import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PKG, "engine"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import canonical as C          # noqa: E402
import jwd_read                # noqa: E402
import pdt_read                # noqa: E402

PLUGIN = (u"G:/工作/PDMS相关/00 PDMS插件/02 实用插件/PKPM导入导出插件")
JWD = PLUGIN + u"/JLCJ2.jwd"
PDT = PLUGIN + u"/1_PM.pdt"


def dump_model(tag, m):
    print("=" * 70)
    print("%s   source=%s  format=%s" % (tag, os.path.basename(m.source), m.source_format))
    print("counts = %s" % (m.counts(),))
    errs, warns = m.errors(), m.warnings()
    print("validate: E-%d  W-%d" % (len(errs), len(warns)))
    for e in errs[:10]:
        print("   E: " + e)
    kinds = {}
    for w in warns:
        kinds[w.split(":")[0]] = kinds.get(w.split(":")[0], 0) + 1
    print("   W 分类: %s" % kinds)
    ecc = [x for x in m.members if any(abs(v) > C.TOL for v in x.ecc)]
    print("非零偏心构件: %d / %d" % (len(ecc), len(m.members)))
    print("notes: %d 条；前 6 条：" % len(m.notes))
    for n in m.notes[:6]:
        print("   - " + n)
    proj = [n for n in m.notes if "PROJECT_NAME=" in n]
    print("PROJECT_NAME 候选: %s" % (proj[:1],))
    print("板厚集合: %s" % (m.panel_thicknesses(),))
    print("used_sections: %d / sections: %d"
          % (len(m.used_sections()), len(m.sections)))


if __name__ == "__main__":
    dump_model("JWD", jwd_read.read_jwd(JWD))
    dump_model("PDT", pdt_read.read_pdt(PDT))
