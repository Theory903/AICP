# AICP — The Agentic Control Plane

**Turn any software into a governed, auditable action surface for AI agents.**

[![CI](https://github.com/Theory903/AICP/actions/workflows/ci.yml/badge.svg)](https://github.com/Theory903/AICP/actions/workflows/ci.yml)
[![Version](https://img.shields.io/github/v/tag/Theory903/AICP?label=version&sort=semver)](https://github.com/Theory903/AICP/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-3776AB)](https://www.python.org/)
[![Rust](https://img.shields.io/badge/rust-1.75+-dea584)](https://www.rust-lang.org/)
[![Tests](https://img.shields.io/badge/tests-1224%20passing-brightgreen)](https://github.com/Theory903/AICP/actions/workflows/ci.yml)
[![Compliance](https://img.shields.io/badge/compliance-Level%205-green)](STATUS.md)
[![Schemas](https://img.shields.io/badge/schemas-23-purple)](spec/schemas/)

[Quick Start](#-quick-start) • [Install](#-install) • [Run](#-run) • [SDKs](#-sdks) • [Features](#-features) • [Docs](docs/)

---

## 🤔 What is AICP?

AICP is the **control plane for secure AI agent execution**. It gives you:

| Capability | What It Means |
|------------|---------------|
| **Typed Capabilities** | Every action has strict input/output schemas |
| **Policy Engine** | Allow, deny, or ask before any execution |
| **Approval Workflows** | Humans can approve/deny risky actions |
| **Resumable Sessions** | Sessions survive restarts |
| **Audit Trail** | Every action is logged and replayable |
| **Multi-Agent** | Orchestrator → Specialist → Worker hierarchy |
| **Workflows** | Sequential, parallel, event-driven, loops |

**Mammoth** is the shell — a beautiful TUI for interacting with AICP.

---

## 🚀 Quick Start

### One-Command Install

```bash
# Clone and install everything
git clone https://github.com/Theory903/AICP.git
cd AICP

# Install Python packages (AICP control plane)
pip install -e "packages/core[dev]" -e packages/runtime -e packages/cli

# OR: Install just the CLI
pip install aicp-cli
```

### Run the Control Plane

```bash
# Start the dev server
aicp dev

# In another terminal: execute a capability
aicp run notes.create -i '{"title": "Hello", "body": "World"}'
```

### Run Mammoth (The Shell)

```bash
cd apps/mammoth
cargo build -p mammoth-cli
./target/debug/mammoth --help

# Or run interactively
./target/debug/mammoth
```

---

## 📦 What's Included

### AICP Control Plane (Python)

```python
from aicp import AicpClient, CapabilityRegistry

# Start the server
# aicp dev

client = AicpClient("http://localhost:8000")

# List capabilities
caps = await client.list_capabilities()

# Execute a capability
result = await client.execute("notes.create", {"title": "Hello"})
```

### Mammoth Shell (Rust)

The TUI shell for operators and agents:

```bash
mammoth                    # Interactive mode
mammoth prompt "summarize this file"
mammoth --model claude "review my code"
```

### SDKs

| SDK | Status | Install |
|-----|--------|---------|
| **Python** | ✅ Full | `pip install aicp-sdk` |
| **TypeScript** | ✅ Core + Runtime + Client | `@aicp/core`, `@aicp/runtime`, `@aicp/client` |

---

## 🔌 Integrations

### Framework Adapters
- **FastAPI** — `mount_aicp(app)` adds all routes
- **Express** — `aicp_connect_express`
- **NestJS** — `aicp_connect_nestjs`

### Protocol Adapters
- **MCP Server** — Exposes AICP to MCP clients
- **MCP Adapter** — Consumes external MCP tools
- **OpenAPI** — Import from OpenAPI specs

### Agent Frameworks
- LangChain, LangGraph, CrewAI adapters

---

## 🛠️ Common Commands

```bash
# Development
aicp dev                    # Start dev server
aicp scan openapi ./api.json # Import capabilities
aicp preview <capability>   # Show capability schema

# Execution
aicp run <capability> -i 'JSON'
aicp run <capability> --yes  # Auto-approve

# Governance
aicp protect <capability>    # Require approval
aicp safe <namespace>       # Mark as safe
aicp deny <capability>      # Block entirely
aicp limit <namespace> --rpm 60  # Rate limit

# Approvals
aicp appr ls                # List pending
aicp appr ok <id>           # Approve
aicp appr no <id> --reason "..." # Deny

# Testing
pytest packages/core/tests/ -v
pytest packages/runtime/tests/ -v
```

---

## 📊 Current State

| Metric | Value |
|--------|-------|
| **Version** | 0.9.10 |
| **Python Tests** | 1038 |
| **Rust Tests** | 186 |
| **Compliance Level** | L5 (Full Orchestration) |
| **JSON Schemas** | 23 |
| **CLI Commands** | 28 |

### Feature Matrix

| Area | Status |
|------|--------|
| Capability Registry | ✅ Complete |
| Policy Engine | ✅ Complete |
| Workflow Engine | ✅ Complete |
| Approval Lifecycle | ✅ Complete |
| Multi-Agent | ✅ Complete |
| Federation | ✅ Complete |
| Learning System | ✅ Complete |
| Plugin System | ✅ Complete |
| Multi-Channel | ✅ Complete |
| Cost Tracking | ✅ Complete |

---

## 🏗️ Architecture

```
AICP/
├── spec/                    # Protocol schemas (source of truth)
├── packages/
│   ├── core/               # Domain models, validation
│   ├── runtime/            # Execution engine, services
│   └── cli/                 # 28 CLI commands
├── adapters/
│   ├── framework/           # FastAPI, Express, NestJS
│   ├── protocol/            # MCP, OpenAPI
│   └── agent/               # LangChain, LangGraph, CrewAI
├── sdks/
│   ├── python/              # aicp-sdk
│   └── typescript/           # @aicp/core, runtime, client
└── apps/
    └── mammoth/              # Rust TUI shell
```

---

## 📚 Documentation

- [Quick Start Guide](docs/guides/quickstart.md)
- [Architecture](ARCHITECTURE.md)
- [Status](STATUS.md)
- [Roadmap](ROADMAP.md)
- [API Reference](docs/reference/)

---

## 🤝 Contributing

```bash
# Development setup
git clone https://github.com/Theory903/AICP.git
cd AICP
pip install -e "packages/core[dev]" -e packages/runtime -e packages/cli

# Run tests
pytest packages/ -v

# Lint
ruff check . && ruff format --check .
```

---

## 📄 License

Apache 2.0 — see [LICENSE](LICENSE).

---

<div align="center">

**The protocol layer for the agentic web.**

[GitHub](https://github.com/Theory903/AICP) • [Issues](https://github.com/Theory903/AICP/issues) • [Discussions](https://github.com/Theory903/AICP/discussions)

</div>