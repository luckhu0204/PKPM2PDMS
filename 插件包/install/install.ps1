<#
  PKPM-JWD导入导出 —— PDMS 侧安装脚本（PDMS 12.1 SP4）

  用法（先跑 -DryRun 看完整变更清单，确认后再真装）：
      powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1 -DryRun
      powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1

  参数：
    -PdmsRoot    PDMS 安装根目录，缺省 D:\AVEVA\Plant\PDMS12.1.SP4
    -SourceDir   要安装的 PML 包目录，缺省 <本脚本所在目录>\..\pdms
    -PackageName 装到 PMLLIB 下的子目录名，缺省 pkpmjwd
    -DryRun      只打印将要发生的全部改动（含内存中做完的 XML 变换与校验），不落盘
    -Force       跳过“PDMS 正在运行”检查（不推荐；PDMS 在跑时覆盖 PML 会读不到新代码）
    -SkipEncodingCheck  跳过源文件的 GBK/CRLF 校验（不推荐）

  本脚本做什么（契约 §i.4 / §g）：
    1) 把 pdms 包复制到 <PDMS根>\PMLLIB\pkpmjwd\        —— 只新增/覆盖本包这几个文件
    2) 改前把 <PDMS根>\design.uic 备份为 design.uic.bak_pkpmjwd_<yyyyMMdd_HHmmss>
    3) 往 design.uic「追加」一个菜单项后写回：
         <Tools> 段内追加 <MenuTool Name="PKPMJWD.Menu"> + <ButtonTool Name="PKPMJWD.Open">
         <MenuBar> 段内追加 <Tool Name="PKPMJWD.Menu" />
       按钮命令用 <Command><Type>Macro</Type><Macro>show !!pkpmjwd</Macro></Command>
       —— 这是本机 AVEVA 自带文件里真实存在的写法（PDMS 根目录 HistoryToolbar.uic /
       Schematic Model Manager\Resources\SmmToolsMenu.uic 的 <Type>Macro</Type>），
       不需要任何 .NET add-in，因此**不动 DesignAddins.xml**
       （DesignAddins.xml 只登记 .NET 程序集，写进去会让 Design 启动时找不存在的 DLL）。
    4) 保持 UTF-8 带 BOM + 原换行风格写回；写前/写后都用 [xml] 解析校验；
       写失败或写后校验失败 → 用备份回滚，并报告回滚结果。
    5) 幂等：design.uic 里已有 PKPMJWD.Menu 时跳过注入（不动该文件）。

  禁止事项：不删除任何既有文件；不重排/改写既有 XML 条目；不动 P-TRANS 目录。
#>
[CmdletBinding()]
param(
    [string]$PdmsRoot = 'D:\AVEVA\Plant\PDMS12.1.SP4',
    [string]$SourceDir = '',
    [string]$PackageName = 'pkpmjwd',
    [switch]$DryRun,
    [switch]$Force,
    [switch]$SkipEncodingCheck
)

$ErrorActionPreference = 'Stop'
$ExitOk = 0
$ExitArgs = 2
$ExitCheck = 3
$ExitRunning = 4
$ExitWrite = 5

function Say([string]$m) { Write-Host $m }
function Fail([string]$m, [int]$code) { Write-Host ("FAIL: " + $m); exit $code }

if ([string]::IsNullOrWhiteSpace($SourceDir)) {
    $SourceDir = (Resolve-Path (Join-Path $PSScriptRoot '..\pdms')).Path
}
if (-not (Test-Path -LiteralPath $PdmsRoot -PathType Container)) {
    Fail ("PDMS 根目录不存在：" + $PdmsRoot) $ExitArgs
}
$uicPath = Join-Path $PdmsRoot 'design.uic'
if (-not (Test-Path -LiteralPath $uicPath -PathType Leaf)) {
    Fail ("找不到 " + $uicPath) $ExitArgs
}
if (-not (Test-Path -LiteralPath $SourceDir -PathType Container)) {
    Fail ("源包目录不存在：" + $SourceDir) $ExitArgs
}

