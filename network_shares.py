"""Accès aux partages réseau Windows (UNC) avec identifiants."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path
from typing import Any

# Codes Win32 utiles
_NO_ERROR = 0
_ERROR_ALREADY_ASSIGNED = 85
_ERROR_DEVICE_ALREADY_REMEMBERED = 1202
_ERROR_SESSION_CREDENTIAL_CONFLICT = 1219
_RESOURCETYPE_DISK = 1
_CONNECT_TEMPORARY = 4

_CONNECTED: set[str] = set()


class NETRESOURCE(ctypes.Structure):
    _fields_ = [
        ("dwScope", wintypes.DWORD),
        ("dwType", wintypes.DWORD),
        ("dwDisplayType", wintypes.DWORD),
        ("dwUsage", wintypes.DWORD),
        ("lpLocalName", wintypes.LPWSTR),
        ("lpRemoteName", wintypes.LPWSTR),
        ("lpComment", wintypes.LPWSTR),
        ("lpProvider", wintypes.LPWSTR),
    ]


def is_unc_path(path: str) -> bool:
    cleaned = str(path or "").strip().replace("/", "\\")
    return cleaned.startswith("\\\\") and not cleaned.startswith("\\\\?\\")


def parse_unc(path: str) -> tuple[str, str] | None:
    """Retourne (serveur, partage) pour \\\\serveur\\partage\\…"""
    cleaned = str(path or "").strip().replace("/", "\\")
    if not is_unc_path(cleaned):
        return None
    parts = [p for p in cleaned[2:].split("\\") if p]
    if len(parts) < 2:
        return None
    return parts[0], parts[1]


def unc_share_root(path: str) -> str | None:
    parsed = parse_unc(path)
    if not parsed:
        return None
    server, share = parsed
    return f"\\\\{server}\\{share}"


def _normalize_host(host: str) -> str:
    value = str(host or "").strip().replace("/", "\\")
    while value.startswith("\\"):
        value = value[1:]
    if "\\" in value:
        value = value.split("\\", 1)[0]
    return value.lower()


def _match_cred(
    server: str,
    share: str,
    credentials: list[dict[str, str]],
) -> dict[str, str] | None:
    server_key = _normalize_host(server)
    share_key = share.lower()
    exact = None
    host_only = None
    wildcard = None
    for raw in credentials:
        if not isinstance(raw, dict):
            continue
        user = str(raw.get("username") or "").strip()
        if not user:
            continue
        entry = {
            "host": str(raw.get("host") or "").strip(),
            "share": str(raw.get("share") or "").strip(),
            "username": user,
            "password": str(raw.get("password") or ""),
        }
        host_n = _normalize_host(entry["host"]) if entry["host"] else ""
        share_n = entry["share"].lower() if entry["share"] else ""
        if host_n and host_n != server_key:
            continue
        if share_n and share_n != share_key:
            continue
        if host_n and share_n:
            exact = entry
            break
        if host_n and not share_n:
            host_only = host_only or entry
        if not host_n:
            wildcard = wildcard or entry
    return exact or host_only or wildcard


def _format_win_error(code: int) -> str:
    messages = {
        5: "Accès refusé (identifiants incorrects ou droits insuffisants).",
        53: "Chemin réseau introuvable (hôte hors ligne ou mauvais nom).",
        67: "Nom de partage introuvable.",
        86: "Mot de passe incorrect.",
        1219: "Conflit de session : une autre connexion existe déjà avec d’autres identifiants.",
        1326: "Identifiant ou mot de passe incorrect.",
    }
    if code in messages:
        return messages[code]
    try:
        buf = ctypes.create_unicode_buffer(512)
        flags = 0x00001000  # FORMAT_MESSAGE_FROM_SYSTEM
        n = ctypes.windll.kernel32.FormatMessageW(
            flags, None, code, 0, buf, len(buf), None
        )
        if n:
            return buf.value.strip()
    except Exception:
        pass
    return f"Erreur Windows {code}."


def _wnet_connect(remote: str, username: str, password: str) -> None:
    if sys.platform != "win32":
        raise OSError("Les identifiants NAS ne sont disponibles que sous Windows.")

    mpr = ctypes.windll.mpr
    nr = NETRESOURCE()
    nr.dwType = _RESOURCETYPE_DISK
    nr.lpLocalName = None
    nr.lpRemoteName = remote
    nr.lpProvider = None

    user = username.strip() or None
    pwd = password if password is not None else None

    result = mpr.WNetAddConnection2W(
        ctypes.byref(nr),
        pwd,
        user,
        _CONNECT_TEMPORARY,
    )
    if result in (
        _NO_ERROR,
        _ERROR_ALREADY_ASSIGNED,
        _ERROR_DEVICE_ALREADY_REMEMBERED,
    ):
        _CONNECTED.add(remote.lower())
        return

    if result == _ERROR_SESSION_CREDENTIAL_CONFLICT:
        # Coupe la session existante puis réessaie
        mpr.WNetCancelConnection2W(remote, 0, True)
        result = mpr.WNetAddConnection2W(
            ctypes.byref(nr),
            pwd,
            user,
            _CONNECT_TEMPORARY,
        )
        if result in (
            _NO_ERROR,
            _ERROR_ALREADY_ASSIGNED,
            _ERROR_DEVICE_ALREADY_REMEMBERED,
        ):
            _CONNECTED.add(remote.lower())
            return

    raise OSError(f"{remote} — {_format_win_error(result)}")


def connect_unc(
    path: str,
    *,
    username: str,
    password: str = "",
) -> str:
    """Établit une connexion temporaire vers le partage UNC du chemin."""
    remote = unc_share_root(path)
    if not remote:
        raise ValueError(f"Chemin UNC invalide : {path}")
    _wnet_connect(remote, username, password)
    return remote


def ensure_path_access(
    path: str,
    credentials: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """
    Si le chemin est UNC, tente une connexion avec les identifiants connus.
    Retourne un petit rapport {path, unc, connected, message}.
    """
    folder = str(path or "").strip()
    parsed = parse_unc(folder)
    if not parsed:
        return {
            "path": folder,
            "unc": False,
            "connected": False,
            "message": "",
        }

    server, share = parsed
    remote = f"\\\\{server}\\{share}"
    creds = credentials or []
    match = _match_cred(server, share, creds)

    if match:
        try:
            _wnet_connect(remote, match["username"], match.get("password") or "")
            return {
                "path": folder,
                "unc": True,
                "connected": True,
                "remote": remote,
                "message": f"Connecté à {remote} ({match['username']})",
            }
        except OSError as exc:
            raise OSError(
                f"Impossible d’accéder à {remote} avec les identifiants NAS : {exc}"
            ) from exc

    # Pas d’identifiants : laisse Windows utiliser la session déjà ouverte
    root = Path(folder)
    try:
        if root.is_dir():
            return {
                "path": folder,
                "unc": True,
                "connected": False,
                "remote": remote,
                "message": f"Accès OK sans nouvel identifiant ({remote})",
            }
    except OSError as exc:
        raise OSError(
            f"Accès refusé à {remote}. "
            "Ajoutez hôte / utilisateur / mot de passe dans Paramètres → Accès NAS."
        ) from exc

    raise FileNotFoundError(
        f"Dossier introuvable : {folder}. "
        "Vérifiez le chemin UNC, ou renseignez les identifiants NAS dans Paramètres."
    )


def ensure_paths_access(
    paths: list[str],
    credentials: list[dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Connecte chaque chemin (dédupliqué par partage)."""
    reports: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in paths:
        remote = unc_share_root(path)
        key = (remote or path).lower()
        if key in seen:
            continue
        seen.add(key)
        reports.append(ensure_path_access(path, credentials))
    return reports


def test_credentials(
    *,
    host: str,
    share: str = "",
    username: str,
    password: str = "",
) -> dict[str, Any]:
    """Teste une connexion NAS (utilisé par l’UI Paramètres)."""
    host_n = _normalize_host(host)
    share_n = str(share or "").strip().strip("\\")
    if not host_n:
        raise ValueError("Indiquez le nom ou l’IP du NAS.")
    if not username.strip():
        raise ValueError("Indiquez un nom d’utilisateur.")
    if not share_n:
        raise ValueError("Indiquez un nom de partage (ex. volume1, Media).")
    remote = f"\\\\{host_n}\\{share_n}"
    _wnet_connect(remote, username.strip(), password)
    ok = Path(remote).is_dir()
    if not ok:
        raise OSError(f"Connecté à {remote} mais le partage n’est pas accessible.")
    return {"ok": True, "remote": remote, "message": f"Connexion OK : {remote}"}
