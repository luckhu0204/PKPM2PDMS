# 格式规范 —— PKPM `.jwd`（交付版）

> 来源：本包对样本 `JLCJ2.jwd` 的只读解析（SQLite 全表导出 + 逐列统计）与逐条核对，
> 结论同时固化在 `spec/CONTRACT.md`（可执行条款）与 `engine/jwd_read.py`（实现）。
> **证据分级（全文遵守）**：
> * **【事实】** 有字节/SQL/逐行级直证，可直接编码；
> * **【推断】** 由证据推得、机理未证实：**可以编码，但必须留痕**（报告 `assumptions`/`note`），不得当结论向用户陈述；
> * **【未知】** 明确未解：**禁止猜测**，一律"报出 + 落报告"。
>
> 本文所有数字都可用 §9 的命令复现；凡"未在 PDMS 实机验证"的结论都在文中标注。

---

## 1. 文件性质

| 项目 | 值 | 证据 |
|---|---|---|
| 文件类型 | **SQLite 3** 单文件数据库（头 16 字节 `SQLite format 3\0`） | 【事实】`test\check_deliverables.py`：表 46 / encoding UTF-8 / user_version 0 / 合计 6480 行（本机复跑 FAIL 项 0） |
| `PRAGMA encoding` | `UTF-8` | 【事实】`PRAGMA encoding` → `('UTF-8',)`（本次只读实测） |
| `PRAGMA user_version` | `0` | 【事实】同上 |
| 表数 | **46 张**，全部以 `pkpm` 开头：**21 张非空（合计 6,480 行）+ 25 张空** | 【事实】本次 `sqlite_master` 只读枚举 |
| 外键 | DDL 里有 `REFERENCES … ON DELETE CASCADE`，但连接**未开** `PRAGMA foreign_keys` ⇒ **外键不具约束力** | 【事实】`_recon\jwd_dump\00_schema.txt` |
| 中文列编码 | **混合编码**：`pkpm*Sect.Name` 是 **GBK 字节**、`pkpmLoadSect.Loadname` 是 **UTF-8 字节** | 【事实】见 §8 |

> 与其他文档的一处数字差异：早期侦察报告写"43 张表（21 非空 + 22 空）"。
> 本次实测（`SELECT name FROM sqlite_master WHERE type='table'` 共 46 条）与
> `spec/CONTRACT.md` §0.2 的更正一致：**46 张表、25 张空**。`engine/jwd_write.py` 的建表 DDL 按 46 张执行。

数据模型是"**按标准层存放的 2D 平面 + 层表 + 构件段**"：

```
pkpmStdFlr 标准层 ──< pkpmJoint 节点 / pkpmGrid 网格线 / pkpmAxis 轴线 / pkpmSlab 房间
         │                  │
         │                  └── 梁段 pkpmBeamSeg（GridID → 网格线，两端节点由网格线给出）
         ├──< pkpmColSeg 柱段（JtID → 节点，竖向贯穿本层）
         ├──< pkpmBraceSeg 支撑段（Jt1ID/Jt2ID → 节点）
         └──< pkpmSlabHole 板洞索引
pkpmFloor 自然层 ── StdFlrID → pkpmStdFlr；LevelB/Height 给出真实标高与层高
```

---

## 2. 表清单

### 2.1 非空表（21 张，行数为本样本实测）

