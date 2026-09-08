from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_home_and_admin_render():
    assert client.get("/").status_code == 200
    response = client.get("/admin")
    assert response.status_code == 200
    assert "Admin Knowledge Base" in response.text


def test_empty_chat_input_returns_422():
    assert client.post("/chat", json={"question": " "}).status_code == 422


def test_invalid_upload_rejected():
    response = client.post("/admin/upload", data={"title": "Bad", "category": "Other"}, files={"file": ("bad.exe", b"abc", "application/octet-stream")})
    assert response.status_code == 400


def test_missing_document_actions_return_404(monkeypatch):
    monkeypatch.setattr("app.services.document_service.get_vector_store", lambda: object())
    assert client.post("/admin/documents/not-found/reindex").status_code == 404
    assert client.delete("/admin/documents/not-found").status_code == 404
