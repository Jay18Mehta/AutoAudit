"""Recursive repository scanner producing :class:`FileIndexEntry` records."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from compliance_guard.indexing.models import FileCategory, FileIndexEntry
from compliance_guard.scanner.exclusions import (
    DOCKERFILE_NAMES,
    MAX_FILE_BYTES,
    SUPPORTED_EXTENSIONS,
    extension_for_language,
    is_probably_binary,
    should_skip_path,
)
from compliance_guard.security.redactor import estimate_tokens

logger = logging.getLogger(__name__)


class FileScanner:
    """Walk a directory tree and classify files for analysis."""

    def __init__(
        self,
        max_bytes: int = MAX_FILE_BYTES,
        additional_ignore_dirs: frozenset[str] | None = None,
    ) -> None:
        self._max_bytes = max_bytes
        self._extra_dirs = additional_ignore_dirs or frozenset()

    def scan(self, root: Path) -> list[FileIndexEntry]:
        """Recursively scan *root* and return index entries."""
        root = root.resolve()
        if not root.is_dir():
            raise NotADirectoryError(f"Not a directory: {root}")

        results: list[FileIndexEntry] = []

        for dirpath, dirnames, filenames in os.walk(
            root, topdown=True, followlinks=False
        ):
            dir_path = Path(dirpath)
            # Prune ignored directories in-place for efficiency
            extra_lower = {x.lower() for x in self._extra_dirs}
            for d in list(dirnames):
                child = dir_path / d
                skip, _ = should_skip_path(child, root)
                if skip or d.lower() in extra_lower:
                    dirnames.remove(d)

            for name in filenames:
                path = dir_path / name
                rel = path.relative_to(root)
                skip, reason = should_skip_path(path, root)
                if skip:
                    results.append(
                        FileIndexEntry(
                            path=path,
                            relative_path=str(rel).replace("\\", "/"),
                            category=FileCategory.EXCLUDED,
                            skip_reason=reason,
                        )
                    )
                    continue

                try:
                    st = path.stat()
                except OSError as exc:
                    logger.debug("stat failed for %s: %s", path, exc)
                    continue

                size = st.st_size
                if size > self._max_bytes:
                    results.append(
                        FileIndexEntry(
                            path=path,
                            relative_path=str(rel).replace("\\", "/"),
                            size_bytes=size,
                            category=FileCategory.OVERSIZED,
                            skip_reason=f"file>{self._max_bytes}_bytes",
                        )
                    )
                    continue

                name_l = name.lower()
                ext = path.suffix.lower()
                is_docker = name_l in DOCKERFILE_NAMES
                if ext not in SUPPORTED_EXTENSIONS and not is_docker:
                    results.append(
                        FileIndexEntry(
                            path=path,
                            relative_path=str(rel).replace("\\", "/"),
                            size_bytes=size,
                            category=FileCategory.EXCLUDED,
                            skip_reason="unsupported_extension",
                        )
                    )
                    continue

                if is_probably_binary(path):
                    results.append(
                        FileIndexEntry(
                            path=path,
                            relative_path=str(rel).replace("\\", "/"),
                            size_bytes=size,
                            category=FileCategory.BINARY,
                            skip_reason="binary_heuristic",
                        )
                    )
                    continue

                lang = extension_for_language(path)
                line_count: int | None = None
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                    line_count = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
                except OSError as exc:
                    logger.warning("Could not read %s: %s", path, exc)
                    results.append(
                        FileIndexEntry(
                            path=path,
                            relative_path=str(rel).replace("\\", "/"),
                            size_bytes=size,
                            category=FileCategory.SKIPPED,
                            skip_reason=f"read_error:{exc}",
                        )
                    )
                    continue

                token_est = estimate_tokens(text)
                cat = (
                    FileCategory.CONFIG
                    if ext in {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf"}
                    else FileCategory.SOURCE
                )

                results.append(
                    FileIndexEntry(
                        path=path,
                        relative_path=str(rel).replace("\\", "/"),
                        size_bytes=size,
                        language=lang,
                        category=cat,
                        line_count=line_count,
                        token_estimate=token_est,
                    )
                )

        results.sort(key=lambda e: e.relative_path)
        return results
