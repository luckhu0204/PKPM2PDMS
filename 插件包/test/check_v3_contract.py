# -*- coding: utf-8 -*-
r"""C15：R3 契约静态自检（架构包）。对应 CONTRACT 附录 G。

检查项：
  1. 附录 F.1 唯一化函数夹具：签名 / EXIST+(2,109) 探测 / re 序列与 re99 上限 / defined /
     append / FAIL 返回空串 / 出处注释齐全
  2. 唯一化候选序列的 Python 参考实现（验收 15-②）：base → re → re2 … re99，共 100 个，
     全占用 ⇒ FAIL；与夹具的算法语义一致
  3. 附录 F.2 宏片段：ONERROR GOLABEL / 故障注入 / LABEL 尾 / $M 预载
  4. 附录 F.3：本契约 §p.3 的 .uic 描述与 tgtext.uic 同构对照表存在且 Key 三处一致
     （.uic Key = Addin Command Key = "PKPMJWD.OpenTools"）
  5. §h 的 renames 键、§p.3 的 13 项控件名、§q 验收 15–19、§12#26–29 存在
  6. CONTRACT.md 表格列数自检
  7. 无接触基准可核对（C14 的 verify 直接由独立脚本承担，这里只检查基准文件存在）

运行：python test/check_v3_contract.py
"""
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
DOC = os.path.join(PKG, 'spec', 'CONTRACT.md')
BASE = os.path.join(HERE, '_v3_csc_check', '_baseline')

doc = open(DOC, encoding='utf-8').read()
fails = []


def check(cond, label, detail=''):
    print('  [%s] %s %s' % ('OK' if cond else 'FAIL', label, detail))
    if not cond:
        fails.append(label)


# ------------------------------------------------- 1. F.1 uniquify fixture
print('=== 1. 附录 F.1 唯一化函数夹具 ===')
fixtures = re.findall(r'```pml\r?\n(.*?)```', doc, re.S)
# 契约里有 6 个 ```pml 块（§o.2 签名/§o.4 片段/§o.4 模板/§o.5 尾/F.1 函数/F.2 宏片段），按内容定位
fx = next((b for b in fixtures if 'define function !!pkpmjwdUniquename' in b
           and 'EXIST' in b), '')
mac = next((b for b in fixtures if 'ONERROR GOLABEL /PKPMJWDERR' in b
            and 'NEW SCTN $!n' in b and 'LABEL /PKPMJWDERR' in b), '')
check(len(fixtures) >= 6, '找到 pml 夹具（§o.2/§o.4×2/§o.5/F.1/F.2）', '%d 块' % len(fixtures))
check(bool(fx), 'F.1 函数夹具定位成功')
check(bool(mac), 'F.2 宏片段定位成功')
check('define function !!pkpmjwdUniquename(!base is STRING) is STRING' in fx,
      '函数签名与 §o.2 一致')
check('var !probe EXIST $!cand' in fx, '占用探测写法①（EXIST $!x，base 自带 /；§0.4-12）')
check('EXIST /$!cand' not in fx, '旧形 //名 探测已禁用（§0.4-12：全库 0 例的未证实形态）')
check('handle (2,109)' in fx, 'handle (2,109)（Undefined name ⇒ 可用）')
check("from 0 to 99" in fx, '候选上限 re99（do 0..99，共 100 个）')
check("!base & 're'" in fx, "后缀 re 直接拼接")
check('defined(!!pkpmjwdRenames)' in fx, 'defined() 守卫（nucdesogwall.pmlobj:206）')
check('!!pkpmjwdRenames = object ARRAY()' in fx, '全局数组建立')
check('.append(' in fx, 'append 记录（GRIDDESIGN.pmlfrm:986）')
check("'FAIL|'" in fx and "'FAIL|' & !base" in fx, 'FAIL 留痕条目')
check('abaarealib.pmlfrm:107-114' in fx, '探测写法的出处注释在夹具内')
check('abaarea.pmlfrm:527' in fx, 'handle 内 return 的出处注释在夹具内')

# ------------------------------------------------- 2. candidate sequence sim
print('\n=== 2. 候选序列参考实现（验收 15-② 的逻辑对照） ===')


def candidates(base):
    out = [base, base + 're']
    out += ['%sre%d' % (base, i) for i in range(2, 100)]
    return out


def uniquify(base, occupied):
    for c in candidates(base):
        if c not in occupied:
            return c, ('renamed' if c != base else 'original')
    return None, 'fail'


seq = candidates('/STL_COL_1')
check(len(seq) == 100, '候选数 = 100', str(len(seq)))
check(seq[0] == '/STL_COL_1' and seq[1] == '/STL_COL_1re' and seq[2] == '/STL_COL_1re2'
      and seq[-1] == '/STL_COL_1re99', '序列形态', '%s … %s' % (seq[1], seq[-1]))
occ = set(['/STL_COL_1'])
name, why = uniquify('/STL_COL_1', occ)
check(name == '/STL_COL_1re' and why == 'renamed', '原名占用 → re', name)
occ |= {name, '/STL_COL_1re2', '/STL_COL_1re3'}
name, why = uniquify('/STL_COL_1', occ)
check(name == '/STL_COL_1re4', 're2/re3 也占用 → re4', name)
occ |= set(seq)
name, why = uniquify('/STL_COL_1', occ)
check(name is None and why == 'fail', '全占用（含 re99）→ FAIL（报错中止，不跳过）', str(why))
occ2 = set()
name, why = uniquify('/STL_COL_1', occ2)
check(name == '/STL_COL_1' and why == 'original', '全新环境 → 原名，不产生改名记录')

