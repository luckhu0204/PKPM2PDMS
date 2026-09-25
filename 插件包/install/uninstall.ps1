<#
  PKPM-JWD导入导出 —— PDMS 侧卸载脚本（PDMS 12.1 SP4）

  用法（先跑 -DryRun 看清单）：
      powershell -NoProfile -ExecutionPolicy Bypass -File uninstall.ps1 -DryRun
      powershell -NoProfile -ExecutionPolicy Bypass -File uninstall.ps1
      powershell -NoProfile -ExecutionPolicy Bypass -File uninstall.ps1 -Purge
      powershell -NoProfile -ExecutionPolicy Bypass -File uninstall.ps1 -RestoreBackup

  参数：
    -PdmsRoot     PDMS 安装根目录，缺省 D:\AVEVA\Plant\PDMS12.1.SP4
    -PackageName  PMLLIB 下的包目录名，缺省 pkpmjwd
    -DryRun       只打印将要发生的全部改动，不落盘
    -Purge        真正删除包目录（缺省是“移动到备份目录”，不删文件）
    -RestoreBackup  用最新的 design.uic.bak_pkpmjwd_* 整份覆盖 design.uic
                    （缺省走“只删本包追加的条目”的外科式移除，不动别人的条目）

  行为：
    1) 改前先把 <PDMS根>\design.uic 备份为 design.uic.bak_uninstall_<yyyyMMdd_HHmmss>
    2) 只移除本包追加的三处 XML 条目（幂等；找不到就跳过、不写文件）：
         <ButtonTool Name="PKPMJWD.Open"> … </ButtonTool>
         <MenuTool   Name="PKPMJWD.Menu"> … </MenuTool>
         <MenuBar> 内的 <Tool Name="PKPMJWD.Menu" />
       其它条目（TGTEXT / PDCOPILOT / Bopood 等）原样保留；移除后用 [xml] 校验，
       失败立即用备份回滚并报错。
    3) 移除 <PDMS根>\PMLLIB\pkpmjwd：缺省移动为 PMLLIB\_removed_pkpmjwd_<ts>\（保留证据）；
       -Purge 时先逐条列出文件清单再删（不用通配符删除，逐条列出后按确切路径删）。
    4) 不触碰 PMLLIB\pml.index、不触碰样本原件、不触碰 P-TRANS。
#>
[CmdletBinding()]
param(
    [string]$PdmsRoot = 'D:\AVEVA\Plant\PDMS12.1.SP4',
    [string]$PackageName = 'pkpmjwd',
    [switch]$DryRun,
    [switch]$Purge,
    [switch]$RestoreBackup
)

$ErrorActionPreference = 'Stop'
$ExitOk = 0
$ExitArgs = 2
$ExitCheck = 3
$ExitWrite = 5

function Say([string]$m) { Write-Host $m }
function Fail([string]$m, [int]$code) { Write-Host ("FAIL: " + $m); exit $code }

