"""Abstract LLM client for swappable backends."""

from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMConfig:
    """Runtime configuration for an LLM provider."""

    model: str
    temperature: float = 0.2
    max_output_tokens: int = 8192


class LLMClient(abc.ABC):
    """Protocol-like abstract base for text generation."""

    @abc.abstractmethod
    async def generate_json(self, system_instruction: str, user_prompt: str) -> str:
        """Return a JSON string from the model (validated by caller)."""

    @abc.abstractmethod
    async def generate_text(self, system_instruction: str, user_prompt: str) -> str:
        """Return free-form text (used for RAG-style Q&A)."""

    @property
    @abc.abstractmethod
    def config(self) -> LLMConfig:
        """Active configuration."""
