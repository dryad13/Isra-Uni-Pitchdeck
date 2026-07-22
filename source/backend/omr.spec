# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for the On-Premises OMR System (one-folder build).
# Build on Windows from the backend/ directory:
#
#     pyinstaller --clean --noconfirm omr.spec
#
# Output: backend\dist\OMR\OMR.exe  (ship the whole backend\dist\OMR folder)
#
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []
binaries = []
hiddenimports = []

# The vendored OMRChecker engine is loaded dynamically at runtime (its source
# is shipped as data, not analyzed), so its third-party dependencies must be
# collected explicitly here.
for pkg in [
    "matplotlib",
    "rich",
    "jsonschema",
    "screeninfo",
    "dotmap",
    "deepmerge",
    "pandas",
    "webview",
]:
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

hiddenimports += collect_submodules("uvicorn")
hiddenimports += [
    "websockets",
    "openpyxl",
    "PIL",
    "pdf2image",
    "anyio",
    "sqlalchemy.dialects.sqlite",
]

# Read-only resources, mirrored under sys._MEIPASS at runtime (see app/paths.py).
datas += [
    ("../frontend/dist", "frontend/dist"),
    ("../samples", "samples"),
    ("../config.yaml", "."),
    ("../tests/fixtures/scans", "tests/fixtures/scans"),
    ("omr_engine", "omr_engine"),
    ("alembic", "alembic"),
    ("alembic.ini", "."),
]

a = Analysis(
    ["desktop.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="OMR",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="OMR",
)
