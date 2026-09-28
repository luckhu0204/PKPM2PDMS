# probe_dbelement.ps1 -- READ-ONLY reflection dump of Aveva.Pdms.Database.DbElement members
# 用途：为 SiteProber.cs 的「DbElement 直查」提供本机实测签名（只读加载，不改 D:\AVEVA）。
# 复跑：powershell -NoProfile -ExecutionPolicy Bypass -File probe_dbelement.ps1
$ErrorActionPreference = 'Continue'
[System.AppDomain]::CurrentDomain.add_ReflectionOnlyAssemblyResolve({
    param($s, $e)
    $simple = ($e.Name -split ',')[0]
    foreach ($d in @('D:\AVEVA\Plant\PDMS12.1.SP4', 'D:\AVEVA\Plant\PDMS12.1.SP4\SolidSupport',
                     'C:\Windows\Microsoft.NET\Framework\v2.0.50727',
                     'C:\Program Files\Reference Assemblies\Microsoft\Framework\v3.5')) {
        $p = Join-Path $d ($simple + '.dll')
        if (Test-Path -LiteralPath $p) { return [System.Reflection.Assembly]::ReflectionOnlyLoadFrom($p) }
    }
    return $null
})
function Mods([System.Reflection.MethodBase]$m) {
    $t = @()
    if ($m.IsAbstract) { $t += 'abstract' }
    if ($m.IsVirtual)  { $t += 'virtual' }
    if ($m.IsStatic)   { $t += 'static' }
    if ($m.IsPublic) { $t += 'public' } elseif ($m.IsFamily) { $t += 'protected' } elseif ($m.IsFamilyOrAssembly) { $t += 'protected internal' } else { $t += 'nonpublic' }
    return ($t -join ' ')
}
$asm = [System.Reflection.Assembly]::ReflectionOnlyLoadFrom('D:\AVEVA\Plant\PDMS12.1.SP4\Aveva.Pdms.Database.dll')
foreach ($name in @('Aveva.Pdms.Database.DbElement', 'Aveva.Pdms.Database.DbElementType')) {
    $t = $asm.GetType($name)
    if ($t -eq $null) { Write-Output ("===== MISSING TYPE: " + $name); continue }
    Write-Output ('===== ' + $t.FullName + '  IsAbstract=' + $t.IsAbstract + '  Base=' + $t.BaseType)
    $flags = [System.Reflection.BindingFlags]::Instance -bor [System.Reflection.BindingFlags]::Public -bor [System.Reflection.BindingFlags]::NonPublic -bor [System.Reflection.BindingFlags]::Static -bor [System.Reflection.BindingFlags]::DeclaredOnly
    foreach ($m in $t.GetMethods($flags) | Sort-Object Name) {
        Write-Output ('    {0,-96} [{1}]' -f $m.ToString(), (Mods $m))
    }
    Write-Output '  -- props --'
    foreach ($p in $t.GetProperties([System.Reflection.BindingFlags]::Instance -bor [System.Reflection.BindingFlags]::Public -bor [System.Reflection.BindingFlags]::Static -bor [System.Reflection.BindingFlags]::DeclaredOnly) | Sort-Object Name) {
        Write-Output ('    prop {0,-30} type={1}' -f $p.Name, $p.PropertyType)
    }
    Write-Output ''
}
# CurrentElement 所在的类型（AvEva 官方库里的静态入口）
foreach ($tn in @('Aveva.Pdms.Database.DbElementHelper', 'Aveva.Pdms.Database.Database', 'Aveva.Pdms.Database.CurrentElement')) {
    $t2 = $asm.GetType($tn)
    if ($t2 -ne $null) {
        Write-Output ('===== ' + $t2.FullName)
        foreach ($m in $t2.GetMethods([System.Reflection.BindingFlags]::Static -bor [System.Reflection.BindingFlags]::Public -bor [System.Reflection.BindingFlags]::NonPublic -bor [System.Reflection.BindingFlags]::DeclaredOnly) | Sort-Object Name) {
            Write-Output ('    {0,-96} [{1}]' -f $m.ToString(), (Mods $m))
        }
    }
}
