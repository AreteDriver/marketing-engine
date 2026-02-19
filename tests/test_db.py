"""Tests for marketing_engine.db."""

from __future__ import annotations

from datetime import UTC, date, datetime

from marketing_engine.db import Database
from marketing_engine.enums import ApprovalStatus, ContentStream, Platform
from marketing_engine.models import PipelineRun, PostDraft

# --- Schema ---


class TestSchema:
    def test_pipeline_runs_table_exists(self, tmp_db):
        conn = tmp_db._get_conn()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='pipeline_runs'"
        ).fetchone()
        assert row is not None

    def test_content_briefs_table_exists(self, tmp_db):
        conn = tmp_db._get_conn()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='content_briefs'"
        ).fetchone()
        assert row is not None

    def test_post_drafts_table_exists(self, tmp_db):
        conn = tmp_db._get_conn()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='post_drafts'"
        ).fetchone()
        assert row is not None

    def test_wal_mode_enabled(self, tmp_db):
        conn = tmp_db._get_conn()
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"

    def test_foreign_keys_enabled(self, tmp_db):
        conn = tmp_db._get_conn()
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1


# --- save_brief ---


class TestSaveBrief:
    def test_inserts_and_returns_id(self, tmp_db, sample_brief, sample_pipeline_run):
        tmp_db.save_pipeline_run(sample_pipeline_run)
        brief_id = tmp_db.save_brief(sample_brief, sample_pipeline_run.id)
        assert brief_id == sample_brief.id

    def test_brief_retrievable_via_sql(self, tmp_db, sample_brief, sample_pipeline_run):
        tmp_db.save_pipeline_run(sample_pipeline_run)
        tmp_db.save_brief(sample_brief, sample_pipeline_run.id)
        conn = tmp_db._get_conn()
        row = conn.execute(
            "SELECT * FROM content_briefs WHERE id = ?", (sample_brief.id,)
        ).fetchone()
        assert row is not None
        assert row["topic"] == sample_brief.topic
        assert row["angle"] == sample_brief.angle
        assert row["stream"] == sample_brief.stream.value


# --- save_draft ---


class TestSaveDraft:
    def test_inserts_and_returns_id(self, tmp_db, sample_post, sample_brief, sample_pipeline_run):
        tmp_db.save_pipeline_run(sample_pipeline_run)
        tmp_db.save_brief(sample_brief, sample_pipeline_run.id)
        draft_id = tmp_db.save_draft(sample_post, sample_pipeline_run.id)
        assert draft_id == sample_post.id

    def test_draft_retrievable_via_sql(
        self, tmp_db, sample_post, sample_brief, sample_pipeline_run
    ):
        tmp_db.save_pipeline_run(sample_pipeline_run)
        tmp_db.save_brief(sample_brief, sample_pipeline_run.id)
        tmp_db.save_draft(sample_post, sample_pipeline_run.id)
        conn = tmp_db._get_conn()
        row = conn.execute("SELECT * FROM post_drafts WHERE id = ?", (sample_post.id,)).fetchone()
        assert row is not None
        assert row["content"] == sample_post.content
        assert row["platform"] == sample_post.platform.value


# --- save_pipeline_run ---


class TestSavePipelineRun:
    def test_inserts_and_returns_id(self, tmp_db, sample_pipeline_run):
        run_id = tmp_db.save_pipeline_run(sample_pipeline_run)
        assert run_id == sample_pipeline_run.id

    def test_run_retrievable_via_sql(self, tmp_db, sample_pipeline_run):
        tmp_db.save_pipeline_run(sample_pipeline_run)
        conn = tmp_db._get_conn()
        row = conn.execute(
            "SELECT * FROM pipeline_runs WHERE id = ?", (sample_pipeline_run.id,)
        ).fetchone()
        assert row is not None
        assert row["status"] == "running"
        assert row["week_of"] == sample_pipeline_run.week_of.isoformat()


# --- update_pipeline_run ---


