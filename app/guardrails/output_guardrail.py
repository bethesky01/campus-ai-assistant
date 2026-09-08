from app.models.schemas import ChatResponse


class OutputGuardrail:
    def validate(self, response: ChatResponse, valid_document_ids: set[str] | None = None) -> ChatResponse:
        if not response.answer.strip():
            raise ValueError("Assistant answer cannot be empty")
        if response.tool_used == "College Policy RAG" and response.grounded and not response.sources:
            raise ValueError("A grounded college-policy answer must include sources")
        if response.safety_status == "insufficient_evidence" and response.grounded:
            raise ValueError("An insufficient-evidence response cannot be grounded")
        if response.tool_used != "College Policy RAG" and response.grounded:
            raise ValueError("Only College Policy RAG responses may be marked grounded")
        for source in response.sources:
            if not source.document_id or not source.document_title or not source.chunk_id:
                raise ValueError("Source metadata is incomplete")
            if source.page is not None and source.page < 1:
                raise ValueError("Source page must be positive")
            if valid_document_ids is not None and source.document_id not in valid_document_ids:
                raise ValueError("Source does not correspond to a registered document")
        return response
