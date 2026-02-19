"""Draft agent for generating platform-ready post content."""

from __future__ import annotations

import json
from typing import Any

from marketing_engine.agents.base import BaseAgent
from marketing_engine.models import ContentBrief

_STREAM_TONES = {
    "project_marketing": (
        "Professional but approachable. Show technical depth without jargon overload."
    ),
    "benchgoblins": "Casual and fun. Fantasy sports energy. Hot takes welcome.",
    "eve_content": "In-universe immersion mixed with community engagement. Speak to capsuleers.",
    "linux_tools": "Practical and direct. Show, don't tell. Demo-oriented.",
    "technical_ai": "Thought leadership. Deep technical insight. Challenge conventional thinking.",
}


class DraftAgent(BaseAgent):
    """Generates post drafts from content briefs using brand voice rules."""

    def __init__(self, llm: Any, config: dict) -> None:
        super().__init__(llm, config)
        self._brand_voice = config.get("brand_voice", {})

    @property
    def system_prompt(self) -> str:
        avoid_list = self._brand_voice.get(
            "avoid",
            [
                "excited to announce",
                "game-changer",
                "leveraging AI",
                "revolutionary",
                "synergy",
            ],
        )
        principles = self._brand_voice.get(
            "principles",
            [
                "Be direct and specific",
                "Show results, not promises",
                "Include a clear call to action",
                "Write like a human, not a press release",
            ],
        )

        avoid_str = ", ".join(f'"{a}"' for a in avoid_list)
        principles_str = "\n".join(f"- {p}" for p in principles)

        return (
            "You are a social media copywriter for a developer's project portfolio.\n"
            "\n"
            "Brand voice principles:\n"
            f"{principles_str}\n"
            "\n"
            f"NEVER use these phrases: {avoid_str}\n"
            "\n"
            "Given a content brief, write a compelling post. "
            "Include a clear CTA. "
            'Output ONLY JSON: {{"content": "...", "cta_url": "...", "hashtags": [...]}}'
        )

    def build_user_prompt(self, brief: ContentBrief | None = None, **kwargs: Any) -> str:
        """Format the content brief into a prompt."""
        if brief is None:
            brief = kwargs.get("brief")
        if brief is None:
            return "Write a general developer marketing post."

        stream_tone = _STREAM_TONES.get(brief.stream.value, "Professional and engaging.")
        links_str = ", ".join(brief.relevant_links) if brief.relevant_links else "none"
        platforms_str = ", ".join(p.value for p in brief.platforms)

        return (
            f"Content Brief:\n"
            f"Topic: {brief.topic}\n"
            f"Angle: {brief.angle}\n"
            f"Target Audience: {brief.target_audience}\n"
            f"Relevant Links: {links_str}\n"
            f"Stream: {brief.stream.value}\n"
            f"Target Platforms: {platforms_str}\n"
            f"\n"
            f"Tone guidance for {brief.stream.value}: {stream_tone}\n"
            f"\n"
            f"Write the post now."
        )

    def parse_response(self, raw: str) -> dict:
        """Parse JSON response into a dict with content, cta_url, hashtags."""
        data = json.loads(raw)
        return {
            "content": data.get("content", ""),
            "cta_url": data.get("cta_url", ""),
            "hashtags": data.get("hashtags", []),
        }

    def run(self, brief: ContentBrief | None = None, **kwargs: Any) -> dict:
        """Generate a draft post from a content brief."""
        return super().run(brief=brief, **kwargs)
