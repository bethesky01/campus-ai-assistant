# Campus AI Assistant — LAB1 + LAB2 Architecture

This diagram represents the application completed through LAB3. The LAB1/LAB2 flow below is wrapped
by the following LAB3 defense-in-depth pipeline.

```mermaid
flowchart LR
    INPUT[User Input] --> IG[Input Guardrail]
    IG --> PII[Personal Data Redaction]
    PII --> ID[Prompt Injection Detector]
    ID --> ROUTER[LAB2 Query Router]
    ROUTER --> PATH[RAG / Learning Tool / General AI]
    PATH --> GG[Grounding Validation]
    GG --> OG[Pydantic Output Validation]
    OG --> SSE[Buffered SSE + Safety Metadata]
    ADMIN[Admin PDF] --> FV[File Validation]
    FV --> DS[Document Safety Scan]
    DS --> INDEX[Chunk + Embed + ChromaDB]
```

```mermaid
flowchart TB
    USER([Student]) --> UI[Student Chat UI<br/>Jinja2 + HTML/CSS/JavaScript]
    ADMIN_USER([Administrator]) --> ADMIN_UI[Admin Knowledge Base UI]

    subgraph BROWSER[Browser]
        UI -->|Question + session_id| STREAM_CLIENT[Fetch SSE Client]
        STREAM_CLIENT -->|Progressive tokens| UI
        STREAM_CLIENT -->|Tool and source metadata| UI
        ADMIN_UI
    end

    subgraph FASTAPI[FastAPI Application]
        STREAM_CLIENT -->|POST /chat/stream| CHAT_ROUTE[Chat Route]
        UI -.->|POST /chat fallback| CHAT_ROUTE
        ADMIN_UI -->|/admin endpoints| ADMIN_ROUTE[Admin Routes]

        CHAT_ROUTE --> ASSISTANT[Assistant Service]
        ASSISTANT <--> SESSION[In-memory Session Service<br/>bounded recent history]
        ASSISTANT --> ROUTER[Query Router<br/>Pydantic QueryRoute]

        ROUTER -->|Clear keywords| RULES[Deterministic Routing]
        ROUTER -->|Ambiguous query| ROUTER_LLM[Qwen3 Structured Routing]
        RULES --> DECISION{Intent + confidence}
        ROUTER_LLM --> DECISION
        DECISION -->|Below 0.65| CLARIFY[Clarification Response]

        DECISION -->|college_policy| POLICY[RAG Policy Path]
        DECISION -->|learning_resource| RESOURCE[Learning Resource Tool]
        DECISION -->|general| GENERAL[General AI Path]

        POLICY --> RETRIEVER[Semantic Retriever<br/>top-k + score-margin filtering]
        RETRIEVER --> POLICY_PROMPT[Grounded Policy Prompt<br/>context + recent history]
        POLICY_PROMPT --> POLICY_LLM[Qwen3 Answer Generation]
        RETRIEVER --> SOURCES[Document and Page Sources]

        RESOURCE --> SECTION{Requested section clear?}
        SECTION -->|Yes| SELECTOR[Deterministic Section Selector]
        SECTION -->|No| SECTION_LLM[Qwen3 + Pydantic<br/>ResourceRequest]
        SECTION_LLM --> SELECTOR
        SELECTOR --> FORMATTER[Deterministic JSON Formatter]

        GENERAL --> GENERAL_PROMPT[General Tutor Prompt<br/>not official college policy]
        GENERAL_PROMPT --> GENERAL_LLM[Qwen3 Answer Generation]

        CLARIFY --> SSE[SSE Event Stream]
        POLICY_LLM --> SSE
        SOURCES --> SSE
        FORMATTER --> SSE
        GENERAL_LLM --> SSE
        SSE -->|route → token → metadata → done| STREAM_CLIENT

        ADMIN_ROUTE --> DOCUMENT_SERVICE[Document Service]
        DOCUMENT_SERVICE --> VALIDATE[Validate PDF<br/>type, signature, size, empty file]
        VALIDATE --> EXTRACT[Page-aware PDF Extraction]
        EXTRACT --> CHUNK[Recursive Text Chunking]
        CHUNK --> INDEX[Embedding and Indexing]
        DOCUMENT_SERVICE --> REGISTRY[JSON Document Registry]
        ADMIN_ROUTE -->|List / Re-index / Delete| DOCUMENT_SERVICE
    end

    subgraph LOCAL_AI[Local AI — Ollama]
        OLLAMA_LLM[Qwen3 8B<br/>reasoning off, capped output]
        OLLAMA_EMBED[EmbeddingGemma]
    end

    subgraph LOCAL_DATA[Local Data]
        PDF_STORE[(data/documents<br/>Uploaded PDFs)]
        REGISTRY_FILE[(registry.json)]
        CHROMA[(Persistent ChromaDB<br/>campus_knowledge_base)]
        RESOURCE_JSON[(data/learning_resources<br/>Python · GenAI · Cloud<br/>Data Engineering · ML)]
    end

    ROUTER_LLM --> OLLAMA_LLM
    SECTION_LLM --> OLLAMA_LLM
    POLICY_LLM --> OLLAMA_LLM
    GENERAL_LLM --> OLLAMA_LLM
    RETRIEVER -->|Embed question| OLLAMA_EMBED
    RETRIEVER <--> CHROMA
    RESOURCE --> RESOURCE_JSON
    DOCUMENT_SERVICE <--> PDF_STORE
    REGISTRY <--> REGISTRY_FILE
    INDEX -->|Embed chunks| OLLAMA_EMBED
    INDEX --> CHROMA

    classDef ui fill:#e9f2e5,stroke:#17563f,color:#17231e;
    classDef service fill:#fffefa,stroke:#66736c,color:#17231e;
    classDef decision fill:#fff2bd,stroke:#9b7a13,color:#17231e;
    classDef ai fill:#e8e5ff,stroke:#5547a8,color:#17231e;
    classDef data fill:#e6f0ff,stroke:#3d6795,color:#17231e;
    class UI,ADMIN_UI,STREAM_CLIENT ui;
    class CHAT_ROUTE,ADMIN_ROUTE,ASSISTANT,SESSION,ROUTER,RULES,POLICY,RESOURCE,GENERAL,RETRIEVER,POLICY_PROMPT,SOURCES,SELECTOR,FORMATTER,GENERAL_PROMPT,SSE,DOCUMENT_SERVICE,VALIDATE,EXTRACT,CHUNK,INDEX,REGISTRY,CLARIFY service;
    class DECISION,SECTION decision;
    class ROUTER_LLM,SECTION_LLM,POLICY_LLM,GENERAL_LLM,OLLAMA_LLM,OLLAMA_EMBED ai;
    class PDF_STORE,REGISTRY_FILE,CHROMA,RESOURCE_JSON data;
```

