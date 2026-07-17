"""Clients débrideurs (AllDebrid, Real-Debrid) via leurs APIs officielles."""

from __future__ import annotations

import time
import warnings
from typing import Any
from urllib.parse import urlparse

import smart_naming

import requests
from urllib3.exceptions import InsecureRequestWarning

warnings.filterwarnings("ignore", category=InsecureRequestWarning)

AGENT = "Linkora"
TIMEOUT = 45

_DEAD_CODES = {
    "LINK_DOWN",
    "LINK_HOST_UNAVAILABLE",
}
_NO_RETRY_CODES = {
    "LINK_HOST_NOT_SUPPORTED",
    "AUTH_BAD_APIKEY",
    "AUTH_BLOCKED",
    "AUTH_USER_BANNED",
}


def _request_with_ssl_fallback(session: requests.Session, method: str, url: str, **kwargs):
    """Certaines machines Windows échouent la vérif SSL ; retente sans verify."""
    try:
        return session.request(method, url, **kwargs)
    except requests.exceptions.SSLError:
        kwargs = {**kwargs, "verify": False}
        return session.request(method, url, **kwargs)


class DebridError(Exception):
    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code


def _is_protector(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    needles = (
        "dl-protect",
        "dlprotect",
        "protect-lien",
        "linkprotect",
        "safelinking",
        "adf.ly",
        "ouo.io",
        "linkvertise",
    )
    return any(n in host for n in needles)


def _format_size(n: Any) -> str:
    try:
        size = int(n)
    except (TypeError, ValueError):
        return ""
    if size <= 0:
        return ""
    units = ["o", "Ko", "Mo", "Go", "To"]
    i = 0
    value = float(size)
    while value >= 1024 and i < len(units) - 1:
        value /= 1024
        i += 1
    return f"{value:.0f} {units[i]}" if i == 0 else f"{value:.1f} {units[i]}"


# ─── AllDebrid ───────────────────────────────────────────────────────────────


class AllDebridClient:
    BASE = "https://api.alldebrid.com/v4"

    def __init__(self, api_key: str):
        if not api_key:
            raise DebridError("Clé API AllDebrid manquante.")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def _post(self, path: str, data: dict | None = None) -> dict:
        resp = _request_with_ssl_fallback(
            self.session,
            "POST",
            f"{self.BASE}{path}",
            data=data or {},
            params={"agent": AGENT},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("status") != "success":
            err = payload.get("error") or {}
            raise DebridError(
                err.get("message") or "Erreur AllDebrid",
                err.get("code"),
            )
        return payload.get("data") or {}

    def _get(self, path: str) -> dict:
        resp = _request_with_ssl_fallback(
            self.session,
            "GET",
            f"{self.BASE}{path}",
            params={"agent": AGENT},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("status") != "success":
            err = payload.get("error") or {}
            raise DebridError(
                err.get("message") or "Erreur AllDebrid",
                err.get("code"),
            )
        return payload.get("data") or {}

    def test(self) -> dict:
        data = self._get("/user")
        user = data.get("user") or data
        return {
            "ok": True,
            "provider": "alldebrid",
            "username": user.get("username") or user.get("email") or "",
            "premium": bool(user.get("isPremium") or user.get("premiumUntil")),
            "raw": {"premiumUntil": user.get("premiumUntil")},
        }

    def redirector(self, url: str) -> list[str]:
        data = self._post("/link/redirector", {"link": url})
        return list(data.get("links") or [])

    def unlock(self, url: str) -> dict:
        data = self._post("/link/unlock", {"link": url})
        if data.get("delayed"):
            data = self._wait_delayed(int(data["delayed"]))
        return data

    def _wait_delayed(self, delayed_id: int, attempts: int = 20) -> dict:
        for _ in range(attempts):
            data = self._post("/link/delayed", {"id": delayed_id})
            # status: 1 = still processing, 2 = ready, 3 = error
            status = data.get("status")
            if status == 2:
                return data
            if status == 3:
                raise DebridError("Génération du lien AllDebrid échouée.", "DELAYED_ERROR")
            time.sleep(1.5)
        raise DebridError("Délai dépassé pour la génération du lien.", "DELAYED_TIMEOUT")

    def resolve_one(self, protected_url: str) -> dict:
        """Résout un lien (protecteur ou hébergeur) via AllDebrid."""
        result = {
            "source_url": protected_url,
            "status": "error",
            "hoster_url": "",
            "download_url": "",
            "filename": "",
            "filesize": "",
            "host": "",
            "error": "",
        }
        try:
            candidates = [protected_url]
            if _is_protector(protected_url):
                extracted = self.redirector(protected_url)
                if not extracted:
                    result["error"] = "Aucun lien extrait du protecteur."
                    return result
                candidates = extracted

            # Un protecteur peut contenir plusieurs liens ; on prend le 1er
            # (pour une série, chaque episode = 1 protecteur → 1 lien)
            unlocked = self.unlock(candidates[0])
            download = unlocked.get("link") or ""
            result.update(
                {
                    "status": "ok" if download else "error",
                    "download_url": download,
                    "hoster_url": candidates[0]
                    if not candidates[0].startswith("https://redirect.alldebrid.com")
                    else "",
                    "filename": unlocked.get("filename") or "",
                    "filesize": _format_size(unlocked.get("filesize")),
                    "host": unlocked.get("hostDomain")
                    or unlocked.get("host")
                    or "",
                    "error": "" if download else "Pas d'URL de téléchargement.",
                    "extra_links": candidates[1:] if len(candidates) > 1 else [],
                }
            )
        except DebridError as exc:
            result["error"] = str(exc)
            # LINK_DOWN et variantes → dead ; le reste → error (retriable)
            code = (exc.code or "").upper()
            msg = str(exc).lower()
            if code in _DEAD_CODES or any(
                w in msg for w in ("down", "unavailable", "not found", "removed")
            ):
                result["status"] = "dead"
            elif code in _NO_RETRY_CODES:
                result["status"] = "error"
            else:
                result["status"] = "error"
            result["error_code"] = code
        except requests.RequestException as exc:
            result["error"] = f"Réseau : {exc}"
        return result


# ─── Real-Debrid ─────────────────────────────────────────────────────────────


class RealDebridClient:
    BASE = "https://api.real-debrid.com/rest/1.0"

    def __init__(self, api_key: str):
        if not api_key:
            raise DebridError("Clé API Real-Debrid manquante.")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def _request(self, method: str, path: str, data: dict | None = None) -> Any:
        resp = _request_with_ssl_fallback(
            self.session,
            method,
            f"{self.BASE}{path}",
            data=data,
            timeout=TIMEOUT,
        )
        if resp.status_code == 204:
            return {}
        if resp.status_code >= 400:
            try:
                err = resp.json()
                msg = err.get("error") or err.get("error_code") or resp.text
            except Exception:
                msg = resp.text
            raise DebridError(str(msg), str(resp.status_code))
        if not resp.content:
            return {}
        return resp.json()

    def test(self) -> dict:
        user = self._request("GET", "/user")
        return {
            "ok": True,
            "provider": "realdebrid",
            "username": user.get("username") or user.get("email") or "",
            "premium": user.get("type") == "premium",
            "raw": {"expiration": user.get("expiration")},
        }

    def unrestrict(self, url: str) -> dict:
        return self._request("POST", "/unrestrict/link", {"link": url})

    def unrestrict_folder(self, url: str) -> list:
        data = self._request("POST", "/unrestrict/folder", {"link": url})
        if isinstance(data, list):
            return data
        return list(data or [])

    def resolve_one(self, protected_url: str) -> dict:
        result = {
            "source_url": protected_url,
            "status": "error",
            "hoster_url": "",
            "download_url": "",
            "filename": "",
            "filesize": "",
            "host": "",
            "error": "",
        }
        try:
            # Tentative directe ; pour certains protecteurs RD utilise /folder
            try:
                unlocked = self.unrestrict(protected_url)
            except DebridError:
                folder_links = self.unrestrict_folder(protected_url)
                if not folder_links:
                    raise
                first = folder_links[0]
                if isinstance(first, str):
                    unlocked = self.unrestrict(first)
                    result["hoster_url"] = first
                else:
                    unlocked = first

            download = unlocked.get("download") or ""
            hoster = unlocked.get("link") or result.get("hoster_url") or ""
            result.update(
                {
                    "status": "ok" if download else "error",
                    "download_url": download,
                    "hoster_url": hoster,
                    "filename": unlocked.get("filename") or "",
                    "filesize": _format_size(unlocked.get("filesize")),
                    "host": unlocked.get("host") or "",
                    "error": "" if download else "Pas d'URL de téléchargement.",
                }
            )
        except DebridError as exc:
            result["error"] = str(exc)
            result["status"] = "dead" if "unavailable" in str(exc).lower() else "error"
        except requests.RequestException as exc:
            result["error"] = f"Réseau : {exc}"
        return result


# ─── Facade ──────────────────────────────────────────────────────────────────


PROVIDERS = {
    "alldebrid": AllDebridClient,
    "realdebrid": RealDebridClient,
}


def get_client(provider: str, api_key: str):
    cls = PROVIDERS.get(provider)
    if not cls:
        raise DebridError(f"Fournisseur inconnu : {provider}")
    return cls(api_key)


def _merge_resolved(item: dict, info: dict, attempts: int = 1) -> dict:
    source = item.get("url") or ""
    merged = {
        **item,
        "resolved": info,
        "url_display": info.get("download_url") or source,
        "real_url": info.get("download_url") or "",
        "hoster_url": info.get("hoster_url") or "",
        "resolve_status": info.get("status") or "error",
        "resolve_error": info.get("error") or "",
        "resolve_filename": info.get("filename") or item.get("label") or "",
        "resolve_size": info.get("filesize") or item.get("size") or "",
        "resolve_host": info.get("host") or "",
        "resolve_attempts": attempts,
    }
    return smart_naming.enrich_link(merged)


def _should_retry(info: dict) -> bool:
    status = info.get("status")
    if status == "ok":
        return False
    # Erreurs d'auth / host non supporté : inutile de réessayer
    code = None
    # le code peut être dans le message pour RD ; côté AD on l'a sur DebridError
    err = (info.get("error") or "").lower()
    if "not supported" in err or "apikey" in err or "banned" in err:
        return False
    return status in ("dead", "error")


def resolve_item(
    provider: str,
    api_key: str,
    item: dict,
    *,
    max_retries: int = 3,
    retry_delay: float = 0.8,
) -> dict:
    """
    Résout un lien. En cas de dead/erreur temporaire, retente jusqu'à
    `max_retries` fois (comme le comportement manuel sur AllDebrid).
    """
    client = get_client(provider, api_key)
    source = item.get("url") or ""
    last = None
    attempts = max(1, int(max_retries))

    for attempt in range(1, attempts + 1):
        info = client.resolve_one(source)
        # Affiner dead si le message le suggère
        err_l = (info.get("error") or "").lower()
        if info.get("status") == "error" and any(
            w in err_l for w in ("down", "unavailable", "not found", "removed", "dead")
        ):
            info["status"] = "dead"
        last = _merge_resolved(item, info, attempts=attempt)
        if info.get("status") == "ok":
            return last
        if not _should_retry(info) or attempt >= attempts:
            break
        time.sleep(retry_delay)

    return last or _merge_resolved(
        item,
        {
            "status": "error",
            "error": "Résolution impossible",
            "download_url": "",
            "hoster_url": "",
            "filename": "",
            "filesize": "",
            "host": "",
        },
        attempts=attempts,
    )


def _is_auth_failure(resolved: dict) -> bool:
    err = (resolved.get("resolve_error") or "").lower()
    needles = (
        "apikey",
        "api key",
        "auth",
        "unauthorized",
        "forbidden",
        "banned",
        "quota",
        "limit",
        "premium",
    )
    return any(n in err for n in needles)


def resolve_item_rotating(
    provider: str,
    api_keys: list[str],
    item: dict,
    *,
    max_retries: int = 3,
) -> dict:
    """Essaie plusieurs clés si erreur d'auth / quota."""
    keys = [k.strip() for k in api_keys if str(k or "").strip()]
    if not keys:
        raise DebridError("Aucune clé API fournie.")
    last = None
    for idx, key in enumerate(keys):
        last = resolve_item(provider, key, item, max_retries=max_retries)
        if last.get("resolve_status") == "ok":
            if idx > 0:
                last["resolve_key_index"] = idx + 1
            return last
        if _is_auth_failure(last) and idx < len(keys) - 1:
            continue
        return last
    return last


def resolve_links(
    provider: str,
    api_key: str,
    links: list[dict],
    *,
    max_retries: int = 3,
) -> list[dict]:
    return [
        resolve_item(provider, api_key, item, max_retries=max_retries)
        for item in links
    ]


def test_provider(provider: str, api_key: str) -> dict:
    return get_client(provider, api_key).test()
