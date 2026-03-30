# Platform Demo

This is the cleanest way to understand what AICP can do right now as a product stack rather than as isolated parts.

It ties together:

- `AICP Runtime` for governed execution and durable state
- `AICP Connect` for importing existing systems into capabilities
- `AICP CLI` for operator and ingestion workflows
- `AICP Studio` for approvals, audit, and workflow visibility
- `examples/payment-transfer` as the flagship governed action demo

## What This Demo Proves

The current platform demo is built around a payment transfer flow that:

1. defines agent-usable capabilities
2. runs through the runtime workflow layer
3. triggers policy-driven approval
4. records approval and audit state durably
5. exposes that state in CLI and Studio

This is the shortest path to seeing AICP as a governed runtime platform.

## 1. Start The Runtime In Durable Mode

From the repository root:

```bash
aicp serve --host 127.0.0.1 --port 8000 --store-path ./.aicp-runtime
```

This creates a file-backed runtime using the current `FileRuntimeStore` implementation.

## 2. Run The Flagship Payment Demo

Run the platform-backed payment transfer demo:

```bash
PYTHONPATH="packages/core/src:packages/runtime/src:examples/payment-transfer/src" \
python -m payment_transfer.platform_demo
```

What it does:

- creates a runtime workflow
- triggers `ASK` policy on a high-value transfer
- creates an approval request
- records audit events
- approves the request
- resumes the workflow to completion

## 3. Inspect Governance State From The CLI

List approvals:

```bash
aicp approvals list --store-path ./.aicp-runtime
```

View history:

```bash
aicp history --store-path ./.aicp-runtime
```

Filter by workflow:

```bash
aicp history --workflow-id <workflow_id> --store-path ./.aicp-runtime
```

## 4. Open Studio

Run the thin Studio seed against the same store:

```bash
python -c "from studio.app import create_file_backed_studio_app; import uvicorn; uvicorn.run(create_file_backed_studio_app('./.aicp-runtime'), host='127.0.0.1', port=3000)"
```

Then open:

```text
http://127.0.0.1:3000
```

What you can do now:

- view the approval inbox
- approve or reject pending requests
- inspect audit history
- open workflow detail pages

## 5. Show The Connect Wedge

The same repo now supports multiple ingestion paths from the CLI:

```bash
aicp map openapi ./api.json
aicp map postman ./collection.postman_collection.json
aicp map har ./session.har
aicp map curl "curl 'https://api.example.com/users?limit=10'"
```

This demonstrates the adoption wedge directly: existing surfaces can be converted into governed capabilities without rebuilding the underlying systems first.

## 6. What To Say In A Demo

The simplest truthful framing is:

- `Protocol` defines the contract
- `Runtime` executes with governance and durability
- `Connect` imports existing systems into capabilities
- `Studio` gives operators a control plane

And the payment flow proves the hardest part:

- action selection
- policy checkpoint
- approval request
- approval decision
- workflow resume
- audit trail

## Current Reality

This is a real early platform demo, not a production launch kit.

What is real now:

- governed runtime flow
- durable file-backed state
- approval and audit services
- CLI governance commands
- Connect importers and mappers
- Studio seed app

What is still early:

- database-backed persistence
- richer auth metadata in importers
- Studio polish and replay UX
- broader runtime configuration and deployment ergonomics

That is fine. The point of this demo is not to pretend the product is finished. The point is to show that AICP is now a coherent platform, not just a protocol idea.
