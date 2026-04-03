# CLI Reference

> Complete command reference for the AICP command-line interface — 28 commands for bootstrapping, governance, execution, and runtime management.

---

## The Core Lifecycle

Most applications follow a simple 4-step path via the CLI:

```
1. bootstrap → Scan app, create YAML capability definitions
2. preview  → Understand how agents see each capability
3. protect  → Add approval requirements to risky actions
4. dev      → Run the engine in front of your application
```

---

## Installation

```bash
# Install from source
pip install -e ./packages/cli

# Or install all packages
pip install -e "packages/core[dev]" -e packages/runtime -e packages/cli
```

---

## Commands

### Setup and Scaffolding

#### `aicp bootstrap <adapter> <module:app>`

The fastest way to onboard an application. Combines init, scan, export, and doctor into a single command.

```bash
# Bootstrap a FastAPI server
aicp bootstrap fastapi src.main:app

# Bootstrap an OpenAPI spec
aicp bootstrap openapi ./api.json

# Bootstrap with custom output directory
aicp bootstrap fastapi src.main:app --output-dir ./aicp-capabilities
```

**Behavior:**
- Auto-creates directories (`aicp/capabilities/`, `aicp/policies/`)
- Inspects routing layer, extracts schemas
- Tags destructive actions as `[destructive]`
- Warns if destructive actions are left unprotected

---

#### `aicp init`

Sets up an empty AICP workspace with the required file structure.

```bash
aicp init
```

**Creates:**
- `aicp.yaml` — Core project configuration
- `aicp/capabilities/` — Where API contracts live
- `aicp/policies/` — Where governance policies live

---

#### `aicp scan <adapter> <module:app>`

Passively inspects a running application, deduces inputs/outputs, exports to YAML.

```bash
# Scan a FastAPI app
aicp scan fastapi src.main:app

# Scan and output to specific directory
aicp scan fastapi src.main:app --output-dir ./my-capabilities
```

---

### Validation and Governance

#### `aicp preview <capability_name>`

Rich formatted viewer showing how agents see each capability and what policy applies.

```bash
# Preview a specific capability
aicp preview payments.transfer

# Preview with verbose policy details
aicp preview payments.transfer --verbose

# List all capabilities
aicp preview --list
```

**Output includes:**
- Extracted input/output schemas
- Applied tags (`[destructive]`, `[high-risk]`)
- Effective policy (`allow`, `ask`, `require_approval`, `deny`)
- Risk score dimensions

---

#### `aicp doctor`

Gatekeeper command that rigorously verifies configurations before production.

```bash
# Run all checks
aicp doctor

# Run specific check
aicp doctor --check security
aicp doctor --check hygiene
aicp doctor --check integrity
```

**Checks:**
- **Security**: Ensures destructive endpoints are not openly allowed
- **Hygiene**: Missing descriptions, empty schemas, invalid types
- **Integrity**: Unsafe wildcards (`**`), orphaned logic

---

#### `aicp protect <capability_name>`

Direct shortcut to mandate human approval for a capability.

```bash
# Require approval for a capability
aicp protect payments.transfer

# Require approval with custom reason
aicp protect payments.transfer --reason "High-value transfer requires approval"
```

**Effect:** Forces capability into approval loop (`ask` or `require_approval`)

---

#### `aicp limit <pattern>`

Safeguard endpoints computationally with rate limits.

```bash
# Add rate limit to reading operations
aicp limit "users.read.*" --rpm 60

# Add rate limit with burst
aicp limit "orders.*" --rpm 100 --burst 20

# Remove rate limit
aicp limit "users.read.*" --remove
```

---

### Runtime and Execution

#### `aicp serve`

Starts the AICP runtime server with governed execution and persistence.

```bash
# Start with file-backed persistence
aicp serve --host 127.0.0.1 --port 8000 --store-path ./.aicp-runtime

# Start with SQLite-backed persistence
aicp serve --host 127.0.0.1 --port 8000 --store-backend sqlite --store-path ./runtime.db

# Start with custom capabilities directory
aicp serve --capabilities-dir ./my-capabilities
```

**Exposes:**
- Discovery endpoints
- Workflow management
- Approval endpoints
- Audit history

---

#### `aicp dev`

Starts AICP in development mode with live reload.

```bash
# Standard dev mode
aicp dev

# Custom port
aicp dev --port 8080

# With verbose logging
aicp dev --verbose
```

---

#### `aicp execute <capability_name>`

