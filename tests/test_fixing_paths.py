"""Tests for safe path resolution in the fixing module."""

from pathlib import Path

from compliance_guard.fixing.paths import resolve_under_root


def test_resolve_under_root_ok(tmp_path: Path) -> None:
    f = tmp_path / "src" / "a.py"
    f.parent.mkdir(parents=True)
    f.write_text("x", encoding="utf-8")
    got = resolve_under_root(tmp_path, "src/a.py")
    assert got == f.resolve()


def test_resolve_rejects_traversal(tmp_path: Path) -> None:
    assert resolve_under_root(tmp_path, "../outside") is None
    assert resolve_under_root(tmp_path, "a/../../etc/passwd") is None


def test_resolve_rejects_absolute(tmp_path: Path) -> None:
    assert resolve_under_root(tmp_path, "/etc/passwd") is None


def test_resolve_normalizes_dot_slash(tmp_path: Path) -> None:
    f = tmp_path / "b.py"
    f.write_text("", encoding="utf-8")
    assert resolve_under_root(tmp_path, "./b.py") == f.resolve()
