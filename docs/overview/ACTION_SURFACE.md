# Action Surface

AICP Action Surface is the agent-facing surface of software.

It is not a visual UI. It is a semantic operating layer where agents can discover capabilities, understand typed inputs and outputs, see policy, pause for approval, resume safely, and receive structured outcomes.

## What it contains

- capabilities
- policies
- workflow state
- approval checkpoints
- execution results
- structured errors
- continuation hints
- audit records

## Why it exists

APIs are optimized for developers and UIs are optimized for humans. Agents need a different surface: one that is machine-readable, policy-aware, and resumable.

## Design rules

- no hidden state
- no ambiguous outcomes
- no unstructured failures
- no policy as afterthought
- no human-only assumptions

## Relationship to AICP products

- Protocol defines the contract
- Runtime executes the contract
- Connect imports existing systems into the contract
- Studio observes and governs execution on top of the contract
