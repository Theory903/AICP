# AICP: Agentic Experience Design

## The Vision

AICP should be the **easiest protocol for AI to process**.

Not just "machine-readable" — but **AI-optimized**. Designed so that:

- A 1B parameter model can use it effectively
- Reasoning required is minimized to near-zero
- Every response tells the AI exactly what to do next
- Ambiguity is eliminated at every level
- The AI never has to guess, infer, or wonder

---

## Core Principle: AI-Ease Over Human-Ease

Traditional APIs are designed for developers.

Traditional tool schemas are designed for prompt engineers.

**AICP is designed for AI agents themselves.**

---

## Design Rules for AI-Ease

### Rule 1: Explicit Over Implicit

**Bad**: `error: "failed"`

**AICP**: 
```json
{
  "status": "failed",
  "error": {
    "code": "invalid_amount",
    "message": "Amount must be greater than 0",
    "field": "amount",
    "retryable": false,
    "fix_hint": "Provide a positive number for amount"
  }
}
```

The AI knows exactly what happened and what to do.

---

### Rule 2: Always Include Next Steps

**Bad**: Return result and let AI figure out next move.

**AICP**: Every response includes:
```json
{
  "result": {...},
  "next": {
    "can_continue": true,
    "required_fields": ["delivery_address"],
    "suggested_steps": ["address.select", "payment.confirm"],
    "workflow_complete": false
  }
}
```

The AI never wonders "what now?"

---

### Rule 3: Enforced Action Types

**Bad**: AI must guess if an action is safe to auto-execute.

**AICP**: Every capability declares:
```json
{
  "name": "payment.transfer",
  "autonomous_execution": false,
  "requires_confirmation": true,
  "risk": "high",
  "confirmation_prompt": "Confirm transfer of {amount} to {recipient}?"
}
```

The AI knows whether to ask or proceed.

---

### Rule 4: Schema Is Contract

**Bad**: `input: { ... }` — AI must interpret what fields mean.

**AICP**:
```json
{
  "input": {
    "type": "object",
    "properties": {
      "recipient_id": {
        "type": "string",
        "description": "Unique recipient identifier",
        "example": "user_123",
        "required": true,
        "validation": "uuid_v4_format"
      }
    }
  }
}
```

The AI knows exactly what's valid.

---

### Rule 5: State Is Always Current

**Bad**: AI must track workflow progress manually.

**AICP**:
```json
{
  "workflow_state": {
    "workflow_id": "wf_order_123",
    "current_step": "payment.confirm",
    "completed_steps": ["restaurant.search", "menu.select", "cart.review", "address.select"],
    "missing_inputs": [],
    "next_possible_steps": ["payment.confirm", "cancel_order"],
    "estimated_remaining_steps": 1
  }
}
```

The AI never loses track.

---

### Rule 6: Built-in Validation Feedback

**Bad**: AI sends invalid input, gets generic error.

**AICP**:
```json
{
  "status": "invalid_input",
  "validation_errors": [
    {
      "field": "email",
      "error": "invalid_format",
      "message": "Email must be valid format",
      "received": "not-an-email",
      "suggestion": "user@example.com"
    }
  ]
}
```

The AI can auto-fix and retry.

---

### Rule 7: Opinionated Over Flexible

**Bad**: Many ways to do the same thing.

**AICP**: One canonical way.

- Standard capability naming: `{domain}.{action}`
- Standard status values
- Standard error codes
- Standard workflow patterns

The AI can predict and template.

---

## Mini-LM Compatibility

### What Mini-LMs Need

- **Clear directives** — no ambiguity
- **Direct action paths** — no exploration
- **Built-in hints** — no inference required
- **Complete context** — no missing pieces

### How AICP Delivers

| Mini-LM Need | AICP Solution |
|--------------|----------------|
| "What can I do?" | `capabilities` array with clear descriptions |
| "What does this need?" | `input` with required/optional marked |
| "Is this safe?" | `policy.autonomous_execution` boolean |
| "What happened?" | `status` + structured `error` |
| "What now?" | `next` with suggested steps |
| "Where am I?" | `workflow_state` with current step |
| "How do I fix it?" | `fix_hint` in error responses |

---

## Response Templates

### Success Template
```json
{
  "status": "success",
  "capability": "order.place",
  "data": { ... },
  "workflow_state": { ... },
  "next": {
    "can_continue": false,
    "workflow_complete": true,
    "result_summary": "Order #123 placed successfully"
  }
}
```

### Failure Template
```json
{
  "status": "failed",
  "capability": "payment.transfer",
  "error": {
    "code": "insufficient_balance",
    "message": "Account balance too low",
    "field": "amount",
    "retryable": true,
    "fix_hint": "Reduce amount or add funds"
  },
  "next": {
    "can_continue": true,
    "suggested_steps": ["account.add_funds", "payment.reduce_amount"]
  }
}
```

### Confirmation Template
```json
{
  "status": "needs_confirmation",
  "capability": "payment.transfer",
  "confirmation": {
    "type": "user_approval",
    "prompt": "Transfer $100 to John?",
    "required_fields": ["user_confirmation"],
    "expires_in_seconds": 300
  },
  "data": { ... }
}
```

### Input Error Template
```json
{
  "status": "invalid_input",
  "validation_errors": [
    {
      "field": "email",
      "error": "format_invalid",
      "message": "Email format invalid",
      "received": "john@",
      "expected_format": "user@domain.com"
    }
  ],
  "next": {
    "can_continue": false,
    "fix_hint": "Provide valid email and retry"
  }
}
```

---

## Why This Matters

### Traditional Tool Calling
```
AI: "I need to call getWeather... but what arguments? What if it fails? 
What do I do next? Is this safe? What's the current state?"
```

### AICP Agentic Experience
```
AI: "Status is needs_confirmation. Policy says requires_confirmation=true. 
I must ask user before proceeding. Here's the prompt..."
```

**The AI doesn't think. It follows.**

---

## Implementation Priority

### Phase 1: Response Templates (v0.1)

- Standard success/failure/confirmation structures
- `next` object on every response
- Structured error with `fix_hint`

### Phase 2: State Awareness (v0.2)

- Built-in workflow state
- Current step tracking
- Suggested next steps

### Phase 3: Smart Hints (v0.3)

- Auto-suggestions based on context
- Intent detection
- One-click resolution hints

---

## The Promise

With AICP, even a mini LLM can:

1. **Discover** what's available (clear capability list)
2. **Validate** inputs before sending (schema + hints)
3. **Execute** with confidence (policy tells if safe)
4. **Understand** results (structured response)
5. **Recover** from errors (fix_hint + retryable)
6. **Progress** through workflows (next steps)
7. **Complete** tasks successfully (state tracking)

**No reasoning required. Just follow AICP.**
