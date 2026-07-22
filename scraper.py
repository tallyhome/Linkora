"""Logique d'extraction des liens hébergeurs depuis une page HTML."""

from __future__ import annotations

import base64
import re
import warnings
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

EXTRACT_MODES = ("providers", "domains", "extensions", "smart")
DEFAULT_EXTRACT_MODE = "smart"
DEFAULT_EXTENSIONS = (".zip", ".rar", ".7z", ".exe", ".iso", ".tar", ".gz", ".apk")

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

# Domaines associés à chaque hébergeur (mode domains / smart).
HOST_DOMAINS: dict[str, tuple[str, ...]] = {
    "rapidgator": ("rapidgator.net", "rg.to"),
    "nitroflare": ("nitroflare.com", "nitro.download"),
    "1fichier": ("1fichier.com",),
    "turbobit": ("turbobit.net", "turbobit.com"),
    "uptobox": ("uptobox.com", "uptostream.com"),
    "mega": ("mega.nz", "mega.co.nz"),
    "mixdrop": ("mixdrop.top", "mixdrop.co", "mixdrop.ag", "mixdrop.sx", "mixdrop.to"),
    "gofile": ("gofile.io",),
    "pixeldrain": ("pixeldrain.com",),
    "workupload": ("workupload.com",),
    "vikingfile": ("vikingfile.com",),
    "uploadrar": ("uploadrar.com",),
    "send.now": ("send.now",),
    "mirrored.to": ("mirrored.to",),
    "megaup": ("megaup.net",),
    "hxfile": ("hxfile.co",),
    "cloudfam": ("cloudfam.io",),
    "bowfile": ("bowfile.com",),
    "uploady": ("uploady.io", "uploady.com"),
    "dailyuploads": ("dailyuploads.net",),
    "vidoza": ("vidoza.net",),
    "mystream": ("mystream.to", "embed.mystream.to"),
    "vidlox": ("vidlox.me",),
}

# Variantes de matching (classes providers* / titres sur les pages source).
_HOST_ALIASES: dict[str, tuple[str, ...]] = {
    "send.now": ("send.now", "sendnow"),
    "mirrored.to": ("mirrored.to", "mirrored"),
    "1fichier": ("1fichier", "1ficher"),
    "dailyuploads": ("dailyuploads", "dailyupload"),
}

_URL_RE = re.compile(r"https?://[^\s<>\"'\]]+", re.I)
_EPISODE_LABEL_RE = re.compile(r"(?i)^\s*episode\s*\d+")

# Protecteurs de liens (débridables via AllDebrid / Real-Debrid).
PROTECTOR_DOMAINS: tuple[str, ...] = (
    "dl-protect.link",
    "dl-protect.com",
    "dlprotect.info",
    "protect-lien.com",
    "linkprotect.cyp",
    "safelinking.net",
    "ouo.io",
    "linkvertise.com",
)

_DOMAIN_TO_HOST: dict[str, str] = {}
for _host, _domains in HOST_DOMAINS.items():
    for _d in _domains:
        _DOMAIN_TO_HOST[_d.lower()] = _host


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


def normalize_extract_mode(raw: str | None) -> str:
    mode = str(raw or DEFAULT_EXTRACT_MODE).strip().lower()
    return mode if mode in EXTRACT_MODES else DEFAULT_EXTRACT_MODE


def normalize_extensions(raw) -> list[str]:
    if raw is None:
        parts = list(DEFAULT_EXTENSIONS)
    elif isinstance(raw, str):
        parts = re.split(r"[\s,;|]+", raw)
    elif isinstance(raw, (list, tuple)):
        parts = [str(x) for x in raw]
    else:
        parts = list(DEFAULT_EXTENSIONS)
    out: list[str] = []
    seen: set[str] = set()
    for part in parts:
        ext = str(part or "").strip().lower()
        if not ext:
            continue
        if not ext.startswith("."):
            ext = "." + ext
        if ext in seen:
            continue
        seen.add(ext)
        out.append(ext)
        if len(out) >= 40:
            break
    return out or list(DEFAULT_EXTENSIONS)


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


def _clean_url(raw: str) -> str:
    url = (raw or "").strip()
    # Couper ponctuation / balises collées en fin d’URL (texte brut)
    url = url.rstrip(".,);]}>\"'")
    return url


