# Research Findings → Task Mapping

> Synthesized from 5 research groups studying ~60 repos from the Agentic AI Stack.
> Status: Groups 1 ✅ and 5 ✅ complete. Groups 2-4 pending.

---

## Task 1: Fix Code Intelligence Imports (Unblocks 21 Failures)

**Problem**: `aicp_runtime.services.code_intelligence` imports `CodeContext` from `aicp.code_intelligence.models` but it's defined in `code_context.py`. Same for `CallEdge` in `symbol_graph.py`.

**Research Findings (Group 5 — RAG/Doc Intelligence)**:

| Source | Pattern | Reuse Value |
|--------|---------|-------------|
| **kreuzberg** | `ExtractionResult.code_intelligence` — extracts functions, classes, imports, symbols from 248 languages via tree-sitter | HIGH — model for what CodeContext/SymbolGraph should contain |
| **deepwiki-rs** | `CodeStructure` struct with `functions`, `classes`, `imports`, `exports`, `doc_comments` fields | HIGH — reference for CodeContext dataclass fields |
| **tree-sitter** | Query patterns for function_definition, class_definition, call_expression | HIGH — implementation for `lsp_bridge.py` |

**Action**: Fix `__init__.py` exports so `CodeContext` and `CallEdge` are importable from `aicp.code_intelligence.models`. Then flesh out the models using kreuzberg/deepwiki-rs patterns for code structure representation.

---

## Task 2: Fix Workflow Engine / Runtime Services

**Problem**: Workflow engine has state machine but some transitions may have incomplete handlers.

**Research Findings**: Pending Groups 2 (multi-agent frameworks) and 4 (observability).

**Preliminary from Group 1**: rig (Rust) has a pipeline/chain pattern with typed input→output that could inform workflow step typing.

---

## Task 3: Fix Governance Policy Engine

**Problem**: Policy evaluation may have stubs in compiled policy engine.

**Research Findings**: Pending Group 4 (observability/AI devtools — BAML, TensorZero have policy patterns).

---

## Task 4: Fix Audit/Replay/Observability

**Problem**: Audit entries may not capture full execution envelope fields.

**Research Findings**: Pending Group 4 (Langfuse, TensorZero have observability patterns).

---

## Task 5: Implement Real Federation CRDT/DID/Mesh

**Problem**: 11 stub classes in `federation.py` with `pass` bodies. Need real CRDT merge, DID auth, mesh networking.

**Research Findings**: Pending Group 2 (multi-agent frameworks — VoltAgent, Portia AI have federation patterns).

---

## Task 6: Implement Real Perception/Signal Layer

**Problem**: Perception module needs real signal processing, a11y tree parsing, behavioral signal extraction.

**Research Findings (Group 5)**:

| Source | Pattern | Reuse Value |
|--------|---------|-------------|
| **quivr** | `ProcessorRegistry` — register processors by file extension, unified `process()` API | HIGH — adapt for signal type registry |
| **quivr** | `DocumentProcessor` ABC with `extract()` and `get_metadata()` | HIGH — base class for signal processors |
| **edgequake** | Chunking strategies (fixed, semantic, recursive) | MEDIUM — for signal batching/windowing |
| **deepwiki-rs** | 4-stage pipeline: Preprocess → Research → Compose → Validate | MEDIUM — signal processing pipeline pattern |

**Action**: Build a `SignalProcessorRegistry` following quivr's pattern. Each signal type (DOM, a11y, screenshot, behavioral) gets a processor. Pipeline follows deepwiki-rs's staged pattern.

---

## Task 7: Implement Real Embedding Providers in Semantic Discovery

**Problem**: `semantic.py` has placeholder embedding logic. Need real OpenAI/Ollama providers.

**Research Findings (Group 3 — Vector/Memory Systems)**:

| Source | Pattern | Reuse Value |
|--------|---------|-------------|
| **Qdrant** | `QdrantClient(":memory:")` + `create_collection` + `query_points` | HIGH — direct storage for capability embeddings |
| **Qdrant** | `Filter(must=[FieldCondition(key="namespace", match={"value": ns})])` | HIGH — namespace-scoped semantic search |
| **LanceDB** | `table.search(vec).where("namespace=?").limit(10).to_list()` | MEDIUM — simpler alternative |
| **async-openai** (Group 1) | `client.post("/embeddings").json(&request).send().await` | HIGH — async OpenAI embeddings pattern |

**Action**: Implement `QdrantVectorStore` class in `semantic.py` wrapping qdrant-client. Add batch embedding, dimension detection, and namespace filtering. Follow async-openai's retry/backoff pattern for OpenAI API calls.

---

## Task 8: Implement Real AI Plane (Planner/Judge/Intent Router + Memory)

**Problem**: AI plane modules (planner.py, judge.py, intent_router.py) and memory store have stub implementations.

**Research Findings (Group 3 — Vector/Memory Systems)**:

