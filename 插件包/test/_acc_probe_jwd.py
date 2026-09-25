# -*- coding: utf-8 -*-
"""临时探针 5（本会话自建）：直接读 .jwd 里的截面表原始行（含列名），查 Kind=3 的证据。"""
import os, sqlite3

SD = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
JWD = os.path.join(SD, "JLCJ2.jwd")
out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_acc_probe_jwd.txt"),
           "w", encoding="utf-8")

uri = "file:%s?mode=ro" % JWD.replace("\\", "/").replace("?", "%3f")
con = sqlite3.connect(uri, uri=True)
con.text_factory = bytes
cur = con.cursor()


def _dec(b):
    if not isinstance(b, bytes):
        return b
    for enc in ("ascii", "utf-8"):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode("gbk", "replace")
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [_dec(r[0]) for r in cur.fetchall()]
print("tables(%d): %s" % (len(tables), tables), file=out)
for t in ("pkpmBraceSect", "pkpmBeamSect", "pkpmColSect", "pkpmBraceSeg", "pkpmProperty",
          "pkpmJoint", "pkpmFloor", "pkpmStdFlr"):
    if t not in tables:
        continue
    print("=" * 70, file=out)
    cur.execute("PRAGMA table_info(%s)" % t)
    cols = [r[1] for r in cur.fetchall()]
    print("%s cols=%s" % (t, cols), file=out)
    cur.execute("SELECT * FROM %s" % t)
    rows = cur.fetchall()
    print("rows=%d" % len(rows), file=out)
    for r in rows[:60]:
        print("   ", tuple(_dec(x) for x in r), file=out)
    if len(rows) > 60:
        print("    ... (%d more)" % (len(rows) - 60), file=out)
con.close()
out.close()
print("done")
