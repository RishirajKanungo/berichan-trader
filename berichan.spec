# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build spec for the desktop app — optimized for a small, single-file,
non-intrusive executable.

Build:
    pip install pyinstaller
    pyinstaller berichan.spec
    # result: dist/BerichanCrossTransfer.exe  (one self-contained file)

Size strategy: the app only uses QtCore/QtGui/QtWidgets/QtMultimedia, but a full
PySide6 install also ships QtWebEngine, QML/Quick, Qt3D, Charts, etc. — hundreds
of MB. We exclude everything we don't use (QtWebEngine alone is the biggest win)
and UPX-compress, while leaving the startup-critical Qt DLLs uncompressed so the
app stays reliable. The bundled data/sprites are tiny (~5 MB) by comparison.

The build DELIBERATELY excludes .env so no developer credentials ship inside the
binary — each user authenticates via the setup wizard and their token is stored
encrypted (DPAPI) in %APPDATA% on their own machine.
"""

block_cipher = None

# Qt modules (and a few stdlib libs) we never import — excluding them is the main
# size reduction. Keep QtMultimedia (sound) + QtNetwork (its dependency).
_EXCLUDES = [
    # Heavy Qt add-ons we don't use
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtWebChannel", "PySide6.QtWebSockets", "PySide6.QtHttpServer",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQuickWidgets",
    "PySide6.QtQuickControls2",
    "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DInput", "PySide6.Qt3DLogic",
    "PySide6.Qt3DAnimation", "PySide6.Qt3DExtras",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtGraphs",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtDesigner", "PySide6.QtUiTools",
    "PySide6.QtHelp",
    "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtPositioning",
    "PySide6.QtLocation", "PySide6.QtSerialPort", "PySide6.QtSerialBus",
    "PySide6.QtSensors",
    "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets",
    "PySide6.QtSvg", "PySide6.QtSvgWidgets",
    "PySide6.QtPrintSupport", "PySide6.QtXml", "PySide6.QtConcurrent",
    "PySide6.QtRemoteObjects", "PySide6.QtScxml", "PySide6.QtStateMachine",
    "PySide6.QtTextToSpeech", "PySide6.QtSpatialAudio", "PySide6.QtMultimediaWidgets",
    # stdlib / misc we don't ship  (note: do NOT exclude distutils — PyInstaller's
    # setuptools hooks alias it and error out if it's excluded)
    "tkinter", "unittest", "test", "pydoc_data", "lib2to3",
    "numpy", "PIL", "PyQt5", "PyQt6",
]

a = Analysis(
    ["berichan_app.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("assets/sounds/*.wav", "assets/sounds"),
        ("assets/data/*.json", "assets/data"),
        ("assets/sprites/*.png", "assets/sprites"),
        ("assets/items/*.png", "assets/items"),
        ("assets/types/*.gif", "assets/types"),
        ("assets/categories/*.png", "assets/categories"),
    ],
    hiddenimports=["qasync"],
    hookspath=[],
    runtime_hooks=[],
    excludes=_EXCLUDES,
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
    # Leave startup-critical DLLs uncompressed — UPX on these can break launch.
    upx_exclude=[
        "Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll", "Qt6Multimedia.dll",
        "Qt6Network.dll", "python3.dll", "vcruntime140.dll", "vcruntime140_1.dll",
    ],
    runtime_tmpdir=None,
    console=False,            # windowed app, no console window
    disable_windowed_traceback=False,
    icon=None,                # set to "assets/icon.ico" once an icon exists
)
