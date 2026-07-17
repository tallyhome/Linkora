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


def extract_links(html: str, host: str) -> list[dict]:
    """Extrait les liens dont le provider correspond à `host` (libre)."""
    soup = BeautifulSoup(html, "html.parser")
    host_lower = host.strip().lower()
    if not host_lower:
        return []

    results: list[dict] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        provider_span = a.find("span", class_=re.compile(r"^providers", re.I))
        if not provider_span:
            # Fallback : titre data-original-title / title contenant le host
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
            if host_lower not in title_attrs:
                continue
            matches = True
        else:
            classes = provider_span.get("class", [])
            matches_class = any(host_lower in c.lower() for c in classes)
            title = (provider_span.get("title") or "").lower()
            matches_title = host_lower in title
            matches = matches_class or matches_title

        if not matches:
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

        results.append({"label": label, "size": size, "url": href})

    return results


def scrape(url: str, host: str) -> list[dict]:
    html = fetch_html(url)
    return extract_links(html, host)
