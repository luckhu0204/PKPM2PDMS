# -*- coding: utf-8 -*-
"""PKPM2PDMS导入导出 —— 规范模型 → ``.jwd``（SQLite3）。实施包④。

契约条款（``spec/CONTRACT.md``）：§b.3（建表 / 写入顺序 / 父表合成规则 / 文本列字节规则 /
返回值）、§a.2（数据类）、§a.4（ShapeVal 编码）、§a.5（几何公式）、§g（编码纪律）。
本模块按 §b.5 **只 import canonical**。

证据来源（逐条可复核）::

    * 46 条 ``CREATE TABLE`` + 79 条 ``CREATE INDEX`` —— **逐字**取自
      ``_recon\\jwd_dump\\00_schema.txt``（提取脚本 ``test/gen_ddl_block.py``；
      ``test/check_jwd_write_roundtrip.py`` 会逐条核对"本文件里的每条语句都是该文件的子串"）。
    * ``ShapeVal`` 的尾部形状 —— 样本逐行实测（``test/_wr_sample.txt`` 第 2 节）::

          '1,300,600,6,1380,'                     # Kind=1  → <Kind>,<B>,<H>,<Mat>,<ID>,
          '2,10,500,250,16,250,16,5,4080,'        # Kind=2  → Tw,H,B1,T1,B2,T2,Mat,ID
          '3,20,5,32335,'                         # Kind=3  → d,Mat,ID
          '26,39,1,450,0,200,14,9,0,5,4484,'      # Kind=26 → 族码,子类型,H,0,B,tf,tw,0,Mat,ID
          '303,77,…,0,-1,3985,'                   # Kind=303→ …,-1,ID（末二字段 = −1, 本行 ID）
      ⇒ 一律 ``"<Kind>,<参数体>,<Mat 或 −1>,<本行 ID>,"``，**结尾带一个逗号**（所以契约 §a.4
      解参时要先去掉尾部空串）。
    * 文本列字节规则 —— 样本 ``pkpmColSect.Name`` 是 **TEXT 存储类里的 GBK 字节**
      （``typeof='text'``，hex = GBK）。本模块用 ``CAST(? AS TEXT)`` 写 GBK 字节，
      实测 typeof 仍为 ``text``，且契约 §b.2 的 ``dec()`` text_factory 能读回
      （``test/_wr_sample.txt`` 第 13 节）。
    * ``pkpmSlab`` 的"可写常量列"与"可推导列" —— 本次对样本逐列 ``DISTINCT`` 实测
      （``test/_wr_sample.txt`` 第 14 节）：``cc=0``/``Shape=1``/``EdgeSupport=''``/
      ``TwoWaySlab=0``/``Precast*='0'``/``ProfilSlab*=25.0,1.5,100.0`` 等 29 列全表同值；
      ``nEdge`` = 顶点数（222/222）、``VertexZ`` = 板面高 − 层底、``xc/yc`` = 包围盒中心
      （222/222 反例 0）。逐行取值又推不出的列（``TransWay/Ang1/Ang2``）写 NULL 并进
      ``warnings`` —— **不猜**。

R2（契约 v2）新增：数据库反向 ``db2jwd``
----------------------------------------
本模块 v1 的 :func:`write_jwd` **一行未改**（§l.6 明令「v1 的 write_jwd 不动」），R2 只**追加**：

* :func:`write_jwd_sections` —— §l.6 的落点：``SectionTable.to_jwd_sections()`` 产出的
  ``{"beam":[...],"col":[...],"brace":[...]}`` → 只填三张截面表的 ``.jwd``
  （46 表全建、``Kind/ShapeVal/Name/Mat/No_`` 的填充规则见该函数文档）。
* :func:`shapeval_for` 的**构造路径**（§k.3 模板，跟 v1 的"原文搬运"并存）：

  | Kind | 构造条件（无 ``params`` 原文时） | 依据 |
  |---|---|---|
  | 1 | ``dims`` 有 ``B``/``H`` | §k.3；样本 ``1,300,600,6,1380,`` |
  | 3 | ``dims`` 有 ``d`` | §k.3；§0.4-1 的 CIRCLE 推断 |
  | 26 | ``dims`` 有 ``family``(须 **39**)/``H``/``B``/``tf``/``tw``（``subtype`` 缺省 1） | §k.3/§l.6；C10 的 ``PARA(450,200,9,14)`` 复现 ``26,39,1,450,0,200,14,9,0,5,<id>,`` |
  | 303 | ``dims`` 有 ``spec_str``/``d``/``lib_family``，且规格串首字符 ∈ {``B``,``D``} | §k.3 的槽位表 + 样本 3/3 行实测（``B…``→槽 32 = 16672、``D…``→16640） |
  | 其它 | **不可构造** ⇒ 报 ``missing`` 并让调用方落报告（§k.3「不得降级成空串」） | — |

  * **``Kind=2`` 的处置**（与 §k.3 字面「抛 unencodable」有出入，理由如下）：§l.6 明令
    v1 的 ``write_jwd`` 不动，而 v1 对 ``Kind=2`` 是**从 dims 槽位键编码**的（dims 的键就是
    §a.4 解出的槽位 ⇒ 编码即解码的逆；JLCJ2 样本 2/2 行逐字复现，见
    ``test/_db2jwd_out.txt`` §1(b)）；而 db2jwd 方向**没有任何族映射到 Kind=2**
    （§l.6 的族→Kind 表里没有它）⇒ 该方向不会请求它。故处置为：有槽位键 ⇒ 照常编码
    （``write_jwd_sections`` 会逐条 warning 提示 B/T 交错序未证实 §12#4）；既无槽位键
    又无 ``params`` 原文 ⇒ 拒绝 + 报告。
  * **打包串容量 12 字符**（6 槽 × 2，§a.4/§k.3）：超容量的规格串**拒绝编码 + 报告**，
    绝不截断（截断会得到另一个规格名）。本次实测族 77 的 1,199 条里 324 条超容量
    （库族码 7=168、9=156，全是矩形管），见 ``test/_db2jwd_out.txt`` §2 —— 这与
    ``db_pkpm_sections.md`` §4.4 的「长度超过容量则无法表达」一致；DLL 键表里存在 14 字符串
    （``B300*200*12.00``）说明真实编码可能用更多打包槽，但样本只观测到 6 槽 ⇒ 按契约不猜。
  * 构造路径**只认 dims 的槽位键**：``Section.params`` 的语义是 **ShapeVal 参数体原文**
    （canonical §a.4），而 DESP 是族参数序 —— 两者序不同，故 ``pdms_dump`` 不再把 DESP
    塞进 ``params``（只进 ``dims`` + ``note``），避免"原文搬运"分支把 DESP 序当 ShapeVal 序输出。
"""

from __future__ import annotations

import os
import re
import sqlite3
import tempfile
from typing import Any, Dict, List, Optional, Sequence, Tuple

from canonical import TOL, Level, Member, Model, Section

