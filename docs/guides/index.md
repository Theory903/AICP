# Guides

Step-by-step guides for using AICP.

## Getting Started

1. **Installation**
   ```bash
   pip install -e ./packages/core
   ```

2. **Quick Start**
   - Register a capability
   - Execute it via the executor

3. **Run an Example**
   ```bash
   make demo-food
   ```

## Core Concepts

- [Architecture](guides/ARCHITECTURE.md) - System design
- [Technical Specification](guides/TECH_SPEC.md) - Implementation details

## Adapters

- **FastAPI** - Auto-discover routes from FastAPI apps
- **HTTP** - Execute capabilities over HTTP
- **MCP** - Bridge to MCP servers
