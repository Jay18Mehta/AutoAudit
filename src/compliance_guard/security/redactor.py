"""Mask sensitive substrings and estimate token counts (tiktoken-style)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    import tiktoken
except ImportError:  # pragma: no cover
    tiktoken = None


@dataclass(frozen=True)
class RedactionStats:
    """Counts of redaction substitutions applied."""

    emails: int = 0
    tokens_like: int = 0
    passwords: int = 0


class ContentRedactor:
    """Apply regex-based masking for content sent to external LLMs."""

    _EMAIL = re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    )
    _TOKEN_LIKE = re.compile(r"\b(?:Bearer\s+)?[A-Za-z0-9\-_]{32,}\b")
    _PASSWORD_ASSIGN = re.compile(
        r"(?i)(password|passwd|pwd|secret|api[_-]?key|token)\s*[:=]\s*([^\s\n\"']+)",
    )

    def redact(self, text: str, enabled: bool = True) -> tuple[str, RedactionStats]:
        """Return redacted text and substitution statistics."""
        if not enabled:
            return text, RedactionStats()

        out, em = self._EMAIL.subn("[REDACTED_EMAIL]", text)
        out, tk = self._TOKEN_LIKE.subn("[REDACTED_TOKEN]", out)

        def sub_pwd(m: re.Match[str]) -> str:
            key = m.group(1)
            return f"{key}=[REDACTED_SECRET]"

        out, pw = self._PASSWORD_ASSIGN.subn(sub_pwd, out)
        stats = RedactionStats(emails=em, tokens_like=tk, passwords=pw)
        return out, stats


def estimate_tokens(text: str, model_hint: str = "gpt-4o") -> int:
    """Best-effort token count using tiktoken; fallback to chars/4."""
    if tiktoken is None:
        return max(1, len(text) // 4)
    try:
        enc = tiktoken.encoding_for_model(model_hint)
    except Exception:
        try:
            enc = tiktoken.get_encoding("cl100k_base")
        except Exception as exc:  # pragma: no cover
            logger.debug("tiktoken fallback: %s", exc)
            return max(1, len(text) // 4)
    return len(enc.encode(text))
