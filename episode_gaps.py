"""Analyse des épisodes manquants (SxxExx)."""

from __future__ import annotations

import re
from typing import Any

TV_RE = re.compile(
    r"[Ss](\d{1,2})[Ee](\d{1,3})(?:[Ee](\d{1,3}))?",
    re.IGNORECASE,
)
TV_X_RE = re.compile(r"(?<![0-9])(\d{1,2})[xX](\d{1,3})", re.IGNORECASE)


def _episode_keys_from_text(text: str) -> list[tuple[int, int]]:
    found: list[tuple[int, int]] = []
    for m in TV_RE.finditer(text or ""):
        season, ep1 = int(m.group(1)), int(m.group(2))
        found.append((season, ep1))
        if m.group(3):
            found.append((season, int(m.group(3))))
    if not found:
        for m in TV_X_RE.finditer(text or ""):
            found.append((int(m.group(1)), int(m.group(2))))
    return found


def episodes_from_links(links: list[dict]) -> dict[int, set[int]]:
    """season -> set(episodes) trouvés dans labels / clean_name / filename."""
    by_season: dict[int, set[int]] = {}
    for link in links or []:
        blob = " ".join(
            str(link.get(k) or "")
            for k in (
                "clean_name",
                "resolve_filename",
                "label",
                "media_title",
            )
        )
        if link.get("media_season") is not None and link.get("media_episode") is not None:
            try:
                s, e = int(link["media_season"]), int(link["media_episode"])
                by_season.setdefault(s, set()).add(e)
            except (TypeError, ValueError):
                pass
        for s, e in _episode_keys_from_text(blob):
            by_season.setdefault(s, set()).add(e)
    return by_season


def find_missing(
    links: list[dict],
    *,
    season: int | None = None,
    expected_count: int | None = None,
) -> dict[str, Any]:
    """
    Déduit les trous dans la plage min..max (ou 1..expected_count).
    """
    by_season = episodes_from_links(links)
    report: list[dict[str, Any]] = []

    seasons = [season] if season is not None else sorted(by_season.keys())
    if not seasons and season is None:
        return {
            "ok": True,
            "has_tv": False,
            "seasons": [],
            "missing_labels": [],
            "summary": "Aucun épisode SxxExx détecté.",
        }

    for s in seasons:
        present = sorted(by_season.get(s, set()))
        if not present and expected_count:
            present = []
            lo, hi = 1, expected_count
        elif not present:
            continue
        else:
            lo = 1 if expected_count else min(present)
            hi = expected_count if expected_count else max(present)
        missing = [e for e in range(lo, hi + 1) if e not in set(present)]
        labels = [f"S{s:02d}E{e:02d}" for e in missing]
        report.append(
            {
                "season": s,
                "found": present,
                "found_count": len(present),
                "range": [lo, hi],
                "missing": missing,
                "missing_labels": labels,
            }
        )

    all_missing = [lab for block in report for lab in block["missing_labels"]]
    if not report:
        summary = "Aucun épisode analysable."
    elif not all_missing:
        summary = "Aucun épisode manquant dans les plages détectées."
    else:
        summary = f"{len(all_missing)} manquant(s) : " + ", ".join(all_missing[:20])
        if len(all_missing) > 20:
            summary += "…"

    return {
        "ok": True,
        "has_tv": bool(report),
        "seasons": report,
        "missing_labels": all_missing,
        "summary": summary,
    }
