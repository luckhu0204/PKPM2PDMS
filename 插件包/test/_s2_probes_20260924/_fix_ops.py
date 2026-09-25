# -*- coding: utf-8 -*-
"""一次性修复：逐行修正上一轮运算符替换造成的多余右括号（按行号显式给出正确行）。"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PDMS = os.path.join(os.path.dirname(HERE), 'pdms')

FN = {
    'pkpmjwdexport.pmlfnc': {
        111: "   if (!v eq !t) then",
        114: "   if (!v.after('/') eq !t) then",
        143: "   if (!aE lt 0.0) then",
        147: "   if (!aN lt 0.0) then",
        151: "   if (!aU lt 0.0) then",
        154: "   if (!aU gt 1.0) then",
        155: "      if (!aE le 1.0 and !aN le 1.0) then",
        172: "   if (!aE lt 0.0) then",
        176: "   if (!aN lt 0.0) then",
        180: "   if (!aU lt 0.0) then",
        184: "   if (!aU gt 1.0) then",
        185: "      if (!aE le 1.0 and !aN le 1.0) then",
        190: "   if (!aN le 1.0 and !aE gt 1.0) then",
        193: "   if (!aE le 1.0 and !aN gt 1.0) then",
        207: "   if (!el.type eq |PANE|) then",
        210: "   if (!el.type eq |STWALL|) then",
        296: "   if (!nv lt 3) then",
        314: "   if (!spec.length() gt 0) then",
        342: "   if (!spre eq '-') then",
        373: "   if (!outFile.unset() or !outFile.length() le 0) then",
        386: "            if (!site.type eq |SITE|) then",
        404: "   if (!unitName eq 'mm' or !unitName eq 'cm' or !unitName eq 'm') then",
        433: "      if (!e1.type eq |ZONE|) then",
        440: "            if (!e2.type eq |STRU|) then",
        447: "                  if (!e3.type eq |FRMW|) then",
        454: "                        if (!e4.type eq |SBFR|) then",
        462: "                              if (!t5 eq |SCTN|) then",
        466: "                              elseif (!t5 eq |PANE|) then",
        468: "                                 if (!rec.length() gt 0) then",
        475: "                              elseif (!t5 eq |STWALL|) then",
        481: "                        elseif (!e4.type eq |SCTN| or !e4.type eq |PANE| or !e4.type eq |STWALL|) then",
        486: "                           if (!e4.type eq |SCTN|) then",
        490: "                           elseif (!e4.type eq |PANE|) then",
        492: "                              if (!rec.length() gt 0) then",
    },
    'pkpmjwd.pmlfrm': {
        84: "   if (!p.unset() or !p.length() le 0) then",
        111: "   if (!p.unset().not() and !p.length() gt 0) then",
        120: "   if (!out.unset() or !out.length() le 0) then",
        128: "   if (!res.before('|') neq 'OK') then",
    },
}

for name, fixmap in FN.items():
    path = os.path.join(PDMS, name)
    lines = open(path, 'rb').read().decode('utf-8').split('\n')
    for no, want in fixmap.items():
        got = lines[no - 1]
        assert got.count('(') != got.count(')'), '第 %d 行本来括号是平的，不该修：%r' % (no, got)
        lines[no - 1] = want
        print('%s:%d  %s' % (name, no, want))
    open(path, 'wb').write('\n'.join(lines).encode('utf-8'))
print('done')
