"""Google Gemini implementation of :class:`LLMClient`."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import google.generativeai as genai

from compliance_guard.llm.base import LLMClient, LLMConfig
from compliance_guard.llm.prompts import CompliancePromptBuilder

logger = logging.getLogger(__name__)


class GeminiClient(LLMClient):
    """Async-friendly wrapper around ``google.generativeai`` (thread offload)."""

    def __init__(self, api_key: str, config: LLMConfig) -> None:
        self._config = config
        genai.configure(api_key=api_key)

    @property
    def config(self) -> LLMConfig:
        return self._config

    async def generate_json(self, system_instruction: str, user_prompt: str) -> str:
        """Generate JSON text using Gemini structured output when supported."""

        def _call() -> str:
            generation_config: dict[str, Any] = {
                "temperature": self._config.temperature,
                "max_output_tokens": self._config.max_output_tokens,
                "response_mime_type": "application/json",
            }
            model = genai.GenerativeModel(
                model_name=self._config.model,
                system_instruction=system_instruction
                or CompliancePromptBuilder.SYSTEM_INSTRUCTION,
            )
            resp = model.generate_content(
                user_prompt,
                generation_config=generation_config,
            )
            text = _extract_text(resp)
            if not text.strip():
                raise RuntimeError("Empty response from Gemini")
            return text

        return await asyncio.to_thread(_call)

    async def generate_text(self, system_instruction: str, user_prompt: str) -> str:
        """Generate plain text (no JSON mode)."""

        def _call() -> str:
            generation_config: dict[str, Any] = {
                "temperature": self._config.temperature,
                "max_output_tokens": self._config.max_output_tokens,
            }
            model = genai.GenerativeModel(
                model_name=self._config.model,
                system_instruction=system_instruction
                or CompliancePromptBuilder.SYSTEM_INSTRUCTION,
            )
            resp = model.generate_content(
                user_prompt,
                generation_config=generation_config,
            )
            text = _extract_text(resp)
            if not text.strip():
                raise RuntimeError("Empty response from Gemini")
            return text

        return await asyncio.to_thread(_call)


def _extract_text(resp: Any) -> str:
    """Normalize Gemini response text across SDK versions."""
    try:
        return resp.text or ""
    except Exception:
        parts: list[str] = []
        for cand in getattr(resp, "candidates", []) or []:
            content = getattr(cand, "content", None)
            for p in getattr(content, "parts", []) or []:
                t = getattr(p, "text", None)
                if t:
                    parts.append(t)
        return "".join(parts)
