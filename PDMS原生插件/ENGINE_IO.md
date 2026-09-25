# ENGINE_IO.md —— .NET 插件 ⇄ Python 引擎 调用约定（v1.0）

> 本文是 `pdms-net/`（.NET 侧）与 `engine/`（Python 侧）共同遵守的**调用约定**。
> 条文来源：`spec/CONTRACT.md` §p.5（引擎调用，冻结）、§m〔R3〕`--request`（全局选项）、
> §f.2（退出码）、§f.1/§m.1（报告缺省路径）、§h（report.json 结构）与 §o.7（`renames`）。
> **任何一方要改本文，先改契约对应条文（§0.3 变更规则），再改两端代码**；两端不许分叉。

---

## 0. 一图流

```
PKPMJWDForm（PDMS 原生窗体）
   │ ①校验输入  ②写 request JSON  ③进程调用引擎（同步等待，≤30 min）
   ▼
EngineRunner.Run(tool, args)                    pdms-net/EngineRunner.cs:73
   │  <engine_entry> --request "%TEMP%\PKPMJWD\<op>-<时间戳>.json"
   ▼
engine\dist\pkpmjwd_engine.exe   （或 run_engine.cmd 回退，见 §2）
   │  cli.py main() --request 分支（engine/cli.py:2331-2356）
   │  还原成等价命令行 ⇒ 同一个 argparse/_dispatch（与用户命令行零分叉）
   ▼
report.json（§h）+ 产物（.mac/.jwd/.pdt/.csv）+ stdout 摘要（UTF-8）
   │  ④建模方向：PmlBridge.RunPml("$M <生成的 .mac>")（宏内含 §o 唯一化）
   │  ④'取回 !!pkpmjwdRenames ⇒ <report>.renames.txt + 窗体摘要
   ▼
⑤txtSummary 摘要 / btnOpenReport 打开报告 / 失败 ⇒ MessageBox + addin.log
```

---

## 1. 引擎入口的解析顺序（冻结，`EngineRunner.ResolveEntry`，pdms-net/EngineRunner.cs:42-68）

| # | 来源 | 说明 |
|---|---|---|
| 1 | 环境变量 `PKPMJWD_ENGINE` | 绝对路径；存在即用（优先级最高，测试/临时覆盖用） |
| 2 | `<PDMS根>\PKPMJWD\engine_path.txt` | deploy 脚本写入（§p.6-5）；**UTF-8 无 BOM 单行**，内容 = 引擎入口绝对路径；读取用 `new UTF8Encoding(false)`（EngineRunner.cs:54） |
| 3 | `<DLL所在目录>\..\..\engine\dist\pkpmjwd_engine.exe` | 工作区直跑场景（`AppDomain.CurrentDomain.BaseDirectory` 起） |
| 4 | 同目录 `run_engine.cmd` | 上一步 exe 不存在时的回退包装器（§p.1/§12#29） |

`<PDMS根>` 在 .NET 侧取 `AppDomain.CurrentDomain.BaseDirectory`（PKLog.cs:18-22，与 TGSPEC/TGTEXT
同构取法）：部署后 = PDMS 安装根；工作区自测 = `dist\`。`engine_path.txt`、`addin.log`、
`pml\pkpmjwduniquename.pmlfnc` 都在它下面的 `PKPMJWD\` 子目录。

**两种入口形态**（§12#29）：

* `pkpmjwd_engine.exe` —— 构建期用 PyInstaller `--onefile` 打包 `engine/cli.py`
  （本机 PyInstaller 6.22.2 可用，已打包：8,866,520 B，2026-09-25 实测 RC=0）。
* `run_engine.cmd` —— exe 不存在时的回退：先 `py -3.12` 定位 Python 3.12，再退到 PATH 上的
  `python`，然后执行 `"%PY%" "%~dp0..\cli.py" %*`（参数原样透传，含 `--request`）。
  文件为 **ASCII + CRLF**（契约 §g 纪律 6；§p.2 的实测教训：LF/非 ASCII 注释会被 cmd 误解析）。

**重建命令**（在 `engine\` 下原样执行；数据文件必须一并打进去，见 §6）：

```bat
python -m PyInstaller --onefile --noconfirm --name pkpmjwd_engine ^
  --distpath dist --workpath dist\_pybuild --specpath dist\_pybuild ^
  --add-data "D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\engine\secmap_extra.txt;." ^
  --add-data "D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\engine\section_table.csv;." ^
  --add-data "D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\engine\section_table.meta.json;." ^
  "D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出\engine\cli.py"
