# RFC: often_follows Semantics

## Status

Draft

## Summary

Define `often_follows` as an advisory planning hint. It augments discovery ranking and successful execution results through `allowed_next_actions`, but it never authorizes, executes, or bypasses policy for any follow-on capability.

## Motivation

`often_follows` already exists on the capability contract and is already used by the discovery graph. What is missing is the behavioral contract: what it means at runtime, how it differs from explicit continuation metadata, and what guarantees implementations must preserve.

Without a spec note, different runtimes can treat the same field as ranking-only, prefetch-only, planner-only, or no-op metadata. That breaks protocol-level determinism.

## Detailed Specification

### Definition

`often_follows` is an ordered list of capability names that commonly follow successful execution of the current capability.

Example:

```json
{
  "name": "orders.place",
  "kind": "action",
  "often_follows": ["orders.track", "orders.cancel"]
}
```

### Semantics

1. `often_follows` is advisory only.
2. It MUST NOT cause a capability to execute automatically.
3. It MUST NOT bypass normal auth, policy, approval, tenant, or rate-limit checks.
4. It MUST NOT override explicit continuation metadata.

### Precedence

When multiple next-step hint sources exist, implementations SHOULD use this order:

1. Provider polling continuation (`next.action=wait`, polling capability)
2. `continuation.next_capabilities`
3. `often_follows`

`next.capability` remains reserved for the single best immediate continuation. `often_follows` belongs in the ranked candidate set, not the single-slot continuation field.

### Discovery Behavior

When capability ranking is performed with `interaction.last_capability` present:

1. A `continuation` edge SHOULD score higher than an `often_follows` edge.
2. An `often_follows` edge SHOULD still positively influence ranking.
3. The explanation payload SHOULD include a machine-readable reason such as `graph:often_follows`.

### Execution Behavior

On successful execution:

1. The runtime SHOULD emit `allowed_next_actions`.
2. `continuation.next_capabilities` SHOULD be added first.
3. `often_follows` entries SHOULD be appended after explicit continuation entries.
4. Entries MUST be de-duplicated by capability name.
5. Failure results SHOULD NOT emit `often_follows` suggestions.

Suggested payload shape:

```json
{
  "allowed_next_actions": [
    {
      "kind": "capability",
      "name": "orders.track",
      "reason": "declared_continuation",
      "confidence": 0.95
    },
    {
      "kind": "capability",
      "name": "orders.cancel",
      "reason": "often_follows",
      "confidence": 0.70
    }
  ]
}
```

Confidence values are implementation-defined, but explicit continuation SHOULD score higher than `often_follows`.

### Prefetch Behavior

Implementations MAY prefetch capability metadata, schemas, or auth requirements for `often_follows` candidates. They MUST NOT prefetch by executing the capability itself.

### Planner Behavior

Planners MAY use `often_follows` as a candidate expansion hint when:

1. The preceding capability succeeded.
2. No stronger continuation hint is available.
3. Policy evaluation still occurs before execution.

## Backwards Compatibility

This RFC is additive. Existing capability definitions remain valid. Runtimes that already treat `often_follows` as graph metadata stay compatible; they become more useful by surfacing the same metadata through `allowed_next_actions`.

## Open Questions

1. Should confidence bands be standardized across implementations or remain implementation-defined?
2. Should planners persist `often_follows` outcomes into semantic memory for local ranking calibration?
3. Should `often_follows` accept optional per-edge metadata in a future schema revision?

## Related RFCs

- `2026-policy-wasm-migration.md`
