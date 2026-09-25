engine/ —— Python 引擎（标准库，零第三方依赖）
==============================================

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
  engine/dist/  引擎独立可执行入口落点：pkpmjwd_engine.exe（PyInstaller onefile，若可用）
                或 run_engine.cmd 回退（§12#29）；入口解析顺序见 §p.5
  macgen.MacOptions 增 uniquify=True / pml_func_path（§b.6/§o.4：宏内唯一化模板 + $M 预载）

硬性纪律（R3 追加）
------------------
  * 不得写入 G 盘（样本目录只读）；不得改 D:\AVEVA 任何文件（deploy 只交付不执行，§p.10）。
  * 交付落点：本包 + D:\AI_Work\PKPM数据解析\交付_PKPM-JWD插件\（验收 19）。

硬性纪律
--------
  * canonical.py 是叶子模块，不得 import 其他引擎模块（契约 §b.5）。
  * 禁止在引擎里硬编码绝对路径（输入一律由参数传入）；只有 test/ 下的脚本可以。
  * 禁止静默跳过任何对象：全部回流到 Model.notes 或 write_jwd() 的返回值，再由 cli 汇总进 report.json。
  * 编码：Python 源码 UTF-8 无 BOM；secmap_extra.txt 为 GBK 无 BOM + CRLF。

自检（本目录已有）
------------------
  cd /d D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出
  python test\test_contract_selfcheck.py     # 契约自检：canonical.py 在真实 JWD 上 0 个 E- 项
