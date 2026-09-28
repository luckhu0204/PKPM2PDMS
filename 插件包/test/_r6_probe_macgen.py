# -*- coding: utf-8 -*-
"""R6 临时探针：不依赖 secmap 的 macgen 结构自查（合成小模型 → 宏头/尾原文）。"""
import sys

sys.path.insert(0, r"D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/插件包/engine")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import canonical as C
import macgen


class FakeMap:
    """最小 SectionMap 替身（§e.6 的鸭子类型：只有 resolve）。"""

    def __init__(self):
        self.calls = 0

    def resolve(self, sec, kind):
        self.calls += 1
        return C.Resolution(spec_path="/H_INTERNATIONAL-SPEC/HN450X200",
                            status=C.RESOLVED, source="name", pkpm_name=sec.name)


m = C.Model(
    levels=[C.Level(stdflr_id=1, floor_id=1, no=1, z_bot=0.0, z_top=3000.0, height=3000.0)],
    joints={},
    sections={1: C.Section(id=1, kind=26, mat=5, name="HN450X200", dims={},
                           table="beam", shapeval="")},
    members=[C.Member(id=1, type="column", level=1, section=1,
                      start=(400.0, 400.0, 0.0), end=(400.0, 400.0, 3000.0),
                      jusl="rboc", meml="rboc")],
    slabs=[C.Slab(id=1, level=1, polygon=[(0.0, 0.0), (100.0, 0.0), (100.0, 100.0)],
                  z=3000.0, thickness=120.0, no=1)],
    loads=[],
    walls=[],
    source=r"G:\tmp\probe.jwd",
    source_format="jwd",
)
opts = macgen.MacOptions(project="PROBE", secmap=FakeMap(), time_text="2026-09-28 12:00:00")
plan = macgen.build_plan(m, opts)
lines = plan.lines
print("总行数 =", len(lines))
print("=== HEAD 12 ===")
for i in range(12):
    print("%3d|%s" % (i + 1, lines[i]))
print("=== TAIL 10 ===")
for i in range(len(lines) - 10, len(lines)):
    print("%3d|%s" % (i + 1, lines[i]))
print("=== 计数 ===")
print("!!pkpm2pdmsUniquename 调用行 =",
      sum(1 for l in lines if "!!pkpm2pdmsUniquename(" in l))
print("NEW <具名类型> 行 =",
      sum(1 for l in lines if l.strip().startswith(
          ("NEW SITE", "NEW ZONE", "NEW STRU", "NEW FRMW", "NEW SBFR",
           "NEW SCTN", "NEW PANE", "NEW STWALL"))))
print("故障注入守卫行 =", sum(1 for l in lines if "var !pkpm2pdmsFatal EXIST" in l))
for bad in ("pkpm2pdmsFuncMissing", "FuncPath", "$M <"):
    print("含 %-22s = %s" % (bad, any(bad in l for l in lines)))
print("=== assumptions ===")
for a in plan.assumptions:
    print("  -", a)
