# Notes API — AICP Reference Example

A standard FastAPI Notes CRUD API with full AICP integration,
demonstrating the **golden path** from zero to governed agent actions.

## Quick Start

```bash
# 1. Navigate to this example
cd examples/fastapi-notes

# 2. Initialize AICP (already done — see aicp.yaml)
aicp init --app app:app

# 3. Scan your API for capabilities
aicp scan fastapi app:app

# 4. Review what AICP detected
aicp ls

# 5. Start the development server
aicp dev

# 6. Validate your config
aicp doctor
```

## What AICP Sees

From 6 FastAPI routes, AICP detects 6 capabilities:

| Route | Capability | Kind | Risk | Default Policy |
|-------|-----------|------|------|----------------|
| `GET /ping` | `ping` | query | low | allow |
| `POST /notes/` | `notes.create` | action | low | ask |
| `GET /notes/` | `notes.list` | query | low | allow |
| `GET /notes/{id}` | `notes.get` | query | low | allow |
| `PUT /notes/{id}` | `notes.update` | action | medium | ask |
| `DELETE /notes/{id}` | `notes.delete` | action | medium | require_approval |

## How Governance Works

### Default policies (from `aicp.yaml`):
- **Queries** (`GET` routes) → `allow` — agents can read freely
- **Actions** (`POST`/`PUT`) → `ask` — agent must confirm with user
- **Destructive** (`DELETE`) → `require_approval` — HITL approval queue

### Explicit rules override defaults:
```yaml
rules:
  - match: notes.delete
    effect: require_approval
    reason: "Deleting notes is irreversible"
  - match: "*.list"
    effect: allow
```

## Working with Capabilities

### Execute a capability
```bash
aicp run notes.create -i '{"title": "Hello AICP", "content": "First governed note"}'
```

### Change policy quickly
```bash
# Make notes.list always safe
aicp safe notes.list

# Require confirmation for updates
aicp ask notes.update

# Block all deletes
aicp deny notes.delete
```

### View audit logs
```bash
aicp logs
aicp logs -c notes.create
```

### Manage approvals
```bash
aicp appr ls
aicp appr ok <approval-id>
aicp appr no <approval-id> -r "Not authorized"
```

## File Structure

```
examples/fastapi-notes/
├── app.py                          # Your FastAPI app (unchanged)
├── aicp.yaml                       # AICP project config
├── aicp/
│   ├── capabilities/
│   │   ├── ping.yaml               # GET /ping → query, low risk
│   │   ├── notes.create.yaml       # POST /notes → action, low risk
│   │   ├── notes.list.yaml         # GET /notes → query, low risk
│   │   ├── notes.get.yaml          # GET /notes/{id} → query, low risk
│   │   ├── notes.update.yaml       # PUT /notes/{id} → action, medium risk
│   │   └── notes.delete.yaml       # DELETE /notes/{id} → action, medium risk, destructive
│   ├── policies/
│   │   └── protect_delete.yaml     # Require approval for delete
│   ├── workflows/                  # (empty for now)
│   └── fixtures/                   # (empty for now)
└── README.md                       # This file
```

## What Changed in Your App?

**Nothing.** Your `app.py` is exactly the same FastAPI app it was before.
AICP sits alongside it, reading its route structure and adding governance,
discovery, and audit capabilities without any code changes.

When you're ready for deeper integration, you can use the `@capability` decorator:

```python
from aicp.decorators import capability

@capability("notes.delete", risk="medium", approval="required", destructive=True)
@app.delete("/notes/{note_id}")
async def delete_note(note_id: int):
    ...
```

But the **golden path** requires zero code changes.