if (-not (Test-Path -LiteralPath $PdmsRoot -PathType Container)) {
    Fail ("PDMS 根目录不存在：" + $PdmsRoot) $ExitArgs
}
$uicPath = Join-Path $PdmsRoot 'design.uic'
$targetDir = Join-Path $PdmsRoot ('PMLLIB\' + $PackageName)
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'

$strictUtf8 = New-Object System.Text.UTF8Encoding($false, $true)
$hasUic = Test-Path -LiteralPath $uicPath -PathType Leaf

Say '=============================================================='
Say (' PKPM-JWD导入导出 卸载' + $(if ($DryRun) { '（-DryRun 只打印，不落盘）' } else { '' }))
Say '=============================================================='
Say ('PDMS 根     : ' + $PdmsRoot)
Say ('包目录      : ' + $targetDir)
Say ''

# ---------------------------------------------------------------- 备份选择
$bakList = @()
if ($hasUic) { $bakList = @(Get-ChildItem -LiteralPath $PdmsRoot -Filter 'design.uic.bak_pkpmjwd_*' -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending) }
Say ('【1】已有的安装前备份 design.uic.bak_pkpmjwd_* ：' + $bakList.Count + ' 个')
foreach ($b in $bakList) { Say ('      ' + $b.Name + '   ' + $b.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss') + '   ' + $b.Length + ' 字节') }
$uninstallBak = $uicPath + '.bak_uninstall_' + $ts
Say ('      本次卸载前备份为： ' + $uninstallBak)
Say ''

# ---------------------------------------------------------------- 待移除条目
$patterns = @(
    @{ Name = 'ButtonTool PKPMJWD.Open'; Regex = '(?s)[ \t]*<ButtonTool Name="PKPMJWD\.Open">.*?</ButtonTool>\r?\n' },
    @{ Name = 'MenuTool PKPMJWD.Menu'; Regex = '(?s)[ \t]*<MenuTool Name="PKPMJWD\.Menu">.*?</MenuTool>\r?\n' },
    @{ Name = 'MenuBar Tool PKPMJWD.Menu'; Regex = '(?m)^[ \t]*<Tool Name="PKPMJWD\.Menu" />[ \t]*\r?\n' }
)

$uicBytes = $null
$uicText = ''
$counts = @{}
$newText = ''
$changed = $false
if ($hasUic) {
    $uicBytes = [System.IO.File]::ReadAllBytes($uicPath)
    $hasBom = ($uicBytes.Length -ge 3 -and $uicBytes[0] -eq 0xEF -and $uicBytes[1] -eq 0xBB -and $uicBytes[2] -eq 0xBF)
    try { $uicText = [System.IO.File]::ReadAllText($uicPath, $strictUtf8) }
    catch { Fail ("design.uic 不是合法 UTF-8：" + $_.Exception.Message) $ExitCheck }
    $newText = $uicText
    foreach ($p in $patterns) {
        $m = [regex]::Matches($newText, $p.Regex)
        $counts[$p.Name] = $m.Count
        if ($m.Count -gt 0) { $changed = $true; $newText = [regex]::Replace($newText, $p.Regex, '') }
    }
    $orphan = ([regex]::Matches($newText, 'PKPMJWD')).Count
    Say '【2】design.uic 内本包条目的移除计划：'
    foreach ($p in $patterns) { Say ('      ' + $p.Name + ' ： 命中 ' + $counts[$p.Name] + ' 处') }
    Say ('      移除后残留 PKPMJWD 字样 ： ' + $orphan + ' 处（应为 0）')
    Say ('      是否需要写回 ： ' + $changed)
    if ($changed) {
        try { $null = [xml]$newText }
        catch { Fail ("移除条目后 XML 校验失败，未写盘：" + $_.Exception.Message) $ExitCheck }
    }
} else {
    Say '【2】找不到 design.uic：跳过菜单条目移除'
}
Say ''

# ---------------------------------------------------------------- 包目录
$dirFiles = @()
if (Test-Path -LiteralPath $targetDir -PathType Container) {
    $dirFiles = @(Get-ChildItem -LiteralPath $targetDir -File | Sort-Object Name)
} 
$movedTo = Join-Path $PdmsRoot ('PMLLIB\_removed_' + $PackageName + '_' + $ts)
Say '【3】包目录处理：'
if ($dirFiles.Count -eq 0 -and -not (Test-Path -LiteralPath $targetDir)) {
    Say ('      不存在： ' + $targetDir + ' （无需处理）')
} else {
    Say ('      目录内文件 ' + $dirFiles.Count + ' 个（逐条列出，不用通配符）：')
    foreach ($f in $dirFiles) { Say ('        ' + $f.FullName + '   ' + $f.Length + ' 字节') }
    if ($Purge) { Say ('      模式：-Purge —— 按上面列出的确切路径删除该目录') }
    else { Say ('      模式：默认 —— 整目录移动为 ' + $movedTo + '（不删文件）') }
}
Say ''
if ($RestoreBackup) {
    Say '【4】-RestoreBackup：将用最新的 design.uic.bak_pkpmjwd_* 整份覆盖 design.uic'
    if ($bakList.Count -eq 0) { Say '      没有可用备份 → 该项跳过' }
    else { Say ('      使用： ' + $bakList[0].Name) }
    Say ''
}

if ($DryRun) {
    Say 'DRYRUN-OK：以上为将要发生的全部改动，未写入/未移动任何文件。'
    exit $ExitOk
}

# ---------------------------------------------------------------- 执行
Say '【5】开始卸载 …'
$rolledBack = $false
if ($RestoreBackup -and $bakList.Count -gt 0) {
    try {
        Copy-Item -LiteralPath $uicPath -Destination $uninstallBak -ErrorAction Stop
        Say ('   已备份 design.uic → ' + $uninstallBak)
    } catch { Fail ("备份 design.uic 失败，未做任何改动：" + $_.Exception.Message) $ExitWrite }
    try {
        [System.IO.File]::WriteAllBytes($uicPath, [System.IO.File]::ReadAllBytes($bakList[0].FullName))
        $null = [xml]([System.IO.File]::ReadAllText($uicPath, $strictUtf8))
        Say ('   已按备份整份恢复： ' + $bakList[0].Name)
    } catch {
        Say ('   恢复失败：' + $_.Exception.Message + ' —— 回滚本次改动')
        [System.IO.File]::WriteAllBytes($uicPath, $uicBytes)
        Fail '恢复备份失败，已回滚；请人工检查 design.uic' $ExitWrite
    }
} elseif ($changed) {
    try {
        Copy-Item -LiteralPath $uicPath -Destination $uninstallBak -ErrorAction Stop
        Say ('   已备份 design.uic → ' + $uninstallBak)
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
        $verify = [System.IO.File]::ReadAllText($uicPath, $strictUtf8)
        $null = [xml]$verify
        if ($verify -match 'PKPMJWD') { throw '回读内容里仍有 PKPMJWD 字样' }
        Say '   已移除本包条目，写后校验通过（XML 可解析、无 PKPMJWD 残留）'
    } catch {
        Say ('   写后校验失败：' + $_.Exception.Message + ' —— 用备份回滚')
        [System.IO.File]::WriteAllBytes($uicPath, $uicBytes)
        $rolledBack = $true
    }
    if ($rolledBack) {
        try { $null = [xml]([System.IO.File]::ReadAllText($uicPath, $strictUtf8)); Say '   回滚完成：design.uic 已恢复为卸载前内容' }
        catch { Fail ('回滚后 design.uic 仍不可解析！请手动用 ' + $uninstallBak + ' 覆盖恢复') $ExitWrite }
        exit $ExitWrite
    }
} else {
    Say '   design.uic 无本包条目：跳过（幂等）'
}

if (Test-Path -LiteralPath $targetDir -PathType Container) {
    if ($Purge) {
        Say '   删除包目录内已列出的文件：'
        foreach ($f in $dirFiles) { Say ('     删 ' + $f.FullName) }
        foreach ($f in $dirFiles) { Remove-Item -LiteralPath $f.FullName -Force }
        $left = @(Get-ChildItem -LiteralPath $targetDir -Recurse -Force)
        if ($left.Count -gt 0) {
            Say ('   目录内仍有 ' + $left.Count + ' 项（子目录等），保留目录： ' + $targetDir)
            foreach ($x in $left) { Say ('     保留 ' + $x.FullName) }
        } else {
            Remove-Item -LiteralPath $targetDir -Force
            Say ('   已删除空目录 ' + $targetDir)
        }
    } else {
        if (Test-Path -LiteralPath $movedTo) { Fail ('目标备份目录已存在，请改名后重试： ' + $movedTo) $ExitWrite }
        Move-Item -LiteralPath $targetDir -Destination $movedTo
        Say ('   已把包目录移动到 ' + $movedTo + '（未删除任何文件；确认无误后可自行清理）')
    }
} else {
    Say ('   包目录不存在，跳过： ' + $targetDir)
}

Say ''
Say '【6】卸载结果：'
$uicOk = $false
if (Test-Path -LiteralPath $uicPath) {
    try { $t = [System.IO.File]::ReadAllText($uicPath, $strictUtf8); $null = [xml]$t; $uicOk = ($t -notmatch 'PKPMJWD') } catch { }
}
Say ('   design.uic : 可解析且无本包条目 = ' + $uicOk)
Say ('   包目录      : 存在 = ' + (Test-Path -LiteralPath $targetDir))
Say ''
Say '提示：卸载后完全退出并重启 PDMS 生效；不要手工运行 pmlscan.exe、不要改 PMLLIB\pml.index。'
exit $ExitOk
