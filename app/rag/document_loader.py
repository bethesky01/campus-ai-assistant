from pathlib import Path

from langchain_core.documents import Document
from pypdf import PdfReader


def load_pdf(path: Path) -> list[Document]:
    try:
        reader = PdfReader(str(path))
        pages = []
        for number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                pages.append(Document(page_content=text, metadata={"page": number}))
    except Exception as exc:
        raise ValueError(f"The PDF could not be parsed: {exc}") from exc
    if not pages:
        raise ValueError("The PDF contains no extractable text.")
    return pages
