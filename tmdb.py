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
_MIN_INTERVAL = 0.05  # ~20 req/s API — sous la limite TMDB (~40/10s)
_throttle_lock = None
_thread_local = None
_meta_lock = None
_overrides_lock = None


def _locks():
    global _meta_lock, _overrides_lock, _throttle_lock, _thread_local
    import threading

    if _meta_lock is None:
        _meta_lock = threading.Lock()
    if _overrides_lock is None:
        _overrides_lock = threading.Lock()
    if _throttle_lock is None:
        _throttle_lock = threading.Lock()
    if _thread_local is None:
        _thread_local = threading.local()
    return _meta_lock, _overrides_lock


def _http() -> requests.Session:
    """Session HTTP réutilisée par thread (connexion keep-alive)."""
    _locks()
    import threading

    global _thread_local
    if _thread_local is None:
        _thread_local = threading.local()
    sess = getattr(_thread_local, "session", None)
    if sess is None:
        sess = requests.Session()
        _thread_local.session = sess
    return sess


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
    """Limite globale thread-safe pour l’API TMDB (pas pour le CDN images)."""
    global _LAST_REQUEST
    _locks()
    assert _throttle_lock is not None
    with _throttle_lock:
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
    res = _http().get(url, params=query, timeout=15)
    if res.status_code == 401:
        raise PermissionError("Clé API TMDB invalide.")
    if res.status_code == 429:
        time.sleep(1.0)
        res = _http().get(url, params=query, timeout=15)
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
    text = re.sub(r"\s*\(\d{4}\)\s*$", "", text)  # "Titre (2020)" → "Titre"
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
    # CDN images.tmdb.org — pas soumis au quota API, pas de throttle API
    url = f"{TMDB_IMG}{poster_path}"
    res = _http().get(url, timeout=15)
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
    overrides: dict[str, Any] | None = None,
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
        ov_map = overrides if overrides is not None else _load_overrides()
        ov = ov_map.get(entry_id)
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
    max_items: int = 400,
    workers: int = 10,
) -> dict[str, Any]:
    """
    Enrichit une liste d’entrées {id, title, type, year?}.
    Phase 1 : cache local (instantané). Phase 2 : fetch TMDB en parallèle.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading

    posters: dict[str, Any] = {}
    posters_lock = threading.Lock()
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
    overrides = _load_overrides()
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
            overrides=overrides,
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
                "posters": dict(posters),
                "stats": dict(stats),
            }
        )

    meta_lock = threading.Lock()

    def work_safe(item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        local_meta: dict[str, Any] = {}
        result = resolve_poster(
            api_key,
            title=item["title"],
            media=item["type"],
            year=item["year"],
            language=language,
            entry_id=item["id"],
            meta=local_meta,
            overrides=overrides,
            save=False,
            force=True,
        )
        if local_meta:
            with meta_lock:
                meta.update(local_meta)
        return item["id"], result

    done = total - len(to_fetch)
    if to_fetch:
        n_workers = max(2, min(12, workers))
        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures = [pool.submit(work_safe, item) for item in to_fetch]
            for fut in as_completed(futures):
                done += 1
                try:
                    eid, result = fut.result()
                except Exception:
                    stats["errors"] += 1
                    if on_progress:
                        on_progress(
                            {
                                "phase": "tmdb",
                                "percent": int(100 * done / max(1, total)),
                                "message": f"Affiches TMDB… {done}/{total}",
                                "index": done,
                                "total": total,
                                "posters": dict(posters),
                                "stats": dict(stats),
                            }
                        )
                    continue
                if result.get("error") and result["error"] not in ("no_key",):
                    stats["errors"] += 1
                elif result.get("found"):
                    stats["found"] += 1
                    entry_poster = {
                        "poster_url": result.get("poster_url") or "",
                        "matched_title": result.get("matched_title") or "",
                        "overview": result.get("overview") or "",
                        "tmdb_id": result.get("tmdb_id"),
                        "cached": False,
                    }
                    with posters_lock:
                        posters[eid] = entry_poster
                else:
                    stats["miss"] += 1
                if on_progress and (done % 3 == 0 or done >= total):
                    with posters_lock:
                        snap = dict(posters)
                    on_progress(
                        {
                            "phase": "tmdb",
                            "percent": int(100 * done / max(1, total)),
                            "message": f"Affiches TMDB… {done}/{total}",
                            "index": done,
                            "total": total,
                            "posters": snap,
                            "stats": dict(stats),
                        }
                    )

    _save_meta(meta)

    if on_progress:
        on_progress(
            {
                "phase": "done",
                "percent": 100,
                "message": f"Affiches : {stats['found']} trouvées ({stats['cached']} cache).",
                "posters": dict(posters),
                "stats": dict(stats),
            }
        )
    return {"posters": posters, "stats": stats}


# ─── Catalogue TV / épisodes manquants ──────────────────────────────────────

CATALOG_PATH = POSTERS_DIR / "tv_catalog.json"


def _load_catalog_cache() -> dict[str, Any]:
    _ensure_dirs()
    if not CATALOG_PATH.is_file():
        return {}
    try:
        with open(CATALOG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_catalog_cache(cache: dict[str, Any]) -> None:
    _ensure_dirs()
    lock, _ = _locks()
    with lock:
        with open(CATALOG_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)


def fetch_tv_catalog(
    api_key: str,
    *,
    title: str = "",
    year: int | None = None,
    tmdb_id: int | None = None,
    language: str = "fr-FR",
    force: bool = False,
) -> dict[str, Any]:
    """
    Récupère le guide des saisons/épisodes TMDB pour une série.
    Utilise un cache local (tv_catalog.json) pour limiter les appels.
    """
    key = ""
    if tmdb_id:
        key = f"id:{int(tmdb_id)}"
    else:
        key = cache_key(title, "tv", year)

    cache = _load_catalog_cache()
    cached = cache.get(key) if isinstance(cache.get(key), dict) else None
    if cached and not force and (cached.get("seasons") is not None):
        age = int(time.time()) - int(cached.get("fetched_at") or 0)
        if age < 86400 * 14:  # 14 jours
            return {**cached, "cached": True}

    tid = int(tmdb_id) if tmdb_id else None
    if tid is None:
        hit = search_tmdb(
            api_key.strip(),
            title=title,
            media="tv",
            year=year,
            language=language,
        )
        if not hit or not hit.get("tmdb_id"):
            return {
                "found": False,
                "error": "Série introuvable sur TMDB.",
                "title": title,
                "year": year,
            }
        tid = int(hit["tmdb_id"])
        key = f"id:{tid}"

    data = _get(api_key.strip(), f"/tv/{tid}", {"language": language})
    seasons_out: list[dict[str, Any]] = []
    for s in data.get("seasons") or []:
        try:
            sn = int(s.get("season_number"))
        except (TypeError, ValueError):
            continue
        if sn < 1:
            continue  # ignore « Specials »
        try:
            ep_count = int(s.get("episode_count") or 0)
        except (TypeError, ValueError):
            ep_count = 0
        if ep_count <= 0:
            continue
        seasons_out.append(
            {
                "season": sn,
                "episode_count": ep_count,
                "name": s.get("name") or f"Saison {sn:02d}",
            }
        )
    seasons_out.sort(key=lambda x: x["season"])

    year_s = (data.get("first_air_date") or "")[:4]
    result = {
        "found": True,
        "cached": False,
        "tmdb_id": tid,
        "matched_title": data.get("name") or title,
        "year": int(year_s) if year_s.isdigit() else year,
        "number_of_seasons": int(data.get("number_of_seasons") or len(seasons_out) or 0),
        "number_of_episodes": int(data.get("number_of_episodes") or 0),
        "seasons": seasons_out,
        "fetched_at": int(time.time()),
    }
    cache[key] = {k: v for k, v in result.items() if k != "cached"}
    cache[cache_key(title or result["matched_title"], "tv", result.get("year"))] = cache[key]
    _save_catalog_cache(cache)
    return result


def compare_series_gaps(
    local_seasons: list[dict[str, Any]],
    catalog: dict[str, Any],
) -> dict[str, Any]:
    """
    Compare inventaire local vs catalogue TMDB.
    local_seasons: [{season, episodes: [{episode}, ...] ou episodes: [1,2,3]}]
    """
    present: dict[int, set[int]] = {}
    for block in local_seasons or []:
        try:
            sn = int(block.get("season"))
        except (TypeError, ValueError):
            continue
        if sn < 1:
            continue
        eps_raw = block.get("episodes") or []
        got: set[int] = set()
        for ep in eps_raw:
            if isinstance(ep, dict):
                val = ep.get("episode")
            else:
                val = ep
            try:
                if val is not None:
                    got.add(int(val))
            except (TypeError, ValueError):
                continue
        if got:
            present[sn] = present.get(sn, set()) | got

    missing_seasons: list[dict[str, Any]] = []
    missing_episodes: list[dict[str, Any]] = []
    complete_seasons: list[int] = []

    for season in catalog.get("seasons") or []:
        sn = int(season["season"])
        expected_n = int(season.get("episode_count") or 0)
        if expected_n <= 0:
            continue
        expected = set(range(1, expected_n + 1))
        have = present.get(sn, set())
        if not have:
            missing_seasons.append(
                {
                    "season": sn,
                    "episode_count": expected_n,
                    "label": f"Saison {sn:02d}",
                    "missing_labels": [f"S{sn:02d}E{e:02d}" for e in range(1, expected_n + 1)],
                }
            )
            continue
        miss = sorted(expected - have)
        if miss:
            missing_episodes.append(
                {
                    "season": sn,
                    "have": len(have & expected),
                    "expected": expected_n,
                    "missing": miss,
                    "missing_labels": [f"S{sn:02d}E{e:02d}" for e in miss],
                }
            )
        else:
            complete_seasons.append(sn)

    # Saisons locales absentes du catalogue (ex. mauvaise série TMDB)
    extra_local = sorted(set(present) - {int(s["season"]) for s in (catalog.get("seasons") or [])})

    all_labels: list[str] = []
    for ms in missing_seasons:
        all_labels.extend(ms["missing_labels"])
    for me in missing_episodes:
        all_labels.extend(me["missing_labels"])

    return {
        "missing_seasons": missing_seasons,
        "missing_episodes": missing_episodes,
        "complete_seasons": complete_seasons,
        "extra_local_seasons": extra_local,
        "missing_labels": all_labels,
        "missing_count": len(all_labels),
        "present_episode_count": sum(len(v) for v in present.values()),
        "catalog_episode_count": sum(
            int(s.get("episode_count") or 0) for s in (catalog.get("seasons") or [])
        ),
    }


def find_series_gaps(
    api_key: str,
    *,
    title: str,
    year: int | None = None,
    tmdb_id: int | None = None,
    local_seasons: list[dict[str, Any]] | None = None,
    language: str = "fr-FR",
    force: bool = False,
) -> dict[str, Any]:
    """Point d’entrée : catalogue TMDB + comparaison locale."""
    if not (api_key or "").strip():
        return {"found": False, "error": "no_key"}
    catalog = fetch_tv_catalog(
        api_key,
        title=title,
        year=year,
        tmdb_id=tmdb_id,
        language=language,
        force=force,
    )
    if not catalog.get("found"):
        return catalog
    gaps = compare_series_gaps(local_seasons or [], catalog)
    summary = ""
    if gaps["missing_count"] == 0:
        summary = "Complet par rapport à TMDB (hors éventuels spéciaux)."
    else:
        bits = []
        if gaps["missing_seasons"]:
            bits.append(f"{len(gaps['missing_seasons'])} saison(s) absente(s)")
        if gaps["missing_episodes"]:
            n_ep = sum(len(x["missing"]) for x in gaps["missing_episodes"])
            bits.append(f"{n_ep} épisode(s) manquant(s)")
        summary = " · ".join(bits)
    return {
        "found": True,
        "title": title,
        "catalog": {
            "tmdb_id": catalog.get("tmdb_id"),
            "matched_title": catalog.get("matched_title"),
            "year": catalog.get("year"),
            "number_of_seasons": catalog.get("number_of_seasons"),
            "seasons": catalog.get("seasons"),
            "cached": catalog.get("cached"),
        },
        "gaps": gaps,
        "summary": summary,
    }


# ─── Collections films (suites) ─────────────────────────────────────────────

COLLECTION_PATH = POSTERS_DIR / "movie_collections.json"


def _load_collection_cache() -> dict[str, Any]:
    _ensure_dirs()
    if not COLLECTION_PATH.is_file():
        return {}
    try:
        with open(COLLECTION_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_collection_cache(cache: dict[str, Any]) -> None:
    _ensure_dirs()
    lock, _ = _locks()
    with lock:
        with open(COLLECTION_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)


def _norm_title_key(value: str) -> str:
    text = (value or "").lower()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^a-z0-9àâäéèêëïîôùûüç]+", "", text)
    return text.strip()


def fetch_movie_collection(
    api_key: str,
    *,
    collection_id: int,
    language: str = "fr-FR",
    force: bool = False,
) -> dict[str, Any]:
    """Charge une collection TMDB (cache 30 jours)."""
    key = f"col:{int(collection_id)}"
    cache = _load_collection_cache()
    cached = cache.get(key) if isinstance(cache.get(key), dict) else None
    if cached and not force:
        age = int(time.time()) - int(cached.get("fetched_at") or 0)
        if age < 86400 * 30 and cached.get("parts") is not None:
            return {**cached, "cached": True}

    data = _get(api_key.strip(), f"/collection/{int(collection_id)}", {"language": language})
    parts_out: list[dict[str, Any]] = []
    for part in data.get("parts") or []:
        if not isinstance(part, dict):
            continue
        try:
            pid = int(part.get("id"))
        except (TypeError, ValueError):
            continue
        year_s = (part.get("release_date") or "")[:4]
        title = (part.get("title") or part.get("original_title") or "").strip()
        if not title:
            continue
        parts_out.append(
            {
                "tmdb_id": pid,
                "title": title,
                "original_title": (part.get("original_title") or "").strip(),
                "year": int(year_s) if year_s.isdigit() else None,
                "release_date": part.get("release_date") or "",
            }
        )
    parts_out.sort(key=lambda p: (p.get("year") is None, p.get("year") or 0, p.get("title") or ""))
    result = {
        "found": True,
        "collection_id": int(collection_id),
        "name": (data.get("name") or "").strip() or f"Collection {collection_id}",
        "overview": (data.get("overview") or "")[:400],
        "parts": parts_out,
        "part_count": len(parts_out),
        "fetched_at": int(time.time()),
    }
    cache[key] = {k: v for k, v in result.items() if k != "cached"}
    _save_collection_cache(cache)
    return result


def resolve_movie_collection_id(
    api_key: str,
    *,
    title: str = "",
    year: int | None = None,
    tmdb_id: int | None = None,
    language: str = "fr-FR",
) -> dict[str, Any]:
    """Retourne l’id de collection TMDB pour un film (ou found=False)."""
    tid = int(tmdb_id) if tmdb_id else None
    if tid is None:
        hit = search_tmdb(
            api_key.strip(),
            title=title,
            media="movie",
            year=year,
            language=language,
        )
        if not hit or not hit.get("tmdb_id"):
            return {"found": False, "error": "Film introuvable sur TMDB.", "title": title}
        tid = int(hit["tmdb_id"])

    data = _get(api_key.strip(), f"/movie/{tid}", {"language": language})
    coll = data.get("belongs_to_collection")
    if not isinstance(coll, dict) or not coll.get("id"):
        return {
            "found": False,
            "solo": True,
            "tmdb_id": tid,
            "title": data.get("title") or title,
            "error": "Pas de saga / collection TMDB.",
        }
    return {
        "found": True,
        "tmdb_id": tid,
        "title": data.get("title") or title,
        "collection_id": int(coll["id"]),
        "collection_name": (coll.get("name") or "").strip(),
    }


def compare_movie_collection(
    local_movies: list[dict[str, Any]],
    parts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare films locaux vs parties d’une collection TMDB."""
    have_ids: set[int] = set()
    have_keys: set[tuple[str, int | None]] = set()
    have_titles: set[str] = set()
    for raw in local_movies or []:
        if not isinstance(raw, dict):
            continue
        try:
            if raw.get("tmdb_id") is not None and str(raw.get("tmdb_id")).strip() != "":
                have_ids.add(int(raw["tmdb_id"]))
        except (TypeError, ValueError):
            pass
        title = (raw.get("title") or "").strip()
        year = raw.get("year")
        try:
            year_i = int(year) if year is not None and str(year).strip() != "" else None
        except (TypeError, ValueError):
            year_i = None
        key = _norm_title_key(title)
        if key:
            have_titles.add(key)
            have_keys.add((key, year_i))

    present: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for part in parts or []:
        pid = int(part["tmdb_id"])
        title = part.get("title") or ""
        year = part.get("year")
        nkey = _norm_title_key(title)
        owned = (
            pid in have_ids
            or (nkey, year) in have_keys
            or (nkey in have_titles and year is None)
            or nkey in have_titles
        )
        entry = {
            "tmdb_id": pid,
            "title": title,
            "year": year,
            "owned": bool(owned),
        }
        if owned:
            present.append(entry)
        else:
            missing.append(entry)

    return {
        "present": present,
        "missing": missing,
        "present_count": len(present),
        "missing_count": len(missing),
        "part_count": len(parts or []),
    }


