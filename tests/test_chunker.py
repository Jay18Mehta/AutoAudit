"""Tests for :mod:`compliance_guard.rag.chunking`."""

from pathlib import Path

from compliance_guard.rag.chunking import CodeChunker


def test_chunker_splits_long_file(tmp_path: Path) -> None:
    lines = [f"line {i}" for i in range(400)]
    p = tmp_path / "f.py"
    p.write_text("\n".join(lines), encoding="utf-8")
    c = CodeChunker(max_tokens=80, overlap_lines=2)
    chunks = c.chunk_file(p, "f.py")
    assert len(chunks) >= 2
    assert chunks[0].start_line == 1
    assert all(ch.token_estimate > 0 for ch in chunks)
