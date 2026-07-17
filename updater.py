"""Mise à jour automatique — GitHub releases (zip) ou site (latest.json)."""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import threading
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
    "error": "",
    "message": "",
    "source": "github",
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
            "frozen": bool(getattr(sys, "frozen", False)),
        }


def _set_state(**kwargs: Any) -> None:
    with _lock:
        _state.update(kwargs)


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
            # Fallback source archive
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
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=120, stream=True)
    if resp.status_code != 200:
        raise RuntimeError(f"Téléchargement impossible (HTTP {resp.status_code}).")
    raw = resp.content
    if raw[:2] != b"PK":
        raise RuntimeError("Le fichier téléchargé n’est pas un zip valide.")
    return raw


def _extract_zip_bytes(raw: bytes) -> None:
    """Extrait en préservant data/ et fichiers sensibles."""
    preserve_top = {"data", ".git", ".venv", "venv", "__pycache__", "logs"}
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = zf.namelist()
        if not names:
            raise RuntimeError("Archive vide.")

        # Détecte un préfixe unique (Linkora-1.0.1/ ou Linkora/)
        first = names[0]
        root_prefix = ""
        if "/" in first:
            candidate = first.split("/", 1)[0] + "/"
            if all(n.startswith(candidate) or n == candidate.rstrip("/") for n in names):
                root_prefix = candidate

        for info in zf.infolist():
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
            if top in preserve_top:
                continue
            # Ne pas écraser le zip updater en cours de façon dangereuse — OK
            target = ROOT / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)


def apply_update(
    tag: str | None = None,
    *,
    download_url: str | None = None,
    manifest_url: str | None = None,
) -> dict[str, Any]:
    state = get_state()
    if not state.get("checked") or manifest_url:
        state = check_for_update(manifest_url)

    target = (tag or state.get("latest") or "").lstrip("vV")
    url = download_url or state.get("download_url") or ""
    current = read_version()

    if not target:
        _set_state(error="Aucune version cible.", applied=False)
        return get_state()
    if not is_newer(target, current) and tag is None and not download_url:
        _set_state(message=f"Déjà à jour ({current}).", applied=False)
        return get_state()

    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if _is_git_repo() and not getattr(sys, "frozen", False) and not url.endswith(".zip"):
            _apply_via_git(target)
        else:
            if not url:
                raise RuntimeError("Pas d’URL de téléchargement pour la MAJ.")
            raw = _download_zip(url)
            _extract_zip_bytes(raw)

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


def startup_autoupdate(*, enabled: bool = True, manifest_url: str | None = None) -> None:
    def worker() -> None:
        try:
            state = check_for_update(manifest_url)
            if enabled and state.get("update_available"):
                apply_update(state.get("latest"), manifest_url=manifest_url)
        except Exception as exc:
            _set_state(error=str(exc))

    threading.Thread(target=worker, daemon=True, name="linkora-updater").start()