| Source | Pattern | Reuse Value |
|--------|---------|-------------|
| **Cortex Memory** | Three-tier L0/L1/L2 hierarchy with weights 20%/30%/50% | HIGH — TieredRetrieval class |
| **Cortex Memory** | Event-driven incremental updates, LRU+TTL caching | HIGH — memory update pipeline |
| **Motorhead** | Session windowing: summarize when N messages reached | HIGH — EpisodicMemory windowing |
| **Motorhead** | `POST /sessions/{id}/retrieval` semantic search within session | HIGH — semantic retrieval within session |

**Research Findings (Group 2 — PENDING)**:
- MetaGPT planner patterns expected

**Preliminary from Group 5**: edgequake's entity extraction pipeline could inform the judge's evaluation pipeline.

---

## Task 9: Fix Mammoth Cargo.toml and Compilation Errors

**Problem**: 7 compilation errors. `reqwest` uses `features = ["blocking"]` but code is async. Missing `ProviderClient::MammothApi` variant. Duplicate test modules.

**Research Findings (Group 1 — Rust LLM/Agent Ecosystem)**:

| Source | Pattern | Reuse Value |
|--------|---------|-------------|
| **async-openai** | `reqwest = { version = "0.12", features = ["json", "stream", "multipart"] }` | DIRECT FIX — replace `blocking` with `json` |
| **async-openai** | `Client { http_client: reqwest::Client, config: C, backoff: ExponentialBackoff }` | HIGH — exact struct pattern for `AicpClient` |
| **async-openai** | Error enum: `ApiError`, `Reqwest(reqwest::Error)`, `StreamError` | HIGH — error handling pattern |
| **rig** | Builder pattern for client configuration | MEDIUM — alternative client construction |

**Action**: Change `Cargo.toml` features from `["blocking", "rustls-tls"]` to `["json", "rustls-tls"]`. Add missing `MammothApi` variant. Remove duplicate test modules. Follow async-openai's client struct pattern.

---

## Task 10: Replace 6 curl Shell-Outs with Native Async AicpClient

**Problem**: `aicp_cmds.rs` has 6 functions using `Command::new("curl")`. Need native async HTTP.

**Research Findings (Group 1)**:

| Source | Pattern | Reuse Value |
|--------|---------|-------------|
| **async-openai** | `client.http_client.post(url).bearer_auth(key).json(&request).send().await` | DIRECT COPY — exact replacement for curl |
| **async-openai** | `backoff::future::retry()` with exponential backoff on 429/5xx | HIGH — retry logic |
| **async-openai** | Response deserialization: `.json::<T>().await?` | HIGH — typed response parsing |

**Action**: Build `AicpClient` struct with `post()`, `get()`, `delete()` methods following async-openai. Replace each curl function with a one-liner client call.

---

## Task 11: Fix Remaining Test Failures

**Problem**: After Tasks 1-10, run full test suite and fix stragglers.

**Research Findings**: No specific research needed — this is a mop-up task.

---

## Task 12: Update STATUS.md / README.md / AGENTS.md

**Problem**: Documentation contradicts reality (LangChain/LangGraph listed as "Empty", compliance claimed as L5 when honest is L2-L3).

**Research Findings**: No specific research needed — this uses the ground truth from our codebase audit.

---

## Appendix A: Group 1 Findings (Rust LLM/Agent Ecosystem) ✅

### async-openai (Gold Reference for Tasks 9-10)
- **Repo**: https://github.com/64bit/async-openai
- **Key file**: `src/client.rs` — Full HTTP client with post/get/delete/stream, backoff retry
- **Cargo.toml**: `reqwest 0.12` with `features = ["json", "stream", "multipart"]`
- **Error handling**: `OpenAIError { ApiError, Reqwest, StreamError }` with auto-retry on 429/5xx
- **Config trait**: `url()`, `headers()`, `query()` methods for flexible endpoint config
- **Full gitingest saved**: `/Users/abhishekjha/.local/share/opencode/tool-output/tool_d5efc31740010tPXTY6gOehcpU`

### rig (Alternative Patterns)
- Builder pattern for client construction
- Pipeline/chain with typed input→output (useful for workflow engine)

### rust-bert, llm-chain, mistral.rs
- Less directly applicable to AICP's needs
- rust-bert: Local model inference patterns (if needed for offline mode)

---

## Appendix B: Group 5 Findings (RAG/Doc Intelligence) ✅

### kreuzberg
- Code intelligence extraction from 248 languages via tree-sitter
- TOON wire format (~30-50% fewer tokens than JSON)
- Directly applicable to Module 10 (Code Intelligence DB)

### edgequake
- Rust Graph RAG with entity extraction + knowledge graph
- Chunking strategies: fixed, semantic, recursive
- Graph storage with PostgreSQL AGE extension
- Applicable to Module 10 (symbol graph) and Module 11 (discovery)

### quivr
- ProcessorRegistry pattern — register processors by extension
- DocumentProcessor ABC — clean base class for extensibility
- Applicable to Module 6 (Perception/Signal Layer)

### deepwiki-rs (litho)
- 4-stage pipeline: Preprocess → Research → Compose → Validate
- CodeStructure, Function, Class, Import structs
- Language-specific processors via tree-sitter
- Applicable to Module 10 (Code Intelligence DB)

