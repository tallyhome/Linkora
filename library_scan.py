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
    paths = root.rglob("*") if recursive else root.iterdir()
    items: list[dict[str, Any]] = []
    scanned = 0

    if on_progress:
        on_progress(
            {
                "phase": "scan",
                "percent": 5,
                "message": "Parcours des fichiers…",
            }
        )

    for path in sorted(paths):
        scanned += 1
        if on_progress and scanned % 40 == 0:
            # Progression soft (pas de total fiable sans double parcours NAS)
            soft = min(90, 5 + int(scanned ** 0.55))
            on_progress(
                {
                    "phase": "scan",
                    "percent": soft,
                    "message": f"Scan… {len(items)} média(s), {scanned} éléments vus",
                    "index": scanned,
                }
            )
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext not in allowed:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            size = 0

        if ext in ARCHIVE_EXTS:
            info = _parse_archive(path.name, template_id)
        else:
            info = smart_naming.suggest_name(path.name, template_id=template_id)

        identity = media_identity(info)
        items.append(
            {
                "path": str(path),
                "filename": path.name,
                "ext": ext,
                "size": size,
                "type": info.get("type") or "other",
                "title": info.get("title") or "",
                "season": info.get("season"),
                "episode": info.get("episode"),
                "year": info.get("year"),
                "suggested": info.get("suggested") or path.name,
                "identity": identity,
                "season_pack": bool(info.get("season_pack")),
                "archive_format": info.get("archive_format") or (
                    ext.lstrip(".") if ext in ARCHIVE_EXTS else ""
                ),
            }
        )

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

    folder_out = str(root)
    try:
        if not folder_out.startswith("\\\\"):
            folder_out = str(root.resolve())
    except OSError:
        pass

    return {
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
    }


def _series_key(item: dict[str, Any]) -> str:
    return normalize_title(item.get("title") or "") or "inconnu"


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
                    "kinds": set(),
                    "seasons": {},
                    "episode_count": 0,
                    "file_count": 0,
                }
            entry = series_map[key]
            entry["kinds"].add(media)
            entry["file_count"] += 1
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
        series_list.append(
            {
                "key": entry["key"],
                "title": entry["title"],
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
