<#
  PKPM2PDMS导入导出 v2.1.0 —— PDMS 侧安装脚本（PDMS 12.1 SP4）

  用法（先跑 -DryRun 看完整变更清单，确认后再真装）：
      powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1 -DryRun
      powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1

  参数：
    -PdmsRoot    PDMS 安装根目录，缺省 D:\AVEVA\Plant\PDMS12.1.SP4
    -SourceDir   要安装的 PML 包目录，缺省 <本脚本所在目录>\..\pdms
    -PackageName 装到 PMLLIB 下的子目录名，缺省 pkpm2pdms
    -DryRun      只打印将要发生的全部改动（含内存中做完的 XML 变换与校验），不落盘
    -Force       跳过“PDMS 正在运行”检查（不推荐；PDMS 在跑时覆盖 PML 会读不到新代码）
    -SkipEncodingCheck  跳过源文件的 GBK/CRLF 校验（不推荐）

  本脚本做什么（契约 §i.4 / §g）：
    1) 把 pdms 包复制到 <PDMS根>\PMLLIB\pkpm2pdms\        —— 只新增/覆盖本包这几个文件
    2) 改前把 <PDMS根>\design.uic 备份为 design.uic.bak_pkpm2pdms_<yyyyMMdd_HHmmss>
    3) 往 design.uic「追加」一个菜单项后写回：
         <Tools> 段内追加 <MenuTool Name="PKPM2PDMS.PML.Menu"> + <ButtonTool Name="PKPM2PDMS.PML.Open">
         <MenuBar> 段内追加 <Tool Name="PKPM2PDMS.PML.Menu" />
         ---- Tool Key 必须全局唯一：PDMS 的 RootTools 集合是**跨 uic 文件**的，
              同名会让后加载的整份 uic 被拒载（2026-09-28 实机 P3：原生路线的
              pkpm2pdms.uic 因与本文件注入的 PKPM2PDMS.Menu/PKPM2PDMS.Open 重名，
              被 PDMS 报 "Key ... already exists in the RootTools collection" 整份放弃）。
              原生路线已占用 PKPM2PDMS.Menu / PKPM2PDMS.Open，故本（legacy PML）路线
              一律加 .PML. 前缀；菜单标题仍是「PKPM2PDMS PML」（P3 判据看标题，不看 Key）。
       按钮命令用 <Command><Type>Macro</Type><Macro>show !!pkpm2pdms</Macro></Command>
       —— 这是本机 AVEVA 自带文件里真实存在的写法（PDMS 根目录 HistoryToolbar.uic /
       Schematic Model Manager\Resources\SmmToolsMenu.uic 的 <Type>Macro</Type>），
       不需要任何 .NET add-in，因此**不动 DesignAddins.xml**
       （DesignAddins.xml 只登记 .NET 程序集，写进去会让 Design 启动时找不存在的 DLL）。
    4) 保持 UTF-8 带 BOM + 原换行风格写回；写前/写后都用 [xml] 解析校验；
       写失败或写后校验失败 → 用备份回滚，并报告回滚结果。
    5) 幂等：design.uic 里已有 PKPM2PDMS.PML.Menu 时跳过注入（不动该文件）。

  禁止事项：不删除任何既有文件；不重排/改写既有 XML 条目；不动 P-TRANS 目录。
