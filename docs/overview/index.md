# AICP Documentation

> AICP is the governed control plane. Mammoth is the only primary interaction shell for now.

---

## Product Shape

| Layer | Role | Current product posture |
|-------|------|-------------------------|
| **Mammoth** | Operator and agent shell | Primary TUI/CLI surface for invoking, supervising, and reviewing work |
| **AICP** | Control plane | Capabilities, workflows, policy, approvals, sessions, audit, discovery |
| **Studio** | Supervision UX | Should converge into Mammoth instead of remaining a separate front door |

This doc set should be read through that lens: Mammoth is where work starts; AICP is where work is governed.

---

## Start Here

| Document | Description |
|----------|-------------|
| [Vision](./VISION.md) | The v1 product thesis: Mammoth-first interaction on top of a governed control plane |
| [PRD](./PRD.md) | Product requirements and system goals |
| [Status](../../STATUS.md) | Verified current implementation state |
| [Roadmap](../../ROADMAP.md) | Phased path to v1.0.0 |
| [Architecture](../../ARCHITECTURE.md) | 11-plane architecture and control-plane boundaries |
| [Mammoth Guide](../guides/MAMMOTH.md) | Shell-level operator/developer experience |

---

## Key Themes for v1

- **Mammoth-only interaction shell for now**
- **AICP as the secure org automation control plane**
- **Policy before side effects**
- **Approval and replay as first-class supervision primitives**
- **Studio embedded into Mammoth, not split from it**

---

## Navigation

| Area | Document set |
|------|--------------|
| Product framing | [overview/](./) |
| Operator and developer workflows | [guides/](../guides/index.md) |
| Protocol and schemas | [spec/](../spec/) |
| API and shell reference | [reference/](../reference/index.md) |
| Examples and demos | [examples/](../examples/) |

---

## Notes

- Root docs are authoritative for product positioning.
- `/spec` remains authoritative for protocol structure.
- Reference apps and clean-room study materials should be treated as inputs to Mammoth and AICP, not as separate flagship products.
