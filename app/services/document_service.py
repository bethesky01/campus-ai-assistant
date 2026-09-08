import logging
import re
import asyncio
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import get_settings
from app.guardrails.document_guardrail import DocumentGuardrail
from app.logging_utils import log_operation
from app.models.schemas import CATEGORIES, DocumentMetadata
from app.rag.chunker import chunk_documents
from app.rag.document_loader import load_pdf
from app.rag.vector_store import get_vector_store
from app.services.registry_service import RegistryService

logger = logging.getLogger(__name__)
ProgressCallback = Callable[[str, int, str], None]


class DocumentService:
    def __init__(self, registry: RegistryService | None = None, vector_store=None):
        self.settings = get_settings()
        self.registry = registry or RegistryService()
        self._vector_store = vector_store

    @property
    def vector_store(self):
        return self._vector_store or get_vector_store()

    def list_documents(self) -> list[DocumentMetadata]:
        with log_operation(logger, "document_listing"):
            return sorted(self.registry.list(), key=lambda item: item.uploaded_at, reverse=True)

    async def upload(
        self, title: str, category: str, upload: UploadFile, progress: ProgressCallback | None = None,
    ) -> DocumentMetadata:
        with log_operation(
            logger, "document_upload", filename=Path(upload.filename or "").name, category=category,
        ):
            return await self._upload(title, category, upload, progress)

    @staticmethod
    def _progress(callback: ProgressCallback | None, stage: str, percent: int, message: str) -> None:
        if callback:
            callback(stage, percent, message)

    async def _upload(
        self, title: str, category: str, upload: UploadFile, progress: ProgressCallback | None = None,
    ) -> DocumentMetadata:
        self._progress(progress, "validating", 5, "Validating the PDF and upload details")
        title = title.strip()
        if not title or len(title) > 200:
            raise ValueError("Document title is required and must be under 200 characters.")
        if category not in CATEGORIES:
            raise ValueError("Invalid document category.")
        filename = Path(upload.filename or "").name
        if Path(filename).suffix.lower() != ".pdf":
            raise ValueError("Only PDF files are accepted.")
        if upload.content_type and upload.content_type not in {"application/pdf", "application/octet-stream"}:
            raise ValueError("The uploaded file is not identified as a PDF.")
        content = await upload.read(self.settings.max_upload_size_mb * 1024 * 1024 + 1)
        if not content:
            raise ValueError("The uploaded PDF is empty.")
        if len(content) > self.settings.max_upload_size_mb * 1024 * 1024:
            raise ValueError(f"PDF exceeds the {self.settings.max_upload_size_mb} MB upload limit.")
        if not content.startswith(b"%PDF-"):
            raise ValueError("The file content is not a valid PDF.")
        logger.info("process_completed operation=upload_validation size_bytes=%d", len(content))

        # PDF parsing, embedding, and vector writes are blocking operations. Run them in a worker
        # thread so the event loop can stream actual progress updates to the admin UI.
        return await asyncio.to_thread(
            self._store_and_index, title, category, filename, content, progress,
        )

    def _store_and_index(
        self, title: str, category: str, filename: str, content: bytes,
        progress: ProgressCallback | None = None,
    ) -> DocumentMetadata:
        self._progress(progress, "storing", 15, "Saving the PDF in local document storage")

        document_id = str(uuid4())
        safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(filename).stem).strip("-_") or "document"
        stored_filename = f"{document_id}_{safe_stem}.pdf"
        path = self.settings.documents_dir / stored_filename
        with log_operation(logger, "pdf_storage", document_id=document_id, size_bytes=len(content)):
            path.write_bytes(content)
        record = DocumentMetadata(document_id=document_id, title=title, category=category, filename=stored_filename)
        self.registry.save(record)
        try:
            result = self._index(record, path, progress)
            self._progress(progress, "complete", 100, "Knowledge base updated successfully")
            return result
        except Exception as exc:
            logger.exception("Indexing failed for document %s", document_id)
            record.status, record.error = "failed", str(exc)
            self.registry.save(record)
            raise RuntimeError(f"Document was saved but indexing failed: {exc}") from exc

    def ingest_path(self, path: Path, title: str | None = None, category: str = "Other") -> DocumentMetadata:
        with log_operation(logger, "cli_document_ingestion", filename=path.name, category=category):
            if path.suffix.lower() != ".pdf":
                raise ValueError("Only PDF files can be ingested.")
            existing = next((x for x in self.registry.list() if x.filename == path.name), None)
            if existing:
                return self.reindex(existing.document_id)
            record = DocumentMetadata(
                document_id=str(uuid4()), title=title or path.stem.replace("_", " ").title(),
                category=category if category in CATEGORIES else "Other", filename=path.name,
            )
            self.registry.save(record)
            return self._index(record, path)

    def _index(
        self, record: DocumentMetadata, path: Path, progress: ProgressCallback | None = None,
    ) -> DocumentMetadata:
        logger.info("process_started operation=document_indexing document_id=%s", record.document_id)
        self._progress(progress, "extracting", 25, "Extracting text and page metadata")
        with log_operation(logger, "pdf_text_extraction", document_id=record.document_id):
            pages = load_pdf(path)
        self._progress(progress, "safety", 38, "Scanning document content for unsafe instructions")
        with log_operation(logger, "document_safety_scan", document_id=record.document_id):
            record.safety_flags = DocumentGuardrail().scan(pages)
            record.safety_status = "flagged_for_review" if record.safety_flags else "passed"
            if record.safety_flags:
                logger.warning("document_safety_flags document_id=%s flags=%s", record.document_id, record.safety_flags)
        self._progress(progress, "chunking", 52, "Splitting pages into searchable knowledge chunks")
        with log_operation(logger, "document_chunking", document_id=record.document_id, page_count=len(pages)):
            chunks = chunk_documents(pages)
        if not chunks:
            raise ValueError("No text chunks could be created from this PDF.")
        ids = []
        for index, chunk in enumerate(chunks):
            chunk_id = f"{record.document_id}:{index}"
            ids.append(chunk_id)
            chunk.metadata.update({
                "document_id": record.document_id, "source": record.filename,
                "document_title": record.title, "category": record.category,
                "chunk_id": chunk_id, "uploaded_at": record.uploaded_at,
            })
        self._progress(progress, "preparing", 64, "Preparing the vector collection for this document")
        with log_operation(logger, "old_vector_removal", document_id=record.document_id):
            self.vector_store.delete(where={"document_id": record.document_id})
        try:
            self._progress(progress, "embedding", 74, "Generating embeddings and updating ChromaDB")
            with log_operation(logger, "embedding_and_vector_storage", document_id=record.document_id, chunk_count=len(chunks)):
                self.vector_store.add_documents(chunks, ids=ids)
        except Exception:
            self.vector_store.delete(where={"document_id": record.document_id})
            raise
        self._progress(progress, "indexing", 92, "Committing vectors and document metadata")
        record.status, record.page_count, record.chunk_count, record.error = "indexed", len(pages), len(chunks), None
        self.registry.save(record)
        logger.info(
            "process_completed operation=document_indexing document_id=%s pages=%d chunks=%d",
            record.document_id, len(pages), len(chunks),
        )
        return record

    def reindex(self, document_id: str) -> DocumentMetadata:
        with log_operation(logger, "document_reindex", document_id=document_id):
            record = self.registry.get(document_id)
            if not record:
                raise KeyError("Document not found.")
            path = self.settings.documents_dir / record.filename
            if not path.exists():
                raise FileNotFoundError("Stored PDF is missing.")
            record.status = "processing"
            self.registry.save(record)
            try:
                return self._index(record, path)
            except Exception as exc:
                record.status, record.error = "failed", str(exc)
                self.registry.save(record)
                raise

    def delete(self, document_id: str) -> None:
        with log_operation(logger, "document_deletion", document_id=document_id):
            record = self.registry.get(document_id)
            if not record:
                raise KeyError("Document not found.")
            with log_operation(logger, "vector_deletion", document_id=document_id):
                self.vector_store.delete(where={"document_id": document_id})
            path = self.settings.documents_dir / record.filename
            if path.exists():
                with log_operation(logger, "pdf_deletion", document_id=document_id):
                    path.unlink()
            self.registry.delete(document_id)
