import logging
from functools import lru_cache

from langchain_chroma import Chroma

from app.config import get_settings
from app.llm.client import get_embeddings
from app.logging_utils import log_operation

logger = logging.getLogger(__name__)


@lru_cache
def get_vector_store() -> Chroma:
    settings = get_settings()
    with log_operation(logger, "vector_store_initialization", collection=settings.chroma_collection):
        return Chroma(
            collection_name=settings.chroma_collection,
            embedding_function=get_embeddings(),
            persist_directory=str(settings.chroma_dir),
        )


def delete_document_vectors(document_id: str) -> None:
    with log_operation(logger, "vector_deletion", document_id=document_id):
        get_vector_store().delete(where={"document_id": document_id})