class TestUpdatePipelineRun:
    def test_updates_status(self, tmp_db, sample_pipeline_run):
        tmp_db.save_pipeline_run(sample_pipeline_run)
        tmp_db.update_pipeline_run(sample_pipeline_run.id, status="completed")
        conn = tmp_db._get_conn()
        row = conn.execute(
            "SELECT status FROM pipeline_runs WHERE id = ?", (sample_pipeline_run.id,)
        ).fetchone()
        assert row["status"] == "completed"

    def test_updates_completed_at_datetime(self, tmp_db, sample_pipeline_run):
        tmp_db.save_pipeline_run(sample_pipeline_run)
        now = datetime(2025, 3, 3, 9, 30, tzinfo=UTC)
        tmp_db.update_pipeline_run(sample_pipeline_run.id, completed_at=now)
        conn = tmp_db._get_conn()
        row = conn.execute(
            "SELECT completed_at FROM pipeline_runs WHERE id = ?", (sample_pipeline_run.id,)
        ).fetchone()
        assert row["completed_at"] == now.isoformat()

    def test_updates_briefs_count(self, tmp_db, sample_pipeline_run):
        tmp_db.save_pipeline_run(sample_pipeline_run)
        tmp_db.update_pipeline_run(sample_pipeline_run.id, briefs_count=5)
        conn = tmp_db._get_conn()
        row = conn.execute(
            "SELECT briefs_count FROM pipeline_runs WHERE id = ?", (sample_pipeline_run.id,)
        ).fetchone()
        assert row["briefs_count"] == 5

    def test_empty_kwargs_does_nothing(self, tmp_db, sample_pipeline_run):
        tmp_db.save_pipeline_run(sample_pipeline_run)
        tmp_db.update_pipeline_run(sample_pipeline_run.id)
        conn = tmp_db._get_conn()
        row = conn.execute(
            "SELECT status FROM pipeline_runs WHERE id = ?", (sample_pipeline_run.id,)
        ).fetchone()
        assert row["status"] == "running"

    def test_non_allowed_keys_ignored(self, tmp_db, sample_pipeline_run):
        tmp_db.save_pipeline_run(sample_pipeline_run)
        tmp_db.update_pipeline_run(sample_pipeline_run.id, bogus_field="nope")
        conn = tmp_db._get_conn()
        row = conn.execute(
            "SELECT * FROM pipeline_runs WHERE id = ?", (sample_pipeline_run.id,)
        ).fetchone()
        assert row["status"] == "running"


# --- get_queue ---


class TestGetQueue:
    def _insert_post(self, tmp_db, sample_brief, sample_pipeline_run, scheduled_time, post_id):
        """Helper to insert a post with a specific scheduled_time."""
        post = PostDraft(
            id=post_id,
            brief_id=sample_brief.id,
            stream=ContentStream.project_marketing,
            platform=Platform.twitter,
            content=f"Post {post_id}",
            scheduled_time=scheduled_time,
            created_at=datetime(2025, 3, 3, 12, 0, tzinfo=UTC),
            updated_at=datetime(2025, 3, 3, 12, 0, tzinfo=UTC),
        )
        tmp_db.save_draft(post, sample_pipeline_run.id)

    def test_returns_posts_for_week(self, tmp_db, sample_brief, sample_pipeline_run):
        tmp_db.save_pipeline_run(sample_pipeline_run)
        tmp_db.save_brief(sample_brief, sample_pipeline_run.id)
        self._insert_post(
            tmp_db,
            sample_brief,
            sample_pipeline_run,
            datetime(2025, 3, 4, 10, 0, tzinfo=UTC),
            "q1",
        )
        self._insert_post(
            tmp_db,
            sample_brief,
            sample_pipeline_run,
            datetime(2025, 3, 5, 14, 0, tzinfo=UTC),
            "q2",
        )
        # week_of=Monday 2025-03-03
        queue = tmp_db.get_queue(date(2025, 3, 3))
        assert len(queue) == 2
        # Should be sorted by scheduled_time
        assert queue[0].id == "q1"
        assert queue[1].id == "q2"

    def test_empty_week_returns_empty(self, tmp_db, sample_brief, sample_pipeline_run):
        tmp_db.save_pipeline_run(sample_pipeline_run)
        tmp_db.save_brief(sample_brief, sample_pipeline_run.id)
        self._insert_post(
            tmp_db,
            sample_brief,
            sample_pipeline_run,
            datetime(2025, 3, 4, 10, 0, tzinfo=UTC),
            "q3",
        )
        # Query a different week
        queue = tmp_db.get_queue(date(2025, 4, 7))
        assert queue == []


# --- get_pending ---


