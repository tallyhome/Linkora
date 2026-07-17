"""Helper de MAJ silencieux — aucun shell / aucune fenêtre DOS.

Lancé ainsi (même Linkora.exe, console=False) :
  Linkora.exe --linkora-updater <dossier_staging> <pid_parent>
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

_CREATE_NO_WINDOW = 0x08000000
_DETACHED_PROCESS = 0x00000008
_CREATE_NEW_PROCESS_GROUP = 0x00000200


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes

            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _copy_tree_merge(src: Path, dst: Path) -> None:
    """Copie le contenu de src vers dst en ignorant data/."""
    for root, dirs, files in os.walk(src):
        root_p = Path(root)
        rel = root_p.relative_to(src)
        parts = rel.parts
        if parts and parts[0].lower() == "data":
            dirs[:] = []
            continue
        dest_dir = dst / rel
        dest_dir.mkdir(parents=True, exist_ok=True)
        for name in files:
            shutil.copy2(root_p / name, dest_dir / name)


def run_helper(staging: str, parent_pid: int) -> int:
    staging_p = Path(staging)
    if not staging_p.is_dir():
        return 2

    # Attendre que l’appli principale libère les DLL
    deadline = time.time() + 120
    while _pid_alive(parent_pid) and time.time() < deadline:
        time.sleep(0.35)
    time.sleep(1.0)

    dest = Path(sys.executable).resolve().parent
    try:
        _copy_tree_merge(staging_p, dest)
    except Exception:
        return 3

    # Relancer Linkora (sans arguments) — exe windowed = pas de console
    flags = _DETACHED_PROCESS | _CREATE_NEW_PROCESS_GROUP
    if sys.platform == "win32":
        flags |= _CREATE_NO_WINDOW
    try:
        subprocess.Popen(
            [sys.executable],
            cwd=str(dest),
            creationflags=flags if sys.platform == "win32" else 0,
            close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return 4

    shutil.rmtree(staging_p, ignore_errors=True)
    return 0
