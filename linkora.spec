# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — Linkora one-folder (Windows)."""

from pathlib import Path

block_cipher = None

# Métadonnées PE (générées par tools/gen_version_info.py avant le build)
_version_info = Path("tools/_file_version_info.txt")
if not _version_info.is_file():
    raise SystemExit(
        "tools/_file_version_info.txt manquant — lancez : python tools/gen_version_info.py"
    )

datas = [
    ("templates", "templates"),
    ("static", "static"),
    ("VERSION", "."),
    ("LICENSE", "."),
    ("README.md", "."),
    ("CHANGELOG.md", "."),
]

hiddenimports = [
    "flask",
    "requests",
    "bs4",
    "fpdf",
    "urllib3",
    "episode_gaps",
    "smart_naming",
    "library_scan",
    "network_shares",
    "tmdb",
    "updater",
    "update_helper",
    "paths",
    "settings",
    "storage",
    "debrid",
    "scraper",
]

a = Analysis(
    ["desktop.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports
    + [
        "webview",
        "webview.platforms.winforms",
        "clr",
        "desktop",
        "app",
    ],
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
    # Pas d’UPX : packers → faux positifs antivirus (heuristiques).
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="static/img/logo.ico",
    version=str(_version_info),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Linkora",
)
