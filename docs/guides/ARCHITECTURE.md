# AICP + Mammoth Architecture

> Technical architecture for contributors — the Mammoth interaction OS, the AICP execution OS, and how they compose.

---

## Architectural Principles

| Principle | Description |
|-----------|-------------|
| **Mammoth is the interaction OS** | Every human and agent interaction goes through Mammoth channels — terminal, web, CLI, extension |
| **AICP is the execution OS** | Every side-effecting action is policy-evaluated, workflow-managed, and audited by AICP before execution |
| **Spec first** | Protocol contract defined before implementation details. `/spec` is the source of truth. |
| **Framework-agnostic core** | Core domain model must not depend on one backend framework. |
| **Thin adapters** | Adapters translate existing systems into AICP concepts, not reinvent core logic. |
| **Policy as first-class layer** | Permissions, trust tiers, and approvals are part of the schema, not post-processing. |
| **Workflow state is explicit** | Every workflow tracks current step, completed steps, missing inputs — not hidden in prompts. |
| **Fail-closed defaults** | If policy evaluation fails, deny the action. If schema validation fails, reject. |
| **Defense in depth** | Policy checked at API boundary, service layer, and data layer. |

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Mammoth: Interaction OS                      │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Terminal   │  │    Web      │  │   CLI    │  │Extension │  │
│  │   Channel   │  │  Channel    │  │ Channel  │  │ Channel  │  │
│  │ (mammoth)   │  │(mammoth     │  │(mammoth  │  │(mammoth  │  │
│  │             │  │  serve)     │  │ <cmd>)   │  │  ext)    │  │
│  └──────┬──────┘  └──────┬──────┘  └────┬─────┘  └────┬─────┘  │
└─────────┼────────────────┼──────────────┼──────────────┼────────┘
          │                │              │              │
          └────────────────┴──────────────┴──────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AICP: Execution OS                          │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Policy Evaluation Layer                      │   │
│  │  (Trust tier, risk scoring, approval gates)               │   │
│  └──────────────────────────┬───────────────────────────────┘   │
│                             │                                    │
│  ┌──────────────────────────▼───────────────────────────────┐   │
│  │                  Workflow Runtime                         │   │
│  │  (Stateful execution, compensation, resume, parallel)     │   │
│  └──────────────────────────┬───────────────────────────────┘   │
│                             │                                    │
│  ┌──────────────────────────▼───────────────────────────────┐   │
│  │                   Capability Registry                     │   │
│  │  (Store, validate, rank, discover capabilities)           │   │
│  └──────────────────────────┬───────────────────────────────┘   │
│                             │                                    │
│  ┌──────────────────────────▼───────────────────────────────┐   │
│  │                   Execution Envelope                      │   │
│  │  (allowed_next_actions, audit trail, rendered output)     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Provider Registry                              │
│  (Anthropic, OpenAI, Gemini, Ollama, OpenRouter, Groq, Mistral) │
└─────────────────────────────────────────────────────────────────┘
```

---

## Mammoth: Interaction OS

Mammoth (`apps/mammoth/`) is the unified interaction layer. It is built in Rust as a Cargo workspace with 9 crates.

### Crate Structure

```
apps/mammoth/crates/
├── aicp/          # AICP middleware (L1 complete) — AicpToolExecutor<T> wrapper
├── api/           # Provider API clients (Anthropic, OpenAI, Gemini, etc.)
├── runtime/       # Conversation runtime, config, session, channel abstraction
├── tools/         # ~18 tool implementations (bash, read_file, WebFetch, Agent, Skill…)
├── mammoth-cli/   # Terminal channel entry point — binary `mammoth`
├── server/        # Web channel backend — axum HTTP + SSE + WebSocket
├── commands/      # Slash command implementations
├── plugins/       # Plugin system
└── lsp/           # LSP integration
```

### Channel Abstraction

Each Mammoth channel implements the `Channel` trait (defined in `crates/runtime/src/channel.rs`):

```rust
pub trait Channel: Send + Sync {
    fn kind(&self) -> ChannelKind;
    fn render_text(&self, text: &str);
    fn render_tool_use(&self, name: &str, input: &serde_json::Value);
    fn render_tool_result(&self, name: &str, result: &str);
    fn prompt_approval(&self, request: &ApprovalRequest) -> ApprovalDecision;
}