| 表 | 行数 | 用途 |
|---|---:|---|
| `pkpmStdFlr` | 5 | 标准层（建模单位） |
| `pkpmFloor` | 5 | 自然层（**标高与层高的唯一来源**） |
| `pkpmJoint` | 382 | 节点（2D 平面坐标 + 相对层顶高差） |
| `pkpmGrid` | 604 | 网格线/杆件轴（**梁的几何载体**） |
| `pkpmAxis` | 112 | 轴线（`Name` 全空） |
| `pkpmColSeg` | 200 | 柱段（本表一行 = 一根物理柱） |
| `pkpmBeamSeg` | 598 | 梁段（本表一行 = 一根物理梁） |
| `pkpmBraceSeg` | 13 | 支撑段 |
| `pkpmSlab` | 222 | 房间/板多边形（46 列，仅前段有数据） |
| `pkpmSlabHole` | 29 | 板洞**索引**（几何在 `pkpmSlab` 里） |
| `pkpmBeamSect` | 22 | 梁截面（同构三表） |
| `pkpmColSect` | 4 | 柱截面 |
| `pkpmBraceSect` | 2 | 支撑截面 |
| `pkpmLoadSect` | 17 | 荷载截面/工况 |
| `pkpmLoadSeg` | 121 | 荷载段 |
| `pkpmProperty` | 3574 | 按对象挂的键值属性包 |
| `pkpmSysInfo` | 195 | 系统/设计参数键值表 |
| `pkpmStdFlrPara` | 130 | 每标准层 26 项设计参数（5×26） |
| `pkpmSatTower` | 5 | 塔吊/场地范围 |
| `pkpmSatTowPara` | 180 | 塔吊基础参数 |
| `pkpmSatTowReinInfo` | 60 | 塔吊配筋信息 |

### 2.2 空表（25 张）

`pkpmBeamJYDef`、`pkpmCantiSlab`、`pkpmCantiSlabDef`、`pkpmColcapSect`、`pkpmCraneDef`、`pkpmCraneInfo`、
`pkpmDamperSect`、`pkpmJointDamperSeg`、`pkpmMemberDamperSeg`、`pkpmMidBeamSeg`、`pkpmMidSlab`、
`pkpmPetroDeviceSect`、`pkpmPetroDeviceSeg`、`pkpmSatConstruct`、`pkpmSatCover`、`pkpmSlabHoleDef`、
`pkpmSlabJYDef`、`pkpmStairDef`、`pkpmStairSeg`、`pkpmSubBeam`、`pkpmULoadDef`、`pkpmWallHole`、
`pkpmWallHoleDef`、`pkpmWallSect`、`pkpmWallSeg`。

* 表名含义（由列名推断）：墙段/墙洞、楼梯、吊车、阻尼器、悬挑板、柱帽、梁端/板端铰接定义、
  次梁（`pkpmSubBeam` 直接用 `X1..Z2` 存三维端点）、用户自定义荷载、装配式施工段落等。
* **【未知】** 这些表族的**字段语义未解码**（本样本无数据，无法验证）。
  `pkpmWallSeg` / `pkpmSubBeam` 在真实工程里常非空 ⇒ 转换器必须**报出而不猜**：
  非空时记入 `report.skipped`（`engine/jwd_read.py` 的 `UNDECODED_OBJECT_TABLES` 清单）。
* **局限（已独立复核确认）**：`engine/jwd_read.py:59-86` 的"未解码表留痕"只按**硬编码的三张表清单**扫描，
  **数据库里存在、而三张清单都没列到的表会被静默忽略**（对已知样本无影响，46 张表与清单的交集检查为 0 缺口）。
  详见 `docs/交付报告.md` 复核条目（代码与纪律 §8）。

---

## 3. 关键表字段（列名/类型为本次 `PRAGMA table_info` 实测）

### 3.1 楼层

```sql
pkpmStdFlr(ID INTEGER, No_ INTEGER, Height INTEGER)                       -- Height 样本全 0，不可用
pkpmFloor (ID INTEGER, No_ INTEGER, Name TEXT, StdFlrID INTEGER,
           LevelB REAL, Height REAL)                                     -- 真实标高与层高
```

| 列 | 含义 | 样本值 |
|---|---|---|
| `pkpmStdFlr.ID` / `No_` | 标准层主键 / 层序号 | 1001, 1736, 2205, 3799, 31531 / 1..5 |
| `pkpmStdFlr.Height` | 层高（mm）——**本样本全 0，禁止使用** | `0` |
| `pkpmFloor.ID` / `No_` | 自然层主键 / 序号 | 5120, 5121, 5122, 5123, 32399 / 1..5 |
| `pkpmFloor.StdFlrID` | → `pkpmStdFlr.ID` | 1001, 1736, 2205, 3799, 31531 |
| `pkpmFloor.LevelB` | **层底绝对标高（mm）** | −2000, −1000, 6600, 11600, 16600 |
| `pkpmFloor.Height` | **层高（mm）** | 1000, 7600, 5000, 5000, 5460 |

