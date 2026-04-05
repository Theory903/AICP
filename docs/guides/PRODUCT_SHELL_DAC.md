# Product Shell DAC

> DAC here means **Design Adaptation Charter**: a concrete plan for building an AICP-native product shell from studied repos without doing a raw code transplant.

## Scope

This charter covers two reference sources:

- `ref/` — an internal terminal-product reference study used for TUI, bridge, plugin, skill, and server-product patterns.
- `nanobot` — used for lightweight Python product patterns: config loading, channel/plugin registry layout, packaging, and operator-facing ergonomics.

This document is not legal advice. It is an engineering adaptation policy intended to materially reduce copy/paste risk.

## Adaptation Rules

1. Keep AICP protocol, runtime, and supervision semantics as the source of truth.
2. Do not copy product names, package names, command names, or directory layouts wholesale.
3. Re-express glue code around AICP endpoints and AICP terminology.
4. Lift patterns, not monoliths: registry layout, state boundaries, lifecycle hooks, screen composition, and config schema design.
5. Record provenance in AICP docs when a subsystem is inspired by a studied repo.

## Filesystem Mapping

The product shell starts with a deliberately renamed layout.

| Studied Pattern | AICP Target |
|---|---|
| `main.tsx` bootstrap | `apps/operator-shell/src/boot/cli.tsx` |
| `commands.ts` registry | `apps/operator-shell/src/commands/registry.ts` |
| `context.ts` + state helpers | `apps/operator-shell/src/state/` |
| tool/server runtime clients | `apps/operator-shell/src/connect/` |
| `screens/` | `apps/operator-shell/src/ui/` |
| product config schemas | `apps/operator-shell/src/config/` |
| product shell docs | `apps/operator-shell/README.md` |

For future phases, the same rule applies:

| Studied Pattern | Planned AICP-Native Name |
|---|---|
| `bridge/` | `connectors/ide/` |
| `tasks/` | `jobs/` |
| `plugins/` | `extensions/` |
| `memdir/` | `memory-ledger/` |
| channel adapters | `connectors/channels/` |

## What We Reuse

### From `ref/`

- Ink-based terminal shell composition
- command registry patterns
- product state layering
- remote/bridge lifecycle patterns
- plugin and skill host structure

### From `nanobot`

- lightweight Python packaging sensibility
- config schema/loader layering
- registry-based product integration layout
- channel-oriented connector organization

## What We Do Not Reuse Directly

- Claude-specific query engine code
- Anthropic account and product wiring
- nanobot provider/channel implementations as-is
- any repo-specific naming, branding, or UX copy

## Phase 1 Deliverable

Phase 1 creates `apps/operator-shell/` with:

1. a standalone package
2. an Ink dashboard bound to AICP runtime routes
3. a command registry for `shell` and `snapshot`
4. AICP-native folder naming and rewritten glue code

## Next Phases

1. add live refresh and SSE/WebSocket supervision feed
2. add approval decision actions from the TUI
3. add workflow replay and execution inspection views
4. add IDE connector package
5. add extension/skill host package
