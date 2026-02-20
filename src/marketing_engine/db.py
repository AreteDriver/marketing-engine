"""SQLite database layer for marketing engine."""

from __future__ import annotations

import functools
import json
import sqlite3
import threading
from datetime import UTC, date, datetime
from pathlib import Path

from marketing_engine.enums import ApprovalStatus, ContentStream, Platform, PublishStatus
from marketing_engine.exceptions import DatabaseError
from marketing_engine.models import ContentBrief, PipelineRun, PostDraft
from marketing_engine.publishers.result import PublishResult

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id TEXT PRIMARY KEY,
    week_of TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    briefs_count INTEGER DEFAULT 0,
    drafts_count INTEGER DEFAULT 0,
    posts_count INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'running',
    error TEXT
);
CREATE TABLE IF NOT EXISTS content_briefs (
    id TEXT PRIMARY KEY,
    pipeline_run_id TEXT NOT NULL REFERENCES pipeline_runs(id),
    topic TEXT NOT NULL,
    angle TEXT NOT NULL,
    target_audience TEXT NOT NULL,
    relevant_links TEXT NOT NULL DEFAULT '[]',
    stream TEXT NOT NULL,
    platforms TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS post_drafts (
    id TEXT PRIMARY KEY,
    brief_id TEXT NOT NULL REFERENCES content_briefs(id),
    pipeline_run_id TEXT NOT NULL REFERENCES pipeline_runs(id),
    stream TEXT NOT NULL,
    platform TEXT NOT NULL,
    content TEXT NOT NULL,
    media_urls TEXT NOT NULL DEFAULT '[]',
    cta_url TEXT NOT NULL DEFAULT '',
    hashtags TEXT NOT NULL DEFAULT '[]',
    subreddit TEXT,
    scheduled_time TEXT,
    approval_status TEXT NOT NULL DEFAULT 'pending',
    edited_content TEXT,
    rejection_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_drafts_status ON post_drafts(approval_status);
CREATE INDEX IF NOT EXISTS idx_drafts_platform ON post_drafts(platform);
CREATE INDEX IF NOT EXISTS idx_drafts_scheduled ON post_drafts(scheduled_time);
CREATE INDEX IF NOT EXISTS idx_briefs_pipeline ON content_briefs(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_drafts_pipeline ON post_drafts(pipeline_run_id);
CREATE TABLE IF NOT EXISTS publish_log (
    id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    status TEXT NOT NULL,
    platform_post_id TEXT,
    post_url TEXT,
    error TEXT,
    published_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_publish_log_post ON publish_log(post_id);
"""

_MIGRATION_COLUMNS = [
    ("post_drafts", "publish_status", "TEXT NOT NULL DEFAULT 'pending'"),
    ("post_drafts", "published_at", "TEXT"),
    ("post_drafts", "post_url", "TEXT"),
    ("post_drafts", "platform_post_id", "TEXT"),
    ("post_drafts", "publish_error", "TEXT"),
]


class Database:
    """SQLite database wrapper with WAL mode and thread-local connections."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._local = threading.local()
        # Ensure parent directory exists
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create a thread-local database connection."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return conn

    def init_schema(self) -> None:
        """Create tables and indexes if they do not exist."""
        conn = self._get_conn()
        try:
            conn.executescript(_SCHEMA)
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to initialize schema: {exc}") from exc
        self._migrate_columns(conn)

    def _migrate_columns(self, conn: sqlite3.Connection) -> None:
        """Add columns that may be missing from older schemas."""
        for table, column, col_def in _MIGRATION_COLUMNS:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
                conn.commit()
            except sqlite3.OperationalError:
                # Column already exists
                pass

    def save_brief(self, brief: ContentBrief, pipeline_run_id: str) -> str:
        """Insert a content brief and return its ID."""
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO content_briefs
                   (id, pipeline_run_id, topic, angle, target_audience,
                    relevant_links, stream, platforms, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    brief.id,
                    pipeline_run_id,
                    brief.topic,
                    brief.angle,
                    brief.target_audience,
                    json.dumps(brief.relevant_links),
                    brief.stream.value,
                    json.dumps([p.value for p in brief.platforms]),
                    brief.created_at.isoformat(),
                ),
            )
            conn.commit()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to save brief {brief.id}: {exc}") from exc
        return brief.id

    def save_draft(self, draft: PostDraft, pipeline_run_id: str) -> str:
        """Insert a post draft and return its ID."""
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO post_drafts
                   (id, brief_id, pipeline_run_id, stream, platform, content,
                    media_urls, cta_url, hashtags, subreddit, scheduled_time,
                    approval_status, edited_content, rejection_reason,
                    publish_status, published_at, post_url, platform_post_id,
                    publish_error, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    draft.id,
                    draft.brief_id,
                    pipeline_run_id,
                    draft.stream.value,
                    draft.platform.value,
                    draft.content,
                    json.dumps(draft.media_urls),
                    draft.cta_url,
                    json.dumps(draft.hashtags),
                    draft.subreddit,
                    draft.scheduled_time.isoformat() if draft.scheduled_time else None,
                    draft.approval_status.value,
                    draft.edited_content,
                    draft.rejection_reason,
                    draft.publish_status.value,
                    draft.published_at.isoformat() if draft.published_at else None,
                    draft.post_url,
                    draft.platform_post_id,
                    draft.publish_error,
                    draft.created_at.isoformat(),
                    draft.updated_at.isoformat(),
                ),
            )
            conn.commit()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to save draft {draft.id}: {exc}") from exc
        return draft.id

    def save_pipeline_run(self, run: PipelineRun) -> str:
        """Insert a pipeline run record and return its ID."""
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO pipeline_runs
                   (id, week_of, started_at, completed_at, briefs_count,
                    drafts_count, posts_count, status, error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run.id,
                    run.week_of.isoformat(),
                    run.started_at.isoformat(),
                    run.completed_at.isoformat() if run.completed_at else None,
                    run.briefs_count,
                    run.drafts_count,
                    run.posts_count,
                    run.status,
                    run.error,
                ),
            )
            conn.commit()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to save pipeline run {run.id}: {exc}") from exc
        return run.id

    def update_pipeline_run(self, run_id: str, **kwargs: object) -> None:
        """Update fields on an existing pipeline run."""
        if not kwargs:
            return
        conn = self._get_conn()
        allowed = {
            "completed_at",
            "briefs_count",
            "drafts_count",
            "posts_count",
            "status",
            "error",
        }
        filtered = {k: v for k, v in kwargs.items() if k in allowed}
        if not filtered:
            return
        # Serialize datetime values
        for key, val in filtered.items():
            if isinstance(val, (datetime, date)):
                filtered[key] = val.isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in filtered)
        values = list(filtered.values()) + [run_id]
        try:
            conn.execute(
                f"UPDATE pipeline_runs SET {set_clause} WHERE id = ?",  # noqa: S608
                values,
            )
            conn.commit()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to update pipeline run {run_id}: {exc}") from exc

    def _row_to_post(self, row: sqlite3.Row) -> PostDraft:
        """Convert a database row to a PostDraft model."""
        return PostDraft(
            id=row["id"],
            brief_id=row["brief_id"],
            stream=ContentStream(row["stream"]),
            platform=Platform(row["platform"]),
            content=row["content"],
            media_urls=json.loads(row["media_urls"]),
            cta_url=row["cta_url"],
            hashtags=json.loads(row["hashtags"]),
            subreddit=row["subreddit"],
            scheduled_time=(
                datetime.fromisoformat(row["scheduled_time"]) if row["scheduled_time"] else None
            ),
            approval_status=ApprovalStatus(row["approval_status"]),
            edited_content=row["edited_content"],
            rejection_reason=row["rejection_reason"],
            publish_status=PublishStatus(row["publish_status"]),
            published_at=(
                datetime.fromisoformat(row["published_at"]) if row["published_at"] else None
            ),
            post_url=row["post_url"],
            platform_post_id=row["platform_post_id"],
            publish_error=row["publish_error"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def get_queue(self, week_of: date) -> list[PostDraft]:
        """Return all posts scheduled for the given week."""
        conn = self._get_conn()
        # Week boundaries: week_of (Monday) to week_of + 6 days (Sunday)
        start = week_of.isoformat()
        end_date = date.fromordinal(week_of.toordinal() + 7)
        end = end_date.isoformat()
        try:
            rows = conn.execute(
                """SELECT * FROM post_drafts
                   WHERE scheduled_time >= ? AND scheduled_time < ?
                   ORDER BY scheduled_time""",
                (start, end),
            ).fetchall()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to get queue for {week_of}: {exc}") from exc
        return [self._row_to_post(r) for r in rows]

    def get_pending(self, week_of: date | None = None) -> list[PostDraft]:
        """Return pending posts, optionally filtered by week."""
        conn = self._get_conn()
        try:
            if week_of is not None:
                start = week_of.isoformat()
                end_date = date.fromordinal(week_of.toordinal() + 7)
                end = end_date.isoformat()
                rows = conn.execute(
                    """SELECT * FROM post_drafts
                       WHERE approval_status = 'pending'
                         AND scheduled_time >= ? AND scheduled_time < ?
                       ORDER BY scheduled_time""",
                    (start, end),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM post_drafts
                       WHERE approval_status = 'pending'
                       ORDER BY scheduled_time""",
                ).fetchall()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to get pending posts: {exc}") from exc
        return [self._row_to_post(r) for r in rows]

    def get_post(self, post_id: str) -> PostDraft | None:
        """Return a single post by ID, or None if not found."""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM post_drafts WHERE id = ?", (post_id,)).fetchone()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to get post {post_id}: {exc}") from exc
        if row is None:
            return None
        return self._row_to_post(row)

    def update_approval(
        self,
        post_id: str,
        status: ApprovalStatus,
        edited_content: str | None = None,
        rejection_reason: str | None = None,
    ) -> None:
        """Update the approval status of a post."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()
        try:
            conn.execute(
                """UPDATE post_drafts
                   SET approval_status = ?, edited_content = ?,
                       rejection_reason = ?, updated_at = ?
                   WHERE id = ?""",
                (status.value, edited_content, rejection_reason, now, post_id),
            )
            conn.commit()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to update approval for {post_id}: {exc}") from exc

    def _row_to_run(self, row: sqlite3.Row) -> PipelineRun:
        """Convert a database row to a PipelineRun model."""
        return PipelineRun(
            id=row["id"],
            week_of=date.fromisoformat(row["week_of"]),
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=(
                datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None
            ),
            briefs_count=row["briefs_count"],
            drafts_count=row["drafts_count"],
            posts_count=row["posts_count"],
            status=row["status"],
            error=row["error"],
        )

    def get_pipeline_runs(self, limit: int = 10) -> list[PipelineRun]:
        """Return recent pipeline runs, newest first."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to get pipeline runs: {exc}") from exc
        return [self._row_to_run(r) for r in rows]

    def get_publishable(self, now: datetime) -> list[PostDraft]:
        """Return approved posts that are due for publishing."""
        conn = self._get_conn()
        now_str = now.isoformat()
        try:
            rows = conn.execute(
                """SELECT * FROM post_drafts
                   WHERE approval_status IN ('approved', 'edited')
                     AND publish_status = 'pending'
                     AND scheduled_time <= ?
                   ORDER BY scheduled_time""",
                (now_str,),
            ).fetchall()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to get publishable posts: {exc}") from exc
        return [self._row_to_post(r) for r in rows]

    def update_publish_status(
        self,
        post_id: str,
        status: PublishStatus,
        published_at: datetime | None = None,
        post_url: str | None = None,
        platform_post_id: str | None = None,
        publish_error: str | None = None,
    ) -> None:
        """Update the publish status and related fields of a post."""
        conn = self._get_conn()
        now = datetime.now(UTC).isoformat()
        try:
            conn.execute(
                """UPDATE post_drafts
                   SET publish_status = ?, published_at = ?, post_url = ?,
                       platform_post_id = ?, publish_error = ?, updated_at = ?
                   WHERE id = ?""",
                (
                    status.value,
                    published_at.isoformat() if published_at else None,
                    post_url,
                    platform_post_id,
                    publish_error,
                    now,
                    post_id,
                ),
            )
            conn.commit()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to update publish status for {post_id}: {exc}") from exc

    def save_publish_log(self, result: PublishResult) -> None:
        """Insert a publish log entry."""
        from uuid import uuid4

        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO publish_log
                   (id, post_id, platform, status, platform_post_id,
                    post_url, error, published_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid4()),
                    result.post_id,
                    result.platform.value,
                    "published" if result.success else "failed",
                    result.platform_post_id,
                    result.post_url,
                    result.error,
                    result.published_at.isoformat() if result.published_at else None,
                ),
            )
            conn.commit()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to save publish log: {exc}") from exc

    def get_publish_history(self, limit: int = 20) -> list[dict]:
        """Return recent publish log entries."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM publish_log ORDER BY published_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to get publish history: {exc}") from exc
        return [dict(r) for r in rows]

    def close(self) -> None:
        """Close the thread-local database connection."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None


@functools.lru_cache(maxsize=1)
def get_database() -> Database:
    """Return a cached singleton Database instance."""
    from marketing_engine.config import get_db_path

    return Database(get_db_path())


def reset_database() -> None:
    """Clear the cached Database singleton."""
    get_database.cache_clear()