# ---------------------------------------------------------------------------
# DDL：46 表 + 79 索引，逐字取自 _recon\jwd_dump\00_schema.txt
# ---------------------------------------------------------------------------
# _DDL_TABLES / _DDL_INDEXES —— 逐字取自 _recon\jwd_dump\00_schema.txt
# （该文件与样本 JLCJ2.jwd 的 sqlite_master 一致；提取脚本 test/gen_ddl_block.py）
# CREATE TABLE 数 = 46，CREATE INDEX 数 = 79
_DDL_TABLES = [
    'CREATE TABLE pkpmAxis (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,StdFlrID INTEGER  REFERENCES pkpmStdFlr(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,Jt1ID INTEGER,Jt2ID INTEGER  REFERENCES pkpmJoint(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,Name TEXT)',
    'CREATE TABLE pkpmBeamJYDef (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,Kind INTEGER,Para TEXT)',
    'CREATE TABLE pkpmBeamSect (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,Name TEXT,Mat INTEGER  NOT NULL ON CONFLICT REPLACE DEFAULT 6,Kind INTEGER  NOT NULL ON CONFLICT REPLACE DEFAULT 1,ShapeVal TEXT)',
    'CREATE TABLE pkpmBeamSeg (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,StdFlrID INTEGER  REFERENCES pkpmStdFlr(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,SectID INTEGER  REFERENCES pkpmBeamSect(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,GridID INTEGER  REFERENCES pkpmGrid(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,Ecc INTEGER,HDiff1 INTEGER,HDiff2 INTEGER,Rotation REAL,JYDef TEXT)',
    'CREATE TABLE pkpmBraceSect (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,Name TEXT,Mat INTEGER  NOT NULL ON CONFLICT REPLACE DEFAULT 6,Kind INTEGER  NOT NULL ON CONFLICT REPLACE DEFAULT 1,ShapeVal TEXT)',
    'CREATE TABLE pkpmBraceSeg (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,StdFlrID INTEGER  REFERENCES pkpmStdFlr(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,SectID INTEGER  REFERENCES pkpmBraceSect(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,Jt1ID INTEGER  REFERENCES pkpmJoint(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,Jt2ID INTEGER  REFERENCES pkpmJoint(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,EccX1 INTEGER,EccY1 INTEGER,HDiff1 INTEGER,EccX2 INTEGER,EccY2 INTEGER,HDiff2 INTEGER,Rotation REAL)',
    'CREATE TABLE pkpmCantiSlab (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,StdFlrID INTEGER  REFERENCES pkpmStdFlr(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,SectID INTEGER  REFERENCES pkpmCantiSlabDef(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,GridID INTEGER  REFERENCES pkpmGrid(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,ez INTEGER,ec INTEGER,dr INTEGER)',
    'CREATE TABLE pkpmCantiSlabDef (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,Kind INTEGER,Length INTEGER,Width INTEGER,Thick INTEGER)',
    'CREATE TABLE pkpmColSect (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,Name TEXT,Mat INTEGER  NOT NULL ON CONFLICT REPLACE DEFAULT 6,Kind INTEGER  NOT NULL ON CONFLICT REPLACE DEFAULT 1,ShapeVal TEXT)',
    'CREATE TABLE pkpmColSeg (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,StdFlrID INTEGER  REFERENCES pkpmStdFlr(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,SectID INTEGER  REFERENCES pkpmColSect(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,JtID INTEGER  REFERENCES pkpmJoint(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,EccX INTEGER,EccY INTEGER,Rotation REAL,HDiffB INTEGER,ColcapId INTEGER,Cut_Col TEXT,Cut_Cap TEXT,Cut_Slab TEXT)',
    'CREATE TABLE pkpmColcapSect (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,Kind INTEGER,W INTEGER,L INTEGER,H INTEGER,SW INTEGER,SL INTEGER,SH INTEGER)',
    'CREATE TABLE pkpmCraneDef (No_ INTEGER NOT NULL, V1 REAL,NG INTEGER,NW1 INTEGER,PMAX REAL,WG REAL,BK REAL,RAILHEIGHT REAL,PMIN REAL,COEFFINCIENT REAL,aLK REAL,C1 REAL)',
    'CREATE TABLE pkpmCraneInfo (ID INTEGER, StdFlrID INTEGER  REFERENCES pkpmStdFlr(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,No_ INTEGER NOT NULL,xsA REAL,xsB REAL,JSN1 INTEGER,IDX11 INTEGER,IDX12 INTEGER,JAN2 INTEGER ,IDX21 INTEGER,IDX22 INTEGER,EX1 REAL,EX2 REAL,HX REAL,F1 REAL,F2 REAL,IDCHNUM INTEGER,IDCH1 INTEGER,IDCH2 REAL,ShapeVal TEXT)',
    'CREATE TABLE pkpmDamperSect (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,Style INTEGER ,Name TEXT,Kind INTEGER  NOT NULL ON CONFLICT REPLACE DEFAULT 1,d1 REAL,H REAL,H1 REAL,ShapeVal TEXT)',
    'CREATE TABLE pkpmFloor (ID INTEGER,No_ INTEGER,Name TEXT,StdFlrID INTEGER  REFERENCES pkpmStdFlr(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,LevelB REAL,Height REAL)',
    'CREATE TABLE pkpmGrid (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,StdFlrID INTEGER  REFERENCES pkpmStdFlr(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,Jt1ID INTEGER  REFERENCES pkpmJoint(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,Jt2ID INTEGER  REFERENCES pkpmJoint(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,AxisID INTEGER  REFERENCES pkpmAxis(ID) ON UPDATE CASCADE  ON DELETE SET NULL )',
    'CREATE TABLE pkpmJoint (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,StdFlrID INTEGER  REFERENCES pkpmStdFlr(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,X REAL,Y REAL,HDiff INTEGER)',
    'CREATE TABLE pkpmJointDamperSeg (BasepntID INTEGER ,Count INTEGER ,JointID TEXT,DamperID TEXT )',
    'CREATE TABLE pkpmLoadSect (ID INTEGER  PRIMARY KEY ASC,No INTEGER,Loadname TEXT,ElementKind INTEGER,ShapeVal TEXT)',
    'CREATE TABLE pkpmLoadSeg(ID INTEGER  PRIMARY KEY ASC, No INTEGER, SectID INTEGER, Type INTEGER, ElementID INTEGER, strParas1 TEXT, nPtCnt INTEGER, strParasX TEXT, strParasY TEXT, strParasZ TEXT, StdFlrID INTEGER)',
    'CREATE TABLE pkpmMemberDamperSeg (MemberID INTEGER  REFERENCES pkpmBeamSeg(ID) ON UPDATE CASCADE,DamperID INTEGER  )',
    'CREATE TABLE pkpmMidBeamSeg (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,StdFlrID INTEGER  REFERENCES pkpmStdFlr(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,SectID INTEGER  REFERENCES pkpmBeamSect(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,GridID INTEGER  REFERENCES pkpmGrid(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,Ecc INTEGER,HDiff1 INTEGER,HDiff2 INTEGER,Rotation REAL,JYDef TEXT)',
    'CREATE TABLE pkpmMidSlab (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,StdFlrID INTEGER  REFERENCES pkpmStdFlr(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,GridsID TEXT,VertexX TEXT,VertexY TEXT,VertexZ TEXT,LinkedRoomID INTEGER,Thickness INTEGER,cc INTEGER,dead REAL,live REAL,TransWay INTEGER,Ang1 REAL,Ang2 REAL,nEdge INTEGER,EdgeSupport TEXT,Shape INTEGER,xc REAL,yc REAL,HollowSlabID INTEGER,PrecastSlabID TEXT,PrecastSlabRebarPara TEXT,SingleSeamB INTEGER,SingleSeamBMax INTEGER,PairSeamB INTEGER,PairSeamBMax INTEGER,TwoWaySlab INTEGER,PrecastSlabLastL REAL,PrecastSlabRotate INTEGER,PrecastSlabStyle_PK INTEGER,PrecastSlabOffsetX INTEGER,PrecastSlabOffsetY INTEGER,PrecastSlabX TEXT,PrecastSlabY TEXT,PrecastSlabIndex INTEGER,PrecastSlabCount INTEGER,PrecastSlabArrangeNo TEXT,PrecastSlabArrangeWidth TEXT,precastSlabSpace TEXT,PrecastSlabParaArr TEXT,ProfilSlabDefId INTEGER,ProfilSlabAng REAL,ProfilSlabConcertW REAL,ProfilSlabWorkLoad REAL,ProfilSlabbhou REAL)',
    'CREATE TABLE pkpmPetroDeviceSect (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,Style INTEGER  ,Name TEXT,ShapeVal TEXT)',
    'CREATE TABLE pkpmPetroDeviceSeg (ID INTEGER  PRIMARY KEY ASC,SectID INTEGER,No_ INTEGER,Style INTEGER  ,Name TEXT,SlabID INTEGER  NOT NULL ON CONFLICT REPLACE DEFAULT 1,Ecc INTEGER  NOT NULL ON CONFLICT REPLACE DEFAULT 1,EccX INTEGER  NOT NULL ON CONFLICT REPLACE DEFAULT 1,EccY INTEGER  NOT NULL ON CONFLICT REPLACE DEFAULT 1,Rotation INTEGER  NOT NULL ON CONFLICT REPLACE DEFAULT 1,ByBeam INTEGER,BeamID INTEGER,fLen REAL,fWidth REAL,Beam2ID INTEGER,nCorner INTEGER,scornerX TEXT,scornerY TEXT)',
    'CREATE TABLE pkpmProperty (ID INTEGER,Name TEXT,Type INTEGER,ShapeVal TEXT)',
    'CREATE TABLE pkpmSatConstruct (FlrID INTEGER ,MemberID INTEGER ,MemberType INTEGER, MemberOrder INTEGER ,MemberDismantle INTEGER , PRIMARY KEY(FlrID ASC,MemberID ASC) ON CONFLICT REPLACE )',
    'CREATE TABLE pkpmSatCover (FlrID INTEGER ,CovID INTEGER, VertexX TEXT,VertexY TEXT,PRIMARY KEY(FlrID ASC,CovID ASC) ON CONFLICT REPLACE )',
    'CREATE TABLE pkpmSatTowPara (FlrID INTEGER ,TowID INTEGER,Kind INTEGER,ParaVal VARIANT, PRIMARY KEY(FlrID ASC,TowID ASC, Kind ASC) ON CONFLICT REPLACE )',
    'CREATE TABLE pkpmSatTowReinInfo (FlrID INTEGER ,TowID INTEGER,Kind INTEGER,ParaVal VARIANT, PRIMARY KEY(FlrID ASC,TowID ASC, Kind ASC) ON CONFLICT REPLACE )',
    'CREATE TABLE pkpmSatTower (FlrID INTEGER NOT NULL ,TowID INTEGER NOT NULL, VertexX TEXT,VertexY TEXT,PRIMARY KEY(FlrID ASC, TowID ASC) ON CONFLICT REPLACE )',
    'CREATE TABLE pkpmSlab (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,StdFlrID INTEGER  REFERENCES pkpmStdFlr(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,GridsID TEXT,VertexX TEXT,VertexY TEXT,VertexZ TEXT,RoomIsHole INTEGER,Thickness INTEGER,cc INTEGER,dead REAL,live REAL,TransWay INTEGER,Ang1 REAL,Ang2 REAL,nEdge INTEGER,EdgeSupport TEXT,Shape INTEGER,xc REAL,yc REAL,HollowSlabID INTEGER,PrecastSlabID TEXT,PrecastSlabRebarPara TEXT,SingleSeamB INTEGER,SingleSeamBMax INTEGER,PairSeamB INTEGER,PairSeamBMax INTEGER,TwoWaySlab INTEGER,PrecastSlabLastL REAL,PrecastSlabRotate INTEGER,PrecastSlabStyle_PK INTEGER,PrecastSlabOffsetX INTEGER,PrecastSlabOffsetY INTEGER,PrecastSlabX TEXT,PrecastSlabY TEXT,PrecastSlabIndex INTEGER,PrecastSlabCount INTEGER,PrecastSlabArrangeNo TEXT,PrecastSlabArrangeWidth TEXT,precastSlabSpace TEXT,PrecastSlabParaArr TEXT,ProfilSlabDefId INTEGER,ProfilSlabAng REAL,ProfilSlabConcertW REAL,ProfilSlabWorkLoad REAL,ProfilSlabbhou REAL)',
    'CREATE TABLE pkpmSlabHole (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,StdFlrID INTEGER  REFERENCES pkpmStdFlr(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,SectID INTEGER  REFERENCES pkpmSlabHoleDef(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,JtID INTEGER  REFERENCES pkpmJoint(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,SlabID INTEGER  REFERENCES pkpmSlab(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,EccX INTEGER,EccY INTEGER,Rotation REAL)',
    'CREATE TABLE pkpmSlabHoleDef (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,Kind INTEGER  NOT NULL ON CONFLICT REPLACE DEFAULT 1,ShapeVal TEXT)',
    'CREATE TABLE pkpmSlabJYDef (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,Kind INTEGER,Para TEXT)',
    'CREATE TABLE pkpmStairDef (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,StdFlrID INTEGER  REFERENCES pkpmStdFlr(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,Type INTEGER,StairBeamNum INTEGER,StairColmNum INTEGER,StairSlabNum INTEGER,StepHeight REAL,StepWidth REAL,AutoAddMidColumn INTEGER,AutoAddCorColumn INTEGER, ParaOfStep1 TEXT, FlatWidth REAL,nCorner INTEGER,CornerX TEXT,CornerY TEXT,nStair INTEGER, StairBeamInfo TEXT, StairColmInfo TEXT, StairSlabInfo TEXT )',
    'CREATE TABLE pkpmStairSeg (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,StdFlrID INTEGER  REFERENCES pkpmStdFlr(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,SectionID INTEGER,SlabID INTEGER,StartNode INTEGER,AntiClockwise INTEGER)',
    'CREATE TABLE pkpmStdFlr (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,Height INTEGER)',
    'CREATE TABLE pkpmStdFlrPara (StdFlrID INTEGER  REFERENCES pkpmStdFlr(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,Kind INTEGER,ParaVal VARIANT, PRIMARY KEY(StdFlrID ASC,Kind ASC) ON CONFLICT REPLACE )',
    'CREATE TABLE pkpmSubBeam (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,StdFlrID INTEGER  REFERENCES pkpmStdFlr(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,SectID INTEGER  REFERENCES pkpmBeamSect(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,X1 REAL,Y1 REAL,Z1 REAL,X2 REAL,Y2 REAL,Z2 REAL,Grid1ID INTEGER  REFERENCES pkpmGrid(ID) ON UPDATE CASCADE  ON DELETE SET NULL ,Grid2ID INTEGER  REFERENCES pkpmGrid(ID) ON UPDATE CASCADE  ON DELETE SET NULL )',
    'CREATE TABLE pkpmSysInfo (ID INTEGER  PRIMARY KEY ASC,ParaVal VARIANT)',
    'CREATE TABLE pkpmULoadDef (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,kind INTEGER,dDead REAL,nLive INTEGER,dLive1 REAL,dLive2 REAL,dLive3 REAL,strName TEXT,Data TEXT)',
    'CREATE TABLE pkpmWallHole (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,StdFlrID INTEGER  REFERENCES pkpmStdFlr(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,SectID INTEGER  REFERENCES pkpmWallHoleDef(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,GridID INTEGER  REFERENCES pkpmGrid(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,Ecc REAL,HDiff REAL)',
    'CREATE TABLE pkpmWallHoleDef (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,B INTEGER,H INTEGER)',
    'CREATE TABLE pkpmWallSect (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,Mat INTEGER  NOT NULL ON CONFLICT REPLACE DEFAULT 6,Kind INTEGER  NOT NULL ON CONFLICT REPLACE DEFAULT 1,B INTEGER,H INTEGER)',
    'CREATE TABLE pkpmWallSeg (ID INTEGER  PRIMARY KEY ASC,No_ INTEGER,StdFlrID INTEGER  REFERENCES pkpmStdFlr(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,SectID INTEGER  REFERENCES pkpmWallSect(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,GridID INTEGER  REFERENCES pkpmGrid(ID) ON UPDATE CASCADE  ON DELETE CASCADE ,Ecc INTEGER,HDiff1 INTEGER,HDiff2 INTEGER,HDiffB INTEGER,sloping INTEGER,EccDown INTEGER,offset1 INTEGER,offset2 INTEGER)',
]