$required = @('pkpmjwd.pmlfrm', 'pkpmjwdexport.pmlfnc', 'pkpmjwddbexport.pmlfnc', 'pkpmjwdrun.mac')
$sources = @()
foreach ($n in $required) {
    $p = Join-Path $SourceDir $n
    if (-not (Test-Path -LiteralPath $p -PathType Leaf)) { Fail ("源包缺少 " + $n) $ExitArgs }
    $sources += $p
}
$targetDir = Join-Path $PdmsRoot ('PMLLIB\' + $PackageName)

# ---------------------------------------------------------------- 源文件编码校验
$encFails = @()
if (-not $SkipEncodingCheck) {
    foreach ($p in $sources) {
        $b = [System.IO.File]::ReadAllBytes($p)
        if ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF) {
            $encFails += ("UTF-8 BOM：" + (Split-Path $p -Leaf))
            continue
        }
        $loneLf = 0
        for ($i = 0; $i -lt $b.Length; $i++) {
            if ($b[$i] -eq 0x0A -and ($i -eq 0 -or $b[$i - 1] -ne 0x0D)) { $loneLf++ }
        }
        if ($loneLf -gt 0) { $encFails += ("非 CRLF 换行 " + $loneLf + " 处：" + (Split-Path $p -Leaf)) }
        $gbk = [System.Text.Encoding]::GetEncoding(936)
        $rt = $gbk.GetBytes($gbk.GetString($b))
        if ($rt.Length -ne $b.Length) { $encFails += ("GBK 往返长度不一致：" + (Split-Path $p -Leaf)) }
        else {
            for ($i = 0; $i -lt $b.Length; $i++) {
                if ($rt[$i] -ne $b[$i]) { $encFails += ("GBK 往返字节不一致（偏移 " + $i + "）：" + (Split-Path $p -Leaf)); break }
            }
        }
    }
    if ($encFails.Count -gt 0) {
        Say '源包编码检查未通过（契约 §g：PDMS 侧产物必须 GBK 无 BOM + CRLF）：'
        foreach ($e in $encFails) { Say ('   - ' + $e) }
        Say '提示：先跑  python test\make_gbk.py  转换后再安装；确要跳过请加 -SkipEncodingCheck'
        exit $ExitCheck
    }
}

# ---------------------------------------------------------------- PDMS 进程检查
if (-not $DryRun -and -not $Force) {
    $running = @()
    foreach ($pn in @('des', 'PDMSConsole', 'mon')) {
        if (Get-Process -Name $pn -ErrorAction SilentlyContinue) { $running += $pn }
    }
    if ($running.Count -gt 0) {
        Fail ("PDMS 正在运行（" + ($running -join ', ') + "）：先完全退出 PDMS 再安装；确要强行安装加 -Force") $ExitRunning
    }
}

# ---------------------------------------------------------------- design.uic 变换（内存中）
$strictUtf8 = New-Object System.Text.UTF8Encoding($false, $true)
$uicBytes = [System.IO.File]::ReadAllBytes($uicPath)
$hasBom = ($uicBytes.Length -ge 3 -and $uicBytes[0] -eq 0xEF -and $uicBytes[1] -eq 0xBB -and $uicBytes[2] -eq 0xBF)
try { $uicText = [System.IO.File]::ReadAllText($uicPath, $strictUtf8) }
catch { Fail ("design.uic 不是合法 UTF-8：" + $_.Exception.Message) $ExitCheck }
$nl = "`r`n"; if ($uicText -notmatch "`r`n") { $nl = "`n" }

try { $null = [xml]$uicText; $origParses = $true }
catch { $origParses = $false; $origErr = $_.Exception.Message }

