"""Helper de MAJ silencieux — aucun shell / aucune fenêtre DOS.

Lancé depuis l’exe extrait dans le staging ({install}\\updates\\…), pas depuis l’install :
  <staging>\\Linkora.exe --linkora-updater <staging> <pid_parent> <dossier_install>

Ainsi les fichiers installés ne sont pas verrouillés par le helper.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

_CREATE_NO_WINDOW = 0x08000000
_CREATE_NEW_PROCESS_GROUP = 0x00000200


def _log_path(staging: Path | None = None) -> Path:
    """Log dans {install}/updates/linkora-update.log (plus %TEMP%)."""
    try:
        if staging is not None:
            # staging = …/updates/linkora-upd-xxx → parent = updates/
            parent = staging.resolve().parent
            if parent.name.lower() == "updates":
                return parent / "linkora-update.log"
            return parent / "updates" / "linkora-update.log"
    except Exception:
        pass
    try:
        from paths import UPDATES_DIR

        UPDATES_DIR.mkdir(parents=True, exist_ok=True)
        return UPDATES_DIR / "linkora-update.log"
    except Exception:
        return Path(os.environ.get("TEMP") or os.environ.get("TMP") or ".") / "linkora-update.log"


def _log(msg: str, staging: Path | None = None) -> None:
    try:
        path = _log_path(staging)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except OSError:
        pass


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes

            # PROCESS_QUERY_LIMITED_INFORMATION
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


def _replace_file(src: Path, dst: Path) -> None:
    """Copie en gérant les fichiers encore verrouillés (rename .old puis copie)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    last_err: Exception | None = None
    for attempt in range(10):
        try:
            if not dst.exists():
                shutil.copy2(src, dst)
                return
            try:
                shutil.copy2(src, dst)
                return
            except PermissionError:
                old = dst.with_name(dst.name + f".old{os.getpid()}")
                if old.exists():
                    try:
                        old.unlink()
                    except OSError:
                        pass
                dst.rename(old)
                try:
                    shutil.copy2(src, dst)
                finally:
                    try:
                        old.unlink()
                    except OSError:
                        pass
                return
        except Exception as exc:
            last_err = exc
            time.sleep(0.35 + attempt * 0.1)
    raise RuntimeError(f"Impossible de remplacer {dst}: {last_err}")


def _copy_tree_merge(src: Path, dst: Path) -> None:
    """Copie le contenu de src vers dst en ignorant data/ et updates/."""
    skip_top = {"data", "updates"}
    for root, dirs, files in os.walk(src):
        root_p = Path(root)
        rel = root_p.relative_to(src)
        parts = rel.parts
        if parts and parts[0].lower() in skip_top:
            dirs[:] = []
            continue
        # Ne pas descendre dans data/updates s’ils apparaissent dans le zip
        dirs[:] = [d for d in dirs if d.lower() not in skip_top]
        for name in files:
            _replace_file(root_p / name, dst / rel / name)


def run_helper(staging: str, parent_pid: int, install_dir: str | None = None) -> int:
    staging_p = Path(staging).resolve()
    if not staging_p.is_dir():
        _log(f"FAIL staging missing: {staging}", staging_p)
        return 2

    dest = Path(install_dir).resolve() if install_dir else Path(sys.executable).resolve().parent
    # Si le staging est sous dest/updates/, ne pas remonter install vers staging parent
    _log(
        f"helper start staging={staging_p} pid={parent_pid} dest={dest} exe={sys.executable}",
        staging_p,
    )

    # Attendre que l’appli principale libère les DLL
    deadline = time.time() + 120
    while _pid_alive(parent_pid) and time.time() < deadline:
        time.sleep(0.35)
    if _pid_alive(parent_pid):
        _log(
            f"WARN parent pid {parent_pid} still alive after timeout — continue anyway",
            staging_p,
        )
    time.sleep(1.2)

    try:
        _copy_tree_merge(staging_p, dest)
        _log("copy OK", staging_p)
    except Exception:
        _log("copy FAIL\n" + traceback.format_exc(), staging_p)
        return 3

    exe = dest / "Linkora.exe"
    if not exe.is_file():
        candidates = list(dest.glob("*.exe"))
        exe = candidates[0] if candidates else exe
    if not exe.is_file():
        _log(f"FAIL no exe in {dest}", staging_p)
        return 4

    flags = _CREATE_NEW_PROCESS_GROUP
    if sys.platform == "win32":
        flags |= _CREATE_NO_WINDOW
    try:
        subprocess.Popen(
            [str(exe)],
            cwd=str(dest),
            creationflags=flags if sys.platform == "win32" else 0,
            close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _log(f"relaunch OK {exe}", staging_p)
    except Exception:
        _log("relaunch FAIL\n" + traceback.format_exc(), staging_p)
        return 5

    shutil.rmtree(staging_p, ignore_errors=True)
    _log("done", staging_p)
    return 0