_DDL_INDEXES = [
    'CREATE INDEX idx_pkpmAxis_Jt2ID ON pkpmAxis (Jt2ID ASC)',
    'CREATE INDEX idx_pkpmAxis_No_ ON pkpmAxis (No_ ASC)',
    'CREATE INDEX idx_pkpmAxis_StdFlrID ON pkpmAxis (StdFlrID ASC)',
    'CREATE INDEX idx_pkpmBeamJYDef_No_ ON pkpmBeamJYDef (No_ ASC)',
    'CREATE INDEX idx_pkpmBeamSect_No_ ON pkpmBeamSect (No_ ASC)',
    'CREATE INDEX idx_pkpmBeamSeg_GridID ON pkpmBeamSeg (GridID ASC)',
    'CREATE INDEX idx_pkpmBeamSeg_No_ ON pkpmBeamSeg (No_ ASC)',
    'CREATE INDEX idx_pkpmBeamSeg_SectID ON pkpmBeamSeg (SectID ASC)',
    'CREATE INDEX idx_pkpmBeamSeg_StdFlrID ON pkpmBeamSeg (StdFlrID ASC)',
    'CREATE INDEX idx_pkpmBraceSect_No_ ON pkpmBraceSect (No_ ASC)',
    'CREATE INDEX idx_pkpmBraceSeg_Jt1ID ON pkpmBraceSeg (Jt1ID ASC)',
    'CREATE INDEX idx_pkpmBraceSeg_Jt2ID ON pkpmBraceSeg (Jt2ID ASC)',
    'CREATE INDEX idx_pkpmBraceSeg_No_ ON pkpmBraceSeg (No_ ASC)',
    'CREATE INDEX idx_pkpmBraceSeg_SectID ON pkpmBraceSeg (SectID ASC)',
    'CREATE INDEX idx_pkpmBraceSeg_StdFlrID ON pkpmBraceSeg (StdFlrID ASC)',
    'CREATE INDEX idx_pkpmCantiSlabDef_No_ ON pkpmCantiSlabDef (No_ ASC)',
    'CREATE INDEX idx_pkpmCantiSlab_GridID ON pkpmCantiSlab (GridID ASC)',
    'CREATE INDEX idx_pkpmCantiSlab_No_ ON pkpmCantiSlab (No_ ASC)',
    'CREATE INDEX idx_pkpmCantiSlab_SectID ON pkpmCantiSlab (SectID ASC)',
    'CREATE INDEX idx_pkpmCantiSlab_StdFlrID ON pkpmCantiSlab (StdFlrID ASC)',
    'CREATE INDEX idx_pkpmColSect_No_ ON pkpmColSect (No_ ASC)',
    'CREATE INDEX idx_pkpmColSeg_JtID ON pkpmColSeg (JtID ASC)',
    'CREATE INDEX idx_pkpmColSeg_No_ ON pkpmColSeg (No_ ASC)',
    'CREATE INDEX idx_pkpmColSeg_SectID ON pkpmColSeg (SectID ASC)',
    'CREATE INDEX idx_pkpmColSeg_StdFlrID ON pkpmColSeg (StdFlrID ASC)',
    'CREATE INDEX idx_pkpmColcapSect_No_ ON pkpmColcapSect (No_ ASC)',
    'CREATE INDEX idx_pkpmFloor_No_ ON pkpmFloor (No_ ASC)',
    'CREATE INDEX idx_pkpmFloor_StdFlrID ON pkpmFloor (StdFlrID ASC)',
    'CREATE INDEX idx_pkpmGrid_Jt1ID ON pkpmGrid (Jt1ID ASC)',
    'CREATE INDEX idx_pkpmGrid_Jt2ID ON pkpmGrid (Jt2ID ASC)',
    'CREATE INDEX idx_pkpmGrid_No_ ON pkpmGrid (No_ ASC)',
    'CREATE INDEX idx_pkpmGrid_StdFlrID ON pkpmGrid (StdFlrID ASC)',
    'CREATE INDEX idx_pkpmJoint_No_ ON pkpmJoint (No_ ASC)',
    'CREATE INDEX idx_pkpmJoint_StdFlrID ON pkpmJoint (StdFlrID ASC)',
    'CREATE INDEX idx_pkpmMidBeamSeg_GridID ON pkpmMidBeamSeg (GridID ASC)',
    'CREATE INDEX idx_pkpmMidBeamSeg_No_ ON pkpmMidBeamSeg (No_ ASC)',
    'CREATE INDEX idx_pkpmMidBeamSeg_SectID ON pkpmMidBeamSeg (SectID ASC)',
    'CREATE INDEX idx_pkpmMidBeamSeg_StdFlrID ON pkpmMidBeamSeg (StdFlrID ASC)',
    'CREATE INDEX idx_pkpmMidSlab_No_ ON pkpmMidSlab (No_ ASC)',
    'CREATE INDEX idx_pkpmMidSlab_StdFlrID ON pkpmMidSlab (StdFlrID ASC)',
    'CREATE INDEX idx_pkpmSatCover_CovID ON pkpmSatCover (CovID ASC)',
    'CREATE INDEX idx_pkpmSatCover_FlrID ON pkpmSatCover (FlrID ASC)',
    'CREATE INDEX idx_pkpmSatTowPara_FlrID ON pkpmSatTowPara (FlrID ASC)',
    'CREATE INDEX idx_pkpmSatTowPara_Kind ON pkpmSatTowPara (Kind ASC)',
    'CREATE INDEX idx_pkpmSatTowReinInfo_FlrID ON pkpmSatTowReinInfo (FlrID ASC)',
    'CREATE INDEX idx_pkpmSatTowReinInfo_Kind ON pkpmSatTowReinInfo (Kind ASC)',
    'CREATE INDEX idx_pkpmSatTower_FlrID ON pkpmSatTower (FlrID ASC)',
    'CREATE INDEX idx_pkpmSatTower_TowID ON pkpmSatTower (TowID ASC)',
    'CREATE INDEX idx_pkpmSlabHoleDef_No_ ON pkpmSlabHoleDef (No_ ASC)',
    'CREATE INDEX idx_pkpmSlabHole_JtID ON pkpmSlabHole (JtID ASC)',
    'CREATE INDEX idx_pkpmSlabHole_No_ ON pkpmSlabHole (No_ ASC)',
    'CREATE INDEX idx_pkpmSlabHole_SectID ON pkpmSlabHole (SectID ASC)',
    'CREATE INDEX idx_pkpmSlabHole_StdFlrID ON pkpmSlabHole (StdFlrID ASC)',
    'CREATE INDEX idx_pkpmSlabJYDef_No_ ON pkpmSlabJYDef (No_ ASC)',
    'CREATE INDEX idx_pkpmSlab_No_ ON pkpmSlab (No_ ASC)',
    'CREATE INDEX idx_pkpmSlab_StdFlrID ON pkpmSlab (StdFlrID ASC)',
    'CREATE INDEX idx_pkpmStairDef_No_ ON pkpmStairDef (No_ ASC)',
    'CREATE INDEX idx_pkpmStairDef_StdFlrID ON pkpmStairDef (StdFlrID ASC)',
    'CREATE INDEX idx_pkpmStairSeg_No_ ON pkpmStairSeg (No_ ASC)',
    'CREATE INDEX idx_pkpmStairSeg_StdFlrID ON pkpmStairSeg (StdFlrID ASC)',
    'CREATE INDEX idx_pkpmStdFlrPara_Kind ON pkpmStdFlrPara (Kind ASC)',
    'CREATE INDEX idx_pkpmStdFlrPara_StdFlrID ON pkpmStdFlrPara (StdFlrID ASC)',
    'CREATE INDEX idx_pkpmStdFlr_No_ ON pkpmStdFlr (No_ ASC)',
    'CREATE INDEX idx_pkpmSubBeam_Grid1ID ON pkpmSubBeam (Grid1ID ASC)',
    'CREATE INDEX idx_pkpmSubBeam_Grid2ID ON pkpmSubBeam (Grid2ID ASC)',
    'CREATE INDEX idx_pkpmSubBeam_No_ ON pkpmSubBeam (No_ ASC)',
    'CREATE INDEX idx_pkpmSubBeam_SectID ON pkpmSubBeam (SectID ASC)',
    'CREATE INDEX idx_pkpmSubBeam_StdFlrID ON pkpmSubBeam (StdFlrID ASC)',
    'CREATE INDEX idx_pkpmULoadDef_No_ ON pkpmULoadDef (No_ ASC)',
    'CREATE INDEX idx_pkpmWallHoleDef_No_ ON pkpmWallHoleDef (No_ ASC)',
    'CREATE INDEX idx_pkpmWallHole_GridID ON pkpmWallHole (GridID ASC)',
    'CREATE INDEX idx_pkpmWallHole_No_ ON pkpmWallHole (No_ ASC)',
    'CREATE INDEX idx_pkpmWallHole_SectID ON pkpmWallHole (SectID ASC)',
    'CREATE INDEX idx_pkpmWallHole_StdFlrID ON pkpmWallHole (StdFlrID ASC)',
    'CREATE INDEX idx_pkpmWallSect_No_ ON pkpmWallSect (No_ ASC)',
    'CREATE INDEX idx_pkpmWallSeg_GridID ON pkpmWallSeg (GridID ASC)',
    'CREATE INDEX idx_pkpmWallSeg_No_ ON pkpmWallSeg (No_ ASC)',
    'CREATE INDEX idx_pkpmWallSeg_SectID ON pkpmWallSeg (SectID ASC)',
    'CREATE INDEX idx_pkpmWallSeg_StdFlrID ON pkpmWallSeg (StdFlrID ASC)',
]


#: 全部表名（返回值 ``tables`` 的键，契约 §b.3）
TABLE_NAMES: Tuple[str, ...] = tuple(sorted(
    re.match(r'CREATE TABLE\s+(\w+)', s).group(1) for s in _DDL_TABLES))

#: 契约 §b.3 的建表/写入顺序（父表先于子表）；其余表只建表不插行
WRITE_ORDER: Tuple[str, ...] = (
    'pkpmStdFlr', 'pkpmFloor', 'pkpmJoint', 'pkpmAxis', 'pkpmGrid',
    'pkpmBeamSect', 'pkpmColSect', 'pkpmBraceSect',
    'pkpmColSeg', 'pkpmBeamSeg', 'pkpmBraceSeg',
    'pkpmSlab', 'pkpmSlabHole', 'pkpmLoadSect', 'pkpmLoadSeg',
    'pkpmProperty', 'pkpmSysInfo', 'pkpmStdFlrPara')

#: ``Section.table`` → JWD 截面表名（契约 §a.2 的取值域：'beam'|'col'|'brace'|…）
_SECT_TABLE = {'beam': 'pkpmBeamSect', 'col': 'pkpmColSect', 'brace': 'pkpmBraceSect'}

#: 构件类型 → JWD 截面表名（注意与 ``Section.table`` 的域不同：这里是 'column'）
_TYPE_SECT = {'beam': 'pkpmBeamSect', 'column': 'pkpmColSect', 'brace': 'pkpmBraceSect'}

#: 构件类型 → 段表
_SEG_TABLE = {'column': 'pkpmColSeg', 'beam': 'pkpmBeamSeg', 'brace': 'pkpmBraceSeg'}

#: ``pkpmLoadSect.ElementKind``（jwd_format.md §1.6：12 = 梁上线荷载，−1 = 节点集中荷载）
_LOAD_ELEMENT_KIND = {'beam-line': 12, 'joint-point': -1}

#: ``pkpmSlab`` 里样本全表同值（未启用）的列 —— 语义未解，只为保持 PKPM 端字段完整而
#: 写入同一常量（逐列 DISTINCT 实测见 ``test/_wr_sample.txt`` 第 14 节）。
_SLAB_DEFAULTS: Dict[str, Any] = {
    'cc': 0, 'Shape': 1, 'EdgeSupport': '', 'TwoWaySlab': 0,
    'HollowSlabID': 0, 'PrecastSlabID': '0', 'PrecastSlabRebarPara': '0',
    'SingleSeamB': 0, 'SingleSeamBMax': 0, 'PairSeamB': 0, 'PairSeamBMax': 0,
    'PrecastSlabLastL': 0.0, 'PrecastSlabRotate': 0, 'PrecastSlabStyle_PK': 0,
    'PrecastSlabOffsetX': 0, 'PrecastSlabOffsetY': 0, 'PrecastSlabX': '0',
    'PrecastSlabY': '0', 'PrecastSlabIndex': 0, 'PrecastSlabCount': 0,
    'PrecastSlabArrangeNo': '0', 'PrecastSlabArrangeWidth': '0',
    'precastSlabSpace': '0', 'PrecastSlabParaArr': '', 'ProfilSlabDefId': 0,
    'ProfilSlabAng': 0.0, 'ProfilSlabConcertW': 25.0,
    'ProfilSlabWorkLoad': 1.5, 'ProfilSlabbhou': 100.0,
}

