# -*- coding: utf-8 -*-
"""Write pdms-net build.cmd (CRLF + ASCII, contract p.2 verbatim) and
pkpmjwd.uic (UTF-8 no BOM + LF, tgtext.uic skeleton per contract F.3),
then copy the uic into dist/."""
import io, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]          # pdms-net/

BUILD_CMD = "\r\n".join([
    "@echo off",
    "rem build PKPMJWD.dll (x86, CLR2/.NET3.5, C#3) against local PDMS 12.1.SP4 assemblies",
    "rem source locator: works in-place (pdms-net\\) and also when this script is",
    "rem staged/copied elsewhere (e.g. the workspace root): it then finds the real",
    "rem pdms-net dir via %HERE%pdms-net\\ or %HERE%PKPM-JWD*\\pdms-net\\.",
    "setlocal",
    r"set CSC=C:\Windows\Microsoft.NET\Framework\v3.5\csc.exe",
    r"set PDMS=D:\AVEVA\Plant\PDMS12.1.SP4",
    "set HERE=%~dp0",
    "",
    'if not exist "%CSC%" set CSC=C:\\Windows\\Microsoft.NET\\Framework64\\v3.5\\csc.exe',
    "",
    'set SRC=%HERE%',
    'if not exist "%SRC%PKPMJWDAddin.cs" set SRC=%HERE%pdms-net\\',
    'if not exist "%SRC%PKPMJWDAddin.cs" for /d %%D in ("%HERE%PKPM-JWD*") '
    'do if exist "%%~fD\\pdms-net\\PKPMJWDAddin.cs" set SRC=%%~fD\\pdms-net\\',
    'if not exist "%SRC%PKPMJWDAddin.cs" (',
    "  echo BUILD FAILED: PKPMJWDAddin.cs not found next to build.cmd,",
    '  echo   nor in "%HERE%pdms-net", nor in "%HERE%PKPM-JWD*\\pdms-net"',
    "  exit /b 1",
    ")",
    'if not exist "%SRC%dist" mkdir "%SRC%dist"',
    "",
    '"%CSC%" /nologo /target:library /platform:x86 /optimize+ /utf8output /codepage:65001 ^',
    ' /warnaserror- /out:"%SRC%dist\\PKPMJWD.dll" ^',
    ' /r:"%PDMS%\\Aveva.ApplicationFramework.dll" ^',
    ' /r:"%PDMS%\\Aveva.ApplicationFramework.Presentation.dll" ^',
    ' /r:"%PDMS%\\Aveva.Pdms.Database.dll" ^',
    ' /r:"%PDMS%\\Aveva.Pdms.Utilities.dll" ^',
    ' /r:"%PDMS%\\Aveva.Pdms.Geometry.dll" ^',
    " /r:System.dll /r:System.Core.dll /r:System.Drawing.dll ^",
    " /r:System.Windows.Forms.dll ^",
    ' "%SRC%PKPMJWDAddin.cs" "%SRC%PKPMJWDForm.cs" "%SRC%PmlBridge.cs" ^',
    ' "%SRC%EngineRunner.cs" "%SRC%PKLog.cs"',
    "",
    "if errorlevel 1 (",
    "  echo BUILD FAILED",
    "  exit /b 1",
    ")",
    "echo BUILD OK: %SRC%dist\\PKPMJWD.dll",
]) + "\r\n"

UIC = "\n".join([
    '<?xml version="1.0" encoding="utf-8"?>',
    '<UserInterfaceCustomization xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
    'xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns="www.aveva.com">',
    "  <Version>1.0</Version>",
    "  <Tools>",
    '    <ButtonTool Name="PKPMJWD.Open">',
    "      <Command>",
    "        <Type>Instance</Type>",
    "        <Key>PKPMJWD.OpenTools</Key>",
    "        <Arguments />",
    "      </Command>",
    "      <Image />",
    "      <Caption>PKPM JWD \u5bfc\u5165\u5bfc\u51fa</Caption>",
    "      <DisplayStyle>Default</DisplayStyle>",
    "    </ButtonTool>",
    '    <MenuTool Name="PKPMJWD.Menu">',
    "      <Image />",
    "      <Caption>PKPM JWD</Caption>",
    "      <DisplayStyle>Default</DisplayStyle>",
    "      <Tools>",
    '        <Tool Name="PKPMJWD.Open" />',
    "      </Tools>",
    "    </MenuTool>",
    "  </Tools>",
    "  <InstanceTools />",
    "  <MenuBar>",
    '    <Tool Name="PKPMJWD.Menu" />',
    "  </MenuBar>",
    "  <CommandBars />",
    "  <TaskPanes />",
    "  <ContextMenus />",
    "  <AreaLeftTools />",
    "  <AreaRightTools />",
    "  <FooterTools />",
    "  <QATTools>",
    '    <Tool Name="PKPMJWD.Open" />',
    "  </QATTools>",
    "  <ContextualTabGroups />",
    "  <TabToolbarTools />",
    "  <Tabs />",
    "  <MiniToolbarTools />",
    "</UserInterfaceCustomization>",
]) + "\n"


def main():
    p1 = HERE / "build.cmd"
    p1.write_bytes(BUILD_CMD.encode("ascii"))
    p2 = HERE / "pkpmjwd.uic"
    p2.write_bytes(UIC.encode("utf-8"))             # UTF-8 no BOM + LF (F.3)
    dist = HERE / "dist"
    dist.mkdir(exist_ok=True)
    shutil.copyfile(p2, dist / "pkpmjwd.uic")
    for p in (p1, p2, dist / "pkpmjwd.uic"):
        b = p.read_bytes()
        print(p.name, len(b), "bytes, BOM:", b[:3] == b"\xef\xbb\xbf",
              "CRLF:", b.count(b"\r\n"), "LF:", b.count(b"\n"))
    # build.cmd must be pure ASCII (contract g-6)
    BUILD_CMD.encode("ascii")
    print("build.cmd is pure ASCII: True")
    return 0


if __name__ == "__main__":
    sys.exit(main())
