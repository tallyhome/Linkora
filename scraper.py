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


def fetch_html(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=25)
    except requests.exceptions.SSLError:
        warnings.filterwarnings("ignore", message="Unverified HTTPS request")
        resp = requests.get(url, headers=HEADERS, timeout=25, verify=False)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def _normalize_hosts(host: str | list[str] | None) -> list[str]:
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
        if len(out) >= 6:
            break
    return out


def _anchor_matches_host(a, provider_span, host_lower: str) -> bool:
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
        ).lower()
        return host_lower in title_attrs

    classes = provider_span.get("class", [])
    matches_class = any(host_lower in c.lower() for c in classes)
    title = (provider_span.get("title") or "").lower()
    matches_title = host_lower in title
    return matches_class or matches_title


def extract_links(html: str, host: str | list[str]) -> list[dict]:
    """Extrait les liens dont le provider correspond à un ou plusieurs hébergeurs."""
    soup = BeautifulSoup(html, "html.parser")
    hosts = _normalize_hosts(host)
    if not hosts:
        return []

    results: list[dict] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        provider_span = a.find("span", class_=re.compile(r"^providers", re.I))
        matched_host = ""
        for candidate in hosts:
            if _anchor_matches_host(a, provider_span, candidate.lower()):
                matched_host = candidate
                break
        if not matched_host:
            continue

        href = a["href"].strip()
        if not href or href in seen:
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


def scrape(url: str, host: str | list[str]) -> list[dict]:
    html = fetch_html(url)
    return extract_links(html, host)