#: ``pkpmSlab`` 里样本逐行取值、规范模型不承载、无法推导的列（写 NULL + 进 warnings）
_SLAB_UNKNOWN_COLS = ('TransWay', 'Ang1', 'Ang2')


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
class _GbkBytes:
    """标记：该值以 **GBK 字节** 写进 TEXT 列（契约 §b.3 的字节规则）。

    契约 §g.3：先编码再写 —— ``encode('gbk')`` 失败即抛（禁止静默替换）。
    """

    __slots__ = ('data',)

    def __init__(self, s: str):
        self.data = str(s).encode('gbk')


def _txt(s: Any) -> Any:
    """契约 §b.3：一般文本列 —— 全 ASCII 用 ``str``，含非 ASCII 用 GBK 字节。"""
    t = '' if s is None else str(s)
    try:
        t.encode('ascii')
        return t
    except UnicodeEncodeError:
        return _GbkBytes(t)


def _fmt(v: Any) -> str:
    """参数体里的数字：整数值写整数（样本即此形状），否则最简浮点文本。"""
    f = float(v)
    if f == int(f):
        return str(int(f))
    return repr(f)


def _fmt2(v: Any) -> str:
    """坐标文本：能精确表示到 2 位小数就用 ``%.2f``（样本格式），否则保精度不四舍五入。"""
    f = float(v)
    if round(f, 2) == f:
        return '%.2f' % f
    return repr(f)


def _csv2(vals: Sequence[float]) -> str:
    """``VertexX/Y/Z`` 形状：每个值后跟一个逗号（样本 ``'0.00,0.00,2475.00,'``）。"""
    return ''.join(_fmt2(v) + ',' for v in vals)


def _csv_int(vals: Sequence[int]) -> str:
    """``GridsID`` 形状：``'2243,2247,2244,2254,'``。"""
    return ''.join('%d,' % int(v) for v in vals)


def _zdelta(z: float, base: float) -> float:
    """高差 = 端点标高 − 基准标高；|差| ≤ TOL 归零（去掉 −0.0 / 1e-13 噪声）。"""
    d = float(z) - float(base)
    return 0.0 if abs(d) <= TOL else d


def _check_unique(what: str, ids: Sequence[int]) -> None:
    """.jwd 的主键就是 ID —— 重复必须中止（否则 INSERT 直接失败，报错难懂）。"""
    seen, dup = set(), []
    for i in ids:
        if i in seen and i not in dup:
            dup.append(i)
        seen.add(i)
    if dup:
        raise ValueError('%s 的 ID 重复 %s：.jwd 以 ID 为主键，写回前必须唯一'
                         '（契约 §b.3 / jwd_format.md §2.1）' % (what, dup[:8]))


# ---------------------------------------------------------------------------
# 楼层：楼层型直接写；平面型按契约 §b.3 归并成楼层
# ---------------------------------------------------------------------------
class _FloorSet:
    """要写出的楼层集合 + "某个对象属于哪一层"的判定。

    ``direct``（楼层型模型，``.jwd`` 来源）：对象的 ``level`` 字段**就是**楼层键，
    直接 ``by_key`` 取回；只有平面型（``.pdt`` / ``dump`` 来源）才按标高归并/定位。
    """

    def __init__(self, floors: List[Level], merged: bool):
        self.floors = floors
        self.merged = merged
        self.direct = not merged

    def by_key(self, key: int) -> Optional[Level]:
        for f in self.floors:
            if f.stdflr_id == key:
                return f
        return None

    def for_joint(self, level_key: int, z: float) -> Tuple[Optional[Level], str]:
        """节点：楼层型按 ``level``；平面型按"层顶 == z"（§a.3 的平面画在层顶）。"""
        if self.direct:
            f = self.by_key(level_key)
            if f is not None:
                return f, ''
        return self.by_z(z)

    def for_slab(self, level_key: int, z: float) -> Tuple[Optional[Level], str]:
        """板：同节点（板的 ``level`` 与 ``z`` 在楼层型模型里是同一层）。"""
        if self.direct:
            f = self.by_key(level_key)
            if f is not None:
                return f, ''
        return self.by_z(z)

    def for_member_obj(self, level_key: int, mtype: str, z0: float
                       ) -> Tuple[Optional[Level], str]:
        """构件：楼层型按 ``level``；平面型按柱=层底/梁支撑=层顶（§a.5 的基准标高）。"""
        if self.direct:
            f = self.by_key(level_key)
            if f is not None:
                return f, ''
        return self.for_member(mtype, z0)

    def by_top(self, z: float) -> Optional[Level]:
        for f in self.floors:
            if abs(f.z_top - z) <= TOL:
                return f
        return None

    def by_bot(self, z: float) -> Optional[Level]:
        for f in self.floors:
            if abs(f.z_bot - z) <= TOL:
                return f
        return None

    def containing(self, z: float) -> Optional[Level]:
        for f in self.floors:
            if (f.z_bot - TOL) <= z <= (f.z_top + TOL):
                return f
        return None

    def nearest_below(self, z: float) -> Optional[Level]:
        cand = [f for f in self.floors if f.z_bot <= z + TOL]
        if not cand:
            return self.floors[0] if self.floors else None
        return max(cand, key=lambda f: f.z_bot)

    def by_z(self, z: float) -> Tuple[Optional[Level], str]:
        """平面型模型：优先"层顶 == 该标高"（.jwd 的标准层平面画在层顶，契约 §a.3）。"""
        for finder, why in ((self.by_top, ''),
                            (self.by_bot, '层顶无匹配，按层底落到层 %s'),
                            (self.containing, '层顶/层底均无匹配，按"落在层区间内"落到层 %s'),
                            (self.nearest_below, '标高不在任何层区间内，落到最近的层 %s')):
            f = finder(z)
            if f is not None:
                return f, (why % f.stdflr_id) if why else ''
        return None, '模型没有楼层'

    def for_member(self, mtype: str, z0: float) -> Tuple[Optional[Level], str]:
        """构件：柱按"层底 == 起点标高"、梁/支撑按"层顶 == 起点标高"（§a.5 的基准）。

        ``z0`` 取 ``Member.level`` 那个 Level 的标高（平面型 Level 的 z_bot == z_top）。
        """
        order = (('bot', self.by_bot), ('top', self.by_top), ('in', self.containing)) \
            if mtype == 'column' else \
            (('top', self.by_top), ('bot', self.by_bot), ('in', self.containing))
        for tag, finder in order:
            f = finder(z0)
            if f is not None:
                if tag == 'in':
                    return f, '起点标高 %g 只能按"落在层区间内"定位到层 %s' % (z0, f.stdflr_id)
                return f, ''
        f = self.nearest_below(z0)
        if f is not None:
            return f, '起点标高 %g 不在任何层区间内，落到最近的层 %s' % (z0, f.stdflr_id)
        return None, '模型没有楼层'


def _dedup_sorted(vals: Sequence[float]) -> List[float]:
    out: List[float] = []
    for v in sorted(float(x) for x in vals):
        if not out or abs(v - out[-1]) > TOL:
            out.append(v)
    return out


def _build_floors(model: Model, warnings: List[str]) -> _FloorSet:
    """要写出的楼层集合。

    全为楼层型（``height > 0``）⇒ 原样写；存在平面型 ⇒ 按契约 §b.3 把"模型里出现过的
    全部 Z 升序去重后相邻成层"，最高面不再单独成层。
    """
    if model.levels and not any(l.is_plane for l in model.levels):
        return _FloorSet(sorted(model.levels, key=lambda l: (l.z_bot, l.z_top, l.stdflr_id)),
                         False)
    zs: List[float] = []
    for l in model.levels:
        zs += [l.z_bot, l.z_top]
    for j in model.joints.values():
        zs.append(j.z)
    for m in model.members:
        zs += [m.start[2], m.end[2]]
    for s in model.slabs:
        zs.append(s.z)
    for wl in model.walls:
        zs += [wl.z_bot, wl.z_top]
    zz = _dedup_sorted(zs)
    floors = [Level(stdflr_id=i + 1, floor_id=i + 1, no=i + 1,
                    z_bot=zz[i], z_top=zz[i + 1], height=zz[i + 1] - zz[i], name='')
              for i in range(max(0, len(zz) - 1))]
    if floors:
        warnings.append('平面型 Level 已按契约 §b.3 归并成楼层：模型内 %d 个标高 → %d 层，'
                        'stdflr_id/floor_id/No_ 为合成序号 1..%d（标高：%s）'
                        % (len(zz), len(floors), len(floors),
                           ', '.join('%g' % z for z in zz[:8]) + (', …' if len(zz) > 8 else '')))
    return _FloorSet(floors, True)


# ---------------------------------------------------------------------------
# ShapeVal 反算（契约 §a.4 的逆运算 + R2 §k.3 的构造模板）
# ---------------------------------------------------------------------------
def _pack_spec_str(spec: str) -> List[int]:
    """契约 §a.4：6 个 16 位整数，每槽"低字节在前"拼两个 ASCII 字符，``0x00`` 截断。

    .. warning::
       容量只有 **12 字符**（6 槽 × 2）。调用方必须先做 :func:`_spec_str_capacity_error`
       检查 —— 本函数对超长串会**静默截断**，只用于"已经过检查"的输入。
    """
    buf = bytearray(str(spec).encode('ascii'))[:12]
    buf += b'\x00' * (12 - len(buf))
    return [buf[i] | (buf[i + 1] << 8) for i in range(0, 12, 2)]


def _spec_str_capacity_error(spec: str) -> str:
    """Kind=303 的规格串能否放进打包槽（6 槽 × 2 字符 = **12**）；不能则返回原因。

    依据：契约 §a.4/§k.3 的槽 2..7 布局（样本 3/3 条观测）；超容量的情形
    ``db_pkpm_sections.md`` §4.4 已记为"无法表达"，故本实现**拒绝编码并报告**，
    绝不截断成另一个规格名（本次实测：族 77 里有 ``7-B150*100*10.00`` 这类 15 字符串）。
    """
    s = str(spec)
    if not s:
        return '规格串为空'
    if len(s) > 12:
        return ('规格串 %r 长 %d 字符 > 打包槽容量 12（6 槽 × 2，契约 §a.4/§k.3）'
                '⇒ 无法表达' % (s, len(s)))
    if not all(0x21 <= ord(c) <= 0x7e for c in s):
        return '规格串 %r 含非可见 ASCII 字符 ⇒ 打包槽放不下' % s
    return ''


#: R2 §k.3 / §a.4：Kind=303 的槽位（**split 下标**，split_len=84）
_K303_SPLIT_LEN = 84
_K303_BODY_LEN = 80          # = split[1:-2] 的长度（去掉首字段 Kind 与尾部 Mat/ID）
_K303_FAMILY = 77            # 槽 1：薄壁管/钢管族码
_K303_SLOT_D = 18            # 槽 18：d（边长/直径）
_K303_SLOT_D2 = 20           # 槽 20：d（矩形管的另一边长**未观测** ⇒ 沿用 d，§k.3）
_K303_SLOT_LIB = 27          # 槽 27：库族码（= 名首数字）
_K303_SLOT_MAT = 30          # 槽 30：Mat
_K303_SLOT_SHAPE = 32        # 槽 32：形状码（方矩 16672 / 圆 16640）
_K303_SHAPE_SQUARE = 16672
_K303_SHAPE_CIRCLE = 16640

#: Kind=26（族码 39）的固定子类型（§l.6：「`subtype=1`」）
_K26_SUBTYPE_DEFAULT = 1


