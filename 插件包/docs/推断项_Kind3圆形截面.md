# 推断项：`Kind=3` 单尺寸截面判为圆形（直径）

> 状态：**推断（inferred）**，不是事实（resolved）。本文件是这一条的**唯一用户侧说明**；
> 交付文档阶段（S6）请把本文件并入 `docs/格式规范_JWD.md` 与 `docs/截面映射说明.md`
> （这两个文件本阶段尚不存在，`docs/` 下只有 `README.txt`）。
> 证据等级：**文件/行号级直证**（下面每条都给出文件:行，可自行复核）＋ **样本数据自检**；
> **未实机**（本机没有在 PDMS 里跑过导入宏）。

---

## 1. 结论

`JLCJ2.jwd` 里 12 根**屋面水平支撑**引用的截面（`pkpmBraceSect` ID=32335，`Name` 空、
`Kind=3`、`ShapeVal='3,20,5,32335,'`）在 PKPM 数据里**没有名字**、在用户匹配文件里
**没有条目**、在随包目录宏里**没有对应的现成规格**。按证据判定它是**圆形截面（实心圆钢），
唯一尺寸 20 = 直径**，因此导入宏里按 PDMS 的**用户参数化圆形族**建：

```
SPREF /USER_CIRCLE-SPEC/Circle_Profile
DESP 20
```

报告（`report.json`）里这条截面记成 `status='inferred'`（**不是** `resolved`），
并带 `evidence`（证据链）与 `reason`（残余风险与改法）；宏里该构件块**上方**有一行注释：

```
-- 推断截面（非原件映射，契约 §e.1a）：Kind=3 按证据判为族 CIRCLE → /USER_CIRCLE-SPEC/Circle_Profile；DESP = 20（单位 mm）；若实为别的族请改 engine/secmap_extra.txt 的 @FAMILY 行
```

## 2. 为什么需要一条"推断"（原来的死结）

* 验收标准 1 要求「每个构件都有 `SPREF` 或 `DESP`」——**字面**要求 811/811。
* 契约原本（旧 §12#5）把 `Kind=3` 冻结为 unresolved（"族别未定，不许猜"），
  于是这 12 根只能省略 `SPREF`，**字面判定必失败**。
* 而能"照抄"的规格在本样本里**并不存在**：随包目录宏 `PKPM（PDMS数据库）.txt` 的 2920 个
  截面里，最小的圆管是 `/TUBE_TUBE-SPEC/D32X2.5`（其次是 `/TUBE_TUBE50018-SPEC/D25X1.5`、
  `/TUBE_TUBE6728_2002-SPEC/D21.3*1.20`），**没有 20 mm 的圆形截面**。写一条不存在的规格
  只会让 PDMS 导入报错——那不是"修好"，那是伪造。

## 3. 证据链（每条都可用只读方式复核）

| # | 证据 | 说明 |
|---|---|---|
| ① | `1_PM.pdt:2387-2388`：`ID=1009, NAME=圆形4800, SHAPE=3` / `KIND=3, B1=4800, B2=0, H1=0, …` | 插件自己的 PDMS→PKPM 方向里，`SHAPE/KIND=3` 就是"**圆形**"，且 `B1` 承载**直径**（4800 mm）。这是 `_recon/jwd_format.md` §9.3#1 当初要求"取含 Kind=3 的其他模型来确认"的那个证据 |
| ② | 同一 `JLCJ2.jwd`：`pkpmBraceSect` ID=62965 的 `Name='薄壁方钢管: B20'`，`Kind=303` | 作者把**方管**归到 `Kind=303` ⇒ `Kind=3` 不是方管（排除了当初的另一个候选"200 方管"） |
| ③ | `PKPM（PDMS数据库）.txt:2494,2502-2513,3026`：`NEW STCATEGORY /USER_CIRCLE` + `NEW DTSET` 里**只有一个**参数 `DKEY D / PTYP DIST / PPRO ( ATTRIB DESP[1] ) / DPRO ( 300 ) / NUMB 1`，以及 `NEW SPCOMPONENT /USER_CIRCLE-SPEC/Circle_Profile` | 该族的 `DESP` 只有 1 个参数（直径）⇒ `Kind=3` 的单个尺寸正好对应；`DESP 20` 就是这个参数。（注意 `DPRO` 默认是 **300**：**不写 `DESP` 会建出 φ300**，这正是必须写 `DESP` 的原因） |
| ④ | `PKPM转PDMS截面匹配文件.txt:27`：`CIRCLE, /USER_CIRCLE-SPEC/Circle_Profile` | 用户原件自己的约定：圆形族 → 该规格 |

