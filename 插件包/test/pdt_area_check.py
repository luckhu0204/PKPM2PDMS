# -*- coding: utf-8 -*-
"""几何交叉核对：板 184706 的环面积应 = 2900×2000 = 5.8 m²（pdt_format.md §9.3#3 实测值）。"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pdt_read import read_pdt                                   # noqa: E402

PDT = r'G:\工作\PDMS相关\00 PDMS插件\02 实用插件\PKPM导入导出插件\1_PM.pdt'
m = read_pdt(PDT)
for sid in (184706, 185006):
    s = [x for x in m.slabs if x.id == sid]
    if not s:
        print('%s 未找到' % sid)
        continue
    s = s[0]
    print('slab %s z=%g t=%g polygon=%s' % (s.id, s.z, s.thickness, s.polygon))
    print('   area=%.1f mm² = %.3f m²  周长=%.0f mm'
          % (s.area, s.area / 1e6, sum(
              ((s.polygon[(i + 1) % len(s.polygon)][0] - s.polygon[i][0]) ** 2 +
               (s.polygon[(i + 1) % len(s.polygon)][1] - s.polygon[i][1]) ** 2) ** 0.5
              for i in range(len(s.polygon)))))
print('第一块板（184706）期望 2900x2000 = 5800000 mm²（pdt_format.md §9.3#3）')
