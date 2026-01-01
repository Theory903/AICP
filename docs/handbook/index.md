# Handbook

The AICP handbook covers the agentic experience and human-centered design principles.

## Agentic Experience

AICP is designed for AI agents to understand:
- **What** they can do (capabilities)
- **What step** they are in (workflow state)
- **What is allowed** (policy)
- **What is missing** (validation)
- **What to do next** (continuation hints)

This enables smaller models to work effectively by providing structured guidance rather than requiring them to infer everything from raw tool definitions.

## Key Principles

1. **Capability over Tool** - Rich metadata beyond just function signatures
2. **Workflow Awareness** - Agents know their current step and context
3. **Policy as First-Class** - Explicit rules, not just ad-hoc checks
4. **Structured Errors** - Errors include fix hints
5. **Explicit Next Steps** - Results include continuation guidance
