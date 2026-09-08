import logging
from contextvars import ContextVar
from time import perf_counter

from langchain_ollama import ChatOllama, OllamaEmbeddings

from app.config import get_settings

logger = logging.getLogger(__name__)
_query_embedding_active: ContextVar[bool] = ContextVar("query_embedding_active", default=False)


class TimedChatOllama(ChatOllama):
    def invoke(self, input, config=None, **kwargs):
        logger.info("llm_call_started model=%s", self.model)
        started = perf_counter()
        try:
            response = super().invoke(input, config=config, **kwargs)
        except Exception:
            logger.exception(
                "llm_call_failed model=%s elapsed_seconds=%.3f",
                self.model, perf_counter() - started,
            )
            raise
        logger.info(
            "llm_call_completed model=%s elapsed_seconds=%.3f",
            self.model, perf_counter() - started,
        )
        return response

    def stream(self, input, config=None, **kwargs):
        logger.info("llm_stream_started model=%s", self.model)
        started = perf_counter()
        try:
            for chunk in super().stream(input, config=config, **kwargs):
                yield chunk
        except Exception:
            logger.exception("llm_stream_failed model=%s elapsed_seconds=%.3f", self.model, perf_counter() - started)
            raise
        logger.info("llm_stream_completed model=%s elapsed_seconds=%.3f", self.model, perf_counter() - started)


class TimedOllamaEmbeddings(OllamaEmbeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if _query_embedding_active.get():
            return super().embed_documents(texts)
        return self._timed_embedding("documents", len(texts), lambda: super(TimedOllamaEmbeddings, self).embed_documents(texts))

    def embed_query(self, text: str) -> list[float]:
        def call_query():
            token = _query_embedding_active.set(True)
            try:
                return super(TimedOllamaEmbeddings, self).embed_query(text)
            finally:
                _query_embedding_active.reset(token)
        return self._timed_embedding("query", 1, call_query)

    def _timed_embedding(self, call_type: str, item_count: int, call):
        logger.info(
            "embedding_call_started model=%s call_type=%s item_count=%d",
            self.model, call_type, item_count,
        )
        started = perf_counter()
        try:
            result = call()
        except Exception:
            logger.exception(
                "embedding_call_failed model=%s call_type=%s item_count=%d elapsed_seconds=%.3f",
                self.model, call_type, item_count, perf_counter() - started,
            )
            raise
        logger.info(
            "embedding_call_completed model=%s call_type=%s item_count=%d elapsed_seconds=%.3f",
            self.model, call_type, item_count, perf_counter() - started,
        )
        return result


def get_llm() -> TimedChatOllama:
    settings = get_settings()
    return TimedChatOllama(
        base_url=settings.ollama_base_url,
        model=settings.ollama_llm_model,
        temperature=0,
        # Policy Q&A does not need extended reasoning; cap output and retain the model to reduce response latency.
        reasoning=False,
        num_predict=200,
        keep_alive="10m",
    )


def get_embeddings() -> TimedOllamaEmbeddings:
    settings = get_settings()
    return TimedOllamaEmbeddings(
        base_url=settings.ollama_base_url,
        model=settings.ollama_embedding_model,
    )