$menuInner = @(
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
$barLine = '    <Tool Name="PKPMJWD.Menu" />'

$already = $uicText -match 'PKPMJWD\.Menu'
$newText = $uicText
$insToolsLine = -1
$insBarLine = -1
if (-not $already) {
    if (-not $origParses) { Fail ("design.uic 现在就不是合法 XML，拒绝改动：" + $origErr) $ExitCheck }

    # 顶层 </Tools>：其后（忽略空白）紧跟 <InstanceTools 的那一个
    $idx = -1
    $searchFrom = 0
    while ($true) {
        $p = $uicText.IndexOf('</Tools>', $searchFrom)
        if ($p -lt 0) { break }
        $tail = $uicText.Substring($p + 8)
        if ($tail -match '^\s*<InstanceTools') { $idx = $p; break }
        $searchFrom = $p + 1
    }
    if ($idx -lt 0) { Fail '设计文件里找不到顶层 </Tools>（其后应为 <InstanceTools），拒绝猜测插入点' $ExitCheck }

    # </MenuBar> 必须唯一
    $barCount = ([regex]::Matches($uicText, '</MenuBar>')).Count
    if ($barCount -ne 1) { Fail ("design.uic 里 </MenuBar> 出现 " + $barCount + " 次，无法唯一定位，拒绝改动") $ExitCheck }
    $barIdx = $uicText.IndexOf('</MenuBar>')

    $insToolsLine = ($uicText.Substring(0, $idx) -split "`n").Count
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

    try { $null = [xml]$newText; $newParses = $true }
    catch { Fail ("追加菜单后 XML 校验失败，未写盘：" + $_.Exception.Message) $ExitCheck }
} else {
    $newParses = $true
}

# ---------------------------------------------------------------- 变更清单
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$bakCandidate = $uicPath + '.bak_pkpmjwd_' + $ts
$bakPath = $bakCandidate
$k = 1
while ((Test-Path -LiteralPath $bakPath) -and (-not $DryRun)) {
    $bakPath = $bakCandidate + '_' + $k
    $k++
}

Say '=============================================================='
Say (' PKPM-JWD导入导出 安装' + $(if ($DryRun) { '（-DryRun 只打印，不落盘）' } else { '' }))
Say '=============================================================='
Say ('PDMS 根      : ' + $PdmsRoot)
Say ('源包目录     : ' + $SourceDir)
Say ('目标包目录   : ' + $targetDir)
Say ''
Say '【1】将新增/覆盖的文件（逐条）：'
foreach ($p in $sources) {
    $leaf = Split-Path $p -Leaf
    $dst = Join-Path $targetDir $leaf
    $action = if (Test-Path -LiteralPath $dst) { '覆盖' } else { '新增' }
    Say ('   ' + $action + '  ' + $dst)
    Say ('         ← ' + $p + '   (' + (Get-Item -LiteralPath $p).Length + ' 字节)')
}
Say ''
Say '【2】design.uic 追加菜单项：'
Say ('   文件       : ' + $uicPath)
Say ('   当前状态   : ' + $(if ($already) { '已含 PKPMJWD.Menu —— 本次跳过注入（幂等）' } else { '未含 PKPMJWD.Menu，将追加' }))
Say ('   原文件    : ' + $uicBytes.Length + ' 字节，' + ($uicText -split "`n").Count + ' 行，BOM=' + $hasBom + '，换行=' + $(if ($nl -eq "`r`n") { 'CRLF' } else { 'LF' }))
Say ('   现在即可解析 XML : ' + $origParses)
if (-not $already) {
    Say ('   备份为     : ' + $bakPath)
    Say ('   插入点 1   : 第 ' + $insToolsLine + ' 行 </Tools> 之前（<Tools> 段的末尾）')
    Say ('   插入点 2   : 第 ' + $insBarLine + ' 行 </MenuBar> 之前（菜单栏末尾）')
    Say ('   追加内容   :')
    foreach ($l in ($menuBlock -split "`n")) { Say ('      ' + $l) }
    Say ('      ' + $barLine)
    Say ('   写回后    : ' + ($strictUtf8.GetByteCount($newText) + $(if ($hasBom) { 3 } else { 0 })) + ' 字节，' + ($newText -split "`n").Count + ' 行，UTF-8' + $(if ($hasBom) { ' 带 BOM' } else { ' 无 BOM' }) + ' + 原换行风格')
    Say ('   写前校验   : 追加后 XML 解析 ' + $(if ($newParses) { '通过' } else { '失败' }))
    Say ('   写后校验   : 回读并重新解析 design.uic；失败则用上面的 .bak 回滚')
}
Say ''
Say '【3】不做的事：'
Say '   - 不改 DesignAddins.xml（本包是纯 PML，没有 .NET add-in 可登记）'
Say '   - 不删除、不重排、不改写 design.uic 既有条目（TGTEXT / PDCOPILOT / Bopood 等原样保留）'
Say '   - 不动 P-TRANS 目录、不动任何样本原件、不动 PMLLIB\pml.index'
Say ''

if ($DryRun) {
    Say 'DRYRUN-OK：以上为将要发生的全部改动，未写入任何文件。'
    exit $ExitOk
}

# ---------------------------------------------------------------- 执行
Say '【4】开始安装 …'
if (-not (Test-Path -LiteralPath $targetDir -PathType Container)) {
    $null = New-Item -ItemType Directory -Path $targetDir -Force
    Say ('   已创建目录 ' + $targetDir)
}
foreach ($p in $sources) {
    $leaf = Split-Path $p -Leaf
    $dst = Join-Path $targetDir $leaf
    Copy-Item -LiteralPath $p -Destination $dst -Force
    Say ('   已复制 ' + $dst)
}

$rolledBack = $false
if (-not $already) {
    try {
        Copy-Item -LiteralPath $uicPath -Destination $bakPath -ErrorAction Stop
        Say ('   已备份 design.uic → ' + $bakPath)
    } catch { Fail ("备份 design.uic 失败，未做任何改动：" + $_.Exception.Message) $ExitWrite }

    $outBytes = $strictUtf8.GetBytes($newText)
    if ($hasBom) {
        $withBom = New-Object byte[] ($outBytes.Length + 3)
        $withBom[0] = 0xEF; $withBom[1] = 0xBB; $withBom[2] = 0xBF
        [Array]::Copy($outBytes, 0, $withBom, 3, $outBytes.Length)
        $outBytes = $withBom
    }
    try {
        [System.IO.File]::WriteAllBytes($uicPath, $outBytes)
        Say ('   已写回 design.uic（' + $outBytes.Length + ' 字节）')
    } catch {
        Say ('   写 design.uic 失败：' + $_.Exception.Message + ' —— 尝试回滚')
        [System.IO.File]::WriteAllBytes($uicPath, $uicBytes)
        $rolledBack = $true
    }

    if (-not $rolledBack) {
        try {
            $verify = [System.IO.File]::ReadAllText($uicPath, $strictUtf8)
            $null = [xml]$verify
            if ($verify -notmatch 'PKPMJWD\.Menu') { throw '回读内容里没有 PKPMJWD.Menu' }
            Say '   写后校验通过（XML 可解析，菜单项存在）'
        } catch {
            Say ('   写后校验失败：' + $_.Exception.Message + ' —— 用备份回滚')
            [System.IO.File]::WriteAllBytes($uicPath, $uicBytes)
            $rolledBack = $true
        }
    }
    if ($rolledBack) {
        try {
            $null = [xml]([System.IO.File]::ReadAllText($uicPath, $strictUtf8))
            Say '   回滚完成：design.uic 已恢复为安装前内容（XML 可解析）'
        } catch {
            Fail ('回滚后 design.uic 仍不可解析！请手动用 ' + $bakPath + ' 覆盖恢复') $ExitWrite
        }
        exit $ExitWrite
    }
} else {
    Say '   design.uic 已含 PKPMJWD.Menu，跳过注入与备份（幂等）'
}

Say ''
Say '【5】安装结果：'
Say ('   包目录     : ' + $targetDir)
foreach ($p in $sources) {
    $leaf = Split-Path $p -Leaf
    $dst = Join-Path $targetDir $leaf
    $fi = Get-Item -LiteralPath $dst
    Say ('     ' + $leaf + '  ' + $fi.Length + ' 字节  ' + $fi.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss'))
}
$finalOk = $false
try { $final = [System.IO.File]::ReadAllText($uicPath, $strictUtf8); $null = [xml]$final; $finalOk = ($final -match 'PKPMJWD\.Menu') } catch { }
Say ('   design.uic : 可解析且含菜单项 = ' + $finalOk)
Say ''
Say '接下来：完全退出并重启 PDMS（新 PML 文件需要重启后才会被索引；'
Say '        不要手工运行 pmlscan.exe，也不要改 PMLLIB\pml.index）。'
Say '        进入 DESIGN 后菜单栏应出现「PKPM-JWD」，或命令行执行'
Say '        $m "%PMLLIB%/pkpmjwd/pkpmjwdrun.mac" 打开窗体。'
exit $ExitOk
