"""Enrichissement bibliothèque via TMDB (affiches) + cache local."""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from paths import DATA_DIR

TMDB_API = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/w342"
POSTERS_DIR = DATA_DIR / "posters"
META_PATH = POSTERS_DIR / "meta.json"
IMG_DIR = POSTERS_DIR / "img"

_LAST_REQUEST = 0.0
_MIN_INTERVAL = 0.28  # ~3,5 req/s — marge sous la limite TMDB


def _ensure_dirs() -> None:
    POSTERS_DIR.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)


def _load_meta() -> dict[str, Any]:
    _ensure_dirs()
    if not META_PATH.is_file():
        return {}
    try:
        with open(META_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_meta(meta: dict[str, Any]) -> None:
    _ensure_dirs()
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def cache_key(title: str, media: str, year: int | None = None) -> str:
    from library_scan import normalize_title

    kind = "tv" if media in ("tv", "anime", "archive") else "movie"
    y = str(int(year)) if year is not None else ""
    raw = f"{kind}|{normalize_title(title)}|{y}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:24]


def _throttle() -> None:
    global _LAST_REQUEST
    now = time.monotonic()
    wait = _MIN_INTERVAL - (now - _LAST_REQUEST)
    if wait > 0:
        time.sleep(wait)
    _LAST_REQUEST = time.monotonic()


def _get(api_key: str, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    _throttle()
    query = dict(params or {})
    query["api_key"] = api_key
    url = f"{TMDB_API}{path}"
    res = requests.get(url, params=query, timeout=20)
    if res.status_code == 401:
        raise PermissionError("Clé API TMDB invalide.")
    if res.status_code == 429:
        time.sleep(1.2)
        res = requests.get(url, params=query, timeout=20)
    res.raise_for_status()
    data = res.json()
    return data if isinstance(data, dict) else {}


def test_api_key(api_key: str) -> dict[str, Any]:
    key = (api_key or "").strip()
    if not key:
        raise ValueError("Clé API TMDB manquante.")
    data = _get(key, "/configuration")
    images = data.get("images") or {}
    return {
        "ok": True,
        "message": "Clé TMDB valide.",
        "secure_base_url": images.get("secure_base_url") or TMDB_IMG.rsplit("/w", 1)[0] + "/",
    }


def _clean_query(title: str) -> str:
    text = str(title or "").strip()
    text = re.sub(r"[\._]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:120]


def _pick_result(results: list[dict], year: int | None, title_keys: tuple[str, ...]) -> dict | None:
    if not results:
        return None
    if year is not None:
        for item in results:
            date = item.get("release_date") or item.get("first_air_date") or ""
            if date.startswith(str(year)):
                return item
    # Préférer un titre proche
    from library_scan import normalize_title

    want = normalize_title(title_keys[0] if title_keys else "")
    for item in results:
        for field in title_keys:
            name = item.get(field) or ""
            if normalize_title(name) == want:
                return item
    return results[0]


def search_tmdb(
    api_key: str,
    *,
    title: str,
    media: str,
    year: int | None = None,
    language: str = "fr-FR",
) -> dict[str, Any] | None:
    query = _clean_query(title)
    if not query:
        return None
    kind = "tv" if media in ("tv", "anime", "archive") else "movie"
    path = "/search/tv" if kind == "tv" else "/search/movie"
    params: dict[str, Any] = {
        "query": query,
        "language": language,
        "include_adult": "false",
    }
    if year is not None:
        if kind == "tv":
            params["first_air_date_year"] = int(year)
        else:
            params["year"] = int(year)
    data = _get(api_key, path, params)
    results = data.get("results") or []
    if not isinstance(results, list):
        results = []
    title_keys = ("name", "original_name") if kind == "tv" else ("title", "original_title")
    pick = _pick_result(results, year, title_keys)
    if not pick and year is not None:
        # Repli sans année
        params.pop("year", None)
        params.pop("first_air_date_year", None)
        data = _get(api_key, path, params)
        results = data.get("results") or []
        pick = _pick_result(results if isinstance(results, list) else [], None, title_keys)
    if not pick and kind == "tv" and media == "anime":
        # Anime parfois indexé en film
        data = _get(
            api_key,
            "/search/movie",
            {"query": query, "language": language, "include_adult": "false"},
        )
        results = data.get("results") or []
        pick = _pick_result(results if isinstance(results, list) else [], year, ("title", "original_title"))
        if pick:
            kind = "movie"
    if not pick:
        return None
    poster_path = pick.get("poster_path") or ""
    matched = pick.get("name") or pick.get("title") or query
    return {
        "tmdb_id": pick.get("id"),
        "media": kind,
        "matched_title": matched,
        "poster_path": poster_path,
        "year": (pick.get("first_air_date") or pick.get("release_date") or "")[:4] or None,
        "overview": (pick.get("overview") or "")[:280],
    }


def _download_poster(poster_path: str, dest: Path) -> bool:
    if not poster_path or not str(poster_path).startswith("/"):
        return False
    if dest.is_file() and dest.stat().st_size > 0:
        return True
    _throttle()
    url = f"{TMDB_IMG}{poster_path}"
    res = requests.get(url, timeout=30)
    res.raise_for_status()
    dest.write_bytes(res.content)
    return dest.is_file()


def resolve_poster(
    api_key: str,
    *,
    title: str,
    media: str,
    year: int | None = None,
    language: str = "fr-FR",
    force: bool = False,
) -> dict[str, Any]:
    """
    Retourne les infos poster pour un titre (cache disque prioritaire).
    """
    key = cache_key(title, media, year)
    meta = _load_meta()
    entry = meta.get(key) if isinstance(meta.get(key), dict) else None

    if entry and not force:
        local = entry.get("file") or ""
        path = IMG_DIR / local if local else None
        if path and path.is_file():
            return {
                "key": key,
                "cached": True,
                "found": True,
                "tmdb_id": entry.get("tmdb_id"),
                "matched_title": entry.get("matched_title") or title,
                "overview": entry.get("overview") or "",
                "poster_url": f"/api/library/poster/{quote(key)}",
                "media": entry.get("media") or media,
            }
        if entry.get("miss"):
            return {
                "key": key,
                "cached": True,
                "found": False,
                "poster_url": "",
                "matched_title": title,
            }

    if not (api_key or "").strip():
        return {"key": key, "cached": False, "found": False, "poster_url": "", "error": "no_key"}

    try:
        hit = search_tmdb(
            api_key.strip(),
            title=title,
            media=media,
            year=year,
            language=language,
        )
    except Exception as exc:
        return {
            "key": key,
            "cached": False,
            "found": False,
            "poster_url": "",
            "error": str(exc),
        }

    if not hit or not hit.get("poster_path"):
        meta[key] = {
            "miss": True,
            "title": title,
            "media": media,
            "year": year,
            "fetched_at": int(time.time()),
        }
        _save_meta(meta)
        return {"key": key, "cached": False, "found": False, "poster_url": ""}

    tmdb_id = hit.get("tmdb_id") or key
    filename = f"{hit.get('media') or media}_{tmdb_id}.jpg"
    dest = IMG_DIR / filename
    try:
        ok = _download_poster(str(hit["poster_path"]), dest)
    except Exception as exc:
        return {
            "key": key,
            "cached": False,
            "found": False,
            "poster_url": "",
            "error": f"Téléchargement affiche : {exc}",
        }
    if not ok:
        return {"key": key, "cached": False, "found": False, "poster_url": ""}

    meta[key] = {
        "miss": False,
        "title": title,
        "media": hit.get("media") or media,
        "year": year,
        "tmdb_id": tmdb_id,
        "matched_title": hit.get("matched_title") or title,
        "overview": hit.get("overview") or "",
        "poster_path": hit.get("poster_path"),
        "file": filename,
        "fetched_at": int(time.time()),
    }
    _save_meta(meta)
    return {
        "key": key,
        "cached": False,
        "found": True,
        "tmdb_id": tmdb_id,
        "matched_title": hit.get("matched_title") or title,
        "overview": hit.get("overview") or "",
        "poster_url": f"/api/library/poster/{quote(key)}",
        "media": hit.get("media") or media,
    }


def poster_file_for_key(key: str) -> Path | None:
    meta = _load_meta()
    entry = meta.get(key)
    if not isinstance(entry, dict) or entry.get("miss"):
        return None
    name = entry.get("file") or ""
    if not name:
        return None
    path = IMG_DIR / Path(name).name
    return path if path.is_file() else None


def enrich_entries(
    api_key: str,
    entries: list[dict[str, Any]],
    *,
    language: str = "fr-FR",
    on_progress=None,
    max_items: int = 80,
) -> dict[str, Any]:
    """
    Enrichit une liste d’entrées {id, title, type, year?}.
    Retourne {posters: {id: {...}}, stats}.
    """
    posters: dict[str, Any] = {}
    stats = {"total": 0, "found": 0, "cached": 0, "miss": 0, "errors": 0}
    cleaned: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in entries:
        if not isinstance(raw, dict):
            continue
        eid = str(raw.get("id") or "").strip()
        title = str(raw.get("title") or "").strip()
        if not eid or not title:
            continue
        if eid in seen:
            continue
        seen.add(eid)
        year = raw.get("year")
        try:
            year_i = int(year) if year is not None and str(year).strip() != "" else None
        except (TypeError, ValueError):
            year_i = None
        cleaned.append(
            {
                "id": eid,
                "title": title,
                "type": str(raw.get("type") or "movie"),
                "year": year_i,
            }
        )
        if len(cleaned) >= max_items:
            break

    total = len(cleaned)
    for idx, item in enumerate(cleaned):
        stats["total"] += 1
        if on_progress:
            on_progress(
                {
                    "phase": "tmdb",
                    "percent": int(100 * idx / max(1, total)),
                    "message": f"Affiches TMDB… {idx + 1}/{total} — {item['title']}",
                    "index": idx + 1,
                    "total": total,
                }
            )
        result = resolve_poster(
            api_key,
            title=item["title"],
            media=item["type"],
            year=item["year"],
            language=language,
        )
        if result.get("error") and result["error"] not in ("no_key",):
            stats["errors"] += 1
        elif result.get("found"):
            stats["found"] += 1
            if result.get("cached"):
                stats["cached"] += 1
            posters[item["id"]] = {
                "poster_url": result.get("poster_url") or "",
                "matched_title": result.get("matched_title") or item["title"],
                "overview": result.get("overview") or "",
                "tmdb_id": result.get("tmdb_id"),
                "cached": bool(result.get("cached")),
            }
        else:
            stats["miss"] += 1

    if on_progress:
        on_progress(
            {
                "phase": "done",
                "percent": 100,
                "message": f"Affiches : {stats['found']} trouvées ({stats['cached']} cache).",
            }
        )
    return {"posters": posters, "stats": stats}
