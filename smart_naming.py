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
# Variante fréquente : S03.E01 / S03_E01 / S03 E01
TV_DOT_RE = re.compile(
    r"(?<![0-9])[Ss](\d{1,2})[\s._-]+[Ee](\d{1,3})(?:[\s._-]*[Ee](\d{1,3}))?",
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
# Épisode numéroté type « 01 - Titre » / « 01.Titre » / « 12 - Collection »
NUMBERED_EP_RE = re.compile(
    r"^(?P<ep>\d{1,2})\s*[-–.]\s+(?P<title>.+)$",
    re.IGNORECASE,
)
# Saison dans un nom de dossier
SEASON_FOLDER_RE = re.compile(
    r"(?:^|[\s._-])(?:saison|season|s)[\s._-]*(\d{1,2})$",
    re.IGNORECASE,
)
FOLDER_YEAR_RE = re.compile(r"(?<![0-9])(19\d{2}|20\d{2})(?![0-9])")


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


TEMPLATES = {
    "plex": {
        "tv": "{title} - S{season:02d}E{episode:02d}{ext}",
        "movie": "{title} ({year}){ext}",
        "anime": "{title} - S{season:02d}E{episode:03d}{ext}",
        "other": "{title}{ext}",
    },
    "jellyfin": {
        "tv": "{title} S{season:02d}E{episode:02d}{ext}",
        "movie": "{title} ({year}){ext}",
        "anime": "{title} S{season:02d}E{episode:03d}{ext}",
        "other": "{title}{ext}",
    },
    "simple": {
        "tv": "{title} S{season:02d}E{episode:02d}{ext}",
        "movie": "{title} ({year}){ext}",
        "anime": "{title} S{season:02d}E{episode:03d}{ext}",
        "other": "{title}{ext}",
    },
    "dotted": {
        "tv": "{title}.S{season:02d}E{episode:02d}{ext}",
        "movie": "{title}.{year}{ext}",
        "anime": "{title}.S{season:02d}E{episode:03d}{ext}",
        "other": "{title}{ext}",
    },
}


def _format_template(template: str, **kwargs: Any) -> str:
    class _Fmt(dict):
        def __missing__(self, key: str) -> str:
            return ""

    # Support {season:02d} style via manual replace for common keys
    out = template
    season = kwargs.get("season")
    episode = kwargs.get("episode")
    year = kwargs.get("year")
    title = kwargs.get("title") or ""
    ext = kwargs.get("ext") or ""

    replacements = {
        "{title}": title,
        "{ext}": ext,
        "{year}": "" if year is None else str(year),
        "{season}": "" if season is None else str(season),
        "{episode}": "" if episode is None else str(episode),
        "{season:02d}": "" if season is None else f"{int(season):02d}",
        "{episode:02d}": "" if episode is None else f"{int(episode):02d}",
        "{episode:03d}": "" if episode is None else f"{int(episode):03d}",
    }
    for k, v in replacements.items():
        out = out.replace(k, v)
    return re.sub(r"\s+", " ", out).strip(" ._-")


def apply_template(info: dict[str, Any], template_id: str = "simple") -> str:
    """Applique un template de nommage sur un résultat suggest_name."""
    presets = TEMPLATES.get(template_id) or TEMPLATES["simple"]
    media = info.get("type") or "other"
    if media == "tv":
        key = "tv"
    elif media == "movie":
        key = "movie"
    elif media == "anime":
        key = "anime"
    else:
        key = "other"
    tmpl = presets.get(key) or presets["other"]
    original = info.get("original") or info.get("suggested") or ""
    path = Path(original)
    ext = path.suffix if path.suffix else ""
    # Si suggested a déjà une ext
    if not ext and info.get("suggested"):
        ext = Path(info["suggested"]).suffix

    season = info.get("season")
    episode = info.get("episode")
    # Anime default season 1
    if media == "anime" and season is None:
        season = 1

    name = _format_template(
        tmpl,
        title=info.get("title") or "Sans titre",
        season=season,
        episode=episode,
        year=info.get("year"),
        ext=ext,
    )
    if not name.lower().endswith(ext.lower()) and ext:
        name = name + ext
    return _safe_filename(name)



def _strip_leading_episode_num(title: str, episode: int | None) -> str:
    """Enlève un préfixe '12 ' / '12 -' du titre s'il reprend le n° d'épisode."""
    text = (title or "").strip()
    if not text or episode is None:
        return text
    m = re.match(r"^(\d{1,3})\s*[-–.]?\s+(.*)$", text)
    if m and int(m.group(1)) == int(episode):
        rest = m.group(2).strip(" -._")
        return rest or text
    return text


def _finalize_tv(
    result: dict[str, Any],
    *,
    title: str,
    season: int,
    episode: int,
    template_id: str,
    year: int | None = None,
    ep2: int | None = None,
) -> dict[str, Any]:
    clean = _strip_leading_episode_num(_clean_title(title) or "Serie", episode)
    result.update(
        {
            "type": "tv",
            "title": clean,
            "season": season,
            "episode": episode,
            "year": year,
        }
    )
    base = apply_template(result, template_id)
    if ep2:
        p = Path(base)
        result["suggested"] = _safe_filename(f"{p.stem}E{int(ep2):02d}{p.suffix}")
    else:
        result["suggested"] = base
    return result


def path_context(file_path: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    """
    Indices issus des dossiers parents : titre de série, saison, année.
    Ex. .../Les 4400 (2021)/Saison 01/ep.mkv
    """
    path = Path(file_path)
    root_path = Path(root).resolve() if root else None
    series_hint = ""
    season_hint: int | None = None
    year_hint: int | None = None

    parents = list(path.parents)
    for folder in parents:
        if root_path is not None:
            try:
                folder.relative_to(root_path)
            except ValueError:
                break
            if folder == root_path:
                # Le dossier racine du scan peut aussi porter le titre
                name = folder.name
                ym = FOLDER_YEAR_RE.search(name)
                if ym and year_hint is None:
                    year_hint = int(ym.group(1))
                cleaned = FOLDER_YEAR_RE.sub(" ", name)
                cleaned = SEASON_FOLDER_RE.sub("", cleaned)
                cleaned = _clean_title(cleaned)
                if cleaned and len(cleaned) > 2 and not series_hint:
                    series_hint = cleaned
                break

        name = folder.name
        sm = SEASON_FOLDER_RE.search(name.strip())
        if sm and season_hint is None:
            try:
                season_hint = int(sm.group(1))
            except ValueError:
                pass
            continue
        ym = FOLDER_YEAR_RE.search(name)
        if ym and year_hint is None:
            year_hint = int(ym.group(1))
        # Dossier « série » : ignorer disques / volumes génériques
        low = name.lower()
        if low in {"series", "séries", "films", "movies", "tv", "video", "videos", "media"}:
            continue
        cleaned = FOLDER_YEAR_RE.sub(" ", name)
        cleaned = SEASON_FOLDER_RE.sub("", cleaned)
        cleaned = _clean_title(cleaned)
        if cleaned and len(cleaned) > 2 and not series_hint:
            series_hint = cleaned

    return {
        "series_title": series_hint,
        "season": season_hint,
        "year": year_hint,
    }


def _looks_like_numbered_episode(stem: str) -> re.Match[str] | None:
    return NUMBERED_EP_RE.match(stem.strip())


def suggest_name(
    filename: str,
    template_id: str = "simple",
    *,
    path_hint: str | Path | None = None,
    root_hint: str | Path | None = None,
) -> dict[str, Any]:
    """Produit un nom Plex/Kodi/Jellyfin à partir d'un nom de fichier."""
    original = (filename or "").strip()
    path = Path(original)
    ext = path.suffix.lower() if path.suffix else ""
    stem = path.stem if path.suffix else original
    ctx = path_context(path_hint or original, root_hint) if (path_hint or root_hint) else {
        "series_title": "",
        "season": None,
        "year": None,
    }
    # Si on n'a passé que le nom, tenter le chemin complet via path_hint
    if path_hint and not ctx.get("series_title"):
        ctx = path_context(path_hint, root_hint)

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

    def _title_from(raw: str, episode: int | None = None) -> str:
        base = ctx.get("series_title") or _clean_title(raw) or "Serie"
        if ctx.get("series_title"):
            return str(ctx["series_title"])
        return _strip_leading_episode_num(base, episode)

    # ── Série TV : SxxExx ──
    m = TV_RE.search(stem)
    if m:
        season, ep1, ep2 = int(m.group(1)), int(m.group(2)), m.group(3)
        raw_title = stem[: m.start()].rstrip("._- ")
        trail = re.search(r"[Ss](\d{1,2})\s*$", raw_title)
        if trail and season == 1:
            season = int(trail.group(1))
            raw_title = raw_title[: trail.start()].rstrip("._- ")
        if ctx.get("season") and season == 1 and not trail:
            # Rare : S01Exx dans un dossier Saison 03 → garder S01 du fichier
            pass
        year = ctx.get("year")
        return _finalize_tv(
            result,
            title=_title_from(raw_title, ep1),
            season=season,
            episode=ep1,
            template_id=template_id,
            year=year,
            ep2=int(ep2) if ep2 else None,
        )

    # ── Série TV : Sxx.Exx / Sxx_Exx / Sxx E01 ──
    m = TV_DOT_RE.search(stem)
    if m:
        season, ep1, ep2 = int(m.group(1)), int(m.group(2)), m.group(3)
        raw_title = stem[: m.start()].rstrip("._- ")
        return _finalize_tv(
            result,
            title=_title_from(raw_title, ep1),
            season=season,
            episode=ep1,
            template_id=template_id,
            year=ctx.get("year"),
            ep2=int(ep2) if ep2 else None,
        )

    # ── Série : 3x01 (éventuellement collé au titre : Risquess3x13) ──
    m = TV_X_RE.search(stem)
    if m:
        season, ep1, ep2 = int(m.group(1)), int(m.group(2)), m.group(3)
        raw_title = stem[: m.start()].rstrip("._- ")
        # Enlever une lettre orpheline collée (…Risquess → …Risques si double s)
        raw_title = re.sub(r"([a-zàâäéèêëïîôùûüç])\1+$", r"\1", raw_title, flags=re.I)
        return _finalize_tv(
            result,
            title=_title_from(raw_title, ep1),
            season=season,
            episode=ep1,
            template_id=template_id,
            year=ctx.get("year"),
            ep2=int(ep2) if ep2 else None,
        )

    # ── Saison X Episode Y (FR) ──
    m = TV_FR_RE.search(stem)
    if m:
        season, ep1 = int(m.group(1)), int(m.group(2))
        raw_title = stem[: m.start()].rstrip("._- ")
        return _finalize_tv(
            result,
            title=_title_from(raw_title, ep1),
            season=season,
            episode=ep1,
            template_id=template_id,
            year=ctx.get("year"),
        )

    # ── Épisode numéroté « 01 - Titre » (souvent séries anciennes / FR) ──
    numbered = _looks_like_numbered_episode(stem)
    if numbered:
        ep = int(numbered.group("ep"))
        rest = numbered.group("title").strip()
        # Une année dans le titre d'épisode (ex. Collection 1909) n'en fait PAS un film
        rest_no_year = YEAR_RE.sub(" ", rest).strip(" ._()-")
        season = int(ctx["season"]) if ctx.get("season") is not None else 1
        title = ctx.get("series_title") or _clean_title(rest_no_year) or _clean_title(rest) or "Serie"
        return _finalize_tv(
            result,
            title=title,
            season=season,
            episode=ep,
            template_id=template_id,
            year=ctx.get("year"),
        )

    # ── Film : Titre (Année) — uniquement si ce n'est pas un faux positif ──
    year_m = YEAR_RE.search(stem)
    if year_m:
        year = int(year_m.group(1))
        raw_title = stem[: year_m.start()].rstrip("._- ()[]")
        title = _clean_title(raw_title) or "Film"
        # Année très ancienne + titre court / numéroté → plutôt série / autre
        if year < 1930 and re.match(r"^\d{1,2}\b", title):
            pass  # ne pas classer film — tombe plus bas
        else:
            # Prefer folder series context: fichier dans une série → TV, année = année de série
            if ctx.get("series_title"):
                return _finalize_tv(
                    result,
                    title=str(ctx["series_title"]),
                    season=int(ctx["season"] or 1),
                    episode=1,
                    template_id=template_id,
                    year=ctx.get("year") or year,
                )
            result.update(
                {
                    "type": "movie",
                    "title": title,
                    "year": year,
                }
            )
            result["suggested"] = apply_template(result, template_id)
            return result

    # ── Anime / numérotation simple ──
    anime_m = ANIME_EP_RE.search(stem)
    if anime_m:
        ep = int(anime_m.group(1))
        raw_title = stem[: anime_m.start()].rstrip("._- ")
        title = ctx.get("series_title") or _clean_title(raw_title) or "Anime"
        result.update(
            {
                "type": "anime",
                "title": title,
                "season": int(ctx["season"] or 1),
                "episode": ep,
                "year": ctx.get("year"),
            }
        )
        result["suggested"] = apply_template(result, template_id)
        return result

    # ── Fallback ──
    title = ctx.get("series_title") or _clean_title(stem)
    result.update(
        {
            "title": title,
            "type": "tv" if ctx.get("series_title") else "other",
            "season": ctx.get("season"),
            "year": ctx.get("year"),
        }
    )
    result["suggested"] = apply_template(
        {**result, "suggested": f"{title}{ext}"}, template_id
    )
    return result


def enrich_link(link: dict, template_id: str | None = None) -> dict:
    """Ajoute clean_name / media_type à un lien résolu ou source."""
    if template_id is None:
        try:
            import settings as app_settings

            template_id = app_settings.get_rename_template()
        except Exception:
            template_id = "simple"
    raw = (
        link.get("resolve_filename")
        or link.get("label")
        or link.get("url", "").split("/")[-1]
        or ""
    )
    info = suggest_name(raw, template_id=template_id or "simple")
    return {
        **link,
        "clean_name": info["suggested"],
        "media_type": info["type"],
        "media_title": info.get("title") or "",
        "media_season": info.get("season"),
        "media_episode": info.get("episode"),
        "media_year": info.get("year"),
    }


def list_templates() -> list[dict[str, str]]:
    return [
        {"id": "simple", "label": "Simple — Titre S03E01"},
        {"id": "plex", "label": "Plex — Titre - S03E01"},
        {"id": "jellyfin", "label": "Jellyfin — Titre S03E01"},
        {"id": "dotted", "label": "Points — Titre.S03E01"},
    ]


def scan_folder(
    folder: str, *, recursive: bool = False, template_id: str = "simple"
) -> list[dict[str, Any]]:
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
        info = suggest_name(p.name, template_id=template_id)
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
