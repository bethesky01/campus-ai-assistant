import json
import logging
import os
import tempfile
from pathlib import Path

from app.config import get_settings
from app.logging_utils import log_operation
from app.models.schemas import DocumentMetadata

logger = logging.getLogger(__name__)


class RegistryService:
    def __init__(self, path: Path | None = None):
        self.path = path or get_settings().registry_path

    def list(self) -> list[DocumentMetadata]:
        with log_operation(logger, "registry_read"):
            if not self.path.exists():
                return []
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                return [DocumentMetadata.model_validate(item) for item in data]
            except (json.JSONDecodeError, OSError, ValueError) as exc:
                raise RuntimeError(f"Document registry is invalid: {exc}") from exc

    def get(self, document_id: str) -> DocumentMetadata | None:
        return next((item for item in self.list() if item.document_id == document_id), None)

    def save(self, item: DocumentMetadata) -> None:
        with log_operation(logger, "registry_save", document_id=item.document_id, status=item.status):
            items = [existing for existing in self.list() if existing.document_id != item.document_id]
            items.append(item)
            self._write(items)

    def delete(self, document_id: str) -> None:
        with log_operation(logger, "registry_delete", document_id=document_id):
            self._write([item for item in self.list() if item.document_id != document_id])

    def _write(self, items: list[DocumentMetadata]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(dir=self.path.parent, suffix=".json.tmp")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump([item.model_dump() for item in items], stream, indent=2)
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
