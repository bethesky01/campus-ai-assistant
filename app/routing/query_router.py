import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.llm.client import get_llm
from app.logging_utils import log_operation
from app.models.schemas import ChatMessage, QueryRoute

logger = logging.getLogger(__name__)

POLICY_WORDS = {"attendance", "examination", "exam", "placement", "internship", "eligibility", "college policy", "hall ticket"}
LEARNING_WORDS = {"roadmap", "learn", "learning path", "study plan", "curriculum"}
GENERAL_WORDS = {"what are embeddings", "what is machine learning", "explain", "define"}


class QueryRouter:
    def route(self, question: str, history: list[ChatMessage]) -> QueryRoute:
        text = question.lower().strip()
        if text in {"what is the requirement?", "what are the requirements?", "what is required?"}:
            return QueryRoute(intent="college_policy", topic="unspecified requirement", confidence=0.35)
        if any(phrase in text for phrase in GENERAL_WORDS):
            return QueryRoute(intent="general", topic=self._topic(text), confidence=0.90)
        if any(word in text for word in LEARNING_WORDS):
            return QueryRoute(intent="learning_resource", topic=self._topic(text), confidence=0.96)
        if any(word in text for word in POLICY_WORDS):
            return QueryRoute(intent="college_policy", topic=self._topic(text), confidence=0.95)
        if history and self._is_follow_up(text):
            previous = next((m.route for m in reversed(history) if m.role == "assistant" and m.route), None)
            if previous in {"college_policy", "learning_resource", "general"}:
                return QueryRoute(intent=previous, topic="follow-up", confidence=0.90)
        return self._structured_route(question, history)

    def _structured_route(self, question: str, history: list[ChatMessage]) -> QueryRoute:
        recent = "\n".join(f"{m.role}: {m.content}" for m in history[-4:]) or "None"
        prompt = """Classify the latest message for a campus assistant.
college_policy: institution rules, attendance, exams, placements, internships.
learning_resource: requests for a roadmap, study plan, or how to learn a subject.
general: explanations and other general knowledge. Give low confidence when underspecified."""
        with log_operation(logger, "query_routing"):
            try:
                structured = get_llm().with_structured_output(QueryRoute)
                return structured.invoke([SystemMessage(content=prompt), HumanMessage(content=f"Recent conversation:\n{recent}\nLatest: {question}")])
            except Exception:
                logger.exception("Structured routing failed; using safe low-confidence route")
                return QueryRoute(intent="general", topic="unclear", confidence=0.0)

    @staticmethod
    def _is_follow_up(text: str) -> bool:
        return any(text.startswith(prefix) for prefix in ("what if", "what happens", "why", "how about", "and ")) or any(x in text.split() for x in ("it", "that", "them"))

    @staticmethod
    def _topic(text: str) -> str:
        for topic in ("python", "generative ai", "genai", "cloud", "data engineering", "machine learning", "attendance", "examination", "placement", "internship", "embeddings"):
            if topic in text:
                return "generative ai" if topic == "genai" else topic
        return text[:100]