复核命令（只读，本机 Python 3.12）：

```bat
python -X utf8 -c "print(open(r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\1_PM.pdt','rb').read().decode('gbk').splitlines()[2386:2389])"
python -X utf8 -c "import sqlite3;c=sqlite3.connect('file:G:/工作/PDMS相关/00 PDMS插件/02 实用插件/PKPM导入导出插件/JLCJ2.jwd?mode=ro',uri=True);c.text_factory=bytes;print([r for r in c.execute('select ID,No_,Name,Mat,Kind,ShapeVal from pkpmBraceSect')])"
```

## 4. 残余风险（必须随交付物一起给用户）

1. **不能 100% 排除** `d=20` 是别的单尺寸族（例如别的圆形截面族的写法），也不能 100% 证明
   单位一定是 mm（本包全部长度量均为 mm，且 ② 的方管 20 → 200 mm 说明该列的数值需要按
   族别理解）。证据强度：**中-高**（4 条独立旁证一致）。
2. 若判定错了，后果是**这 12 根支撑的截面不对**（会被建成 φ20 实心圆）；其余 799 根构件不受影响。
3. **未实机验证**：本包所有 PDMS 语法都只做过静态核对（本机 PML 源码出处见 `spec/CONTRACT.md` §d.3），
   导入宏没有在 PDMS 12.1 SP4 里真正跑过。实机时请优先看这 12 根。

## 5. 怎么改（一行搞定）／怎么回滚

改 **`engine/secmap_extra.txt`** 里的指令行（不要改用户原件）：

```
@FAMILY 3 = CIRCLE      ← 现状（启用推断：圆形族 + DESP <直径>）
@FAMILY 3 = none        ← 停止推断：这 12 根回到"未解析"，宏里只留 -- UNRESOLVED SECTION 标记
```

* 想换成别的族：把 `CIRCLE` 改成契约 §e.3 里有证据的族键（当前已知族键见
  `engine/secmap.py` 的 `FAMILY_SPEC`）；写成未知族键**不会生效**，只在报告 `warnings` 里记一条。
* 也可以完全不改这一行，改用**兜底键**点名某个真实规格（契约 §e.1 候选键 5），
  例如在 `engine/secmap_extra.txt` 里加 `3#20, /你的规格库/你的截面`。
* ⚠ 注意：**改成 `none` 之后，验收标准 1「每个构件都有 SPREF 或 DESP」会不成立**
  （12/811 根没有规格引用）。这是**故意的**取舍：宁可少写规格，也不写没证据的规格。

## 6. 授权与落地位置

* 授权：本工作流编排方明确裁决"走有证据支持的契约修订"（不是实施者自拍板），
  并逐条复核了上面 4 条证据。
* 契约：`spec/CONTRACT.md` §0.4 变更记录 #1-#3、§e.1a、§e.3（Kind=3 行）、§e.4a、§e.5a、
  §d.4-2b、§d.4-3、§h、§12#5。
* 数据（唯一的开关）：`engine/secmap_extra.txt` 的 `@FAMILY 3 = CIRCLE`。
* 代码：`engine/secmap.py`（指令解析 + `_inferred()`）、`engine/macgen.py`（DESP 与推断注释）、
  `engine/cli.py`（报告 `inferred` 计数与警告）、`engine/canonical.py`（`INFERRED` 状态与 `evidence`）。
* 测试：`test/acceptance.py` 检查 1（字面判定 + 推断构件的 `DESP` 值与注释）与检查 2
  （独立复算期望 `status='inferred'`、`evidence` 非空、不混进 `unresolved`）。
