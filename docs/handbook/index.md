# Handbook

> Deep-dive conceptual documentation for understanding AICP as an agentic operating system.

---

## Agentic Experience

AICP is designed for AI agents to understand:
- **What** they can do (capabilities with typed I/O)
- **What step** they are in (workflow state)
- **What is allowed** (policy evaluation, trust tiers)
- **What is missing** (validation errors, fix hints)
- **What to do next** (`allowed_next_actions` on every response)

This enables smaller models to work effectively by providing structured guidance rather than requiring them to infer everything from raw tool definitions.

---

## Key Principles

| Principle | Description |
|-----------|-------------|
| **Capability over Tool** | Rich metadata beyond just function signatures |
| **Workflow Awareness** | Agents know current step and context |
| **Policy as First-Class** | Explicit rules, not ad-hoc checks |
| **Structured Errors** | Errors include fix hints and retry guidance |
| **Explicit Next Steps** | Results include `allowed_next_actions` |
| **Cognitive Protocols** | Domain-adapted behavior profiles |
| **11-Plane Awareness** | Agents aware of full system architecture |

---

## Cognitive Protocols

Cognitive protocols adapt AICP behavior to different operational domains:

| Protocol | Default Trust | Approval Sensitivity | Use Case |
|----------|--------------|---------------------|----------|
| UX | Tier 2 | Medium | User-facing assistants |
| SWE | Tier 3 | Low | Code execution agents |
| Ops | Tier 2 | High | DevOps automation |
| Research | Tier 3 | Low | Data analysis agents |
| Finance | Tier 1 | Very High | Financial transactions |

---

## Perception Model

AICP's Perception Plane enables agents to observe application state:
- Accessibility tree for UI element discovery
- DOM observation and mutation tracking
- Visual state capture (screenshots)
- Behavioral signal processing

---

## See Also

- [AGENTIC_EXPERIENCE.md](./AGENTIC_EXPERIENCE.md) — Complete AI-optimized design guide
- [ACTION_SURFACE.md](../overview/ACTION_SURFACE.md) — Capability model
- [GOVERNANCE.md](../overview/GOVERNANCE.md) — Policy and trust tiers
- [/ARCHITECTURE.md](../../ARCHITECTURE.md] — 11-plane architecture