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
) -> dict[str, Any]:
    """
    Scanne un dossier et retourne un inventaire plat (pas de modification disque).
    Inclut les vidéos/audios et les archives (.zip / .rar / .7z).
    """
    root = Path(folder).expanduser()
    if not root.is_dir():
        raise FileNotFoundError(f"Dossier introuvable : {folder}")

    allowed = smart_naming.VIDEO_EXTS | smart_naming.AUDIO_EXTS | ARCHIVE_EXTS
    paths = root.rglob("*") if recursive else root.iterdir()
    items: list[dict[str, Any]] = []

    for path in sorted(paths):
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

    return {
        "folder": str(root.resolve()),
        "recursive": recursive,
        "count": len(items),
        "unique_identities": len(identities),
        "archive_count": archive_count,
        "season_pack_count": season_pack_count,
        "by_type": by_type,
        "items": items,
    }