def _shape_code_for_spec(spec: str) -> Optional[int]:
    """规格串 → §k.3 的槽 32 形状码；不认识的形状返回 ``None``（不猜）。

    证据（本次实测，见 ``test/_v2_slots.txt``）：样本 3/3 条 —— ``B250*10.00``/
    ``B200*10.00`` → **16672**、``D194X8.0`` → **16640**；内置表族 77 的 1,199 条规格串
    首字符只有 ``B``(782) 与 ``D``(417) ⇒ 本函数对族 77 全覆盖。
    """
    if not spec:
        return None
    if spec[0] == 'B':
        return _K303_SHAPE_SQUARE
    if spec[0] == 'D':
        return _K303_SHAPE_CIRCLE
    return None


def _shapeval_303_from_dims(d: Dict[str, Any], mat: int, sid: int,
                            missing: List[str]) -> Optional[str]:
    """R2 §k.3：由 ``dims``（``spec_str``/``d``/``lib_family``）**构造** Kind=303 的参数体。

    样本槽位实测（``test/_v2_slots.txt`` §1）：非零槽只有
    ``0=303, 1=77, 2..7=打包串, 18=d, 20=d, 27=库族码, 30=Mat, 32=形状码, 81=-1, 82=ID``，
    其余全 0、``split_len=84`` ⇒ 参数体 = split[1:81]（80 个字段）。
    """
    spec = d.get('spec_str')
    lib = d.get('lib_family')
    dv = d.get('d')
    if spec is None:
        missing.append('spec_str（Kind=303 的打包规格串）')
    if lib is None:
        missing.append('lib_family（槽 27 的库族码）')
    if dv is None:
        missing.append('d（槽 18/20 的尺寸）')
    shape = _shape_code_for_spec(str(spec)) if spec else None
    if spec and shape is None:
        missing.append('槽 32 形状码（规格串首字符 %r 不是 B/D；§k.3 只解出方矩 16672/圆 16640）'
                       % str(spec)[:1])
    if missing:
        return None
    body = ['0'] * _K303_BODY_LEN
    body[0] = _fmt(d.get('family') or _K303_FAMILY)          # split 1 = 族码 77
    for i, v in enumerate(_pack_spec_str(str(spec))):        # split 2..7 = 打包串
        body[1 + i] = str(v)
    body[_K303_SLOT_D - 1] = _fmt(dv)                        # split 18
    body[_K303_SLOT_D2 - 1] = _fmt(dv)                       # split 20（矩形管未观测 ⇒ 沿用 d）
    body[_K303_SLOT_LIB - 1] = _fmt(lib)                     # split 27
    body[_K303_SLOT_MAT - 1] = _fmt(mat)                     # split 30
    body[_K303_SLOT_SHAPE - 1] = str(shape)                  # split 32
    return ','.join(body)


def _shapeval_body(sec: Section, missing: List[str]) -> Optional[str]:
    """把 ``Section`` 反算成 ShapeVal 的**参数体**（不含 Kind 与尾部 Mat/ID）。

    不可能无损反算时**不猜**：把缺的槽位填进 ``missing`` 并返回 ``None``。
    """
    kind = int(sec.kind or 0)
    d = dict(sec.dims or {})
    p = list(sec.params or [])

    def need(*keys: str) -> bool:
        lack = [k for k in keys if d.get(k) is None]
        missing.extend(lack)
        return not lack

    if kind == 1:
        if need('B', 'H'):
            return ','.join([_fmt(d['B']), _fmt(d['H'])])
        if len(p) >= 2:
            return ','.join(p[:2])
        return None

    if kind == 3:
        if need('d'):
            return _fmt(d['d'])
        if p:
            return p[0]
        return None

    if kind == 2:
        # Kind=2（焊接 H）的处置（与 §k.3 的字面「不可生成」有出入，理由写在模块文档里）：
        #   * 契约 §l.6 明令「v1 的 write_jwd 不动」，而 v1 对 Kind=2 是**从 dims 槽位键编码**
        #     （dims 键 = §a.4 解码出的槽位 ⇒ 编码就是解码的逆；样本 2/2 行逐字复现）；
        #   * db2jwd 方向根本没有族映射到 Kind=2（§l.6 的族→Kind 表）⇒ 不会从这里请求；
        #   * 只有 dims 槽位键不全、且没有原文可搬运时才拒绝并报告（不猜）。
        keys = ('Tw', 'H', 'B1', 'T1', 'B2', 'T2')
        if need(*keys):
            return ','.join(_fmt(d[k]) for k in keys)
        if len(p) >= 6:
            return ','.join(p[:6])
        return None

    if kind == 26:
        # 样本形状：26, 族码, 子类型, H, 0, B, tf, tw, 0, Mat, ID,
        # （字段 4/8 恒 0 —— jwd_format.md §3.2 的字段布局表）
        keys = ('family', 'subtype', 'H', 'B', 'tf', 'tw')
        if not p and d.get('family') is not None and int(d['family']) != 39:
            # §k.3：只有族码 39 的 6 尺寸槽顺序已知 ⇒ 无原文时不得构造其它族
            missing.append('族码 %s 的 6 尺寸槽顺序未知（§k.3 / §12#19）⇒ 无原文时不可构造'
                           % d['family'])
            return None
        if d.get('subtype') is None and d.get('family') is not None:
            d = dict(d)
            d['subtype'] = _K26_SUBTYPE_DEFAULT      # §l.6：族码 39 → subtype=1
        if need(*keys):
            return ','.join([_fmt(d['family']), _fmt(d['subtype']), _fmt(d['H']), '0',
                             _fmt(d['B']), _fmt(d['tf']), _fmt(d['tw']), '0'])
        if len(p) >= 8:
            return ','.join(p[:8])
        return None

    if kind == 303:
        # 两条路（先原文、后构造）：
        # ① 有 params 原文（来自 .jwd）⇒ 以原文为底改写已解槽 —— 槽 33..81 全 0 的块只有原文能带出来；
        # ② 无原文（db2jwd 构造）⇒ 按 R2 §k.3 的模板从 dims 造（槽 32 形状码由规格串首字符定）。
        # 两条路共用的前置检查：规格串必须放得进 6 个打包槽（12 字符），否则拒绝编码（不截断）。
        if d.get('spec_str') is not None:
            err = _spec_str_capacity_error(str(d['spec_str']))
            if err:
                missing.append(err)
                return None
        if len(p) >= _K303_SPLIT_LEN - 4:            # 至少覆盖到槽 32（body 下标 31）
            out = list(p)
            if d.get('family') is not None:
                out[0] = _fmt(d['family'])
            elif not out[0]:
                missing.append('family')
            if d.get('spec_str'):
                for i, v in enumerate(_pack_spec_str(str(d['spec_str']))):
                    out[1 + i] = str(v)
            elif not any(out[1:7]):
                missing.append('spec_str（params[1..6] 打包规格串）')
            for idx, key in ((17, 'd'), (19, 'b')):
                if d.get(key) is not None:
                    out[idx] = _fmt(d[key])
                elif not out[idx]:
                    missing.append(key)
            if d.get('lib_family') is not None:
                out[26] = _fmt(d['lib_family'])
            elif not out[26]:
                missing.append('lib_family')
            if sec.mat:
                out[29] = _fmt(sec.mat)
            if missing:
                return None
            return ','.join(out)
        return _shapeval_303_from_dims(d, int(sec.mat or 0), int(sec.id or 0), missing)

    if p:                      # 未知 Kind 但留了原文 ⇒ 原样搬运（不解释）
        return ','.join(p)
    missing.append('Kind=%s 无参数体可反算（§k.3 的模板只覆盖 1/3/26(族39)/303）' % (sec.kind,))
    return None


def shapeval_for(section: Section) -> Tuple[str, List[str]]:
    """由 ``Section`` 反算 ShapeVal 文本（契约 §a.4 的逆运算）。

    返回 ``(shapeval, missing)``：``missing`` 非空 ⇒ 有槽位缺证据，``shapeval`` 返回 ``''``
    —— **不写半真半假的截面定义**，由调用方落报告（契约 §0.1【未知】的处置）。
    """
    missing: List[str] = []
    kind = int(section.kind or 0)
    if kind not in (1, 2, 3, 26, 303):
        missing.append('Kind=%s 不在已解码族 {1,2,3,26,303}（jwd_format.md §3.2）' % (section.kind,))
        return '', missing
    body = _shapeval_body(section, missing)
    if body is None or missing:
        return '', missing
    mat_field = -1 if kind == 303 else int(section.mat)
    return '%d,%s,%d,%d,' % (kind, body, mat_field, int(section.id)), []


# ---------------------------------------------------------------------------
# 插入器
# ---------------------------------------------------------------------------
class _Writer:
    """极薄的插入器：``_GbkBytes`` 值自动用 ``CAST(? AS TEXT)`` 占位。"""

    def __init__(self, con: sqlite3.Connection):
        self.con = con
        self.counts: Dict[str, int] = {t: 0 for t in TABLE_NAMES}

    def add(self, table: str, cols: Sequence[str], rows: Sequence[Sequence[Any]]) -> int:
        rows = [r for r in rows if r is not None]
        if not rows:
            return 0
        ph, params = [], []
        for r in rows:
            one = []
            for v in r:
                if isinstance(v, _GbkBytes):
                    one.append('CAST(? AS TEXT)')
                    params.append(v.data)
                else:
                    one.append('?')
                    params.append(v)
            ph.append('(%s)' % ','.join(one))
        self.con.execute('INSERT INTO %s (%s) VALUES %s'
                         % (table, ','.join(cols), ','.join(ph)), params)
        self.counts[table] = self.counts.get(table, 0) + len(rows)
        return len(rows)


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------
def _num_no(v: Any) -> Optional[int]:
    try:
        i = int(v)
    except (TypeError, ValueError):
        return None
    return i if i > 0 else None


