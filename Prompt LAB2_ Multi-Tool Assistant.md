We are continuing the existing project:

# Campus AI Assistant

LAB1 is already implemented in this SAME project folder.

LAB1 includes:

- Student chat
- Admin Knowledge Base
- PDF upload
- Document processing
- EmbeddingGemma
- ChromaDB
- RAG
- Qwen3 8B
- Source attribution
- FastAPI
- Jinja2 UI

Now implement LAB2 by EXTENDING the existing application.

IMPORTANT:

DO NOT rebuild the application.

DO NOT create a separate LAB2 folder.

DO NOT remove working LAB1 functionality.

Preserve the Admin Knowledge Base completely.

LAB2 adds:

- Query routing
- Learning Resource Tool
- General AI path
- Pydantic structured routing
- Confidence
- Clarification
- Streaming
- Session chat history

Do NOT implement LAB3 guardrails/evaluation yet.

---

# 1. DEVELOPMENT WORKFLOW

Before modifying files:

1. Inspect the complete LAB1 project.
2. Understand existing modules.
3. Identify extension points.
4. Propose the implementation plan.
5. Propose files to add/change.
6. Explain any architectural changes.
7. Wait for my approval.

After approval:

1. Implement LAB2.
2. Preserve LAB1.
3. Run all tests.
4. Test routing.
5. Test Learning Resource Tool.
6. Test RAG.
7. Test streaming.
8. Test session history.
9. Test Admin functionality.
10. Fix regressions.

Do not claim tests passed unless actually run.

---

# 2. FINAL LAB2 FLOW

The student flow becomes:

User
 ↓
Query Router
 ↓
 ├── College Policy
 │       ↓
 │      RAG
 │
 ├── Learning Resource
 │       ↓
 │   Learning Resource Tool
 │
 └── General AI
         ↓
       Qwen3

Then:

Response
 ↓
Streaming
 ↓
UI

The Admin Knowledge Base remains:

Admin
 ↓
Upload PDF
 ↓
Process
 ↓
EmbeddingGemma
 ↓
ChromaDB
 ↓
College Policy RAG

---

# 3. LOCAL AI

Continue using only:

Ollama
Qwen3 8B
EmbeddingGemma

Reuse:

app/llm/client.py

Do not introduce cloud APIs.

---

# 4. ADD ROUTING

Create:

app/routing/
├── __init__.py
└── query_router.py

The router must classify:

college_policy
learning_resource
general

Examples:

"What is the attendance requirement?"

→ college_policy

"What are placement eligibility criteria?"

→ college_policy

"Give me a roadmap for Generative AI."

→ learning_resource

"How should I learn Python?"

→ learning_resource

"What are embeddings?"

→ general

"What is machine learning?"

→ general

---

# 5. PYDANTIC STRUCTURED ROUTING

Create:

class QueryRoute(BaseModel):
    intent: Literal[
        "college_policy",
        "learning_resource",
        "general"
    ]
    topic: str
    confidence: float

Validate:

0 <= confidence <= 1

Use structured output from the LLM where practical.

Avoid fragile string parsing as the primary mechanism.

Keep the routing implementation understandable.

---

# 6. ROUTER CONFIDENCE

Add:

ROUTER_CONFIDENCE_THRESHOLD=0.65

If confidence is below the threshold:

Do not guess.

Ask clarification.

Example:

User:

"What is the requirement?"

Assistant:

"Which requirement do you mean?

• Attendance
• Examination
• Placement
• Internship"

The clarification can be generated or constructed deterministically.

---

# 7. LEARNING RESOURCE TOOL

Add:

app/tools/
├── __init__.py
├── learning_resource_tool.py
└── registry.py

Add:

data/learning_resources/

python.json
genai.json
cloud.json
data_engineering.json
machine_learning.json

Each resource should include:

- title
- description
- prerequisites
- learning stages
- recommended topics
- projects
- next steps

The tool should return structured data.

Do not create an autonomous agent.

Do not use LangGraph.

Keep the tool architecture simple.

---

# 8. TOOL REGISTRY

Create a simple registry.

It should make it obvious which tools exist.

Example:

learning_resource

The router selects the path.

The application then invokes the appropriate tool.

---

# 9. GENERAL AI

For:

intent = general

allow Qwen3 8B to answer.

However, the response must clearly identify:

Tool Used:
General AI

It must never be presented as official college policy.

---

# 10. ADMIN KNOWLEDGE BASE

