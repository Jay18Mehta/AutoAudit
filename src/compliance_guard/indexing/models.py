"""Pydantic models for scanned file metadata and repository indexes."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class FileCategory(str, Enum):
    """High-level classification for indexed paths."""

    SOURCE = "source"
    CONFIG = "config"
    SKIPPED = "skipped"
    BINARY = "binary"
    OVERSIZED = "oversized"
    EXCLUDED = "excluded"


class FileIndexEntry(BaseModel):
    """Metadata for a single path discovered during scanning."""

    path: Path
    relative_path: str
    size_bytes: int = 0
    language: str | None = None
    category: FileCategory = FileCategory.SOURCE
    sha256: str | None = None
    line_count: int | None = None
    token_estimate: int | None = None
    skip_reason: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


class RepositoryIndex(BaseModel):
    """Full index for a repository root."""

    root: Path
    created_at_utc: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    entries: list[FileIndexEntry] = Field(default_factory=list)

    def sources(self) -> list[FileIndexEntry]:
        """Return source-code entries (non-config)."""
        return [e for e in self.entries if e.category == FileCategory.SOURCE]

    def analysis_targets(self) -> list[FileIndexEntry]:
        """Return source and config files eligible for LLM compliance analysis."""
        return [
            e
            for e in self.entries
            if e.category in (FileCategory.SOURCE, FileCategory.CONFIG)
        ]

    model_config = {"arbitrary_types_allowed": True}
