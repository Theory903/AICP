# RFCs

> Request for Comments process for AICP protocol changes — the mechanism for evolving the Agentic Web Operating System.

---

## Overview

AICP uses RFCs (Request for Comments) for control-plane changes that affect how secure agentic work is defined, governed, executed, or supervised.

The current product framing for RFC review is:

- **AICP** is the control plane
- **Mammoth** is the primary interaction shell
- **Studio** is embedded UX inside Mammoth, not a separate primary product

That means RFCs should be evaluated not only for protocol correctness, but also for their impact on security, approvals, auditability, org automation, and Mammoth-first operator interaction.

---

## When to Submit an RFC

RFCs are **required** for:
- New capability kinds or capability families
- Policy contract changes (trust tiers, risk scoring, approval thresholds)
- Workflow model changes (parallel, loops, compensation, event-driven primitives)
- Breaking schema changes
- New transport protocol adapters
- Multi-agent hierarchy changes (orchestrator/specialist/worker/supervisor)
- Federation protocol changes (`/.well-known/aicp`, CRDT, DID)
- New planes or modules in the architecture
- Execution envelope field additions

---

## RFC Process

### 1. Create an RFC

Create a new file: `rfcs/YYYY-descriptive-title.md`

### 2. Include in RFC

```markdown
# RFC: [Title]

## Summary
[One paragraph explanation]

## Motivation
[Why is this needed? What problem does it solve?]

## Detailed Specification
[Technical details, schema changes, API changes]

## Backwards Compatibility
[Impact analysis — can existing implementations continue to work?]

## Open Questions
[Things to resolve before acceptance]

## Related RFCs
[Links to related proposals]
```

### 3. Submit as PR

- Submit as a PR for community discussion
- Address feedback from reviewers
- Iterate until consensus

### 4. Implementation

After RFC approval:
- Update schemas in `/spec/schemas/`
- Add valid/invalid examples
- Add conformance tests
- Update documentation

---

## RFC Statuses

| Status | Meaning |
|--------|---------|
| Draft | Under development, not yet proposed |
| Proposed | Submitted for review |
| Accepted | Approved for implementation |
| Implemented | Shipped in a release |
| Deprecated | Superseded by newer RFC |

---

## Accepted RFCs

| Number | Title | Status |
|--------|-------|--------|

---

## Draft RFCs

| Number | Title | Status |
|--------|-------|--------|
| 2026 | [often_follows Semantics](./2026-often-follows-semantics.md) | Draft |
| 2026 | [JSON Policy to WASM Migration](./2026-policy-wasm-migration.md) | Draft |
| 2026 | [Mammoth-First Shell, AICP Control Plane](./2026-mammoth-first-shell.md) | Draft |

---

## Protocol Invariants

Remember: `/spec` is the authoritative source. If runtime behavior and spec disagree, spec wins. RFCs must maintain backward compatibility within major versions.

---

## See Also

- [/spec/schemas/](../spec/schemas/) — JSON schema source of truth
- [/ARCHITECTURE.md](../ARCHITECTURE.md) — 11-plane system architecture
- [/MODULE_MAP.md](../MODULE_MAP.md) — Feature-to-module mapping