Keep ALL LAB1 Admin functionality.

Admin must still be able to:

- upload PDFs
- categorize documents
- index documents
- list documents
- re-index
- delete
- view chunk counts

Do not change the Admin workflow unnecessarily.

The College Policy route must use the documents uploaded through Admin.

---

# 11. RESPONSE MODELS

Extend Pydantic schemas as useful.

Potential models:

ChatMessage
Conversation
ToolResult
SourceReference
AssistantResponse

AssistantResponse can include:

answer
tool_used
sources
grounded
metadata

Do not over-engineer.

---

# 12. SESSION CHAT HISTORY

Add:

app/services/session_service.py

Use simple in-memory sessions.

No Redis.

No PostgreSQL.

No MongoDB.

No external persistence.

The goal is to demonstrate conversational context.

Example:

User:

"What is the attendance requirement?"

Assistant:

"75%."

User:

"What happens if I fall below it?"

The system should use recent conversation context.

Document that in-memory session history is suitable for a workshop prototype, not production persistence.

---

# 13. STREAMING

Add live response streaming.

Prefer:

Server-Sent Events (SSE)

The UI should display the response progressively.

Example:

Assistant starts:

"According to the placement guidelines..."

Then the rest appears progressively.

Use current compatible Ollama/LangChain APIs.

Do not introduce WebSockets unless genuinely necessary.

If metadata cannot be streamed naturally, stream answer text and provide final source/tool metadata when the response completes.

---

# 14. UI

Preserve the LAB1 UI style.

Add:

Tool Used

Streaming

Conversation state

Example:

Tool Used:
📚 College Policy RAG

or:

Tool Used:
🧭 Learning Resource Tool

or:

Tool Used:
🤖 General AI

For RAG:

Show source cards.

For Learning Resource:

Show structured learning roadmap information.

For General AI:

Clearly identify it as General AI.

---

# 15. ROUTING EXAMPLES

These should work:

1.

"What is the minimum attendance requirement?"

→ College Policy RAG

2.

"What are placement eligibility criteria?"

→ College Policy RAG

3.

"Give me a Generative AI roadmap."

→ Learning Resource Tool

4.

"How should I learn Python?"

→ Learning Resource Tool

5.

"What are embeddings?"

→ General AI

6.

"What is machine learning?"

→ General AI

7.

"What is the requirement?"

→ Clarification

---

# 16. TESTS

Add tests for:

- QueryRoute validation
- Routing
- confidence threshold
- clarification
- Learning Resource Tool
- Tool registry
- General AI path
- RAG path
- source preservation
- session history
- streaming
- Admin functionality

All LAB1 tests must continue passing.

Separate unit and integration tests where useful.

---

# 17. DOCUMENTATION

Update:

docs/architecture.md

Show:

Admin:

Upload
→ Process
→ EmbeddingGemma
→ ChromaDB

Student:

User
→ Router
→ College RAG / Learning Resource Tool / General AI
→ Response
→ UI

Update:

docs/concepts.md

Explain:

- Tool
- Routing
- Structured output
- Pydantic
- Confidence
- Clarification
- Streaming
- Session history
- Why simple routing is preferable for this workshop to an autonomous agent

Update:

docs/workshop-notes.md

LAB2 activity:

ASK DIFFERENT QUESTIONS
→ OBSERVE ROUTING
→ OBSERVE TOOL
→ TEST LOW CONFIDENCE
→ TEST FOLLOW-UP
→ OBSERVE STREAMING

---

# 18. README

Update README.

Explain:

LAB1:
RAG + Admin Knowledge Base

LAB2:
Multi-Tool Assistant

Include example questions and expected routes.

Mention LAB3 will later add:

- guardrails
- prompt injection defense
- grounding validation
- responsible AI
- evaluation

Do not implement LAB3 yet.

---

# 19. CODE QUALITY

Maintain:

- modular architecture
- type hints
- Pydantic
- logging
- error handling
- clear services
- reusable model client

Do not create a giant router or chat service.

Students should be able to follow:

Question
→ Router
→ Tool/RAG/General
→ Response

---

# 20. FINAL DEFINITION OF DONE

LAB2 is complete when:

- LAB1 works
- Admin upload works
- Admin document management works
- RAG works
- Router works
- Pydantic structured routing works
- Learning Resource Tool works
- General AI works
- Low-confidence questions request clarification
- Tool used is visible
- RAG sources are visible
- Streaming works
- Session history works
- Tests pass where possible
- Documentation is updated
- README is updated
- No cloud APIs are used