```

> 打包里带这三个数据文件的原因：`secmap.DEFAULT_EXTRA_FILE`（secmap.py:52-53）与
> `sectionlib.BUILTIN_TABLE/BUILTIN_META`（sectionlib.py:113-114）都按"模块所在目录"解析，
> 冻结后指向 `_MEIPASS`，不带就会退化为"补充文件不存在 ⇒ 不加载"（§e.4 的缺省行为悄悄变化）。
> 重建后必须跑一遍 §7 的冒烟用例再交付。

---

## 2. 调用协议（冻结，§p.5 / §m〔R3〕）

```
<engine_entry> --request <request 文件>
```

* **request 文件**：UTF-8（无 BOM；引擎按 `utf-8-sig` 读，容忍 BOM），JSON 对象：

```jsonc
{
  "tool": "jwd2pdms",        // §m.1 的子命令名（窗体用其中 10 个，dbsections 不进窗体，§p.3-1）
  "args": { …该子命令的全部参数… }   // 键名与 CLI 完全一致，见 §3
}
```

* `.NET` 侧把 request 写到 `%TEMP%\PKPMJWD\<op>-<yyyyMMdd-HHmmss>.json`
  （EngineRunner.cs:86-90，UTF-8 无 BOM），并把路径作为**唯一**命令行参数传给引擎。
* 引擎行为（engine/cli.py:2331-2356）：识别首个 token `--request` ⇒ 读文件（`_load_request`，
  cli.py:2314-2328）⇒ 还原成**等价命令行**（`_request_to_argv`，cli.py:2240-2311）⇒ 交给与命令行
  **同一个** `build_parser()/parse_args()/_dispatch()`。§f.1/§m.1 的缺省值、校验、退出码、报告规则
  因此逐字一致（契约 §p.5：「与命令行**同一执行函数**，不许分叉」）。
* request 文件是**一次性**通信物：.NET 不复用、引擎不回写；保留在 `%TEMP%\PKPMJWD\` 供排障。

---

## 3. `args` 的键约定（与 pdms-net/EngineRunner.cs:17-18、71-72 的跨包对齐点）

* **键 = CLI 长选项名去前导 `--`**（= argparse dest）：`out`、`secmap`、`extra`、`project`、
  `base`、`angle`、`unit`、`report`、`dump_unit`、`skeleton`、`suffix`、`clean`、
  `catalogue_user`、`catalogue_stss`、`from_builtin`、`format`。
  连字符选项两种写法都收：`dump-unit`/`dump_unit`、`from-builtin`/`from_builtin`、
  `catalogue-user`/`catalogue_user`（引擎按 dest 归一，cli.py:2278 的 `key.replace("-","_")`）。
* **位置参数用子命令自己的 dest 名**：`jwd`（jwd2pdms/jwd2db/jwd2pdt）、`pdt`
  （pdt2pdms/pdt2db/pdt2jwd/pdt2model）、`dump`（pdms2jwd/pdms2pdt）、`db`（db2jwd/db2pdt/dbsections）。
  引擎按**该子命令 parser 的位置 dest 顺序**落位（cli.py:2263-2272 的内省，不靠手写表）。
* **值类型映射**（EngineRunner.cs:142-181 的 `BuildRequest` ⇔ cli.py:2291-2300 的还原）：

  | .NET 值 | JSON | 引擎行为 |
  |---|---|---|
  | `string` 非空 | `"…"` | `--键 值` |
  | `null` / `""` | 省略 | 走 CLI 缺省（§f.1/§m.1 的缺省规则） |
  | `bool true` | `true` | 只加选项串（store_true：`clean`、`from_builtin`） |
  | `bool false` | 省略 | 同上 |
  | `string[3]`（`base`） | `["e","n","u"]` | `--base e n u`（nargs=3 展开） |
  | 其它数值 | `"90"` | 十进制字符串（`--angle 90`） |

* **未知键 = 码 2**：引擎对不在该子命令里的键报
  `--request：tool=<t> 没有参数 '<键>'（可选键 …）`（cli.py:2288-2290）——**每个操作只传
  §m.1 该子命令实际存在的参数；不存在的选项绝不发明**（PKPMJWDForm.cs:607-608 同款红线）。
  `dbsections` 的 `db` 是 `nargs="?"`（`--from-builtin` 时可省），引擎按 `required` 判定
  （cli.py:2308-2310，缺必需位置参数同样码 2）。
* **手测样例**（本机实测，2026-09-25）：`{"tool":"dbsections","args":{"from_builtin":true,
  "out":"…csv","format":"csv"}}` ⇒ `dbsections --from-builtin --out …csv --format csv`，RC=0。

---

## 4. 退出码（§f.2，冻结；.NET 侧的处置 = §p.5 ④）

| 码 | 含义 | .NET 侧处置（PKPMJWDForm.JobDone / RunJob，PKPMJWDForm.cs:649-712） |
|---|---|---|
| 0 | 成功（允许有 unresolved/W-，须看报告） | 建模方向（`*2pdms`）继续 `$M <.mac>` 并取回 renames；其余方向直接出摘要 |
| 1 | 未捕获异常（stderr 有 traceback） | 弹错 + `addin.log` |
| 2 | 参数/输入文件错误（编码、文法、文件不存在、匹配文件缺失） | 弹错（stdout 的「错误：…」行 + stderr）+ 日志 |
| 3 | `Model.validate()` 有 `E-` 项 ⇒ **不写产物** | 弹错（**E- 清单在 stderr，逐行**，cli.py `_dispatch` 后的 stderr 输出）+ 日志 |

进程层失败（入口缺失 / 超时被 Kill / 启动异常）不占用契约码：
`EngineResult.EntryMissing` / `TimedOut`（EngineRunner.cs:27-35），.NET 侧按码 1 的方式处置。

---

## 5. stdout / stderr

* **stdout = 一行摘要 + 未解析清单**（§p.5），编码 **UTF-8**：引擎在**非交互**（管道）时把
  stdout/stderr 重配置为 UTF-8（cli.py:2340-2346 的 `isatty()` 判定）；交互控制台保持控制台
  编码 + `errors="replace"`（用户可读优先）。`.NET` 侧用
  `StandardOutputEncoding = Encoding.UTF8` 读（EngineRunner.cs:100-101）。
* 摘要行格式（`RunResult.lines`，与 CLI 用户看到的一致）：
  `[<tool>] 成功（退出码 0）：<src> -> <out>` / `耗时 …；产物：…` / `报告：…` /
  `构件计数：…` / `截面：resolved=… parametric=… inferred=… unresolved=…（共 …）` /
  `unresolved: N`（N>0 时逐条，`dbsections`/`db2*` 等无构件截面的命令打
  `unresolved: 不适用（本命令不产出构件截面清单，看下面的 db 块）`）/ db 块摘要（目录宏/容器/安全）/
  `warnings=… geometry_anomalies=… skipped=… errors=…`。
* **stderr**：码 3 时逐行打 `E-` 项（§f.2）；其余码只在 `RunResult.error` 有内容时打一段
  人类可读错误。异步收流（`BeginOutputReadLine`，EngineRunner.cs:110-116）防管道缓冲写满死锁。

---

## 6. report.json（.NET 侧唯一要读的文件）

* **位置**（§f.1/§m.1 缺省规则）：`args.report` 显式给出 ⇒ 用它；省略 ⇒
  `<--out 同目录>\<--out 基名>.report.json`（PKPMJWDForm.cs:570-574 的 `ReportPathFor` 与
  引擎的 `_default_report_path` 是同一条规则的两端实现）。**窗体总是显式传 `report`**
  （PKPMJWDForm.cs:624），路径 = 输出文件同目录同基名。
* **编码**：UTF-8 无 BOM + LF（§g）。
* **顶层键**（§h + §m.3 + §h v3）：`contract_version / tool / source / source_format / output /
  options / assumptions / counts / sections / geometry_anomalies / skipped / warnings / errors /
  stats / renames / db`。键**必须齐全**（缺席方向写 `null`/空表，不得省略）。
* **`renames`（§o.7）**：引擎（纯生成方向）恒写 `[]`——改名只发生在 PDMS 运行期，生成文件里
  仍是原名。PDMS 内执行宏后，.NET 把 `!!pkpmjwdRenames` 取回，**落盘
  `<report>.renames.txt` 并显示在窗体摘要**（PKPMJWDForm.cs:717-731）；该文件是运行期结果
  （`TYPE|原名|实际名` / `FAIL|原名|最后候选` 三段竖线串）与报告 `renames` 的并集真相。
* **窗体摘要要显示什么**（§p.3-11）：`counts`（构件计数）、`sections`（resolved/parametric/
  inferred/unresolved 计数与未解析清单）、`renames`、`db` 块摘要（目录宏/容器/安全）、warnings/errors。

---

## 7. 超时、日志与冒烟用例

* **超时**：30 分钟（`EngineRunner.TimeoutMs`，EngineRunner.cs:39 = 契约 §p.5 ③）；超时
  `proc.Kill()` 并置 `TimedOut`。
* **日志**：`<PDMS根>\PKPMJWD\addin.log`（ASCII、毫秒时间戳、追加；PKLog.cs:29-43）。
  引擎的 request 路径、入口选择、退出码都会进日志（EngineRunner.cs:92、137）。
* **改动引擎后的冒烟用例**（三步，全部本机实测过）：

```bat
rem ① 纯命令行（用户路径）
python PKPM-JWD导入导出\engine\cli.py jwd2pdms "G:\…\JLCJ2.jwd" --out PKPM-JWD导入导出\test\out\r3.mac --secmap "G:\…\PKPM转PDMS截面匹配文件.txt" --project JLCJ2
rem ② 包装器（回退入口）
PKPM-JWD导入导出\engine\dist\run_engine.cmd dbsections --from-builtin --out PKPM-JWD导入导出\test\out\_w.csv --format csv
rem ③ 打包 exe + --request（插件路径）
PKPM-JWD导入导出\engine\dist\pkpmjwd_engine.exe --request PKPM-JWD导入导出\test\out\_exe_request.json
```

三条都应退出 0，且 ③ 的 stdout 可按 UTF-8 解码（§5）。
request 造法见 `test\_s3_cli\make_requests.py`。

---

## 8. 混写红线（§p.4，与本文配对的另一半）

* .NET **不直接**读写 `.jwd/.pdt`（格式转换一律进引擎进程）；
* PML **不做**文件格式解析（PDMS 库取数/执行宏归 PML：`pdms/pkpmjwdexport.pmlfnc`、
  `pdms/pkpmjwddbexport.pmlfnc`、`pdms/pkpmjwduniquename.pmlfnc`）；
* 引擎 **不碰** PDMS 进程/数据库（无 `Aveva.*` 引用、不开进程、不写 PDMS 目录）。
* .NET↔PML 的三个冻结方法在 `PmlBridge.cs`：`RunPml` / `RunPmlWithResult` /
  `ImportDotnet`（§p.4）；本文只管 .NET↔引擎这一条边。
