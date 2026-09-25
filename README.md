# PKPM-JWD 导入导出插件（PKPM ↔ AVEVA PDMS 12.1 SP4）

把国产结构设计软件 PKPM 的结构模型接入 AVEVA PDMS 12.1 SP4 的插件套件，包含三条能力线：

| 能力线 | 说明 |
|---|---|
| **几何建模双向** | `.jwd`（PKPM 结构模型，SQLite）与 `.pdt`（PKPM 中间模型，GBK 文本）→ PDMS Design 结构模型（SITE/ZONE/STRU/FRMW/SBFR/SCTN/PANE/STWALL）；PDMS 模型 → `.jwd` / `.pdt` 导出；两种格式互相转换 |
| **截面库双向（数据库层）** | PKPM 截面定义（`*Sect` 表的 Kind/ShapeVal 编码、`$DEFFRAMESECTION`）→ PDMS Catalogue + Specification 宏（STSECTION/STCATEGORY/DTSET/PTSSET/SPRFILE/SPCOMPONENT）；PDMS 目录宏（DB Output 格式）→ 反算回 PKPM 截面定义；附 3176 行机读转化表 |
| **PDMS 原生插件** | .NET Add-in（C#，`IAddin` + WinForms 窗体）+ PML 混写：PDMS 菜单「PKPM JWD」点开原生窗体完成全部操作；导入时所有层次与元件**运行期命名唯一化**——与库中已有模型重名自动加后缀 `re`（再冲突 `re2`、`re3`…，上限 99，耗尽则安全中止） |

## 目录结构

```
├─ 插件包/                  主交付包
│  ├─ engine/               转换引擎（纯 Python 标准库）：12 个子命令 CLI + tkinter GUI
│  ├─ pdms/                 PDMS 侧 PML（窗体/导出函数/运行宏，GBK 无 BOM + CRLF）
│  ├─ pdms-net/             .NET 原生插件源码（C# .NET 3.5 / x86）+ build.cmd + deploy 脚本
│  ├─ install/              v1 PML 路线安装/卸载脚本（PowerShell）
│  ├─ spec/                 接口契约（CONTRACT.md，v1+R2+R3 全记录）
│  ├─ docs/                 使用说明、格式规范（JWD/PDT）、数据库转化、截面映射、交付报告
│  └─ test/                 验收测试（acceptance*.py，三套共 26 项）与独立复核脚本
├─ PDMS原生插件/            上面 pdms-net 的发布副本 + 部署说明
├─ 安装程序/                v1 向导安装程序 exe（编译产物，见 Release 附件）
├─ 交付清单.txt / SHA256哈希清单.txt / 从这里开始.txt
```

## 快速开始

### 主用法：PDMS 内原生界面（PDMS 12.1 SP4，需 .NET Framework 3.5 运行库）

1. **PDMS 完全停机**；
2. 进入 `PDMS原生插件/deploy/`，先 `python deploy_pkpmjwd.py`（dry-run 看完整变更清单），
   确认后 `python deploy_pkpmjwd.py --execute`（改 DesignAddins.xml / DesignCustomization.xml 前自动备份、只加不删、幂等）；
3. 启动 PDMS 进 DESIGN，菜单栏出现「PKPM JWD」→ 打开原生窗体：选 `.jwd`/`.pdt`、选截面匹配文件、
   设基点/转角/单位、勾选构件类别、执行；转换由内置引擎完成，建模与命名唯一化在 PDMS 内执行。

> 说明：窗体的「PDMS 文本导出」按钮依赖 v1 PML 路线（`插件包/install/install.ps1`，同样支持 -DryRun）安装的
> `!!pkpmjwdexport`；不用导出功能可跳过这一步。两条路线装完都要**完全退出并重启 PDMS**。

### 命令行 / 图形界面（不进 PDMS 也能转换）

```text
python 插件包/engine/cli.py jwd2pdms  工程.jwd --out 模型.mac --secmap 截面匹配文件.txt
python 插件包/engine/cli.py pdt2pdms  工程.pdt --out 模型.mac
python 插件包/engine/cli.py jwd2db / pdt2db   # PKPM 截面定义 → PDMS 目录+规格宏
python 插件包/engine/cli.py db2jwd / db2pdt   # PDMS 目录宏 → PKPM 截面定义
python 插件包/engine/cli.py jwd2pdt / pdt2jwd # 两种 PKPM 格式互转
python 插件包/engine/cli.py dbsections        # 查看/导出截面转化表
python 插件包/engine/gui.py                   # tkinter 图形界面
```

引擎只依赖 Python 标准库；免 Python 环境可使用 Release 附件里的独立引擎 exe 与 v1 向导安装程序。

## 质量与验证状态（如实声明）

- **验收**：三套独立验收测试共 26 项全部通过（几何 7 / 数据库+PDT 13 / 原生插件+重名约束 6），
  由编排脚本以真实退出码把关；几何另由独立复核角色直接从原始 SQLite 重算并与产物逐项比对
  （811 根构件 1622 个端点、222 块板顶点序列、包围盒全部相等），并用负向对照自证了比对器灵敏度。
- **.NET 插件**：用 `csc.exe`(v3.5) `/platform:x86` 真编译通过，产物 CLR 版本 v2.0.50727 经独立读 PE 头核实
  （与 PDMS `des.exe` 及 Aveva 程序集一致）。
- **未实机**：宏、PML 与 .NET 插件均未在真实 PDMS 会话中加载执行过；命名唯一化的运行期行为未在真库验证
  （失败安全：异常经宏头 ONERROR 中止，不会建出错名元素）。首次安装请先跑 dry-run 核对清单。
- **安全设计**：安装/部署脚本只加不删、改前备份、幂等、可回滚（卸载后 design.uic 与安装前逐字节一致）；
  数据库宏只操作本包自己的 CATALOGUE，第二遍引用全部带父级限定链，不会改写用户库同名元素。

## 已知限制

- 荷载不参与转换（按要求不做；`.pdt` 写出时荷载段只写段头、体内为空）。
- `.jwd` 的 22 张空表（墙/楼梯/次梁/阻尼器/柱帽/施工段等）在本样本工程无数据，未实现对应转换。
- 少量未解码截面族按「不猜」原则列为待确认（族码 19、TRAPEZOID/DOUBLE_C/RECT、Kind=2、族码 32 槽序）。
- 混凝土板/墙的 PDMS 规格名（/Concrete_Slab-SPEC 等）是占位名，请按自己的等级库在
  `engine/secmap_extra.txt` 中替换。

## 数据来源与致谢

截面转化表由用户提供的《PKPM转PDMS截面匹配文件.txt》（2,836 条）、《PKPM（PDMS数据库）.txt》
（PDMS DB Output 目录宏，2,920 个 SPRFILE/SPCOMPONENT）与 PKPM 官方 P-TRANS 内嵌截面编码表交叉对齐生成。
PDMS 侧命令写法全部引自 AVEVA PDMS 12.1 SP4 本机安装内真实代码（`sctlcrelem.pmlfnc` 等），未凭空编造语法。

## 免责声明

本插件与 PKPM、AVEVA 无隶属关系；在 PDMS 中执行导入前请先备份工程数据库。按现状提供，不附带任何担保。
