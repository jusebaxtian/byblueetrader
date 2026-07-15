# -*- mode: python ; coding: utf-8 -*-
# Build: pyinstaller byblue.spec
# Output: dist/ByblueTrader/ByblueTrader.exe (onedir build)

import os

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
ICON_PATH = "resources/icon.ico"

a = Analysis(
    ["byblue/main.py"],
    pathex=["."],
    binaries=[],
    datas=[("byblue/db/schema.sql", "byblue/db")],
    hiddenimports=collect_submodules("iqoptionapi") + ["websocket"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ByblueTrader",
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=ICON_PATH if os.path.exists(ICON_PATH) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="ByblueTrader",
)
