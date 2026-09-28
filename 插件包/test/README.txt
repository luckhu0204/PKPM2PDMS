test/ —— 测试与证据
==================
（本文件由架构包维护；v1 的版本曾被后续包删除，此处按当前实际内容重建。
  与 `spec/CONTRACT.md` 冲突时以契约为准。）

架构包自己的只读探针 / 自检（**不修改任何样本**，全部可复现）
-----------------------------------------------------------
契约 §0.2 与附录 C/E 引用的编号（C1–C12）一一对应：

  probe_samples.py          C1：截面匹配文件与 JLCJ2.jwd 的字节级事实
                            （GBK/CRLF/行数/数据行 2836/右值缺前导斜杠 4 条/表清单/层标高/中文字节）
  probe_samples2.py         C2：匹配文件左值唯一性(0 重复)、53 个规格前缀、jwd 46 张 pkpm 表、PRAGMA
  probe_kind26_keys.py      C3：Kind=26 候选键命中（Name 7/8；<子类型>-<Name> 补齐 [18a）
  test_contract_selfcheck.py C4：canonical.py 的 JSON 往返、真实 JWD 上 validate() 0 个 E- 项、
                            ShapeVal 解码与 §e 候选键规则逐条断言（当前 0 FAIL）
  check_dump_grammar.py     C5：按 CONTRACT §c.3 规则解析 §c.4 的 PDMSDUMP 夹具（参考实现，
                            不导入 engine/pdms_dump.py；当前 0 FAIL）
  check_markdown_tables.py  C6：Markdown 表格列数自检
                            （`python test\check_markdown_tables.py spec\CONTRACT.md`；`\|` 视为转义不计列）

【R2 新增（契约 §j/§k/§l 与附录 D/E）】
  probe_v2_shapes.py        C7：`1_PM.pdt` 逐段行式（repr，含缩进/小数位/EXI/EXR 形态）
                            + `PDMSxCA_Addin121.dll` 内 `.pdt` 格式串（按偏移取 UTF-16LE）
                            + 侦察转化表规模/列/唯一性/取值域
  probe_v2_table_keys.py    C8：转化表键与重复分析（非空 pkpm_name 唯一、pdms_spec_path 唯一、
                            256 条 in_pdms_macro=''、4 条缺前导斜杠已补齐并命中）
  probe_v2_exr_wrap.py      C9：EXR 每行 ≤10 组（首行缩进 7、续行 8）、SLABID 每行 20 个（续行 11）、
                            `$DEADLOAD` 分组头紧随子段头
  probe_v2_kind303_slots.py C12：`.jwd` 3 条 Kind=303 的 ShapeVal 原文与槽位下标
  build_section_table.py    C10：从 `_recon/dbsect/pkpm_pdms_section_table.csv` **生成**
                            `engine/section_table.csv`（3,176 行 × 15 列）+ `section_table.meta.json`
                            （幂等；sha256 写进 meta）
  check_v2_contract.py      C11：v2 契约静态自检 —— 内置表规模/列序/键/JSON 列、§k.3 编码回算
                            与 `.jwd` 样本逐字一致（Kind=26 一条 + Kind=303 三条）、附录 D.4 宏夹具
                            （NEW:END 平衡、OLD 无 END、五条引用链、纯 ASCII、容器名合规）、
                            CONTRACT.md 表格列数。**当前 0 FAIL**

【R3 新增（契约 §o/§p 与附录 F/G）】
  check_v3_csc_probe.py     C13：§p.2 编译命令实测 —— csc 3.5 + `/platform:x86` 编译最小 IAddin 桩
                            （test/_v3_csc_check/stub_pkpm2pdms.cs）⇒ 退出码 0、产物 CLR=v2.0.50727、
                            PE machine=I386；旁证样例 TGTEXT.dll（备份副本）同为 CLR2/x86；
                            并核对编译前后 D:\AVEVA 监视文件零变化。当前 0 FAIL
  check_v3_notouch.py       C14：无接触基准（G:\…\PKPM导入导出插件 递归 751 文件 +
                            D:\AVEVA\Plant\PDMS12.1.SP4 顶层 645 文件，size+mtime+sha256）
                            —— `snapshot` 建基准 / `verify` 核对（验收 17/19 的可执行部分）
  check_v3_contract.py      C15：v3 夹具自检 —— 附录 F.1 唯一化函数夹具（签名/探测/上限 99/FAIL）、
                            F.2 宏片段（ONERROR 尾 + 故障注入）、F.3 的 .uic 同构对照、
                            §h 的 renames 键、CONTRACT.md 表格列数
  _v3_csc_check/            C13 的产物留档（stub 源码/build.cmd/编译 DLL/_csc_probe.txt/
                            _baseline/*.json 无接触基准）

产物留档（本会话运行快照，非交付产物）
--------------------------------------
  _selfcheck_out.txt / _grammar_out.txt / _v2_probe_a.txt / _v2_build_out.txt / _v2_check_out.txt
                            各次运行的 stdout 留档（重跑命令见 spec/CONTRACT.md 附录 C/E）
  _acc_* / _dev/ / _acceptance_out/ / out/ / _rt_out/ / _s2_probes_20260924/
                            各实施包（S1–S6）自己的开发探针、夹具与运行输出；
                            它们是**证据**，不要删除、不要当垃圾清理

规矩
----
  * 测试可以使用样本绝对路径，但**只读**；不得向样本目录写任何文件（`G:\…\PKPM导入导出插件\`）。
  * 每个测试必须打印可复制的命令与结论；"未跑" 就说未跑，禁止用更弱的检查冒充。
  * 测试失败时不得为了让门禁通过而修改断言——先报出，由契约/实现方决定。
  * R2 的实机项（目录宏、清场语句、`TYPE=3`）在 test 里**只能**标注"未实机"，不得伪造通过。
