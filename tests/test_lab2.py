import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.models.schemas import ChatMessage, QueryRoute, ResourceRequest
from app.routing.query_router import QueryRouter
from app.services.assistant_service import AssistantService
from app.services.session_service import SessionService
from app.tools.registry import get_tool, list_tools


@pytest.mark.parametrize(("question", "intent"), [
    ("What is the attendance requirement?", "college_policy"),
    ("What are placement eligibility criteria?", "college_policy"),
    ("Give me a Generative AI roadmap.", "learning_resource"),
    ("How should I learn Python?", "learning_resource"),
    ("What are embeddings?", "general"),
    ("What is machine learning?", "general"),
])
def test_expected_routes_without_model_call(question, intent):
    assert QueryRouter().route(question, []).intent == intent


def test_query_route_confidence_validation():
    with pytest.raises(ValidationError):
        QueryRoute(intent="general", topic="test", confidence=1.1)


def test_underspecified_requirement_has_low_confidence():
    assert QueryRouter().route("What is the requirement?", []).confidence < 0.65


def test_follow_up_inherits_previous_route():
    history = [ChatMessage(role="assistant", content="75%", route="college_policy")]
    assert QueryRouter().route("What happens if I fall below it?", history).intent == "college_policy"


def test_learning_resource_tool_and_registry():
    assert list_tools() == ("learning_resource",)
    result = get_tool("learning_resource").run("generative ai")
    assert result.data["title"] == "Generative AI Learning Roadmap"
    assert result.data["learning_stages"] and "Projects:" in result.answer


def test_clear_resource_section_is_deterministic(monkeypatch):
    monkeypatch.setattr("app.tools.learning_resource_tool.get_llm", lambda: (_ for _ in ()).throw(AssertionError("LLM should not run")))
    result = get_tool("learning_resource").run("cloud", "What are the cloud prerequisites?")
    assert result.data["requested_section"] == "prerequisites"
    assert "Networking basics" in result.answer and "Stage 1" not in result.answer


def test_unclear_resource_request_uses_qwen_section_classification(monkeypatch):
    class Structured:
        def invoke(self, messages): return ResourceRequest(section="prerequisites", confidence=.91)
    class FakeLLM:
        def with_structured_output(self, schema):
            assert schema is ResourceRequest
            return Structured()
    monkeypatch.setattr("app.tools.learning_resource_tool.get_llm", lambda: FakeLLM())
    result = get_tool("learning_resource").run("cloud", "Do I need Linux before starting cloud?")
    assert result.data["requested_section"] == "prerequisites"
    assert result.answer.startswith("Yes.") and "Linux command line" in result.answer


def test_resource_request_normalizes_percentage_confidence():
    request = ResourceRequest(section="prerequisites", confidence=91)
    assert request.confidence == .91


def test_session_history_is_bounded(monkeypatch):
    sessions = SessionService()
    monkeypatch.setattr("app.services.session_service.get_settings", lambda: type("S", (), {"session_max_messages": 2})())
    for value in ("one", "two", "three"):
        sessions.add("session", ChatMessage(role="user", content=value))
    assert [message.content for message in sessions.history("session")] == ["two", "three"]
    sessions.clear("session"); assert sessions.history("session") == []


class FixedRouter:
    def __init__(self, route): self.result = route
    def route(self, question, history): return self.result


def test_clarification_path_does_not_call_llm():
    route = QueryRoute(intent="college_policy", topic="unclear", confidence=0.2)
    response = AssistantService(SessionService(), FixedRouter(route)).respond("Requirement?")
    assert response.tool_used == "Clarification" and "Which requirement" in response.answer


def test_learning_path_and_history():
    sessions = SessionService(); route = QueryRoute(intent="learning_resource", topic="python", confidence=.99)
    service = AssistantService(sessions, FixedRouter(route))
    response = service.respond("How do I learn Python?", "s1")
    assert response.tool_used == "Learning Resource Tool" and response.session_id == "s1"
    assert len(sessions.history("s1")) == 2


def test_streaming_sends_route_tokens_metadata_and_done():
    client = TestClient(app)
    with client.stream("POST", "/chat/stream", json={"question": "How should I learn Python?", "session_id": "stream-test"}) as response:
        body = "".join(response.iter_text())
    assert response.status_code == 200
    assert "event: route" in body and "event: token" in body and "event: metadata" in body and "event: done" in body
    assert "Learning Resource Tool" in body


def test_admin_still_available():
    assert TestClient(app).get("/admin").status_code == 200
