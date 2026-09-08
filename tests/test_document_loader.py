import pytest
from pypdf import PdfWriter

from app.config import get_settings
from app.rag.document_loader import load_pdf


def test_empty_pdf_rejected():
    path = get_settings().documents_dir / "_test_blank.pdf"
    writer = PdfWriter(); writer.add_blank_page(width=100, height=100)
    try:
        with path.open("wb") as stream: writer.write(stream)
        with pytest.raises(ValueError, match="no extractable text"):
            load_pdf(path)
    finally:
        path.unlink(missing_ok=True)


def test_corrupt_pdf_rejected():
    path = get_settings().documents_dir / "_test_bad.pdf"
    try:
        path.write_bytes(b"%PDF-not-really")
        with pytest.raises(ValueError, match="could not be parsed"):
            load_pdf(path)
    finally:
        path.unlink(missing_ok=True)
