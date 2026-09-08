from langchain_core.documents import Document

from app.rag import retriever


class FakeVectorStore:
    def similarity_search_with_score(self, question, k):
        return [
            (Document(page_content="attendance", metadata={"name": "best"}), 0.80),
            (Document(page_content="exam", metadata={"name": "supporting"}), 0.92),
            (Document(page_content="placement", metadata={"name": "noise"}), 1.20),
        ]


def test_retrieval_filters_candidates_farther_than_score_margin(monkeypatch):
    monkeypatch.setattr(retriever, "get_vector_store", lambda: FakeVectorStore())
    documents = retriever.retrieve("Is 70 percent attendance enough?")
    assert [document.metadata["name"] for document in documents] == ["best", "supporting"]
