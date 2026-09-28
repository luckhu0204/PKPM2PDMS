# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:/AI_Work/PKPM数据解析/安装包程序/src/engine_launcher.py'],
    pathex=['D:/AI_Work/PKPM数据解析/安装包程序/assets/engine', 'D:/AI_Work/PKPM数据解析/安装包程序/src'],
    binaries=[],
    datas=[('D:/AI_Work/PKPM数据解析/安装包程序/assets/engine/secmap_extra.txt', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PKPM-JWD_引擎_v1',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