def write_jwd(model: Model, path: str) -> Dict[str, Any]:
    """把 ``Model`` 写成合法 ``.jwd``（SQLite3），返回契约 §b.3 规定的 ``dict``。

    ① 建 46 表 + 79 索引（DDL 逐字取自 ``00_schema.txt``；先 ``PRAGMA encoding='UTF-8'``）；
    ② 按父→子的顺序插行，缺父表时按 §b.3 的合成规则补齐（楼层 / 节点 / 轴网 / 材料属性）；
    ③ 先写同目录临时文件、再 ``os.replace`` 到 ``path``（**不删除**任何别的文件）。
    """
    if not isinstance(model, Model):
        raise TypeError('write_jwd: 需要 canonical.Model，收到 %r' % type(model))
    path = os.path.abspath(path)
    out_dir = os.path.dirname(path) or '.'
    if not os.path.isdir(out_dir):
        raise IOError('输出目录不存在：%s' % out_dir)

    warnings: List[str] = []
    skipped: List[Dict[str, Any]] = []
    once: Dict[str, bool] = {}

    _check_unique('Joint', list(model.joints))
    _check_unique('Section', list(model.sections))
    _check_unique('Member', [m.id for m in model.members])
    _check_unique('Slab', [s.id for s in model.slabs])
    _check_unique('Wall', [w.id for w in model.walls])
    _check_unique('Load', [l.id for l in model.loads])

    fl = _build_floors(model, warnings)
    if not fl.floors:
        warnings.append('模型没有任何楼层：pkpmStdFlr/pkpmFloor 写 0 行，'
                        '构件/节点/板无法归属（契约 §b.3 的合成规则需要至少一个标高）')

    fd, tmp = tempfile.mkstemp(prefix=os.path.basename(path) + '.',
                               suffix='.tmp', dir=out_dir)
    os.close(fd)
    con = sqlite3.connect(tmp)
    w = _Writer(con)
    try:
        con.execute("PRAGMA encoding='UTF-8'")
        by_name = {re.match(r'CREATE TABLE\s+(\w+)', s).group(1): s for s in _DDL_TABLES}
        for name in list(WRITE_ORDER) + [t for t in TABLE_NAMES if t not in WRITE_ORDER]:
            con.execute(by_name[name])
        for stmt in _DDL_INDEXES:
            con.execute(stmt)

        # -------------------- 1. pkpmStdFlr / pkpmFloor --------------------
        w.add('pkpmStdFlr', ('ID', 'No_', 'Height'),
              [(int(f.stdflr_id), int(f.no), 0) for f in fl.floors])
        w.add('pkpmFloor', ('ID', 'No_', 'Name', 'StdFlrID', 'LevelB', 'Height'),
              [(int(f.floor_id or f.stdflr_id), int(f.no), _txt(f.name),
                int(f.stdflr_id), float(f.z_bot), float(f.z_top - f.z_bot))
               for f in fl.floors])
        if fl.floors and not fl.merged:
            warnings.append('pkpmStdFlr.Height 按样本写 0（该列在样本恒 0；'
                            '标高一律由 pkpmFloor.LevelB/Height 表达，'
                            'jwd_format.md §4.3 明令不得用 StdFlr.Height）')

        # -------------------- 2. pkpmJoint --------------------
        jrows, jfloor, jnopool = [], {}, []
        for key in sorted(model.joints):
            j = model.joints[key]
            f, why = fl.for_joint(j.level, j.z)
            if f is None:
                skipped.append({'what': 'joint', 'id': int(j.id),
                                'why': '模型没有楼层，节点无法归属'})
                continue
            if why and not once.get('joint-fb'):
                warnings.append('节点层归属回退（只报第一次）：%s' % why)
                once['joint-fb'] = True
            jfloor[int(j.id)] = f.stdflr_id
            no = _num_no(j.no)
            if no is None:
                jnopool.append(int(j.id))
            jrows.append([int(j.id), no, int(f.stdflr_id), float(j.x), float(j.y),
                          _zdelta(j.z, f.z_top)])
        # 未编号的模型节点：按层内 (y, x) 升序 1..n 补号（契约 §b.3 的节点编号规则）
        for i, jid in enumerate(sorted(jnopool, key=lambda k: (model.joints[k].y,
                                                               model.joints[k].x, k)), 1):
            for r in jrows:
                if r[0] == jid:
                    r[1] = i
        w.add('pkpmJoint', ('ID', 'No_', 'StdFlrID', 'X', 'Y', 'HDiff'), jrows)

        # 节点索引：两个域，取决于模型来源（见 _FloorSet.direct）
        #   * 楼层型（.jwd）：节点是**楼层平面**上的点，柱底节点与楼层平面同 (x, y) 但不同 z
        #     ⇒ 按 (层键, x, y) 匹配（jwd_format.md §4.3：平面画在层顶）
        #   * 平面型（.pdt/.pdmsdump）：节点是三维点 ⇒ 按 (x, y, z) 精确匹配
        jidx: Dict[Tuple[int, int, int], int] = {}
        jidx3: Dict[Tuple[int, int, int], int] = {}
        jlocal: Dict[Tuple[int, int], List[Tuple[int, float]]] = {}
        for k in sorted(jfloor):
            j = model.joints[k]
            kx, ky = round(j.x, 3), round(j.y, 3)
            jidx[(jfloor[k], kx, ky)] = k
            jidx3[(kx, ky, round(j.z, 3))] = k
            jlocal.setdefault((kx, ky), []).append((k, float(j.z)))
        synth: List[Tuple[int, int, float, float, float, float]] = []  # (层键, ID, x, y, z, z_top)

        def next_joint_id() -> int:
            taken = set(jfloor) | {s[1] for s in synth}
            return (max(taken) + 1) if taken else 1

        def need_joint(m: Member, floor: Level, which: str) -> Optional[int]:
            """构件端点的节点：先在已有节点里找，找不到就合成一个（外键必须可解析）。"""
            e = tuple(float(v) for v in (m.ecc or ()))
            p = m.start if which == 'start' else m.end
            x, y = float(p[0]), float(p[1])
            if m.type == 'column' and len(e) >= 2:
                x, y = x - e[0], y - e[1]
            elif m.type == 'brace' and len(e) >= 4:
                x, y = (x - e[0], y - e[1]) if which == 'start' else (x - e[2], y - e[3])
            z = float(p[2])
            k2 = (round(x, 3), round(y, 3))
            k3 = (k2[0], k2[1], round(z, 3))
            hit = None
            if fl.direct:
                hit = jidx.get((floor.stdflr_id, k2[0], k2[1]))
                if hit is None:
                    cand = jlocal.get(k2) or []
                    same = [c for c in cand if abs(c[1] - z) <= TOL]
                    pick = same[0] if same else (cand[0] if len(cand) == 1 else None)
                    if pick is not None:
                        if not once.get('joint-x'):
                            warnings.append('构件端点 (%g, %g, %g) 在本层找不到节点，'
                                            '按同坐标节点 %s 兜底（只报第一次）'
                                            % (x, y, z, pick[0]))
                            once['joint-x'] = True
                        hit = pick[0]
            else:
                hit = jidx3.get(k3)
            if hit is not None:
                return hit
            jid = next_joint_id()
            synth.append((floor.stdflr_id, jid, x, y, z, floor.z_top))
            jidx[(floor.stdflr_id, k2[0], k2[1])] = jid
            jidx3[k3] = jid
            jlocal.setdefault(k2, []).append((jid, z))
            return jid

        # -------------------- 3. 构件（一次遍历，段行 / 轴网行一起算）--------------------
        seg: Dict[str, List[Sequence[Any]]] = {t: [] for t in _SEG_TABLE}
        grid_rows: List[Sequence[Any]] = []
        axis_rows: List[Sequence[Any]] = []
        mfloor: Dict[int, int] = {}
        nouse: Dict[Tuple[str, int], int] = {}
        gno: Dict[int, int] = {}
        ano: Dict[int, int] = {}
        used_grid = set()
        next_grid = max([int(m.grid_id) for m in model.members
                         if m.type == 'beam' and m.grid_id] or [0]) + 1
        next_axis = 1
        for m in model.members:
            if m.type not in _SEG_TABLE:
                skipped.append({'what': 'member', 'id': int(m.id),
                                'why': "type=%r 不是 beam/column/brace（契约 §a.2）" % (m.type,)})
                continue
            L = [l for l in model.levels if l.stdflr_id == m.level]
            if not L:
                skipped.append({'what': 'member', 'id': int(m.id),
                                'why': 'level=%s 不可解析（契约 §a.7 的 E-MEM-LEVEL）' % (m.level,)})
                continue
            f, why = fl.for_member_obj(m.level, m.type, L[0].z_bot)
            if f is None:
                skipped.append({'what': 'member', 'id': int(m.id), 'why': '模型没有楼层'})
                continue
            if why and not once.get('mem-fb-%s' % m.type):
                warnings.append('%s 构件层归属回退（只报第一次）：%s' % (m.type, why))
                once['mem-fb-%s' % m.type] = True
            if m.section not in model.sections:
                skipped.append({'what': 'member', 'id': int(m.id),
                                'why': 'section=%s 不可解析（契约 §a.7 的 E-MEM-SEC）'
                                       % (m.section,)})
                continue
            mfloor[int(m.id)] = f.stdflr_id
            e = tuple(float(v) for v in (m.ecc or ()))
            no = _num_no(m.no)
            if no is None:
                nouse[(m.type, f.stdflr_id)] = nouse.get((m.type, f.stdflr_id), 0) + 1
                no = nouse[(m.type, f.stdflr_id)]

            if m.type == 'column':
                # 优先沿用模型自带的 pkpmColSeg.JtID（契约 §a.2 的 node_id）——那是原始外键，
                # 比按 (层, x, y) 反查更保真；不可解析时才回退到坐标匹配。
                jt = int(m.node_id) if (m.node_id is not None
                                        and int(m.node_id) in model.joints) else None
                if jt is None:
                    jt = need_joint(m, f, 'start')
                seg['column'].append((
                    int(m.id), no, int(f.stdflr_id), int(m.section), jt,
                    e[0] if len(e) >= 1 else 0, e[1] if len(e) >= 2 else 0,
                    float(m.rotation), _zdelta(m.start[2], f.z_bot), 0, '', '', ''))
            elif m.type == 'brace':
                seg['brace'].append((
                    int(m.id), no, int(f.stdflr_id), int(m.section),
                    need_joint(m, f, 'start'), need_joint(m, f, 'end'),
                    e[0] if len(e) >= 1 else 0, e[1] if len(e) >= 2 else 0,
                    _zdelta(m.start[2], f.z_top),
                    e[2] if len(e) >= 3 else 0, e[3] if len(e) >= 4 else 0,
                    _zdelta(m.end[2], f.z_top), float(m.rotation)))
            else:                                   # beam → 需要一行 pkpmGrid + pkpmAxis
                gid = int(m.grid_id) if m.grid_id else next_grid
                if gid in used_grid:
                    warnings.append('梁 %s 的 GridID=%s 与另一根梁重复，已改用新 ID %s'
                                    '（pkpmGrid.ID 是主键）' % (m.id, m.grid_id, next_grid))
                    gid = next_grid
                used_grid.add(gid)
                next_grid = max(next_grid, gid) + 1
                ax = next_axis
                next_axis += 1
                gno[f.stdflr_id] = gno.get(f.stdflr_id, 0) + 1
                ano[f.stdflr_id] = ano.get(f.stdflr_id, 0) + 1
                axis_rows.append((ax, ano[f.stdflr_id], int(f.stdflr_id),
                                  need_joint(m, f, 'start'), need_joint(m, f, 'end'), ''))
                grid_rows.append((gid, gno[f.stdflr_id], int(f.stdflr_id),
                                  need_joint(m, f, 'start'), need_joint(m, f, 'end'), ax))
                seg['beam'].append((
                    int(m.id), no, int(f.stdflr_id), int(m.section), gid,
                    e[0] if len(e) >= 1 else 0,
                    _zdelta(m.start[2], f.z_top), _zdelta(m.end[2], f.z_top),
                    float(m.rotation), _txt(m.jydef)))

        # 合成节点：写进 pkpmJoint（No_ 按层内 (y, x) 升序 1..n，契约 §b.3）
        if synth:
            per: Dict[int, List[Tuple[int, float, float, float, float]]] = {}
            for (fk, jid, x, y, z, ztop) in synth:
                per.setdefault(fk, []).append((jid, x, y, z, ztop))
            rows = []
            for fk in sorted(per):
                items = sorted(per[fk], key=lambda t: (t[2], t[1], t[0]))
                for i, (jid, x, y, z, ztop) in enumerate(items, 1):
                    rows.append((int(jid), i, int(fk), float(x), float(y),
                                 _zdelta(z, ztop)))
            w.add('pkpmJoint', ('ID', 'No_', 'StdFlrID', 'X', 'Y', 'HDiff'), rows)
            warnings.append('由构件端点合成了 %d 个节点（模型未提供或未覆盖该 (层, x, y)）；'
                            'No_ 按层内 (y, x) 升序编号（契约 §b.3 的 pkpmJoint 合成规则）'
                            % len(rows))

        w.add('pkpmAxis', ('ID', 'No_', 'StdFlrID', 'Jt1ID', 'Jt2ID', 'Name'), axis_rows)
        w.add('pkpmGrid', ('ID', 'No_', 'StdFlrID', 'Jt1ID', 'Jt2ID', 'AxisID'), grid_rows)
        if grid_rows:
            warnings.append('pkpmGrid/pkpmAxis 为**合成**结果：每根梁一行'
                            '（GridID 尽量沿用模型的 pkpmBeamSeg.GridID）；'
                            '轴线/轴网的分组编号与原 JWD 可能不同（契约 §b.3、§12#13），'
                            '几何不受影响')

        # -------------------- 4. 截面 --------------------
        usage: Dict[int, List[str]] = {}
        for m in model.members:
            if m.type in _TYPE_SECT:
                usage.setdefault(int(m.section), []).append(_TYPE_SECT[m.type])
        wall_only = set(int(wl.section) for wl in model.walls if wl.section >= 0)
        srows: Dict[str, List[Sequence[Any]]] = {t: [] for t in _SECT_TABLE.values()}
        sno: Dict[str, int] = {}
        written = set()
        for sid in sorted(model.sections):
            s = model.sections[sid]
            tbl = _SECT_TABLE.get(s.table)
            if tbl is None:
                cand = sorted(set(usage.get(int(sid)) or []))
                if not cand:
                    why = ('Section.table=%r 且未被任何构件引用，无法判断该写进三张截面表的'
                           '哪一张（jwd_format.md §9.2#9：未使用截面可丢弃，但需保留 ID 映射）'
                           % (s.table,))
                    if int(sid) in wall_only:
                        why += '；该截面只被墙引用，而墙本身不写进 .jwd（契约 §a.8）'
                    skipped.append({'what': 'section', 'id': int(sid), 'why': why})
                    continue
                tbl = cand[0]
                if len(cand) > 1:
                    warnings.append('Section %s 被多种构件类型引用 %s，按 %s 写入'
                                    '（.jwd 只有三张截面表）' % (sid, cand, tbl))
            sv, missing = shapeval_for(s)
            if missing:
                warnings.append('Section %s(%s, Kind=%s) 的 ShapeVal 无法完整反算：缺 %s '
                                '—— 该行写空 ShapeVal（ID/No_/Name/Kind/Mat 仍写全，'
                                '截面可按名或按 dims 再解析；不写半真半假的定义）'
                                % (sid, s.name or '(无名)', s.kind,
                                   '、'.join(sorted(set(missing)))))
            no = _num_no(s.no)
            if no is None:
                sno[tbl] = sno.get(tbl, 0) + 1
                no = sno[tbl]
            srows[tbl].append((int(sid), no, _GbkBytes(s.name or ''), int(s.mat),
                               int(s.kind), _txt(sv)))
            written.add(int(sid))
        for tbl in ('pkpmBeamSect', 'pkpmColSect', 'pkpmBraceSect'):
            w.add(tbl, ('ID', 'No_', 'Name', 'Mat', 'Kind', 'ShapeVal'), srows[tbl])
        unwritten = [int(k) for k in sorted(model.sections) if int(k) not in written]
        if unwritten:
            warnings.append('下列截面未写进任何 pkpm*Sect 表：%s（见 skipped 的原因）'
                            % unwritten)

        # -------------------- 5. 段表 --------------------
        w.add('pkpmColSeg',
              ('ID', 'No_', 'StdFlrID', 'SectID', 'JtID', 'EccX', 'EccY', 'Rotation',
               'HDiffB', 'ColcapId', 'Cut_Col', 'Cut_Cap', 'Cut_Slab'), seg['column'])
        w.add('pkpmBeamSeg',
              ('ID', 'No_', 'StdFlrID', 'SectID', 'GridID', 'Ecc', 'HDiff1', 'HDiff2',
               'Rotation', 'JYDef'), seg['beam'])
        w.add('pkpmBraceSeg',
              ('ID', 'No_', 'StdFlrID', 'SectID', 'Jt1ID', 'Jt2ID', 'EccX1', 'EccY1',
               'HDiff1', 'EccX2', 'EccY2', 'HDiff2', 'Rotation'), seg['brace'])
        constant_cols = ('pkpmColSeg.ColcapId/Cut_Col/Cut_Cap/Cut_Slab 写样本常量 '
                         "0/''/''/''（jwd_format.md §1.8 逐列实测，规范模型不承载）")
        if seg['column']:
            warnings.append(constant_cols)
        if seg['beam']:
            warnings.append('pkpmBeamSeg.Ecc 写模型记录值；偏心正负方向语义未证实'
                            '（jwd_format.md §9.3#6）—— 非零偏心须人工复核')

        # -------------------- 6. 板 + 板洞 --------------------
        slab_rows: List[Sequence[Any]] = []
        hole_rows: List[Sequence[Any]] = []
        slab_cols = ['ID', 'No_', 'StdFlrID', 'GridsID', 'VertexX', 'VertexY', 'VertexZ',
                     'RoomIsHole', 'Thickness', 'dead', 'live', 'nEdge', 'xc', 'yc']
        slab_cols += list(_SLAB_DEFAULTS)
        slab_defaults = [_SLAB_DEFAULTS[k] for k in _SLAB_DEFAULTS]
        s_no: Dict[int, int] = {}
        hole_id = 0
        for s in model.slabs:
            if len(s.polygon) < 3:
                skipped.append({'what': 'slab', 'id': int(s.id),
                                'why': '多边形顶点数 %d < 3（契约 §a.7 的 E-SLAB-POLY）'
                                       % len(s.polygon)})
                continue
            f, why = fl.for_slab(s.level, s.z)
            if f is None:
                skipped.append({'what': 'slab', 'id': int(s.id), 'why': '模型没有楼层'})
                continue
            if why and not once.get('slab-fb'):
                warnings.append('板层归属回退（只报第一次）：%s' % why)
                once['slab-fb'] = True
            xs = [float(p[0]) for p in s.polygon]
            ys = [float(p[1]) for p in s.polygon]
            no = _num_no(s.no)
            if no is None:
                s_no[f.stdflr_id] = s_no.get(f.stdflr_id, 0) + 1
                no = s_no[f.stdflr_id]
            row = [int(s.id), no, int(f.stdflr_id), _txt(_csv_int(s.grid_edges)),
                   _txt(_csv2(xs)), _txt(_csv2(ys)),
                   _txt(_csv2([_zdelta(s.z, f.z_bot)] * len(xs))),
                   1 if s.is_hole else 0, float(s.thickness), float(s.dead),
                   float(s.live), len(xs), (min(xs) + max(xs)) / 2.0,
                   (min(ys) + max(ys)) / 2.0] + list(slab_defaults)
            slab_rows.append(tuple(row))
            if s.is_hole:
                hole_id += 1
                hole_rows.append((hole_id, no, int(f.stdflr_id), None, None,
                                  int(s.id), 0, 0, 0.0))
        w.add('pkpmSlab', slab_cols, slab_rows)
        w.add('pkpmSlabHole', ('ID', 'No_', 'StdFlrID', 'SectID', 'JtID', 'SlabID',
                               'EccX', 'EccY', 'Rotation'), hole_rows)
        if slab_rows:
            if hole_rows:
                warnings.append('pkpmSlabHole 为按 RoomIsHole=1 合成的索引行（ID 重新分配：'
                                '样本 63830..63882 无法从规范模型还原；洞的几何仍在'
                                ' pkpmSlab 行里，jwd_format.md §1.4）')
            warnings.append('pkpmSlab 的 %s 列写 NULL（规范模型不承载、样本逐行取值不同）；'
                            '另 %d 个未启用列按样本全表同值常量写入，'
                            'nEdge/VertexZ/xc/yc 按公式算（本次样本 222/222 校验通过）'
                            % ('/'.join(_SLAB_UNKNOWN_COLS), len(_SLAB_DEFAULTS)))

        # -------------------- 7. 荷载 --------------------
        ls_rows: List[Sequence[Any]] = []
        lg_rows: List[Sequence[Any]] = []
        sval: Dict[int, Tuple[int, str]] = {}
        load_sid: Dict[int, int] = {}
        fresh = max([int(l.load_sect_id) for l in model.loads
                     if int(l.load_sect_id or 0) > 0] or [0]) + 1
        for l in sorted(model.loads, key=lambda x: int(x.id)):
            if l.kind not in _LOAD_ELEMENT_KIND:
                skipped.append({'what': 'load', 'id': int(l.id),
                                'why': "kind=%r 不在 {'beam-line','joint-point'}（契约 §a.2）"
                                       % (l.kind,)})
                continue
            sid = int(l.load_sect_id or 0)
            if sid <= 0:
                while fresh in sval:
                    fresh += 1
                sid = fresh
                fresh += 1
                warnings.append('Load %s 的 load_sect_id=%s 不可用，已分配占位荷载截面 '
                                'ID=%s（保证 pkpmLoadSeg.SectID 外键可解析）'
                                % (l.id, l.load_sect_id, sid))
            raw = [str(t) for t in (l.raw or [])]
            if not raw:
                raw = ['' if v is None else '%.2f' % float(v) for v in (l.values or ())]
            sv = (','.join(raw) + ',') if raw else ''
            ek = _LOAD_ELEMENT_KIND[l.kind]
            if sid in sval and sval[sid][0] != ek:
                warnings.append('荷载截面 %s 同时被 %s 与 %s 使用，按 %s 写 ElementKind'
                                % (sid, sval[sid][0], ek, sval[sid][0]))
            else:
                sval.setdefault(sid, (ek, sv))
            load_sid[int(l.id)] = sid
        for i, sid in enumerate(sorted(sval), 1):
            ek, sv = sval[sid]
            ls_rows.append((int(sid), i, '', ek, _txt(sv)))
        for i, l in enumerate(sorted(model.loads, key=lambda x: int(x.id)), 1):
            if int(l.id) not in load_sid:
                continue
            lg_rows.append((int(l.id), i, load_sid[int(l.id)], 1, int(l.target_id),
                            '0.00,0.00,0.00,0.00,0.00', 0, '', '', '', 0))
        w.add('pkpmLoadSect', ('ID', 'No', 'Loadname', 'ElementKind', 'ShapeVal'), ls_rows)
        w.add('pkpmLoadSeg',
              ('ID', 'No', 'SectID', 'Type', 'ElementID', 'strParas1', 'nPtCnt',
               'strParasX', 'strParasY', 'strParasZ', 'StdFlrID'), lg_rows)
        if lg_rows:
            warnings.append("pkpmLoadSeg 的 Type 写样本唯一值 1、strParas1 写样本常量 "
                            "'0.00,0.00,0.00,0.00,0.00'、strParasX/Y/Z 写空串、StdFlrID 写 0"
                            '（jwd_format.md §1.6 逐列实测；这些列未承载于规范模型）')
            warnings.append("pkpmLoadSect.Loadname 写空串（规范模型不承载荷载名，样本取值为 "
                            "'' 或 '无'）；荷载数值语义（类型码 1/2/3 与单位）未证实，"
                            '仅原样搬运（jwd_format.md §1.6 / §9.3#8）')

        # -------------------- 8. pkpmProperty：材料等级 --------------------
        prop_rows: List[Sequence[Any]] = []
        for m in model.members:
            mat = (m.material or '').strip()
            if not mat:
                continue
            mo = re.match(r'^([CQcq])\s*([0-9]+(?:\.[0-9]+)?)$', mat)
            if not mo:
                skipped.append({'what': 'property', 'id': int(m.id),
                                'why': "Member.material=%r 不是 'C<强度>'/'Q<牌号>' 形式"
                                       '（契约 §b.2 的 HNTDJ/GANGH 映射）' % (mat,)})
                continue
            val = float(mo.group(2))
            if val <= 0:                       # 契约 §b.2：值 ≤ 0（未指定）时不填
                continue
            prop_rows.append((int(m.id), 'HNTDJ' if mo.group(1).upper() == 'C' else 'GANGH',
                              5, '%.2f' % val))
        w.add('pkpmProperty', ('ID', 'Name', 'Type', 'ShapeVal'), prop_rows)
        if prop_rows:
            warnings.append('pkpmProperty 只写构件材料等级（HNTDJ/GANGH，契约 §b.3）；'
                            '样本另有 Sp*/roomrf/support/DXF 等设计属性'
                            '（3574 行里的 2541 行）未承载于规范模型，未写')

        # -------------------- 9. 未写出的对象 --------------------
        for wl in model.walls:
            skipped.append({'what': 'wall', 'id': int(wl.id),
                            'why': 'pkpmWallSeg 语义未解码（jwd_format.md §1.7）：'
                                   '规范模型的墙不写进 .jwd（契约 §a.8/§b.3）'})
        warnings.append('pkpmSysInfo / pkpmStdFlrPara 建表但 0 行：规范模型不承载工程名'
                        '（样本 pkpmSysInfo.ID=2 = "JLCJ2"）与每标准层 26 项设计参数'
                        '（jwd_format.md §7.2/§7.3）——读回后 CLI 的 --project 需另行给出')
        con.commit()
    finally:
        con.close()

    try:
        os.replace(tmp, path)
    except OSError as exc:
        raise IOError('无法写出 %s（临时文件保留在 %s，未删任何文件）：%s' % (path, tmp, exc))

    counts = model.counts()
    return {
        'tables': dict(w.counts),
        'rows': sum(w.counts.values()),
        'members': dict(counts['members']),
        'slabs': int(counts['slabs']),
        'walls': int(counts['walls']),
        'loads': int(counts['loads_total']),
        'skipped': skipped,
        'warnings': warnings,
    }


