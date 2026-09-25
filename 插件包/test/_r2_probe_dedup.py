# -*- coding: utf-8 -*-
"""R2 探针（本会话自建）：验证 jwd2db 去重后的宏结构（同父级重名应为 0）。"""
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("acc_r2", os.path.join(HERE, "acceptance_r2.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

det, errs = [], []
mac = os.path.join(HERE, "_acc_tmp", "r2_jwd2db_dedup.mac")
db = m._macro_structure_checks("jwd2db", mac, det, errs)
print("errs =", errs)
for d in det:
    s = d.strip()
    if any(k in s for k in ("重名", "SPCOMPONENT", "NEW=", "第二遍", "容器", "参数化族")):
        print("  ", s[:240])