pub enum ChannelKind {
    Terminal,
    Web,
    Cli,
    Extension,
}
```

### Four Channels

| Channel | Crate | Entry | Status |
|---------|-------|-------|--------|
| Terminal | `mammoth-cli` | `mammoth` | Working |
| Web | `server` | `mammoth serve` | Skeleton |
| CLI | `mammoth-cli` | `mammoth <subcommand>` | Working |
| Extension | `apps/mammoth/extension/` | `mammoth ext` | Scaffold |

### Data Flow (Terminal Channel)

```
1. User types in terminal REPL
        ↓
2. mammoth-cli parses input → ConversationRuntime
        ↓
3. AicpToolExecutor intercepts tool calls
        ↓
4. AICP policy evaluation → allow / deny / require_approval
        ↓
5. If approval required → inline terminal prompt (--yes / --no-input)
        ↓
6. Tool executes → result
        ↓
7. AICP wraps result in ExecutionEnvelope
        ↓
8. ConversationRuntime passes envelope to AI model as tool_result
        ↓
9. AI model generates next response
        ↓
10. Terminal channel renders streaming output
```

---

## AICP: Execution OS

AICP (`packages/`, `spec/`, `adapters/`) is the execution backbone.

### Main Components

#### 1. Capability Registry

Stores and serves capability definitions — the atomic semantic actions exposed to AI systems.

| Responsibility | Description |
|---------------|-------------|
| Capability discovery | Enumerate available capabilities |
| Schema validation | Validate input/output schemas against JSON schemas |
| Ranked discovery | Keyword scoring + semantic search |
| Metadata organization | Tags, categories, capability families |

**Key files:**
- `packages/core/src/aicp/capability.py` — Capability domain model
- `packages/runtime/src/aicp_runtime/services/capability_registry.py` — Registry service
- `spec/schemas/capability.schema.json` — Protocol schema

#### 2. Policy Engine

Evaluates whether an action is allowed, denied, or requires approval before execution.

| Responsibility | Description |
|---------------|-------------|
| Scope checks | Verify actor permissions |
| Trust tier evaluation | Apply baseline autonomy rules |
| Risk scoring | Compute multi-dimensional risk scores |
| Approval logic | Determine when to pause for human decision |
| Policy effects | `allow`, `deny`, `ask`, `require_approval`, `limit` |

**Key files:**
- `packages/core/src/aicp/policy.py` — Policy domain model
- `packages/runtime/src/aicp_runtime/services/policy_engine.py` — Policy evaluation service
- `spec/schemas/policy.schema.json` — Protocol schema

#### 3. Workflow Runtime

Tracks multi-step state with branching, retries, compensation, and approval checkpoints.

| Responsibility | Description |
|---------------|-------------|
| Current step tracking | Where are we in the workflow? |
| Completed steps | What has already executed? |
| Next transitions | What can happen next? |
| Missing inputs | What data is still needed? |
| Resume after approval | Continue from checkpoint after human decision |
| Compensation | Rollback completed steps on failure |

**Key files:**
- `packages/core/src/aicp/workflow.py` — Workflow domain model
- `packages/runtime/src/aicp_runtime/services/workflow_runtime.py` — Workflow execution service
- `spec/schemas/workflow.schema.json` — Protocol schema

#### 4. Execution Engine

Runs the selected capability against underlying systems with normalized results.

**Key files:**
- `packages/runtime/src/aicp_runtime/services/execution_service.py`
- `spec/schemas/execution-result.schema.json`

#### 5. Approval Service

Manages the human-in-the-loop checkpoint lifecycle.

| Responsibility | Description |
|---------------|-------------|
| Create approval request | Pause execution, create structured request |
| Route to human | Terminal channel inline, REST API, Mammoth Web dashboard |
| Resolve decision | Approve, reject, modify, delegate, escalate |
| Resume execution | Continue after approval is granted |
| Intent matching | Verify resumed action still makes sense |

#### 6. Audit Service

Immutable append-only journal of every significant event.

#### 7. Session Service

Manages execution context that persists across process restarts.

---

## Architectural Boundaries

### Package Boundaries

| Package | Rule |
|---------|------|
| `/packages/core` | Runtime-agnostic. Adapter-agnostic. Must NOT import from `/packages/runtime` or adapters. |
| `/packages/runtime` | No core domain logic. No adapter-specific logic. |
| `/adapters/` | Translate only. No business logic. No core model leakage. |
| `apps/mammoth/crates/aicp/` | AICP middleware. Wraps tool executor. Does NOT contain AICP execution logic — that lives in Python runtime. |
| `apps/mammoth/crates/server/` | Web channel backend only. No conversation logic. No AI inference in handler functions. |
| `apps/mammoth/crates/mammoth-cli/` | Terminal + CLI channel only. Thin dispatch layer. |

### Mammoth ↔ AICP Boundary

The `AicpToolExecutor<T>` in `crates/aicp/` is the boundary point:

```rust
// mammoth-cli/src/main.rs
let conversation = ConversationRuntime::new(
    client,
    AicpToolExecutor::new(tool_executor, aicp_config),
);
```

This is the only place Mammoth touches AICP directly. The rest of the conversation runtime is AICP-agnostic.

---

## Directory Structure

```
aicp/
├── spec/                          # Protocol source of truth (JSON schemas)
├── packages/
│   ├── core/                      # Protocol domain models (runtime-agnostic)
│   ├── runtime/                   # Execution engine, services, persistence
│   └── cli/                       # 28 CLI commands
├── adapters/
│   ├── protocol/                  # HTTP, MCP, OpenAPI adapters
│   ├── framework/                 # FastAPI adapter
│   ├── agent/                     # LangChain, LangGraph, CrewAI adapters
│   └── importers/                 # cURL, HAR, Postman importers
├── sdks/
│   ├── typescript/                # TypeScript SDK
│   └── python/                    # Python SDK (skeleton)
├── mcp/                           # MCP server (exposes AICP outward to MCP clients)
├── apps/
│   └── mammoth/                   # Mammoth: Interaction OS (Rust workspace)
│       ├── crates/
│       │   ├── aicp/              # AICP middleware (L1)
│       │   ├── api/               # Provider API clients
│       │   ├── runtime/           # Conversation runtime + Channel trait
│       │   ├── tools/             # Tool implementations
│       │   ├── mammoth-cli/       # Terminal + CLI channel (binary: mammoth)
│       │   ├── server/            # Web channel backend (axum)
│       │   ├── commands/          # Slash commands
│       │   ├── plugins/           # Plugin system
│       │   └── lsp/               # LSP integration
│       └── extension/             # Chrome MV3 extension (Web channel overlay)
├── examples/                      # Reference applications
├── docs/
│   ├── overview/                  # Vision, PRD, comparison, use cases
│   └── guides/                    # Architecture, MAMMOTH.md, CLI reference
└── governance/                    # Contributing guidelines
```

---

## Data Flow Example: Payment Transfer via Mammoth Terminal

```
1. User types: "Transfer ₹1000 to Rahul"
        ↓
