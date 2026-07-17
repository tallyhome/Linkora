"""Nommage intelligent pour Plex, Kodi, Jellyfin."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

VIDEO_EXTS = {
    ".mkv",
    ".mp4",
    ".avi",
    ".m4v",
    ".wmv",
    ".mov",
    ".flv",
    ".webm",
    ".ts",
    ".m2ts",
    ".mpg",
    ".mpeg",
}
AUDIO_EXTS = {".mp3", ".flac", ".aac", ".ogg", ".wav", ".m4a"}

NOISE = {
    "truefrench",
    "vf",
    "vff",
    "vfi",
    "vfq",
    "vostfr",
    "vost",
    "multi",
    "french",
    "fr",
    "english",
    "eng",
    "subfrench",
    "sub",
    "dvrip",
    "dvdrip",
    "hdrip",
    "webrip",
    "webdl",
    "web-dl",
    "web",
    "bluray",
    "blu-ray",
    "bdrip",
    "brrip",
    "hdtv",
    "h264",
    "h265",
    "x264",
    "x265",
    "hevc",
    "avc",
    "10bit",
    "8bit",
    "aac",
    "ac3",
    "dts",
    "1080p",
    "720p",
    "480p",
    "576p",
    "2160p",
    "4k",
    "uhd",
    "hdr",
    "hdr10",
    "dolby",
    "atmos",
    "proper",
    "repack",
    "extended",
    "uncut",
    "complete",
    "integrated",
    "wawacity",
    "vip",
    "zone",
    "telechargement",
    "poker",
    "notag",
    "rarbg",
    "yify",
    "sparks",
    "ettv",
    "eztv",
    "lol",
    "dimension",
    "amzn",
    "nf",
    "dsnp",
    "hmax",
    "webrip",
    "internal",
    "limited",
    "readnfo",
    "nfo",
    "sample",
    "trailer",
}

TV_RE = re.compile(
    r"(?<![0-9])[Ss](\d{1,2})[Ee](\d{1,3})(?:[Ee](\d{1,3}))?",
    re.IGNORECASE,
)
TV_X_RE = re.compile(r"(?<![0-9])(\d{1,2})[xX](\d{1,3})(?:[xX](\d{1,3}))?", re.IGNORECASE)
TV_FR_RE = re.compile(
    r"Saison[\s._-]*(\d{1,2})[\s._-]*Episode[\s._-]*(\d{1,3})",
    re.IGNORECASE,
)
ANIME_EP_RE = re.compile(
    r"[\s._-]+(?:E(?:P)?[\s._-]*)?(\d{2,4})(?:[\s._-]|$)",
    re.IGNORECASE,
)
YEAR_RE = re.compile(r"(?<![0-9])(19\d{2}|20\d{2})(?![0-9])")


def _split_tokens(stem: str) -> list[str]:
    parts = re.split(r"[._\s]+", stem)
    return [p for p in parts if p]


def _is_noise(token: str) -> bool:
    low = token.lower().strip("_")
    if not low:
        return True
    if low in NOISE:
        return True
    if re.fullmatch(r"\d+p", low):
        return True
    if re.fullmatch(r"h\d{3,4}", low):
        return True
    return False


def _title_case_fr(text: str) -> str:
    words = text.split()
    out: list[str] = []
    for w in words:
        if not w:
            continue
        if w.isupper() and len(w) <= 4:
            out.append(w)
        elif "-" in w:
            out.append("-".join(p[:1].upper() + p[1:] if p else "" for p in w.split("-")))
        else:
            out.append(w[:1].upper() + w[1:])
    return " ".join(out)


def _clean_title(raw: str) -> str:
    text = raw.replace("_", " ").replace(".", " ")
    text = re.sub(r"\s+", " ", text).strip(" -_")
    tokens = _split_tokens(text)
    kept = [t for t in tokens if not _is_noise(t)]
    if not kept:
        kept = tokens[:8] or [text]
    title = " ".join(kept)
    return _title_case_fr(title)


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned or "Sans titre"


def suggest_name(filename: str) -> dict[str, Any]:
    """Produit un nom Plex/Kodi/Jellyfin à partir d'un nom de fichier."""
    original = (filename or "").strip()
    path = Path(original)
    ext = path.suffix.lower() if path.suffix else ""
    stem = path.stem if path.suffix else original

    result: dict[str, Any] = {
        "original": original,
        "suggested": original,
        "type": "other",
        "title": "",
        "season": None,
        "episode": None,
        "year": None,
    }

    if not stem:
        return result

    # ── Série TV : SxxExx ──
    m = TV_RE.search(stem)
    if m:
        season, ep1, ep2 = int(m.group(1)), int(m.group(2)), m.group(3)
        raw_title = stem[: m.start()].rstrip("._- ")
        title = _clean_title(raw_title) or "Serie"
        ep_part = f"S{season:02d}E{ep1:02d}"
        if ep2:
            ep_part += f"E{int(ep2):02d}"
        suggested = _safe_filename(f"{title} {ep_part}{ext}")
        result.update(
            {
                "suggested": suggested,
                "type": "tv",
                "title": title,
                "season": season,
                "episode": ep1,
            }
        )
        return result

    # ── Série : 3x01 ──
    m = TV_X_RE.search(stem)
    if m:
        season, ep1, ep2 = int(m.group(1)), int(m.group(2)), m.group(3)
        raw_title = stem[: m.start()].rstrip("._- ")
        title = _clean_title(raw_title) or "Serie"
        ep_part = f"S{season:02d}E{ep1:02d}"
        if ep2:
            ep_part += f"E{int(ep2):02d}"
        suggested = _safe_filename(f"{title} {ep_part}{ext}")
        result.update(
            {
                "suggested": suggested,
                "type": "tv",
                "title": title,
                "season": season,
                "episode": ep1,
            }
        )
        return result

    # ── Saison X Episode Y (FR) ──
    m = TV_FR_RE.search(stem)
    if m:
        season, ep1 = int(m.group(1)), int(m.group(2))
        raw_title = stem[: m.start()].rstrip("._- ")
        title = _clean_title(raw_title) or "Serie"
        suggested = _safe_filename(f"{title} S{season:02d}E{ep1:02d}{ext}")
        result.update(
            {
                "suggested": suggested,
                "type": "tv",
                "title": title,
                "season": season,
                "episode": ep1,
            }
        )
        return result

    # ── Film : Titre (Année) ──
    year_m = YEAR_RE.search(stem)
    if year_m:
        year = int(year_m.group(1))
        raw_title = stem[: year_m.start()].rstrip("._- ")
        title = _clean_title(raw_title) or "Film"
        suggested = _safe_filename(f"{title} ({year}){ext}")
        result.update(
            {
                "suggested": suggested,
                "type": "movie",
                "title": title,
                "year": year,
            }
        )
        return result

    # ── Anime / numérotation simple ──
    anime_m = ANIME_EP_RE.search(stem)
    if anime_m:
        ep = int(anime_m.group(1))
        raw_title = stem[: anime_m.start()].rstrip("._- ")
        title = _clean_title(raw_title) or "Anime"
        # Beaucoup d'animes : numéro d'épisode global → S01Exxx
        suggested = _safe_filename(f"{title} S01E{ep:03d}{ext}")
        result.update(
            {
                "suggested": suggested,
                "type": "anime",
                "title": title,
                "season": 1,
                "episode": ep,
            }
        )
        return result

    # ── Fallback : nettoyage léger ──
    title = _clean_title(stem)
    suggested = _safe_filename(f"{title}{ext}")
    result.update({"suggested": suggested, "title": title, "type": "other"})
    return result


