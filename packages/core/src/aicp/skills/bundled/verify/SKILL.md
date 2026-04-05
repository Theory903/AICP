---
name: verify
description: Verification before claiming completion
allowed-tools: [Bash]
when_to_use: Before reporting work complete or creating PRs
arguments: [command]
context: inline
effort: low
---

# Verify Skill

## Required Verification Steps
1. Run lint/typecheck on changed files
2. Run tests and confirm they pass
3. Verify no pre-existing issues were broken

## Evidence Requirements
- File edit → diagnostics clean
- Build command → exit code 0
- Test run → all pass