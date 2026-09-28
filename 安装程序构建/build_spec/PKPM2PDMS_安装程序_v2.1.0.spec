# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/安装程序构建/src/installer_main.py'],
    pathex=['D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/安装程序构建/src'],
    binaries=[],
    datas=[('D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/图标/pkpm2pdms.ico', 'ico'), ('D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/插件包/pdms', 'pdms'), ('D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/插件包/docs', 'docs')],
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
    name='PKPM2PDMS_安装程序_v2.1.0',
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
    icon=['D:/AI_Work/PKPM数据解析/PKPM2PDMS_v2.1.0/图标/pkpm2pdms.ico'],
)