# ---------------------------------------------------------------------------
# R2 §l.6：db2jwd 的落点 —— 只写截面定义的 .jwd
# ---------------------------------------------------------------------------
#: ``sections`` 字典的键 → JWD 截面表（契约 §l.6 的 `{"beam":…,"col":…,"brace":…}`）
_SECT_KEYS = (('beam', 'pkpmBeamSect'), ('col', 'pkpmColSect'), ('brace', 'pkpmBraceSect'))

#: `Mat` 只允许 5=钢 / 6=混凝土（jwd_format.md §1.5）；其它值按 §k.3/§12#17 的规则写 5 并记报告
_MAT_STEEL, _MAT_CONCRETE = 5, 6


def _as_section(x: Any) -> Section:
    """把 ``Section`` 或等价 dict 归一成 canonical ``Section``（§k.1 的 SectionRec → Section）。

    §l.6 的 `sections` 由 ``sectionlib.SectionTable.to_jwd_sections()`` 产出（canonical 对象）；
    这里也接受 dict，便于 CLI/数据库方向直接传记录字典。
    """
    if isinstance(x, Section):
        return x
    if isinstance(x, dict):
        d = dict(x)
        return Section(id=int(d.get('id', 0) or 0), kind=int(d.get('kind', 0) or 0),
                       mat=int(d.get('mat', 0) or 0), name=str(d.get('name', '') or ''),
                       dims=dict(d.get('dims') or {}), table=str(d.get('table', '') or ''),
                       no=int(d.get('no', 0) or 0), shapeval=str(d.get('shapeval', '') or ''),
                       params=[str(t) for t in (d.get('params') or [])],
                       note=str(d.get('note', '') or ''))
    raise TypeError('write_jwd_sections: 期望 canonical.Section 或 dict，收到 %r' % type(x))


