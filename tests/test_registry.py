from app.config import get_settings
from app.models.schemas import DocumentMetadata
from app.services.registry_service import RegistryService


def record(identifier="doc-1"):
    return DocumentMetadata(document_id=identifier, title="Policy", category="Other", filename=f"{identifier}.pdf")


def test_registry_create_update_delete():
    path = get_settings().documents_dir / "_test_registry.json"
    registry = RegistryService(path)
    try:
        item = record(); registry.save(item)
        assert registry.get("doc-1").title == "Policy"
        item.status = "indexed"; item.chunk_count = 2; registry.save(item)
        assert len(registry.list()) == 1 and registry.get("doc-1").chunk_count == 2
        registry.save(record("doc-2")); registry.delete("doc-1")
        assert [x.document_id for x in registry.list()] == ["doc-2"]
    finally:
        path.unlink(missing_ok=True)
