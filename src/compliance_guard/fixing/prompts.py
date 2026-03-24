"""Prompts for turning compliance findings into a corrected file."""

from __future__ import annotations

import json
from typing import Any

from compliance_guard.compliance.models import Violation


class FixPromptBuilder:
    """Builds JSON-mode prompts for full-file remediation."""

    SYSTEM_INSTRUCTION = (
        "You are a senior application security engineer. "
        "You receive a full source file and structured compliance findings. "
        "Produce a corrected version of the file that addresses every finding "
        "without changing unrelated behavior or structure unnecessarily. "
        "Respond ONLY with valid JSON. Do not wrap JSON in markdown fences."
    )

    SCHEMA_HINT: dict[str, Any] = {
        "file": "relative/path/from/repo/root",
        "content": "complete new file contents as a single string",
    }

    @classmethod
    def build_user_prompt(
        cls,
        relative_path: str,
        violations: list[Violation],
        original_source: str,
    ) -> str:
        findings = [
            {
                "issue": v.issue,
                "severity": v.severity.value,
                "standard": v.standard,
                "explanation": v.explanation,
                "fix": v.fix,
                "fixed_code": v.fixed_code or None,
            }
            for v in violations
        ]
        schema = json.dumps(cls.SCHEMA_HINT, indent=2)
        findings_json = json.dumps(findings, indent=2, ensure_ascii=False)
        return (
            "Remediate this file for the listed compliance findings.\n\n"
            f"Target path (must match JSON \"file\" exactly): {relative_path}\n\n"
            f"Findings:\n{findings_json}\n\n"
            f"Return JSON with this shape:\n{schema}\n\n"
            "The \"content\" field MUST be the full rewritten file "
            "(not a snippet or diff).\n\n"
            "Current file:\n```\n"
            f"{original_source}\n```\n"
        )