#>
[CmdletBinding()]
param(
    [string]$PdmsRoot = 'D:\AVEVA\Plant\PDMS12.1.SP4',
    [string]$SourceDir = '',
    [string]$PackageName = 'pkpm2pdms',
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

# R6：PML 包一函数一文件（PMLLIB 自动加载规则 = 文件名 = 函数名，见 pdms\README.txt），
#     所以按目录枚举源包里全部 PML/文本文件（逐条印在【1】清单里），而不是写死 4 个名字。
# 〔R7 实机修复·部署清单〕退役族**不部署**：改名责任已整体移交 .NET 侧 SITE 名探测
#   （SiteProber）+ 引擎生成期查重，宏里零 PML 函数调用
#   （证据 验收/R7日志/addin_log_full_r7.txt 的 "no PML preload at addin start
#    (retired family; site name probed on run)"）。
#   与原生 deploy 路线同一份口径 = 插件包\pdms-net\deploy\deploy_pkpm2pdms.py 的
#   RETIRED_PML。工作树里这 5 个文件**保留不删**，只是不进本清单、不复制到 PMLLIB。
$retired = @('pkpm2pdmsuniquename.pmlfnc', 'pkpm2pdmsrenamescount.pmlfnc',
             'pkpm2pdmsrenamesfailcount.pmlfnc', 'pkpm2pdmsrenamesshow.pmlfnc',
             'pkpm2pdmsrunmac.pmlfnc')
$required = @(Get-ChildItem -LiteralPath $SourceDir -File |
              Where-Object { $_.Extension -in '.pmlfnc', '.pmlfrm', '.mac', '.txt' } |
              Where-Object { $retired -notcontains $_.Name } |
              Sort-Object Name | ForEach-Object { $_.Name })
if ($required.Count -eq 0) { Fail ('源包目录里没有 PML 文件：' + $SourceDir) $ExitArgs }
foreach ($must in @('pkpm2pdms.pmlfrm', 'pkpm2pdmsexport.pmlfnc',
                    'pkpm2pdmsdbexport.pmlfnc', 'pkpm2pdmsrun.mac')) {
    if ($required -notcontains $must) { Fail ('源包缺少 ' + $must) $ExitArgs }
}
$sources = @()
foreach ($n in $required) {
    $p = Join-Path $SourceDir $n
    if (-not (Test-Path -LiteralPath $p -PathType Leaf)) { Fail ("源包缺少 " + $n) $ExitArgs }
    $sources += $p
}
$targetDir = Join-Path $PdmsRoot ('PMLLIB\' + $PackageName)

# ---------------------------------------------------------------- 源文件编码校验
# 范围：只校验 **PDMS 会解析的** PML 源（.pmlfnc/.pmlfrm/.mac）——契约要求
#       「PDMS 侧产物 GBK 无 BOM + CRLF」只针对这几种文件。
#       .txt 是给人看的说明（README.txt，UTF-8 无 BOM + LF，见静态回归规则 B），
#       PDMS 从不解析它，按原形态复制即可；把它纳入 GBK 校验会让安装被自己的
#       文档文件卡死（R6 实机 P1 首跑即命中：README.txt 报「非 CRLF 242 处」）。
$encFails = @()
# 〔R7 实机修复·编码预检空转〕$sources 里装的是**路径字符串**，字符串没有 .Extension
#   属性（取到 $null）-> 这里恒匹配 0 条 -> 预检形同虚设却仍打印"已校验 N 个 = GBK 无 BOM
#   + CRLF"这种结论性措辞（R7 实机 P1_install_dryrun_r7.txt 首行：'已校验 0 个'，
#   根因与实测见 验收/R7日志/P1_install_enc_precheck_defect.txt）。
#   修法：过滤前先 Get-Item 转成 FileInfo（$sources 本身保持字符串，供【1】/【4】沿用）。
$encChecked = @($sources | ForEach-Object { Get-Item -LiteralPath $_ } |
                Where-Object { $_.Extension -in '.pmlfnc', '.pmlfrm', '.mac' })
if (-not $SkipEncodingCheck) {
    foreach ($p in $encChecked) {
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
    # 注意（本机 PS 5.1 实测）："行尾是完整操作数、下一行以 + 开头" 的续行写法会报
    # MissingEndParenthesisInExpression（C:\TEMP\r6\cases\e1.ps1 最小复现：2026-09-28）。
    # 所以续行一律把 + 放在行尾。
    Say ('编码检查：已校验 ' + $encChecked.Count + ' 个 PDMS 解析源（.pmlfnc/.pmlfrm/.mac）' +
         ' = GBK 无 BOM + CRLF；另有 ' + ($sources.Count - $encChecked.Count) +
         ' 个非解析文件（.txt，按原形态复制，PDMS 不解析）未纳入该校验')
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
    '<MenuTool Name="PKPM2PDMS.PML.Menu">',
    '  <Image />',
    '  <Caption>PKPM2PDMS PML</Caption>',
    '  <DisplayStyle>Default</DisplayStyle>',
    '  <Tools>',
    '    <Tool Name="PKPM2PDMS.PML.Open" />',
    '  </Tools>',
    '  <IsContextMenu>false</IsContextMenu>',
    '</MenuTool>',
    '<ButtonTool Name="PKPM2PDMS.PML.Open">',
    '  <Command>',
    '    <Type>Macro</Type>',
    '    <Macro>show !!pkpm2pdms</Macro>',
    '    <Arguments />',
    '  </Command>',
    '  <Image />',
    '  <Caption>PKPM2PDMS PML 导入导出</Caption>',
    '  <DisplayStyle>Default</DisplayStyle>',
    '</ButtonTool>')
$menuBlock = ($menuInner | ForEach-Object { '    ' + $_ }) -join $nl
$barLine = '    <Tool Name="PKPM2PDMS.PML.Menu" />'

$already = $uicText -match 'PKPM2PDMS\.PML\.Menu'
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
$bakCandidate = $uicPath + '.bak_pkpm2pdms_' + $ts
$bakPath = $bakCandidate
$k = 1
while ((Test-Path -LiteralPath $bakPath) -and (-not $DryRun)) {
    $bakPath = $bakCandidate + '_' + $k
    $k++
}

Say '=============================================================='
Say (' PKPM2PDMS导入导出 v2.1.0 安装' + $(if ($DryRun) { '（-DryRun 只打印，不落盘）' } else { '' }))
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
Say ('   —— 另有 ' + $retired.Count + ' 个退役族文件**不部署**（工作树保留不删）：' +
     ($retired -join '、'))
Say ''
Say '【2】design.uic 追加菜单项：'
Say ('   文件       : ' + $uicPath)
Say ('   当前状态   : ' + $(if ($already) { '已含 PKPM2PDMS.PML.Menu —— 本次跳过注入（幂等）' } else { '未含 PKPM2PDMS.PML.Menu，将追加' }))
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
            if ($verify -notmatch 'PKPM2PDMS\.PML\.Menu') { throw '回读内容里没有 PKPM2PDMS.PML.Menu' }
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
    Say '   design.uic 已含 PKPM2PDMS.PML.Menu，跳过注入与备份（幂等）'
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
try { $final = [System.IO.File]::ReadAllText($uicPath, $strictUtf8); $null = [xml]$final; $finalOk = ($final -match 'PKPM2PDMS\.PML\.Menu') } catch { }
Say ('   design.uic : 可解析且含菜单项 = ' + $finalOk)
Say ''
Say '接下来：完全退出并重启 PDMS（新 PML 文件需要重启后才会被索引；'
Say '        不要手工运行 pmlscan.exe，也不要改 PMLLIB\pml.index）。'
Say '        进入 DESIGN 后菜单栏应出现「PKPM2PDMS PML」，或命令行执行'
Say '        $m "%PMLLIB%/pkpm2pdms/pkpm2pdmsrun.mac" 打开窗体。'
exit $ExitOk
