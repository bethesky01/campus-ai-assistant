import logging
from collections.abc import Iterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.config import get_settings
from app.guardrails.grounding_guardrail import GroundingGuardrail
from app.guardrails.injection_detector import InjectionDetector
from app.guardrails.input_guardrail import InputGuardrail
from app.guardrails.output_guardrail import OutputGuardrail
from app.guardrails.personal_data_guardrail import PersonalDataGuardrail
from app.llm.client import get_llm
from app.logging_utils import log_operation
from app.models.schemas import ChatMessage, ChatResponse, QueryRoute, SourceReference
from app.rag.chain import NOT_FOUND_ANSWER, grounded_messages
from app.rag.retriever import retrieve
from app.routing.query_router import QueryRouter
from app.services.session_service import SessionService, session_service
from app.services.registry_service import RegistryService
from app.tools.registry import get_tool

logger = logging.getLogger(__name__)
CLARIFICATION = "Which requirement do you mean? Attendance, Examination, Placement, or Internship?"
GENERAL_SYSTEM = "You are a helpful general AI tutor. Answer clearly and concisely. Do not present general knowledge as official college policy."
ABSTENTION = "I couldn't find enough information about that in the available college documents."
SCOPE_RESPONSE = "I don’t have access to live scores, current weather, or other real-time data. I can help with college policies, learning roadmaps, and general educational concepts."


