# AICP + TOON: AI-Optimized Protocol

## Why TOON?

AICP is designed for AI agents. TOON is designed for AI consumption.

**TOON (Token-Oriented Object Notation)** is a line-oriented format that is:
- **More compact** than JSON for arrays of objects
- **Explicit** with length declarations (prevents truncation issues)
- **Readable** with minimal quoting
- **LLM-friendly** - easy to parse, generate, and validate

## TOON vs JSON Comparison

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

## AICP TOON Design

### Capability Discovery Response

**TOON:**
```
version: 0.1.0
capabilities[4]{name,kind,risk,autonomous}:
  payments.transfer,action,high,false
  orders.search,query,low,true
  food.order.workflow,workflow,medium,false
  reports.generate,async_action,medium,true
```

### Execution Request

**TOON:**
```
capability: payments.transfer
input:
  recipient_id: user_123
  amount: 1000
  currency: INR
workflow_id: wf_001
actor: assistant
```

### Execution Response with Next Steps

**TOON:**
```
status: success
capability: payments.transfer
data:
  transaction_id: txn_abc123
  status: completed
workflow_state:
  workflow_id: wf_order_001
  current_step: order.place
  completed_steps[3]: restaurant.search,menu.select,cart.review
  missing_inputs[0]:
  next_possible_steps[1]: order.track
next:
  can_continue: true
  workflow_complete: true
  result_summary: Order #123 placed successfully
```

### Error with Fix Hint

**TOON:**
```
status: invalid_input
capability: payments.transfer
error:
  code: invalid_amount
  message: Amount must be positive
  field: amount
  received: -100
  retryable: true
  fix_hint: Provide a positive number for amount
next:
  can_continue: true
  suggested_steps[1]: payments.transfer
```

## Response Templates

### Success Template
```
status: success
capability: {capability_name}
data:
  {result_data}
workflow_state:
  workflow_id: {wf_id}
  current_step: {step}
  completed_steps[{n}]: {steps}
  missing_inputs[{m}]: {missing}
  next_possible_steps[{k}]: {next_steps}
next:
  can_continue: {bool}
  workflow_complete: {bool}
  result_summary: {summary}
```

### Error Template
```
status: {error_status}
capability: {capability_name}
error:
  code: {error_code}
  message: {human_message}
  field: {field_name}
  received: {received_value}
  retryable: {bool}
  fix_hint: {how_to_fix}
next:
  can_continue: {bool}
  suggested_steps[{n}]: {recovery_steps}
```

### Confirmation Template
```
status: needs_confirmation
capability: {capability_name}
confirmation:
  type: user_approval
  prompt: {confirmation_prompt}
  required_fields[1]: user_confirmation
  expires_in_seconds: 300
data:
  {pending_data}
```

## Mini-LM Compatibility

TOON makes it even easier for mini LLMs:

| Feature | Benefit |
|---------|----------|
| Explicit lengths `[N]` | LLM knows exact count, no guessing |
| Tabular arrays | One line per item, easy to parse |
| Minimal quoting | Less token overhead |
| Consistent structure | Templateable, predictable |

## Implementation

### Parsing TOON in Python
```python
# Use reference implementation from toon-format
from toon import decode, encode

# Parse AICP response
response = decode(toon_string)

# Encode AICP request  
request = encode(json_data)
```

### Parsing TOON in TypeScript
```typescript
import { decode, encode } from '@toonify/core';

const response = decode(toonString);
const request = encode(data);
```

## File Extensions

- **AICP Schema**: `.toon` (protocol definitions)
- **AICP Request/Response**: `.toon` (runtime messages)
- **AICP Examples**: `.toon` (test fixtures)

## Migration Path

1. **v0.1**: JSON for wire format, TOON for examples
2. **v0.2**: TOON as primary, JSON as fallback
3. **v1.0**: TOON-only wire format

## See Also

- [TOON Specification](https://github.com/toon-format/spec)
- AICP Agentic Experience design (`docs/AGENTIC_EXPERIENCE.md`)
