# AICP Technical Specification

## Scope

This technical specification defines the core data model and behavior required for an AICP-compliant implementation.

## Core Objects

### Capability

A capability is the atomic semantic action exposed to an AI system.

Fields:

- `name`
- `description`
- `kind`
- `input`
- `output`
- `policy`
- `execution`
- `render`

### Capability Kinds

- `action`
- `query`
- `workflow`
- `async_action`
- `batch_action`

## Input Type Requirements

Input schemas must support:

- scalar types,
- arrays,
- objects,
- enums,
- nested schemas,
- required vs optional,
- constraints such as min/max/format,
- defaults.

## Output Type Requirements

Output schemas must support:

- structured success data,
- nested objects,
- enums,
- optional fields,
- and links to render hints.

## Policy Contract

Minimum required fields:

- `risk`
- `scopes`
- `requires_confirmation`
- `autonomous_execution`

Optional fields:

- `approval_thresholds`
- `role_requirements`
- `rate_limits`
- `cost_limits`
- `environment_restrictions`

## Workflow State Contract

Required fields:

- `workflow_id`
- `name`
- `current_step`
- `completed_steps`
- `missing_inputs`
- `next_possible_steps`

Optional fields:

- `pending_approvals`
- `warnings`
- `context`
- `last_result`

## Execution Result Contract

Required fields:

- `status`
- `capability`

Optional fields:

- `data`
- `error`
- `pagination`
- `job`
- `render`
- `debug`

## Standard Statuses

Success-related:

- `success`
- `partial_success`
- `paginated`
- `async_pending`

Input or decision-related:

- `needs_input`
- `needs_confirmation`
- `needs_approval`

Failure-related:

- `denied`
- `invalid_input`
- `unavailable`
- `rate_limited`
- `timeout`
- `failed`

## Error Contract

Required fields:

- `code`
- `message`

Optional fields:

- `field`
- `retryable`
- `details`
- `upstream_status`
- `correlation_id`

## Pagination Contract

AICP should normalize all list-returning capabilities into a common response shape.

Required fields:

- `items`
- `page_info`

Page info fields:

- `has_next_page`
- `next_token`
- `end_cursor`
- `count`

## Async Job Contract

Required fields:

- `job_id`
- `status`

Optional fields:

- `poll_after_ms`
- `submitted_at`
- `completed_at`
- `result`

## Render Contract

Required field:

- `preferred_view`

Optional fields:

- `summary_template`
- `important_fields`
- `empty_state_message`
- `suggested_actions`
- `title`

## Discovery Contract

The discovery endpoint should return:

- protocol version,
- capability list,
- type definitions,
- workflow definitions,
- policy and execution references,
- and extension metadata if applicable.

## Extension Model

Extensions must not break existing required fields and should be namespaced if experimental.

## Versioning

AICP follows semantic versioning:

- major: breaking changes,
- minor: backwards-compatible additions,
- patch: clarifications and fixes.

## JSON Schema Reference

All protocol objects are defined in `/spec/schemas/`:

- `capability.schema.json`
- `workflow.schema.json`
- `policy.schema.json`
- `execution.schema.json`
- `result.schema.json`
- `error.schema.json`
- `pagination.schema.json`
- `render.schema.json`

## Implementation Requirements

1. All capability definitions must validate against JSON schemas.
2. All runtime implementations must handle standard statuses.
3. All adapters must preserve AICP semantics.
4. All error responses must use the error contract.
5. All list responses must use the pagination contract.
