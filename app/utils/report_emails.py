"""Parse and validate semicolon-separated report e-mails."""

from __future__ import annotations

from app.services.email_recipient_service import EMAIL_RE


def parse_report_emails(raw: str | None) -> list[str]:
    if not raw or not str(raw).strip():
        return []
    parts = [p.strip() for p in str(raw).split(";")]
    return [p for p in parts if p]


def normalize_report_emails(raw: str | None) -> str | None:
    emails = parse_report_emails(raw)
    if not emails:
        return None
    return ";".join(emails)


def validate_report_emails(raw: str | None) -> list[str]:
    """Return normalized list or raise ValueError with invalid address."""
    emails = parse_report_emails(raw)
    seen: set[str] = set()
    normalized: list[str] = []
    for email in emails:
        lower = email.lower()
        if not EMAIL_RE.match(lower):
            raise ValueError(f"E-mail inválido: {email}")
        if lower in seen:
            raise ValueError(f"E-mail duplicado: {email}")
        seen.add(lower)
        normalized.append(lower)
    return normalized