## Route summary

| Route | Selected for | Primary data source | Qwen3 usage | Grounded as policy |
|---|---|---|---|---|
| College Policy RAG | Attendance, exams, placements, internships | Uploaded PDFs in ChromaDB | Generates from retrieved chunks | Yes |
| Learning Resource Tool | Roadmaps and learning plans | Local learning-resource JSON | Classifies unclear requested sections only | No |
| General AI | General explanations | Qwen3 pretrained knowledge | Generates the complete answer | No |
| Clarification | Route confidence below `0.65` | Deterministic options | Not required | No |

## Admin ingestion sequence

```mermaid
sequenceDiagram
    actor Admin
    participant UI as Admin UI
    participant API as FastAPI Admin Route
    participant DS as Document Service
    participant PDF as Local PDF Storage
    participant EG as EmbeddingGemma
    participant DB as ChromaDB
    participant REG as JSON Registry

    Admin->>UI: Select title, category, and PDF
    UI->>API: POST /admin/upload
    API->>DS: Upload and process
    DS->>DS: Validate extension, MIME, size, signature
    DS->>PDF: Save with stable document ID
    DS->>DS: Extract page text and create chunks
    DS->>EG: Embed chunks
    EG-->>DS: Vectors
    DS->>DB: Store vectors and metadata
    DS->>REG: Save indexed document metadata
    DS-->>API: Page and chunk counts
    API-->>UI: Indexed document response
    UI-->>Admin: Display success and updated library
```

## Student streaming sequence

```mermaid
sequenceDiagram
    actor Student
    participant UI as Chat UI
    participant API as POST /chat/stream
    participant SESSION as Session Service
    participant ROUTER as Query Router
    participant PATH as Selected Response Path
    participant AI as Local Ollama

    Student->>UI: Enter question
    UI->>API: Question + session ID
    API->>SESSION: Load recent messages
    API->>ROUTER: Classify with context
    ROUTER-->>API: Intent, topic, confidence
    API-->>UI: SSE route event
    API->>PATH: Execute RAG, resource, general, or clarification
    opt Qwen generation required
        PATH->>AI: Prompt or structured request
        AI-->>PATH: Generated chunks
    end
    loop For each answer chunk
        PATH-->>UI: SSE token event
    end
    PATH-->>API: Tool and source metadata
    API->>SESSION: Store user and assistant messages
    API-->>UI: SSE metadata event
    API-->>UI: SSE done event
```
