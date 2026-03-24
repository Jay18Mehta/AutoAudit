"""Aggregate per-file results into roll-up statistics."""

from __future__ import annotations

from compliance_guard.compliance.models import FileComplianceResult, RiskSummary


def compute_risk_summary(results: list[FileComplianceResult]) -> RiskSummary:
    """Compute severity/standard counts and file-level metrics."""
    by_severity: dict[str, int] = {}
    by_standard: dict[str, int] = {}
    total = 0
    files_with_issues = 0
    analyzed = 0
    for fr in results:
        if fr.error:
            continue
        analyzed += 1
        if fr.violations:
            files_with_issues += 1
        for v in fr.violations:
            total += 1
            by_severity[v.severity.value] = by_severity.get(v.severity.value, 0) + 1
            by_standard[v.standard] = by_standard.get(v.standard, 0) + 1
    return RiskSummary(
        total_violations=total,
        by_severity=by_severity,
        by_standard=by_standard,
        files_analyzed=analyzed,
        files_with_issues=files_with_issues,
    )
