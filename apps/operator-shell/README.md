# AICP Operator Shell

`apps/operator-shell/` is a terminal-first product shell for AICP supervision.

It is intentionally **adapted**, not transplanted, from reference products studied in `ref/` and `nanobot`.

## Design Rules

- AICP runtime remains the source of truth.
- This package talks to the runtime over HTTP using existing `/v1` and provider-health routes.
- File names and directory layout are AICP-specific.
- Product names, source structure, and glue code are rewritten to avoid a line-for-line carryover from studied repos.

## Initial Surface

- `shell`: Ink-based interactive operator dashboard
- `snapshot`: JSON snapshot for scripting and debugging

## Local Development

```bash
npm install
npm test
npm run typecheck
npm run build
```

## Default Runtime

The operator shell defaults to:

```text
http://127.0.0.1:10003
```

Start the runtime on that port before launching the shell:

```bash
aicp dev --port 10003
```

Then run:

```bash
npx tsx src/boot/cli.tsx snapshot
npx tsx src/boot/cli.tsx shell
```

## Current Layout

```text
src/
  boot/       CLI startup and command execution
  commands/   command registry and invocation contracts
  config/     shell config normalization
  connect/    runtime HTTP clients
  state/      derived shell state and summaries
  ui/         Ink views and presentation
```
