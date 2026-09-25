# -*- coding: utf-8 -*-
"""一次性修复 install.ps1 的插入缩进：
  * 追加内容按目标子女缩进（<Tools>/<MenuBar> 都是 2 空格 → 子女 4 空格）生成；
  * 插入点改到 </Tools> / </MenuBar> 所在行的行首，保证既有行的缩进不被改动。
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(os.path.dirname(HERE), 'install', 'install.ps1')
text = open(P, 'rb').read().decode('gbk').replace('\r\n', '\n')

OLD_BLOCK_HEAD = """$menuBlock = @(
    '    <MenuTool Name="PKPMJWD.Menu">',
    '      <Image />',
    '      <Caption>PKPM-JWD</Caption>',
    '      <DisplayStyle>Default</DisplayStyle>',
    '      <Tools>',
    '        <Tool Name="PKPMJWD.Open" />',
    '      </Tools>',
    '      <IsContextMenu>false</IsContextMenu>',
    '    </MenuTool>',
    '    <ButtonTool Name="PKPMJWD.Open">',
    '      <Command>',
    '        <Type>Macro</Type>',
    '        <Macro>show !!pkpmjwd</Macro>',
    '        <Arguments />',
    '      </Command>',
    '      <Image />',
    '      <Caption>PKPM-JWD 导入导出</Caption>',
    '      <DisplayStyle>Default</DisplayStyle>',
    '    </ButtonTool>'
) -join $nl
"""
NEW_BLOCK_HEAD = """$menuInner = @(
    '<MenuTool Name="PKPMJWD.Menu">',
    '  <Image />',
    '  <Caption>PKPM-JWD</Caption>',
    '  <DisplayStyle>Default</DisplayStyle>',
    '  <Tools>',
    '    <Tool Name="PKPMJWD.Open" />',
    '  </Tools>',
    '  <IsContextMenu>false</IsContextMenu>',
    '</MenuTool>',
    '<ButtonTool Name="PKPMJWD.Open">',
    '  <Command>',
    '    <Type>Macro</Type>',
    '    <Macro>show !!pkpmjwd</Macro>',
    '    <Arguments />',
    '  </Command>',
    '  <Image />',
    '  <Caption>PKPM-JWD 导入导出</Caption>',
    '  <DisplayStyle>Default</DisplayStyle>',
    '</ButtonTool>')
$menuBlock = ($menuInner | ForEach-Object { '    ' + $_ }) -join $nl
"""

OLD_INSERT = """    $insToolsLine = ($uicText.Substring(0, $idx) -split "`n").Count
    $insBarLine = ($uicText.Substring(0, $barIdx) -split "`n").Count

    $newText = $uicText.Substring(0, $idx) + $menuBlock + $nl + '  ' + $uicText.Substring($idx)
    $barIdx2 = $newText.IndexOf('</MenuBar>')
    $newText = $newText.Substring(0, $barIdx2) + $barLine + $nl + '  ' + $newText.Substring($barIdx2)
"""
NEW_INSERT = """    $insToolsLine = ($uicText.Substring(0, $idx) -split "`n").Count
    $insBarLine = ($uicText.Substring(0, $barIdx) -split "`n").Count

    # 插入到 </Tools> 所在行的行首（只追加，既有行的缩进原样保留）
    $p = $uicText.LastIndexOf($nl, [Math]::Max($idx - 1, 0))
    if ($p -lt 0) { $p = 0 - $nl.Length }
    $toolsLineStart = $p + $nl.Length
    $toolsIndent = $uicText.Substring($toolsLineStart, $idx - $toolsLineStart)
    $newText = $uicText.Substring(0, $toolsLineStart) + $menuBlock + $nl + $toolsIndent + $uicText.Substring($idx)

    $barIdx2 = $newText.IndexOf('</MenuBar>')
    $q = $newText.LastIndexOf($nl, [Math]::Max($barIdx2 - 1, 0))
    if ($q -lt 0) { $q = 0 - $nl.Length }
    $barLineStart = $q + $nl.Length
    $barIndent = $newText.Substring($barLineStart, $barIdx2 - $barLineStart)
    $newText = $newText.Substring(0, $barLineStart) + $barLine + $nl + $barIndent + $newText.Substring($barIdx2)
"""

for old, new, label in ((OLD_BLOCK_HEAD, NEW_BLOCK_HEAD, 'menuBlock 定义'),
                        (OLD_INSERT, NEW_INSERT, '插入逻辑')):
    n = text.count(old)
    assert n == 1, '%s：期望 1 处，实际 %d 处' % (label, n)
    text = text.replace(old, new)
    print('已替换：%s' % label)

open(P, 'wb').write(text.replace('\n', '\r\n').encode('gbk'))
print('written %s (%d 字节)' % (P, os.path.getsize(P)))
