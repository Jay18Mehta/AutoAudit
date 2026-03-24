"""Path patterns, size limits, and binary heuristics."""

from __future__ import annotations

import os
from pathlib import Path

# 5 MB cap per requirements
MAX_FILE_BYTES = 5 * 1024 * 1024

DEFAULT_IGNORE_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        "dist",
        "build",
        "target",
        ".gradle",
        ".idea",
        ".vscode",
        "coverage",
        "htmlcov",
    }
)

# Never read these as text for compliance (secrets / keys)
NEVER_SCAN_BASENAMES: frozenset[str] = frozenset(
    {
        ".env",
        ".env.local",
        ".env.production",
        ".env.development",
    }
)

NEVER_SCAN_SUFFIXES: frozenset[str] = frozenset(
    {
        ".pem",
        ".key",
        ".p12",
        ".pfx",
        ".jks",
        ".keystore",
        ".crt",
        ".cer",
    }
)

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".pyi",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".ts",
        ".tsx",
        ".java",
        ".go",
        ".cs",
        ".fs",
        ".vb",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".config",
        ".properties",
        ".xml",
        ".gradle",
        ".md",
        ".sql",
        ".sh",
        ".ps1",
        ".bat",
        ".dockerfile",
    }
)

DOCKERFILE_NAMES: frozenset[str] = frozenset({"dockerfile", "containerfile"})


def is_probably_binary(path: Path, sample_bytes: int = 8192) -> bool:
    """Heuristic: treat NUL bytes or high ratio of non-text as binary."""
    try:
        with path.open("rb") as f:
            chunk = f.read(sample_bytes)
    except OSError:
        return True
    if not chunk:
        return False
    if b"\x00" in chunk:
        return True
    text_chars = sum(1 for b in chunk if 32 <= b <= 126 or b in (9, 10, 13))
    ratio = text_chars / len(chunk)
    return ratio < 0.70


def should_skip_path(path: Path, root: Path) -> tuple[bool, str | None]:
    """Return (skip, reason) for a path segment or file."""
    parts_lower = [p.lower() for p in path.relative_to(root).parts]
    for p in parts_lower:
        if p in NEVER_SCAN_BASENAMES:
            return True, "sensitive_env_or_secret_filename"
        if p in DEFAULT_IGNORE_DIR_NAMES:
            return True, f"ignored_directory:{p}"
    name_lower = path.name.lower()
    if name_lower in NEVER_SCAN_BASENAMES:
        return True, "sensitive_env_file"
    suf = path.suffix.lower()
    if suf in NEVER_SCAN_SUFFIXES:
        return True, "certificate_or_key_extension"
    return False, None


def extension_for_language(path: Path) -> str | None:
    """Map extension to a coarse language label."""
    name = path.name.lower()
    if name in DOCKERFILE_NAMES:
        return "docker"
    ext = path.suffix.lower()
    mapping = {
        ".py": "python",
        ".pyi": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".go": "go",
        ".cs": "csharp",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".xml": "xml",
        ".sql": "sql",
    }
    return mapping.get(ext)
