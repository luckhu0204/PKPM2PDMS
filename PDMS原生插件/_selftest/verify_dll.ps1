# verify_dll.ps1 - acceptance check for pdms-net\dist\PKPM2PDMS.dll
# 1) [System.Reflection.AssemblyName]::GetAssemblyName()  (ask-named check)
# 2) ReflectionOnlyLoadFrom -> ImageRuntimeVersion (CLR version)
# 3) manual PE header parse -> machine type (0x014c = I386 x86)
$ErrorActionPreference = 'Stop'
$dll = Join-Path $PSScriptRoot '..\dist\PKPM2PDMS.dll'
if (-not (Test-Path $dll)) { Write-Host 'FAIL: DLL not found'; exit 1 }
$item = Get-Item $dll
Write-Host ('DLL path : ' + $item.FullName)
Write-Host ('DLL size : ' + $item.Length + ' bytes')

$an = [System.Reflection.AssemblyName]::GetAssemblyName($dll)
$tok = '?'
if ($an.FullName -match 'PublicKeyToken=([0-9a-f]*|null)') { $tok = $Matches[1] }
Write-Host ('GetAssemblyName: Name=' + $an.Name + ' Version=' + $an.Version.ToString() + ' ProcessorArchitecture=' + $an.ProcessorArchitecture + ' PublicKeyToken=' + $tok)

$asm = [System.Reflection.Assembly]::ReflectionOnlyLoadFrom((Resolve-Path $dll))
Write-Host ('ImageRuntimeVersion (CLR): ' + $asm.ImageRuntimeVersion)
Write-Host 'Referenced Aveva assemblies:'
foreach ($r in $asm.GetReferencedAssemblies()) { if ($r.Name -like 'Aveva*') { Write-Host ('  -> ' + $r.FullName) } }

$b = [IO.File]::ReadAllBytes((Resolve-Path $dll))
$e_lfanew = [BitConverter]::ToInt32($b, 0x3C)
$machine = [BitConverter]::ToUInt16($b, $e_lfanew + 4)
$machineTxt = ' (NOT I386!)'
if ($machine -eq 0x14C) { $machineTxt = ' (I386, x86)' }
Write-Host ('PE: e_lfanew=0x' + $e_lfanew.ToString('X') + ' machine=0x' + $machine.ToString('X') + $machineTxt)

$ok = ($asm.ImageRuntimeVersion -eq 'v2.0.50727') -and ($machine -eq 0x14C) -and ($an.Name -eq 'PKPM2PDMS')
if ($ok) { Write-Host 'RESULT: OK (CLR v2.0.50727 + I386 + name PKPM2PDMS)'; exit 0 }
Write-Host 'RESULT: FAIL'
exit 2