def _url_host(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def _host_for_url(url: str, allowed_hosts: list[str] | None = None) -> str:
    """Retourne le nom d’hébergeur système correspondant à l’URL, ou ''."""
    netloc = _url_host(url)
    if not netloc:
        return ""
    matched = ""
    matched_len = -1
    for domain, host_name in _DOMAIN_TO_HOST.items():
        if allowed_hosts is not None:
            allowed_l = {h.lower() for h in allowed_hosts}
            if host_name.lower() not in allowed_l:
                continue
        if netloc == domain or netloc.endswith("." + domain):
            if len(domain) > matched_len:
                matched_len = len(domain)
                matched = host_name
    return matched


def _is_protector_url(url: str) -> bool:
    host = _url_host(url)
    if not host:
        return False
    return any(host == d or host.endswith("." + d) for d in PROTECTOR_DOMAINS)


def _match_host_in_text(text: str, hosts: list[str]) -> str:
    """Retourne l’hébergeur dont le nom apparaît dans un libellé court."""
    raw = (text or "").strip()
    if not raw or len(raw) > 80:
        return ""
    t = raw.lower()
    if _EPISODE_LABEL_RE.match(t):
        return ""
    best = ""
    best_score = -1
    for host in hosts:
        for key in _host_match_keys(host):
            if len(key) < 3:
                continue
            hit = False
            if t == key or t.replace(" ", "") == key.replace(" ", ""):
                hit = True
            elif re.search(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])", t):
                hit = True
            if hit and len(key) > best_score:
                best_score = len(key)
                best = host
    return best


def _infer_host_near_anchor(a, hosts: list[str]) -> str:
    """
    Sur les pages type zone-annuaire : le nom d’hébergeur précède les Episode N
    (Uploady / Rapidgator / Turbobit…) alors que le href est un protecteur.

    On s’arrête au premier libellé d’hébergeur connu (catalogue système),
    même s’il n’est pas dans le filtre — sinon on remonte trop loin
    (ex. section Turbobit qui « voit » Rapidgator plus haut).
    """
    if not a or not hosts:
        return ""
    catalog = list(SUPPORTED_HOSTS)
    allowed = {h.lower() for h in hosts}
    for el in a.find_all_previous(True, limit=50):
        if getattr(el, "name", None) in ("script", "style", "noscript"):
            continue
        if el.name == "img":
            own = (el.get("alt") or el.get("title") or "").strip()
        else:
            own = el.get_text(" ", strip=True)
        if not own or len(own) > 60:
            continue
        matched = _match_host_in_text(own, catalog)
        if not matched:
            continue
        if matched.lower() in allowed:
            return matched
        return ""
    return ""


def _label_from_protect_url(url: str) -> str:
    """Décode le paramètre fn= (base64) souvent présent sur dl-protect."""
    try:
        qs = parse_qs(urlparse(url).query)
        fn = (qs.get("fn") or [""])[0]
        if not fn:
            return ""
        pad = "=" * ((4 - len(fn) % 4) % 4)
        raw = base64.b64decode(fn + pad).decode("utf-8", errors="ignore").strip()
        # ex. "Lucky - Saison 1 Episode 1 -[VF]"
        return raw[:140]
    except Exception:
        return ""


def _url_has_extension(url: str, extensions: list[str]) -> bool:
    try:
        path = unquote(urlparse(url).path or "").lower()
    except Exception:
        return False
    return any(path.endswith(ext) for ext in extensions)


def _anchor_meta(a) -> tuple[str, str]:
    b_tag = a.find("b") if a else None
    label = b_tag.get_text(strip=True) if b_tag else ""
    if not label and a:
        label = a.get_text(" ", strip=True)[:120]
    label = label.rstrip(" :")
    size_el = a.find(class_="fichetaille") if a else None
    size = size_el.get_text(strip=True) if size_el else ""
    return label, size


def _append_result(
    results: list[dict],
    seen: set[str],
    *,
    url: str,
    matched_host: str,
    label: str = "",
    size: str = "",
) -> None:
    href = _clean_url(url)
    if not href.lower().startswith(("http://", "https://")):
        return
    if href in seen:
        return
    seen.add(href)
    results.append(
        {
            "label": label,
            "size": size,
            "url": href,
            "matched_host": matched_host,
        }
    )


def _extract_providers(
    soup: BeautifulSoup,
    hosts: list[str],
    results: list[dict],
    seen: set[str],
) -> None:
    for a in soup.find_all("a", href=True):
        provider_span = a.find("span", class_=re.compile(r"^providers", re.I))
        matched_host = ""
        matched_score = -1
        for candidate in hosts:
            if not _anchor_matches_host(a, provider_span, candidate):
                continue
            score = max((len(k) for k in _host_match_keys(candidate)), default=0)
            if score > matched_score:
                matched_score = score
                matched_host = candidate
        if not matched_host:
            continue
        label, size = _anchor_meta(a)
        _append_result(
            results,
            seen,
            url=a["href"].strip(),
            matched_host=matched_host,
            label=label,
            size=size,
        )


