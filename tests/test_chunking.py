from langchain_core.documents import Document

from app.rag.chunker import chunk_documents


def test_chunking_preserves_page_metadata():
    pages = [Document(page_content=("Campus policy sentence. " * 40), metadata={"page": 3})]
    chunks = chunk_documents(pages, chunk_size=120, chunk_overlap=20)
    assert len(chunks) > 1
    assert all(chunk.metadata["page"] == 3 for chunk in chunks)
    assert all(len(chunk.page_content) <= 120 for chunk in chunks)


def test_overlap_must_be_smaller_than_size():
    # The splitter itself enforces this invariant for direct overrides.
    try:
        chunk_documents([Document(page_content="text", metadata={})], 100, 100)
    except ValueError:
        return
    raise AssertionError("Expected invalid overlap to raise ValueError")