class AssistantService:
    def __init__(self, sessions: SessionService | None = None, router: QueryRouter | None = None):
        self.sessions = sessions or session_service
        self.router = router or QueryRouter()

    def respond(self, question: str, session_id: str | None = None) -> ChatResponse:
        privacy = PersonalDataGuardrail().redact(question)
        if privacy.detected:
            logger.warning("personal_data_detected categories=%s", privacy.categories)
        response = self._respond(privacy.redacted_text, session_id)
        return self._apply_privacy(response, privacy)

    def _respond(self, question: str, session_id: str | None = None) -> ChatResponse:
        sid = self.sessions.ensure_id(session_id)
        blocked = self._preflight(question, sid)
        if blocked:
            return blocked
        sid, history, route = self._prepare(question, sid)
        if route.confidence < get_settings().router_confidence_threshold:
            return self._finish(sid, question, CLARIFICATION, route, "Clarification", False, safety_status="clarification_required")
        if route.intent == "learning_resource":
            result = get_tool("learning_resource").run(route.topic, question)
            is_grounded = result.data.get("source_type") == "curated_learning_resource"
            return self._finish(
                sid, question, result.answer, route, "Learning Resource Tool",
                is_grounded, metadata=result.data,
            )
        if route.intent == "college_policy":
            contextual_question = self._contextual_query(question, history)
            documents = retrieve(contextual_question)
            if not GroundingGuardrail().evidence_is_sufficient(contextual_question, documents):
                return self._finish(sid, question, ABSTENTION, route, "College Policy RAG", False, safety_status="insufficient_evidence")
            answer = str(get_llm().invoke(grounded_messages(question, documents, self._history_text(history))).content).strip()
            if answer in {NOT_FOUND_ANSWER, ABSTENTION}:
                return self._finish(sid, question, ABSTENTION, route, "College Policy RAG", False, safety_status="insufficient_evidence")
            return self._finish(sid, question, answer, route, "College Policy RAG", True, self._sources(documents))
        messages = [SystemMessage(content=GENERAL_SYSTEM), *self._history_messages(history), HumanMessage(content=question)]
        answer = str(get_llm().invoke(messages).content).strip()
        return self._finish(sid, question, answer, route, "General AI", False)

    def stream(self, question: str, session_id: str | None = None) -> Iterator[dict]:
        # LAB3 buffers generation until validation succeeds, then streams only approved output.
        response = self.respond(question, session_id)
        route = response.metadata.get("route", {"intent": "guardrail", "topic": response.safety_status, "confidence": 1})
        yield {"event": "route", "session_id": response.session_id, **route}
        for word in response.answer.split(" "):
            yield {"event": "token", "content": word + " "}
        yield {"event": "metadata", **response.model_dump(exclude={"answer"})}
        yield {"event": "done"}

    def _prepare(self, question, session_id):
        sid = self.sessions.ensure_id(session_id)
        history = self.sessions.history(sid)
        with log_operation(logger, "assistant_routing", session_id=sid):
            route = self.router.route(question, history)
        logger.info("route_selected session_id=%s intent=%s topic=%s confidence=%.2f", sid, route.intent, route.topic, route.confidence)
        return sid, history, route

    def _finish(self, sid, question, answer, route, tool, grounded, sources=None, metadata=None, safety_status="passed"):
        details = dict(metadata or {})
        details["route"] = route.model_dump()
        if get_settings().debug_mode:
            details["debug"] = {"route": route.intent, "confidence": route.confidence, "tool": tool, "grounded": grounded, "safety_status": safety_status}
        response = ChatResponse(answer=answer, sources=sources or [], tool_used=tool, grounded=grounded, session_id=sid, metadata=details, safety_status=safety_status)
        valid_ids = {document.document_id for document in RegistryService().list()}
        response = OutputGuardrail().validate(response, valid_ids if response.sources else None)
        self.sessions.add(sid, ChatMessage(role="user", content=question))
        self.sessions.add(sid, ChatMessage(role="assistant", content=answer, tool_used=tool, route=route.intent))
        return response

    def _preflight(self, question: str, sid: str) -> ChatResponse | None:
        for guardrail, tool in ((InputGuardrail(), "Input Guardrail"), (InjectionDetector(), "Prompt Injection Guardrail")):
            result = guardrail.check(question)
            if not result.allowed:
                response = ChatResponse(answer=result.message or "This request cannot be processed.", tool_used=tool, grounded=False, session_id=sid, safety_status=result.status, metadata={"guardrail_flags": result.flags})
                OutputGuardrail().validate(response)
                self.sessions.add(sid, ChatMessage(role="user", content=question))
                self.sessions.add(sid, ChatMessage(role="assistant", content=response.answer, tool_used=tool, route="guardrail"))
                return response
        text = question.lower()
        if any(phrase in text for phrase in ("today's ipl", "today’s ipl", "current score", "weather tomorrow", "tomorrow's weather", "live score")):
            response = ChatResponse(answer=SCOPE_RESPONSE, tool_used="Scope Handler", grounded=False, session_id=sid, safety_status="out_of_scope")
            OutputGuardrail().validate(response)
            self.sessions.add(sid, ChatMessage(role="user", content=question))
            self.sessions.add(sid, ChatMessage(role="assistant", content=response.answer, tool_used="Scope Handler", route="scope"))
            return response
        return None

    @staticmethod
    def _apply_privacy(response: ChatResponse, input_privacy) -> ChatResponse:
        output_privacy = PersonalDataGuardrail().redact(response.answer)
        if input_privacy.detected or output_privacy.detected:
            previous_status = response.safety_status
            response.answer = output_privacy.redacted_text
            notice = "I detected personal information and did not repeat it. "
            if not response.answer.startswith(notice):
                response.answer = notice + response.answer
            response.metadata["personal_data"] = {
                "redacted": True,
                "categories": sorted(set(input_privacy.categories + output_privacy.categories)),
                "previous_safety_status": previous_status,
            }
            if response.safety_status in {"passed", "clarification_required"}:
                response.safety_status = "personal_data_redacted"
        return OutputGuardrail().validate(response)

    def _stream_static(self, sid, question, answer, route, tool, grounded, metadata=None):
        for word in answer.split(" "):
            yield {"event": "token", "content": word + " "}
        response = self._finish(sid, question, answer, route, tool, grounded, metadata=metadata)
        yield {"event": "metadata", **response.model_dump(exclude={"answer"})}
        yield {"event": "done"}

    @staticmethod
    def _sources(documents):
        seen, sources = set(), []
        for doc in documents:
            m = doc.metadata; key = (m.get("document_id"), m.get("page"))
            if key in seen: continue
            seen.add(key); sources.append(SourceReference(document_id=str(m.get("document_id", "")), document_title=str(m.get("document_title", "Unknown")), category=str(m.get("category", "Other")), page=m.get("page"), chunk_id=str(m.get("chunk_id", ""))))
        return sources

    @staticmethod
    def _history_text(history): return "\n".join(f"{m.role}: {m.content}" for m in history[-4:])
    @staticmethod
    def _history_messages(history): return [HumanMessage(content=m.content) if m.role == "user" else AIMessage(content=m.content) for m in history[-4:]]
    @staticmethod
    def _contextual_query(question, history):
        previous = next((m.content for m in reversed(history) if m.role == "user"), "")
        return f"{previous}\n{question}" if previous else question
