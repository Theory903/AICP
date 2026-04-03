# Platform Demo

> The cleanest way to understand what AICP can do as a product stack — Runtime, Connect, CLI, and Studio working together.

---

## What This Demo Proves

The platform demo is built around a payment transfer flow that:

1. Defines agent-usable capabilities
2. Runs through the runtime workflow layer
3. Triggers policy-driven approval
4. Records approval and audit state durably
5. Exposes that state in CLI and Studio

This is the shortest path to seeing AICP as a governed runtime platform.

---

## Demo Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   CLI       │────>│   Runtime   │────>│   Studio    │
│ (operator)  │     │ (governed)  │     │ (control)   │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │  Connect    │
                   │ (import)    │
                   └─────────────┘
```

---

## Step 1: Start the Runtime

```bash
aicp serve --host 127.0.0.1 --port 8000 --store-path ./.aicp-runtime
```

This creates a file-backed runtime using `FileRuntimeStore`.

---

## Step 2: Run the Payment Demo

```bash
PYTHONPATH="packages/core/src:packages/runtime/src:examples/payment-transfer/src" \
python -m payment_transfer.platform_demo
```

**What it does:**
- Creates a runtime workflow
- Triggers `require_approval` policy on high-value transfer
- Creates an approval request
- Records audit events
- Approves the request
- Resumes the workflow to completion

---

## Step 3: Inspect via CLI

```bash
# List approvals
aicp approvals list --store-path ./.aicp-runtime

# View audit history
aicp history --store-path ./.aicp-runtime

# Filter by workflow
aicp history --workflow-id <workflow_id> --store-path ./.aicp-runtime
```

---

## Step 4: Open Studio

```bash
python -c "from studio.app import create_file_backed_studio_app; import uvicorn; uvicorn.run(create_file_backed_studio_app('./.aicp-runtime'), host='127.0.0.1', port=3000)"
```

Open `http://127.0.0.1:3000` to:
- View approval inbox
- Approve/reject pending requests
- Inspect audit history
- Open workflow detail pages

---

## Step 5: Show Connect

The CLI supports multiple import paths:

```bash
# Import OpenAPI spec
aicp map openapi ./api.json

# Import Postman collection
aicp map postman ./collection.postman_collection.json

# Import HTTP Archive
aicp map har ./session.har

# Import cURL command
aicp map curl "curl 'https://api.example.com/users?limit=10'"
```

This demonstrates the adoption wedge: existing surfaces can be converted into governed capabilities without rebuilding.

---

## What to Say in a Demo

The simplest truthful framing:

| Layer | Role |
|-------|------|
| **Protocol** | Defines the contract |
| **Runtime** | Executes with governance and durability |
| **Connect** | Imports existing systems into capabilities |
| **Studio** | Gives operators a control plane |

And the payment flow proves the hardest parts:
- Action selection
- Policy checkpoint
- Approval request
- Approval decision
- Workflow resume
- Audit trail

---

## Current Reality

**What is real now:**
- Governed runtime flow
- Durable file-backed state
- Approval and audit services
- CLI governance commands
- Connect importers and mappers
- Studio seed app

**What is still early:**
- Database-backed persistence
- Richer auth metadata in importers
- Studio polish and replay UX
- Broader runtime configuration

---

## See Also

- [RUN_RUNTIME_STUDIO.md](../guides/RUN_RUNTIME_STUDIO.md] — Detailed runtime setup
- [CLI_REFERENCE.md](../guides/CLI_REFERENCE.md] — CLI commands
- [USE_CASES.md](../overview/USE_CASES.md] — Payment transfer use case