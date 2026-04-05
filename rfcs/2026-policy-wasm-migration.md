# RFC: JSON Policy to WASM Migration

## Status

Draft

## Summary

Preserve `policy.schema.json` as the authoring contract for v0.x while defining a migration path to compiled policy bundles for v1.0.0. The runtime moves from direct JSON rule interpretation to a compiler pipeline that emits signed, portable WASM bundles for low-latency enforcement.

## Motivation

The architecture and roadmap already target compiled OPA/Cedar-style policy execution, but the repository still exposes only JSON rule objects. Contributors need a migration contract before building more tooling against the interpreted format.

This matters most for high-assurance domains where policy latency, replay fidelity, and deployment hardening are non-negotiable.

## Detailed Specification

### Authoring Contract

For v0.x, `spec/schemas/policy.schema.json` remains the source-of-truth authoring format.

Authoring semantics remain stable for:

1. `effect`
2. `subject`
3. `condition`
4. `priority`
5. `metadata`

Capability definitions continue to reference policies by `policy_name`.

### Compilation Pipeline

The target production pipeline is:

1. Validate JSON policies against `policy.schema.json`.
2. Normalize them into a canonical AICP policy IR.
3. Compile the IR into an engine-specific bundle.
4. Load the compiled bundle into the runtime as the hot-path evaluator.

The canonical IR is an internal compatibility layer that preserves AICP semantics even if multiple policy engines are supported.

### Bundle Manifest

Compiled bundles SHOULD ship with a manifest containing at least:

```json
{
  "bundle_id": "bundle_finance_prod_v3",
  "engine": "cedar-wasm",
  "source_policy_names": ["financial.default", "trading.notional_limit"],
  "wasm_sha256": "...",
  "generated_at": "2026-04-04T00:00:00Z",
  "compatibility": {
    "schema_version": "0.3.0",
    "runtime_min_version": "0.9.0"
  }
}
```

### Runtime Modes

The runtime SHOULD support three modes during migration:

1. `interpretive`
   - JSON policies evaluated directly.
   - Suitable for local development and tests.

2. `dual_run`
   - JSON interpreter and compiled bundle both evaluate.
   - Mismatches are audited.
   - Compiled result is advisory until promoted.

3. `compiled_strict`
   - Compiled bundle is authoritative.
   - Bundle load or verification failure MUST fail closed.

### Safety Rules

1. If bundle verification fails in `compiled_strict`, execution MUST be denied.
2. If a policy cannot be compiled, the compiler MUST report the unsupported construct explicitly.
3. Production namespaces such as `financial.*` and `trading.*` SHOULD run in `compiled_strict` mode.
4. Any fallback from compiled to interpretive mode MUST be audited as degraded governance.

### CLI and Tooling Direction

The migration path anticipates tooling like:

1. `aicp policy compile`
2. `aicp policy verify`
3. `aicp policy inspect-bundle`

Those commands are future work, but this RFC defines the direction they must follow.

### Delivery Phases

1. Phase A: RFC + docs + runtime data-model alignment
2. Phase B: canonical policy IR
3. Phase C: compiler + dual-run verification
4. Phase D: compiled-strict mode for high-assurance namespaces
5. Phase E: default compiled enforcement for production profiles

## Backwards Compatibility

This RFC preserves the existing JSON authoring experience through v0.x. Existing policies remain valid. The new compiled form is a deployment artifact, not an immediate replacement for the public schema.

## Open Questions

1. Should the first compiler target be Cedar, OPA, or both?
2. Should the canonical IR be public and versioned, or internal to the runtime/compiler boundary?
3. What signing format should compiled bundles use for high-assurance deployments?

## Related RFCs

- `2026-often-follows-semantics.md`
