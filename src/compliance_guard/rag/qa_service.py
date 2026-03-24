"""Lightweight RAG-style Q&A over a repository (keyword retrieval + LLM)."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from compliance_guard.indexing.index_builder import IndexBuilder
from compliance_guard.indexing.models import RepositoryIndex
from compliance_guard.llm.base import LLMClient
from compliance_guard.rag.chunking import CodeChunk, CodeChunker
from compliance_guard.rag.context_builder import ContextWindowBuilder
from compliance_guard.scanner.file_scanner import FileScanner

logger = logging.getLogger(__name__)


def _tokenize(s: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9_]+", s.lower()))


def _score(question: str, chunk: CodeChunk) -> float:
    q = _tokenize(question)
    c = _tokenize(chunk.content + " " + chunk.file)
    if not q:
        return 0.0
    return len(q & c) / max(1, len(q))


class CodebaseQAService:
    """Retrieve top chunks by keyword overlap, then answer with the LLM."""

    def __init__(
        self,
        llm: LLMClient,
        chunker: CodeChunker | None = None,
        context_builder: ContextWindowBuilder | None = None,
    ) -> None:
        self._llm = llm
        self._chunker = chunker or CodeChunker()
        self._ctx = context_builder or ContextWindowBuilder()

    async def answer(
        self,
        root: Path,
        question: str,
        *,
        redact: bool = True,
        top_k: int = 12,
    ) -> str:
        """Scan *root*, rank chunks, and return an answer string."""
        scanner = FileScanner()
        entries = scanner.scan(root)
        index = IndexBuilder().build(root, entries)
        chunks = self._all_chunks(index)
        ranked = sorted(chunks, key=lambda ch: _score(question, ch), reverse=True)[
            :top_k
        ]
        built = self._ctx.build(question, ranked, redact=redact)
        user = (
            f"Question:\n{question}\n\n"
            "Code excerpts:\n"
            + "\n\n".join(built.blocks)
        )
        sys = (
            built.system_preamble
            + " Cite file paths and line ranges when referencing code."
        )
        return await self._llm.generate_text(sys, user)

    def _all_chunks(self, index: RepositoryIndex) -> list[CodeChunk]:
        out: list[CodeChunk] = []
        for entry in index.analysis_targets():
            try:
                out.extend(
                    self._chunker.chunk_file(entry.path, entry.relative_path)
                )
            except OSError as exc:
                logger.warning("Chunk skip %s: %s", entry.path, exc)
        return out