### tree-sitter
- Core AST parsing engine, 248 languages
- Query patterns for function/class/import extraction
- Foundation for all code intelligence features

---

## Appendix: LSP Diagnostic Errors Discovered During Drafting

> These were surfaced by the LSP while writing this draft. They represent additional
> type errors beyond the 21 collection errors from Task 1. Should be captured in Task 11.

| File | Error Count | Summary |
|------|-------------|---------|
| `packages/core/tests/conformance/test_schemas.py` | 6 | Dict literals passed where dataclass instances expected (RenderSpec, ContinuationSpec, PolicyRef, etc.) |
| `packages/core/src/aicp/adapters/protocol/graphql.py` | 5 | Missing `plugin_type` param, unknown `tags` param, `TransportPlugin` not a class |
| `packages/core/src/aicp/plugins/__init__.py` | 6 | `None` passed where `str` / `dict[str, Any]` expected |
| `packages/core/src/aicp/adapters/protocol/websocket.py` | 11 | websockets API mismatch (ServerConnection vs WebSocketServerProtocol), missing params |
| `packages/core/src/aicp/multi_agent/hierarchy.py` | 6 | `AgentHierarchy` missing `agents` attribute |

**Total**: 34 additional type errors to address (mostly in Wave 2-3 scope).

---

## Appendix C: Group 3 Findings (Vector/Memory Systems) ✅

### Qdrant (30k ⭐)
- **Collection + upsert + search** pattern with `PointStruct`, `VectorParams`, `Filter/FieldCondition`
- **Local mode**: `QdrantClient(":memory:")` — no server needed for dev/test
- **FastEmbed integration**: `models.Document(text=..., model=...)` for auto-embedding
- Directly applicable to **Task 7** (semantic discovery) and **Task 8** (SemanticMemory layer)
- Pattern: `client.query_points(collection, query=embedding, query_filter=Filter(...), limit=10)`

### LanceDB (9.8k ⭐)
- **Simpler alternative** — embedded, file-backed, no server
- `table.search(vector).where("namespace = 'payments'").limit(10).to_list()`
- `get_embedding_function("sentence-transformers", "all-MiniLM-L6-v2")` — pluggable providers
- Good alternative to Qdrant for local/dev mode

### Motorhead (911 ⭐)
- **Session-based memory API**: `GET/POST/DELETE /sessions/{id}/memory`
- **Windowing**: `MOTORHEAD_MAX_WINDOW_SIZE=12` — when window fills, LLM summarizes oldest half
- **Semantic retrieval**: `POST /sessions/{id}/retrieval { "text": "..." }`
- Directly applicable to **Task 8** EpisodicMemory layer
- Pattern: `SessionMemoryManager.add_message()` → auto-summarize when window full

### Cortex Memory (230 ⭐) — BEST MATCH FOR TASK 8
- **Three-tier hierarchy**: L0 (~100 tokens, 20% weight), L1 (~500-2000 tokens, 30% weight), L2 (full, 50% weight)
- **Virtual FS URI scheme**: `cortex://session/{id}/timeline/{date}/{time}.md`
- **Qdrant integration** for vector search with `search("cortex-memory").query(embedding).filter(...)`
- **Event-driven incremental updates**: L0/L1 auto-sync when L2 changes
- **LLM result caching**: LRU + TTL
- Benchmark: 68.42% on LoCoMo10, 11x fewer tokens than alternatives
- Applicable to **Task 8** (TieredRetrieval class, VectorStore abstraction)

### pgvecto.rs (2.2k ⭐)
- **SQL vector ops**: `embedding <=> query_embedding` (cosine), `<->` (euclidean), `<#>` (dot product)
- **HNSW index**: `CREATE INDEX USING hnsw (embedding vector_cosine_ops)`
- Applicable if AICP uses Postgres as backend (currently SQLite)

### Key Reusable Patterns for AICP

| Pattern | Source | Target | LOC |
|---------|--------|--------|-----|
| QdrantVectorStore class | qdrant-client | `discovery/semantic.py` | ~50 |
| Qdrant search with filter | qdrant-client | `discovery/semantic.py` | ~30 |
| LanceDB fallback store | lancedb | `memory/store.py` | ~40 |
| Session memory + windowing | motorhead | `memory/store.py` | ~60 |
| Three-tier retrieval | cortex-mem | `memory/store.py` | ~80 |

---

## Appendix D-E: Pending (Groups 2, 4)

### Group 2: Multi-Agent Frameworks — PENDING
- MetaGPT, Portia AI, SuperAGI, VoltAgent, AutoAgents
- Expected findings for: Tasks 5 (federation), 8 (AI plane)

### Group 4: Observability/AI DevTools — PENDING
- Langfuse, TensorZero, BAML, Agenta
- Expected findings for: Tasks 3 (governance), 4 (audit)

### Group F: OpenHands ("open claw") — PENDING
- Expected findings for: Tasks 5-8 (federation, perception, embedding, AI plane)
