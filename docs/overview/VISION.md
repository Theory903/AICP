# AICP Vision

## Title

**AICP: The Governed Action Runtime for AI Agents**

## Vision Statement

AICP exists to make software operable by agents.

Today, software has two native surfaces: APIs for developers and UIs for humans. AICP adds the third surface: Action Surfaces for agents.

That means agents can discover what actions exist, understand their exact input and output shape, know what policy applies, pause for human approval when needed, resume safely, and leave behind a structured audit trail.

AICP is not better tool calling. It is the protocol and runtime layer that makes real-world action safe, stateful, and continuable.

## What AICP solves

Three failures break agent systems in production:

- **Governance gap** — no policy, no approval, no audit
- **State gap** — no workflow memory, no resumable execution
- **Signal gap** — weak errors, no repair hints, no next-step guidance

## Product stack

- **AICP Protocol** — the open contract/spec
- **AICP Runtime** — the execution engine
- **AICP Connect** — the mapper/import layer
- **AICP Studio** — governance, observability, and ops

## Core belief

A capability is not just a callable function.
It is a governed action with typed inputs, typed outputs, policy, workflow relevance, recovery semantics, continuation hints, and auditability.

## Non-negotiables

- governance is protocol-native
- execution must be stateful
- errors must be actionable
- adoption must be easy

## Adoption wedge

AICP Connect is the onramp:

- OpenAPI → AICP
- FastAPI → AICP
- Postman → AICP
- HAR/cURL → AICP

## Long-term outcome

If AICP wins, the internet exposes three surfaces:

- APIs for developers
- UIs for humans
- AICP Action Surfaces for agents

That is the product.
