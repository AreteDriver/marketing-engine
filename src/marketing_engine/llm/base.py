"""Abstract base class and mock implementation for LLM clients."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Abstract base for LLM provider clients."""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        """Generate a text response from the LLM.

        Args:
            system_prompt: System-level instruction for the model.
            user_prompt: User-level prompt to respond to.
            temperature: Sampling temperature (0.0-1.0).

        Returns:
            The generated text response.
        """
        ...


class MockLLMClient(LLMClient):
    """Mock LLM client that cycles through predefined responses.

    Useful for testing and dry-run mode.
    """

    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self._index = 0
        self.calls: list[tuple[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        """Return the next predefined response and record the call."""
        self.calls.append((system_prompt, user_prompt))
        response = self._responses[self._index % len(self._responses)]
        self._index += 1
        return response