Do NOT implement LAB3 yet.

---

# 21. MANDATORY ROUTING, FOLLOW-UP, AND RESPONSE REFINEMENTS

The following requirements are part of LAB2 itself. Implement them in addition to all LAB1 behavior.
They must not introduce LAB3 guardrails yet.

## 21.1 Hybrid routing

Do not send every query to Qwen3 merely to select a route. Use a hybrid router:

1. Deterministically recognize clear policy, learning-resource, and general-knowledge requests.
2. Call Qwen3 with the structured Pydantic routing schema only when the request is genuinely ambiguous.
3. Normalize and validate the returned route and confidence.
4. If confidence is below the configured threshold, ask a concise clarifying question instead of guessing.

Keep deterministic rules small and category-oriented; do not build a giant phrase list. Qwen3 remains the
ambiguity resolver, while the actual tool or RAG pipeline remains responsible for factual content.

Log the selected route, selection method (`deterministic` or `qwen`), normalized confidence, and elapsed
time without logging the user's full question.

## 21.2 Contextual retrieval for follow-up questions

Session memory must support short follow-ups such as `What about medical absence?`. For retrieval only,
combine the most recent relevant user question with the current question when the current wording is
context-dependent. Continue to display and answer the current user message naturally.

Bound session history by a documented maximum number of turns. Do not grow prompts indefinitely. Add
tests showing that a follow-up retrieves the intended policy while an unrelated new question is not
incorrectly attached to old context.

## 21.3 Stable browser session identifier

Generate a session identifier in the browser and retain it in `localStorage`. Send it with every chat
request and streaming reconnect so follow-up behavior survives page interactions. Validate its shape on
the server and create a safe replacement when it is absent or invalid.

## 21.4 Explicit SSE protocol

The streaming endpoint must emit named JSON events in this order:

```text
route -> token (zero or more) -> metadata -> done
```

Use an `error` event for failures and then close the stream cleanly. The UI must not parse arbitrary text
fragments as metadata. The `metadata` event must carry tool name, grounded status, safety status when
available in later labs, citations, and any clarification state as separate fields.

## 21.5 Section-aware Learning Resource Tool

The resource tool must return only the portion requested when intent is clear. Support at least:

- `prerequisites`
- `stages`
- `topics`
- `projects`
- `next_steps`
- `full_roadmap`

Pass both the selected learning topic and the original question into the tool. A question such as
`Do I need networking basics and Linux for learning cloud?` should answer the prerequisite question
directly rather than print the entire cloud roadmap.

The JSON files remain the factual source of truth. Qwen3 may choose a section for an unclear request, but
must not generate, replace, or embellish the resource facts.

## 21.6 Qwen3 only for unclear resource-section requests

Use direct section selection for obvious words such as prerequisite, stages, projects, or next steps.
Only ambiguous resource requests should call Qwen3 with a validated `ResourceRequest` schema containing
the requested section and confidence. If the structured call fails or remains low confidence, return a
short clarification listing the available sections.

Normalize percentage-style confidence values returned by a local model: values greater than 1 and no
greater than 100 are divided by 100 (for example, `85` becomes `0.85`). Reject values outside the accepted
range after normalization. Apply the same rule consistently to routing and resource-section schemas.

## 21.7 Separate response metadata

Keep these concepts independent in API models, SSE metadata, and UI badges:

```text
Tool Used
Grounded: Yes / No
Sources
Clarification Required: Yes / No
```

Do not infer grounding solely from the tool label. Policy RAG is grounded in indexed documents; the
learning tool is grounded in curated JSON; General AI is model-generated and must be labeled accordingly.

## 21.8 Required LAB2 regression tests

In addition to the original tests, verify:

- obvious requests use deterministic routing without an unnecessary router LLM call;
- ambiguous requests use structured Qwen3 routing;
- low-confidence and invalid structured outputs produce clarification safely;
- percentage-style confidence is normalized;
- follow-up retrieval uses bounded relevant context;
- session identifiers persist and invalid identifiers are replaced;
- SSE event ordering and error behavior are stable;
- clear resource-section questions do not call Qwen3;
- unclear resource-section questions use Qwen3 only for classification; and
- prerequisite questions return prerequisites rather than the complete roadmap.

LAB2 is not complete until these refinements and their tests are implemented.
