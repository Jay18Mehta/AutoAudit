"""Assemble LLM context windows from retrieved chunks (future Q&A)."""

from __future__ import annotations

from dataclasses import dataclass

from compliance_guard.rag.chunking import CodeChunk
from compliance_guard.security.redactor import ContentRedactor, estimate_tokens


@dataclass(frozen=True)
class BuiltContext:
    """Packaged prompt context for an LLM."""

    system_preamble: str
    blocks: list[str]
    token_estimate: int


class ContextWindowBuilder:
    """Greedy pack chunks until a token budget is reached."""

    def __init__(
        self,
        max_tokens: int = 6000,
        redactor: ContentRedactor | None = None,
    ) -> None:
        self._max_tokens = max_tokens
        self._redactor = redactor or ContentRedactor()

    def build(
        self,
        question: str,
        chunks: list[CodeChunk],
        redact: bool = True,
    ) -> BuiltContext:
        """Combine *chunks* into a single context under the token budget."""
        blocks: list[str] = []
        total = estimate_tokens(question)
        for ch in chunks:
            header = f"// {ch.file}:{ch.start_line}-{ch.end_line}\n"
            body = ch.content
            if redact:
                body, _ = self._redactor.redact(body, enabled=True)
            block = header + body
            t = estimate_tokens(block)
            if total + t > self._max_tokens:
                break
            blocks.append(block)
            total += t
        preamble = (
            "You answer questions about a codebase using only the excerpts below. "
            "If unknown, say you do not have enough context.\n"
        )
        return BuiltContext(
            system_preamble=preamble,
            blocks=blocks,
            token_estimate=total + estimate_tokens(preamble),
        )
