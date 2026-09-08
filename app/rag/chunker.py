from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings


def chunk_documents(
    pages: list[Document], chunk_size: int | None = None, chunk_overlap: int | None = None
) -> list[Document]:
    settings = get_settings()
    size = chunk_size or settings.chunk_size
    overlap = settings.chunk_overlap if chunk_overlap is None else chunk_overlap
    if overlap >= size:
        raise ValueError("Chunk overlap must be smaller than chunk size")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(pages)