**【事实】** 相邻层首尾相接：`LevelB[i] + Height[i] == LevelB[i+1]`（5 层逐项成立）。
**【事实】** 本样本标准层 : 自然层 = 1 : 1。
**多自然层共用 1 标准层时**（PKPM 常见做法）：必须**按自然层各复制一份构件**，每份用各自 `pkpmFloor` 的
`LevelB/Height`——本样本无此情况，**未实测**。

### 3.2 平面对象

```sql
pkpmJoint(ID, No_, StdFlrID, X REAL, Y REAL, HDiff INTEGER)
pkpmGrid (ID, No_, StdFlrID, Jt1ID, Jt2ID, AxisID)
pkpmAxis (ID, No_, StdFlrID, Jt1ID, Jt2ID, Name TEXT)
```

* `pkpmJoint.No_` 是**层内编号**（与 `ID` 无算术关系）；`X/Y` 为平面坐标（mm）；
  `HDiff` = 相对**本层层顶**的高差（mm）——本样本 382 行**全 0**；
  该表**没有 Z 列**（列清单实测 6 列，无 Z）⇒ Z 只能由楼层表推。
* `pkpmGrid`：每根梁段对应**唯一**一条网格线，两端节点 = `Jt1ID/Jt2ID`；本样本 604 条网格线分布在 112 条轴线上。
* `pkpmAxis.Name` 样本**全空** ⇒ 得不到 "1/A/B" 轴号，PDMS 侧轴网名只能自造。

### 3.3 构件段（一行 = 一根物理构件）

```sql
pkpmColSeg (ID, No_, StdFlrID, SectID, JtID, EccX, EccY, Rotation REAL, HDiffB,
            ColcapId, Cut_Col TEXT, Cut_Cap TEXT, Cut_Slab TEXT)          -- 13 列
pkpmBeamSeg(ID, No_, StdFlrID, SectID, GridID, Ecc, HDiff1, HDiff2,
            Rotation REAL, JYDef TEXT)                                   -- 10 列
pkpmBraceSeg(ID, No_, StdFlrID, SectID, Jt1ID, Jt2ID,
             EccX1, EccY1, HDiff1, EccX2, EccY2, HDiff2, Rotation REAL) -- 13 列
```

