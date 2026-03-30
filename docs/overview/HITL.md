# HITL

Human-in-the-loop is a protocol checkpoint in AICP, not a popup.

## Flow

1. policy returns ask or require_approval
2. runtime creates an approval request
3. execution pauses
4. human reviews inputs, risk, and context
5. human approves, rejects, modifies, or delegates
6. runtime resumes or ends execution

## Requirements

- approval state must persist
- approval must be traceable
- modified arguments must be recorded
- resume must be explicit

## What it is not

- not a UI alert
- not an informal email thread
- not a hidden side channel
