"""Scan bibliothèque média — inventaire lecture seule (phase 1)."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

import smart_naming

ARCHIVE_EXTS = {".zip", ".rar", ".7z"}

_IDENTITY_RE = re.compile(r"[^a-z0-9]+")
# Saison seule dans un nom d’archive : S03, Saison 3, Season 03
_SEASON_ONLY_RE = re.compile(
    r"(?:^|[\s._\-\[(])(?:Saison|Season|S)[\s._\-]*(\d{1,2})(?![\s._\-]*E\d)",
    re.IGNORECASE,
)


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def normalize_title(title: str) -> str:
    """Titre comparable : minuscules, sans accents, alphanum uniquement."""
    raw = _strip_accents(str(title or "").lower().strip())
    raw = _IDENTITY_RE.sub("", raw)
    return raw or "inconnu"


def soft_series_key(title: str, year: int | None = None) -> str:
    """
    Clé de regroupement tolérante :
    - ignore le n° d'épisode en préfixe
    - normalise fautes fréquentes (tous/tout, double lettres finales)
    - sépare les reboot via l'année si connue
    """
    text = str(title or "")
    text = re.sub(r"^\d{1,3}\s*[-–.]?\s*", "", text).strip()
    key = normalize_title(text)
    # Variantes FR fréquentes
    replacements = (
        ("tousrisques", "toutrisques"),
        ("tousrisque", "toutrisques"),
        ("toutrisque", "toutrisques"),
        ("lagencetous", "lagencetout"),
        ("agencetous", "agencetout"),
    )
    for a, b in replacements:
        key = key.replace(a, b)
    # Double lettre finale typo (risquess → risques)
    key = re.sub(r"([a-z])\1+$", r"\1", key)
    if year is not None:
        try:
            return f"{key}|y{int(year)}"
        except (TypeError, ValueError):
            pass
    return key or "inconnu"


def media_identity(info: dict[str, Any]) -> str:
    """
    Clé stable pour doublons / diff (phases 3–4).
    Ex. defiance|s03e01  ou  inception|y2010  ou  defiance|s03|pack
    """
    media = info.get("type") or "other"
    title_key = normalize_title(info.get("title") or "")

    if media == "archive":
        season = info.get("season")
        episode = info.get("episode")
        if season is not None and episode is not None:
            try:
                return f"{title_key}|s{int(season):02d}e{int(episode):02d}|archive"
            except (TypeError, ValueError):
                pass
        if season is not None:
            try:
                return f"{title_key}|s{int(season):02d}|pack"
            except (TypeError, ValueError):
                pass
        year = info.get("year")
        if year is not None:
            try:
                return f"{title_key}|y{int(year)}|archive"
            except (TypeError, ValueError):
                pass
        original = Path(str(info.get("original") or "")).stem
        return f"{title_key}|archive|{normalize_title(original)[:40]}"

    if media in ("tv", "anime"):
        season = info.get("season")
        episode = info.get("episode")
        if season is not None and episode is not None:
            try:
                return f"{title_key}|s{int(season):02d}e{int(episode):02d}"
            except (TypeError, ValueError):
                pass
        if episode is not None:
            try:
                return f"{title_key}|e{int(episode):03d}"
            except (TypeError, ValueError):
                pass
        return f"{title_key}|{media}"

    if media == "movie":
        year = info.get("year")
        if year is not None:
            try:
                return f"{title_key}|y{int(year)}"
            except (TypeError, ValueError):
                pass
        return f"{title_key}|movie"

    original = Path(str(info.get("original") or "")).stem
    extra = normalize_title(original)[:40]
    return f"{title_key}|other|{extra}"


def _parse_archive(filename: str, template_id: str) -> dict[str, Any]:
    """Analyse un .zip / .rar / .7z (souvent une saison complète)."""
    info = smart_naming.suggest_name(filename, template_id=template_id)
    stem = Path(filename).stem
    season_pack = False
    fmt = Path(filename).suffix.lower().lstrip(".")
    has_episode_token = bool(
        smart_naming.TV_RE.search(stem) or smart_naming.TV_DOT_RE.search(stem)
    )
    has_saison_word = bool(re.search(r"(?:Saison|Season)", stem, re.I))

    season_m = re.search(r"(?:Saison|Season)[\s._\-]*(\d{1,2})", stem, re.I)
    if not season_m and not has_episode_token:
        season_m = _SEASON_ONLY_RE.search(stem)

    # Pack saison : mot Saison/Season, ou S03 sans E01
    if season_m and (has_saison_word or not has_episode_token):
        season = int(season_m.group(1))
        raw_title = stem[: season_m.start()].rstrip("._- []()")
        raw_title = re.sub(
            r"[\s._\-]*(?:Saison|Season)\s*$", "", raw_title, flags=re.I
        )
        title = (
            smart_naming._clean_title(raw_title)
            if raw_title
            else (info.get("title") or "Archive")
        )
        info = {
            **info,
            "title": title or info.get("title") or "Archive",
            "season": season,
            "episode": None,
            "original": filename,
        }
        season_pack = True
    elif info.get("season") is not None and info.get("episode") is None:
        season_pack = True

    return {
        **info,
        "type": "archive",
        "original": filename,
        "season_pack": season_pack,
        "archive_format": fmt,
    }


def scan_library(
    folder: str,
    *,
    recursive: bool = True,
    template_id: str = "simple",
    credentials: list[dict] | None = None,
    on_progress=None,
) -> dict[str, Any]:
    """
    Scanne un dossier et retourne un inventaire plat (pas de modification disque).
    Inclut les vidéos/audios et les archives (.zip / .rar / .7z).
    """
    try:
        import network_shares
        import settings as app_settings

        creds = credentials if credentials is not None else app_settings.get_network_shares()
        if on_progress:
            on_progress(
                {
                    "phase": "connect",
                    "percent": 2,
                    "message": "Connexion au dossier / NAS…",
                }
            )
        network_shares.ensure_path_access(folder, creds)
    except ImportError:
        pass

    root = Path(folder).expanduser()
    if not root.is_dir():
        raise FileNotFoundError(f"Dossier introuvable : {folder}")

    allowed = smart_naming.VIDEO_EXTS | smart_naming.AUDIO_EXTS | ARCHIVE_EXTS
    use_cache = True
    cache = _load_scan_cache(folder, recursive) if use_cache else None
    cached_items = {
        str(it.get("path") or ""): it
        for it in (cache.get("items") or [])
        if isinstance(it, dict) and it.get("path")
    } if cache else {}

    items: list[dict[str, Any]] = []
    scanned = 0
    reused = 0
    parsed = 0
    import os
    import time as _time

    t0 = _time.monotonic()

    if on_progress:
        on_progress(
            {
                "phase": "scan",
                "percent": 5,
                "message": "Parcours des fichiers…",
            }
        )

    root_str = str(root)
    for entry in _walk_media_files(root, recursive=recursive, allowed=allowed):
        scanned += 1
        if on_progress and scanned % 50 == 0:
            soft = min(90, 5 + int(scanned ** 0.55))
            on_progress(
                {
                    "phase": "scan",
                    "percent": soft,
                    "message": (
                        f"Scan… {len(items)} média(s) "
                        f"({reused} cache, {parsed} nouveaux)"
                    ),
                    "index": scanned,
                }
            )
        path_str = entry.path
        ext = os.path.splitext(entry.name)[1].lower()
        try:
            st = entry.stat(follow_symlinks=False)
            size = int(st.st_size)
            mtime = float(st.st_mtime)
        except OSError:
            size = 0
            mtime = 0.0

        prev = cached_items.get(path_str)
        if (
            prev
            and prev.get("size") == size
            and abs(float(prev.get("mtime") or 0) - mtime) < 0.01
            and prev.get("identity")
        ):
            items.append(prev)
            reused += 1
            continue

        if ext in ARCHIVE_EXTS:
            info = _parse_archive(entry.name, template_id)
        else:
            info = smart_naming.suggest_name(
                entry.name,
                template_id=template_id,
                path_hint=path_str,
                root_hint=root_str,
            )

        identity = media_identity(info)
        items.append(
            {
                "path": path_str,
                "filename": entry.name,
                "ext": ext,
                "size": size,
                "mtime": mtime,
                "type": info.get("type") or "other",
                "title": info.get("title") or "",
                "season": info.get("season"),
                "episode": info.get("episode"),
                "year": info.get("year"),
                "suggested": info.get("suggested") or entry.name,
                "identity": identity,
                "season_pack": bool(info.get("season_pack")),
                "archive_format": info.get("archive_format") or (
                    ext.lstrip(".") if ext in ARCHIVE_EXTS else ""
                ),
            }
        )
        parsed += 1

    if on_progress:
        on_progress(
            {
                "phase": "build",
                "percent": 95,
                "message": "Construction de la bibliothèque…",
            }
        )

    by_type = {"tv": 0, "anime": 0, "movie": 0, "archive": 0, "other": 0}
    identities: set[str] = set()
    archive_count = 0
    season_pack_count = 0
    for item in items:
        t = item["type"] if item["type"] in by_type else "other"
        by_type[t] = by_type.get(t, 0) + 1
        identities.add(item["identity"])
        if item["type"] == "archive":
            archive_count += 1
            if item.get("season_pack"):
                season_pack_count += 1

    items.sort(key=lambda x: (x.get("path") or "").lower())

    folder_out = str(root)
    try:
        if not folder_out.startswith("\\\\"):
            folder_out = str(root.resolve())
    except OSError:
        pass

    result = {
        "folder": folder_out,
        "recursive": recursive,
        "count": len(items),
        "unique_identities": len(identities),
        "archive_count": archive_count,
        "season_pack_count": season_pack_count,
        "by_type": by_type,
        "items": items,
        "tree": build_library_tree(items),
        "duplicates": find_duplicates(items),
        "cache": {
            "used": bool(cache),
            "reused": reused,
            "parsed": parsed,
            "scanned_entries": scanned,
            "elapsed_s": round(_time.monotonic() - t0, 2),
        },
    }
    _save_scan_cache(folder, recursive, result)
    return result


def _walk_media_files(root: Path, *, recursive: bool, allowed: set[str]):
    """Parcours rapide (os.scandir) — bien plus efficace sur NAS que Path.rglob+sorted."""
    import os

    stack = [str(root)]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            if recursive and not entry.name.startswith("."):
                                stack.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            ext = os.path.splitext(entry.name)[1].lower()
                            if ext in allowed:
                                yield entry
                    except OSError:
                        continue
        except OSError:
            continue


def _cache_dir() -> Path:
    from paths import DATA_DIR

    d = DATA_DIR / "library_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_key(folder: str, recursive: bool) -> str:
    import hashlib

    raw = f"{folder.strip().lower()}|{'1' if recursive else '0'}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def _load_scan_cache(folder: str, recursive: bool) -> dict[str, Any] | None:
    import json

    path = _cache_dir() / f"{_cache_key(folder, recursive)}.json"
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            return data
    except (OSError, json.JSONDecodeError):
        return None
    return None


def _save_scan_cache(folder: str, recursive: bool, result: dict[str, Any]) -> None:
    import json
    import time as _time

    path = _cache_dir() / f"{_cache_key(folder, recursive)}.json"
    payload = {
        "folder": folder,
        "recursive": recursive,
        "saved_at": int(_time.time()),
        "count": result.get("count"),
        "items": result.get("items") or [],
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    except OSError:
        pass


def _series_key(item: dict[str, Any]) -> str:
    year = item.get("year")
    try:
        year_i = int(year) if year is not None else None
    except (TypeError, ValueError):
        year_i = None
    return soft_series_key(item.get("title") or "", year_i)


def _merge_similar_series(
    series_map: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Fusionne des clés proches (ratio élevé) si année compatible."""
    from difflib import SequenceMatcher

    keys = list(series_map.keys())
    parent: dict[str, str] = {k: k for k in keys}

    def find(k: str) -> str:
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    def year_of(k: str):
        if "|y" in k:
            try:
                return int(k.rsplit("|y", 1)[1])
            except ValueError:
                return None
        return series_map[k].get("year")

    def base_of(k: str) -> str:
        return k.split("|y", 1)[0]

    for i, a in enumerate(keys):
        for b in keys[i + 1 :]:
            ya, yb = year_of(a), year_of(b)
            if ya is not None and yb is not None and ya != yb:
                continue
            ba, bb = base_of(a), base_of(b)
            if not ba or not bb:
                continue
            if abs(len(ba) - len(bb)) > max(4, len(ba) // 3):
                continue
            if SequenceMatcher(None, ba, bb).ratio() >= 0.88:
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[rb] = ra

    merged: dict[str, dict[str, Any]] = {}
    for k, entry in series_map.items():
        root = find(k)
        if root not in merged:
            merged[root] = entry
            merged[root]["key"] = root
            continue
        target = merged[root]
        target["file_count"] += entry["file_count"]
        target["episode_count"] += entry["episode_count"]
        target["kinds"] |= entry["kinds"]
        if len(entry.get("title") or "") > len(target.get("title") or ""):
            target["title"] = entry["title"]
        if target.get("year") is None and entry.get("year") is not None:
            target["year"] = entry["year"]
        for season_n, block in entry["seasons"].items():
            if season_n not in target["seasons"]:
                target["seasons"][season_n] = {"season": season_n, "episodes": []}
            target["seasons"][season_n]["episodes"].extend(block["episodes"])
    return merged


def build_library_tree(items: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Phase 2 — regroupe l’inventaire :
    séries → saisons → épisodes | films | archives | autres
    """
    series_map: dict[str, dict[str, Any]] = {}
    movies: list[dict[str, Any]] = []
    archives: list[dict[str, Any]] = []
    others: list[dict[str, Any]] = []

    for item in items:
        media = item.get("type") or "other"
        if media in ("tv", "anime"):
            key = _series_key(item)
            if key not in series_map:
                series_map[key] = {
                    "key": key,
                    "title": item.get("title") or "Série",
                    "year": item.get("year"),
                    "kinds": set(),
                    "seasons": {},
                    "episode_count": 0,
                    "file_count": 0,
                }
            entry = series_map[key]
            entry["kinds"].add(media)
            entry["file_count"] += 1
            cand = item.get("title") or ""
            if len(cand) > len(entry.get("title") or ""):
                entry["title"] = cand
            if entry.get("year") is None and item.get("year") is not None:
                entry["year"] = item.get("year")
            season_n = item.get("season")
            try:
                season_n = int(season_n) if season_n is not None else 0
            except (TypeError, ValueError):
                season_n = 0
            seasons = entry["seasons"]
            if season_n not in seasons:
                seasons[season_n] = {"season": season_n, "episodes": []}
            seasons[season_n]["episodes"].append(item)
            if item.get("episode") is not None:
                entry["episode_count"] += 1
        elif media == "movie":
            movies.append(item)
        elif media == "archive":
            archives.append(item)
        else:
            others.append(item)

    series_map = _merge_similar_series(series_map)

    series_list: list[dict[str, Any]] = []
    for entry in series_map.values():
        seasons_sorted = []
        for season_n in sorted(entry["seasons"].keys()):
            block = entry["seasons"][season_n]
            eps = sorted(
                block["episodes"],
                key=lambda x: (
                    x.get("episode") is None,
                    int(x["episode"]) if x.get("episode") is not None else 0,
                    x.get("filename") or "",
                ),
            )
            seasons_sorted.append(
                {
                    "season": season_n,
                    "label": f"Saison {season_n:02d}" if season_n else "Sans saison",
                    "count": len(eps),
                    "episodes": eps,
                }
            )
        kinds = sorted(entry["kinds"])
        year = entry.get("year")
        title = entry["title"]
        if year is not None:
            try:
                title = f"{title} ({int(year)})"
            except (TypeError, ValueError):
                pass
        series_list.append(
            {
                "key": entry["key"],
                "title": title,
                "year": year,
                "kind": "anime" if kinds == ["anime"] else ("tv" if "tv" in kinds else kinds[0]),
                "episode_count": entry["episode_count"],
                "file_count": entry["file_count"],
                "season_count": len(seasons_sorted),
                "seasons": seasons_sorted,
            }
        )

    series_list.sort(key=lambda s: (s["title"] or "").lower())
    movies.sort(
        key=lambda m: (
            (m.get("title") or "").lower(),
            m.get("year") is None,
            m.get("year") or 0,
        )
    )
    archives.sort(key=lambda a: ((a.get("title") or "").lower(), a.get("season") or 0))
    others.sort(key=lambda o: (o.get("filename") or "").lower())

    return {
        "series": series_list,
        "movies": movies,
        "archives": archives,
        "other": others,
        "series_count": len(series_list),
        "movie_count": len(movies),
        "archive_count": len(archives),
        "other_count": len(others),
    }


def _format_size(n: int) -> str:
    try:
        size = float(n)
    except (TypeError, ValueError):
        return "—"
    if size < 1024:
        return f"{int(size)} o"
    for unit in ("Ko", "Mo", "Go", "To"):
        size /= 1024.0
        if size < 1024:
            return f"{size:.1f} {unit}"
    return f"{size:.1f} Po"


def _is_ambiguous(item: dict[str, Any]) -> bool:
    """Heuristique : parsing peu fiable → à vérifier manuellement."""
    media = item.get("type") or "other"
    identity = str(item.get("identity") or "")
    if media == "other" or "|other|" in identity:
        return True
    if media in ("tv", "anime") and (
        item.get("season") is None or item.get("episode") is None
    ):
        return True
    if media == "movie" and not (item.get("title") or "").strip():
        return True
    return False


def find_duplicates(items: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Phase 3 — groupes de fichiers partageant la même identité (≥ 2).
    """
    buckets: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        key = str(item.get("identity") or "").strip()
        if not key:
            continue
        buckets.setdefault(key, []).append(item)

    groups: list[dict[str, Any]] = []
    for identity, files in buckets.items():
        if len(files) < 2:
            continue
        # Dédupliquer chemins exacts (même fichier listé 2×)
        seen_paths: set[str] = set()
        unique_files: list[dict[str, Any]] = []
        for f in files:
            path = str(f.get("path") or "")
            if path and path in seen_paths:
                continue
            if path:
                seen_paths.add(path)
            unique_files.append(f)
        if len(unique_files) < 2:
            continue

        unique_files.sort(key=lambda f: (f.get("size") or 0, f.get("filename") or ""))
        title = next((f.get("title") for f in unique_files if f.get("title")), "") or identity
        media = unique_files[0].get("type") or "other"
        ambiguous = any(_is_ambiguous(f) for f in unique_files)
        enriched = []
        for f in unique_files:
            enriched.append(
                {
                    **f,
                    "size_label": _format_size(int(f.get("size") or 0)),
                    "ambiguous": _is_ambiguous(f),
                }
            )
        groups.append(
            {
                "identity": identity,
                "title": title,
                "type": media,
                "count": len(enriched),
                "ambiguous": ambiguous,
                "files": enriched,
            }
        )

    groups.sort(key=lambda g: (-g["count"], (g.get("title") or "").lower()))
    return {
        "group_count": len(groups),
        "file_count": sum(g["count"] for g in groups),
        "groups": groups,
    }


def _identity_map(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Une entrée représentative par identité (préfère vidéo aux archives)."""
    rank = {"tv": 0, "anime": 0, "movie": 1, "archive": 3, "other": 2}
    out: dict[str, dict[str, Any]] = {}
    for item in items:
        key = str(item.get("identity") or "").strip()
        if not key:
            continue
        prev = out.get(key)
        if prev is None:
            out[key] = item
            continue
        r_new = rank.get(item.get("type") or "other", 9)
        r_old = rank.get(prev.get("type") or "other", 9)
        if r_new < r_old:
            out[key] = item
        elif r_new == r_old and (item.get("size") or 0) > (prev.get("size") or 0):
            out[key] = item
    return out


def _diff_entry(item: dict[str, Any], *, side: str) -> dict[str, Any]:
    return {
        "identity": item.get("identity") or "",
        "title": item.get("title") or "",
        "type": item.get("type") or "other",
        "season": item.get("season"),
        "episode": item.get("episode"),
        "year": item.get("year"),
        "filename": item.get("filename") or "",
        "path": item.get("path") or "",
        "size": item.get("size") or 0,
        "size_label": _format_size(int(item.get("size") or 0)),
        "side": side,
        "season_pack": bool(item.get("season_pack")),
        "archive_format": item.get("archive_format") or "",
    }


def _normalize_folder_list(
    folders: list[str] | str | None = None,
    *legacy: str,
) -> list[str]:
    """Accepte une liste, une chaîne multi-lignes, ou d’anciens args uniques."""
    candidates: list[str] = []
    if isinstance(folders, list):
        candidates.extend(str(x) for x in folders)
    elif isinstance(folders, str) and folders.strip():
        for part in folders.replace(";", "\n").splitlines():
            if part.strip():
                candidates.append(part.strip())
    for extra in legacy:
        if extra and str(extra).strip():
            candidates.append(str(extra).strip())
    out: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        value = item.strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
        if len(out) >= 12:
            break
    return out


def scan_many(
    folders: list[str],
    *,
    recursive: bool = True,
    template_id: str = "simple",
    on_progress=None,
    side_label: str = "",
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Scanne plusieurs dossiers et fusionne les items."""
    items: list[dict[str, Any]] = []
    ok_folders: list[str] = []
    errors: list[str] = []
    total = max(1, len(folders))
    for idx, folder in enumerate(folders):
        if on_progress:
            on_progress(
                {
                    "phase": "scan",
                    "side": side_label,
                    "index": idx + 1,
                    "total": total,
                    "folder": folder,
                    "message": f"Scan {side_label} {idx + 1}/{total} : {folder}",
                }
            )
        try:
            result = scan_library(
                folder, recursive=recursive, template_id=template_id
            )
            items.extend(result["items"])
            ok_folders.append(result["folder"])
        except FileNotFoundError as exc:
            errors.append(str(exc))
        except Exception as exc:
            errors.append(f"{folder} → {exc}")
    return items, ok_folders, errors


def diff_libraries(
    folder_a: str | list[str] | None = None,
    folder_b: str | list[str] | None = None,
    *,
    folders_a: list[str] | None = None,
    folders_b: list[str] | None = None,
    recursive: bool = True,
    template_id: str = "simple",
    label_a: str = "PC",
    label_b: str = "NAS",
    on_progress=None,
) -> dict[str, Any]:
    """
    Compare une ou plusieurs racines PC vs NAS par identité média.
    missing_on_b = présent sur A (PC), absent sur B (NAS)
    missing_on_a = présent sur B (NAS), absent sur A (PC)
    """
    list_a = _normalize_folder_list(folders_a if folders_a is not None else folder_a)
    list_b = _normalize_folder_list(folders_b if folders_b is not None else folder_b)
    if not list_a:
        raise FileNotFoundError("Aucun dossier PC indiqué.")
    if not list_b:
        raise FileNotFoundError("Aucun dossier NAS indiqué.")

    if on_progress:
        on_progress(
            {
                "phase": "prepare",
                "percent": 2,
                "message": f"Préparation : {len(list_a)} dossier(s) PC, {len(list_b)} NAS…",
            }
        )

    try:
        import network_shares
        import settings as app_settings

        network_shares.ensure_paths_access(
            list_a + list_b, app_settings.get_network_shares()
        )
    except ImportError:
        pass

    def progress_a(info: dict[str, Any]) -> None:
        if not on_progress:
            return
        # PC = 5% → 45%
        frac = info["index"] / max(1, info["total"])
        on_progress(
            {
                **info,
                "percent": 5 + int(40 * frac),
            }
        )

    def progress_b(info: dict[str, Any]) -> None:
        if not on_progress:
            return
        # NAS = 45% → 85%
        frac = info["index"] / max(1, info["total"])
        on_progress(
            {
                **info,
                "percent": 45 + int(40 * frac),
            }
        )

    items_a, ok_a, err_a = scan_many(
        list_a,
        recursive=recursive,
        template_id=template_id,
        on_progress=progress_a,
        side_label=label_a,
    )
    items_b, ok_b, err_b = scan_many(
        list_b,
        recursive=recursive,
        template_id=template_id,
        on_progress=progress_b,
        side_label=label_b,
    )

    if not items_a and err_a and not ok_a:
        raise FileNotFoundError("Aucun dossier PC accessible : " + " | ".join(err_a))
    if not items_b and err_b and not ok_b:
        raise FileNotFoundError("Aucun dossier NAS accessible : " + " | ".join(err_b))

    if on_progress:
        on_progress(
            {
                "phase": "compare",
                "percent": 90,
                "message": "Comparaison des identités…",
            }
        )

    map_a = _identity_map(items_a)
    map_b = _identity_map(items_b)
    keys_a = set(map_a)
    keys_b = set(map_b)

    missing_on_b = [
        _diff_entry(map_a[k], side="a")
        for k in sorted(keys_a - keys_b, key=lambda x: (map_a[x].get("title") or "").lower())
    ]
    missing_on_a = [
        _diff_entry(map_b[k], side="b")
        for k in sorted(keys_b - keys_a, key=lambda x: (map_b[x].get("title") or "").lower())
    ]
    common = []
    for k in sorted(keys_a & keys_b, key=lambda x: (map_a[x].get("title") or "").lower()):
        common.append(
            {
                "identity": k,
                "title": map_a[k].get("title") or map_b[k].get("title") or "",
                "type": map_a[k].get("type") or map_b[k].get("type") or "other",
                "a": _diff_entry(map_a[k], side="a"),
                "b": _diff_entry(map_b[k], side="b"),
            }
        )

    return {
        "label_a": label_a,
        "label_b": label_b,
        "folders_a": ok_a,
        "folders_b": ok_b,
        "folder_a": ok_a[0] if ok_a else "",
        "folder_b": ok_b[0] if ok_b else "",
        "errors_a": err_a,
        "errors_b": err_b,
        "count_a": len(items_a),
        "count_b": len(items_b),
        "identities_a": len(map_a),
        "identities_b": len(map_b),
        "missing_on_b": missing_on_b,
        "missing_on_a": missing_on_a,
        "common": common,
        "missing_on_b_count": len(missing_on_b),
        "missing_on_a_count": len(missing_on_a),
        "common_count": len(common),
    }
