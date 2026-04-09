# AICP — AI Capability Protocol

<div align="center">

**The control plane for secure, governed AI agent execution.**

Turn any software into a typed, policy-enforced, auditable action surface for AI agents.

[![CI](https://github.com/Theory903/AICP/actions/workflows/ci.yml/badge.svg)](https://github.com/Theory903/AICP/actions/workflows/ci.yml)
[![Version](https://img.shields.io/github/v/tag/Theory903/AICP?label=version&sort=semver)](https://github.com/Theory903/AICP/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-3776AB)](https://www.python.org/)
[![Rust](https://img.shields.io/badge/rust-1.75+-dea584)](https://www.rust-lang.org/)
[![Tests](https://img.shields.io/badge/tests-1001%20passing-brightgreen)](https://github.com/Theory903/AICP/actions/workflows/ci.yml)
[![Compliance](https://img.shields.io/badge/compliance-Level%205-green)](STATUS.md)

</div>

---

## Table of Contents

- [What is AICP?](#what-is-aicp)
- [Why AICP?](#why-aicp)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [SDKs & Tools](#sdks--tools)
- [Features](#features)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

---

## What is AICP?

AICP (AI Capability Protocol) is the **control plane for secure AI agent execution**. It provides a governed layer between AI agents and your actual software, ensuring every action is:

| Feature | Description |
|---------|-------------|
| **Typed** | Every capability has strict input/output schemas |
| **Policy-Enforced** | Allow, deny, or ask before any execution |
| **Approved** | Humans can approve/deny risky actions |
| **Auditable** | Complete audit trail, every action logged & replayable |
| **Resumable** | Sessions survive restarts |
| **Multi-Agent** | Orchestrator → Specialist → Worker hierarchy |

### The Problem AICP Solves

```
┌─────────────────────────────────────────────────────────────────────┐
│ WITHOUT AICP                                                        │
├─────────────────────────────────────────────────────────────────────┤
│  AI Agent ───► Execute Anything ───► No Tracking                    │
│                                                                     │
│  • Unrestricted access to your systems                             │
│  • No way to approve or deny risky actions                         │
│  • Black box - you can't see what the agent did                    │
│  • No accountability - who did what, when, why?                    │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ WITH AICP                                                           │
├─────────────────────────────────────────────────────────────────────┤
│  AI Agent ──► AICP Control Plane ──► Policy Check ──► Execute     │
│                            │                                        │
│                    ┌──────▼──────┐                                  │
│                    │   DECISION  │                                  │
│                    ├─────────────┤                                  │
│                    │ ✓ ALLOW     │  (safe, proceed)                 │
│                    │ ✗ DENY      │  (blocked)                       │
│                    │ ⏳ ASK       │  (needs approval)               │
│                    │ ⚡ LIMIT     │  (rate limited)                 │
│                    └─────────────┘                                  │
│                            │                                        │
│                    ┌──────▼──────┐                                  │
│                    │   AUDIT     │                                  │
│                    │   Complete  │                                  │
│                    │   Log       │                                  │
│                    └─────────────┘                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Why AICP?

AI agents are becoming capable of more actions, but most lack:

1. **Governance** — Agents execute without policy checks
2. **Approval Gates** — Risky actions run automatically  
3. **Audit Trail** — Can't track what the agent did
4. **Session Persistence** — Agents forget everything on restart
5. **Typed Contracts** — Every tool has different input/output
6. **Replayability** — Can't replay agent actions for debugging

AICP adds the **missing governance layer** to any AI agent implementation.

---

## Architecture

AICP follows a **11-plane architecture** for complete agentic control:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AICP ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────┤
│  Plane 0: Signal       - Event ingestion, routing                 │
│  Plane 1: Perception   - DOM, screenshots, accessibility tree     │
│  Plane 2: AI           - Planner, judge, memory, code intelligence│
│  Plane 3: Capability   - Registry, schema, discovery              │
│  Plane 4: Workflow     - Sequential, parallel, loops, subflows      │
│  Plane 5: Governance   - Policy, trust tiers, risk scoring        │
│  Plane 6: Execution    - Realtime, transactional, event-driven     │
│  Plane 7: Multi-Agent  - Orchestrator, specialist, worker         │
│  Plane 8: Federation   - CRDT, DID, cross-organization             │
│  Plane 9: Supervision  - Approval queue, replay, human-in-loop     │
│  Plane 10: Learning    - Skill mining, drift detection             │
└─────────────────────────────────────────────────────────────────────┘
```

### Project Structure

```
AICP/
├── spec/                    # Protocol schemas (JSON)
├── modules/
│   ├── aicp-core/           # Domain models, execution, policies
│   ├── aicp-runtime/        # Workflow engine, services
│   ├── aicp-cli/            # Command-line interface
│   ├── aicp-integrations/   # 36+ provider integrations
│   ├── aicp-mcp/           # MCP server adapter
│   └── aicp-extensions/    # Plugin system
├── sdks/
│   ├── python/              # Python SDK (aicp-sdk)
│   └── typescript/         # TypeScript SDK (@aicp/core)
├── adapters/
│   ├── framework/           # FastAPI, Express, NestJS
│   ├── protocol/            # MCP, OpenAPI
│   └── agent/               # LangChain, LangGraph, CrewAI
└── apps/
    └── mammoth/             # Rust TUI shell
```

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/Theory903/AICP.git
cd AICP

# Install Python packages (control plane)
pip install -e "modules/aicp-core[dev]" -e modules/aicp-runtime -e modules/aicp-cli

# OR install just the CLI
pip install aicp-cli
```

### Run the Control Plane

```bash
# Start the development server
aicp dev

# In another terminal: execute a capability
aicp run notes.create -i '{"title": "Hello", "body": "World"}'
```

### Run Mammoth (Rust TUI Shell)

```bash
cd apps/mammoth
cargo build -p mammoth-cli
./target/debug/mammoth --help

# Run interactively
./target/debug/mammoth
```

---

## Core Concepts

### Capability

A capability is a typed action an AI agent can execute:

```yaml
name: notes.create
description: Create a new note
kind: action
input:
  type: object
  properties:
    title: { type: string }
    body: { type: string }
  required: [title]
output:
  type: object
  properties:
    id: { type: string }
    created_at: { type: string }
tags: [notes, write, risk:low]
```

### Policy

Policies govern what capabilities can execute:

```yaml
policies:
  - name: protect-database
    effect: ask
    condition:
      capability_tags: [database, write]
      
  - name: allow-readonly
    effect: allow
    condition:
      capability_tags: [read, risk:low]
```

### Workflow

Multi-step execution with state tracking:

```yaml
name: user-onboarding
steps:
  - capability: user.create
  - capability: welcome-email.send
  - capability: dashboard.setup
```

---

## SDKs & Tools

### Python SDK

```python
from aicp import AicpClient, CapabilityRegistry

client = AicpClient("http://localhost:8000")

# List capabilities
caps = await client.list_capabilities()

# Execute a capability
result = await client.execute("notes.create", {"title": "Hello"})
```

### TypeScript SDK

```typescript
import { AicpClient } from "@aicp/client";

const client = new AicpClient({ baseUrl: "http://localhost:8000" });

const caps = await client.listCapabilities();
const result = await client.execute("notes.create", { title: "Hello" });
```

### CLI Commands

```bash
aicp dev              # Start dev server
aicp run <cap>       # Execute a capability
aicp ls              # List capabilities
aicp scan            # Scan for capabilities
aicp protect <cap>   # Require approval
aicp appr ls         # List pending approvals
aicp appr ok <id>   # Approve request
```

---

## Features

### ✅ Completed Features (v0.9.10)

| Feature | Status |
|---------|--------|
| Capability Registry | ✅ Complete |
| Policy Engine (Allow/Deny/Ask/Limit) | ✅ Complete |
| Workflow Engine (Sequential/Parallel/Loops) | ✅ Complete |
| Approval Lifecycle | ✅ Complete |
| Session Management (Resumable) | ✅ Complete |
| Audit Trail | ✅ Complete |
| Multi-Agent Hierarchy | ✅ Complete |
| Federation (CRDT, DID) | ✅ Complete |
| Learning System (Skill Mining) | ✅ Complete |
| Plugin System | ✅ Complete |
| Multi-Channel Support | ✅ Complete |
| Cost Tracking | ✅ Complete |

### Protocol Schemas (23)

- `capability.schema.json` — Action, query, workflow, async, batch
- `workflow.schema.json` — Sequential, parallel, fork/join, loops
- `policy.schema.json` — Allow/deny/ask/limit, trust tiers
- `execution-result.schema.json` — Canonical response envelope
- `approval-request.schema.json` — Risk assessment
- `session.schema.json` — Resumable sessions
- And 17 more...

---

## Development

### Running Tests

```bash
# Python tests
pytest modules/aicp-core/tests/ -v
pytest modules/aicp-runtime/tests/ -v
pytest modules/aicp-cli/tests/ -v

# Rust tests
cd apps/mammoth && cargo test

# TypeScript tests
cd sdks/typescript/packages/core && npm test
```

### Linting

```bash
# Python (ruff)
ruff check . && ruff format --check .

# TypeScript
cd sdks/typescript && npm run lint
```

### Building

```bash
# Python packages
pip install -e "modules/aicp-core[dev]" -e modules/aicp-runtime -e modules/aicp-cli

# Rust (Mammoth)
cd apps/mammoth && cargo build

# TypeScript SDKs
cd sdks/typescript/packages/core && npm run build
```

---

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

```bash
# Fork and clone
git clone https://github.com/Theory903/AICP.git
cd AICP

# Create a feature branch
git checkout -b feature/amazing-feature

# Make your changes and test
pytest modules/ -v

# Commit and push
git commit -m "Add amazing feature"
git push origin feature/amazing-feature

# Open a Pull Request
```

---

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

---

## Resources

- [Documentation](docs/)
- [API Reference](docs/reference/)
- [Architecture Details](ARCHITECTURE.md)
- [Current Status](STATUS.md)
- [Roadmap](ROADMAP.md)

---

<div align="center">

**The missing governance layer for AI agents.**

[GitHub](https://github.com/Theory903/AICP) • [Issues](https://github.com/Theory903/AICP/issues) • [Discussions](https://github.com/Theory903/AICP/discussions)

</div>