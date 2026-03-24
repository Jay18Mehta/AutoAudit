"""Filesystem scanning for source and config files."""

from compliance_guard.scanner.file_scanner import FileScanner
from compliance_guard.scanner.exclusions import (
    DEFAULT_IGNORE_DIR_NAMES,
    MAX_FILE_BYTES,
    is_probably_binary,
)

__all__ = [
    "FileScanner",
    "DEFAULT_IGNORE_DIR_NAMES",
    "MAX_FILE_BYTES",
    "is_probably_binary",
]
