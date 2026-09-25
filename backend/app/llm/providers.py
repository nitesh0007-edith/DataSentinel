"""Concrete LLM providers over plain HTTPS (no vendor SDK dependency)."""

from __future__ import annotations

import httpx

from app.core.config import Settings
from app.core.logging import get_logger
from app.llm.base import LLMError, LLMMessage, LLMProvider

log = get_logger("llm")

DEFAULT_MODELS = {
    "anthropic": "claude-opus-5-5",
    "openai": "gpt-4.1",
}


class AnthropicProvider(LLMProvider):
    name = "anthropic"
    url = "https://api.anthropic.com/v1/messages"

    def __init__(self, model: str, api_key: str, timeout: int) -> None:
        super().__init__(model)
        self._api_key = api_key
        self._timeout = timeout

    def generate(self, system: str, messages: list[LLMMessage], max_tokens: int = 2000) -> str:
        try:
            resp = httpx.post(
                self.url,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": [m.model_dump() for m in messages],
                },
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise LLMError(f"Anthropic request failed: {exc}") from exc
        if resp.status_code != 200:
            raise LLMError(f"Anthropic API error {resp.status_code}: {resp.text[:300]}")
        blocks = resp.json().get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, model: str, api_key: str, base_url: str, timeout: int) -> None:
        super().__init__(model)
        self._api_key = api_key
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._timeout = timeout

    def generate(self, system: str, messages: list[LLMMessage], max_tokens: int = 2000) -> str:
        try:
            resp = httpx.post(
                self._url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "response_format": {"type": "json_object"},
                    "messages": [{"role": "system", "content": system}]
                    + [m.model_dump() for m in messages],
                },
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise LLMError(f"OpenAI request failed: {exc}") from exc
        if resp.status_code != 200:
            raise LLMError(f"OpenAI API error {resp.status_code}: {resp.text[:300]}")
        return resp.json()["choices"][0]["message"]["content"] or ""


def get_llm_provider(settings: Settings) -> LLMProvider | None:
    """Return the configured provider, or None for the deterministic heuristic engine."""
    name = (settings.llm_provider or "heuristic").strip().lower()
    if name in {"", "none", "heuristic", "mock", "offline"}:
        return None
    if name == "anthropic":
        if not settings.anthropic_api_key:
            log.warning("LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set; using heuristic RCA")
            return None
        return AnthropicProvider(
            settings.llm_model or DEFAULT_MODELS["anthropic"],
            settings.anthropic_api_key,
            settings.llm_timeout_seconds,
        )
    if name == "openai":
        if not settings.openai_api_key:
            log.warning("LLM_PROVIDER=openai but OPENAI_API_KEY is not set; using heuristic RCA")
            return None
        return OpenAIProvider(
            settings.llm_model or DEFAULT_MODELS["openai"],
            settings.openai_api_key,
            settings.openai_base_url,
            settings.llm_timeout_seconds,
        )
    log.warning("Unknown LLM_PROVIDER '%s'; using heuristic RCA", name)
    return None
