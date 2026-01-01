# AICP

AI Capability Protocol

A standard for **AI-friendly** capability-aware, workflow-aware, and policy-aware execution.

## Why AICP

AICP is designed so **even mini LLMs** can complete real-world tasks without complex reasoning.

Every response tells the AI:
- What happened (explicit status)
- What went wrong (structured errors with fix hints)
- What to do next (built-in next steps)
- Where we are (workflow state)
- If it's safe to proceed (policy)

## Key Differentiator

| Traditional Tool Calling | AICP Agentic Experience |
|------------------------|------------------------|
| AI must infer what to do | AI gets explicit next steps |
| Errors are vague | Errors include fix_hint |
| AI tracks workflow manually | State is in every response |
| AI guesses if safe | Policy is explicit |

## Features

- **Agentic-ready responses** - Every response includes `next` with suggested actions
- **Built-in fix hints** - Errors tell AI exactly how to recover
- **Workflow state** - Track where the AI is in multi-step processes
- **Typed capabilities** - Define what actions exist with full input/output schemas
- **Policy evaluation** - Enforce what is allowed, restricted, or requires confirmation
- **Smart rendering** - Tell UI how to display results (table, card, receipt, etc.)
- **Pagination & async jobs** - Normalized handling of lists and long-running tasks
- **Adapter-friendly design** - Works with HTTP, MCP, OpenAPI, GraphQL, LangChain, and more

## Repo Structure

```
aicp/
├── spec/           # Protocol source of truth (JSON schemas)
├── docs/           # Human-readable documentation
├── packages/       # Reference implementations (Python)
├── sdks/          # Language-specific SDKs (TypeScript, Python)
├── adapters/       # Framework & protocol adapters
├── mcp/           # MCP Server implementations
├── examples/      # Working reference applications
├── rfcs/         # Protocol change proposals
└── governance/    # Contribution guidelines
```

## Quick Start

See `docs/guides/quickstart.md` for installation and usage.

## Contributing

See `governance/CONTRIBUTING.md`

## License

Apache-2.0
