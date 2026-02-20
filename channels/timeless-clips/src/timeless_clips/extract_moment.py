"""Moment extraction using Ollama LLM."""

from __future__ import annotations

import json
import logging

import httpx

from timeless_clips.models import ArchiveItem, ShortScript, TextOverlay

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a viral content curator specializing in historical media.
Given archival content metadata, identify the single most compelling 30-60 second moment
and write a script for a YouTube Short / TikTok.

Respond ONLY with valid JSON matching this schema:
{
    "hook": "Opening line that stops the scroll (< 10 words)",
    "start_time": 45.0,
    "end_time": 90.0,
    "narration": "Original commentary providing context (2-3 sentences)",
    "text_overlays": [
        {"time": 0.0, "text": "1951", "position": "top-right"},
        {"time": 2.0, "text": "Duck and Cover", "position": "bottom"}
    ],
    "closing": "Call to action or cliffhanger",
    "category": "educational",
    "mood": "nostalgic",
    "tags": ["cold war", "1950s"]
}"""


class MomentExtractor:
    """Use Ollama to identify compelling moments and generate scripts."""

    def __init__(self, config: dict, client: httpx.Client | None = None) -> None:
        llm_config = config.get("llm", {})
        self._host = llm_config.get("host", "http://localhost:11434")
        self._model = llm_config.get("model", "llama3.2")
        self._client = client or httpx.Client(timeout=120)

    def extract(self, item: ArchiveItem) -> ShortScript:
        """Generate a ShortScript from an archive item."""
        prompt = self._build_prompt(item)
        raw = self._call_llm(prompt)
        data = self._parse_response(raw)
        return ShortScript(
            item_id=item.identifier,
            hook=data.get("hook", ""),
            start_time=float(data.get("start_time", 0)),
            end_time=float(data.get("end_time", 60)),
            narration=data.get("narration", ""),
            text_overlays=[
                TextOverlay(
                    time=o.get("time", 0),
                    text=o.get("text", ""),
                    position=o.get("position", "bottom"),
                )
                for o in data.get("text_overlays", [])
            ],
            closing=data.get("closing", ""),
            category=data.get("category", item.category),
            mood=data.get("mood", "nostalgic"),
            tags=data.get("tags", []),
        )

    def _build_prompt(self, item: ArchiveItem) -> str:
        parts = [
            f"Title: {item.title}",
            f"Year: {item.year or 'Unknown'}",
            f"Collection: {item.collection}",
            f"Category: {item.category}",
        ]
        if item.description:
            # Truncate long descriptions
            desc = item.description[:500]
            parts.append(f"Description: {desc}")
        if item.duration:
            parts.append(f"Duration: {item.duration:.0f} seconds")
        if item.tags:
            parts.append(f"Tags: {', '.join(item.tags)}")
        return "\n".join(parts)

    def _call_llm(self, prompt: str) -> str:
        """Call Ollama generate endpoint."""
        resp = self._client.post(
            f"{self._host}/api/generate",
            json={
                "model": self._model,
                "system": _SYSTEM_PROMPT,
                "prompt": prompt,
                "stream": False,
            },
        )
        resp.raise_for_status()
        return resp.json().get("response", "")

    def _parse_response(self, raw: str) -> dict:
        """Parse JSON from LLM response, stripping fences if needed."""
        text = raw.strip()
        # Strip markdown code fences
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            text = "\n".join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response, using defaults")
            return {}
