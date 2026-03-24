"""Markdown report with risk summary and fix recommendations."""

from __future__ import annotations

from pathlib import Path

from compliance_guard.compliance.models import (
    FileComplianceResult,
    RepositoryComplianceReport,
    Severity,
    Violation,
    severity_rank,
)


def render_markdown_report(report: RepositoryComplianceReport) -> str:
    """Build a Markdown document from a repository report."""
    lines: list[str] = []
    lines.append("# Compliance scan report\n")
    lines.append(f"- Root: `{report.root}`")
    lines.append(f"- Model: `{report.model}`")
    lines.append(f"- Generated (UTC): `{report.generated_at_utc.isoformat()}`\n")

    rs = report.risk_summary
    lines.append("## Risk summary\n")
    lines.append(f"- Files analyzed: **{rs.files_analyzed}**")
    lines.append(f"- Files with findings: **{rs.files_with_issues}**")
    lines.append(f"- Total violations: **{rs.total_violations}**\n")
    lines.append("### By severity\n")
    for k, v in sorted(rs.by_severity.items(), key=lambda kv: _sev_key(kv[0])):
        lines.append(f"- **{k}**: {v}")
    lines.append("\n### By standard\n")
    for k, v in sorted(rs.by_standard.items()):
        lines.append(f"- **{k}**: {v}")

    lines.append("\n## Fix recommendations (prioritized)\n")
    all_v: list[tuple[Violation, str]] = []
    for fr in report.results:
        for v in fr.violations:
            all_v.append((v, fr.file))
    all_v.sort(key=lambda t: (severity_rank(t[0].severity), t[0].standard))
    for v, fpath in all_v[:50]:
        lines.append(
            f"- **[{v.severity.value.upper()}] {v.standard}** — `{fpath}`: {v.issue}\n"
            f"  - Fix: {v.fix}\n"
        )
    if len(all_v) > 50:
        lines.append(f"\n_({len(all_v) - 50} additional items omitted)_\n")

    lines.append("\n## Per-file results\n")
    for fr in sorted(report.results, key=lambda r: r.file):
        lines.extend(_file_section(fr))

    return "\n".join(lines) + "\n"


def _sev_key(name: str) -> int:
    try:
        return severity_rank(Severity(name.lower()))
    except Exception:
        return 99


def _file_section(fr: FileComplianceResult) -> list[str]:
    out: list[str] = [f"### `{fr.file}`\n"]
    if fr.error:
        out.append(f"_Error: {fr.error}_\n")
        return out
    if fr.secure_patterns:
        out.append("**Positive patterns**")
        for p in fr.secure_patterns:
            out.append(f"- {p}")
        out.append("")
    if not fr.violations:
        out.append("_No violations reported._\n")
        return out
    for v in fr.violations:
        out.append(
            f"- **[{v.severity.value}] {v.standard}** — {v.issue}\n"
            f"  - Explanation: {v.explanation}\n"
            f"  - Fix: {v.fix}\n"
        )
        if v.fixed_code.strip():
            out.append("  - Suggested code:\n")
            out.append("    ```\n    " + v.fixed_code.replace("\n", "\n    ") + "\n    ```\n")
    out.append("")
    return out


def write_markdown_report(report: RepositoryComplianceReport, path: Path) -> None:
    """Write Markdown report to *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_report(report), encoding="utf-8")