2. Terminal channel → ConversationRuntime → AI model
        ↓
3. AI model calls tool: payment.transfer({amount: 1000, recipient: "Rahul"})
        ↓
4. AicpToolExecutor intercepts tool call
        ↓
5. AICP Policy Engine evaluates:
   - Trust tier: 2 (Trusted)
   - Risk score: {financial: 0.7, irreversibility: 0.9}
   - Effect: require_approval (threshold exceeded)
        ↓
6. Terminal channel renders inline approval prompt
   User approves: "y"
        ↓
7. Workflow Runtime steps to execution
        ↓
8. Execution Engine invokes payment.transfer
        ↓
9. AICP produces ExecutionEnvelope:
   {
     "status": "success",
     "data": { "transaction_id": "txn_..." },
     "allowed_next_actions": [{"name": "order.track", ...}],
     "rendered": "Transfer of ₹1000 to Rahul completed"
   }
        ↓
10. Audit Service logs the complete flow
        ↓
11. Terminal channel streams rendered output to user
```

---

## See Also

- [MAMMOTH.md](./MAMMOTH.md) — Mammoth architecture deep-dive (4 channels, channel trait, extension protocol)
- [VISION.md](../overview/VISION.md) — Mammoth + AICP dual OS vision
- [ACTION_SURFACE.md](../overview/ACTION_SURFACE.md) — Capability model details
- [GOVERNANCE.md](../overview/GOVERNANCE.md) — Policy and trust tier details
- [/spec/schemas/](../../spec/schemas/) — JSON schema source of truth
- [CLI_REFERENCE.md](./CLI_REFERENCE.md) — 28 CLI commands
