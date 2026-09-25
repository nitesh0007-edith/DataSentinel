"""Provider-agnostic LLM interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class LLMMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class LLMError(Exception):
    pass


class LLMProvider(ABC):
    name: str = "base"

    def __init__(self, model: str) -> None:
        self.model = model

    @abstractmethod
    def generate(self, system: str, messages: list[LLMMessage], max_tokens: int = 2000) -> str:
        """Return the model's text response."""

    @property
    def label(self) -> str:
        return f"{self.name}/{self.model}"
