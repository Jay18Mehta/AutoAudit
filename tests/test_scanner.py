"""Tests for :mod:`compliance_guard.scanner.file_scanner`."""

from pathlib import Path

from compliance_guard.indexing.models import FileCategory
from compliance_guard.scanner.file_scanner import FileScanner


def test_scanner_finds_python_and_ignores_node_modules(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("console.log(1)", encoding="utf-8")

    scanner = FileScanner()
    entries = scanner.scan(tmp_path)
    rels = {e.relative_path for e in entries}
    assert "src/app.py" in rels
    assert not any("node_modules" in r for r in rels)


def test_env_file_excluded(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("SECRET=x\n", encoding="utf-8")
    scanner = FileScanner()
    entries = scanner.scan(tmp_path)
    assert any(
        e.relative_path == ".env" and e.category == FileCategory.EXCLUDED
        for e in entries
    )
