@echo off
rem build PKPM2PDMS.dll v2.1.0 (x86, CLR2/.NET3.5, C#3) against local PDMS 12.1.SP4 assemblies
rem source locator: works in-place (pdms-net\) and also when this script is
rem staged/copied elsewhere (e.g. the workspace root): it then finds the real
rem pdms-net dir via %HERE%pdms-net\ or %HERE%PKPM2PDMS*\pdms-net\.
setlocal
set CSC=C:\Windows\Microsoft.NET\Framework\v3.5\csc.exe
set PDMS=D:\AVEVA\Plant\PDMS12.1.SP4
set HERE=%~dp0

if not exist "%CSC%" set CSC=C:\Windows\Microsoft.NET\Framework64\v3.5\csc.exe

set SRC=%HERE%
if not exist "%SRC%PKPM2PDMSAddin.cs" set SRC=%HERE%pdms-net\
if not exist "%SRC%PKPM2PDMSAddin.cs" for /d %%D in ("%HERE%PKPM2PDMS*") do if exist "%%~fD\pdms-net\PKPM2PDMSAddin.cs" set SRC=%%~fD\pdms-net\
if not exist "%SRC%PKPM2PDMSAddin.cs" (
  echo BUILD FAILED: PKPM2PDMSAddin.cs not found next to build.cmd,
  echo   nor in "%HERE%pdms-net", nor in "%HERE%PKPM2PDMS*\pdms-net"
  exit /b 1
)
if not exist "%SRC%dist" mkdir "%SRC%dist"

rem ---- icon (produced by the C package into <tree-root>\<icon-dir>\pkpm2pdms.ico) ----
rem Resolved with ASCII-only literals: the icon DIRECTORY name is non-ASCII, so this
rem script never spells it out (a non-ASCII literal in a .cmd is read in the OEM
rem codepage and would be garbled).  Two candidate roots cover both layouts:
rem   %HERE%..\..\  = in-place pdms-net\ inside the tree   (..\<icon-dir>)
rem   %HERE%..\     = flat publish copy sitting at the tree root
set ICON=
if defined PKPM2PDMS_ICON set ICON=%PKPM2PDMS_ICON%
if not defined ICON for /d %%D in ("%HERE%..\..\*") do if exist "%%~fD\pkpm2pdms.ico" set ICON=%%~fD\pkpm2pdms.ico
if not defined ICON for /d %%D in ("%HERE%..\*") do if exist "%%~fD\pkpm2pdms.ico" set ICON=%%~fD\pkpm2pdms.ico
set ICONOPT=
if defined ICON if exist "%ICON%" set ICONOPT=/win32icon:"%ICON%" /resource:"%ICON%",pkpm2pdms.ico
if defined ICON (echo ICON: %ICON%) else (echo ICON: none - building without icon)

"%CSC%" /nologo /target:library /platform:x86 /optimize+ /utf8output /codepage:65001 ^
 /warnaserror- /out:"%SRC%dist\PKPM2PDMS.dll" %ICONOPT% ^
 /r:"%PDMS%\Aveva.ApplicationFramework.dll" ^
 /r:"%PDMS%\Aveva.ApplicationFramework.Presentation.dll" ^
 /r:"%PDMS%\Aveva.Pdms.Database.dll" ^
 /r:"%PDMS%\Aveva.Pdms.Utilities.dll" ^
 /r:"%PDMS%\Aveva.Pdms.Geometry.dll" ^
 /r:System.dll /r:System.Core.dll /r:System.Drawing.dll ^
 /r:System.Windows.Forms.dll ^
 "%SRC%PKPM2PDMSAddin.cs" "%SRC%PKPM2PDMSForm.cs" "%SRC%PmlBridge.cs" ^
 "%SRC%SiteProber.cs" ^
 "%SRC%EngineRunner.cs" "%SRC%PKLog.cs" "%SRC%AssemblyInfo.cs"

if errorlevel 1 (
  echo BUILD FAILED
  exit /b 1
)
echo BUILD OK: %SRC%dist\PKPM2PDMS.dll
