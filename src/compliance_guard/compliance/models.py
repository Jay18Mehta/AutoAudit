"""Pydantic models for violations and scan aggregates."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Severity(str, Enum):
    """Normalized severity for reporting and sorting."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


def severity_rank(s: Severity) -> int:
    """Lower number = higher risk."""
    order = [
        Severity.CRITICAL,
        Severity.HIGH,
        Severity.MEDIUM,
        Severity.LOW,
        Severity.INFO,
    ]
    return order.index(s) if s in order else len(order)


class Violation(BaseModel):
    """Single compliance finding for a file."""

    standard: str
    severity: Severity
    issue: str
    explanation: str
    fix: str
    fixed_code: str = ""

    @field_validator("severity", mode="before")
    @classmethod
    def normalize_severity(cls, v: Any) -> Severity:
        if isinstance(v, Severity):
            return v
        if isinstance(v, str):
            key = v.strip().lower()
            for s in Severity:
                if s.value == key:
                    return s
        return Severity.INFO


class FileComplianceResult(BaseModel):
    """LLM output for one file."""

    file: str
    violations: list[Violation] = Field(default_factory=list)
    secure_patterns: list[str] = Field(default_factory=list)
    raw_response: str | None = None
    error: str | None = None


class RiskSummary(BaseModel):
    """Roll-up counts for executive summary."""

    total_violations: int = 0
    by_severity: dict[str, int] = Field(default_factory=dict)
    by_standard: dict[str, int] = Field(default_factory=dict)
    files_analyzed: int = 0
    files_with_issues: int = 0


class RepositoryComplianceReport(BaseModel):
    """Full scan result for a repository."""

    root: Path
    generated_at_utc: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    model: str
    results: list[FileComplianceResult] = Field(default_factory=list)
    risk_summary: RiskSummary = Field(default_factory=RiskSummary)
    index_snapshot: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}
