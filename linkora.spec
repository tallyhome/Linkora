# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — Linkora one-folder (Windows)."""

from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas = [
    ("templates", "templates"),
    ("static", "static"),
    ("VERSION", "."),
    ("LICENSE", "."),
    ("README.md", "."),
]

hiddenimports = [
    "flask",
    "requests",
    "bs4",
    "fpdf",
    "urllib3",
    "episode_gaps",
    "smart_naming",
    "updater",
    "paths",
    "settings",
    "storage",
    "debrid",
    "scraper",
]

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Linkora",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="static/img/logo.png",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Linkora",
)
