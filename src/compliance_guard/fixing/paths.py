"""Safe path resolution for applying edits under a repository root."""

from __future__ import annotations

from pathlib import Path


def resolve_under_root(root: Path, relative: str) -> Path | None:
    """Return *root*/*relative* if it resolves strictly under *root*; else None."""
    root_res = root.resolve()
    rel_str = relative.strip().replace("\\", "/")
    if rel_str.startswith("./"):
        rel_str = rel_str[2:]
    if not rel_str or rel_str == ".":
        return None
    rel_path = Path(rel_str)
    if rel_path.is_absolute() or ".." in rel_path.parts:
        return None
    candidate = (root_res / rel_path).resolve()
    try:
        candidate.relative_to(root_res)
    except ValueError:
        return None
    return candidate
