import logging

from langchain_core.documents import Document

from app.config import get_settings
from app.logging_utils import log_operation
from app.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)


def retrieve(question: str) -> list[Document]:
    settings = get_settings()
    top_k = settings.top_k
    with log_operation(logger, "knowledge_retrieval", top_k=top_k, score_margin=settings.retrieval_score_margin):
        matches = get_vector_store().similarity_search_with_score(question, k=top_k)
        if not matches:
            documents = []
        else:
            # Chroma returns distances: smaller values are more similar. Keep results close
            # to the best match so TOP_K is a candidate limit, not a mandate to cite noise.
            best_score = matches[0][1]
            cutoff = best_score + settings.retrieval_score_margin
            documents = [document for document, score in matches if score <= cutoff]
            logger.info(
                "retrieval_scores best_score=%.4f cutoff=%.4f candidates=%d selected=%d",
                best_score, cutoff, len(matches), len(documents),
            )
    logger.info("retrieval_result chunk_count=%d", len(documents))
    return documents