def find_movie_collections_gaps(
    api_key: str,
    movies: list[dict[str, Any]],
    *,
    language: str = "fr-FR",
    force: bool = False,
    max_movies: int = 60,
) -> dict[str, Any]:
    """
    Pour une liste de films locaux, détecte les sagas TMDB et les suites manquantes.
    """
    if not (api_key or "").strip():
        return {"found": False, "error": "no_key", "results": []}

    # Index local enrichi (résolution tmdb_id si besoin)
    locals_enriched: list[dict[str, Any]] = []
    collection_locals: dict[int, list[dict[str, Any]]] = {}
    collection_meta: dict[int, str] = {}
    scanned = 0
    solos = 0
    errors = 0

    for raw in (movies or [])[: max(1, min(120, max_movies))]:
        if not isinstance(raw, dict):
            continue
        title = (raw.get("title") or "").strip()
        if not title:
            continue
        scanned += 1
        year = raw.get("year")
        try:
            year_i = int(year) if year is not None and str(year).strip() != "" else None
        except (TypeError, ValueError):
            year_i = None
        tmdb_id = raw.get("tmdb_id")
        try:
            tmdb_id_i = (
                int(tmdb_id) if tmdb_id is not None and str(tmdb_id).strip() != "" else None
            )
        except (TypeError, ValueError):
            tmdb_id_i = None

        try:
            link = resolve_movie_collection_id(
                api_key,
                title=title,
                year=year_i,
                tmdb_id=tmdb_id_i,
                language=language,
            )
        except Exception:
            errors += 1
            continue

        entry = {
            "title": title,
            "year": year_i,
            "tmdb_id": link.get("tmdb_id") or tmdb_id_i,
            "identity": raw.get("identity") or "",
        }
        locals_enriched.append(entry)
        if not link.get("found"):
            if link.get("solo"):
                solos += 1
            else:
                errors += 1
            continue
        cid = int(link["collection_id"])
        collection_locals.setdefault(cid, []).append(entry)
        if link.get("collection_name"):
            collection_meta[cid] = str(link["collection_name"])

    results: list[dict[str, Any]] = []
    incomplete = 0
    for cid, owned in collection_locals.items():
        try:
            coll = fetch_movie_collection(
                api_key, collection_id=cid, language=language, force=force
            )
        except Exception as exc:
            results.append(
                {
                    "found": False,
                    "collection_id": cid,
                    "name": collection_meta.get(cid) or f"Collection {cid}",
                    "error": str(exc),
                }
            )
            continue
        if not coll.get("found"):
            continue
        # Inclure tous les films locaux qui matchent n’importe quelle partie
        # (pas seulement ceux qui ont déclenché la collection)
        gaps = compare_movie_collection(locals_enriched, coll.get("parts") or [])
        # Ne garder que les collections où on a au moins 1 film local
        if gaps["present_count"] <= 0:
            continue
        # Ignorer les « collections » d’un seul film
        if gaps["part_count"] < 2:
            continue
        miss = gaps["missing_count"]
        if miss:
            incomplete += 1
            summary = (
                f"{gaps['present_count']}/{gaps['part_count']} film(s) · "
                f"{miss} suite(s) manquante(s)"
            )
        else:
            summary = f"Complet · {gaps['part_count']} film(s) dans la saga"
        results.append(
            {
                "found": True,
                "kind": "collection",
                "collection_id": cid,
                "name": coll.get("name") or collection_meta.get(cid) or f"Collection {cid}",
                "parts": coll.get("parts") or [],
                "gaps": gaps,
                "summary": summary,
            }
        )

    results.sort(
        key=lambda r: (
            0 if (r.get("gaps") or {}).get("missing_count") else 1,
            (r.get("name") or "").lower(),
        )
    )
    return {
        "found": True,
        "scanned": scanned,
        "collections": len(results),
        "incomplete": incomplete,
        "solos": solos,
        "errors": errors,
        "results": results,
    }