def _reid_shapeval(sv: str, sid: int) -> Tuple[str, bool]:
    """把 ShapeVal 的**末字段（本行 ID）**改成 ``sid``（契约 §a.4：末字段恒 == 本行 ID）。

    只在调用方给的 ShapeVal 自带的 ID 与要写的行 ID 不同时才动，其余**逐字保留**。
    """
    toks = sv.split(',')
    while toks and toks[-1] == '':
        toks.pop()
    if len(toks) < 2:
        return sv, False
    if toks[-1] == str(int(sid)):
        return sv, False
    toks[-1] = str(int(sid))
    return ','.join(toks) + ',', True


def write_jwd_sections(sections: Dict[str, Any], path: str,
                       opts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """**R2 §l.6 的 `db2jwd` 落点**：把截面定义写成 ``.jwd``（46 张表全建，只填三张截面表）。

    :param sections: ``{"beam":[…], "col":[…], "brace":[…]}`，元素是 canonical
        :class:`~canonical.Section`（由 ``sectionlib.SectionTable.to_jwd_sections()`` 产出）
        或等价 dict。三个键都可缺省/为空；其它键记 warning 后忽略。
    :param path: 输出 ``.jwd`` 路径。**本函数只写 ``path``**（同目录临时文件 + ``os.replace``），
        不删/不改任何别的文件；是否覆盖已有文件由调用方决定（CLI 的 ``--out``）。
    :param opts: 已知键只有 ``project``（§l.6 括注）：非空时写 ``pkpmSysInfo(ID=2)`` 工程名。
        未知键记 warning（不静默忽略）。
    :returns: 结构同契约 §b.3（8 个键）：``tables`` 是 46 张表的实际插入行数，``rows`` 为合计。

    **行级规则**（验收要的"填充规则"）：

    * ``Kind``  = ``Section.kind``（db2jwd 由 §l.6 的族→Kind 表决定：族 39→26、族 77→303、
      ``/USER_RECT``→1、``/USER_CIRCLE``→3）；
    * ``ShapeVal`` = ① ``Section.shapeval`` 非空 ⇒ 用它（`sectionlib.encode_shapeval` 的结果；
      末字段 ID 与本行不符时只改末字段并记 warning）；② 否则按 §a.4/§k.3 的模板由
      ``Section.dims``/``params`` 反算（本模块 `shapeval_for`）；③ 两者都失败 ⇒ **跳过该行**
      并记 ``skipped``（§k.3：「不得降级成空串」）；
    * ``Name``  = ``Section.name``，按 §b.3 的字节规则以 **GBK 字节**写入 TEXT 列
      （中文名可用，ASCII 名两者等价）；
    * ``Mat``   = ``Section.mat``；∉{5,6}（未知）⇒ 写 5 并记 warning（§k.2 的钢材缺省 + §12#17）；
    * ``No_``   = ``Section.no``（非 0 时）否则按该表内的出现顺序 1..n 编号；``ID`` 用
      ``Section.id``（>0 时），否则按同表内已有最大 ID 递增分配（表内唯一，重复即 ``ValueError``）；
    * **父表引用完整性**：本函数写出的 ``.jwd`` 里，三张截面表没有对外键引用；反过来
      ``ShapeVal`` 的末字段 = 本行 ``ID``（§a.4 的不变式），故用 ``jwd_read`` 读回时
      截面自洽、外键集合为空 = 全部可解析。
    """
    opts = dict(opts or {})
    warnings: List[str] = []
    skipped: List[Dict[str, Any]] = []
    for k in sorted(set(opts) - {'project'}):
        warnings.append('write_jwd_sections: opts 的未知键 %r 被忽略'
                        '（§l.6 只定义了 project）' % k)
    for k in sorted(set(sections) - {key for key, _ in _SECT_KEYS}):
        warnings.append('write_jwd_sections: sections 的未知键 %r 被忽略'
                        '（§l.6 只允许 beam/col/brace）' % k)

    path = os.path.abspath(path)
    out_dir = os.path.dirname(path) or '.'
    if not os.path.isdir(out_dir):
        raise IOError('输出目录不存在：%s' % out_dir)

    # ---- 归一 + 逐表分派（先做校验，避免写出半个库）
    per_table: Dict[str, List[Tuple[int, int, Section, str]]] = {}
    for key, table in _SECT_KEYS:
        per_table[table] = []
        ids: Dict[int, int] = {}
        seq = 0
        for item in (sections.get(key) or []):
            seq += 1
            sec = _as_section(item)
            tgt = _SECT_TABLE.get(sec.table or '')
            if tgt is not None and tgt != table:
                warnings.append('Section %s 的 table=%r 与它在 sections[%r] 里的位置不符，'
                                '按位置写入 %s' % (sec.id, sec.table, key, table))
            sid = int(sec.id or 0)
            if sid in ids:
                raise ValueError('%s 内 Section.ID 重复 %s：.jwd 表内以 ID 为主键'
                                 '（契约 §a.4 的末字段 == 本行 ID 也需要它唯一）' % (table, sid))
            ids[sid] = seq
            per_table[table].append((seq, sid, sec, key))

    fd, tmp = tempfile.mkstemp(prefix=os.path.basename(path) + '.', suffix='.tmp', dir=out_dir)
    os.close(fd)
    con = sqlite3.connect(tmp)
    w = _Writer(con)
    try:
        con.execute("PRAGMA encoding='UTF-8'")
        by_name = {re.match(r'CREATE TABLE\s+(\w+)', s).group(1): s for s in _DDL_TABLES}
        for name in list(WRITE_ORDER) + [t for t in TABLE_NAMES if t not in WRITE_ORDER]:
            con.execute(by_name[name])
        for stmt in _DDL_INDEXES:
            con.execute(stmt)

        for _, table in _SECT_KEYS:
            rows: List[Sequence[Any]] = []
            rows_meta: List[Tuple[int, int, int, int]] = []
            no_seq = 0
            next_id = max([sid for _, sid, _, _ in per_table[table] if sid > 0] or [0]) + 1
            for _seq, sid, sec, key in per_table[table]:
                if sid <= 0:
                    sid = next_id
                    next_id += 1
                # ① Mat：∉{5,6} ⇒ 5 + 报告（§k.2 / §12#17）
                mat = int(sec.mat or 0)
                if mat not in (_MAT_STEEL, _MAT_CONCRETE):
                    warnings.append('Section %s(%s) 的 mat=%s 不在 {5=钢,6=混凝土}，'
                                    '按 §k.2/§12#17 写 5 并在此留痕'
                                    % (sid, sec.name or '(无名)', sec.mat))
                    mat = _MAT_STEEL
                # ② ShapeVal：先原文、后反算；都失败 ⇒ 跳过（§k.3 不得降级成空串）
                sv, missing = '', []
                if (sec.shapeval or '').strip():
                    sv = sec.shapeval.strip()
                    sv, changed = _reid_shapeval(sv, sid)
                    if changed:
                        warnings.append('Section %s 的 ShapeVal 末字段（本行 ID）已按行 ID 改写'
                                        '（§a.4 的不变式）' % sid)
                else:
                    probe = Section(id=sid, kind=sec.kind, mat=mat, name=sec.name,
                                    dims=dict(sec.dims or {}), table=sec.table, no=sec.no,
                                    shapeval='', params=list(sec.params or []), note=sec.note)
                    sv, missing = shapeval_for(probe)
                if not sv:
                    skipped.append({'what': 'section', 'id': sid, 'table': table,
                                    'name': sec.name, 'kind': sec.kind,
                                    'why': 'ShapeVal 无法编码：%s（§k.3 要求不可降级成空串）'
                                           % ('、'.join(sorted(set(missing))) or '无原文且不可构造')})
                    continue
                if int(sec.kind or 0) == 2:
                    warnings.append('Section %s(%s) 是 Kind=2（焊接 H）：§k.3 把该族列为'
                                    '"不可生成"，本次按 §a.4 解码的逆（dims 键 = 槽位）编码'
                                    ' —— B/T 交错序未证实（§12#4），请人工确认'
                                    % (sid, sec.name or '(无名)'))
                # ③ No_：非 0 用原值，否则表内 1..n
                no = int(sec.no or 0)
                if no <= 0:
                    no_seq += 1
                    no = no_seq
                rows.append((sid, no, _GbkBytes(sec.name or ''), mat, int(sec.kind or 0),
                             _txt(sv)))
                rows_meta.append((sid, no, mat, int(sec.kind or 0)))
            w.add(table, ('ID', 'No_', 'Name', 'Mat', 'Kind', 'ShapeVal'), rows)

        # §l.6 的括注：可选写 pkpmSysInfo.ID=2 工程名
        project = opts.get('project')
        if project:
            w.add('pkpmSysInfo', ('ID', 'ParaVal'), [(2, _txt(str(project)))])

        con.commit()
    finally:
        con.close()

    try:
        os.replace(tmp, path)
    except OSError as exc:
        raise IOError('无法写出 %s（临时文件保留在 %s，未删任何文件）：%s' % (path, tmp, exc))

    warnings.append('这是**截面定义文件**：只填 pkpmBeamSect/pkpmColSect/pkpmBraceSect，'
                    '其余 43 张表建而空（几何/节点/轴网/荷载都不在里面，契约 §l.6）')
    if not any(v for k, v in w.counts.items() if k in ('pkpmBeamSect', 'pkpmColSect',
                                                       'pkpmBraceSect')):
        warnings.append('三张截面表都是 0 行：输入的 sections 为空或全部不可编码'
                        '（见 skipped）')
    return {
        'tables': dict(w.counts),
        'rows': sum(w.counts.values()),
        'members': {'beam': 0, 'column': 0, 'brace': 0},
        'slabs': 0,
        'walls': 0,
        'loads': 0,
        'skipped': skipped,
        'warnings': warnings,
    }
