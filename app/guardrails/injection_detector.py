import re

from app.models.schemas import GuardrailResult

PATTERNS = {
    "ignore_instructions": r"\bignore\s+(?:all\s+)?(?:previous|prior|system)\s+instructions?\b",
    "reveal_prompt": r"\b(?:reveal|show|print|repeat|tell me)\b.{0,40}\b(?:system prompt|hidden instructions?)\b",
    "unrestricted_role": r"\bact as (?:an? )?(?:unrestricted|uncensored) assistant\b",
    "override_system": r"\b(?:override|bypass)\b.{0,30}\b(?:system|instructions?|guardrails?)\b",
}


class InjectionDetector:
    def check(self, text: str) -> GuardrailResult:
        flags = [name for name, pattern in PATTERNS.items() if re.search(pattern, text, re.IGNORECASE)]
        if flags:
            return GuardrailResult(
                allowed=False, status="blocked_prompt_injection", flags=flags,
                message="I can’t follow requests to ignore instructions or reveal internal prompts. I can still help with college policies, learning resources, or general educational questions.",
            )
        return GuardrailResult(allowed=True, status="passed")

    def scan_document(self, text: str) -> list[str]:
        return [name for name, pattern in PATTERNS.items() if re.search(pattern, text, re.IGNORECASE)]
