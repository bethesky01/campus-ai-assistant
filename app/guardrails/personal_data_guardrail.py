import re

from app.models.schemas import PersonalDataResult


class PersonalDataGuardrail:
    """Detects selected workshop PII patterns; this is not comprehensive DLP."""

    PATTERNS = (
        ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE), "[REDACTED_EMAIL]"),
        ("phone_number", re.compile(r"(?<!\d)(?:\+?91[-\s]?)?[6-9]\d{9}(?!\d)"), "[REDACTED_PHONE]"),
        ("student_id", re.compile(r"\b[A-Z]{2,8}[-/]?\d{5,12}\b", re.IGNORECASE), "[REDACTED_STUDENT_ID]"),
    )

    def redact(self, text: str) -> PersonalDataResult:
        redacted = text
        categories = []
        for category, pattern, replacement in self.PATTERNS:
            redacted, count = pattern.subn(replacement, redacted)
            if count:
                categories.append(category)
        return PersonalDataResult(detected=bool(categories), redacted_text=redacted, categories=categories)
