test/ —— 测试与证据
==================

已有文件（架构包，**均为只读探针/自检，不修改任何样本**）
--------------------------------------------------------
  probe_samples.py          C1：截面匹配文件与 JLCJ2.jwd 的字节级事实
                            （GBK/CRLF/行数/数据行 2836/右值缺前导斜杠 4 条/表清单/层标高/中文字节）
  probe_samples2.py         C2：匹配文件左值唯一性(0 重复)、53 个规格前缀、jwd 46 张 pkpm 表、PRAGMA
  probe_kind26_keys.py      C3：Kind=26 候选键命中（Name 7/8；<子类型>-<Name> 补齐 [18a）
  test_contract_selfcheck.py C4：canonical.py 的 JSON 往返、真实 JWD 上 validate() 0 个 E- 项、
                            ShapeVal 解码与 §e 候选键规则逐条断言（当前 0 FAIL）
  check_dump_grammar.py     C5：按 CONTRACT §c.3 规则解析 §c.4 的 PDMSDUMP 夹具（参考实现，
                            不导入 engine/pdms_dump.py；当前 0 FAIL）
  _selfcheck_out.txt        C4 的原始 stdout 留档（架构包本地的一次运行快照，非交付产物）
  _grammar_out.txt          C5 的原始 stdout 留档（同上）
  check_markdown_tables.py  C6：Markdown 表格列数自检（`python test\check_markdown_tables.py spec\CONTRACT.md`，
                            当前 0 处不一致；`\|` 视为转义不计列）

计划文件（S4 测试包负责）
------------------------
  test_jwd_read.py      读 .jwd 的字段级断言（层标高 / 构件计数 / Z 公式）
  test_pdt_read.py      读 .pdt 的节·记录·续行断言（EXR 折行、$RIGID 的 SLABID 折行）
  test_secmap.py        匹配文件容错（缺斜杠、注释、空白）、四级优先级、补充文件叠加、逆映射
  test_macgen.py        宏的编码（GBK 无 BOM + CRLF）、未解析截面的注释行为、单位缩放
  test_roundtrip.py     .jwd → Model → .jwd'（逐表行数与关键列比对）
  test_dump.py          PDMSDUMP 1.0 文法（含 §c.4 夹具）、缺省单位、`-` 哨兵、`~` 尾部
  test_cli.py           三个子命令的退出码（0/1/2/3）与 report.json 结构

纪律
----
  * 测试可以使用样本绝对路径，但**只读**；不得向样本目录写任何文件。
  * 每个测试必须打印可复制的命令与结论；"未跑" 就说未跑，禁止用更弱的检查冒充。
  * 测试失败时不得为了让门禁通过而修改断言——先报出，由契约/实现方决定。
