import re

from app.config import get_settings
from app.models.schemas import GuardrailResult


class InputGuardrail:
    def check(self, text: str) -> GuardrailResult:
        if not text or not text.strip():
            return GuardrailResult(allowed=False, status="invalid_input", message="Please enter a question.")
        if len(text) > get_settings().guardrail_max_input_chars:
            return GuardrailResult(allowed=False, status="input_too_long", message="Your question is too long. Please shorten it and try again.")
        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", text):
            return GuardrailResult(allowed=False, status="malformed_input", message="The question contains unsupported control characters.")
        return GuardrailResult(allowed=True, status="passed")
