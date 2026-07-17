"""Mise à jour automatique — GitHub releases (zip) ou site (latest.json)."""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from pathlib import Path
from typing import Any

import requests

from paths import ROOT, VERSION_FILE, DATA_DIR

GITHUB_REPO = "tallyhome/Linkora"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}"
USER_AGENT = "Linkora-Updater"

_state: dict[str, Any] = {
    "checked": False,
    "update_available": False,
    "current": "",
    "latest": "",
    "download_url": "",
    "applied": False,
    "needs_restart": False,
    "restarting": False,
    "error": "",
    "message": "",
    "source": "github",
    # Progression UI
    "busy": False,
    "phase": "",
    "percent": 0,
    "progress_message": "",
    "done": False,
}
_lock = threading.Lock()
_apply_lock = threading.Lock()

# Windows : process sans fenêtre
_CREATE_NO_WINDOW = 0x08000000
_CREATE_NEW_PROCESS_GROUP = 0x00000200


def read_version() -> str:
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def _parse_version(raw: str) -> tuple[int, ...]:
    text = (raw or "0").lstrip("vV").strip()
    parts: list[int] = []
    for chunk in text.split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:4])


def is_newer(remote: str, local: str) -> bool:
    return _parse_version(remote) > _parse_version(local)


def get_state() -> dict[str, Any]:
    with _lock:
        return {
            **_state,
            "current": _state.get("current") or read_version(),
            "repo": GITHUB_REPO,
            "frozen": bool(getattr(sys, "frozen", False)),
        }


def _set_state(**kwargs: Any) -> None:
    with _lock:
        _state.update(kwargs)


def _set_progress(phase: str, percent: int, message: str, **extra: Any) -> None:
    _set_state(
        phase=phase,
        percent=max(0, min(100, int(percent))),
        progress_message=message,
        message=message,
        **extra,
    )


def _headers() -> dict[str, str]:
    return {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}


