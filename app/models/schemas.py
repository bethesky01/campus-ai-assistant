from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

CATEGORIES = ("Attendance", "Examination", "Placement", "Internship", "Other")


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=100)

    @field_validator("question")
    @classmethod
    def non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question cannot be empty")
        return value


class SourceReference(BaseModel):
    document_id: str
    document_title: str
    category: str
    page: int | None = None
    chunk_id: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceReference] = Field(default_factory=list)
    tool_used: str = "College Policy RAG"
    grounded: bool = True
    session_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    safety_status: str = "passed"


class QueryRoute(BaseModel):
    intent: Literal["college_policy", "learning_resource", "general"]
    topic: str = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    tool_used: str | None = None
    route: str | None = None


class ToolResult(BaseModel):
    tool_name: str
    answer: str
    data: dict[str, Any] = Field(default_factory=dict)


class GuardrailResult(BaseModel):
    allowed: bool
    status: str
    message: str | None = None
    flags: list[str] = Field(default_factory=list)


class PersonalDataResult(BaseModel):
    detected: bool
    redacted_text: str
    categories: list[str] = Field(default_factory=list)


class ResourceRequest(BaseModel):
    section: Literal[
        "prerequisites", "learning_stages", "recommended_topics",
        "projects", "next_steps", "full_resource",
    ]
    confidence: float = Field(ge=0, le=1, description="Confidence from 0.0 to 1.0")

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_percentage_confidence(cls, value):
        """Some local models emit 85 instead of 0.85 despite the requested schema."""
        numeric = float(value)
        if 1 < numeric <= 100:
            return numeric / 100
        return numeric


class DocumentMetadata(BaseModel):
    document_id: str
    title: str
    category: str
    filename: str
    status: Literal["processing", "indexed", "failed"] = "processing"
    uploaded_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    page_count: int = 0
    chunk_count: int = 0
    error: str | None = None
    safety_status: str = "not_scanned"
    safety_flags: list[str] = Field(default_factory=list)
