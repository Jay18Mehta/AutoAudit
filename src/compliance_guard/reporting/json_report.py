"""Serialize compliance reports to JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from compliance_guard.compliance.models import RepositoryComplianceReport


def write_json_report(report: RepositoryComplianceReport, path: Path) -> None:
    """Write *report* as indented UTF-8 JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = report.model_dump(mode="json")
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def report_to_dict(report: RepositoryComplianceReport) -> dict[str, Any]:
    """Return a JSON-serializable dict."""
    return report.model_dump(mode="json")


def load_json_report(path: Path) -> RepositoryComplianceReport:
    """Load a report previously written by :func:`write_json_report`."""
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    return RepositoryComplianceReport.model_validate(data)
