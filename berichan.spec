# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build spec for the desktop app.

Build:
    pip install pyinstaller
    pyinstaller berichan.spec

Produces a single windowed executable in dist/. Bundles the read-only assets
(sounds, QSS) and DELIBERATELY excludes .env so no developer credentials ever
ship inside the binary — each user authenticates through the setup wizard, and
their token is stored encrypted (DPAPI) on their own machine.
"""

block_cipher = None

a = Analysis(
    ["src/gui/__main__.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("assets/sounds/*.wav", "assets/sounds"),
        ("assets/data/*.json", "assets/data"),
        ("assets/sprites/*.png", "assets/sprites"),
    ],
    hiddenimports=["qasync"],
    hookspath=[],
    runtime_hooks=[],
    # Never bundle local credentials / caches.
    excludes=[".env"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="BerichanCrossTransfer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,            # windowed app, no console
    disable_windowed_traceback=False,
    icon=None,                # set to "assets/icon.ico" once an icon exists
)
