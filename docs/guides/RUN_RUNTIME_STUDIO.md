# Run Runtime and Studio

> The shortest path to running the current AICP stack locally — Runtime, CLI, and Studio.

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.10+ |
| pip | Latest |

---

## 1. Install Packages

From the repository root:

```bash
pip install -e ./packages/core -e ./packages/runtime -e ./packages/cli
pip install -e ./apps/studio
pip install -e ./adapters/protocol/openapi
pip install -e ./adapters/framework/fastapi
pip install -e ./adapters/protocol/mcp
pip install -e ./adapters/importers/postman
pip install -e ./adapters/importers/har
pip install -e ./adapters/importers/curl
```

---

## 2. Start the Runtime

### File-Backed Persistence

```bash
aicp serve --host 127.0.0.1 --port 8000 --store-path ./.aicp-runtime
```

### SQLite-Backed Persistence

```bash
aicp serve --host 127.0.0.1 --port 8000 --store-backend sqlite --store-path ./.aicp-runtime/runtime.db
```

**What this does:**
- Boots the runtime application
- Enables file-backed or SQLite-backed persistence
- Exposes discovery, workflow, approval, and history routes
- Logs available endpoints

---

## 3. Use CLI Against Stored State

### List Approvals

```bash
# File-backed
aicp approvals list --store-path ./.aicp-runtime

# SQLite-backed
aicp approvals list --store-backend sqlite --store-path ./.aicp-runtime/runtime.db
```

### Decide an Approval

```bash
aicp approvals decide apr_123 \
  --decision approve \
  --approver ops@company.com \
  --reason "Approved from CLI" \
  --store-path ./.aicp-runtime
```

### View Audit History

```bash
# All history
aicp history --store-path ./.aicp-runtime

# Filter by workflow
aicp history --workflow-id wf_123 --store-path ./.aicp-runtime

# Filter by capability
aicp history --capability payments.transfer --store-path ./.aicp-runtime
```

---

## 4. Use Connect (Import Capabilities)

### OpenAPI

```bash
aicp map openapi ./api.json
```

### Postman

```bash
aicp map postman ./collection.postman_collection.json
```

### HAR

```bash
aicp map har ./session.har
```

### cURL

```bash
aicp map curl "curl 'https://api.example.com/users?limit=10'"
```

These commands emit discovered capabilities as JSON.

---

## 5. Start Studio

Studio provides a web interface for:
- Approval inbox viewing
- Approve/reject actions
- Audit history viewing
- Workflow timeline viewing
- Workflow detail pages

### Run with File-Backed Store

```bash
python -c "from studio.app import create_file_backed_studio_app; import uvicorn; uvicorn.run(create_file_backed_studio_app('./.aicp-runtime'), host='127.0.0.1', port=3000)"
```

### Open Studio

```
http://127.0.0.1:3000
```

---

## 6. Typical Local Development Loop

```
1. Start runtime: aicp serve --store-path ./.aicp-runtime
2. Generate capabilities: aicp map openapi ./api.json
3. Create workflow/approval state via examples or API
4. Inspect approvals/history via CLI
5. Inspect and act on same state via Studio
```

---

## What Exists Now

| Component | Status |
|-----------|--------|
| Capability and workflow models | Protocol-aligned |
| Governed runtime | Approval + audit services |
| Durable persistence | File-backed + SQLite |
| Connect adapters | OpenAPI, FastAPI, MCP, Postman, HAR, cURL |
| CLI commands | Mapping, approvals, history, runtime |
| Studio seed app | Server-rendered HTML |

---

## What Is Still Early

| Component | Notes |
|-----------|-------|
| Runtime persistence | File/SQLite-backed, not production database |
| Studio | Seed app, not full control-plane |
| Importer fidelity | Improving, needs richer auth semantics |
| Some flows | Reference-grade, not production-hardened |

---

## Recommended Paths

| Task | Recommended Command |
|------|---------------------|
| Protocol/runtime work | `aicp serve --store-path ...` |
| Adoption demos | `aicp map openapi`, `aicp map postman`, `aicp map har` |
| Governance demos | `aicp approvals ...`, `aicp history ...`, Studio |

---

## See Also

- [CLI_REFERENCE.md](./CLI_REFERENCE.md) — 28 CLI commands
- [HOW_TO_USE.md](./HOW_TO_USE.md) — Complete usage guide
- [/docs/overview/GOVERNANCE.md](../overview/GOVERNANCE.md) — Policy and approval details