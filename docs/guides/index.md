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

4. **Run the current platform stack**
   - [Run Runtime + Studio](RUN_RUNTIME_STUDIO.md)

## Complete Usage Guide

- **[Complete How-To Guide](HOW_TO_USE.md)** - All features with code examples:
  - Authentication (API Key, Basic, Bearer, OAuth2)
  - Variable substitution (.env files)
  - Capability registry and tag-based search
  - Execution and streaming
  - Plugin architecture
  - Security (rate limiting, key rotation, audit signing)
  - Multi-tenancy with quotas
  - Reliability (retry, circuit breaker)
  - Observability (logging, metrics, tracing)
  - Notifications (webhooks, Slack, email)
  - Secrets management (Vault, AWS)
  - Redis caching
  - Production API (versioning, health checks)

## Core Concepts

- [Architecture](ARCHITECTURE.md) - System design
- [Technical Specification](TECH_SPEC.md) - Implementation details

## Adapters

- **FastAPI** - Auto-discover routes from FastAPI apps
- **HTTP** - Execute capabilities over HTTP
- **WebSocket** - Real-time streaming execution
- **SSE** - Server-Sent Events streaming
- **GraphQL** - GraphQL-based execution
- **MCP** - Bridge to MCP servers
- **OpenAPI / Postman / HAR / cURL** - Import existing surfaces into governed capabilities
