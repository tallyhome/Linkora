"""Logique d'extraction des liens hébergeurs depuis une page HTML."""

from __future__ import annotations

import re
import warnings

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# Hébergeurs connus du système (filtre providers* + suggestions UI).
# L’ordre compte en mode « tous » : priorité multi-hébergeurs / fallback.
SUPPORTED_HOSTS: list[str] = [
    "rapidgator",
    "nitroflare",
    "1fichier",
    "turbobit",
    "uptobox",
    "mega",
    "mixdrop",
    "gofile",
    "pixeldrain",
    "workupload",
    "vikingfile",
    "uploadrar",
    "send.now",
    "mirrored.to",
    "megaup",
    "hxfile",
    "cloudfam",
    "bowfile",
    "uploady",
    "dailyuploads",
    "vidoza",
    "mystream",
    "vidlox",
]

# Variantes de matching (classes providers* / titres sur les pages source).
_HOST_ALIASES: dict[str, tuple[str, ...]] = {
    "send.now": ("send.now", "sendnow"),
    "mirrored.to": ("mirrored.to", "mirrored"),
    "1fichier": ("1fichier", "1ficher"),
    "dailyuploads": ("dailyuploads", "dailyupload"),
}


def _ssl_ignore_enabled() -> bool:
    try:
        import settings as app_settings

        return bool(app_settings.load_settings().get("ssl_ignore_errors"))
    except Exception:
        return False


def fetch_html(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=25)
    except requests.exceptions.SSLError:
        # Repli sans vérification TLS uniquement si l'utilisateur l'a activé
        # (Paramètres → « Ignorer les erreurs SSL ») : sinon on remonte l'erreur.
        if not _ssl_ignore_enabled():
            raise
        warnings.filterwarnings("ignore", message="Unverified HTTPS request")
        resp = requests.get(url, headers=HEADERS, timeout=25, verify=False)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def _normalize_hosts(
    host: str | list[str] | None,
    *,
    max_hosts: int | None = 6,
) -> list[str]:
    if host is None:
        return []
    if isinstance(host, str):
        raw = [host]
    else:
        raw = list(host)
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        value = str(item or "").strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
        if max_hosts is not None and len(out) >= max_hosts:
            break
    return out


def _host_match_keys(host: str) -> list[str]:
    """Clés de sous-chaîne à chercher dans providers* / titres."""
    base = (host or "").strip().lower()
    if not base:
        return []
    aliases = _HOST_ALIASES.get(base)
    if aliases:
        return list(aliases)
    keys = [base]
    nodot = base.replace(".", "")
    if nodot != base:
        keys.append(nodot)
    return keys


def _text_matches_host(haystack: str, host: str) -> bool:
    text = (haystack or "").lower()
    if not text:
        return False
    return any(key in text for key in _host_match_keys(host))


def _anchor_matches_host(a, provider_span, host: str) -> bool:
    if not provider_span:
        title_attrs = " ".join(
            filter(
                None,
                [
                    a.get("data-original-title"),
                    a.get("title"),
                    a.get_text(" ", strip=True),
                ],
            )
        )
        return _text_matches_host(title_attrs, host)

    classes = " ".join(str(c) for c in (provider_span.get("class") or []))
    title = provider_span.get("title") or ""
    return _text_matches_host(classes, host) or _text_matches_host(title, host)


def extract_links(html: str, host: str | list[str], *, max_hosts: int | None = 6) -> list[dict]:
    """Extrait les liens dont le provider correspond à un ou plusieurs hébergeurs."""
    soup = BeautifulSoup(html, "html.parser")
    hosts = _normalize_hosts(host, max_hosts=max_hosts)
    if not hosts:
        return []

    results: list[dict] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        provider_span = a.find("span", class_=re.compile(r"^providers", re.I))
        matched_host = ""
        matched_score = -1
        for candidate in hosts:
            if not _anchor_matches_host(a, provider_span, candidate):
                continue
            # Préfère le nom le plus long (megaup > mega, uploadrar > upload…)
            score = max((len(k) for k in _host_match_keys(candidate)), default=0)
            if score > matched_score:
                matched_score = score
                matched_host = candidate
        if not matched_host:
            continue

        href = a["href"].strip()
        # Seules les URL http(s) sont acceptées : bloque javascript:, data:, etc.
        if not href.lower().startswith(("http://", "https://")):
            continue
        if href in seen:
            continue
        seen.add(href)

        b_tag = a.find("b")
        label = b_tag.get_text(strip=True) if b_tag else ""
        label = label.rstrip(" :")

        size_el = a.find(class_="fichetaille")
        size = size_el.get_text(strip=True) if size_el else ""

        results.append(
            {
                "label": label,
                "size": size,
                "url": href,
                "matched_host": matched_host,
            }
        )

    return results


def scrape(url: str, host: str | list[str], *, max_hosts: int | None = 6) -> list[dict]:
    html = fetch_html(url)
    return extract_links(html, host, max_hosts=max_hosts)
