# LAB1 architecture

For the complete visual architecture through LAB2, see
[architecture-diagram.md](architecture-diagram.md).

Campus AI Assistant is one local FastAPI application with two deliberately separate experiences.

```text
ADMIN: Upload → validate → extract pages → chunk → EmbeddingGemma → ChromaDB
STUDENT: Question → EmbeddingGemma → ChromaDB → context → Qwen3 → answer + sources
```

In LAB2, the student flow is extended without changing Admin ingestion:

```text
Question → session history → Pydantic router
                         ├─ college_policy → existing RAG + sources
                         ├─ learning_resource → local JSON tool
                         ├─ general → Qwen3 (not official policy)
                         └─ low confidence → clarification
Response → Server-Sent Events → browser UI → in-memory history
```

`POST /chat/stream` streams route, token, metadata, and completion events. Tool selection remains
explicit application code rather than an autonomous agent.

LAB3 wraps these paths with focused validation:

```text
Input → Input Guardrail → Injection Detector → Router → Selected Path
      → Grounding Check → Output Validation → Buffered SSE → Safety metadata

Admin PDF → File Validation → Extraction → Document Safety Scan
          → Chunking → EmbeddingGemma → ChromaDB
```

Uploaded PDFs remain in `data/documents`. A small atomic JSON registry records stable UUIDs,
titles, categories, filenames, processing state, pages, and chunk counts. Every Chroma chunk
contains that UUID plus title, source filename, category, page, chunk ID, and upload time.
Deleting uses the UUID filter, so unrelated vectors are untouched. Re-indexing deletes the old
UUID-matched vectors before adding a single replacement set.

Routes validate HTTP input and translate errors. Services own workflows. The `rag` package owns
extraction, chunking, retrieval, vector storage, and the grounded prompt. Ollama client construction
is centralized in `app/llm/client.py`. Nothing is automatically ingested during application startup.
