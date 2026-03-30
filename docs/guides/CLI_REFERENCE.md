# The AICP Command-Line Interface (CLI)

The AICP CLI transforms your existing APIs and functions into securely governed agentic capabilities effortlessly. 

This reference outlines all of the available CLI commands across bootstrapping, validating, governing, and running the AICP runtime.

---

## The Core Lifecycle

Most applications follow a simple 4-step path via the CLI:
1. `bootstrap` to read existing routes and instantly create the configuration.
2. `preview` and `doctor` to verify the mapping and ensure no destructive actions are dangerously unchecked.
3. `protect` and `limit` to configure Human-in-the-loop and traffic governance instantly.
4. `dev` (or `start`) to run the engine in front of your application.

---

## Setup & Scaffolding

### `aicp bootstrap`

The fastest way to onboard an application. `bootstrap` combines `init`, `scan`, `export`, and `doctor` into a single, seamless script. 
It auto-creates directories, inspects your code's routing layer, creates YAML representations for each capability, and ensures overall application health.

**Usage:**
```bash
# General syntax
aicp bootstrap <adapter> <module:app>

# Example: Bootstrap a FastAPI server 
aicp bootstrap fastapi src.main:app
```

> [!TIP]
> If a route handles deletion logic, `bootstrap` will aggressively tag it as `destructive` and warn you if it's left unprotected!

### `aicp init`

Sets up an empty AICP workspace gracefully. Instead of generating boilerplate code, it scaffolds the physical file structure and the root `aicp.yaml` configuration required to track governance state locally.

**Usage:**
```bash
aicp init
```
**Creates:**
- `aicp.yaml` - Core project configuration.
- `aicp/capabilities/` - Where your specific API contracts will live.
- `aicp/policies/` - Where advanced Auth/governance policies live.

### `aicp scan`

Passively inspects your running application or framework components, deduces inputs/outputs and descriptions, and exports them directly into the `aicp/capabilities/` directory as structured YAML.

**Usage:**
```bash
aicp scan fastapi src.main:app
```

---

## Validation & Governance

### `aicp preview`

A rich, formatted viewer that lets you look up a specific capability and deeply understand how the Agent sees it and *how AICP will restrict it*. 
It perfectly flattens global policy resolution against local definitions to show you exactly what effect will apply at runtime.

**Usage:**
```bash
aicp preview <capability_name>
```

**Example Output Insight:** It will display the extracted schemas, applied tags (e.g. `[destructive]`), and the **Effective Policy**, including whether it defaults to `allow`, `ask` (human-in-the-loop), or `deny`.

### `aicp doctor`

The gatekeeper command. It rigorously verifies your `aicp.yaml` setups and capability definitions to catch security problems *before* they hit production. 

**Usage:**
```bash
aicp doctor
```

It validates:
- **Security Check:** Ensures endpoints marked `destructive` are not left as openly allowed.
- **Hygiene Check:** Checks for missing descriptions, empty schemas, or invalid types.
- **Integrity Check:** Compares capabilities against raw `aicp.yaml` rules to surface unsafe wildcards (`**`) and orphaned logic.

### `aicp protect`

A direct, safe shortcut that programmatically updates your `aicp.yaml` file to mandate that the specified capability *strictly requires human approval* prior to execution.

**Usage:**
```bash
aicp protect payments.transfer
```
_This forces the capability into an `ask` loop, redirecting any Agent payload to the notification queue for confirmation._

### `aicp limit`

Safeguard endpoints computationally by modifying rate limits directly across one or more actions.

**Usage:**
```bash
# Add a boundary of 60 requests per minute to reading operations.
aicp limit "users.read.*" --rpm 60
```

---

## Runtime

### `aicp dev`

Starts the AICP local development server. This effectively wraps your defined capabilities, stands up the standardized AICP execution and protocol interface, and prepares your app to be consumed safely by Agents via SDKs, webhooks, or MCP.

**Usage:**
```bash
aicp dev

# Or with custom port configurations
aicp dev --port 8000
```
