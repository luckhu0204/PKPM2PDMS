engine/ —— Python 引擎 v2.1.0（标准库，零第三方依赖）
==============================================

〔改名片〕本引擎历史上以「PKPM-JWD导入导出 v2.0」的名义交付（内部实施轮次 R1/R2/R3）；
v2.1.0 相对 v2.0 **只做标识改名与版本号统一，逻辑一行未改**。
注意区分两个版本号：**插件版本 = v2.1.0**；`canonical.py` 的 `CONTRACT_VERSION` 常量
= **"1.0"**（那是**规范模型 schema 版本**，出现在 `.jwd`/`report.json` 的 `contract_version`
字段里，被 spec/CONTRACT.md 与多个测试引用，本版**不动**）。

本目录文件与归属（**文件范围互不重叠，可并行实施**；签名以 spec/CONTRACT.md §b 为准）
------------------------------------------------------------------------------
  canonical.py    【架构包·已完成】规范模型数据类 + validate() + to_json/from_json（契约 §a）
  jwd_read.py     【S1-①】read_jwd(path) -> Model      .jwd(SQLite) → 规范模型
  pdt_read.py     【S1-②】read_pdt(path) -> Model      .pdt(文本)   → 规范模型
  secmap.py       【S1-②】SectionMap.load/resolve/reverse/validate（契约 §e）
  macgen.py       【S1-③】generate_macro(model, opts) -> str ; write_macro(path, text)（GBK+CRLF）
  jwd_write.py    【S1-④】write_jwd(model, path) -> dict（父表先于子表，文本列按列 GBK/UTF-8）
  pdms_dump.py    【S1-④】parse_dump(text) -> Model（契约 §c 的 PDMSDUMP 1.0）
  cli.py          【S3】jwd2pdms / pdms2jwd / pdt2model 三个子命令（契约 §f）
                  〔R6〕+ pdt2pdms / pdms2pdt / jwd2pdt / pdt2jwd / jwd2db / pdt2db /
                  db2jwd / db2pdt / dbsections / pdt2model / **auto2pdms**（自动识别）
  gui.py          【S3】tkinter 图形界面，逻辑必须复用 cli.py
  secmap_extra.txt【S1-②】截面映射补充条目（**不改用户原件**；语法同原件）

【R2 新增（契约 §j/§k/§l/§m；**尚未实现**）】
  pdt_write.py    write_pdt(model, path, opts) / write_pdt_sections(sections, path, opts)（GBK+CRLF，13 段）
  sectionlib.py   SectionRec/SectionTable/ParamDef + decode/encode 四件套 + to_pdms/from_pdms（§k）
  dbmacro.py      generate_db_macro(table, opts) / write_db_macro(path, text)（纯 ASCII + CRLF，两遍式）
  dbparse.py      parse_db_macro(text) / parse_db_macro_file(path) -> SectionTable（§l.5）
  section_table.csv       【数据文件·已由 test/build_section_table.py 生成】内置转化表（3,176 行 × 15 列，UTF-8 带 BOM + CRLF）
  section_table.meta.json 【数据文件】来源/行数/列序/sha256（见 §k.2）
  jwd_write.py 追加：write_jwd_sections(sections, path, opts)（§l.6）
  pdt_read.py  追加：`$SETELEMENT.TYPE=3 → 'brace'` 映射（§0.4-5，§j.4.5）

【R3 新增（契约 §o/§p；**尚未实现**）】
  cli.py 增 `--request FILE` 全局选项（§m/§p.5 的引擎调用协议：{"tool":…,"args":{…}}，
          与命令行同一执行函数；.NET 以进程方式调用，对用户不暴露）
  engine/dist/  引擎独立可执行入口落点：pkpm2pdms_engine.exe（PyInstaller onefile，若可用）
                或 run_engine.cmd 回退（§12#29）；入口解析顺序见 §p.5
  macgen.MacOptions 增 uniquify=True / pml_func_path（§b.6/§o.4：每个创建元素前 emit 唯一化模板；
                〔R6 起〕pml_func_path **不再写进宏**，只作记录进 report.assumptions）

【R6 新增（用户实机反馈问题②③；两处都在本目录）】
  macgen.py  宏结构标准化（问题②）：宏本体只有标准结构，与用户原件 DB Output 宏
             （G:\…\P-TRANS\pkpm_section_DBOutput.txt）逐行同形：
               头 = `$S-  -- Synonym translation OFF` / `-- `+64 个 `-` 的分隔线 /
                    `-- <用途>  Date: <生成时间>` / 空行 / `ONERROR GOLABEL /PKPM2PDMSERR` /
                    一行 `-- 元素：SITE 1 / ZONE 1 / … / SCTN <n> / PANE <n>`（唯一说明注释）
               体 = 元素创建语句（每个创建元素前的唯一化模板 `!!pkpm2pdmsType` /
                    `!n = !!pkpm2pdmsUniquename(…)` / 空名故障注入 / `NEW <T> $!n` 保留）
               尾 = `-- Switch synonyms back on if an error occurs.` / `LABEL /PKPM2PDMSERR` /
                    `handle ANY` / `$S+` / `RETURN ERROR` / `endhandle` /
                    `-- End <用途>  Date: <生成时间>` / `$S+  -- Synonym translation ON` / 分隔线
             **删掉**（不再写进宏）：`!pkpm2pdmsFuncPath = …` + `$M <$!pkpm2pdmsFuncPath>` 预载，
             以及唯一化函数可用性检查 + 故障注入块（`…UniquenameMissing()`）。
             〔R7〕上述"体"里的唯一化模板与"尾"里的 LABEL/handle 错误块**同样作废**（见下）。
  cli.py     新增子命令 `auto2pdms`（问题③：窗体下拉第一项「PKPM导入PDMS」= 自动识别）：
             读文件头判定走哪一支（前 16 字节 `SQLite format 3` ⇒ jwd2pdms；否则按 GBK/UTF-8
             解码后命中 `$VERSION`/`$NODECOOR` 或首个非空行以 `;File` 开头 ⇒ pdt2pdms；
             两者都不像 ⇒ 退出码 2，不猜）；判定后**内部调用** run_jwd2pdms / run_pdt2pdms
             的同一执行函数（不复制逻辑）。选项与 jwd2pdms 逐项相同，位置参数 dest = `src`
             （`--request` 里 `src` / `jwd` / `pdt` 三个键都落在同一个槽）。
             报告差异仅 3 处：`tool='auto2pdms'`、`options.auto_detected`、一条 assumptions。

