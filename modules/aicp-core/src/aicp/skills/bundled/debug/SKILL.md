---
name: debug
description: Systematic debugging with root cause investigation
allowed-tools: [Bash, FileRead, Grep]
when_to_use: When encountering bugs or unexpected behavior
arguments: [error, context]
context: inline
effort: high
---

# Debug Skill

## Approach
1. INVESTIGATE - Gather evidence without making assumptions
2. ANALYZE - Find patterns in the evidence
3. HYPOTHESIZE - Form a testable theory about the root cause
4. IMPLEMENT - Fix the root cause, not symptoms

## Iron Law
No fixes without root cause identification first.