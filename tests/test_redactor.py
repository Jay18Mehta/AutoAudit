"""Tests for :mod:`compliance_guard.security.redactor`."""

from compliance_guard.security.redactor import ContentRedactor, estimate_tokens


def test_redact_masks_email_and_assignment() -> None:
    r = ContentRedactor()
    text = 'user@example.com password=secret123 token: abcdefghijklmnopqrstuvwxyz0123456789abcd'
    out, stats = r.redact(text, enabled=True)
    assert "[REDACTED_EMAIL]" in out
    assert "example.com" not in out
    assert stats.emails >= 1
    assert stats.passwords >= 1


def test_estimate_tokens_positive() -> None:
    t = estimate_tokens("hello world " * 50)
    assert t > 10
