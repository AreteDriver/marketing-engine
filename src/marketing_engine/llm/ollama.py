"""Ollama LLM client implementation."""

from __future__ import annotations

import os

import httpx

from marketing_engine.exceptions import LLMError
from marketing_engine.llm.base import LLMClient


class OllamaClient(LLMClient):
    """LLM client that communicates with a local Ollama instance."""

    def __init__(self, model: str = "llama3.2", host: str | None = None) -> None:
        self.model = model
        self.host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        """Generate a response via the Ollama HTTP API.

        Args:
            system_prompt: System instruction for the model.
            user_prompt: User prompt to respond to.
            temperature: Sampling temperature.

        Returns:
            The generated text.

        Raises:
            LLMError: On network errors, timeouts, or unexpected responses.
        """
        url = f"{self.host.rstrip('/')}/api/generate"
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        try:
            resp = httpx.post(url, json=payload, timeout=120.0)
            resp.raise_for_status()
        except httpx.TimeoutException as exc:
            raise LLMError(f"Ollama request timed out ({self.host}): {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise LLMError(
                f"Ollama returned HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"Ollama request failed ({self.host}): {exc}") from exc

        try:
            data = resp.json()
        except ValueError as exc:
            raise LLMError(f"Ollama returned invalid JSON: {resp.text[:200]}") from exc

        if "response" not in data:
            raise LLMError(f"Ollama response missing 'response' key: {list(data.keys())}")
        return data["response"]
