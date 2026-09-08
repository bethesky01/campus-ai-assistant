import pytest

from app.llm.client import get_embeddings, get_llm


@pytest.mark.integration
def test_configured_ollama_models_respond():
    vector = get_embeddings().embed_query("attendance policy")
    assert vector and all(isinstance(value, float) for value in vector)
    response = get_llm().invoke("Reply with the word ready.")
    assert response.content
