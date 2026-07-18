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
TMDB_IMG = "https://image.tmdb.org/t/p/w185"
TMDB_IMG_PREVIEW = "https://image.tmdb.org/t/p/w92"
POSTERS_DIR = DATA_DIR / "posters"
META_PATH = POSTERS_DIR / "meta.json"
OVERRIDES_PATH = POSTERS_DIR / "overrides.json"
IMG_DIR = POSTERS_DIR / "img"

_LAST_REQUEST = 0.0
_MIN_INTERVAL = 0.08  # ~12 req/s — sous la limite TMDB (~40/10s)
_meta_lock = None
_overrides_lock = None


def _locks():
    global _meta_lock, _overrides_lock
    import threading

    if _meta_lock is None:
        _meta_lock = threading.Lock()
    if _overrides_lock is None:
        _overrides_lock = threading.Lock()
    return _meta_lock, _overrides_lock


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
    lock, _ = _locks()
    with lock:
        with open(META_PATH, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)


def _load_overrides() -> dict[str, Any]:
    _ensure_dirs()
    if not OVERRIDES_PATH.is_file():
        return {}
    try:
        with open(OVERRIDES_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_overrides(data: dict[str, Any]) -> None:
    _ensure_dirs()
    _, lock = _locks()
    with lock:
        with open(OVERRIDES_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


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
    results = search_tmdb_list(
        api_key,
        query=title,
        media=media,
        year=year,
        language=language,
        limit=1,
    )
    return results[0] if results else None


def search_tmdb_list(
    api_key: str,
    *,
    query: str,
    media: str = "tv",
    year: int | None = None,
    language: str = "fr-FR",
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Recherche TMDB — retourne jusqu’à `limit` candidats (sans télécharger)."""
    q = _clean_query(query)
    if not q:
        return []
    kind = "tv" if media in ("tv", "anime", "archive") else "movie"
    path = "/search/tv" if kind == "tv" else "/search/movie"
    params: dict[str, Any] = {
        "query": q,
        "language": language,
        "include_adult": "false",
    }
    if year is not None:
        if kind == "tv":
            params["first_air_date_year"] = int(year)
        else:
            params["year"] = int(year)
    data = _get(api_key, path, params)
    raw = data.get("results") or []
    if not isinstance(raw, list):
        raw = []
    # Si rien avec année, un seul retry sans filtre année
    if not raw and year is not None:
        params.pop("year", None)
        params.pop("first_air_date_year", None)
        data = _get(api_key, path, params)
        raw = data.get("results") or []
        if not isinstance(raw, list):
            raw = []

    out: list[dict[str, Any]] = []
    for item in raw[: max(1, min(20, limit))]:
        poster_path = item.get("poster_path") or ""
        matched = item.get("name") or item.get("title") or q
        year_s = (item.get("first_air_date") or item.get("release_date") or "")[:4]
        out.append(
            {
                "tmdb_id": item.get("id"),
                "media": kind,
                "matched_title": matched,
                "original_title": item.get("original_name") or item.get("original_title") or "",
                "poster_path": poster_path,
                "preview_url": f"{TMDB_IMG_PREVIEW}{poster_path}" if poster_path else "",
                "year": int(year_s) if year_s.isdigit() else None,
                "overview": (item.get("overview") or "")[:280],
            }
        )
    return out


def _download_poster(poster_path: str, dest: Path) -> bool:
    if not poster_path or not str(poster_path).startswith("/"):
        return False
    if dest.is_file() and dest.stat().st_size > 0:
        return True
    _throttle()
    url = f"{TMDB_IMG}{poster_path}"
    res = requests.get(url, timeout=20)
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
    entry_id: str | None = None,
    meta: dict[str, Any] | None = None,
    save: bool = True,
    cache_only: bool = False,
) -> dict[str, Any]:
    """
    Retourne les infos poster pour un titre (cache disque prioritaire).
    Si `entry_id` a un override manuel, il prime.
    `cache_only=True` : ne touche pas au réseau.
    """
    key = cache_key(title, media, year)
    if entry_id:
        overrides = _load_overrides()
        ov = overrides.get(entry_id)
        if isinstance(ov, dict) and ov.get("file"):
            path = IMG_DIR / Path(str(ov["file"])).name
            if path.is_file():
                return {
                    "key": key,
                    "cached": True,
                    "found": True,
                    "override": True,
                    "tmdb_id": ov.get("tmdb_id"),
                    "matched_title": ov.get("matched_title") or title,
                    "overview": ov.get("overview") or "",
                    "poster_url": f"/api/library/poster/{quote(key)}?entry={quote(entry_id)}",
                    "media": ov.get("media") or media,
                }

    own_meta = meta is None
    if meta is None:
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

    if cache_only:
        return {
            "key": key,
            "cached": False,
            "found": False,
            "poster_url": "",
            "needs_fetch": True,
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
        if save and own_meta:
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
    if save and own_meta:
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


def assign_poster(
    api_key: str,
    *,
    entry_id: str,
    title: str,
    media: str,
    tmdb_id: int,
    tmdb_media: str | None = None,
    language: str = "fr-FR",
    year: int | None = None,
) -> dict[str, Any]:
    """Associe manuellement une entrée bibliothèque à un résultat TMDB."""
    eid = str(entry_id or "").strip()
    if not eid:
        raise ValueError("Identifiant d’entrée manquant.")
    kind = "tv" if (tmdb_media or media) in ("tv", "anime", "archive") else "movie"
    path = f"/{kind}/{int(tmdb_id)}"
    data = _get(api_key, path, {"language": language})
    poster_path = data.get("poster_path") or ""
    matched = data.get("name") or data.get("title") or title
    overview = (data.get("overview") or "")[:280]
    year_s = (data.get("first_air_date") or data.get("release_date") or "")[:4]
    key = cache_key(title, media, year)
    filename = f"{kind}_{int(tmdb_id)}.jpg"
    dest = IMG_DIR / filename
    if poster_path:
        _download_poster(poster_path, dest)
    if not dest.is_file():
        raise OSError("Impossible de télécharger l’affiche TMDB.")

    # Cache générique + override par entrée
    meta = _load_meta()
    meta[key] = {
        "miss": False,
        "title": title,
        "media": kind,
        "year": year,
        "tmdb_id": int(tmdb_id),
        "matched_title": matched,
        "overview": overview,
        "poster_path": poster_path,
        "file": filename,
        "fetched_at": int(time.time()),
        "manual": True,
    }
    _save_meta(meta)
    overrides = _load_overrides()
    overrides[eid] = {
        "tmdb_id": int(tmdb_id),
        "media": kind,
        "matched_title": matched,
        "overview": overview,
        "year": int(year_s) if year_s.isdigit() else year,
        "file": filename,
        "poster_path": poster_path,
        "key": key,
        "fetched_at": int(time.time()),
    }
    _save_overrides(overrides)
    return {
        "entry_id": eid,
        "found": True,
        "tmdb_id": int(tmdb_id),
        "matched_title": matched,
        "overview": overview,
        "poster_url": f"/api/library/poster/{quote(key)}?entry={quote(eid)}",
        "media": kind,
        "year": overrides[eid].get("year"),
    }


def poster_file_for_key(key: str, entry_id: str | None = None) -> Path | None:
    if entry_id:
        ov = _load_overrides().get(entry_id)
        if isinstance(ov, dict) and ov.get("file"):
            path = IMG_DIR / Path(str(ov["file"])).name
            if path.is_file():
                return path
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
    max_items: int = 120,
    workers: int = 6,
) -> dict[str, Any]:
    """
    Enrichit une liste d’entrées {id, title, type, year?}.
    Phase 1 : cache local (instantané). Phase 2 : fetch TMDB en parallèle.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading

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
    meta = _load_meta()
    to_fetch: list[dict[str, Any]] = []

    # Phase 1 — cache / overrides uniquement
    for item in cleaned:
        stats["total"] += 1
        result = resolve_poster(
            api_key,
            title=item["title"],
            media=item["type"],
            year=item["year"],
            language=language,
            entry_id=item["id"],
            meta=meta,
            save=False,
            cache_only=True,
        )
        if result.get("found"):
            stats["found"] += 1
            stats["cached"] += 1
            posters[item["id"]] = {
                "poster_url": result.get("poster_url") or "",
                "matched_title": result.get("matched_title") or "",
                "overview": result.get("overview") or "",
                "tmdb_id": result.get("tmdb_id"),
                "cached": True,
                "override": bool(result.get("override")),
            }
        elif result.get("cached") and not result.get("found"):
            stats["miss"] += 1
        else:
            to_fetch.append(item)

    if on_progress:
        on_progress(
            {
                "phase": "tmdb",
                "percent": int(100 * (total - len(to_fetch)) / max(1, total)),
                "message": f"Cache OK — fetch TMDB {len(to_fetch)} titre(s)…",
            }
        )

    meta_lock = threading.Lock()

    def work(item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        with meta_lock:
            result = resolve_poster(
                api_key,
                title=item["title"],
                media=item["type"],
                year=item["year"],
                language=language,
                entry_id=item["id"],
                meta=meta,
                save=False,
                force=True,
            )
        return item["id"], result

    done = total - len(to_fetch)
    if to_fetch:
        with ThreadPoolExecutor(max_workers=max(2, min(8, workers))) as pool:
            futures = [pool.submit(work, item) for item in to_fetch]
            for fut in as_completed(futures):
                done += 1
                if on_progress:
                    on_progress(
                        {
                            "phase": "tmdb",
                            "percent": int(100 * done / max(1, total)),
                            "message": f"Affiches TMDB… {done}/{total}",
                            "index": done,
                            "total": total,
                        }
                    )
                try:
                    eid, result = fut.result()
                except Exception:
                    stats["errors"] += 1
                    continue
                if result.get("error") and result["error"] not in ("no_key",):
                    stats["errors"] += 1
                elif result.get("found"):
                    stats["found"] += 1
                    posters[eid] = {
                        "poster_url": result.get("poster_url") or "",
                        "matched_title": result.get("matched_title") or "",
                        "overview": result.get("overview") or "",
                        "tmdb_id": result.get("tmdb_id"),
                        "cached": False,
                    }
                else:
                    stats["miss"] += 1

    _save_meta(meta)

    if on_progress:
        on_progress(
            {
                "phase": "done",
                "percent": 100,
                "message": f"Affiches : {stats['found']} trouvées ({stats['cached']} cache).",
            }
        )
    return {"posters": posters, "stats": stats}
