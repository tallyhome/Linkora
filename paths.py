"""Chemins application (source Python ou .exe PyInstaller)."""

from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    """Dossier durable (à côté de Linkora.exe ou racine du projet)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_root() -> Path:
    """Ressources empaquetées (templates/static) — _MEIPASS en mode frozen."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


ROOT = app_root()
DATA_DIR = ROOT / "data"
VERSION_FILE = ROOT / "VERSION"
