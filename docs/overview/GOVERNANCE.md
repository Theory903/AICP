# Governance

Governance is a first-class protocol concern in AICP.

It includes policy evaluation, approval handling, audit trails, and execution control.

## Core primitives

- policy
- approval request
- approval decision
- audit entry
- workflow state

## Policy outcomes

- allow
- deny
- ask
- require_approval
- limit

## Why it matters

Without governance, agents can act but cannot be safely controlled, inspected, or audited.

## Principles

- policy is protocol-native
- approvals are execution checkpoints
- audit is immutable
- decisions must be inspectable
- policy reasons must be structured

## Runtime responsibilities

- evaluate policy before execution
- create approval requests when needed
- pause execution while waiting on human input
- resume execution after approval or rejection
- write audit entries for important events
