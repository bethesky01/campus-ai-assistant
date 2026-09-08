import logging

from app.llm.client import get_llm
from app.logging_utils import log_operation
from app.models.schemas import ChatResponse, SourceReference
from app.rag.chain import NOT_FOUND_ANSWER, answer_with_context
from app.rag.retriever import retrieve
from app.services.registry_service import RegistryService

logger = logging.getLogger(__name__)


class ChatService:
    def ask(self, question: str) -> ChatResponse:
        with log_operation(logger, "chat_request", question_length=len(question)):
            if not any(document.status == "indexed" for document in RegistryService().list()):
                logger.info("chat_short_circuit reason=no_indexed_documents")
                return ChatResponse(answer=NOT_FOUND_ANSWER)
            documents = retrieve(question)
            answer = answer_with_context(question, documents, get_llm())
            if answer == NOT_FOUND_ANSWER:
                return ChatResponse(answer=answer)
            seen, sources = set(), []
            for doc in documents:
                meta = doc.metadata
                key = (meta.get("document_id"), meta.get("page"))
                if key in seen:
                    continue
                seen.add(key)
                sources.append(SourceReference(
                    document_id=str(meta.get("document_id", "")),
                    document_title=str(meta.get("document_title", "Unknown document")),
                    category=str(meta.get("category", "Other")), page=meta.get("page"),
                    chunk_id=str(meta.get("chunk_id", "")),
                ))
            logger.info("source_attribution_completed source_count=%d", len(sources))
            return ChatResponse(answer=answer, sources=sources)
