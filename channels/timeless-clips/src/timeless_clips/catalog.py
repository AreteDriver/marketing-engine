"""SQLite catalog for discovered Internet Archive items."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

from timeless_clips.models import ArchiveItem

_SCHEMA = """
CREATE TABLE IF NOT EXISTS catalog (
    identifier TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    year INTEGER,
    collection TEXT NOT NULL,
    media_type TEXT NOT NULL DEFAULT 'movies',
    license_info TEXT NOT NULL DEFAULT 'publicdomain',
    source_url TEXT NOT NULL,
    download_urls TEXT NOT NULL DEFAULT '[]',
    duration REAL,
    category TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '[]',
    discovered_at TEXT NOT NULL,
    processed BOOLEAN DEFAULT 0,
    processed_at TEXT,
    local_path TEXT,
    short_path TEXT,
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_catalog_category ON catalog(category);
CREATE INDEX IF NOT EXISTS idx_catalog_processed ON catalog(processed);
CREATE INDEX IF NOT EXISTS idx_catalog_collection ON catalog(collection);
"""


class Catalog:
    """SQLite catalog for Internet Archive items."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._local = threading.local()
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create a thread-local database connection."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn = conn
        return conn

    def _init_schema(self) -> None:
        """Create tables and indexes if they do not exist."""
        conn = self._get_conn()
        conn.executescript(_SCHEMA)

    def save_item(self, item: ArchiveItem, metadata: dict | None = None) -> None:
        """Upsert an archive item into the catalog."""
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO catalog
               (identifier, title, description, year, collection, media_type,
                license_info, source_url, download_urls, duration, category, tags,
                discovered_at, processed, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item.identifier,
                item.title,
                item.description,
                item.year,
                item.collection,
                item.media_type,
                item.license_info,
                item.source_url,
                json.dumps(item.download_urls),
                item.duration,
                item.category,
                json.dumps(item.tags),
                item.discovered_at.isoformat(),
                int(item.processed),
                json.dumps(metadata or {}),
            ),
        )
        conn.commit()

    def get_unprocessed(self, category: str | None = None, limit: int = 10) -> list[ArchiveItem]:
        """Return unprocessed items, optionally filtered by category."""
        conn = self._get_conn()
        if category:
            rows = conn.execute(
                "SELECT * FROM catalog WHERE processed = 0 AND category = ? LIMIT ?",
                (category, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM catalog WHERE processed = 0 LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_item(r) for r in rows]

    def mark_processed(self, identifier: str, short_path: str | None = None) -> None:
        """Mark an item as processed."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()
        conn.execute(
            "UPDATE catalog SET processed = 1, processed_at = ?, short_path = ? "
            "WHERE identifier = ?",
            (now, short_path, identifier),
        )
        conn.commit()

    def set_local_path(self, identifier: str, local_path: str) -> None:
        """Set the local file path for a downloaded item."""
        conn = self._get_conn()
        conn.execute(
            "UPDATE catalog SET local_path = ? WHERE identifier = ?",
            (local_path, identifier),
        )
        conn.commit()

    def get_item(self, identifier: str) -> ArchiveItem | None:
        """Get a single item by identifier."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM catalog WHERE identifier = ?",
            (identifier,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_item(row)

    def get_stats(self) -> dict:
        """Return catalog statistics."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM catalog").fetchone()[0]
        processed = conn.execute("SELECT COUNT(*) FROM catalog WHERE processed = 1").fetchone()[0]

        by_category: dict[str, int] = {}
        for row in conn.execute(
            "SELECT category, COUNT(*) as cnt FROM catalog GROUP BY category"
        ).fetchall():
            by_category[row["category"]] = row["cnt"]

        by_collection: dict[str, int] = {}
        for row in conn.execute(
            "SELECT collection, COUNT(*) as cnt FROM catalog GROUP BY collection"
        ).fetchall():
            by_collection[row["collection"]] = row["cnt"]

        return {
            "total": total,
            "processed": processed,
            "unprocessed": total - processed,
            "by_category": by_category,
            "by_collection": by_collection,
        }

    def _row_to_item(self, row: sqlite3.Row) -> ArchiveItem:
        """Convert a database row to an ArchiveItem model."""
        return ArchiveItem(
            identifier=row["identifier"],
            title=row["title"],
            description=row["description"],
            year=row["year"],
            collection=row["collection"],
            media_type=row["media_type"],
            license_info=row["license_info"],
            source_url=row["source_url"],
            download_urls=json.loads(row["download_urls"]),
            duration=row["duration"],
            category=row["category"],
            tags=json.loads(row["tags"]),
            discovered_at=datetime.fromisoformat(row["discovered_at"]),
            processed=bool(row["processed"]),
        )

    def close(self) -> None:
        """Close the thread-local database connection."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None
