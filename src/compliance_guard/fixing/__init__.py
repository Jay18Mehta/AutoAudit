"""Apply compliance remediations to source files (LLM-assisted full-file rewrite)."""

from compliance_guard.fixing.applier import (
    FileFixResult,
    FixRunSummary,
    apply_fixes_from_report,
    violations_at_or_above,
)

__all__ = [
    "FileFixResult",
    "FixRunSummary",
    "apply_fixes_from_report",
    "violations_at_or_above",
]
