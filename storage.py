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
    init_library_history()


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


def init_library_history() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS library_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                title TEXT,
                folders_json TEXT NOT NULL,
                summary TEXT,
                result_file TEXT,
                count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_library_history(
    *,
    kind: str,
    title: str,
    folders: list[str] | dict | None,
    summary: str,
    result: dict,
    count: int = 0,
) -> dict:
    """Persiste un scan / diff bibliothèque (résultat sur disque)."""
    import time
    from paths import DATA_DIR

    init_library_history()
    hist_dir = DATA_DIR / "library_history"
    hist_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO library_history
                (kind, title, folders_json, summary, result_file, count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                kind,
                title[:200],
                json.dumps(folders if folders is not None else [], ensure_ascii=False),
                summary[:500],
                "",
                int(count),
                now,
            ),
        )
        conn.commit()
        row_id = int(cur.lastrowid)
    result_name = f"{row_id}.json"
    result_path = hist_dir / result_name
    # Ne pas stocker posters/blobs inutiles — résultat déjà JSON-serializable
    slim = {k: v for k, v in result.items() if k != "cache"}
    slim["cache"] = result.get("cache")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(slim, f, ensure_ascii=False)
    with _connect() as conn:
        conn.execute(
            "UPDATE library_history SET result_file = ? WHERE id = ?",
            (result_name, row_id),
        )
        conn.commit()
    # Garder 40 entrées max
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, result_file FROM library_history ORDER BY id DESC"
        ).fetchall()
        for old in rows[40:]:
            conn.execute("DELETE FROM library_history WHERE id = ?", (old["id"],))
            try:
                (hist_dir / (old["result_file"] or "")).unlink(missing_ok=True)
            except OSError:
                pass
        conn.commit()
    return get_library_history_item(row_id) or {"id": row_id}


def _parse_library_folders(raw: str | None) -> dict:
    """Normalise folders_json (liste legacy ou dict a/b/path)."""
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError:
        data = []
    if isinstance(data, dict):
        folders_a = [str(x).strip() for x in (data.get("a") or []) if str(x).strip()]
        folders_b = [str(x).strip() for x in (data.get("b") or []) if str(x).strip()]
        path = str(data.get("path") or "").strip()
        if path and not folders_a and not folders_b:
            folders = [path]
        else:
            folders = folders_a + folders_b
        recursive = data.get("recursive")
        return {
            "folders": folders,
            "folders_a": folders_a,
            "folders_b": folders_b,
            "recursive": True if recursive is None else bool(recursive),
        }
    if isinstance(data, list):
        folders = [str(x).strip() for x in data if str(x).strip()]
        return {
            "folders": folders,
            "folders_a": [],
            "folders_b": [],
            "recursive": True,
        }
    return {"folders": [], "folders_a": [], "folders_b": [], "recursive": True}


def list_library_history(limit: int = 40) -> list[dict]:
    init_library_history()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, kind, title, folders_json, summary, count, created_at
            FROM library_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, min(100, limit)),),
        ).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        parsed = _parse_library_folders(item.pop("folders_json", None))
        item.update(parsed)
        out.append(item)
    return out


def get_library_history_item(item_id: int, *, include_result: bool = True) -> dict | None:
    from paths import DATA_DIR

    init_library_history()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM library_history WHERE id = ?", (item_id,)
        ).fetchone()
    if not row:
        return None
    item = dict(row)
    parsed = _parse_library_folders(item.pop("folders_json", None))
    item.update(parsed)
    if not include_result:
        item["result"] = None
        return item
    result_file = item.get("result_file") or ""
    path = DATA_DIR / "library_history" / result_file
    if path.is_file():
        try:
            with open(path, encoding="utf-8") as f:
                item["result"] = json.load(f)
        except (OSError, json.JSONDecodeError):
            item["result"] = None
    else:
        item["result"] = None
    return item


def delete_library_history(item_id: int) -> bool:
    from paths import DATA_DIR

    init_library_history()
    item = get_library_history_item(item_id)
    if not item:
        return False
    result_file = item.get("result_file") or ""
    with _connect() as conn:
        cur = conn.execute("DELETE FROM library_history WHERE id = ?", (item_id,))
        conn.commit()
        ok = cur.rowcount > 0
    if ok and result_file:
        try:
            (DATA_DIR / "library_history" / result_file).unlink(missing_ok=True)
        except OSError:
            pass
    return ok
