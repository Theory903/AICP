# AICP Architecture

## Overview

AICP (AI Capability Protocol) is a protocol and runtime model for AI-native action execution. It standardizes how AI systems discover capabilities, understand workflows, evaluate permissions, execute safely, track progress, and render outcomes.

## Design Principles

### 1. Spec-First
- `/spec` contains JSON schemas that are the source of truth
- All implementations must validate against these schemas
- Examples in `/spec/examples/` test schema compliance

### 2. Reference Implementation
- `/packages/core` and `/packages/runtime` are reference implementations
- Clean, well-documented, not the "only way"
- Adapters translate between frameworks/protocols and AICP

### 3. Adapter Architecture
- Adapters in `/adapters/` translate between systems and AICP
- Protocol adapters: HTTP, MCP, OpenAPI, GraphQL, WebSocket
- Framework adapters: FastAPI, Express, NestJS, NextJS, Spring Boot
- Agent adapters: LangChain, LangGraph, CrewAI

### 4. SDK Layering
- `/sdks/typescript` and `/sdks/python` provide language-specific SDKs
- Built on top of core packages with ergonomic APIs

### 5. MCP Integration
- `/mcp/` contains MCP server implementations
- Bridges MCP clients to AICP capabilities

## Directory Purposes

| Directory | Purpose |
|-----------|---------|
| `/spec` | Protocol schemas, examples, validation tests |
| `/docs` | Human-readable documentation |
| `/packages` | Reference implementations |
| `/sdks` | Language-specific SDKs |
| `/adapters` | Framework and protocol adapters |
| `/mcp` | MCP server implementations |
| `/examples` | Working reference applications |
| `/rfcs` | Protocol change proposals |
| `/governance` | Contribution guidelines, maintainers |
| `/tools` | Internal development tooling |

## Key Protocol Concepts

### Capability
A meaningful action the system can perform (e.g., `payments.transfer`)

### Workflow
A multi-step process made from one or more capabilities

### Policy
Rules defining what is allowed, restricted, or requires confirmation

### Execution
The actual invocation of a capability with result normalization

### Render
Metadata telling the UI how to display progress and outcomes

## Version Alignment

| Component | Version | Notes |
|-----------|---------|-------|
| Spec | 0.1.0 | Initial capability/workflow/policy |
| Python Core | 0.1.0 | Matches spec |
| Python Runtime | 0.1.0 | Matches spec |
| TypeScript SDK | 0.1.0 | Matches spec |
| MCP Server | 0.1.0 | Bridges to MCP ecosystem |

All components stay aligned initially, then can diverge if needed.
