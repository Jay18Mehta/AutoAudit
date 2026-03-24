"""Rich CLI tables for scan summaries."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from compliance_guard.compliance.models import RepositoryComplianceReport


def print_cli_summary(report: RepositoryComplianceReport, console: Console | None = None) -> None:
    """Print risk summary and top violations as tables."""
    c = console or Console()
    c.print("[bold]Compliance scan summary[/bold]\n")
    rs = report.risk_summary
    t = Table(title="Risk overview")
    t.add_column("Metric", style="cyan")
    t.add_column("Value", justify="right")
    t.add_row("Files analyzed", str(rs.files_analyzed))
    t.add_row("Files with issues", str(rs.files_with_issues))
    t.add_row("Total violations", str(rs.total_violations))
    c.print(t)

    if rs.by_severity:
        ts = Table(title="Violations by severity")
        ts.add_column("Severity")
        ts.add_column("Count", justify="right")
        for sev, cnt in sorted(rs.by_severity.items()):
            ts.add_row(sev, str(cnt))
        c.print(ts)

    if rs.by_standard:
        tb = Table(title="Violations by standard")
        tb.add_column("Standard")
        tb.add_column("Count", justify="right")
        for std, cnt in sorted(rs.by_standard.items()):
            tb.add_row(std, str(cnt))
        c.print(tb)

    rows = Table(title="Sample findings (up to 15)")
    rows.add_column("File", overflow="fold")
    rows.add_column("Std")
    rows.add_column("Sev")
    rows.add_column("Issue", overflow="fold")
    n = 0
    for fr in report.results:
        for v in fr.violations:
            rows.add_row(fr.file, v.standard, v.severity.value, v.issue)
            n += 1
            if n >= 15:
                break
        if n >= 15:
            break
    c.print(rows)
