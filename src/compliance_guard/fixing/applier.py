"""Apply LLM-driven fixes from a stored or in-memory compliance report."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from difflib import unified_diff
from pathlib import Path

from pydantic import BaseModel, ValidationError

from compliance_guard.compliance.models import (
    FileComplianceResult,
    RepositoryComplianceReport,
    Severity,
    Violation,
    severity_rank,
)
from compliance_guard.fixing.paths import resolve_under_root
from compliance_guard.fixing.prompts import FixPromptBuilder
from compliance_guard.llm.base import LLMClient

logger = logging.getLogger(__name__)


class _FixLLMResponse(BaseModel):
    file: str
    content: str


@dataclass
class FileFixResult:
    """Outcome for one file."""

    file: str
    ok: bool
    message: str = ""
    diff_line_count: int = 0
    diff_preview: str = ""


@dataclass
class FixRunSummary:
    """Aggregate results from a fix pass."""

    files_considered: int = 0
    files_skipped: int = 0
    results: list[FileFixResult] = field(default_factory=list)


def violations_at_or_above(
    violations: list[Violation],
    min_severity: Severity,
) -> list[Violation]:
    """Return violations with severity at least *min_severity* (by rank)."""
    floor = severity_rank(min_severity)
    return [v for v in violations if severity_rank(v.severity) <= floor]


def _unified_diff_lines(
    rel: str,
    before: str,
    after: str,
    max_lines: int,
) -> tuple[str, int]:
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    diff = list(
        unified_diff(
            before_lines,
            after_lines,
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
            n=3,
        )
    )
    total = len(diff)
    shown = diff[:max_lines] if total > max_lines else diff
    text = "".join(shown)
    if total > max_lines:
        text += f"\n... ({total - max_lines} more diff lines)\n"
    return text, total


async def apply_fixes_from_report(
    *,
    root: Path,
    report: RepositoryComplianceReport,
    llm: LLMClient,
    min_severity: Severity = Severity.INFO,
    write: bool = False,
    max_concurrent: int = 3,
    diff_preview_lines: int = 200,
) -> FixRunSummary:
    """
    For each file in *report* with violations (and no scan error), ask the LLM
    for a full corrected file. If *write* is True, replace the file on disk;
    otherwise populate *diff_preview* on each result.
    """
    sem = asyncio.Semaphore(max(1, max_concurrent))
    summary = FixRunSummary()

    async def _run(fr: FileComplianceResult, violations: list[Violation]) -> FileFixResult:
        async with sem:
            rel = fr.file
            path = resolve_under_root(root, rel)
            if path is None or not path.is_file():
                return FileFixResult(
                    file=rel,
                    ok=False,
                    message="skip: path not under repo or not a file",
                )
            try:
                original = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                return FileFixResult(file=rel, ok=False, message=f"read_error:{exc}")

            user_prompt = FixPromptBuilder.build_user_prompt(rel, violations, original)
            raw: str | None = None
            try:
                raw = await llm.generate_json(
                    FixPromptBuilder.SYSTEM_INSTRUCTION,
                    user_prompt,
                )
                data = json.loads(raw)
                parsed = _FixLLMResponse.model_validate(data)
            except (json.JSONDecodeError, ValidationError, RuntimeError) as exc:
                logger.warning("Fix LLM failed for %s: %s", rel, exc)
                return FileFixResult(file=rel, ok=False, message=str(exc))

            out_path = resolve_under_root(root, parsed.file)
            if out_path != path:
                return FileFixResult(
                    file=rel,
                    ok=False,
                    message="model returned different path; refusing to write",
                )

            new_text = parsed.content
            preview, total_diff = _unified_diff_lines(
                rel, original, new_text, diff_preview_lines
            )
            if new_text == original:
                return FileFixResult(
                    file=rel,
                    ok=True,
                    message="unchanged (model matched original)",
                    diff_line_count=0,
                    diff_preview="",
                )

            if write:
                try:
                    path.write_text(new_text, encoding="utf-8")
                except OSError as exc:
                    return FileFixResult(file=rel, ok=False, message=f"write_error:{exc}")
                return FileFixResult(
                    file=rel,
                    ok=True,
                    message=f"wrote ({total_diff} diff lines)",
                    diff_line_count=total_diff,
                    diff_preview=preview,
                )

            return FileFixResult(
                file=rel,
                ok=True,
                message="dry-run (use --write to apply)",
                diff_line_count=total_diff,
                diff_preview=preview,
            )

    tasks: list[asyncio.Task[FileFixResult]] = []
    for fr in report.results:
        if fr.error:
            summary.files_skipped += 1
            continue
        to_fix = violations_at_or_above(fr.violations, min_severity)
        if not to_fix:
            continue
        summary.files_considered += 1
        tasks.append(asyncio.create_task(_run(fr, to_fix)))

    summary.results = list(await asyncio.gather(*tasks)) if tasks else []
    return summary
