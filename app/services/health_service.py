import logging

import httpx

from app.config import get_settings
from app.logging_utils import log_operation
from app.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)


def health_status() -> tuple[dict, int]:
    settings = get_settings()
    result = {"status": "degraded", "ollama": False, "llm_model": False, "embedding_model": False, "chromadb": False}
    try:
        with log_operation(logger, "ollama_health_check"):
            response = httpx.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags", timeout=2)
            response.raise_for_status()
            names = {item["name"] for item in response.json().get("models", [])}
            def installed(configured: str) -> bool:
                return configured in names or (":" not in configured and f"{configured}:latest" in names)
            result["ollama"] = True
            result["llm_model"] = installed(settings.ollama_llm_model)
            result["embedding_model"] = installed(settings.ollama_embedding_model)
    except Exception:
        pass
    try:
        with log_operation(logger, "chromadb_health_check"):
            result["chromadb"] = get_vector_store()._collection.count() >= 0
    except Exception:
        pass
    if all(result[key] for key in ("ollama", "llm_model", "embedding_model", "chromadb")):
        result["status"] = "ready"
        logger.info("health_check_completed status=ready components=%s", result)
        return result, 200
    logger.warning("health_check_completed status=degraded components=%s", result)
    return result, 503
