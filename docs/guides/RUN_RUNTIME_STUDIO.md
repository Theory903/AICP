# Run Runtime + Studio

This is the shortest path to running the current AICP stack locally:

- `AICP Runtime` for governed execution and persistence
- `AICP CLI` for discovery, mapping, approvals, and history
- `AICP Studio` for approval and workflow visibility

This runbook reflects what actually exists in the repository now.

## What You Need

- Python `3.10+`
- the repo checked out locally
- dependencies installed in editable mode for the packages you want to use

## 1. Install The Current Local Packages

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

If you want one-off test-style execution without editable installs, you can also use `PYTHONPATH`, but editable installs are the cleaner operator path.

## 2. Start The Runtime In Durable Mode

Use a file-backed store so workflows, approvals, and audit history survive restarts:

```bash
aicp serve --host 127.0.0.1 --port 8000 --store-path ./.aicp-runtime
```

Use SQLite-backed state when you want a single durable database file instead:

```bash
aicp serve --host 127.0.0.1 --port 8000 --store-backend sqlite --store-path ./.aicp-runtime/runtime.db
```

What this does now:

- boots the runtime app
- enables file-backed persistence via `FileRuntimeStore`, or sqlite-backed persistence via `SqliteRuntimeStore`
- exposes discovery, workflow, approval, and history routes

## 3. Use The CLI Against Stored State

The CLI can already inspect and operate on persisted governance state using the same store path.

### View approvals

```bash
aicp approvals list --store-path ./.aicp-runtime
```

SQLite-backed path:

```bash
aicp approvals list --store-backend sqlite --store-path ./.aicp-runtime/runtime.db
```

### Decide an approval

```bash
aicp approvals decide apr_123 \
  --decision approved \
  --approver ops@company.com \
  --reason "Approved from local runbook" \
  --store-path ./.aicp-runtime
```

### View audit history

```bash
aicp history --store-path ./.aicp-runtime
```

SQLite-backed path:

```bash
aicp history --store-backend sqlite --store-path ./.aicp-runtime/runtime.db
```

### Filter audit history by workflow

```bash
aicp history --workflow-id wf_123 --store-path ./.aicp-runtime
```

## 4. Use Connect From The CLI

The current zero-code ingestion paths exposed from the CLI are:

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

These commands emit discovered capabilities as JSON so you can inspect or redirect them into files.

## 5. Start Studio

Studio is still a thin seed app, but it is already useful for:

- approval inbox viewing
- approve/reject actions
- audit history viewing
- workflow timeline viewing
- workflow detail page

Run it with the same runtime store:

```bash
python -c "from studio.app import create_file_backed_studio_app; import uvicorn; uvicorn.run(create_file_backed_studio_app('./.aicp-runtime'), host='127.0.0.1', port=3000)"
```

This assumes `aicp-studio` is installed in the active environment.

Today, the seed Studio app ships with the file-backed helper path. For the smoothest Studio walkthrough, use the file-backed runtime mode. SQLite is now supported in the runtime and CLI, but Studio does not yet ship a dedicated sqlite boot helper.

Then open:

```text
http://127.0.0.1:3000
```

## 6. Current Operating Model

Today, the most realistic local loop is:

1. start runtime with `--store-path`
2. generate or inspect capabilities with `aicp map ...`
3. use the runtime and examples to create workflow/approval state
4. inspect approvals/history via CLI
5. inspect and act on the same state via Studio

## What Is Real Today

- protocol-aligned capability and workflow models
- governed runtime with approval and audit services
- durable file-backed and sqlite-backed runtime stores
- Connect packages for OpenAPI, FastAPI, MCP, Postman, HAR, and cURL
- CLI commands for mapping, approvals, history, and runtime serving
- thin Studio control plane

## What Is Still Early

- runtime persistence is early-stage file/sqlite backed, not production database backed
- Studio is server-rendered HTML, not a full control-plane app yet
- importer fidelity is improving, but still needs richer auth and request semantics over time
- some runtime flows are still reference-grade rather than production-hardened

## Recommended Local Paths

- For protocol/runtime work: start with `aicp serve --store-path ...`
- For adoption wedge demos: use `aicp map openapi`, `aicp map postman`, `aicp map har`, and `aicp map curl`
- For governance demos: use `aicp approvals ...`, `aicp history ...`, and Studio together
