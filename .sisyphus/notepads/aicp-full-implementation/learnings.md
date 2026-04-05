## 2026-04-05 — AI plane/runtime stub audit

- The requested AI plane runtime modules under `packages/runtime/src/aicp_runtime/ai/` and `packages/runtime/src/aicp_runtime/memory/` were already implemented; the live stub debt in this scope was concentrated in `packages/runtime/src/aicp_runtime/services/code_intelligence.py`.
- `CodeIntelligenceService` now provides real fallback behavior without LSP by indexing Python files with `ASTIndexer`, reusing `SymbolGraph`, building `CodeContext` from indexed focus files, resolving definitions by symbol-under-cursor, and finding Python references via AST name-load scanning.
- Added regression coverage in `packages/runtime/tests/test_code_intelligence_service.py` for context building, definition lookup, and reference lookup so future regressions in the fallback path are caught even when no LSP bridge is configured.

## 2026-04-05 — federation core implementation

- `packages/core/src/aicp/federation/federation.py` now replaces stubbed federation models with real schema-aligned types: literal root models for discovery/sync strategy, concrete federation/share/discovery models, dataclass-based `CrossOrgCapability` and `DIDAuthenticator`, a CRDT registry with internal per-entry LWW metadata, and a concrete mesh/service layer.
- Keeping `CRDTRegistry.entries` as plain user-visible values preserved compatibility with existing semantic federation tests; per-entry merge metadata now lives in a private `_entry_versions` store so `merge()` can still do LWW resolution without changing the public shape of `entries`.
- `FederationProvider` had to remain a plain ABC instead of a Pydantic model to stay compatible with `HttpFederationProvider`'s custom `__init__`; making the provider itself a `BaseModel` breaks inherited initialization in this codebase.
- Added `packages/core/tests/test_federation.py` to cover node validation, well-known serialization, CRDT put/get/merge, DID challenge/authentication, capability mesh lookups, and sync well-known discovery behavior.

## 2026-04-05 — semantic/federation stub removal

- `OpenAIEmbeddingProvider.embed()` in `packages/core/src/aicp/discovery/semantic.py` now performs a real `openai.OpenAI(...).embeddings.create(..., encoding_format="float")` call and raises a helpful `ImportError` when `openai` is not installed.
- `HttpFederationProvider` in `packages/core/src/aicp/federation/http_provider.py` now accepts `node_endpoint`, performs real `POST /v1/federation/register` and `GET /v1/federation/registry` requests with `httpx`, and returns structured error payloads when registration fails.
- Added focused regression coverage in `packages/core/tests/test_semantic_federation.py` for missing-openai fallback, OpenAI client invocation, federation registration, remote registry fetch, and no-endpoint fallback behavior.

## 2026-04-05 — T11: Full test suite validation

### Result: **737 passed, 0 failed, 0 errors** (5 deprecation warnings)

### Fixes applied:
1. **`auth.py` vs `auth/` module conflict** (fixed 3 failures): `packages/core/src/aicp/auth.py` shadowed the `auth/` package directory. Moved `auth.py` → `auth/__init__.py` and cleared stale `.pyc` cache.
2. **CLI `require_runtime_context` false negative** (fixed 2 failures): `load_project()` no longer raises when no `aicp.yaml` exists (returns defaults). Added explicit `find_config_file()` check at top of `require_runtime_context()` in `packages/cli/src/aicp_cli/context.py`.

### Conformance: 86/86 passed (L4+L5 compliance verified)

### Stub audit: 24 `pass` stubs in core + 2 in runtime — all legitimate (`@abstractmethod` bodies, `except Exception: pass` fire-and-forget, ABC method stubs). Zero production non-abstract `pass` stubs.

### Import check: `python -c "import aicp; print('core OK')"` → OK

### Files modified:
- `packages/core/src/aicp/auth/__init__.py` (was `auth.py`)
- `packages/cli/src/aicp_cli/context.py` (lines 261-280)

## 2026-04-05 — T10: aicp_cmds.rs curl removal

- `apps/mammoth/crates/mammoth-cli/src/aicp_cmds.rs` now builds an `AicpClient` from `runtime::AicpConfig::default()` and wraps async client calls with `tokio::runtime::Runtime::new()?.block_on(...)` so the existing sync CLI command signatures stay unchanged.
- The `aicp` crate only re-exports `AicpClient` and `ExecutionEnvelope`, so `AicpConfig` must still be imported from the `runtime` crate inside `mammoth-cli`.
- `run_caps`, `run_capability`, `run_appr_ls`, `run_appr_decide`, `run_logs`, and `run_status_check` now use native client methods; `delegate_aicp` remains in place for workspace-oriented `scan`, `dev`, `policy`, `map`, and `test` passthrough commands.
- `apps/mammoth/crates/aicp/src/client.rs` gained `list_history` and `health_check`; lightweight TCP-backed unit tests were added there to validate the new HTTP endpoints without adding new dev dependencies.
- Mammoth provider expansion follows existing `Provider` trait and `OpenAiCompatClient` patterns; targeted red-phase tests added first for provider detection and tool exposure.

- 2026-04-05: Mammoth Phase 2 runtime compile path succeeded with lightweight `skills.rs`, `agent.rs`, and `memory.rs` modules plus config/prompt/compact integration. Manual skill manifest parsing was sufficient because runtime has no `toml` crate dependency.
- 2026-04-05: For this Rust toolchain, test-time `std::env::set_var`/`remove_var` calls required explicit `unsafe` blocks in touched tests/helpers to keep LSP diagnostics clean on changed files.

## 2026-04-05 — Phase 3 Task 0+2+5: runtime rename + adapter_registry
- runtime crate renamed to mammoth-runtime; 7 dependent Cargo.toml files updated
- adapter_registry.rs created: ChannelAdapterRegistry, ChannelsConfig, broadcast/fanout/shutdown_all
- lib.rs updated with pub mod adapter_registry
- cargo build -p mammoth-cli clean, 3 adapter_registry tests pass

## 2026-04-05 — Phase 3 Tasks 6-9: VS Code extension scaffold

- `jest.mock('vscode', ..., { virtual: true })` factory functions are hoisted above `const` declarations by Jest's babel transform. Referencing a `const mockFn = jest.fn()` directly inside the factory causes `ReferenceError: Cannot access before initialization`. Fix: wrap in an arrow function `(...args: any[]) => mockFn(...args)` so the reference is resolved at call time, or use `function() { return mockFn.apply(null, arguments); }` for spread-arg cases.
- TypeScript strict mode with `@types/vscode` types `addEventListener` overloads: custom SSE event names like `'approval_request'` don't match `keyof EventSourceEventMap`. Fix: cast the handler as `unknown as (e: Event) => void` instead of `as EventListener` (which requires DOM lib).
- Spread arguments with `(...args: any[])` fail TS2556 when passed to `mockFn(...args)` under strict. Using `any` (no brackets) or `Function.apply` pattern avoids the spread tuple requirement.
- All 11 tests pass: MammothClient (3), MammothPanel (2), GhostTextProvider (3), ApprovalForwarder (3). `tsc --noEmit` clean.