def _extract_domains(
    soup: BeautifulSoup,
    hosts: list[str],
    results: list[dict],
    seen: set[str],
) -> None:
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        matched = _host_for_url(href, hosts)
        if not matched:
            continue
        label, size = _anchor_meta(a)
        _append_result(
            results,
            seen,
            url=href,
            matched_host=matched,
            label=label,
            size=size,
        )


def _extract_extensions(
    soup: BeautifulSoup,
    extensions: list[str],
    results: list[dict],
    seen: set[str],
) -> None:
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not _url_has_extension(href, extensions):
            continue
        matched = _host_for_url(href) or "file"
        label, size = _anchor_meta(a)
        if not label:
            try:
                label = unquote(urlparse(href).path.rsplit("/", 1)[-1])
            except Exception:
                label = ""
        _append_result(
            results,
            seen,
            url=href,
            matched_host=matched,
            label=label,
            size=size,
        )


def _extract_plaintext_urls(
    html: str,
    hosts: list[str],
    results: list[dict],
    seen: set[str],
) -> None:
    for match in _URL_RE.finditer(html or ""):
        href = _clean_url(match.group(0))
        matched = _host_for_url(href, hosts)
        if not matched:
            continue
        _append_result(results, seen, url=href, matched_host=matched)


def _extract_protectors(
    soup: BeautifulSoup,
    hosts: list[str],
    results: list[dict],
    seen: set[str],
    *,
    include_unknown: bool = False,
) -> None:
    """
    Liens protecteurs (dl-protect…) : associe l’hébergeur au libellé voisin.
    Couvre zone-annuaire / annuaires similaires sans spans providers*.
    """
    allowed = hosts or list(SUPPORTED_HOSTS)
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not _is_protector_url(href):
            continue
        inferred = _infer_host_near_anchor(a, allowed)
        if not inferred:
            if not include_unknown:
                continue
            inferred = "protect"
        elif hosts and inferred.lower() not in {h.lower() for h in hosts}:
            continue

        label, size = _anchor_meta(a)
        if not label or label.lower().startswith("http"):
            label = _label_from_protect_url(href) or label
        _append_result(
            results,
            seen,
            url=href,
            matched_host=inferred,
            label=label,
            size=size,
        )


def _extract_adaptive(
    soup: BeautifulSoup,
    html: str,
    hosts: list[str],
    results: list[dict],
    seen: set[str],
) -> None:
    """
    Mode adaptatif : providers + domaines hosters + protecteurs contextualisés
    + URLs texte. Sert de base « multi-sites » sans LLM.
    """
    _extract_providers(soup, hosts, results, seen)
    _extract_domains(soup, hosts, results, seen)
    _extract_protectors(
        soup,
        hosts,
        results,
        seen,
        include_unknown=len(hosts) >= len(SUPPORTED_HOSTS) - 2,
    )
    _extract_plaintext_urls(html, hosts, results, seen)


def extract_links(
    html: str,
    host: str | list[str],
    *,
    max_hosts: int | None = 6,
    mode: str | None = None,
    extensions: list[str] | tuple[str, ...] | str | None = None,
) -> list[dict]:
    """Extrait les liens selon le mode (providers / domains / extensions / smart)."""
    soup = BeautifulSoup(html, "html.parser")
    hosts = _normalize_hosts(host, max_hosts=max_hosts)
    extract_mode = normalize_extract_mode(mode)
    exts = normalize_extensions(extensions)

    # Mode extensions : pas besoin d’hébergeur nommé
    if extract_mode != "extensions" and not hosts:
        return []

    results: list[dict] = []
    seen: set[str] = set()

    if extract_mode == "providers":
        _extract_providers(soup, hosts, results, seen)
    elif extract_mode == "domains":
        _extract_domains(soup, hosts, results, seen)
        _extract_protectors(soup, hosts, results, seen, include_unknown=False)
    elif extract_mode == "extensions":
        _extract_extensions(soup, exts, results, seen)
    else:  # smart — adaptatif multi-sites
        _extract_adaptive(soup, html, hosts, results, seen)

    return results


def scrape(
    url: str,
    host: str | list[str],
    *,
    max_hosts: int | None = 6,
    mode: str | None = None,
    extensions: list[str] | tuple[str, ...] | str | None = None,
) -> list[dict]:
    html = fetch_html(url)
    return extract_links(
        html,
        host,
        max_hosts=max_hosts,
        mode=mode,
        extensions=extensions,
    )
