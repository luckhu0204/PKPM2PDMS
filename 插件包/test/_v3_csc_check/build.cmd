@echo off
rem compile probe for CONTRACT section p.2 (same shape as TGTEXT backup build.cmd)
setlocal
set CSC=C:\Windows\Microsoft.NET\Framework\v3.5\csc.exe
set PDMS=D:\AVEVA\Plant\PDMS12.1.SP4
set HERE=%~dp0

if not exist "%CSC%" set CSC=C:\Windows\Microsoft.NET\Framework64\v3.5\csc.exe

"%CSC%" /nologo /target:library /platform:x86 /optimize+ /utf8output /codepage:65001 ^
 /warnaserror- /out:"%HERE%stub_pkpmjwd.dll" ^
 /r:"%PDMS%\Aveva.ApplicationFramework.dll" ^
 /r:"%PDMS%\Aveva.ApplicationFramework.Presentation.dll" ^
 /r:"%PDMS%\Aveva.Pdms.Database.dll" ^
 /r:"%PDMS%\Aveva.Pdms.Utilities.dll" ^
 /r:"%PDMS%\Aveva.Pdms.Geometry.dll" ^
 /r:System.dll /r:System.Core.dll /r:System.Drawing.dll ^
 /r:System.Windows.Forms.dll ^
 "%HERE%stub_pkpmjwd.cs"

if errorlevel 1 (
  echo BUILD FAILED
  exit /b 1
)
echo BUILD OK: %HERE%stub_pkpmjwd.dll
