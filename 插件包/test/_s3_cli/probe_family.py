# -*- coding: utf-8 -*-
"""探针：sample_db.mac / sample_pdt_db.mac 的族-规格对应（§l.3.4-1 不变量的实际口径）。

跑法：``python PKPM-JWD导入导出\\test\\_s3_cli\\probe_family.py [macro]``
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), "test", "out")


def main(path):
    txt = open(path, "rb").read().decode("ascii", "replace")
    lines = txt.splitlines()
    fams = [m.group(1) for m in
            (re.match(r"\s*NEW STCATEGORY (\S+)", l) for l in lines) if m]
    seps = {l.split()[1] for l in lines if l.strip().startswith("NEW STSECTION")}
    sprs = {m.group(1) for m in (re.match(r"\s*NEW SPRFILE (\S+)", l) for l in lines) if m}
    comps = [m.group(1) for m in
             (re.match(r"\s*NEW SPCOMPONENT (\S+)", l) for l in lines) if m]
    print("STSECTION(%d): %s" % (len(seps), sorted(seps)))
    print("STCATEGORY(%d): %s" % (len(fams), fams))
    print("SPRFILE(%d) / SPCOMPONENT(%d)" % (len(sprs), len(comps)))
    bad = []
    for c in comps:
        owner, leaf = c.rsplit("/", 1)
        fam = owner[:-len("-SPEC")] if owner.endswith("-SPEC") else owner
        if ("/" + leaf not in sprs) or (fam not in fams):
            bad.append((c, fam, "/" + leaf, "/" + leaf in sprs, fam in fams))
    print("不变式违例 %d 条：" % len(bad))
    for b in bad:
        print("   SPCOMPONENT=%s → 期望族=%s、SPRFILE=%s（SPRFILE在=%s 族在=%s）" % b)
    rep = path[:-4] + ".report.json"
    if os.path.isfile(rep):
        r = json.load(io.open(rep, encoding="utf-8"))
        ws = [w for w in (r.get("warnings") or []) if "不变量" in w or "规格名" in w]
        print("报告里「不变量」类 warning %d 条：" % len(ws))
        for w in ws[:6]:
            print("   - %s" % w[:200])


if __name__ == "__main__":
    args = sys.argv[1:] or [os.path.join(OUT, "sample_db.mac"),
                            os.path.join(OUT, "sample_pdt_db.mac")]
    for p in args:
        print("=" * 78)
        print(p)
        main(p)
