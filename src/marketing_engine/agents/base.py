"""Abstract base agent with LLM integration and JSON retry logic."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

from marketing_engine.exceptions import LLMError
from marketing_engine.llm.base import LLMClient


class BaseAgent(ABC):
    """Base class for all content generation agents.

    Provides LLM calling with automatic JSON fence stripping and
    one-shot retry on parse failures.
    """

    def __init__(self, llm: LLMClient, config: dict) -> None:
        self.llm = llm
        self.config = config

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        ...

    @abstractmethod
    def build_user_prompt(self, **kwargs: Any) -> str:
        """Build the user prompt from keyword arguments."""
        ...

    @abstractmethod
    def parse_response(self, raw: str) -> Any:
        """Parse the raw LLM response into structured data."""
        ...

    def _strip_json_fences(self, raw: str) -> str:
        """Remove markdown JSON code fences from LLM output.

        Handles ```json ... ``` and ``` ... ``` patterns.
        """
        stripped = raw.strip()
        # Remove ```json or ``` prefix
        pattern = r"^```(?:json)?\s*\n?"
        stripped = re.sub(pattern, "", stripped)
        # Remove trailing ```
        stripped = re.sub(r"\n?```\s*$", "", stripped)
        return stripped.strip()

    def run(self, **kwargs: Any) -> Any:
        """Execute the agent: build prompt, call LLM, parse response.

        On JSON parse failure, retries once with a correction prompt.

        Raises:
            LLMError: If the LLM call fails or response cannot be parsed
                after retry.
        """
        user_prompt = self.build_user_prompt(**kwargs)
        raw = self.llm.generate(self.system_prompt, user_prompt)
        cleaned = self._strip_json_fences(raw)

        try:
            return self.parse_response(cleaned)
        except json.JSONDecodeError:
            # Retry once with correction
            correction = "Your response was not valid JSON. Please output only valid JSON."
            retry_prompt = f"{user_prompt}\n\n{correction}"
            raw_retry = self.llm.generate(self.system_prompt, retry_prompt)
            cleaned_retry = self._strip_json_fences(raw_retry)
            try:
                return self.parse_response(cleaned_retry)
            except json.JSONDecodeError as exc:
                raise LLMError(
                    f"Failed to parse LLM response as JSON after retry: {cleaned_retry[:200]}"
                ) from exc
