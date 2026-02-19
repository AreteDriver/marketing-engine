"""Research agent for generating content briefs."""

from __future__ import annotations

import json
from typing import Any

from marketing_engine.agents.base import BaseAgent
from marketing_engine.enums import ContentStream, Platform
from marketing_engine.models import ContentBrief

_SYSTEM_PROMPT = (
    "You are a content strategist for a developer's project portfolio. "
    "Given content streams and recent activity, produce content briefs. "
    "Each brief should have a unique angle that drives engagement. "
    "Output ONLY a JSON array of objects with keys: "
    "topic, angle, target_audience, relevant_links (array of URLs), "
    "stream (one of: project_marketing, benchgoblins, eve_content, "
    "linux_tools, technical_ai), "
    "platforms (array of: twitter, linkedin, reddit)."
)

_ALL_STREAMS = [s.value for s in ContentStream]


class ResearchAgent(BaseAgent):
    """Generates content briefs from streams and recent activity."""

    @property
    def system_prompt(self) -> str:
        return _SYSTEM_PROMPT

    def build_user_prompt(
        self,
        streams: list[str] | None = None,
        activity: str = "",
        **kwargs: Any,
    ) -> str:
        """Build user prompt with target streams and activity context."""
        target_streams = streams if streams else _ALL_STREAMS
        lines = [
            "Generate content briefs for the following streams:",
            ", ".join(target_streams),
        ]
        if activity:
            lines.append("")
            lines.append("Recent activity and context:")
            lines.append(activity)
        lines.append("")
        lines.append(
            "Create one brief per stream. Each brief should target 2-3 platforms for maximum reach."
        )
        return "\n".join(lines)

    def parse_response(self, raw: str) -> list[ContentBrief]:
        """Parse JSON array into ContentBrief models."""
        data = json.loads(raw)
        if not isinstance(data, list):
            data = [data]

        briefs = []
        for item in data:
            # Normalize platform values
            platforms = []
            for p in item.get("platforms", ["twitter"]):
                p_lower = p.lower().strip()
                if p_lower in Platform.__members__:
                    platforms.append(Platform(p_lower))
            if not platforms:
                platforms = [Platform.twitter]

            # Normalize stream value
            stream_val = item.get("stream", "project_marketing").lower().strip()
            if stream_val not in ContentStream.__members__:
                stream_val = "project_marketing"

            brief = ContentBrief(
                topic=item.get("topic", "Untitled"),
                angle=item.get("angle", ""),
                target_audience=item.get("target_audience", "developers"),
                relevant_links=item.get("relevant_links", []),
                stream=ContentStream(stream_val),
                platforms=platforms,
            )
            briefs.append(brief)
        return briefs

    def run(
        self,
        streams: list[str] | None = None,
        activity: str = "",
        **kwargs: Any,
    ) -> list[ContentBrief]:
        """Run the research agent to produce content briefs."""
        return super().run(streams=streams, activity=activity)
