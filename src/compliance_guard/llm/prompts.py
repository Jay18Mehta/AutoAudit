"""Structured prompts for compliance analysis."""

from __future__ import annotations

import json
from typing import Any


class CompliancePromptBuilder:
    """Builds deterministic prompts for Gemini JSON outputs."""

    SYSTEM_INSTRUCTION = (
        "You are a senior application security and compliance auditor. "
        "Analyze source code for SOC2, HIPAA, and ISO 27001 style issues. "
        "Respond ONLY with valid JSON matching the schema. "
        "Do not wrap JSON in markdown fences."
    )

    SCHEMA_HINT: dict[str, Any] = {
        "file": "",
        "violations": [
            {
                "standard": "SOC2|HIPAA|ISO27001",
                "severity": "critical|high|medium|low|info",
                "issue": "short title",
                "explanation": "why this matters",
                "fix": "recommended secure approach",
                "fixed_code": "minimal patch or snippet",
            }
        ],
        "secure_patterns": ["positive controls observed"],
    }

    @classmethod
    def build_user_prompt(
        cls,
        relative_path: str,
        language: str | None,
        code: str,
    ) -> str:
        """Create the user message with embedded code."""
        schema = json.dumps(cls.SCHEMA_HINT, indent=2)
        lang = language or "unknown"
        checklist = (
            "Check SOC2-style issues such as: hardcoded secrets; logging sensitive data; "
            "missing authentication/authorization; poor error handling; missing audit logging.\n"
            "Check HIPAA-style issues such as: PHI exposure risks; improper encryption; "
            "data leakage; missing access controls.\n"
            "Check ISO 27001-style issues such as: security misconfigurations; weak crypto; "
            "secrets management; input validation problems.\n"
        )
        return (
            "Analyze this code for compliance violations.\n\n"
            f"{checklist}\n"
            "Return JSON with this shape (fill all fields logically):\n"
            f"{schema}\n\n"
            f'Use "file": "{relative_path}" in the output.\n'
            f"Language: {lang}\n\n"
            "Code:\n"
            "```\n"
            f"{code}\n"
            "```\n"
        )
