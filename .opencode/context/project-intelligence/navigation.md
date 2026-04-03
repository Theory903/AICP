<!-- Context: project-intelligence/navigation | Priority: high | Version: 1.0 | Updated: 2026-04-03 -->

# Project Intelligence

| File | Description | Priority |
|------|-------------|----------|
| technical-domain.md | Tech stack, architecture patterns, development conventions | critical |

## Quick Reference

- **Framework**: Python 3.10+ (reference), TypeScript 5.x (SDK)
- **Protocol**: JSON Schema 2020-12 (source of truth)
- **Compliance Level**: L2 (Resumable Workflows)
- **Architecture**: 11 planes, 20 modules
- **Key Standards**: Policy-before-execution, fail-closed defaults, immutable audit

## Usage

This context tells agents:
- Python is the primary implementation language
- JSON schemas in `/spec/schemas/` are the source of truth
- Execution envelope is the canonical response format
- Adapters must translate only — no business logic