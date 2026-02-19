"""Content generation pipeline orchestrator."""

from __future__ import annotations

from datetime import UTC, date, datetime

from marketing_engine.agents.draft import DraftAgent
from marketing_engine.agents.format import FormatAgent
from marketing_engine.agents.queue import QueueAgent
from marketing_engine.agents.research import ResearchAgent
from marketing_engine.db import Database
from marketing_engine.enums import ContentStream
from marketing_engine.exceptions import PipelineError
from marketing_engine.llm.base import LLMClient
from marketing_engine.models import PipelineRun, PostDraft


class ContentPipeline:
    """Orchestrates the full content generation pipeline.

    Stages:
    1. Research — generate content briefs
    2. Draft — write raw post content for each brief
    3. Format — adapt posts to each target platform
    4. Queue — schedule posts across the week
    """

    def __init__(self, db: Database, llm: LLMClient, config: dict) -> None:
        self.db = db
        self.llm = llm
        self.config = config

    def run(
        self,
        week_of: date,
        streams: list[ContentStream] | None = None,
        activity: str = "",
    ) -> PipelineRun:
        """Execute the full pipeline for a given week.

        Args:
            week_of: The Monday of the target week.
            streams: Optional list of content streams to target.
            activity: Recent activity context for the research agent.

        Returns:
            A PipelineRun record with counts and status.

        Raises:
            PipelineError: If any stage of the pipeline fails.
        """
        pipeline_run = PipelineRun(week_of=week_of)
        self.db.save_pipeline_run(pipeline_run)

        try:
            # Stage 1: Research — generate briefs
            stream_values = [s.value for s in streams] if streams else None
            research_agent = ResearchAgent(llm=self.llm, config=self.config)
            briefs = research_agent.run(streams=stream_values, activity=activity)
            for brief in briefs:
                self.db.save_brief(brief, pipeline_run.id)
            pipeline_run.briefs_count = len(briefs)

            # Stage 2: Draft — write posts for each brief
            draft_agent = DraftAgent(
                llm=self.llm,
                config={
                    "brand_voice": self.config.get("brand_voice", {}),
                },
            )
            all_posts: list[PostDraft] = []
            for brief in briefs:
                draft_data = draft_agent.run(brief=brief)

                # Create a PostDraft for each target platform
                for platform in brief.platforms:
                    post = PostDraft(
                        brief_id=brief.id,
                        stream=brief.stream,
                        platform=platform,
                        content=draft_data.get("content", ""),
                        cta_url=draft_data.get("cta_url", ""),
                        hashtags=draft_data.get("hashtags", []),
                    )
                    all_posts.append(post)

            pipeline_run.drafts_count = len(all_posts)

            # Stage 3: Format — adapt to platform constraints
            format_agent = FormatAgent(
                llm=self.llm,
                config={
                    "platform_rules": self.config.get("platform_rules", {}),
                },
            )
            for post in all_posts:
                formatted = format_agent.run(
                    content=post.content,
                    platform=post.platform,
                    stream=post.stream,
                )
                post.content = formatted.get("content", post.content)
                post.hashtags = formatted.get("hashtags", post.hashtags)
                if formatted.get("subreddit"):
                    post.subreddit = formatted["subreddit"]

            # Stage 4: Queue — schedule across the week
            queue_agent = QueueAgent(config=self.config.get("schedule_rules", {}))
            queue_agent.schedule(all_posts, week_of)

            # Save all posts
            for post in all_posts:
                self.db.save_draft(post, pipeline_run.id)
            pipeline_run.posts_count = len(all_posts)

            # Mark completed
            pipeline_run.completed_at = datetime.now(UTC)
            pipeline_run.status = "completed"
            self.db.update_pipeline_run(
                pipeline_run.id,
                completed_at=pipeline_run.completed_at,
                briefs_count=pipeline_run.briefs_count,
                drafts_count=pipeline_run.drafts_count,
                posts_count=pipeline_run.posts_count,
                status="completed",
            )

        except PipelineError:
            raise
        except Exception as exc:
            pipeline_run.status = "failed"
            pipeline_run.error = str(exc)
            self.db.update_pipeline_run(
                pipeline_run.id,
                status="failed",
                error=str(exc),
            )
            raise PipelineError(f"Pipeline failed: {exc}") from exc

        return pipeline_run
