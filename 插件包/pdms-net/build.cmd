@echo off
rem build PKPMJWD.dll (x86, CLR2/.NET3.5, C#3) against local PDMS 12.1.SP4 assemblies
rem source locator: works in-place (pdms-net\) and also when this script is
rem staged/copied elsewhere (e.g. the workspace root): it then finds the real
rem pdms-net dir via %HERE%pdms-net\ or %HERE%PKPM-JWD*\pdms-net\.
setlocal
set CSC=C:\Windows\Microsoft.NET\Framework\v3.5\csc.exe
set PDMS=D:\AVEVA\Plant\PDMS12.1.SP4
set HERE=%~dp0

if not exist "%CSC%" set CSC=C:\Windows\Microsoft.NET\Framework64\v3.5\csc.exe

set SRC=%HERE%
if not exist "%SRC%PKPMJWDAddin.cs" set SRC=%HERE%pdms-net\
if not exist "%SRC%PKPMJWDAddin.cs" for /d %%D in ("%HERE%PKPM-JWD*") do if exist "%%~fD\pdms-net\PKPMJWDAddin.cs" set SRC=%%~fD\pdms-net\
if not exist "%SRC%PKPMJWDAddin.cs" (
  echo BUILD FAILED: PKPMJWDAddin.cs not found next to build.cmd,
  echo   nor in "%HERE%pdms-net", nor in "%HERE%PKPM-JWD*\pdms-net"
  exit /b 1
)
if not exist "%SRC%dist" mkdir "%SRC%dist"

"%CSC%" /nologo /target:library /platform:x86 /optimize+ /utf8output /codepage:65001 ^
 /warnaserror- /out:"%SRC%dist\PKPMJWD.dll" ^
 /r:"%PDMS%\Aveva.ApplicationFramework.dll" ^
 /r:"%PDMS%\Aveva.ApplicationFramework.Presentation.dll" ^
 /r:"%PDMS%\Aveva.Pdms.Database.dll" ^
 /r:"%PDMS%\Aveva.Pdms.Utilities.dll" ^
 /r:"%PDMS%\Aveva.Pdms.Geometry.dll" ^
 /r:System.dll /r:System.Core.dll /r:System.Drawing.dll ^
 /r:System.Windows.Forms.dll ^
 "%SRC%PKPMJWDAddin.cs" "%SRC%PKPMJWDForm.cs" "%SRC%PmlBridge.cs" ^
 "%SRC%EngineRunner.cs" "%SRC%PKLog.cs"

if errorlevel 1 (
  echo BUILD FAILED
  exit /b 1
)
echo BUILD OK: %SRC%dist\PKPMJWD.dll
