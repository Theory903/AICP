# AICP Plugin Architecture

## Overview

AICP plugins are **first-class extensions** that add capabilities, workflow behaviors, approval logic, policy rules, or perception features to the control plane. They are discovered, versioned, isolated, and policy-gated.

The plugin system is designed around these principles:

1. **Manifest-First** — Metadata (JSON) is the source of truth, loaded before runtime code
2. **Lazy Loading** — Heavy logic deferred until needed; light contracts used for discovery
3. **Strict SDK Boundaries** — Plugins import from `aicp.plugins.*` only, not internal core
4. **Hook-Based Extensibility** — Plugins register handlers for lifecycle phases
5. **Priority-Ranked Discovery** — Config > Workspace > Global > Bundled sources
6. **Sandbox Isolation** — Non-main plugins run in isolated environments by default

---

## Plugin Manifest

Every plugin defines an `aicp.plugin.json` manifest at its root. This is the single source of truth.

### Example Manifest

```json
{
  "id": "memory-lancedb",
  "kind": "capability_source",
  "name": "LanceDB Memory Store",
  "version": "1.0.0",
  "description": "Semantic memory storage backed by LanceDB",
  "author": "AICP Team",
  "license": "Apache-2.0",
  "tags": ["memory", "storage", "vector-db"],
  "requirements": {
    "aicp_version_min": "1.0.0",
    "python_version_min": "3.11",
    "dependencies": {
      "lancedb": ">=0.3.0"
    }
  },
  "config_schema": {
    "type": "object",
    "properties": {
      "db_path": {
        "type": "string",
        "description": "Path to LanceDB database directory"
      },
      "max_results": {
        "type": "integer",
        "default": 10
      }
    },
    "required": ["db_path"]
  },
  "lifecycle": {
    "auto_enable": false,
    "lazy_load": true,
    "isolation_mode": "sandbox"
  },
  "capabilities": [
    { "name": "memory.store", "kind": "action", "description": "Store memory" },
    { "name": "memory.retrieve", "kind": "query", "description": "Retrieve memory" }
  ],
  "hooks": [
    "on_capability_execute_after",
    "on_learning_event"
  ],
  "entry_points": {
    "main": "memory_lancedb:define_plugin",
    "runtime": "memory_lancedb.runtime:*"
  },
  "permissions": {
    "access_level": "scoped",
    "trust_tier": 2
  }
}
```

---

## Plugin SDK Boundary

### Public Imports

Plugins should import ONLY from the public SDK surface:

```python
# ✅ ALLOWED: Public SDK
from aicp.plugins import (
    PluginAPI,
    PluginEntry,
    PluginMetadata,
    HookContext,
    HookPhase,
    define_plugin,
)
```

### Forbidden Imports

```python
# ❌ FORBIDDEN: Internal core imports
from aicp.core.executor import AicpExecutor
from aicp.core.registry import CapabilityRegistry
```

---

## Plugin Lifecycle

### Phase 1: Discovery (No Runtime)
Manifests loaded, no Python code executed.

### Phase 2: Configuration Validation
Plugin config validated against `config_schema`.

### Phase 3: Lazy Runtime Load
Heavy code imported on first use.

### Phase 4: Hook Registration
Plugin handlers registered for lifecycle phases.

### Phase 5: Active Execution
Capabilities discoverable, hooks invoked.

---

## See Also

- [Plugin Manifest Schema](/spec/schemas/plugin-manifest.schema.json)
- [Core Plugin API](/packages/core/src/aicp/plugins/)
