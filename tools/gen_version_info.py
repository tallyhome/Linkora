#!/usr/bin/env python3
"""Génère tools/_file_version_info.txt pour PyInstaller (métadonnées PE Windows)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"
OUT = Path(__file__).resolve().parent / "_file_version_info.txt"

COMPANY = "Tallyhome"
PRODUCT = "Linkora"
DESCRIPTION = "Linkora — récupérateur de liens, débridage et bibliothèque"
COPYRIGHT = "Copyright © 2026 Tallyhome"
# Français (France) + Unicode
LANG_ID = 1036  # 0x040C
CODEPAGE = 1200  # 0x04B0
TABLE = "040C04B0"


def _tuple4(version: str) -> tuple[int, int, int, int]:
    parts = [int(p) for p in version.lstrip("vV").split(".") if p.isdigit()]
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])  # type: ignore[return-value]


def main() -> None:
    version = VERSION_FILE.read_text(encoding="utf-8").strip().lstrip("vV")
    major, minor, patch, build = _tuple4(version)
    filevers = f"({major}, {minor}, {patch}, {build})"
    # Chaînes version affichées
    file_ver_str = f"{major}.{minor}.{patch}.{build}"
    prod_ver_str = version

    content = f"""# UTF-8
#
# Auto-généré par tools/gen_version_info.py — ne pas éditer à la main.
# VSVersionInfo pour Linkora.exe (Authenticode / Explorateur Windows).

VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={filevers},
    prodvers={filevers},
    mask=0x3F,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '{TABLE}',
          [
            StringStruct('CompanyName', '{COMPANY}'),
            StringStruct('FileDescription', '{DESCRIPTION}'),
            StringStruct('FileVersion', '{file_ver_str}'),
            StringStruct('InternalName', 'Linkora'),
            StringStruct('LegalCopyright', '{COPYRIGHT}'),
            StringStruct('OriginalFilename', 'Linkora.exe'),
            StringStruct('ProductName', '{PRODUCT}'),
            StringStruct('ProductVersion', '{prod_ver_str}'),
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [{LANG_ID}, {CODEPAGE}])])
  ]
)
"""
    OUT.write_text(content, encoding="utf-8")
    print(f"OK -> {OUT} (v{version}, {COMPANY})")


if __name__ == "__main__":
    main()