Execute a capability directly from CLI.

```bash
# Execute with arguments
aicp execute payments.transfer --args '{"amount": 100, "recipient": "rahul"}'

# Execute with approval (--yes to auto-approve)
aicp execute payments.transfer --args '{"amount": 100}' --yes

# Execute with session context
aicp execute orders.place --args '{"cart_id": "cart_123"}' --session sess_abc
```

---

### Capability Mapping

#### `aicp map openapi <file>`

Import OpenAPI spec as AICP capabilities.

```bash
# Import OpenAPI spec
aicp map openapi ./api.json

# Output to file
aicp map openapi ./api.json -o ./capabilities.json
```

---

#### `aicp map postman <file>`

Import Postman collection as AICP capabilities.

```bash
aicp map postman ./collection.postman_collection.json
```

---

#### `aicp map har <file>`

Import HAR (HTTP Archive) as AICP capabilities.

```bash
aicp map har ./session.har
```

---

#### `aicp map curl <command>`

Import cURL command as AICP capability.

```bash
aicp map curl "curl 'https://api.example.com/users?limit=10'"
```

---

### Approvals

#### `aicp approvals list`

List pending approval requests.

```bash
# List all pending approvals
aicp approvals list

# List approvals for specific session
aicp approvals list --session-id sess_abc

# List with filtering
aicp approvals list --status pending --capability payments.transfer
```

---

#### `aicp approvals decide <approval_id>`

Decide on an approval request.

```bash
# Approve
aicp approvals decide apr_123 --decision approve --approver ops@company.com --reason "Verified transaction"

# Reject
aicp approvals decide apr_123 --decision reject --approver ops@company.com --reason "Suspicious activity"

# Modify (with changed arguments)
aicp approvals decide apr_123 --decision modify --approver ops@company.com --reason "Changed amount" --modify-args '{"amount": 500}'
```

---

#### `aicp approvals watch`

Watch for new approval requests (long-running).

```bash
# Watch with polling
aicp approvals watch

# Watch with custom interval
aicp approvals watch --interval 5
```

---

### History and Audit

#### `aicp history`

View audit history.

```bash
# List recent history
aicp history

# Filter by workflow
aicp history --workflow-id wf_123

# Filter by capability
aicp history --capability payments.transfer

# Filter by status
aicp history --status success

# Limit results
aicp history --limit 50
```

---

#### `aicp history show <execution_id>`

Show detailed execution record.

```bash
aicp history show exec_abc123
```

---

### Workflow Management

#### `aicp workflows list`

List workflows.

```bash
aicp workflows list

# Filter by status
aicp workflows list --status running
aicicp workflows list --status completed
```

---

#### `aicp workflows show <workflow_id>`

Show workflow details.

```bash
aicp workflows show wf_abc123

# Show with step details
aicp workflows show wf_abc123 --steps
```

---

#### `aicp workflows resume <workflow_id>`

Resume a paused workflow.

```bash
aicp workflows resume wf_abc123
```

---

### Discovery

#### `aicp discover`

Discover capabilities from runtime.

```bash
# List all capabilities
aicp discover

# Search by name pattern
aicp discover --pattern "payments.*"

# Search by tag
aicp discover --tag finance

# Search with query
aicp discover --query "transfer money"
```

---

### Utility Commands

#### `aicp version`

Show version information.

```bash
aicp version
```

---

#### `aicp doctor`

See [Validation and Governance](#validation-and-governance) section.

---

#### `aicp config`

Show current configuration.

```bash
# Show all config
aicp config

# Show specific section
aicp config runtime
aicp config capabilities
```

---

## Global Options

| Option | Description |
|--------|-------------|
| `--help` | Show help message |
| `--verbose` | Enable verbose output |
| `--output-format` | Output format (`json`, `yaml`, `table`) |
| `--store-path` | Path to runtime store |
| `--store-backend` | Store backend (`file`, `sqlite`) |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | Capability not found |
| 4 | Policy denied |
| 5 | Approval required |

---

## See Also

- [HOW_TO_USE.md](./HOW_TO_USE.md) — Complete usage guide
- [ARCHITECTURE.md](./ARCHITECTURE.md) — System design for contributors
- [RUN_RUNTIME_STUDIO.md](./RUN_RUNTIME_STUDIO.md) — Running runtime and Studio
- [/docs/overview/GOVERNANCE.md](../overview/GOVERNANCE.md] — Policy and approval details