# ------------------------------------------------- 3. F.2 macro fragment
print('\n=== 3. 附录 F.2 宏片段 ===')
check(bool(mac), 'F.2 宏片段已定位（见上）')
check('ONERROR GOLABEL /PKPMJWDERR' in mac, 'ONERROR 尾（DB Listing 同构，出处 L5）')
check("$M <$!pkpmjwdFuncPath>" in mac, '$M 预载唯一化函数（§o.4）')
check('if (!n eq \'\') then' in mac, '空名检查（eq 运算符，出处 sdnfinver3:113）')
check('var !pkpmjwdFatal EXIST $!n' in mac, '故障注入（§12#27；§0.4-12 形态 = EXIST $!n）')
check('!!pkpmjwdType =' in mac, 'TYPE 通道 = 双 ! 全局（§0.4-12：跨作用域传给函数）')
check('LABEL /PKPMJWDERR' in mac and 'handle ANY' in mac and 'RETURN ERROR' in mac
      and 'endhandle' in mac, '宏尾四件套')
check('NEW SCTN $!n' in mac, '创建命令用唯一化结果')

# ------------------------------------------------- 4. §p.3 uic + key consistency
print('\n=== 4. §p.3 界面与 Command Key 一致性 ===')
uic = re.search(r'```xml\r?\n(<ButtonTool Name="PKPMJWD\.Open".*?)```', doc, re.S)
check(uic is not None, '找到 §p.3 的 .uic 片段')
u = uic.group(1) if uic else ''
check('<Key>PKPMJWD.OpenTools</Key>' in u, '.uic 的 Command Key')
check('<Caption>PKPM JWD 导入导出</Caption>' in u, '中文 Caption（对照 tgtext.uic:12 中文直排）')
check('<MenuTool Name="PKPMJWD.Menu">' in u, 'MenuTool 容器（对照 tgtext.uic:15-22）')
check(doc.count('PKPMJWD.OpenTools') >= 3, 'Key 三处一致（.uic/Addin/Command）',
      '出现 %d 次' % doc.count('PKPMJWD.OpenTools'))
# F.3 对照表
check('| 结构项 | tgtext.uic（备份副本，行号） | pkpmjwd.uic（本包） |' in doc,
      'F.3 同构对照表存在')

# ------------------------------------------------- 5. contract-wide keys
print('\n=== 5. 契约级键与验收 ===')
check('"renames"' in doc and '§o.7' in doc, '§h 的 renames 键')
for ctl in ('cmbOp', 'txtSource', 'btnBrowseSource', 'txtSecmap', 'chkUseExtra',
            'numBaseE', 'numBaseN', 'numBaseU', 'numAngle', 'cmbUnit',
            'chkColumn', 'chkBeam', 'chkHBrace', 'chkVBrace', 'chkSlab', 'chkWall',
            'chkGrid', 'chkHole', 'txtOut', 'btnBrowseOut', 'btnRun',
            'progressBar1', 'txtSummary', 'btnOpenReport'):
    if ctl not in doc:
        check(False, '§p.3 控件缺失', ctl)
        break
else:
    check(True, '§p.3 控件清单齐全（13 项 / 24 个控件名）')
for acc in ('| 15 |', '| 16 |', '| 17 |', '| 18 |', '| 19 |'):
    check(acc in doc, '验收标准存在 %s' % acc.strip('| '))
for row in ('| 26 **〔R3〕**', '| 27 **〔R3〕**', '| 28 **〔R3〕**', '| 29 **〔R3〕**'):
    check(row in doc, '§12 行存在 %s' % row)
check('不部署' in doc and '不启动 PDMS' in doc and '不写 G 盘' in doc and 'D:\\AVEVA' in doc,
      '§p.10 四条硬边界')
check('PKPM-JWD导入导出/pdms/pkpmjwduniquename.pmlfnc'.replace('/', '\\') in doc
      or 'pdms/pkpmjwduniquename.pmlfnc' in doc, 'PML 函数落点写明')
check('PDMS三维文字程序' in doc and '备份' in doc, 'F.6 记录了样例路径差异（任务给的路径已不存在）')

# ------------------------------------------------- 6. markdown tables
print('\n=== 6. Markdown 表格 ===')
SEP = re.compile(r'^\|[\s:\-|]+\|$')


def ncols(s):
    return s.replace('\\|', '').count('|') - 1


dl = doc.split('\n')
bad = []
i = 0
while i < len(dl):
    ln = dl[i].strip()
    if ln.startswith('|') and ln.endswith('|') and i + 1 < len(dl) and SEP.match(dl[i + 1].strip()):
        want = ncols(ln)
        j = i
        while j < len(dl):
            s = dl[j].strip()
            if not (s.startswith('|') and s.endswith('|')):
                break
            if not SEP.match(s) and ncols(s) != want:
                bad.append((j + 1, want, ncols(s)))
            j += 1
        i = j
    else:
        i += 1
check(not bad, '表格列数一致', str(bad[:5]))

# ------------------------------------------------- 7. baselines exist
print('\n=== 7. 无接触基准（C14 的 verify 由 check_v3_notouch.py 承担） ===')
for key in ('g_plugin', 'aveva_root'):
    check(os.path.exists(os.path.join(BASE, key + '.json')), '基准存在 ' + key)

print('\n=== 结论 ===')
print('CONTRACT.md 行数 = %d' % (doc.count('\n') + 1))
print('FAIL 项: %d %s' % (len(fails), fails if fails else ''))
sys.exit(1 if fails else 0)
