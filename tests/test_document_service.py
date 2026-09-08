from shutil import copyfile

from app.config import get_settings
from app.models.schemas import DocumentMetadata
from app.services.document_service import DocumentService
from app.services.registry_service import RegistryService


class FakeVectorStore:
    def __init__(self): self.documents = []; self.delete_calls = []
    def delete(self, where):
        self.delete_calls.append(where)
        document_id = where["document_id"]
        self.documents = [doc for doc in self.documents if doc.metadata["document_id"] != document_id]
    def add_documents(self, documents, ids): self.documents.extend(documents)


def test_index_metadata_reindex_without_duplicates_and_delete():
    settings = get_settings()
    source = settings.documents_dir / "demo_attendance_policy.pdf"
    path = settings.documents_dir / "_test_service.pdf"
    registry_path = settings.documents_dir / "_test_service_registry.json"
    copyfile(source, path)
    registry = RegistryService(registry_path)
    vectors = FakeVectorStore()
    service = DocumentService(registry=registry, vector_store=vectors)
    record = DocumentMetadata(document_id="stable-id", title="Attendance", category="Attendance", filename=path.name)
    registry.save(record)
    try:
        first = service.reindex(record.document_id)
        assert first.page_count == 1 and first.chunk_count >= 1
        assert first.safety_status == "passed" and first.safety_flags == []
        assert all(doc.metadata["document_id"] == "stable-id" for doc in vectors.documents)
        assert all(doc.metadata["page"] == 1 for doc in vectors.documents)
        first_count = len(vectors.documents)
        service.reindex(record.document_id)
        assert len(vectors.documents) == first_count
        service.delete(record.document_id)
        assert not path.exists() and not vectors.documents and registry.get(record.document_id) is None
    finally:
        path.unlink(missing_ok=True)
        registry_path.unlink(missing_ok=True)
