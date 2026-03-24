"""Split source files into overlapping chunks for embeddings (future RAG Q&A)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from compliance_guard.security.redactor import estimate_tokens


@dataclass(frozen=True)
class CodeChunk:
    """A slice of a source file with stable addressing."""

    file: str
    start_line: int
    end_line: int
    content: str
    token_estimate: int


class CodeChunker:
    """Greedy tokenizer-budget chunker with line overlap."""

    def __init__(
        self,
        max_tokens: int = 1500,
        overlap_lines: int = 10,
    ) -> None:
        self._max_tokens = max_tokens
        self._overlap = max(0, overlap_lines)

    def chunk_file(self, path: Path, relative_path: str) -> list[CodeChunk]:
        """Chunk a UTF-8 text file into :class:`CodeChunk` records."""
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        chunks: list[CodeChunk] = []
        i = 0
        n = len(lines)
        while i < n:
            piece: list[str] = []
            start = i
            est = 0
            while i < n:
                line = lines[i]
                cand = "\n".join(piece + [line])
                new_est = estimate_tokens(cand)
                if piece and new_est > self._max_tokens:
                    break
                piece.append(line)
                est = new_est
                i += 1
            if not piece:
                break
            body = "\n".join(piece)
            end_line = start + len(piece)
            chunks.append(
                CodeChunk(
                    file=relative_path,
                    start_line=start + 1,
                    end_line=end_line,
                    content=body,
                    token_estimate=est,
                )
            )
            if i >= n:
                break
            i = max(start + max(1, len(piece) - self._overlap), start + 1)
        return chunks