class TestGetPending:
    def _save_setup(self, tmp_db, sample_brief, sample_pipeline_run):
        """Insert the pipeline run and brief so foreign keys are satisfied."""
        tmp_db.save_pipeline_run(sample_pipeline_run)
        tmp_db.save_brief(sample_brief, sample_pipeline_run.id)

    def test_returns_only_pending(self, tmp_db, sample_brief, sample_pipeline_run):
        self._save_setup(tmp_db, sample_brief, sample_pipeline_run)
        pending = PostDraft(
            id="pend-1",
            brief_id=sample_brief.id,
            stream=ContentStream.project_marketing,
            platform=Platform.twitter,
            content="Pending post",
            scheduled_time=datetime(2025, 3, 4, 10, 0, tzinfo=UTC),
            approval_status=ApprovalStatus.pending,
            created_at=datetime(2025, 3, 3, 12, 0, tzinfo=UTC),
            updated_at=datetime(2025, 3, 3, 12, 0, tzinfo=UTC),
        )
        approved = PostDraft(
            id="appr-1",
            brief_id=sample_brief.id,
            stream=ContentStream.project_marketing,
            platform=Platform.linkedin,
            content="Approved post",
            scheduled_time=datetime(2025, 3, 4, 12, 0, tzinfo=UTC),
            approval_status=ApprovalStatus.approved,
            created_at=datetime(2025, 3, 3, 12, 0, tzinfo=UTC),
            updated_at=datetime(2025, 3, 3, 12, 0, tzinfo=UTC),
        )
        tmp_db.save_draft(pending, sample_pipeline_run.id)
        tmp_db.save_draft(approved, sample_pipeline_run.id)
        result = tmp_db.get_pending()
        assert len(result) == 1
        assert result[0].id == "pend-1"

    def test_with_week_of_filter(self, tmp_db, sample_brief, sample_pipeline_run):
        self._save_setup(tmp_db, sample_brief, sample_pipeline_run)
        in_week = PostDraft(
            id="pw-1",
            brief_id=sample_brief.id,
            stream=ContentStream.project_marketing,
            platform=Platform.twitter,
            content="In-week pending",
            scheduled_time=datetime(2025, 3, 4, 10, 0, tzinfo=UTC),
            approval_status=ApprovalStatus.pending,
            created_at=datetime(2025, 3, 3, 12, 0, tzinfo=UTC),
            updated_at=datetime(2025, 3, 3, 12, 0, tzinfo=UTC),
        )
        out_week = PostDraft(
            id="pw-2",
            brief_id=sample_brief.id,
            stream=ContentStream.project_marketing,
            platform=Platform.twitter,
            content="Out-of-week pending",
            scheduled_time=datetime(2025, 4, 10, 10, 0, tzinfo=UTC),
            approval_status=ApprovalStatus.pending,
            created_at=datetime(2025, 3, 3, 12, 0, tzinfo=UTC),
            updated_at=datetime(2025, 3, 3, 12, 0, tzinfo=UTC),
        )
        tmp_db.save_draft(in_week, sample_pipeline_run.id)
        tmp_db.save_draft(out_week, sample_pipeline_run.id)
        result = tmp_db.get_pending(week_of=date(2025, 3, 3))
        assert len(result) == 1
        assert result[0].id == "pw-1"

    def test_without_week_of_returns_all_pending(self, tmp_db, sample_brief, sample_pipeline_run):
        self._save_setup(tmp_db, sample_brief, sample_pipeline_run)
        p1 = PostDraft(
            id="all-1",
            brief_id=sample_brief.id,
            stream=ContentStream.project_marketing,
            platform=Platform.twitter,
            content="First pending",
            scheduled_time=datetime(2025, 3, 4, 10, 0, tzinfo=UTC),
            approval_status=ApprovalStatus.pending,
            created_at=datetime(2025, 3, 3, 12, 0, tzinfo=UTC),
            updated_at=datetime(2025, 3, 3, 12, 0, tzinfo=UTC),
        )
        p2 = PostDraft(
            id="all-2",
            brief_id=sample_brief.id,
            stream=ContentStream.project_marketing,
            platform=Platform.twitter,
            content="Second pending",
            scheduled_time=datetime(2025, 5, 1, 10, 0, tzinfo=UTC),
            approval_status=ApprovalStatus.pending,
            created_at=datetime(2025, 3, 3, 12, 0, tzinfo=UTC),
            updated_at=datetime(2025, 3, 3, 12, 0, tzinfo=UTC),
        )
        tmp_db.save_draft(p1, sample_pipeline_run.id)
        tmp_db.save_draft(p2, sample_pipeline_run.id)
        result = tmp_db.get_pending()
        assert len(result) == 2


# --- get_post ---


