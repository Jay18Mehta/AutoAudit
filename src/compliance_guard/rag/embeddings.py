"""Embedding pipeline abstraction for future vector search (FAISS/Chroma)."""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Sequence

from compliance_guard.rag.chunking import CodeChunk


@dataclass(frozen=True)
class EmbeddedChunk:
    """Chunk plus dense vector (as a flat Python list for portability)."""

    chunk: CodeChunk
    vector: list[float]


class EmbeddingPipeline(abc.ABC):
    """Pluggable embeddings for RAG (Gemini embeddings or local models)."""

    @abc.abstractmethod
    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one vector per input text."""

    def embed_chunks(self, chunks: Sequence[CodeChunk]) -> list[EmbeddedChunk]:
        """Embed many chunks."""
        texts = [c.content for c in chunks]
        vecs = self.embed_texts(texts)
        return [
            EmbeddedChunk(chunk=c, vector=v) for c, v in zip(chunks, vecs, strict=True)
        ]


class PassthroughEmbeddingPipeline(EmbeddingPipeline):
    """Placeholder used until a real embedding backend is wired in."""

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Return small zero vectors (no external calls)."""
        return [[0.0] * 8 for _ in texts]