def enrich_link(link: dict) -> dict:
    """Ajoute clean_name / media_type à un lien résolu ou source."""
    raw = (
        link.get("resolve_filename")
        or link.get("label")
        or link.get("url", "").split("/")[-1]
        or ""
    )
    info = suggest_name(raw)
    return {
        **link,
        "clean_name": info["suggested"],
        "media_type": info["type"],
        "media_title": info.get("title") or "",
        "media_season": info.get("season"),
        "media_episode": info.get("episode"),
        "media_year": info.get("year"),
    }


def scan_folder(folder: str, *, recursive: bool = False) -> list[dict[str, Any]]:
    """Scanne un dossier local et propose des renommages."""
    root = Path(folder).expanduser()
    if not root.is_dir():
        raise FileNotFoundError(f"Dossier introuvable : {folder}")

    allowed = VIDEO_EXTS | AUDIO_EXTS
    paths = root.rglob("*") if recursive else root.iterdir()
    items: list[dict[str, Any]] = []

    for p in sorted(paths):
        if not p.is_file():
            continue
        if p.suffix.lower() not in allowed:
            continue
        info = suggest_name(p.name)
        target = p.with_name(info["suggested"])
        items.append(
            {
                "original": p.name,
                "suggested": info["suggested"],
                "path": str(p),
                "target_path": str(target),
                "type": info["type"],
                "title": info.get("title") or "",
                "season": info.get("season"),
                "episode": info.get("episode"),
                "year": info.get("year"),
                "unchanged": p.name == info["suggested"],
                "conflict": target.exists() and target.resolve() != p.resolve(),
            }
        )
    return items


def apply_renames(items: list[dict[str, Any]], *, dry_run: bool = False) -> dict[str, Any]:
    """Applique les renommages (liste de {path, suggested} ou {path, target_path})."""
    renamed: list[dict] = []
    skipped: list[dict] = []
    errors: list[dict] = []

    for item in items:
        src = Path(item.get("path") or "")
        name = item.get("suggested") or item.get("target_name") or ""
        if not src.is_file():
            errors.append({"path": str(src), "error": "Fichier introuvable"})
            continue
        if not name:
            skipped.append({"path": str(src), "reason": "Nom vide"})
            continue

        dst = src.with_name(_safe_filename(name))
        if src.name == dst.name:
            skipped.append({"path": str(src), "reason": "Déjà propre"})
            continue
        if dst.exists():
            errors.append({"path": str(src), "error": f"Existe déjà : {dst.name}"})
            continue

        if dry_run:
            renamed.append({"from": src.name, "to": dst.name, "path": str(src)})
            continue

        try:
            src.rename(dst)
            renamed.append({"from": src.name, "to": dst.name, "path": str(dst)})
        except OSError as exc:
            errors.append({"path": str(src), "error": str(exc)})

    return {
        "dry_run": dry_run,
        "renamed": renamed,
        "skipped": skipped,
        "errors": errors,
        "count": len(renamed),
    }
