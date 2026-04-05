# RFC: Mammoth-First Shell, AICP Control Plane

## Summary

Reposition the product so that **Mammoth is the only primary interaction shell for now** and **AICP is the control plane behind it**. Studio-style supervision, replay, approval, and audit views should be treated as embedded Mammoth capabilities rather than as a separate first-class application.

## Motivation

The repository currently tells multiple overlapping stories:

- AICP as the full product and operating system
- Mammoth as a separate local coding shell
- Studio as a separate supervision console
- Nanobot and other reference apps as peer products

That fragmentation makes the roadmap, docs, and implementation priorities harder to reason about. It also weakens the security story because the boundary between shell and control plane is blurred.

This RFC establishes a simpler product model:

- **Mammoth** owns operator and agent interaction
- **AICP** owns governance, execution, workflows, approvals, sessions, audit, and discovery
- **Studio** becomes Mammoth-embedded supervision UX

## Detailed Specification

### Product boundary

1. Mammoth is the operator and agent shell.
2. AICP is the governed backend and protocol/runtime control plane.
3. Studio should no longer be documented as an independent primary surface.

### Documentation consequences

1. Root docs should describe AICP as the control plane for secure org automation.
2. Mammoth docs should describe Mammoth as the sole interaction shell for now.
3. Studio references should be rewritten as embedded Mammoth supervision UX.
4. Reference apps and clean-room study materials should be explicitly marked as inputs, not peers.

### Architecture consequences

1. Features that change what is allowed, denied, approved, executed, resumed, or audited belong in AICP.
2. Features that change how operators or agents see, invoke, inspect, review, or supervise work belong in Mammoth.
3. Approval queue, replay, workflow status, diff views, provider switching, and tool/result inspection should converge into Mammoth surfaces backed by AICP APIs.

### Security consequences

1. Mammoth-triggered work must still pass through AICP policy evaluation before side effects.
2. Approval gating and audit attribution remain control-plane responsibilities.
3. Shell affordances must not create bypass paths around the control plane.

## Backwards Compatibility

This RFC is primarily a product and documentation repositioning. It does not require immediate schema breaks. Existing routes, packages, and apps may remain in place while docs and implementation converge.

## Implementation Notes

Near-term priorities:

1. Rewrite root docs around the Mammoth-first / AICP-control-plane framing.
2. Add Mammoth-integrated workflow, approval, and supervision surfaces.
3. Treat `apps/studio/` as legacy or embedded UX seed material.
4. Maintain a private reference map for clean-room feature migration from study repos.

## Open Questions

1. Which Studio capabilities should be embedded into Mammoth first: approvals, replay, or policy editing?
2. Should Mammoth Web ship before or after terminal Mammoth reaches parity for workflow supervision?
3. At what milestone should separate Studio branding be formally retired from public docs?

## Related RFCs

- [often_follows Semantics](./2026-often-follows-semantics.md)
- [JSON Policy to WASM Migration](./2026-policy-wasm-migration.md)
