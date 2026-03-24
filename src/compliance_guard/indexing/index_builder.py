"""Build a :class:`RepositoryIndex` from scanner output."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from compliance_guard.indexing.models import FileIndexEntry, RepositoryIndex

logger = logging.getLogger(__name__)


class IndexBuilder:
    """Assembles repository indexes and optional content checksums."""

    def __init__(self, compute_hashes: bool = False) -> None:
        self._compute_hashes = compute_hashes

    def build(
        self,
        root: Path,
        entries: list[FileIndexEntry],
    ) -> RepositoryIndex:
        """Create a :class:`RepositoryIndex`, optionally hashing file contents."""
        if self._compute_hashes:
            for entry in entries:
                if entry.category.value != "source":
                    continue
                try:
                    data = entry.path.read_bytes()
                    entry.sha256 = hashlib.sha256(data).hexdigest()
                except OSError as exc:
                    logger.warning("Could not hash %s: %s", entry.path, exc)
        return RepositoryIndex(root=root.resolve(), entries=entries)
