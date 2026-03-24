"""Orchestrates per-file Gemini analysis with redaction and parsing."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from pydantic import ValidationError

from compliance_guard.compliance.models import (
    FileComplianceResult,
    RepositoryComplianceReport,
    Violation,
)
from compliance_guard.reporting.aggregator import compute_risk_summary
from compliance_guard.indexing.models import FileIndexEntry, RepositoryIndex
from compliance_guard.llm.base import LLMClient
from compliance_guard.llm.prompts import CompliancePromptBuilder
from compliance_guard.security.redactor import ContentRedactor

logger = logging.getLogger(__name__)


class ComplianceAnalyzer:
    """Runs structured compliance prompts per indexed source file."""

    def __init__(
        self,
        llm: LLMClient,
        redactor: ContentRedactor,
        redact: bool = True,
        max_concurrent: int = 3,
    ) -> None:
        self._llm = llm
        self._redactor = redactor
        self._redact = redact
        self._max_concurrent = max(1, max_concurrent)

    async def analyze_repository(
        self,
        index: RepositoryIndex,
    ) -> RepositoryComplianceReport:
        """Analyze all source entries in the index."""
        sem = asyncio.Semaphore(self._max_concurrent)
        targets = index.analysis_targets()

        async def _one(entry: FileIndexEntry) -> FileComplianceResult:
            async with sem:
                return await self._analyze_file(entry)

        results = await asyncio.gather(*(_one(e) for e in targets))

        summary = compute_risk_summary(results)
        return RepositoryComplianceReport(
            root=index.root,
            model=self._llm.config.model,
            results=results,
            risk_summary=summary,
            index_snapshot={
                "entry_count": len(index.entries),
                "analysis_target_count": len(index.analysis_targets()),
            },
        )

    async def _analyze_file(self, entry: FileIndexEntry) -> FileComplianceResult:
        rel = entry.relative_path
        try:
            raw_text = entry.path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return FileComplianceResult(
                file=rel,
                error=f"read_error:{exc}",
            )

        text, _stats = self._redactor.redact(raw_text, enabled=self._redact)
        user_prompt = CompliancePromptBuilder.build_user_prompt(
            relative_path=rel,
            language=entry.language,
            code=text,
        )
        raw: str | None = None
        try:
            raw = await self._llm.generate_json(
                CompliancePromptBuilder.SYSTEM_INSTRUCTION,
                user_prompt,
            )
            data = json.loads(raw)
            return self._parse_result(data, raw, default_file=rel)
        except (json.JSONDecodeError, ValidationError, RuntimeError) as exc:
            logger.warning("Analysis failed for %s: %s", rel, exc)
            return FileComplianceResult(
                file=rel,
                error=str(exc),
                raw_response=raw,
            )

    def _parse_result(
        self,
        data: dict[str, Any],
        raw: str,
        default_file: str,
    ) -> FileComplianceResult:
        violations_raw = data.get("violations") or []
        violations: list[Violation] = []
        for v in violations_raw:
            try:
                violations.append(Violation.model_validate(v))
            except ValidationError as exc:
                logger.debug("Skip invalid violation: %s", exc)
        secure = list(data.get("secure_patterns") or [])
        file_path = str(data.get("file") or default_file or "")
        return FileComplianceResult(
            file=file_path,
            violations=violations,
            secure_patterns=secure,
            raw_response=raw,
        )
