"""Persistance SQLite des extractions sauvegardées."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pathlib import Path

from paths import DATA_DIR

DB_PATH = DATA_DIR / "history.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS extractions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_url TEXT NOT NULL,
                host TEXT NOT NULL,
                title TEXT,
                links_json TEXT NOT NULL,
                link_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_extraction(
    source_url: str,
    host: str,
    links: list[dict],
    title: str | None = None,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO extractions
                (source_url, host, title, links_json, link_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                source_url,
                host,
                title or "",
                json.dumps(links, ensure_ascii=False),
                len(links),
                now,
            ),
        )
        conn.commit()
        row_id = cur.lastrowid
    return get_extraction(row_id)


def update_extraction(extraction_id: int, links: list[dict], title: str | None = None) -> dict | None:
    existing = get_extraction(extraction_id)
    if not existing:
        return None
    with _connect() as conn:
        if title is not None:
            conn.execute(
                """
                UPDATE extractions
                SET links_json = ?, link_count = ?, title = ?
                WHERE id = ?
                """,
                (json.dumps(links, ensure_ascii=False), len(links), title, extraction_id),
            )
        else:
            conn.execute(
                """
                UPDATE extractions
                SET links_json = ?, link_count = ?
                WHERE id = ?
                """,
                (json.dumps(links, ensure_ascii=False), len(links), extraction_id),
            )
        conn.commit()
    return get_extraction(extraction_id)


def find_by_source(source_url: str, host: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM extractions
            WHERE source_url = ? AND host = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (source_url, host),
        ).fetchone()
    if not row:
        return None
    data = dict(row)
    data["links"] = json.loads(data.pop("links_json"))
    return data


def upsert_extraction(
    source_url: str,
    host: str,
    links: list[dict],
    title: str | None = None,
) -> dict:
    """Met à jour l'entrée existante (même URL + hébergeur) ou en crée une nouvelle."""
    existing = find_by_source(source_url, host)
    if existing:
        return update_extraction(existing["id"], links, title=title or existing.get("title"))
    return save_extraction(source_url, host, links, title)


def list_extractions(limit: int = 50) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, source_url, host, title, link_count, created_at
            FROM extractions
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_extraction(extraction_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM extractions WHERE id = ?",
            (extraction_id,),
        ).fetchone()
    if not row:
        return None
    data = dict(row)
    data["links"] = json.loads(data.pop("links_json"))
    return data


def delete_extraction(extraction_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM extractions WHERE id = ?", (extraction_id,))
        conn.commit()
        return cur.rowcount > 0
