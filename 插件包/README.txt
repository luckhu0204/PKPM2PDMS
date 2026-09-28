PKPM2PDMS导入导出 v2.1.0 —— 交付包骨架
====================================

〔改名片〕本包历史上以「PKPM-JWD导入导出 v2.0」的名义交付（内部实施轮次 R1/R2/R3）。
v2.1.0 相对 v2.0 **只做标识改名与版本号统一，逻辑一行未改**。
注意区分两个版本号：插件版本 = **v2.1.0**；engine/canonical.py 的 CONTRACT_VERSION
常量 = **"1.0"**（那是规范模型 schema 版本，出现在 .jwd/report.json 的 contract_version
字段里，本版不动）。

用途
----
在 **不改动**《PKPM导入导出插件》(P-TRANS) 任何原有文件的前提下，新增一套独立的
.jwd(SQLite) ⇄ AVEVA PDMS 12.1 SP4 结构模型转换工具。

三条管线（共用规范模型 canonical）
---------------------------------
  【导入】 .jwd ── engine/jwd_read.py ──► Model ── engine/macgen.py ──► PDMS 宏(.mac, GBK/CRLF)
  【导出】 PDMS 模型 ── pdms/pkpm2pdms_export.pmlfnc ──► PDMSDUMP(.txt, GBK/CRLF)
           ── engine/pdms_dump.py ──► Model ── engine/jwd_write.py ──► .jwd
  【对照】 .pdt ── engine/pdt_read.py ──► Model（交叉验证 / 回归）

目录用途
--------
  engine/    Python 引擎（标准库，零第三方依赖）
  pdms/      PDMS 端 PML 包（GBK 无 BOM + CRLF）
  install/   安装/卸载脚本（改 design.uic、DesignAddins.xml 前必须备份）
  docs/      用户文档与格式规范（去侦察口气的交付版）
  test/      测试与证据（含本包已有的只读探针与契约自检）
  spec/      唯一接口契约 CONTRACT.md；spec/out 放导出样例/固件
  deliver/   最终交付清单、ZD 说明与安装包

先读什么
--------
  1. spec/CONTRACT.md   ← **唯一接口契约**，所有模块交互以它为准
  2. engine/canonical.py ← 契约的数据结构实现（契约 §a）
  3. 侦察报告（只读，位于工作区 _recon/）：
       _recon/jwd_format.md   .jwd 表结构 / ShapeVal 解码 / Z 推导
       _recon/pdt_format.md   .pdt 文本格式逐字段规范
       _recon/pdms_target.md  现有插件创建物 / PDMS 建模语法(带出处) / 编码纪律

编码纪律（摘要，详见 CONTRACT §g）
----------------------------------
  Python 源码 / README / docs/*.md   UTF-8 无 BOM
  *.mac / *.pmlfrm / *.pmlfnc        GBK 无 BOM + CRLF
  secmap_extra.txt / PDMSDUMP 文本    GBK 无 BOM + CRLF
  *.json                             UTF-8 无 BOM

范围边界（摘要，详见 CONTRACT §i）
----------------------------------
  不改 PDMSxCA_Addin*.dll；不改任何样本原件；不逆向 SPAS；不改 PDMS 安装内既有文件；
  不删除任何文件（本包只允许在工作区 PKPM2PDMS导入导出/ 内新增/覆盖自己的文件）。

v2.1.0 改名带来的唯一兼容性代价（必读）
--------------------------------------
  PDMSDUMP 文本的首行 magic 含插件标识，本次从 #PKPM-JWD-PDMSDUMP 改为
  #PKPM2PDMS-PDMSDUMP（其后格式版本 1.0 不变）。pdms2jwd / pdms2pdt 对首行硬校验：
  **v2.0 生成的旧 dump 文本会被 v2.1.0 引擎拒绝**。迁移：用旧引擎，或手工把旧文本首行
  的 #PKPM-JWD-PDMSDUMP 改成 #PKPM2PDMS-PDMSDUMP（其余行不动）。本版不加自动兼容分支。
  详见 spec/CONTRACT.md §c 首段、docs/使用说明.md §4.1、engine/pdms_dump.py 的 HEADER 注释。

交付/打包提示
-------------
  各目录下的 __pycache__\ 是 Python 运行时字节码缓存（跑过脚本就会生成），
  打包交付时应当排除，不属于源码；本包不删除任何文件，故保留在原地。
  归集到 deliver\ 时按 deliver\README.txt 的规则用哈希核对，不要手改后再打包。
