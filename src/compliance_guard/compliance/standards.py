"""Compliance standard identifiers (extensible)."""

from __future__ import annotations

from enum import Enum


class ComplianceStandard(str, Enum):
    """Supported compliance frameworks for classification."""

    SOC2 = "SOC2"
    HIPAA = "HIPAA"
    ISO27001 = "ISO27001"