def fetch_from_custom_url(manifest_url: str) -> dict[str, str] | None:
    """latest.json : { version, url, notes? }"""
    try:
        resp = requests.get(manifest_url, headers={"User-Agent": USER_AGENT}, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        version = str(data.get("version") or "").lstrip("vV").strip()
        url = str(data.get("url") or data.get("download_url") or "").strip()
        if version and url:
            return {"version": version, "url": url, "notes": str(data.get("notes") or "")}
    except (requests.RequestException, ValueError, TypeError):
        return None
    return None


def fetch_github_release() -> dict[str, str] | None:
    """Dernière release GitHub + asset zip Windows si présent."""
    try:
        resp = requests.get(f"{GITHUB_API}/releases/latest", headers=_headers(), timeout=15)
        if resp.status_code != 200:
            return _fetch_github_tag_fallback()
        data = resp.json()
        tag = (data.get("tag_name") or "").strip().lstrip("vV")
        if not tag:
            return None
        zip_url = ""
        for asset in data.get("assets") or []:
            name = (asset.get("name") or "").lower()
            if name.endswith(".zip") and ("windows" in name or "linkora" in name or "win" in name):
                zip_url = asset.get("browser_download_url") or ""
                break
        if not zip_url:
            for asset in data.get("assets") or []:
                if (asset.get("name") or "").lower().endswith(".zip"):
                    zip_url = asset.get("browser_download_url") or ""
                    break
        if not zip_url:
            zip_url = f"https://github.com/{GITHUB_REPO}/archive/refs/tags/v{tag}.zip"
        return {"version": tag, "url": zip_url, "notes": (data.get("body") or "")[:500]}
    except requests.RequestException:
        return _fetch_github_tag_fallback()


def _fetch_github_tag_fallback() -> dict[str, str] | None:
    try:
        resp = requests.get(
            f"{GITHUB_API}/tags",
            headers=_headers(),
            params={"per_page": 5},
            timeout=12,
        )
        if resp.status_code != 200:
            return None
        tags = resp.json()
        if not isinstance(tags, list) or not tags:
            return None
        name = (tags[0].get("name") or "").strip().lstrip("vV")
        if not name:
            return None
        return {
            "version": name,
            "url": f"https://github.com/{GITHUB_REPO}/archive/refs/tags/v{name}.zip",
            "notes": "",
        }
    except requests.RequestException:
        return None


def check_for_update(manifest_url: str | None = None) -> dict[str, Any]:
    current = read_version()
    _set_state(current=current, checked=True, error="", message="", download_url="")

    info = None
    source = "github"
    if manifest_url:
        info = fetch_from_custom_url(manifest_url)
        source = "custom"
    if not info:
        info = fetch_github_release()
        source = "github"

    if not info:
        _set_state(
            latest="",
            update_available=False,
            source=source,
            message="Aucune version disponible (GitHub / site).",
        )
        return get_state()

    latest = info["version"]
    available = is_newer(latest, current)
    _set_state(
        latest=latest,
        download_url=info.get("url") or "",
        update_available=available,
        source=source,
        message=(
            f"Mise à jour {latest} disponible."
            if available
            else f"Vous êtes à jour ({current})."
        ),
    )
    return get_state()


def _is_git_repo() -> bool:
    return (ROOT / ".git").is_dir() and not getattr(sys, "frozen", False)


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _apply_via_git(tag: str) -> None:
    fetch = _git("fetch", "--tags", "origin")
    if fetch.returncode != 0:
        raise RuntimeError(fetch.stderr.strip() or "git fetch a échoué.")
    pull = _git("pull", "--ff-only", "origin", "HEAD")
    if pull.returncode != 0:
        for ref in (f"v{tag}", tag):
            checkout = _git("checkout", ref)
            if checkout.returncode == 0:
                return
        raise RuntimeError((pull.stderr or "git pull/checkout a échoué.").strip())


def _download_zip(url: str) -> bytes:
    """Télécharge le zip en mettant à jour la barre de progression."""
    _set_progress("download", 8, "Connexion au serveur de téléchargement…")
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=180, stream=True)
    if resp.status_code != 200:
        raise RuntimeError(f"Téléchargement impossible (HTTP {resp.status_code}).")

    total = int(resp.headers.get("Content-Length") or 0)
    chunks: list[bytes] = []
    done = 0
    last_pct = -1
    for chunk in resp.iter_content(chunk_size=256 * 1024):
        if not chunk:
            continue
        chunks.append(chunk)
        done += len(chunk)
        if total > 0:
            pct = 8 + int(62 * done / total)  # 8 → 70
            if pct != last_pct:
                mb = done / (1024 * 1024)
                total_mb = total / (1024 * 1024)
                _set_progress(
                    "download",
                    pct,
                    f"Téléchargement… {mb:.1f} / {total_mb:.1f} Mo",
                )
                last_pct = pct
        else:
            mb = done / (1024 * 1024)
            _set_progress("download", min(68, 8 + done // (512 * 1024)), f"Téléchargement… {mb:.1f} Mo")

    raw = b"".join(chunks)
    if raw[:2] != b"PK":
        raise RuntimeError("Le fichier téléchargé n’est pas un zip valide.")
    _set_progress("download", 70, "Téléchargement terminé.")
    return raw


def _zip_root_prefix(names: list[str]) -> str:
    if not names:
        return ""
    first = names[0]
    if "/" not in first:
        return ""
    candidate = first.split("/", 1)[0] + "/"
    if all(n.startswith(candidate) or n == candidate.rstrip("/") for n in names):
        return candidate
    return ""


def _extract_zip_to(raw: bytes, dest: Path, *, preserve_top: set[str] | None = None) -> None:
    preserve = preserve_top or set()
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        if not names:
            raise RuntimeError("Archive vide.")
        root_prefix = _zip_root_prefix(zf.namelist())
        total = len(names)
        for idx, info in enumerate(zf.infolist(), start=1):
            if info.is_dir():
                continue
            rel = info.filename
            if root_prefix and rel.startswith(root_prefix):
                rel_path = rel[len(root_prefix) :]
            else:
                rel_path = rel
            if not rel_path or rel_path.endswith("/"):
                continue
            top = rel_path.split("/", 1)[0]
            if top in preserve:
                continue
            target = dest / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
            if total:
                pct = 70 + int(18 * idx / total)  # 70 → 88
                if idx == 1 or idx == total or idx % 25 == 0:
                    _set_progress("extract", pct, f"Extraction… {idx}/{total} fichiers")


def _extract_zip_bytes(raw: bytes) -> None:
    _extract_zip_to(
        raw,
        ROOT,
        preserve_top={"data", ".git", ".venv", "venv", "__pycache__", "logs"},
    )


def _schedule_frozen_replace(staging: Path, target_version: str) -> None:
    """
    Lance le helper depuis l’exe du staging (TEMP), pas depuis l’install.
    Sinon Linkora.exe / _internal restent verrouillés → copie impossible.
    """
    helper_exe = staging / "Linkora.exe"
    if not helper_exe.is_file():
        found = list(staging.glob("*.exe"))
        if not found:
            raise RuntimeError("Exe de MAJ introuvable dans le staging.")
        helper_exe = found[0]

    install_dir = str(ROOT.resolve())
    flags = _CREATE_NEW_PROCESS_GROUP | _CREATE_NO_WINDOW
    # Pas de DETACHED_PROCESS : certains antivirus / Win11 cassent le spawn.
    subprocess.Popen(
        [
            str(helper_exe.resolve()),
            "--linkora-updater",
            str(staging.resolve()),
            str(os.getpid()),
            install_dir,
        ],
        cwd=str(staging.resolve()),
        creationflags=flags,
        close_fds=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    def _exit_soon() -> None:
        # Laisser le temps à l’UI d’afficher « redémarrage… »
        time.sleep(1.2)
        os._exit(0)

    threading.Thread(target=_exit_soon, daemon=True, name="linkora-exit-after-update").start()


def _apply_frozen_zip(raw: bytes, target_version: str) -> None:
    staging = Path(tempfile.mkdtemp(prefix="linkora-upd-"))
    try:
        _set_progress("extract", 72, "Extraction de la mise à jour…")
        _extract_zip_to(raw, staging, preserve_top=set())
        (staging / "VERSION").write_text(target_version + "\n", encoding="utf-8")
        if not (staging / "Linkora.exe").is_file() and not list(staging.glob("*.exe")):
            raise RuntimeError(
                "Le zip de MAJ ne contient pas Linkora.exe. "
                "Utilisez l’asset Windows (Linkora-windows-vX.Y.Z.zip)."
            )
        _set_progress("restart", 95, "Préparation du redémarrage…")
        _schedule_frozen_replace(staging, target_version)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _run_apply(
    tag: str | None,
    download_url: str | None,
    manifest_url: str | None,
) -> None:
    try:
        _set_progress("prepare", 3, "Préparation de la mise à jour…", busy=True, done=False, error="")
        state = get_state()
        if not state.get("checked") or manifest_url:
            _set_progress("prepare", 5, "Vérification de la version…")
            state = check_for_update(manifest_url)

        target = (tag or state.get("latest") or "").lstrip("vV")
        url = download_url or state.get("download_url") or ""
        current = read_version()
        frozen = bool(getattr(sys, "frozen", False))

        if not target:
            raise RuntimeError("Aucune version cible.")
        if not is_newer(target, current) and tag is None and not download_url:
            _set_state(
                message=f"Déjà à jour ({current}).",
                applied=False,
                busy=False,
                done=True,
                percent=100,
                phase="done",
                progress_message=f"Déjà à jour ({current}).",
            )
            return

        DATA_DIR.mkdir(parents=True, exist_ok=True)

        if _is_git_repo() and not frozen and not (url or "").endswith(".zip"):
            _set_progress("apply", 40, f"Mise à jour git vers {target}…")
            _apply_via_git(target)
            VERSION_FILE.write_text(target + "\n", encoding="utf-8")
            _set_state(
                applied=True,
                needs_restart=True,
                restarting=False,
                update_available=False,
                current=target,
                latest=target,
                error="",
                busy=False,
                done=True,
                percent=100,
                phase="done",
                message=f"Mis à jour vers {target}. Redémarrez Linkora.",
                progress_message=f"Mis à jour vers {target}. Redémarrez Linkora.",
            )
            return

        if not url:
            raise RuntimeError("Pas d’URL de téléchargement pour la MAJ.")

        raw = _download_zip(url)
        if frozen:
            _apply_frozen_zip(raw, target)
            _set_state(
                applied=True,
                needs_restart=True,
                restarting=True,
                update_available=False,
                current=target,
                latest=target,
                error="",
                busy=True,
                done=True,
                percent=100,
                phase="restart",
                message=f"Redémarrage vers {target}…",
                progress_message="Installation terminée — redémarrage automatique…",
            )
        else:
            _set_progress("extract", 75, "Installation des fichiers…")
            _extract_zip_bytes(raw)
            VERSION_FILE.write_text(target + "\n", encoding="utf-8")
            _set_state(
                applied=True,
                needs_restart=True,
                restarting=False,
                update_available=False,
                current=target,
                latest=target,
                error="",
                busy=False,
                done=True,
                percent=100,
                phase="done",
                message=f"Mis à jour vers {target}. Redémarrez Linkora.",
                progress_message=f"Mis à jour vers {target}. Redémarrez Linkora.",
            )
    except Exception as exc:
        msg = str(exc)
        if "Permission denied" in msg or "WinError 5" in msg or "[Errno 13]" in msg:
            msg = (
                f"{msg} — fermez Linkora et installez le Setup manuellement une fois ; "
                "les MAJ suivantes se feront automatiquement."
            )
        _set_state(
            error=msg,
            applied=False,
            busy=False,
            done=True,
            restarting=False,
            phase="error",
            percent=100,
            progress_message=msg,
            message="",
        )


def apply_update(
    tag: str | None = None,
    *,
    download_url: str | None = None,
    manifest_url: str | None = None,
    background: bool = True,
) -> dict[str, Any]:
    """
    Lance la MAJ. En mode background (défaut), retourne tout de suite pour
    que l’UI puisse afficher la progression via get_state() / /api/update/progress.
    """
    if not _apply_lock.acquire(blocking=False):
        return get_state()

    def worker() -> None:
        try:
            _run_apply(tag, download_url, manifest_url)
        finally:
            _apply_lock.release()

    if background:
        _set_progress("prepare", 1, "Démarrage de la mise à jour…", busy=True, done=False, error="")
        threading.Thread(target=worker, daemon=True, name="linkora-apply").start()
        return get_state()

    try:
        _run_apply(tag, download_url, manifest_url)
    finally:
        _apply_lock.release()
    return get_state()


def startup_autoupdate(*, enabled: bool = True, manifest_url: str | None = None) -> None:
    def worker() -> None:
        try:
            state = check_for_update(manifest_url)
            if enabled and state.get("update_available") and not getattr(sys, "frozen", False):
                apply_update(state.get("latest"), manifest_url=manifest_url, background=True)
        except Exception as exc:
            _set_state(error=str(exc))

    threading.Thread(target=worker, daemon=True, name="linkora-updater").start()