| 列 | 含义 | 样本实测 |
|---|---|---|
| `SectID` | → 对应 `*Sect.ID` | 柱 3 种、梁 19 种被用到 |
| `Ecc` / `EccX,EccY` | 截面中心相对轴线的水平偏心（mm） | 梁 `Ecc`：0(483)、±150、±100、±175；柱 `EccX/EccY`：0(136)、±50 |
| `HDiff*` | 相对层顶/层底的高差（mm，斜梁/降梁/支撑用） | 梁/柱全 0；支撑 12 根 = 1/1，1 根 = 1/**6650**（见 §7 第 7 行） |
| `Rotation` | 绕构件自身轴的转角 | 样本全 0 |
| `JYDef` | 梁端铰接定义 | 恒 `0,0,0,0` |

**【事实】** 每根构件在段表里**只有一行**，且 `(StdFlrID, GridID)` 组合在同一层内**不重复**
⇒ **禁止**跨层按 ID 合并"同一物理构件"；节点/网格线/房间**每层独立**。

### 3.4 楼板与洞口

```sql
pkpmSlab(ID, No_, StdFlrID, GridsID TEXT, VertexX TEXT, VertexY TEXT, VertexZ TEXT,
         RoomIsHole, Thickness, ... 共 46 列，后 20+ 列为预制/空心/异型板参数)
pkpmSlabHole(ID, No_, StdFlrID, SectID, JtID, SlabID, EccX, EccY, Rotation)   -- 9 列
```

* `GridsID` / `VertexX` / `VertexY` / `VertexZ` 都是 **TEXT，逗号分隔**；`VertexZ` 单位 mm。
* `RoomIsHole = 1` ⇒ 该多边形是**板洞**（样本 29/222）；`Thickness = 0` ⇒ **未建板**（142 行，含 29 个洞）。
* **【事实】** 多边形**不闭合**（首尾不重复），顶点数 4–10；每个顶点都恰是某个节点坐标。
* **【事实】** `VertexZ` 恒等于同层 `pkpmFloor.Height`（222/222）⇒ 板面 = **层顶**。
* **【事实】** `pkpmSlabHole.SlabID` 全部指向 `RoomIsHole=1` 的 `pkpmSlab` 行（29/29），几何就在被引用的
  那一行里 ⇒ **`pkpmSlabHole` 只是索引记录，不得据此再建一遍洞**（重复建会多出 29 个对象）。
  工具的处理：把 `RoomIsHole=1` 的 slab 当洞口/房间对待，`pkpmSlabHole` 记入 `report.skipped`。

### 3.5 截面表（三表同构）

```sql
pkpmBeamSect / pkpmColSect / pkpmBraceSect (ID, No_, Name TEXT, Mat INTEGER, Kind INTEGER, ShapeVal TEXT)
```

* `Mat`：**5 = 钢、6 = 混凝土**（样本只出现这两个值）。
* `Name`：可为空、可为中文（GBK 字节）；**型钢库截面靠 `Name` 做等级库映射最可靠**（`ShapeVal` 尺寸只作校验）。
* `ShapeVal`：见 §4。

### 3.6 荷载

```sql
pkpmLoadSect(ID, No, Loadname TEXT, ElementKind INTEGER, ShapeVal TEXT)       -- 5 列
pkpmLoadSeg (ID, No, SectID, Type, ElementID, strParas1 TEXT, nPtCnt,
             strParasX TEXT, strParasY TEXT, strParasZ TEXT, StdFlrID)        -- 11 列
```

* **【事实】** `ElementKind`：`12` = 梁上荷载、`−1` = 节点集中荷载；
  `ElementID` **唯一解析**（121/121 只命中一张表）：77 行 → `pkpmBeamSeg.ID`、44 行 → `pkpmJoint.ID`。
* **【未知】** `ShapeVal` 的类型码（1/2/3 = 均布/梯形/三角形？）与数值单位（kN vs kN/m）**未证实**
  ⇒ 本版**只做原样搬运 + 计数，不参与几何**，并在报告里注明"荷载为参考值"。

### 3.7 属性/系统表

* `pkpmProperty(ID, Name TEXT, Type INTEGER, ShapeVal TEXT)` = 按对象挂的键值包
  （样本键：`HNTDJ`(混凝土等级，`30.00`)、`GANGH`、`SpBeam`、`SpSlab`、`support` …）。
  工具只用其中的 `HNTDJ` → `Member.material = "C30"`、`GANGH` → `"Q…"`（值 ≤ 0 时不填）。
* `pkpmSysInfo(ID, ParaVal VARIANT)`：`ID=2` 的字符串是工程名（样本 `"JLCJ2"`），
  作为 `--project` 的缺省值。
* `pkpmStdFlrPara(StdFlrID, Kind, ParaVal)`、`pkpmSat*`：与结构几何无关，工具不消费（记 `skipped`）。

---

## 4. `ShapeVal` 解码

### 4.1 通用语法

**【事实】** 三张截面表的 `ShapeVal` 都是逗号分隔、**尾两字段固定**的序列：

```
"<Kind>, <p1>, …, <pN>, <Mat>, <本行 ID>,"
```

* 三表 28/28 行的"末字段 == 本行 `ID`"、"倒数第二字段 == `Mat`"（Kind=303 写 **−1**）、
  "首字段 == `Kind`" 全部成立。
* 解码步骤：按逗号切分 → 去掉**尾部空串**（保留中间空字段）→ 校验尾部两字段 → 中间即**参数体**。
* 工具实现：`engine/jwd_read.py` 的 `_split_shapeval()`；参数体 = `params[1:-2]`（去掉首字段 Kind 与尾部两字段）。

### 4.2 各 Kind 的布局（本样本实际出现 Kind = 1 / 2 / 3 / 26 / 303）

| Kind | 参数体（下标从 0） | `dims` 键 | 证据等级 |
|---|---|---|---|
| 1 | `[0]=B, [1]=H` | `{"B","H"}` | **B/H 先后为【推断-中】**（§7#4） |
| 2 | `[0]=Tw,[1]=H,[2]=B1,[3]=T1,[4]=B2,[5]=T2` | 6 键 | 值集合【推断-高】；**B/T 交错序【未知】**（§7#5） |
| 3 | `[0]=d` | `{"d"}` | 族别【未知】→ 本版按证据判为圆形（`inferred`，§7#1） |
| 26 | `[0]=族码,[1]=子类型,[2]=H,[3]=0,[4]=B,[5]=tf,[6]=tw,[7]=0` | 6 键 | H/B/tf/tw【事实】（8 条中 7 条与 PDMS 截面库独立吻合） |
| 303 | 84 槽内部转储，见 §4.4 | 见 §4.4 | 【事实】（四重印证） |

**本样本 28 行的解码实例（原文照抄）**：

```
Kind=1  pkpmBeamSect 1380  '1,300,600,6,1380,'          → B=300 H=600（混凝土矩形，Mat=6）
Kind=1  pkpmColSect  1116  '1,600,600,6,1116,'
Kind=2  pkpmBeamSect 4080  '2,10,500,250,16,250,16,5,4080,'  → 焊接 H 500×250×10×16（Mat=5）
Kind=3  pkpmBraceSect 32335 '3,20,5,32335,'             → 单尺寸 d=20
Kind=26 pkpmBeamSect 4484  '26,39,1,450,0,200,14,9,0,5,4484,' → HN450X200（族39=国标H，子类型1）
Kind=26 pkpmBeamSect 15148 '26,32,2,180,0,74,9,5,0,5,15148,'  → [18a（族32=槽钢，子类型2=轻型）
Kind=303 pkpmColSect 3985  '303,77,12866,12341,12586,11824,12336,0,…,-1,3985,'
```

### 4.3 Kind=26 的族码/子类型码

**【事实】** 由插件自身 DLL 的键表（`_recon\out_addin_W.txt`）与 PDMS 截面库（`PKPM（PDMS数据库）.txt`
的 `NEW SPRFILE <同名截面>` + `PARA` 行）**独立印证**：

* `族39` = 国标热轧 H 型钢（HN/HW/HM）：`H=字段3`、`B=字段5`、`tf=字段6`、`tw=字段7`（8 条中 7 条逐项吻合）；
* `族32` = 槽钢（子类型 1=普通 `1-*` → `/C_COMMON-SPEC/`；**2=轻型** `2-*` → `/C_LIGHT-SPEC/`）；
* `族31` = 工字钢、`族33` = 角钢（1=等边、3=不等边）、`族36/37/38` = 欧标/日标/美标 H、`族40` = 冷弯方矩管、
  `族66` = T 型钢、`族72` = 冷弯槽钢、`族77` = 用户参数化截面。
* **`[18a` 的"尺寸异常"已解释**：该行子类型 = **2 = 轻型槽钢**，拿它比 GB/T 706 **普通**槽钢（tw=7、tf=10.7）
  是比错了对象；**轻型槽钢的具体表值未逐项核对**（【未知】，见 §7#2）。
* **工程建议**：Kind=26 截面**以 `Name` 为准**做等级库映射，`ShapeVal` 尺寸仅作校验。

### 4.4 Kind=303 用户参数化截面（84 槽）

**槽位（下标从 0，`params = tokens[1:-2]`）**：

| 槽 | 含义 | 样本 |
|---|---|---|
| 0 | 族码 | `77`（参数化截面） |
| 1..6 | **打包规格串**（见下） | `12866,12341,12586,11824,12336,0` |
| 17 | 主尺寸 `d`（边长/直径，mm） | 250 / 200 / 194 |
| 19 | `b` | 与 d 同（方管） |
| 26 | **冷弯薄壁型钢库族码**（**不是壁厚**） | `6`=方管GB6728、`1`=热轧无缝圆管 |
| 29 | `Mat` | `5` |
| 31 | 未解码（16672 / 16640，**禁止使用**） | — |
| 末尾两槽 | `−1` 与**本行 ID** | 尾部标记 |

**打包规格串的算法（【事实】）**：`params[1:7]` 是 6 个 16 位整数，**每槽低字节在前**拼两个 ASCII 字符，
遇 `0x00` 截断：

```python
buf = bytearray()
for t in params[1:7]:
    v = int(float(t or 0))
    buf.append(v & 0xFF); buf.append((v >> 8) & 0xFF)
spec_str = bytes(buf).split(b"\x00")[0].decode("ascii")
```

**本次独立复算（只读样本、自写脚本，未复用引擎）**：

| 表/ID | `params[1:7]` | 复算出的串 | 同槽的族码 | 结论 |
|---|---|---|---|---|
| `pkpmColSect` 3985 | `12866,12341,12586,11824,12336,0` | `B250*10.00` | 6 | 方管 250×250×10.0 |
| `pkpmBraceSect` 62965 | `12866,12336,12586,11824,12336,0` | `B200*10.00` | 6 | 方管 200×200×10.0 |
| `pkpmColSect` 12729 | `12612,13369,14424,12334,0,0` | `D194X8.0` | 1 | 圆管 φ194×8.0 |

**该串就是匹配文件的查找键**（前面加"族码-"前缀）：`6-B250*10.00`、`6-B200*10.00`、`1-D194X8.0`
三条都能在用户的 `PKPM转PDMS截面匹配文件.txt` 里**原样查到**（本次验收检查 2 实测
`Kind=303` 截面按 `shapeval` 命中，`resolved`）。

---

## 5. 外键与 ID 空间

* **【事实】** 全部外键都指向**父表的 `ID` 列**；`No_` 只是**层内序号**，不是外键目标。
* **【事实】** 至少三套互不相干的 ID 空间，**数值会重叠**：
  ① 模型对象（节点/网格线/构件/房间）共用一个递增计数器；
  ② `pkpmStdFlr.ID` 与 `pkpmFloor.ID` 是两套序列（1001… / 5120…）；
  ③ 荷载表 ID（1006–1148）与模型对象 ID 数值重叠（例如 1007 既是节点号也可能是荷载截面号）
  ⇒ **解析时必须按表名区分，不能靠 ID 全局唯一**。
* **【事实】** 同一层内对象 ID **不连续、跨 5 个数量级**（例：标准层 3799 的对象 ID 从 3800 排到 62807）
  ⇒ **不要假设小规模连续编号**。

---

## 6. 单位、坐标与 Z 推导

### 6.1 单位与方向

* 长度 **mm**（标高 −2000…22060、层高 1000…7600、柱截面 600×600、梁长 175…7500 只能自洽于 mm）；
* **X = 东（E）、Y = 北（N）、Z = 上（U）**，右手系；
* 角度（`Rotation`）【推断】为**度**（样本全 0，无法验证）；
* 荷载【推断】kN / kN/m（见 §7#8）。

### 6.2 公式（`engine/jwd_read.py` 照此实现，契约 §a.5）

```
Level.z_bot      = pkpmFloor.LevelB
Level.z_top      = pkpmFloor.LevelB + pkpmFloor.Height        # 平面标高 = 层顶
Joint.z          = Level.z_top + pkpmJoint.HDiff
Beam.start/end   = (GridID → pkpmGrid.Jt1ID/Jt2ID → Joint.(x,y), Level.z_top + HDiff1 / + HDiff2)
Column.start/end = ( Joint.x + EccX, Joint.y + EccY, Level.z_bot + HDiffB ) → ( 同水平位置, Level.z_top )
Brace.start/end  = ( Jt1.(x,y) + (EccX1,EccY1), Level.z_top + HDiff1 )
                   → ( Jt2.(x,y) + (EccX2,EccY2), Level.z_top + HDiff2 )
Slab.polygon     = zip(pkpmSlab.VertexX, pkpmSlab.VertexY)    # TEXT 逗号分隔 → float
Slab.z           = Level.z_top                                # == Level.z_bot + VertexZ（实测 VertexZ == Height）
Opening          = pkpmSlab WHERE RoomIsHole = 1              # pkpmSlabHole 自身忽略
Member.level     = start 端所在层
Member.hdiff_*   = 原始 HDiffB / HDiff1,HDiff2（柱的 hdiff_end = 0）
```

### 6.3 本样本推得的 5 层（【事实】）

| 标准层 | 自然层 | z_bot | z_top | 层高 | 该层对象（实测） |
|---|---:|---:|---:|---:|---|
| 1001 | 5120 | −2000 | −1000 | 1000 | 40 柱、72 梁、29 房间 |
| 1736 | 5121 | −1000 | 6600 | 7600 | 40 柱、70 梁、24 房间、1 支撑 |
| 2205 | 5122 | 6600 | 11600 | 5000 | 40 柱、134 梁、59 房间 |
| 3799 | 5123 | 11600 | 16600 | 5000 | 40 柱、256 梁、83 房间 |
| 31531 | 32399 | 16600 | 22060 | 5460 | 40 柱、66 梁、27 房间、12 屋盖支撑 |

**"平面画在层顶"是唯一自洽解**：`pkpmSlab.VertexZ` 恒等于层高（若平面画在层底，板顶点 Z 应为 0）；
且每层恰好 40 根柱、柱的竖向范围恰好覆盖本层（−2000→−1000、−1000→6600、…、16600→22060），
若解释为"柱自层顶向上"，第 5 层柱会伸出屋面而这个文件只有 5 层。

### 6.4 验收自检（本次实跑，`python test\acceptance.py` 检查 3）

```
层标高：5 层；与 pkpmFloor(LevelB, LevelB+Height) 逐项一致 = 5/5
       实测层顶 = [-1000.0, 6600.0, 11600.0, 16600.0, 22060.0]
       pkpmStdFlr.Height 全 0（[0.0]）⇒ 按契约 §a.3 不得使用
节点：382 个；z == 层顶 + HDiff 且 x/y 一致 = 382/382
构件：811 根（梁 598/柱 200/支撑 13）；端点 (x,y,z) 与契约 §a.5 独立复算一致 = 811/811；其中 Z 不符 = 0
板：222 块；z == 层顶(pkpmFloor.LevelB+Height) = 222/222
板顶点 Z 列（pkpmSlab.VertexZ）：222 块中与所在层层高不符 = 0
例外合计 = 0
```

---

## 7. 已知缺口与未证实项（**必须随交付物一起给出**）

| # | 项 | 性质 | 本版怎么处理 | 怎么解决 |
|---|---|---|---|---|
| 1 | **Kind=3 的族别**（φ20 圆钢？方管？单位？） | 【未知】→ 已按证据判为**圆形** | `status='inferred'`：`/USER_CIRCLE-SPEC/Circle_Profile` + `DESP <d>`；报告带 `evidence`；可能一行改回 `unresolved`（`engine\secmap_extra.txt` 的 `@FAMILY 3 = CIRCLE` 或 `= none`） | 用含 Kind=3 的其他模型核对；或实机看这 12 根支撑的断面 |
| 2 | Kind=26 **轻型槽钢**的两个厚度位 | 【未知】（未查 GB/T 706 轻型表） | 以 `Name`（如 `[18a`）做映射 | 查 GB 轻型槽钢表 |
| 3 | Kind=303 的 31 号槽（16672/16640）等零槽语义 | 【未知】 | 忽略（不影响几何/截面重建） | 多族样本横向比对 |
| 4 | Kind=1 的 **B/H 先后** | 【推断-中】（B 前 H 后） | 按 `[B,H]` 出 `DESP`，`Section.note` 写明 | 用非对称梁（如 250×400）实机看断面朝向 |
| 5 | Kind=2 的 **B/T 交错序** | 【未知】 | 对称（`B1==B2 且 T1==T2`）才出 `DESP`，否则 `unresolved` | 取 `B1≠B2` 或 `T1≠T2` 的模型 |
| 6 | `Ecc/EccX/EccY` **正负方向** | 【未知】 | **只记录不过滤**：几何里按原值相加，非零偏心逐条进报告 | 取一根已知偏心梁实机复核 |
| 7 | `BraceSeg.HDiff2 = 6650` **符号与基准** | 【未知】 | 按"层顶 + HDiff"字面处理；由 `W-MEM-ZRANGE` 报出越层而不是静默 | 在 PKPM 里查看该构件（ID 63116） |
| 8 | **荷载数值语义**（类型码 1/2/3、kN vs kN/m） | 【未知】 | 只做"原样搬运 + 计数"，不参与几何；报告注明"参考值" | 与 PKPM 荷载界面/计算书比对 |
| 9 | `Rotation` 单位与基准轴 | 【推断】（度、绕构件自身轴） | 源值非 0 时写 `BANG`；样本全 0 无影响 | 造 `Rotation≠0` 的模型实测 |
| 10 | 空表族（墙/楼梯/次梁/阻尼器/柱帽/施工段）语义 | 【未知】 | 非空 ⇒ 记 `report.skipped`，不猜 | 另取含这些对象的 JWD 逆向 |
| 11 | `pkpmJoint.HDiff` 是否参与构件几何 | 本样本无法检验（382 行全 0） | 梁/支撑公式只用 `Level.z_top + 端部 HDiff`，**不用** `Joint.z` | 取 `HDiff≠0` 的模型 |
| 12 | `.jwd` 的 25 张空表以外的"未列为清单的表" | 实现局限 | 三张硬编码清单之外的表**不会被留痕**（见 §2.2 末） | 若要严格留痕，需按 `sqlite_master` 全集扫描（属后续增强） |

**未在 PDMS 实机验证**：以上结论全部来自**文件级只读解析 + 样本数据自检**，
**没有在 PDMS 12.1 SP4 里跑过**任何宏或 PML。

---

## 8. 编码：混合字节（最容易踩的坑）

**【事实】** 文件头 `PRAGMA encoding = UTF-8`，但**中文列的实际字节是混合编码**。本次实测原始字节：

| 表.列 | 原始字节（hex） | 正确解码 |
|---|---|---|
| `pkpmColSect.Name`（ID 3985） | `b1a1b1dab7bdb8d6b9dc3a20423235` | **GBK** → `薄壁方钢管: B25` |
| `pkpmColSect.Name`（ID 12729） | `c8c8d4fecedeb7ecd4b2b8d6b9dc3a` | **GBK** → `热轧无缝圆钢管:` |
| `pkpmBraceSect.Name`（ID 62965） | `b1a1b1dab7bdb8d6b9dc3a20423230` | **GBK** → `薄壁方钢管: B20` |
| `pkpmLoadSect.Loadname`（ID 1007） | `e697a0` | **UTF-8** → `无` |

**读取规则**：**逐值**解码 `ASCII → UTF-8 → GBK`（末级 `errors='replace'` 但要统计替换字符数并记报告）。
**禁止**整体 `text_factory=gbk`（会得到 `鏃�` 之类乱码，这正是"截面名乱码"的成因），也**禁止**整体 UTF-8。

写回 `.jwd` 时的列级规则（`engine/jwd_write.py`，契约 §b.3）：

| 列 | 写字节 |
|---|---|
| `pkpm*Sect.Name` | **GBK**（含中文时） |
| `pkpmLoadSect.Loadname` | **UTF-8** |
| 其余文本列（`ShapeVal`、`JYDef`、`VertexX/Y/Z`、`GridsID`、`strParas*` …） | **ASCII**；含非 ASCII 时用 **GBK** |

全部 ASCII 时三种编码等价，无风险；**禁止**写 BOM。

---

## 9. 怎么复现本文的核对

```bat
cd /d D:\AI_Work\PKPM数据解析\PKPM-JWD导入导出

:: ① 表数/行数/编码/关键列（只读 sqlite_master + PRAGMA table_info）
python test\check_deliverables.py            :: 原件指纹：46 表 / 6480 行 / UTF-8 / user_version=0

:: ② 读成规范模型并自检（层标高/端点 Z/板 Z 与 pkpmFloor 逐项比对）
python test\acceptance.py                    :: 检查 3 = 几何自检，例外合计 0

:: ③ 契约自身的自检（JSON 往返 / ShapeVal 解码 / 候选键命中）
python test\test_contract_selfcheck.py

:: ④ 只读样本、逐行打印层表与三张截面表（本文 §3/§4 的实例数据来源）
::    见 _recon\jwd_dump\*.txt（全表导出）或自行用 sqlite3 mode=ro 打开
```

> 说明：本文中的"本次实测"数字来自 `PKPM-JWD导入导出/` 包内的测试与只读探针；
> `_recon/` 下的侦察报告是**结论来源**，其"43 张表"等处与本次实测不一致的地方，**以本文与契约的实测值为准**。
