# AICP Use Cases

## Introduction

Use cases are where AICP stops being theory and becomes operational.

AICP is meant for tasks where AI must not only call something, but proceed through a sequence of meaningful actions while maintaining awareness of state, permission, failure, and user confirmation.

## Use Case 1: Food Ordering

### Narrative

A user tells an AI assistant: "Order a paneer roll from my usual place and deliver it home."

A raw tool-calling system may know how to call a restaurant search function and maybe place an order. But a robust system must understand that ordering food is a workflow.

It must:

1. identify the restaurant,
2. search menu items,
3. select the requested item,
4. create or update a cart,
5. choose the correct delivery address,
6. determine payment method,
7. request confirmation if required,
8. place the order,
9. and optionally track its status.

### AICP Value

AICP provides:

- workflow structure,
- capability names with meaning,
- current step tracking,
- missing input detection,
- payment confirmation semantics,
- and render-aware results.

## Use Case 2: Payment Transfer

### Narrative

A user says: "Send ₹1000 to Rahul."

A payment transfer is not a simple action. It involves:

- recipient resolution,
- amount validation,
- currency handling,
- threshold checks,
- policy enforcement,
- confirmation,
- and a final result state.

### AICP Value

AICP ensures that the AI:

- knows the action is high-risk,
- knows confirmation is required,
- can request missing recipient details,
- and returns a structured receipt-like result.

## Use Case 3: Form Filling

### Narrative

A user asks the AI to fill and submit a complex application form.

The AI must navigate:

- required and optional fields,
- validation rules,
- interdependent fields,
- file uploads,
- review stage,
- submission readiness,
- and final success or rejection.

### AICP Value

AICP makes forms process-aware rather than field-dump-driven. It lets the AI reason over what remains incomplete and what is invalid.

## Use Case 4: Ticket Booking

### Narrative

A user says: "Book a flight to Bangalore next Friday."

The workflow includes:

- search,
- pagination over results,
- user preference filters,
- selection,
- passenger details,
- seat preferences,
- payment,
- confirmation,
- and booking result.

### AICP Value

AICP lets the AI move through this process step by step with awareness of what is still needed and whether each transition is valid.

## Use Case 5: Enterprise Approval Workflows

### Narrative

An internal AI agent is asked to approve or route an invoice.

This requires:

- document lookup,
- policy evaluation,
- role awareness,
- possible escalation,
- stateful transition,
- and audit output.

### AICP Value

AICP provides explicit approval states, policy-driven decisions, and machine-readable outcomes.

## Use Case 6: Support and Issue Resolution

### Narrative

A support AI is asked to investigate and resolve a customer problem.

The process may include:

- searching account status,
- viewing recent orders,
- checking payment state,
- issuing refund if allowed,
- and notifying the user.

### AICP Value

AICP allows the AI to coordinate multiple capabilities under a coherent workflow.

## Shared Patterns Across All Use Cases

Across all of these cases, AICP is valuable because it lets AI understand:

- the available actions,
- the order in which they belong,
- what data is missing,
- what policy applies,
- and how to continue responsibly.