【R7 新增（2026-09-28 用户确认的命名方案；两处都在本目录）】
  * 命名方案（macgen.py）——**SITE 外部传入、中间层前缀全宏唯一、底层 unnamed**：
      SITE            = `opts.site_name`（**必填**；.NET 侧执行前用 DbElement 直查逐个试名
                        `/PKPM2PDMS` → `/PKPM2PDMSre` → … re99，试出第一个可用的再传入；
                        引擎**不生成、不默认、不做 re 逻辑**，缺失即退出码 2）
      ZONE            = `/<SITE名>_<工程名>`
      STRU            = `/<SITE名>_MF`
      FRMW            = `/<SITE名>_EL<n>`（每层一个）、`/<SITE名>_FW`（板墙）、`/<SITE名>_GR`（轴网）
      SBFR            = `/<SITE名>_EL<n>_COLUMN|BEAM|HBRACE|VBRACE`（层 FRMW 下）、
                        `/<SITE名>_EL<n>_SLAB|WALL`（`_FW` 下）
      SCTN/PANE/STWALL= **unnamed 创建**（`NEW SCTN` 不带名字，PDMS 自动分配系统名；
                        其后 SPREF/DESP/POSS/POSE/JUSL/MEML/BANG/ORI/PLOOP/HEIGHT/PAVERT 等
                        属性行作用在当前元素上，出处见 macgen.py 模块头的 PMLLIB 证据表）
      含层号 ⇒ 全宏唯一：生成器维护"已用名字集合"，每个带名 NEW 写入前查重，重复即抛
      `MacroNameError`（生成失败，绝不带病出宏）；`write_macro()` 落盘前再跑一遍全量自查
      （重解析全部 `NEW <TYPE> /名字` + 禁项扫描）。
  * 宏结构（R7 版）：头 = `$S-` / 分隔线 / `-- <用途>  Date: …` / 一行 `-- 元素：…` /
      `ONERROR CONTINUE`；尾 = `-- End <用途>  Date: …` / `$S+  -- Synonym translation ON` /
      分隔线。**没有** LABEL/handle 错误块。
      `ONERROR CONTINUE` 的出处：本机 PMLLIB 内 251 处（如 aba\Forms\abaprocess.pmlfrm:1455、
      aba\Objects\abadrawing.pmlobj:288）。
  * **宏内零运行期函数依赖**：不出现任何 `!!pkpm2pdms*` 调用、不 `$M` 预载任何 `.pmlfnc`；
      `pdms/pkpm2pdmsuniquename*.pmlfnc` 系列自 R7 起**不再部署、不再被任何代码引用**
      （旧文件保留在工作树，只是从部署清单里移除）。
  * `MacOptions` 字段表（§b.6）随之调整：**删** `uniquify` / `pml_func_path`，
      **增** `site_name`（必填）。三个建模型子命令各增选项 `--site-name N`
      （= `--request` 的 `site_name` 键，13 条子命令里只有 `jwd2pdms`/`pdt2pdms`/`auto2pdms` 认）。
  * 报告：`renames` 语义 = **SITE 名探测结果**（`.NET 传入什么就记什么`，引擎不改名）；
      另增 `options.site_name`、`stats.used_names`/`used_names_count`、`stats.unnamed_count`。

硬性纪律（R3 追加）
------------------
  * 不得写入 G 盘（样本目录只读）；不得改 D:\AVEVA 任何文件（deploy 只交付不执行，§p.10）。
  * 交付落点：本包 + D:\AI_Work\PKPM数据解析\交付_PKPM2PDMS插件\（验收 19）。

硬性纪律
--------
  * canonical.py 是叶子模块，不得 import 其他引擎模块（契约 §b.5）。
  * 禁止在引擎里硬编码绝对路径（输入一律由参数传入）；只有 test/ 下的脚本可以。
  * 禁止静默跳过任何对象：全部回流到 Model.notes 或 write_jwd() 的返回值，再由 cli 汇总进 report.json。
  * 编码：Python 源码 UTF-8 无 BOM；secmap_extra.txt 为 GBK 无 BOM + CRLF。

自检（本目录已有）
------------------
  cd /d D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出
  python test\test_contract_selfcheck.py     # 契约自检：canonical.py 在真实 JWD 上 0 个 E- 项
