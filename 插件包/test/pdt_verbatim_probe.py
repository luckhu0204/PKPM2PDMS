# -*- coding: utf-8 -*-
"""探针 ⑧-3：把 1_PM.pdt 里**每一类行的逐字形态**打出来（含行尾空白、缩进、空行结构）。

给 pdt_write 当模板用（契约 §j.4 说模板是从样本逐字抄的；本脚本是那次抄写的复现）。
用法： python test\\pdt_verbatim_probe.py
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PDT = (r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\1_PM.pdt')
txt = open(PDT, 'rb').read().decode('gbk')
L = txt.replace('\r\n', '\n').split('\n')
print('physical lines (split by CRLF) = %d' % (len(L) - 1))

CASES = [
    ('L1   首行注释', 1), ('L2   空行', 2), ('L3   $VERSION 头', 3),
    ('L4   $VERSION 体', 4), ('L5   空行', 5), ('L6   $DESIGNPARA 头', 6),
    ('L7   $DESIGNPARA 首行', 7), ('L57  空行($DESIGNPARA 末)', 57),
    ('L58  $STORY 头', 58), ('L59  $STORY 记录1行1', 59),
    ('L60  $STORY 记录1行2', 60), ('L69  空行', 69),
    ('L70  $NODECOOR 头', 70), ('L71  节点记录行', 71), ('L72  节点 EXR', 72),
    ('L73  空行($NODECOOR 末)', 73 - 0),
    ('L1306 $NET 头', 1306), ('L1307 NET 记录', 1307),
    ('L2366 $DEFFRAMESECTION 头', 2366),
    ('L2367 截面行1', 2367), ('L2368 截面行2', 2368), ('L2369 截面行3', 2369),
    ('L2370 截面行4', 2370), ('L2371 截面 EXI', 2371), ('L2372 下一条截面', 2372),
    ('L2526 $DEFFRAMESECTION 末数据行', 2526), ('L2527 空行', 2527),
    ('L2528 $DEFWASLABSECTION 头', 2528), ('L2529 墙板截面', 2529), ('L2532 末条', 2532),
    ('L2533 空行', 2533), ('L2534 $DEFMATERIAL 头', 2534), ('L2535 材料', 2535),
    ('L2539 末材料', 2539), ('L2540 空行', 2540),
    ('L2541 $SETELEMENT 头', 2541), ('L2542 构件主行', 2542), ('L2543 构件 EXI', 2543),
    ('L2544 构件 EXR 首行', 2544), ('L2545 构件 EXR 续行', 2545),
    ('L2546 下一条构件', 2546),
    ('L6727 空行(?)$', 6727), ('L6728 $SETWALL 头', 6728), ('L6729 墙主行', 6729),
    ('L6730 墙 NUB/NETID', 6730), ('L6731 墙 EXI', 6731), ('L6732 墙 EXR 首行', 6732),
    ('L6733 墙 EXR 续行', 6733), ('L6734 下一条墙', 6734),
    ('L6749 空行', 6749), ('L6750 $SETSLAB 头', 6750), ('L6751 板主行', 6751),
    ('L6752 板 NUB/NETID', 6752), ('L6753 板 EXI', 6753), ('L6754 板 EXR', 6754),
    ('L6755 下一条板', 6755),
    ('L8075 空行', 8075), ('L8076 $RIGID 头', 8076), ('L8077 刚性组行1', 8077),
    ('L8078 SLABID 首行', 8078), ('L8079 SLABID 续行', 8079),
    ('L8083 SLABID 末行', 8083), ('L8084 下一组', 8084),
    ('L8102 $RIGID 末数据', 8102), ('L8103 空行', 8103),
    ('L8104 $DEADLOAD', 8104), ('L8105 $DEFNODELOAD', 8105), ('L8106 首条', 8106),
    ('L8109 末条', 8109), ('L8110 空行', 8110), ('L8111 $SETNODELOAD', 8111),
    ('L8116 空行', 8116), ('L8117 $DEFLINELOAD', 8117), ('L8932 末条', 8932),
    ('L8933 $LIVELOAD', 8933), ('L8934 $DEFLINELOAD', 8934),
    ('L9674 最后数据行', 9674), ('L9675 空行', 9675), ('L9676 空行', 9676),
    ('L9677 $END', 9677), ('L9678 空行(文件末)', 9678),
]
for label, ln in CASES:
    s = L[ln - 1]
    print('%-34s L%-5d len=%-5d %r' % (label, ln, len(s), s[:200]))
print('文件末尾 4 个字符的 bytes = %r' % open(PDT, 'rb').read()[-8:])
