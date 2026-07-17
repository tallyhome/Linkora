"""Mise à jour automatique depuis GitHub (tallyhome/Linkora)."""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import threading
import zipfile
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent
VERSION_FILE = ROOT / "VERSION"
GITHUB_REPO = "tallyhome/Linkora"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}"
USER_AGENT = "Linkora-Updater"

_state: dict[str, Any] = {
    "checked": False,
    "update_available": False,
    "current": "",
    "latest": "",
    "applied": False,
    "needs_restart": False,
    "error": "",
    "message": "",
}
_lock = threading.Lock()


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
        }


def _set_state(**kwargs: Any) -> None:
    with _lock:
        _state.update(kwargs)


def fetch_latest_tag() -> str | None:
    """Retourne le dernier tag GitHub (ex: 1.0.1) ou None."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    # 1) Releases
    try:
        resp = requests.get(
            f"{GITHUB_API}/releases/latest",
            headers=headers,
            timeout=12,
        )
        if resp.status_code == 200:
            data = resp.json()
            tag = (data.get("tag_name") or "").strip()
            if tag:
                return tag.lstrip("vV")
    except requests.RequestException:
        pass

    # 2) Tags
    try:
        resp = requests.get(
            f"{GITHUB_API}/tags",
            headers=headers,
            params={"per_page": 10},
            timeout=12,
        )
        if resp.status_code == 200:
            tags = resp.json()
            if isinstance(tags, list) and tags:
                name = (tags[0].get("name") or "").strip()
                if name:
                    return name.lstrip("vV")
    except requests.RequestException:
        pass
    return None


def check_for_update() -> dict[str, Any]:
    current = read_version()
    _set_state(current=current, checked=True, error="", message="")
    try:
        latest = fetch_latest_tag()
    except Exception as exc:
        _set_state(error=str(exc), update_available=False)
        return get_state()

    if not latest:
        _set_state(
            latest="",
            update_available=False,
            message="Aucune version publiée sur GitHub pour le moment.",
        )
        return get_state()

    available = is_newer(latest, current)
    _set_state(
        latest=latest,
        update_available=available,
        message=(
            f"Mise à jour {latest} disponible."
            if available
            else f"Vous êtes à jour ({current})."
        ),
    )
    return get_state()


def _is_git_repo() -> bool:
    return (ROOT / ".git").is_dir()


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

    # Préférer pull sur la branche suivie si possible, sinon checkout du tag
    pull = _git("pull", "--ff-only", "origin", "HEAD")
    if pull.returncode != 0:
        checkout = _git("checkout", f"v{tag}" if not tag.startswith("v") else tag)
        if checkout.returncode != 0:
            checkout = _git("checkout", tag)
        if checkout.returncode != 0:
            raise RuntimeError(
                (pull.stderr or checkout.stderr or "git pull/checkout a échoué.").strip()
            )


def _apply_via_zip(tag: str) -> None:
    tag_ref = tag if tag.startswith("v") else f"v{tag}"
    urls = [
        f"https://github.com/{GITHUB_REPO}/archive/refs/tags/{tag_ref}.zip",
        f"https://github.com/{GITHUB_REPO}/archive/refs/tags/{tag}.zip",
        f"https://github.com/{GITHUB_REPO}/archive/refs/heads/main.zip",
    ]
    headers = {"User-Agent": USER_AGENT}
    raw: bytes | None = None
    last_err = ""
    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=60)
            if resp.status_code == 200 and resp.content[:2] == b"PK":
                raw = resp.content
                break
            last_err = f"HTTP {resp.status_code} pour {url}"
        except requests.RequestException as exc:
            last_err = str(exc)

    if not raw:
        raise RuntimeError(last_err or "Téléchargement de la mise à jour impossible.")

    preserve = {"data", ".git", ".venv", "venv", "__pycache__"}
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = zf.namelist()
        if not names:
            raise RuntimeError("Archive vide.")
        root_prefix = names[0].split("/")[0] + "/"
        for info in zf.infolist():
            if info.is_dir():
                continue
            rel = info.filename
            if not rel.startswith(root_prefix):
                continue
            rel_path = rel[len(root_prefix) :]
            if not rel_path:
                continue
            top = rel_path.split("/", 1)[0]
            if top in preserve:
                continue
            target = ROOT / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)


def apply_update(tag: str | None = None) -> dict[str, Any]:
    state = check_for_update() if not tag else get_state()
    target = (tag or state.get("latest") or "").lstrip("vV")
    current = read_version()
    if not target:
        _set_state(error="Aucune version cible.", applied=False)
        return get_state()
    if not is_newer(target, current) and tag is None:
        _set_state(message=f"Déjà à jour ({current}).", applied=False)
        return get_state()

    try:
        if _is_git_repo():
            _apply_via_git(target)
        else:
            _apply_via_zip(target)
        # Assurer le fichier VERSION
        VERSION_FILE.write_text(target + "\n", encoding="utf-8")
        _set_state(
            applied=True,
            needs_restart=True,
            update_available=False,
            current=target,
            latest=target,
            error="",
            message=f"Mis à jour vers {target}. Redémarrez Linkora.",
        )
    except Exception as exc:
        _set_state(error=str(exc), applied=False, message="")
    return get_state()


def startup_autoupdate(*, enabled: bool = True) -> None:
    """Vérifie (et applique) une MAJ au démarrage, en arrière-plan."""

    def worker() -> None:
        try:
            state = check_for_update()
            if enabled and state.get("update_available"):
                apply_update(state.get("latest"))
        except Exception as exc:
            _set_state(error=str(exc))

    threading.Thread(target=worker, daemon=True, name="linkora-updater").start()


def write_state_cache() -> None:
    cache = ROOT / "data" / "update_state.json"
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(get_state(), ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
