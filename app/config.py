from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    app_name: str = "Campus AI Assistant"
    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "qwen3:8b"
    ollama_embedding_model: str = "embeddinggemma"
    chunk_size: int = Field(800, ge=100)
    chunk_overlap: int = Field(120, ge=0)
    top_k: int = Field(4, ge=1, le=20)
    retrieval_score_margin: float = Field(0.25, ge=0)
    router_confidence_threshold: float = Field(0.65, ge=0, le=1)
    session_max_messages: int = Field(12, ge=2, le=100)
    guardrail_max_input_chars: int = Field(2000, ge=100, le=20000)
    debug_mode: bool = False
    max_upload_size_mb: int = Field(10, ge=1)
    chroma_collection: str = "campus_knowledge_base"
    documents_dir: Path = ROOT_DIR / "data" / "documents"
    chroma_dir: Path = ROOT_DIR / "chroma_db"
    registry_path: Path = ROOT_DIR / "data" / "documents" / "registry.json"
    learning_resources_dir: Path = ROOT_DIR / "data" / "learning_resources"

    @model_validator(mode="after")
    def validate_chunking(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        return self


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.documents_dir.mkdir(parents=True, exist_ok=True)
    settings.learning_resources_dir.mkdir(parents=True, exist_ok=True)
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    return settings
