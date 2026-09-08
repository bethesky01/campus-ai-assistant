import re

from langchain_core.documents import Document

STOPWORDS = {"what", "is", "are", "the", "a", "an", "for", "of", "in", "to", "and", "college", "policy", "requirement", "requirements", "happens", "if", "i", "it", "my", "me"}


class GroundingGuardrail:
    def evidence_is_sufficient(self, question: str, documents: list[Document]) -> bool:
        if not documents:
            return False
        terms = {word for word in re.findall(r"[a-z]{3,}", question.lower()) if word not in STOPWORDS}
        if not terms:
            return False
        context = " ".join(document.page_content.lower() for document in documents)
        return any(term in context for term in terms)
