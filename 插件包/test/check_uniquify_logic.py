# -*- coding: utf-8 -*-
"""唯一化函数的逻辑等价自测（CONTRACT v3 §o / 附录 F.1）。

⚠ 这是 **逻辑等价复刻，不是 PML 实机**：本包全程未启动 PDMS（本轮范围边界），
  PML 函数 !!pkpmjwdUniquename 本身无法在 Python 里执行。本脚本把
  pdms/pkpmjwduniquename.pmlfnc 的**算法**逐条复刻成 Python（同一候选序列、
  同一记录格式、同一 FAIL 语义），对它做单元断言。

与 PML 的对应关系（逐条）：
  PML `do !idx from 0 to 99` + idx==0/1/else 三分支  → candidates(base)（100 个）
  PML `var !probe EXIST /$!cand` 两种已证实结局       → occupied 集合查询：
        (2,109) 命中 ⇒ 可用（契约 §o.3 写法①冻结语义）
        VAR 正常返回 'FALSEA' ⇒ 可用 / 'TRUEA' ⇒ 占用
      两种结局在逻辑层都归约为「cand 不在 occupied ⇒ 可用」
  PML `!!pkpmjwdRenames.append(...)`                 → renames.append(...)
  PML 记录 'TYPE|原名|实际名'（TYPE 取 !!pkpmjwdType） → ('TYPE', 原名, 实际名) 三元组
  PML `!!pkpmjwdRenames.append('FAIL|' & base & '|' & base & 're99')` + return ''
                                                      → ('FAIL', base, base+'re99') + None
  PML 空基名 append('FAIL||') + return ''             → ('FAIL', '', '') + None

场景（任务指定）：库里已有 NAME、NAMEre ⇒ 返回 NAMEre2。
另覆盖：全新库、仅 NAME 占用、re 链逐级占用、全部占用（含 re99）⇒ FAIL、
空基名、跨调用累计（对应窗体"本次/累计"差值显示）。

用法： python test\\check_uniquify_logic.py     退出码 0=全过 / 1=有 FAIL
"""
import sys

RE_MAX = 99  # §o.1：候选 = base, base&'re', base&'re2'..'base&'re99'


def candidates(base):
    """PML: if idx==0 → base; elseif idx==1 → base&'re'; else → base&'re'&idx.string()"""
    out = [base, base + 're']
    out += ['%sre%d' % (base, i) for i in range(2, RE_MAX + 1)]
    return out


class PmlWorld:
    """PML 运行期的最小模型： occupied = 库里已有名字；renames = !!pkpmjwdRenames。"""

    def __init__(self, occupied=()):
        self.occupied = set(occupied)
        self.renames = []          # ('TYPE'|'FAIL', 原名, 实际名)
        self.type_var = None       # !!pkpmjwdType

    # PML: var !probe EXIST /$!cand —— 值判定（'TRUEA'=占用）+ (2,109)=可用 的逻辑归约
    def probe_occupied(self, cand):
        return cand in self.occupied

    # PML: !!pkpmjwdUniquename
    def uniquename(self, base):
        if base is None or len(base) == 0:            # PML: unset / length() le 0
            self.renames.append(('FAIL', '', ''))
            return ''
        t = self.type_var if self.type_var else '?'   # PML: defined(!!pkpmjwdType)
        final = ''
        for idx, cand in enumerate(candidates(base)):  # PML: do !idx from 0 to 99
            if not self.probe_occupied(cand):          # 可用（两种探测结局的归约）
                final = cand
                if cand != base:                       # PML: 原名可用不留痕
                    self.renames.append((t, base, cand))
                break                                  # PML: break（assybuildname:71 同款）
        if final:
            return final
        self.renames.append(('FAIL', base, base + 're99'))  # PML: §o.6
        return ''


# ---------------------------------------------------------------- 断言器
FAILS = []
N = [0]


def check(cond, label, detail=''):
    N[0] += 1
    tag = 'PASS' if cond else 'FAIL'
    print('  %-4s %s%s' % (tag, label, ('   [%s]' % detail) if detail else ''))
    if not cond:
        FAILS.append(label)