class TestGetPost:
    def test_returns_post_by_id(self, tmp_db, sample_post, sample_brief, sample_pipeline_run):
        tmp_db.save_pipeline_run(sample_pipeline_run)
        tmp_db.save_brief(sample_brief, sample_pipeline_run.id)
        tmp_db.save_draft(sample_post, sample_pipeline_run.id)
        post = tmp_db.get_post(sample_post.id)
        assert post is not None
        assert post.id == sample_post.id
        assert post.content == sample_post.content

    def test_returns_none_for_nonexistent(self, tmp_db):
        assert tmp_db.get_post("does-not-exist") is None


# --- update_approval ---


class TestUpdateApproval:
    def _setup(self, tmp_db, sample_brief, sample_pipeline_run, sample_post):
        tmp_db.save_pipeline_run(sample_pipeline_run)
        tmp_db.save_brief(sample_brief, sample_pipeline_run.id)
        tmp_db.save_draft(sample_post, sample_pipeline_run.id)

    def test_approve(self, tmp_db, sample_brief, sample_pipeline_run, sample_post):
        self._setup(tmp_db, sample_brief, sample_pipeline_run, sample_post)
        tmp_db.update_approval(sample_post.id, ApprovalStatus.approved)
        post = tmp_db.get_post(sample_post.id)
        assert post is not None
        assert post.approval_status == ApprovalStatus.approved

    def test_edit(self, tmp_db, sample_brief, sample_pipeline_run, sample_post):
        self._setup(tmp_db, sample_brief, sample_pipeline_run, sample_post)
        tmp_db.update_approval(
            sample_post.id, ApprovalStatus.edited, edited_content="Updated content here."
        )
        post = tmp_db.get_post(sample_post.id)
        assert post is not None
        assert post.approval_status == ApprovalStatus.edited
        assert post.edited_content == "Updated content here."

    def test_reject(self, tmp_db, sample_brief, sample_pipeline_run, sample_post):
        self._setup(tmp_db, sample_brief, sample_pipeline_run, sample_post)
        tmp_db.update_approval(
            sample_post.id, ApprovalStatus.rejected, rejection_reason="Off-brand"
        )
        post = tmp_db.get_post(sample_post.id)
        assert post is not None
        assert post.approval_status == ApprovalStatus.rejected
        assert post.rejection_reason == "Off-brand"


# --- get_pipeline_runs ---


class TestGetPipelineRuns:
    def test_returns_newest_first(self, tmp_db):
        run_old = PipelineRun(
            id="run-old",
            week_of=date(2025, 2, 24),
            started_at=datetime(2025, 2, 24, 8, 0, tzinfo=UTC),
        )
        run_new = PipelineRun(
            id="run-new",
            week_of=date(2025, 3, 3),
            started_at=datetime(2025, 3, 3, 8, 0, tzinfo=UTC),
        )
        tmp_db.save_pipeline_run(run_old)
        tmp_db.save_pipeline_run(run_new)
        runs = tmp_db.get_pipeline_runs()
        assert len(runs) == 2
        assert runs[0].id == "run-new"
        assert runs[1].id == "run-old"

    def test_limit_parameter(self, tmp_db):
        for i in range(5):
            run = PipelineRun(
                id=f"run-{i}",
                week_of=date(2025, 3, 3),
                started_at=datetime(2025, 3, 3, 8 + i, 0, tzinfo=UTC),
            )
            tmp_db.save_pipeline_run(run)
        runs = tmp_db.get_pipeline_runs(limit=2)
        assert len(runs) == 2

    def test_empty_returns_empty(self, tmp_db):
        assert tmp_db.get_pipeline_runs() == []


# --- close ---


class TestClose:
    def test_close_succeeds(self, tmp_path):
        db = Database(tmp_path / "close_test.db")
        db.close()
        # After close, getting a new connection should work (lazy reconnect)
        conn = db._get_conn()
        assert conn is not None
        db.close()


# --- round trip ---


class TestRoundTrip:
    def test_save_brief_and_draft_then_get_post(
        self, tmp_db, sample_brief, sample_pipeline_run, sample_post
    ):
        tmp_db.save_pipeline_run(sample_pipeline_run)
        tmp_db.save_brief(sample_brief, sample_pipeline_run.id)
        tmp_db.save_draft(sample_post, sample_pipeline_run.id)

        post = tmp_db.get_post(sample_post.id)
        assert post is not None
        assert post.id == sample_post.id
        assert post.brief_id == sample_brief.id
        assert post.stream == sample_post.stream
        assert post.platform == sample_post.platform
        assert post.content == sample_post.content
        assert post.hashtags == sample_post.hashtags
        assert post.approval_status == ApprovalStatus.pending
        assert post.scheduled_time is not None
