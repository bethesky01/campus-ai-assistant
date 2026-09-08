from langchain_core.documents import Document

from app.guardrails.injection_detector import InjectionDetector


class DocumentGuardrail:
    """Flags obvious instruction-like content; it never treats document text as instructions."""
    def scan(self, pages: list[Document]) -> list[str]:
        detector = InjectionDetector()
        return sorted({flag for page in pages for flag in detector.scan_document(page.page_content)})
