# -*- coding: utf-8 -*-
"""S3-R3 探针：给 engine/dist 的 exe / run_engine.cmd 造 --request 请求文件（§p.5）。

跑法：``python test\\_s3_cli\\make_requests.py``
只写 test/out/ 下自己的请求文件；样本只读。
"""
from __future__ import annotations

import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), "test", "out")
PLUG = u"G:/工作/PDMS相关/00 PDMS插件/02 实用插件/PKPM导入导出插件"


def write(name, req):
    p = os.path.join(OUT, name)
    with io.open(p, "w", encoding="utf-8", newline="\n") as fh:   # §p.5：UTF-8 无 BOM
        fh.write(json.dumps(req, ensure_ascii=False, indent=1))
    return p


if __name__ == "__main__":
    print(write("_exe_request.json", {
        "tool": "jwd2db",
        "args": {
            "jwd": PLUG + u"/JLCJ2.jwd",
            "out": u"D:/AI_Work/PKPM数据解析/PKPM2PDMS导入导出/test/out/_exe_request.mac",
            "secmap": PLUG + u"/PKPM转PDMS截面匹配文件.txt",
            "project": "JLCJ2",
        },
    }))
    print(write("_req_r3_jwd2pdms.json", {
        "tool": "jwd2pdms",
        "args": {
            "jwd": PLUG + u"/JLCJ2.jwd",
            "out": u"D:/AI_Work/PKPM数据解析/PKPM2PDMS导入导出/test/out/r3.mac",
            "secmap": PLUG + u"/PKPM转PDMS截面匹配文件.txt",
            "project": "JLCJ2",
        },
    }))
    print(write("_req_r3_pdt2pdms.json", {
        "tool": "pdt2pdms",
        "args": {
            "pdt": PLUG + u"/1_PM.pdt",
            "out": u"D:/AI_Work/PKPM数据解析/PKPM2PDMS导入导出/test/out/r3_pdt.mac",
            "secmap": PLUG + u"/PKPM转PDMS截面匹配文件.txt",
            "project": "JLCJ2",
        },
    }))
