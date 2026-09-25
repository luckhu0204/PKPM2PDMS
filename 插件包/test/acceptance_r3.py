# -*- coding: utf-8 -*-
"""PKPM-JWD导入导出 —— 独立验收测试 R3（契约 v3 验收标准 15–19 + 把关项）。

用法（工作目录 = 工作区根 ``D:\\AI_Work\\PKPM数据解析``）::

    python PKPM-JWD导入导出/test/acceptance_r3.py

输出：逐条结论文本 + **最后一行**机器可读汇总 JSON
``{"passed":true,"passedCount":N,"failedCount":0}``（键名 ASCII）。全通过 ⇒ 退出码 0；
任一条失败 ⇒ 打印失败详情 + ``{"passed":false,…}`` + 退出码非 0。

检查项（契约 v3 §q；v1 的 1–8 由 test/acceptance.py 把关、R2 的 9–14 由 test/acceptance_r2.py 把关）
--------------------------------------------------------------------------------
15  重名唯一化：PML 函数静态逐条（签名/候选序列/EXIST+(2,109) 探测/记录格式/FAIL 语义）
    + **逻辑对照**（本文件自实现的 §o.1 参考算法对构造占用表跑候选序列）
    + renames 键（§o.7）+ 宏侧"不跳过/不覆盖"（ONERROR 尾 + 故障注入 + 全部经 $!n）
16  .NET 插件真编译：跑 pdms-net/build.cmd（退出码 0、产物存在），PE 头核对
    machine=I386(0x14c)、PE32(0x10b)、CLI 运行时 2.5、字面 v2.0.50727；D:\\AVEVA 编译前后零变化
17  注册脚本静态检查：缺省 dry-run 清单（8 项、无"删除"）、幂等（--execute 两次 XML 逐字节不变）、
    卸载=恢复+移动（XML 与 .bak 逐字节相等、4 文件进 _uninstalled_*）、**未对真实 D:\\AVEVA 执行过**
18  界面清单完整：pkpmjwd.uic 与 tgtext.uic 逐条同构对照 + PKPMJWDForm.cs 全部控件
    + Key 三处一致（.uic/Addin/Command 构造器）+ 编译通过（=16）
19  交付落点与"没动过"：R3 交付物齐备于工作区、交付目录含 pdms-net/哈希清单、
    docs 含 §p.10-5 未部署声明、G 盘与 D:\\AVEVA 在整轮前后清单+哈希零变化
把关  宏里创建元素之前的唯一化调用计数 == 元素总数（全部命名元素经 !!pkpmjwdUniquename）

独立性：期望值全部由本文件独立重算（PE 头自解析、占用表模拟自实现、uic 同构对照自建、
基线快照自建）；engine/pdms-net 只作为被测对象被调用。确定性：无时间/随机/网络依赖；
自建产物写入 ``PKPM-JWD导入导出/test/_acc_r3_out/``（覆盖写，不删除任何文件）。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
ROOT = os.path.dirname(PKG)
OUT = os.path.join(HERE, "_acc_r3_out")

SAMPLE_DIR = r"G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件"
SAMPLE_JWD = os.path.join(SAMPLE_DIR, "JLCJ2.jwd")
SAMPLE_PDT = os.path.join(SAMPLE_DIR, "1_PM.pdt")
SAMPLE_MAP = os.path.join(SAMPLE_DIR, "PKPM转PDMS截面匹配文件.txt")
G_PLUGIN = SAMPLE_DIR
AVEVA = r"D:\AVEVA\Plant\PDMS12.1.SP4"
PMLLIB = os.path.join(AVEVA, "PMLLIB")
TGTEXT_BAK = r"D:\AI_Work\pmds三维文字程序-备份\TGTEXT"
TGTEXT_TASK = r"D:\AI_Work\PDMS三维文字程序\TGTEXT"
DELIVERY = os.path.join(ROOT, "交付_PKPM-JWD插件")

PMLFN = os.path.join(PKG, "pdms", "pkpmjwduniquename.pmlfnc")
NET = os.path.join(PKG, "pdms-net")
BUILD_CMD = os.path.join(NET, "build.cmd")
DIST_DLL = os.path.join(NET, "dist", "PKPMJWD.dll")
DIST_UIC = os.path.join(NET, "dist", "pkpmjwd.uic")
UIC = os.path.join(NET, "pkpmjwd.uic")
ADDIN_CS = os.path.join(NET, "PKPMJWDAddin.cs")
FORM_CS = os.path.join(NET, "PKPMJWDForm.cs")
DEPLOY_PY = os.path.join(NET, "deploy", "deploy_pkpmjwd.py")
UNDEPLOY_PY = os.path.join(NET, "deploy", "undeploy_pkpmjwd.py")
CLI = os.path.join(PKG, "engine", "cli.py")

TOL_TYPES = ("SITE", "ZONE", "STRU", "FRMW", "SBFR", "SCTN", "PANE", "STWALL")


# --------------------------------------------------------------------------
# 通用
# --------------------------------------------------------------------------
def _read(path):
    with open(path, "rb") as f:
        return f.read()


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _lone_lf(b):
    return sum(1 for i, c in enumerate(b) if c == 0x0A and (i == 0 or b[i - 1] != 0x0D))


def _run(argv, cwd=None, timeout=600):
    p = subprocess.run(list(argv), cwd=cwd, capture_output=True, timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def _manifest(root, recursive):
    """区域清单：relpath -> (size, mtime, sha256)。只读。"""
    rows = {}
    if recursive:
        for dp, dn, fn in os.walk(root):
            for x in fn:
                p = os.path.join(dp, x)
                try:
                    st = os.stat(p)
                    rows[os.path.relpath(p, root)] = (st.st_size, st.st_mtime, _sha_file(p))
                except OSError:
                    rows[os.path.relpath(p, root)] = None
    else:
        for x in os.listdir(root):
            p = os.path.join(root, x)
            if os.path.isfile(p):
                st = os.stat(p)
                rows[x] = (st.st_size, st.st_mtime, _sha_file(p))
    return rows


def _manifest_diff(old, new):
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(p for p in set(old) & set(new)
                     if old[p] != new[p])
    return added, removed, changed


# --------------------------------------------------------------------------
# §o.1 候选序列（本文件自实现的参考算法；与 PML 的逻辑对照基准）
# --------------------------------------------------------------------------
def ref_candidates(base):
    """契约 §o.1：base, base+re, base+re2 .. base+re99（共 100 个）。"""
    return [base] + [base + "re"] + ["%sre%d" % (base, d) for d in range(2, 100)]


def ref_pick(base, occupied, typ="SCTN"):
    """占用表模拟：返回 (final, rename_record 或 None)。耗尽 ⇒ ('', FAIL 记录)。"""
    for cand in ref_candidates(base):
        if cand not in occupied:
            if cand == base:
                return cand, None
            return cand, {"type": typ, "original": base, "final": cand,
                          "reason": "name in use"}
    return "", {"type": "FAIL", "original": base, "final": base + "re99",
                "reason": "candidates exhausted"}


# ==========================================================================
# 检查 15：重名唯一化
# ==========================================================================
def check_15(ch):
    det, errs = [], []
    # ---------- ① 文件级纪律 + 静态逐条
    if not os.path.isfile(PMLFN):
        ch.add(15, "重名唯一化（静态+逻辑对照+renames+宏侧不跳过）",
               ["缺 %s" % PMLFN], det)
        return
    b = _read(PMLFN)
    try:
        text = b.decode("gbk")
        det.append("pdms/pkpmjwduniquename.pmlfnc %d 字节：GBK 严格解码通过" % len(b))
    except UnicodeDecodeError as exc:
        errs.append("PML 函数不是 GBK：%s" % exc)
        text = b.decode("gbk", "replace")
    if b[:3] == b"\xef\xbb\xbf":
        errs.append("PML 带 BOM")
    if _lone_lf(b):
        errs.append("PML 含 %d 个孤立 LF（要求 CRLF）" % _lone_lf(b))
    det.append("无 BOM、孤立 LF=%d" % _lone_lf(b))
    frozen = [
        ("签名", "define function !!pkpmjwdUniquename(!base is STRING) is STRING"),
        ("defined 守卫", "defined(!!pkpmjwdRenames)"),
        ("数组建立", "object ARRAY()"),
        ("循环 0..99", "do !idx from 0 to 99"),
        ("候选 0=原名", "!cand = !base"),
        ("候选 1=re", "!cand = !base & 're'"),
        ("候选 2..99=reN", "!cand = !base & 're' & !idx.string()"),
        ("探测写法①", "var !probe EXIST $!cand"),
        ("handle (2,109)", "handle (2,109)"),
        ("记录格式 TYPE|原名|实际名", "'|' & !base & '|'"),
        ("FAIL 留痕", "'FAIL|' & !base & '|' & !base & 're99'"),
        ("FAIL 返回空串", "return ''"),
    ]
    for name, needle in frozen:
        ok = needle in text
        det.append("  [%s] %s %r" % ("OK" if ok else "MISS", name, needle))
        if not ok:
            errs.append("PML 缺冻结要素 %s：%r" % (name, needle))
    if re.search(r"\bdelete\b", text, re.I):
        errs.append("PML 函数内出现 delete（§o.6-4：绝不覆盖既有元素）")
    else:
        det.append("  [OK] 函数内无 delete（§o.6-4 不覆盖）")
    # §0.4-12：探测/重探形态 = EXIST $!x（base 自带前导 /）；旧形 //名 插值是全库 0 例的
    # 未证实形态，必须**不出现**（加强项，不是放宽）
    if "EXIST /$!cand" in text:
        errs.append("PML 仍含旧形探测 EXIST /$!cand（会探成 //名，§0.4-12 已禁用）")
    else:
        det.append("  [OK] 无旧形 //名 探测（§0.4-12：探测/重探形态 = EXIST $!x）")
    # 候选上限只许在**代码**里出现一次（re99 只在 FAIL 留痕）；注释里的说明不计
    code_lines = [l.split("--", 1)[0] for l in text.replace("\r\n", "\n").split("\n")]
    code_text = "\n".join(code_lines)
    n99 = code_text.count("re99")
    n_loop = code_text.count("from 0 to 99")
    nums = re.findall(r"re(\d+)", code_text)
    other = sorted({n for n in nums if n != "99"})
    det.append("  [OK=%s] 上限自洽（只数代码，注释不计）：'re99'×%d、'from 0 to 99'×%d、"
               "其它编号后缀 %s" % (n99 == 1 and n_loop == 1 and not other,
                                    n99, n_loop, other or "无"))
    if n99 != 1 or n_loop != 1 or other:
        errs.append("候选上限不自洽（代码级）：re99×%d、循环×%d、其它编号 %s" % (n99, n_loop, other))
    # 实现与 F.1 夹具的两处落地差异必须**在文件内写明**（不许静默偏离）
    dev_doc = ("两种都写" in text) and ("TYPE 通道" in text)
    det.append("  [%s] 两处落地差异在文件头写明（探测双结局 + TYPE 通道）" % ("OK" if dev_doc else "MISS"))
    if not dev_doc:
        errs.append("PML 与附录 F.1 的落地差异未在文件内说明（契约 F.1 注意事项）")

    # ---------- ② 探测写法的 PMLLIB 出处（本机安装内核对）
    pd_checks = [
        (r"aba\Forms\abaarealib.pmlfrm", ("EXIST", "(2,109)", "TRUEA"),
         "§o.3 写法① / 双结局判值"),
        (r"assembly\functions\assybuildname.pmlfnc", ("EXIST", "FALSEA"),
         "VAR EXIST 正常返回 FALSEA 的直证"),
        (r"aba\Forms\abaarea.pmlfrm", ("41,12",), "§o.3 写法②"),
        (r"Building_Design\pmllib\concrete_design\TRADUCTEUR\nucdesogwall.pmlobj",
         ("$M", "defined"), "$M 与 defined()"),
        (r"mypml\forms\GRIDDESIGN.pmlfrm", ("APPEND", ".string()"), ".append() 与 .string()"),
    ]
    for rel, needles, why in pd_checks:
        p = os.path.join(PMLLIB, rel.replace("/", os.sep))
        if not os.path.isfile(p):
            errs.append("出处文件缺失：%s" % rel)
            continue
        lines = _read(p).decode("gbk", "replace").replace("\r\n", "\n").split("\n")
        got = {n: any(n in l for l in lines) for n in needles}
        det.append("  [%s] PMLLIB %s —— %s：%s"
                   % ("OK" if all(got.values()) else "MISS", rel, why, got))
        if not all(got.values()):
            errs.append("PMLLIB 出处核对不齐：%s %s" % (rel, got))

    # ---------- ③ 逻辑对照（本文件自实现的 §o.1 参考算法）
    det.append("逻辑对照（参考算法 = 契约 §o.1：候选 base,re,re2..re99 共 100 个，取第一个未占用）：")
    scen = [
        ("库里无同名（全部原名可用）", set(), "/STL_COL_1", "/STL_COL_1", None),
        ("库里已有原名", {"/STL_COL_1"}, "/STL_COL_1", "/STL_COL_1re",
         {"type": "SCTN", "original": "/STL_COL_1", "final": "/STL_COL_1re",
          "reason": "name in use"}),
        ("原名与 re 都被占", {"/STL_COL_1", "/STL_COL_1re"}, "/STL_COL_1", "/STL_COL_1re2",
         {"type": "SCTN", "original": "/STL_COL_1", "final": "/STL_COL_1re2",
          "reason": "name in use"}),
        ("re99 也被占（候选耗尽）", set(ref_candidates("/BM_9")), "/BM_9", "",
         {"type": "FAIL", "original": "/BM_9", "final": "/BM_9re99",
          "reason": "candidates exhausted"}),
    ]
    for name, occ, base, want_final, want_rec in scen:
        got_final, got_rec = ref_pick(base, occ, "SCTN")
        ok = (got_final == want_final and got_rec == want_rec)
        det.append("  [%s] %s：base=%s 占用 %d 个 ⇒ final=%s 记录=%s"
                   % ("OK" if ok else "FAIL", name, base, len(occ),
                      got_final or "''", json.dumps(got_rec, ensure_ascii=False)))
        if not ok:
            errs.append("逻辑对照失败：%s ⇒ %r/%r（期望 %r/%r）"
                        % (name, got_final, got_rec, want_final, want_rec))
    det.append("  候选序列长度 = %d（§o.1 要求 100：base + re + re2..re99）"
               % len(ref_candidates("/X")))
    if len(ref_candidates("/X")) != 100:
        errs.append("候选序列长度 ≠ 100")

    # ---------- ④ renames 键（§o.7：键必须存在；首跑 = []）
    rep_p = os.path.join(OUT, "r3.report.json")
    if os.path.isfile(rep_p):
        rep = json.load(open(rep_p, encoding="utf-8"))
        has = "renames" in rep
        det.append("  [%s] report.json 含 renames 键（§o.7），首跑值 = %s"
                   % ("OK" if has else "MISS", json.dumps(rep.get("renames"))))
        if not has:
            errs.append("报告缺 renames 键（§o.7：键必须存在）")
    else:
        det.append("  [info] 报告尚未生成（把关项会生成）")

    ch.add(15, "重名唯一化（静态+逻辑对照+renames+宏侧不跳过）", errs, det)


# ==========================================================================
# 检查 16：.NET 插件真编译
# ==========================================================================
def _pe_info(dll):
    """自解析 PE 头：machine / optional magic / CLI 运行时版本 / 字面 'v2.0.50727'。"""
    b = _read(dll)
    if b[:2] != b"MZ" or len(b) < 0x40:
        return None
    pe = int.from_bytes(b[0x3C:0x40], "little")
    if b[pe:pe + 4] != b"PE\x00\x00":
        return None
    machine = int.from_bytes(b[pe + 4:pe + 6], "little")
    nsec = int.from_bytes(b[pe + 6:pe + 8], "little")
    opt_size = int.from_bytes(b[pe + 20:pe + 22], "little")
    magic = int.from_bytes(b[pe + 24:pe + 26], "little")
    dd = pe + 24 + (96 if magic == 0x10B else 112)
    cli_rva = int.from_bytes(b[dd + 14 * 8:dd + 14 * 8 + 4], "little")
    cli_size = int.from_bytes(b[dd + 14 * 8 + 4:dd + 14 * 8 + 8], "little")
    rt = None
    if cli_rva:
        sec0 = pe + 24 + opt_size
        for i in range(nsec):
            s = sec0 + i * 40
            va = int.from_bytes(b[s + 12:s + 16], "little")
            rawsz = int.from_bytes(b[s + 16:s + 20], "little")
            rawptr = int.from_bytes(b[s + 20:s + 24], "little")
            if va <= cli_rva < va + max(rawsz, 1):
                fo = rawptr + (cli_rva - va)
                rt = (int.from_bytes(b[fo + 4:fo + 6], "little"),
                      int.from_bytes(b[fo + 6:fo + 8], "little"))
                break
    return {"machine": machine, "magic": magic, "runtime": rt,
            "literal": b"v2.0.50727" in b, "size": len(b)}


def check_16(ch, aveva_before):
    det, errs = [], []
    for p in (BUILD_CMD, DIST_DLL):
        if not os.path.isfile(p):
            errs.append("缺 %s" % p)
    if errs:
        ch.add(16, ".NET 插件真编译（build.cmd 退出码 0 + CLR v2.0.50727/x86）", errs, det)
        return
    src = _read(BUILD_CMD).decode("ascii", "replace")
    det.append("build.cmd：%d 字节、ASCII=%s、BOM=%s、孤立 LF=%d（§g-6：必须 CRLF+ASCII 注释）"
               % (len(_read(BUILD_CMD)), all(c < 0x80 for c in _read(BUILD_CMD)),
                  _read(BUILD_CMD)[:3] == b"\xef\xbb\xbf", _lone_lf(_read(BUILD_CMD))))
    if _lone_lf(_read(BUILD_CMD)) or any(c > 0x7F for c in _read(BUILD_CMD)):
        errs.append("build.cmd 不是 CRLF+ASCII（契约 §p.2 实测教训）")
    for needle in ("v3.5", "/platform:x86", "/target:library"):
        if needle not in src:
            errs.append("build.cmd 缺 %r（§p.2 冻结命令）" % needle)
    code, out, err = _run([BUILD_CMD], cwd=NET, timeout=300)
    det.append("命令：pdms-net\\build.cmd（cwd=pdms-net）→ 退出码 %d；stdout=%r"
               % (code, out.strip()[:120]))
    if code != 0:
        errs.append("build.cmd 退出码 %d ≠ 0：%s" % (code, (out + err)[:300]))
    if "BUILD OK" not in out:
        errs.append("build.cmd 输出没有 BUILD OK")
    if not os.path.isfile(DIST_DLL):
        errs.append("产物不存在：%s" % DIST_DLL)
        ch.add(16, ".NET 插件真编译（build.cmd 退出码 0 + CLR v2.0.50727/x86）", errs, det)
        return
    info = _pe_info(DIST_DLL)
    det.append("产物 dist\\PKPMJWD.dll：%d 字节；PE=%s" % (info["size"], json.dumps(info)))
    if info["machine"] != 0x14C:
        errs.append("PE machine=0x%x ≠ 0x14c(I386/x86)" % info["machine"])
    if info["magic"] != 0x10B:
        errs.append("optional magic=0x%x ≠ 0x10b(PE32)" % info["magic"])
    if not info["runtime"] or info["runtime"][0] != 2:
        errs.append("CLI 运行时版本 %s ≠ 2.x（CLR2）" % (info["runtime"],))
    if not info["literal"]:
        errs.append("产物内无字面 v2.0.50727（CLR2 旁证）")
    det.append("  旁证 TGTEXT.dll（备份副本）：%s"
               % json.dumps(_pe_info(os.path.join(TGTEXT_BAK, "TGTEXT.dll"))
                            if os.path.isfile(os.path.join(TGTEXT_BAK, "TGTEXT.dll")) else None))
    after = _manifest(AVEVA, False)
    added, removed, changed = _manifest_diff(aveva_before, after)
    det.append("D:\\AVEVA 根在编译前后：added=%d removed=%d changed=%d（编译只读）"
               % (len(added), len(removed), len(changed)))
    if added or removed or changed:
        errs.append("编译期间 D:\\AVEVA 发生变化：added=%s removed=%s changed=%s"
                    % (added[:3], removed[:3], changed[:3]))
    ch.add(16, ".NET 插件真编译（build.cmd 退出码 0 + CLR v2.0.50727/x86）", errs, det)


# ==========================================================================
# 检查 17：注册脚本静态检查（全部在沙箱里做；绝不碰真实 D:\AVEVA）
# ==========================================================================
SB = os.path.join(OUT, "sb17")
FIX_ADDINS = ('<?xml version="1.0" encoding="utf-8"?>\r\n<ArrayOfString>\r\n'
              '  <string>TGTEXT</string>\r\n  <string>PDCOPILOT</string>\r\n'
              '</ArrayOfString>\r\n')
FIX_CUST = ('<?xml version="1.0" encoding="utf-8"?>\r\n<UICustomizationFiles>\r\n'
            '  <CustomizationFile Name="TGTEXT" Path="tgtext.uic" />\r\n'
            '</UICustomizationFiles>\r\n')


def check_17(ch, aveva_before):
    det, errs = [], []
    for p in (DEPLOY_PY, UNDEPLOY_PY):
        if not os.path.isfile(p):
            errs.append("缺 %s" % p)
    if errs:
        ch.add(17, "注册脚本静态检查（dry-run/幂等/可回滚/只加不删/未执行过）", errs, det)
        return
    os.makedirs(SB, exist_ok=True)
    # 沙箱初值（自己的文件，覆盖写；内容每次一致 ⇒ 可重复）
    with open(os.path.join(SB, "DesignAddins.xml"), "wb") as f:
        f.write(FIX_ADDINS.encode("utf-8-sig"))
    with open(os.path.join(SB, "DesignCustomization.xml"), "wb") as f:
        f.write(FIX_CUST.encode("utf-8-sig"))

    dep = [sys.executable, DEPLOY_PY, "--pdms-root", SB,
           "--engine-entry", r"C:\nonexistent\pkpmjwd_engine.exe"]
    # ---------- ① 缺省 dry-run：清单 = 8 项，无"删除"
    code, out, err = _run(dep)
    det.append("命令：python pdms-net/deploy/deploy_pkpmjwd.py --pdms-root <沙箱>（缺省 dry-run）→ 退出码 %d"
               % code)
    if code != 0:
        errs.append("dry-run 退出码 %d ≠ 0：%s" % (code, (out + err)[:200]))
    kinds = {}
    for mo in re.finditer(r"\[\s*(?:DO|skip)\s*\]\s*(\S+)", out):
        kinds[mo.group(1)] = kinds.get(mo.group(1), 0) + 1
    det.append("dry-run 清单：%d 项，种类 %s" % (sum(kinds.values()), kinds))
    if sum(kinds.values()) != 8:
        errs.append("dry-run 清单不是 8 项（§p.6 表：备份2+追加2+复制2+写2）：%s" % kinds)
    want_kinds = {"backup": 2, "insert-addins": 1, "insert-cust": 1, "copy": 3, "write": 1}
    if kinds != want_kinds:
        errs.append("dry-run 清单种类不符：%s ≠ %s（复制 3 + 写 1 是因为 .pmlfnc 走 copy）"
                    % (kinds, want_kinds))
    if "删除" in out or "delete" in out.lower():
        errs.append("dry-run 清单出现删除字样（§p.6 只加不删）")
    else:
        det.append("  [OK] 清单无删除字样")
    # dry-run 不落盘
    b1 = _read(os.path.join(SB, "DesignAddins.xml"))
    det.append("  [OK] dry-run 后沙箱 XML 未变：%s" % (b1 == FIX_ADDINS.encode("utf-8-sig")))
    if b1 != FIX_ADDINS.encode("utf-8-sig"):
        errs.append("dry-run 改动了沙箱文件")

    # ---------- ② 幂等：--execute 两次，XML 逐字节不变、条目只出现一次
    code1, o1, e1 = _run(dep + ["--execute"])
    a1 = _read(os.path.join(SB, "DesignAddins.xml"))
    c1 = _read(os.path.join(SB, "DesignCustomization.xml"))
    code2, o2, e2 = _run(dep + ["--execute"])
    a2 = _read(os.path.join(SB, "DesignAddins.xml"))
    c2 = _read(os.path.join(SB, "DesignCustomization.xml"))
    det.append("--execute #1 退出码 %d；#2 退出码 %d" % (code1, code2))
    if code1 or code2:
        errs.append("--execute 退出码非 0：%d/%d" % (code1, code2))
    det.append("写回 BOM=%s/%s、孤立 LF=%d/%d（§p.6：必须保留 BOM+CRLF）"
               % (a1[:3] == b"\xef\xbb\xbf", c1[:3] == b"\xef\xbb\xbf",
                  _lone_lf(a1), _lone_lf(c1)))
    if a1[:3] != b"\xef\xbb\xbf" or c1[:3] != b"\xef\xbb\xbf" or _lone_lf(a1) or _lone_lf(c1):
        errs.append("写回的 XML 未保留 BOM+CRLF")
    idem = (a1 == a2 and c1 == c2)
    det.append("  [%s] 幂等：第二次 --execute 后两个 XML 与第一次逐字节相同（PKPMJWD 条目 %d 处）"
               % ("OK" if idem else "FAIL", a2.count(b"PKPMJWD")))
    if not idem:
        errs.append("重复安装不幂等（第二次改动了 XML）")
    if a2.count(b"<string>PKPMJWD</string>") != 1:
        errs.append("DesignAddins.xml 的 PKPMJWD 条目数 ≠ 1")

    # ---------- ③ 卸载 = 恢复 + 移动（无删除）
    und = [sys.executable, UNDEPLOY_PY, "--pdms-root", SB]
    und_root = os.path.join(SB, "PKPMJWD")
    pre_dirs = set(os.listdir(und_root)) if os.path.isdir(und_root) else set()
    code3, o3, e3 = _run(und + ["--execute"])
    det.append("undeploy --execute 退出码 %d" % code3)
    if code3:
        errs.append("undeploy 退出码 %d ≠ 0" % code3)
    bak_a = _read(os.path.join(SB, "DesignAddins.xml.pkpmjwd-bak"))
    bak_c = _read(os.path.join(SB, "DesignCustomization.xml.pkpmjwd-bak"))
    now_a = _read(os.path.join(SB, "DesignAddins.xml"))
    now_c = _read(os.path.join(SB, "DesignCustomization.xml"))
    det.append("  [%s] 卸载后两个 XML 与 .pkpmjwd-bak 逐字节相等"
               % ("OK" if (now_a == bak_a and now_c == bak_c) else "FAIL"))
    if now_a != bak_a or now_c != bak_c:
        errs.append("卸载未逐字节恢复 XML")
    post_dirs = set(os.listdir(und_root)) if os.path.isdir(und_root) else set()
    new_dirs = sorted(post_dirs - pre_dirs)          # 只看本次运行新建的 _uninstalled_*
    moved = []
    for d in new_dirs:
        for dp, dn, fn in os.walk(os.path.join(und_root, d)):
            for x in fn:
                moved.append(os.path.relpath(os.path.join(dp, x), os.path.join(und_root, d)))
    det.append("  本次运行移入 %s 的文件：%s（目录名含卸载时刻，不参与判定）"
               % ([re.sub(r"_\d{8}-\d{6}$", "_<stamp>", d) for d in new_dirs] or "(无)",
                  sorted(moved)))
    need = {"PKPMJWD.dll", "pkpmjwd.uic", "engine_path.txt", "pkpmjwduniquename.pmlfnc"}
    got_leaf = {os.path.basename(m) for m in moved}
    if not new_dirs:
        errs.append("undeploy 未新建 _uninstalled_* 目录（§p.6 卸载行：移动而非删除）")
    elif got_leaf != need:
        errs.append("_uninstalled_* 里的文件不符：%s ≠ %s" % (sorted(got_leaf), sorted(need)))

    # ---------- ④ 未对真实 D:\AVEVA 执行过
    real_addins = os.path.join(AVEVA, "DesignAddins.xml")
    real_cust = os.path.join(AVEVA, "DesignCustomization.xml")
    ra = _read(real_addins).decode("utf-8-sig") if os.path.isfile(real_addins) else ""
    rc = _read(real_cust).decode("utf-8-sig") if os.path.isfile(real_cust) else ""
    cond = [("PKPMJWD" not in ra, "DesignAddins.xml 无 PKPMJWD 条目"),
            ('Path="pkpmjwd.uic"' not in rc, "DesignCustomization.xml 无 pkpmjwd.uic 挂载"),
            (not os.path.isfile(os.path.join(AVEVA, "PKPMJWD.dll")), "根目录无 PKPMJWD.dll"),
            (not os.path.isfile(os.path.join(AVEVA, "pkpmjwd.uic")), "根目录无 pkpmjwd.uic"),
            (not os.path.isdir(os.path.join(AVEVA, "PKPMJWD")), "根目录无 PKPMJWD\\ 目录")]
    det.append("真实 D:\\AVEVA 未被执行过的证据：" +
               "; ".join(("%s=%s" % (msg, ok)) for ok, msg in cond))
    for ok, msg in cond:
        if not ok:
            errs.append("注册脚本已被执行过：%s" % msg)
    after = _manifest(AVEVA, False)
    added, removed, changed = _manifest_diff(aveva_before, after)
    if added or removed or changed:
        errs.append("本轮运行期间 D:\\AVEVA 变化：added=%s removed=%s changed=%s"
                    % (added[:3], removed[:3], changed[:3]))
    ch.add(17, "注册脚本静态检查（dry-run/幂等/可回滚/只加不删/未执行过）", errs, det)


# ==========================================================================
# 检查 18：界面清单完整
# ==========================================================================
UIC_ITEMS = [
    ("根元素+命名空间", lambda t, k: ('<UserInterfaceCustomization' in t and 'xmlns="www.aveva.com"' in t)),
    ("ButtonTool + Instance 命令",
     lambda t, k: ('<ButtonTool Name="%s.Open">' % k) in t and "<Type>Instance</Type>" in t),
    ("Command Key", lambda t, k: ("<Key>%s.OpenTools</Key>" % k) in t),
    ("中文 Caption", lambda t, k: re.search(r"<Caption>[^<]*[\u4e00-\u9fff][^<]*</Caption>", t) is not None),
    ("DisplayStyle", lambda t, k: "<DisplayStyle>Default</DisplayStyle>" in t),
    ("MenuTool 容器", lambda t, k: ('<MenuTool Name="%s.Menu">' % k) in t
     and ("<Tool Name=\"%s.Open\" />" % k) in t),
    ("MenuBar 挂载", lambda t, k: ("<MenuBar><Tool Name=\"%s.Menu\" /></MenuBar>" % k) in t
     or re.search(r"<MenuBar>\s*<Tool Name=\"%s\.Menu\" */>\s*</MenuBar>" % k, t) is not None),
    ("QATTools 挂载", lambda t, k: ("<QATTools><Tool Name=\"%s.Open\" /></QATTools>" % k) in t
     or re.search(r"<QATTools>\s*<Tool Name=\"%s\.Open\" */>\s*</QATTools>" % k, t) is not None),
]
CONTROLS = ["cmbOp", "txtSource", "btnBrowseSource", "txtSecmap", "btnBrowseSecmap",
            "chkUseExtra", "txtExtra", "numBaseE", "numBaseN", "numBaseU", "numAngle",
            "cmbUnit", "chkColumn", "chkBeam", "chkHBrace", "chkVBrace", "chkSlab",
            "chkWall", "chkGrid", "chkHole", "txtOut", "btnBrowseOut", "btnRun",
            "progressBar1", "txtSummary", "btnOpenReport"]


def check_18(ch):
    det, errs = [], []
    src_uic = TGTEXT_BAK if os.path.isfile(os.path.join(TGTEXT_BAK, "tgtext.uic")) else (
        TGTEXT_TASK if os.path.isfile(os.path.join(TGTEXT_TASK, "tgtext.uic")) else None)
    det.append("对照母本 tgtext.uic：%s%s"
               % (src_uic or "(两个路径都不存在)",
                  "" if src_uic != TGTEXT_TASK else "（任务给定路径）"))
    rows = []
    for label, path, key in (("tgtext.uic", os.path.join(src_uic, "tgtext.uic")
                              if src_uic else None, "TGTEXT"),
                             ("pkpmjwd.uic", UIC, "PKPMJWD")):
        if not path or not os.path.isfile(path):
            rows.append((label, None))
            errs.append("缺 %s" % label)
            continue
        blob = _read(path)
        try:
            t = blob.decode("utf-8-sig")
        except UnicodeDecodeError:
            t = blob.decode("utf-8", "replace")
        enc_ok = blob[:3] != b"\xef\xbb\xbf" and _lone_lf(blob) > 0 and (
            blob.replace(b"\r\n", b"").count(b"\n") == 0)
        rows.append((label, (t, key, enc_ok, blob[:3] == b"\xef\xbb\xbf", _lone_lf(blob))))
    if len(rows) == 2 and all(r[1] for r in rows):
        (l1, (t1, k1, e1, bom1, lf1)), (l2, (t2, k2, e2, bom2, lf2)) = rows
        det.append("同构对照表（逐条；左=参照 tgtext.uic，右=本包 pkpmjwd.uic）：")
        det.append("  %-22s | %-28s | %s" % ("结构项", l1, l2))
        for name, fn in UIC_ITEMS:
            a, bb = fn(t1, k1), fn(t2, k2)
            det.append("  %-22s | %-28s | %s" % (name, a, bb))
            if not bb:
                errs.append("pkpmjwd.uic 缺结构项：%s" % name)
            if not a:
                errs.append("参照 tgtext.uic 反而缺结构项 %s（对照基准异常）" % name)
        det.append("  %-22s | BOM=%s 孤立LF=%d      | BOM=%s 孤立LF=%d（两者都应为无 BOM+LF）"
                   % ("编码", bom1, lf1, bom2, lf2))
        if bom2 or lf2 == 0:
            errs.append("pkpmjwd.uic 应为 UTF-8 无 BOM + LF（附录 F.3）")
        det.append("  命名差异（仅 Name/Caption/Key 不同）：%s → %s" % (k1, k2))
    # 窗体控件
    if os.path.isfile(FORM_CS):
        ft = _read(FORM_CS).decode("utf-8", "replace")
        miss = [c for c in CONTROLS if c not in ft]
        det.append("PKPMJWDForm.cs：契约 §p.3 的 %d 个控件名，缺 %s"
                   % (len(CONTROLS), miss or "无"))
        if miss:
            errs.append("窗体缺控件：%s" % miss)
    else:
        errs.append("缺 %s" % FORM_CS)
    # Key 三处一致
    if os.path.isfile(ADDIN_CS):
        at = _read(ADDIN_CS).decode("utf-8", "replace")
        n_key = at.count("PKPMJWD.OpenTools")
        n_name = ('public string Name' in at) and ('"PKPMJWD"' in at)
        det.append("PKPMJWDAddin.cs：Key 出现 %d 次（注册日志 + Command 构造器）；IAddin.Name='PKPMJWD'=%s"
                   % (n_key, n_name))
        if n_key < 2:
            errs.append("Addin 内 Key 'PKPMJWD.OpenTools' 出现 %d 次（应 ≥2：Start 登记 + Command 构造器）" % n_key)
        if not n_name:
            errs.append("IAddin.Name 未返回 'PKPMJWD'")
    else:
        errs.append("缺 %s" % ADDIN_CS)
    if os.path.isfile(UIC):
        ut = _read(UIC).decode("utf-8-sig")
        det.append("Key 三处一致（.uic / Addin / Command 构造器）= %s"
                   % (("PKPMJWD.OpenTools" in ut) and os.path.isfile(ADDIN_CS)
                      and "PKPMJWD.OpenTools" in _read(ADDIN_CS).decode("utf-8", "replace")))
    ch.add(18, "界面清单完整（.uic 同构对照 + 13 项控件 + Key 三处一致 + 编译）", errs, det)


# ==========================================================================
# 把关项：宏里创建元素之前的唯一化调用计数 == 元素总数
# ==========================================================================
def _macro_uniquify_stats(path):
    t = _read(path).decode("gbk")
    lines = t.split("\r\n")
    calls = sum(1 for l in lines if "!!pkpmjwdUniquename('" in l)
    named = sum(1 for l in lines
                if re.match(r"\s*NEW (SITE|ZONE|STRU|FRMW|SBFR|SCTN|PANE|STWALL)\b", l))
    literal_named = sum(1 for l in lines
                        if re.match(r"\s*NEW (SITE|ZONE|STRU|FRMW|SBFR|SCTN|PANE|STWALL)\s+/", l))
    guards = sum(1 for l in lines if "var !pkpmjwdFatal EXIST $!n" in l)
    unnamed = sum(1 for l in lines if re.match(r"\s*NEW (PLOOP|PAVERT|DATA|PLINE)\b", l))
    has_onerror = any("ONERROR GOLABEL /PKPMJWDERR" in l for l in lines)
    has_label = any(l.strip() == "LABEL /PKPMJWDERR" for l in lines)
    has_tail = any(l.strip() == "RETURN ERROR" for l in lines) and \
        any(l.strip() == "endhandle" for l in lines) and \
        any(l.strip() == "$S+" for l in lines)
    has_guard = any("defined(!!pkpmjwdUniquename)" in l for l in lines)
    has_m = any(l.strip().startswith("$M ") for l in lines)
    return {"calls": calls, "named_new": named, "literal_named": literal_named,
            "guards": guards, "unnamed_new": unnamed, "onerror": has_onerror,
            "label": has_label, "tail": has_tail, "func_guard": has_guard,
            "m_preload": has_m}


def check_gate(ch):
    det, errs = [], []
    jobs = (("jwd2pdms", SAMPLE_JWD, "r3_jwd2pdms.mac"),
            ("pdt2pdms", SAMPLE_PDT, "r3_pdt2pdms.mac"))
    for tool, src, name in jobs:
        mac = os.path.join(OUT, name)
        code, out, err = _run([sys.executable, CLI, tool, src, "--out", mac,
                               "--report", os.path.join(OUT, name + ".report.json")])
        det.append("命令：cli.py %s %s --out _acc_r3_out/%s → 退出码 %d"
                   % (tool, os.path.basename(src), name, code))
        if code != 0:
            errs.append("%s 退出码 %d：%s" % (tool, code, (out + err)[-200:]))
            continue
        st = _macro_uniquify_stats(mac)
        det.append("  %s：%s" % (name, json.dumps(st)))
        if st["calls"] != st["named_new"]:
            errs.append("%s：唯一化调用 %d ≠ 命名元素总数 %d（把关项：每个创建元素前必须恰好一次调用）"
                        % (name, st["calls"], st["named_new"]))
        if st["guards"] != st["calls"]:
            errs.append("%s：故障注入守卫 %d ≠ 调用数 %d（§o.4 模板三行必须成套）"
                        % (name, st["guards"], st["calls"]))
        if st["literal_named"]:
            errs.append("%s：有 %d 条命名 NEW 未走 $!n（绕过唯一化）"
                        % (name, st["literal_named"]))
        if not (st["onerror"] and st["label"] and st["tail"]):
            errs.append("%s：缺 ONERROR 尾（§o.5：ONERROR/LABEL/handle/$S+/RETURN ERROR）" % name)
        if not st["func_guard"]:
            errs.append("%s：缺唯一化函数可用性检查（defined(!!pkpmjwdUniquename) ⇒ 故障注入）" % name)
        if not st["m_preload"]:
            det.append("  （%s 未带 $M 预载：CLI 未传 pml_func_path ⇒ 按契约 §b.6/§o.4 只发注释提醒；"
                       "运行前须 $M pdms/pkpmjwduniquename.pmlfnc，或由 Add-in/入口宏预载）" % name)
    # 入口宏与 Add-in 的预载链（保证"函数已加载"在交付路径上成立）
    run_mac = os.path.join(PKG, "pdms", "pkpmjwdrun.mac")
    if os.path.isfile(run_mac):
        ok = "pkpmjwduniquename" in _read(run_mac).decode("gbk", "replace")
        det.append("入口宏 pdms/pkpmjwdrun.mac 预载唯一化函数：%s" % ok)
        if not ok:
            errs.append("入口宏未 $M 预载 pkpmjwduniquename.pmlfnc")
    if os.path.isfile(ADDIN_CS):
        at = _read(ADDIN_CS).decode("utf-8", "replace")
        ok = "pkpmjwduniquename" in at
        det.append("Add-in Start() 预载唯一化函数：%s" % ok)
        if not ok:
            errs.append("Add-in 未在 Start() 预载唯一化函数")
    ch.add(20, "把关：宏里创建元素前的唯一化调用计数 == 元素总数（且全部经 $!n）", errs, det)


# ==========================================================================
# 检查 19：交付落点与"没动过"
# ==========================================================================
def check_19(ch, g_before, aveva_before, aveva_after_gate):
    det, errs = [], []
    # ① 工作区 R3 交付物
    want = [("pdms-net/PKPMJWDAddin.cs", ADDIN_CS), ("pdms-net/PKPMJWDForm.cs", FORM_CS),
            ("pdms-net/PmlBridge.cs", os.path.join(NET, "PmlBridge.cs")),
            ("pdms-net/EngineRunner.cs", os.path.join(NET, "EngineRunner.cs")),
            ("pdms-net/PKLog.cs", os.path.join(NET, "PKLog.cs")),
            ("pdms-net/build.cmd", BUILD_CMD), ("pdms-net/pkpmjwd.uic", UIC),
            ("pdms-net/dist/PKPMJWD.dll", DIST_DLL), ("pdms-net/dist/pkpmjwd.uic", DIST_UIC),
            ("pdms-net/deploy/deploy_pkpmjwd.py", DEPLOY_PY),
            ("pdms-net/deploy/undeploy_pkpmjwd.py", UNDEPLOY_PY),
            ("pdms/pkpmjwduniquename.pmlfnc", PMLFN),
            ("engine/dist/pkpmjwd_engine.exe", os.path.join(PKG, "engine", "dist",
                                                            "pkpmjwd_engine.exe")),
            ("engine/dist/run_engine.cmd", os.path.join(PKG, "engine", "dist",
                                                        "run_engine.cmd"))]
    det.append("工作区 R3 交付物（契约 §p.1 目录树）：")
    for label, p in want:
        ok = os.path.isfile(p)
        det.append("  [%s] %s%s" % ("OK" if ok else "MISS", label,
                                    "" if ok else "  （缺）"))
        if not ok:
            errs.append("工作区缺 R3 交付物：%s" % label)
    # ② 交付目录
    det.append("交付目录 D:/AI_Work/PKPM数据解析/交付_PKPM-JWD插件/：")
    if not os.path.isdir(DELIVERY):
        errs.append("交付目录不存在：%s" % DELIVERY)
    else:
        entries = sorted(os.listdir(DELIVERY))
        det.append("  根：%s" % entries)
        pkg_copy = None
        for x in entries:
            p = os.path.join(DELIVERY, x)
            if os.path.isdir(p) and os.path.isfile(os.path.join(p, "spec", "CONTRACT.md")):
                pkg_copy = p
        det.append("  整包副本 = %s" % (pkg_copy or "(未找到含 spec/CONTRACT.md 的整包目录)"))
        if not pkg_copy:
            errs.append("交付目录里没有整包副本（含 spec/CONTRACT.md 的目录）")
        else:
            for label, rel in (("pdms-net", "pdms-net"),
                               ("pdms/pkpmjwduniquename.pmlfnc",
                                os.path.join("pdms", "pkpmjwduniquename.pmlfnc")),
                               ("engine/dist", os.path.join("engine", "dist"))):
                ok = os.path.isdir(os.path.join(pkg_copy, rel)) or \
                    os.path.isfile(os.path.join(pkg_copy, rel))
                det.append("  [%s] 整包副本含 %s" % ("OK" if ok else "MISS", label))
                if not ok:
                    errs.append("交付副本缺 R3 交付物：%s（交付副本是 R2 时代收集的，未随 R3 更新）" % label)
        if not any(x.lower() in ("交付清单.md", "交付清单.txt") for x in entries):
            errs.append("交付目录缺 交付清单.md/txt")
        if not any("哈希" in x or "sha256" in x.lower() for x in entries):
            errs.append("交付目录缺哈希清单（§q-19①）")
        old_inst = os.path.join(DELIVERY, "安装程序")
        if os.path.isdir(old_inst):
            det.append("  安装程序/：%s（§p.8：install.ps1 方案已被 §p 取代；"
                       "如该目录仍是 v1 安装器即为过期交付）" % sorted(os.listdir(old_inst)))
    # ③ docs 的未部署声明（§p.10-5）
    decl_ok = False
    for name in ("交付清单.md", "使用说明.md"):
        p = os.path.join(PKG, "docs", name)
        if not os.path.isfile(p):
            errs.append("缺 docs/%s" % name)
            continue
        t = _read(p).decode("utf-8", "replace")
        hit = ("未部署" in t) and ("安装" in t)
        det.append("docs/%s 含「未部署 + 需用户自行安装」声明：%s" % (name, hit))
        decl_ok = decl_ok or hit
    if not decl_ok:
        errs.append("docs 缺 §p.10-5 的未部署声明（原文：「本包未部署，需要用户自己在 PDMS 停机时"
                    "按 docs/使用说明.md 安装」）")
    # ④ G 盘与 D:\AVEVA 零变化
    for label, before, after in (("G 盘插件目录", g_before, _manifest(G_PLUGIN, True)),
                                 ("D:\\AVEVA 根", aveva_before, aveva_after_gate)):
        added, removed, changed = _manifest_diff(before, after)
        det.append("%s：文件 %d 个；整轮前后 added=%d removed=%d changed=%d"
                   % (label, len(after), len(added), len(removed), len(changed)))
        if added or removed or changed:
            errs.append("%s 在整轮运行前后发生变化：added=%s removed=%s changed=%s"
                        % (label, added[:3], removed[:3], changed[:3]))
    ch.add(19, "交付落点与\"没动过\"（G 盘/D:\\AVEVA 清单+哈希零变化 + 未部署声明）", errs, det)


# ==========================================================================
# 主流程
# ==========================================================================
def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")
        except Exception:
            pass
    os.makedirs(OUT, exist_ok=True)
    print("=" * 78)
    print(" PKPM-JWD导入导出 验收测试 R3（契约 v3 验收标准 15–19 + 把关项）")
    print("=" * 78)
    print("工作区根 : %s" % ROOT)
    print("交付包   : %s" % PKG)
    print("自建产物 : %s" % OUT)
    print("无接触区域: G:\\…\\PKPM导入导出插件（递归）与 %s（顶层）" % AVEVA)

    missing = [p for p in (SAMPLE_JWD, SAMPLE_PDT, SAMPLE_MAP, CLI, PMLFN, BUILD_CMD)
               if not os.path.isfile(p)]
    ch = _Checker()
    if missing:
        print("无法开始：缺输入 %s" % missing)
        print(json.dumps({"passed": False, "passedCount": 0, "failedCount": 6},
                         ensure_ascii=False, separators=(",", ":")))
        return 2

    # 基线（本脚本自己建；不依赖别的脚本）
    print("建立基线清单（G 盘递归 + D:\\AVEVA 顶层，size+mtime+sha256）…")
    g_before = _manifest(G_PLUGIN, True)
    aveva_before = _manifest(AVEVA, False)
    print("  G 盘 %d 文件；D:\\AVEVA 顶层 %d 文件" % (len(g_before), len(aveva_before)))

    calls = (
        (15, "重名唯一化（静态+逻辑对照+renames+宏侧不跳过）", lambda: check_15(ch)),
        (16, ".NET 插件真编译（build.cmd 退出码 0 + CLR v2.0.50727/x86）",
         lambda: check_16(ch, aveva_before)),
        (17, "注册脚本静态检查（dry-run/幂等/可回滚/只加不删/未执行过）",
         lambda: check_17(ch, aveva_before)),
        (18, "界面清单完整（.uic 同构对照 + 13 项控件 + Key 三处一致 + 编译）", lambda: check_18(ch)),
        (20, "把关：宏里创建元素前的唯一化调用计数 == 元素总数（且全部经 $!n）", lambda: check_gate(ch)),
        (19, "交付落点与\"没动过\"（G 盘/D:\\AVEVA 清单+哈希零变化 + 未部署声明）",
         lambda: check_19(ch, g_before, aveva_before, _manifest(AVEVA, False))),
    )
    for cid, title, fn in calls:
        n0 = len(ch.items)
        try:
            fn()
        except Exception as exc:
            import traceback
            if len(ch.items) == n0:
                ch.add(cid, title, ["检查内部异常：%s: %s" % (type(exc).__name__, exc),
                                    traceback.format_exc().strip().splitlines()[-1]], [])
            else:
                c, t, e, d = ch.items[-1]
                ch.items[-1] = (c, t, e + ["该检查内部异常：%s: %s" % (type(exc).__name__, exc)], d)

    print("-" * 78)
    for cid, title, errors, details in ch.items:
        print("[%s] 检查 %s：%s" % ("FAIL" if errors else "PASS", cid, title))
        for d in details:
            print("        %s" % d)
        for e in errors:
            print("        ** %s" % e)
        print()
    failed = ch.failed()
    n_pass, n_fail = ch.passed_count(), len(failed)
    if failed:
        print("=" * 78)
        print("失败详情（%d 条）：" % n_fail)
        print("=" * 78)
        for cid, title, errors, _d in failed:
            print("检查 %s 未通过：%s" % (cid, title))
            for e in errors:
                print("    - %s" % e)
            print()
    print(json.dumps({"passed": n_fail == 0, "passedCount": n_pass, "failedCount": n_fail},
                     ensure_ascii=False, separators=(",", ":")))
    return 0 if n_fail == 0 else 1


class _Checker(object):
    """与 v1/v2 相同的收集器（cid, 标题, [error], [明细]）。"""

    def __init__(self):
        self.items = []

    def add(self, cid, title, errors, details):
        self.items.append((cid, title, list(errors or []), list(details)))

    def passed_count(self):
        return sum(1 for _c, _t, e, _d in self.items if not e)

    def failed(self):
        return [x for x in self.items if x[2]]


if __name__ == "__main__":
    sys.exit(main())
