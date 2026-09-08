# LAB1 concepts

- **LLM:** a language model that generates text. This lab runs Qwen3 locally with Ollama.
- **Embedding:** a numeric representation that places semantically similar text near each other.
- **EmbeddingGemma:** the local Ollama embedding model used for documents and questions.
- **Semantic search:** finds content by meaning rather than exact keyword matches.
- **Vector database:** stores embeddings and associated text/metadata for similarity lookup.
- **ChromaDB:** the local, persistent vector database used by this project.
- **Chunking:** splits long pages into overlapping passages. Smaller passages improve retrieval focus;
  overlap reduces the chance of losing meaning at a boundary.
- **RAG:** retrieval-augmented generation retrieves relevant chunks before asking the LLM to answer.
- **Prompt grounding:** directs the model to use retrieved evidence only and admit missing evidence.
- **Source attribution:** exposes the real document title and page attached to retrieved chunks.

Admin ingestion is separate from chat because parsing and embedding documents is expensive and only
needed when the knowledge base changes. Chat embeds just the question and searches existing vectors.

Grounding reduces hallucination risk; it cannot make hallucination impossible. Retrieval may miss a
relevant passage, extracted text may be flawed, and an LLM can still misinterpret supplied context.
Users should verify consequential answers against the cited policy pages.

## LAB2 concepts

- **Tool:** a named, bounded function. The learning-resource tool reads structured local JSON.
- **Routing:** classifies a question before selecting RAG, a tool, or general AI.
- **Structured output:** asks Qwen3 to return fields validated as `QueryRoute`, avoiding string parsing.
- **Pydantic:** validates route intent, topic, and confidence (`0` through `1`).
- **Confidence and clarification:** ambiguous routes below `0.65` ask the user to clarify instead of guessing.
- **Streaming:** SSE sends answer tokens as they are generated, followed by source/tool metadata.
- **Session history:** recent messages are held in application memory to resolve follow-ups. History is
  lost on restart and is not suitable as production persistence.

Explicit routing is preferable here because students can trace Question → Route → Tool → Response.
An autonomous agent would add control-flow complexity without improving these three fixed paths.

## LAB3 concepts

- **Input guardrail:** rejects empty, oversized, or malformed input before routing.
- **Personal-data guardrail:** redacts selected student-ID, Indian phone-number, and email patterns
  before routing, model calls, and session storage, then scans the answer again. It is an educational
  privacy control, not comprehensive data-loss prevention.
- **Injection detection:** identifies a small set of explicit prompt-override patterns. Pattern matching
  cannot detect every attack.
- **Document injection defense:** flags instruction-like text while treating every retrieved document
  as untrusted reference data, never as application instructions.
- **Grounding validation:** requires meaningful retrieved evidence and valid sources before a college
  policy response can be marked grounded.
- **Output validation:** checks that tool, grounding, safety, and source metadata are consistent.
- **Abstention:** returns an insufficient-evidence response instead of asking the model to guess.
- **Scope handling:** declines requests for unavailable real-time information such as scores or weather.
- **Boundary evaluation:** repeats known, missing, ambiguous, adversarial, source, route, and follow-up
  cases. The included evaluation is educational and not a scientific benchmark.

Generated output is buffered and validated before SSE delivery. This delays the first visible token
but prevents rejected content from being streamed before validation.
