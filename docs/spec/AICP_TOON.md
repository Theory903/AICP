# AICP TOON: AI-Optimized Protocol Format

> TOON (Token-Oriented Object Notation) — a line-oriented format designed for AI consumption, providing compactness, readability, and explicit structure for AICP protocol messages.

---

## Why TOON?

AICP is designed for AI agents. TOON is designed for AI consumption.

**TOON** is a line-oriented format that is:
- **More compact** than JSON for arrays of objects
- **Explicit** with length declarations (prevents truncation issues)
- **Readable** with minimal quoting
- **LLM-friendly** — easy to parse, generate, and validate

---

## TOON vs JSON

### JSON (Verbose)

```json
{
  "capabilities": [
    {"name": "payments.transfer", "risk": "high"},
    {"name": "orders.search", "risk": "low"}
  ],
  "status": "success"
}
```

### TOON (Compact)

```
capabilities[2]{name,risk}:
  payments.transfer,high
  orders.search,low
status: success
```

---

## AICP TOON Design

### Capability Discovery Response

```
version: 0.1.1
capabilities[4]{name,kind,risk,requires_approval}:
  payments.transfer,action,high,true
  orders.search,query,low,false
  food.order.workflow,workflow,medium,true
  reports.generate,async_action,medium,false
```

### Execution Request

```
capability: payments.transfer
input:
  recipient_id: user_123
  amount: 1000
  currency: INR
session_id: sess_abc
actor:
  type: agent
  agent_id: agent_xyz
```

### Execution Response (v1.0.0 Format)

```
status: success
execution_id: exec_a1b2c3d4
capability_name: payments.transfer
capability_kind: action
determinism_class: bounded_nondeterministic
workflow_id: wf_e5f6g7h8
step_id: step_transfer
session_id: sess_i9j0k1l2
execution_mode: sync
policy_result:
  effect: allow
  policy_name: default_actions
  trust_tier: 2
  risk_score[3]: financial:0.7,irreversibility:0.9,privacy:0.1
approval_state:
  status: none
status: success
data:
  transaction_id: txn_abc123
  status: completed
execution_time_ms: 234
idempotency_key: transfer_xyz
allowed_next_actions[1]{name,requires_approval,confidence}:
  payment.confirm,false,0.95
rendered: Transfer of ₹1000 to user_123 completed
format_hint: text
audit_correlation_id: corr_u1v2w3x4
actor:
  type: agent
  agent_id: agent_y5z6
  session_id: sess_i9j0k1l2
timestamp: 2026-04-03T18:45:12.456Z
```

### Error with Fix Hint

```
status: invalid_input
execution_id: exec_a1b2c3d4
capability_name: payments.transfer
error:
  code: invalid_amount
  message: Amount must be positive
  field: amount
  received: -100
  retryable: true
  fix_hint: Provide a positive number for amount
allowed_next_actions[1]:
  payments.transfer
```

---

## Response Templates

### Success Template

```
status: success
execution_id: {exec_id}
capability_name: {capability}
capability_kind: {kind}
determinism_class: {determinism}
workflow_id: {wf_id}
step_id: {step_id}
session_id: {session_id}
execution_mode: sync|async|streaming|deferred
policy_result:
  effect: allow|deny|ask|require_approval|limit
  policy_name: {policy}
  trust_tier: 0-4
  risk_score: {dimensions}
approval_state:
  status: none|pending|approved|rejected|expired
status: success|failure|pending_approval
data: {result_data}
execution_time_ms: {ms}
allowed_next_actions[N]{name,requires_approval,confidence}:
  {capability_name},{bool},{float}
rendered: {human_readable}
format_hint: text|markdown|json|html
timestamp: {iso8601}
```

### Error Template

```
status: failure|invalid_input|denied|timeout
execution_id: {exec_id}
capability_name: {capability}
error:
  code: {error_code}
  message: {human_message}
  field: {field_name}
  retryable: true|false
  fix_hint: {how_to_fix}
allowed_next_actions[N]:
  {recovery_capabilities}
```

### Approval Required Template

```
status: pending_approval
execution_id: {exec_id}
capability_name: {capability}
approval_state:
  approval_id: {approval_id}
  status: pending
  requested_at: {timestamp}
  timeout_seconds: {seconds}
policy_result:
  effect: require_approval|ask
  risk_score: {dimensions}
allowed_next_actions[0]:
data: {pending_data}
```

---

## Mini-LM Compatibility

TOON makes it even easier for small language models:

| Feature | Benefit |
|---------|---------|
| Explicit lengths `[N]` | LLM knows exact count, no guessing |
| Tabular arrays | One line per item, easy to parse |
| Minimal quoting | Less token overhead |
| Consistent structure | Templateable, predictable |
| Field names inline | No ambiguity about what values mean |

---

## Implementation

### Parsing TOON in Python

```python
# Use reference implementation
from toon import decode, encode

# Parse AICP response
response = decode(toon_string)

# Encode AICP request  
request = encode(data)
```

### Parsing TOON in TypeScript

```typescript
import { decode, encode } from '@toonify/core';

const response = decode(toonString);
const request = encode(data);
```

---

## File Extensions

| Usage | Extension | Example |
|-------|-----------|---------|
| Protocol definitions | `.toon` | capability definitions |
| Runtime messages | `.toon` | request/response |
| Test fixtures | `.toon` | valid/invalid examples |

---

## Migration Path

| Version | TOON Usage | JSON Usage |
|---------|-----------|------------|
| v0.1.1 | Examples only | Wire format |
| v0.2.0 | Primary with fallback | Optional fallback |
| v0.3.0 | Primary format | Deprecated |
| v1.0.0 | Primary (no fallback) | Removed |

---

## See Also

- [/spec/schemas/](../../spec/schemas/) — JSON schema source of truth
- [TECH_SPEC.md](../guides/TECH_SPEC.md) — Protocol technical specification
- [ACTION_SURFACE.md](../overview/ACTION_SURFACE.md) — Capability model with execution envelope
- [TOON Specification](https://github.com/toon-format/spec) — Format specification