def main():
    print('=' * 76)
    print('唯一化逻辑等价自测（Python 复刻 pdms/pkpmjwduniquename.pmlfnc；非 PML 实机）')
    print('=' * 76)

    # 1) 候选序列形状（§o.1）
    print('--- 1. 候选序列（§o.1）')
    seq = candidates('/STL_COL_1')
    check(len(seq) == 100, '候选总数 = 100', str(len(seq)))
    check(seq[0] == '/STL_COL_1', 'idx 0 → 原名', seq[0])
    check(seq[1] == '/STL_COL_1re', "idx 1 → 原名 & 're'（直接拼接，无分隔符）", seq[1])
    check(seq[2] == '/STL_COL_1re2' and seq[3] == '/STL_COL_1re3', 'idx 2/3 → re2/re3', '%s %s' % (seq[2], seq[3]))
    check(seq[-1] == '/STL_COL_1re99', 'idx 99 → re99（上限）', seq[-1])

    # 2) 任务指定场景：库里已有 NAME、NAMEre ⇒ NAMEre2
    print('--- 2. 任务指定场景（NAME / NAMEre 已占用）')
    w = PmlWorld({'NAME', 'NAMEre'})
    w.type_var = 'SCTN'
    got = w.uniquename('NAME')
    check(got == 'NAMEre2', 'NAME 与 NAMEre 都被占用 → 返回 NAMEre2', got)
    check(w.renames == [('SCTN', 'NAME', 'NAMEre2')],
          '留痕一条 SCTN|NAME|NAMEre2（原名不可用才留痕）', str(w.renames))

    # 3) 全新库：原名可用，不留痕（§o.7：renames 空 = 全部原名可用）
    print('--- 3. 全新库')
    w = PmlWorld()
    w.type_var = 'SITE'
    got = w.uniquename('/PKPM_JWD')
    check(got == '/PKPM_JWD', '全新库 → 原名', got)
    check(w.renames == [], '不留改名记录', str(w.renames))

    # 4) 仅 NAME 占用 → NAMEre（契约附录 F/check_v3_contract 的同款场景）
    print('--- 4. 仅原名占用')
    w = PmlWorld({'NAME'})
    w.type_var = 'SCTN'
    got = w.uniquename('NAME')
    check(got == 'NAMEre', 'NAME 占用 → NAMEre', got)
    check(w.renames == [('SCTN', 'NAME', 'NAMEre')], '留痕 SCTN|NAME|NAMEre', str(w.renames))

    # 5) re 链逐级占用 + 跨调用累计（对应窗体"本次/累计"差值）
    #    注：宏拿到返回名后会 NEW <TYPE> 该名（§o.4 模板），故每次调用后把返回名
    #    加回 occupied，模拟"库里已建"——这正是 PML 运行期的真实时序。
    print('--- 5. re 链逐级占用与跨调用累计')
    w = PmlWorld({'/X', '/Xre', '/Xre2'})
    w.type_var = 'SBFR'
    got = w.uniquename('/X')
    check(got == '/Xre3', 'X/Xre/Xre2 占用 → Xre3', '/Xre3')
    w.occupied.add(got)                        # 宏执行 NEW SBFR /Xre3
    got = w.uniquename('/X')
    check(got == '/Xre4', '再次调用（/Xre3 已建）→ Xre4', '/Xre4')
    w.occupied.add(got)                        # 宏执行 NEW SBFR /Xre4
    check(w.uniquename('/X') == '/Xre5', '第三次调用 → Xre5', '/Xre5')
    occupied = set(candidates('/X'))            # 全部 100 个都占用
    w2 = PmlWorld(occupied)
    w2.type_var = 'SCTN'
    got = w2.uniquename('/X')
    check(got == '', '全部占用（含 re99）→ 返回空串（§o.6，宏将中止）', repr(got))
    check(w2.renames == [('FAIL', '/X', '/Xre99')], 'FAIL 留痕 FAIL|/X|/Xre99', str(w2.renames))

    # 6) 空基名
    print('--- 6. 空基名（编码错误）')
    w = PmlWorld()
    got = w.uniquename('')
    check(got == '', '空基名 → 返回空串', repr(got))
    check(w.renames == [('FAIL', '', '')], "留痕 'FAIL||'（F.1 夹具同款）", str(w.renames))

    # 7) 窗体显示口径：本次 = (累计改名, 累计FAIL) 的差值
    print('--- 7. 窗体「本次改名 N 个」的差值口径')
    w = PmlWorld({'NAME'})
    w.type_var = 'SCTN'
    t0, f0 = len(w.renames), sum(1 for r in w.renames if r[0] == 'FAIL')
    w.uniquename('NAME')          # 本次：1 次改名
    w.uniquename('OTHER')         # 本次：原名可用，0 改名
    w.uniquename('')              # 本次：1 次 FAIL
    t1, f1 = len(w.renames), sum(1 for r in w.renames if r[0] == 'FAIL')
    renamed = (t1 - f1) - (t0 - f0)
    fails = f1 - f0
    check(renamed == 1 and fails == 1, '本次改名 1 个、失败 1 个（PML runMac 同一算式）',
          'renamed=%d fails=%d' % (renamed, fails))

    print('-' * 76)
    print('汇总：断言 %d 项，FAIL %d 项' % (N[0], len(FAILS)))
    print('结论：%s' % ('全部通过' if not FAILS else '存在 FAIL：' + '; '.join(FAILS)))
    print('（再次强调：这是 PML 逻辑的等价复刻自测，PML 本身未在 PDMS 实机运行）')
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
