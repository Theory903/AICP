# AICP Plugin System

Welcome to the AICP plugin system documentation.

## Quick Links

- **[Architecture Guide](./architecture.md)** — Core concepts, lifecycle, and design patterns
- **[Plugin Manifest Schema](../../spec/schemas/plugin-manifest.schema.json)** — JSON schema reference
- **[Example Plugins](../../examples/plugins/)** — Working plugin examples
- **[API Reference](../../packages/core/src/aicp/plugins/)** — Python SDK

## What are AICP Plugins?

AICP plugins are **discoverable, versioned, isolated extensions** that add new capabilities, workflows, approval logic, or policy rules to the control plane.

Key features:

- ✅ **Manifest-first** — JSON manifests load before runtime code
- ✅ **Lazy loading** — Heavy logic deferred until first use
- ✅ **Priority-ranked discovery** — Config > Workspace > Global > Bundled
- ✅ **Hook system** — Lifecycle phases for extensibility
- ✅ **Sandbox isolation** — Third-party plugins run in containers by default
- ✅ **Public SDK** — Strict boundaries prevent internal core access
- ✅ **Conformance tests** — All plugins must pass schema validation

## Getting Started

### 1. Create Plugin Directory

```
my-plugin/
├── aicp.plugin.json        # Manifest
├── __init__.py             # Plugin definition
├── config.py               # Configuration schema
├── runtime.py              # Heavy logic (lazy-loaded)
└── tests/
    └── test_plugin.py      # Conformance tests
```

### 2. Define Manifest

```json
{
  "id": "my-plugin",
  "kind": "capability_source",
  "name": "My Plugin",
  "version": "1.0.0",
  "capabilities": [
    { "name": "my.action", "kind": "action" }
  ],
  "entry_points": {
    "main": "my_plugin:define_plugin"
  }
}
```

### 3. Implement Plugin

```python
from aicp.plugins import PluginAPI, PluginMetadata, define_plugin

class MyPlugin(PluginAPI):
    async def initialize(self, config):
        pass
    
    async def shutdown(self):
        pass
    
    def get_metadata(self) -> PluginMetadata:
        pass

def define_plugin():
    return define_plugin(
        metadata=...,
        factory=lambda config: MyPlugin(config),
    )
```

### 4. Run Conformance Tests

```bash
pytest examples/plugins/my-plugin/tests/
```

## Plugin Kinds

| Kind | Purpose |
|------|---------|
| `capability_source` | Provides new capabilities |
| `workflow_plugin` | Extends workflow execution |
| `approval_plugin` | Custom approval logic |
| `policy_plugin` | Policy rule engine |
| `perception_plugin` | Perception signal handling |
| `learning_plugin` | Learning system integration |
| `generic` | General-purpose extension |

## Plugin Lifecycle

1. **Discovery** — Manifests scanned, no Python code executed
2. **Configuration** — Config validated against `config_schema`
3. **Auto-Enable** — Plugin activated if requirements met
4. **Lazy Load** — Runtime code imported on first use
5. **Initialization** — `PluginAPI.initialize()` called
6. **Active** — Capabilities and hooks available
7. **Shutdown** — Resources cleaned up on shutdown

## Public SDK

The plugin SDK provides:

```python
from aicp.plugins import (
    PluginAPI,              # Base class for plugins
    PluginEntry,            # Factory entry point
    PluginMetadata,         # Metadata types
    HookContext,            # Hook handler context
    HookPhase,              # Hook phase names
    define_plugin,          # Factory function
    LazyValue,              # Lazy loading
    PluginRegistry,         # Plugin registry
    PluginDiscovery,        # Discovery scanner
)
```

## Forbidden Imports

```python
# ❌ DO NOT import from core internals
from aicp.core.executor import AicpExecutor
from aicp.core.registry import CapabilityRegistry

# ❌ DO NOT import from other plugins
from aicp_other_plugin import something

# ❌ DO NOT use relative imports escaping plugin root
from ../../core import something
```

## Hook Phases

Plugins register handlers for lifecycle phases:

- `on_plugin_initialize` — Plugin initialized
- `on_plugin_shutdown` — Plugin shutting down
- `on_capability_execute_before` — Before capability execution
- `on_capability_execute_after` — After capability execution
- `on_approval_request` — New approval needed
- `on_approval_decision` — Approval decided
- `on_policy_evaluate_before` — Before policy evaluation
- `on_policy_evaluate_after` — After policy evaluation
- `on_workflow_step_before` — Before workflow step
- `on_workflow_step_after` — After workflow step
- `on_perception_event` — Perception event received
- `on_signal_ingestion` — Signal ingested
- `on_learning_event` — Learning event generated

## Discovery Sources

Plugins are discovered from (in priority order):

1. **Config** — `AICP_PLUGINS_DIR` environment variable
2. **Workspace** — `.aicp/plugins/` in project root
3. **Global** — `~/.aicp/plugins/`
4. **Bundled** — Built-in AICP plugins

Deduplication by physical path: higher priority source wins.

## Best Practices

1. ✅ Keep manifests accurate and complete
2. ✅ Use lazy loading for heavy modules
3. ✅ Implement comprehensive shutdown logic
4. ✅ Write conformance tests
5. ✅ Use semantic versioning
6. ✅ Document all hooks and capabilities
7. ✅ Fail gracefully on initialization errors
8. ✅ Respect SDK boundaries
9. ✅ Test in sandbox isolation mode
10. ✅ Include usage examples

## Troubleshooting

### Plugin not discovered
- Check manifest filename: must be `aicp.plugin.json`
- Verify manifest is valid JSON
- Check plugin is in a discovery source directory

### Plugin fails to initialize
- Check config schema validation
- Review error logs for details
- Test with `aicp plugin test my-plugin`

### Lazy loading issues
- Verify entry point paths are correct
- Check module and attribute names
- Test import manually: `python -c "from my_plugin.runtime import X"`

## See Also

- [Architecture Guide](./architecture.md)
- [Example Plugins](../../examples/plugins/)
- [Plugin Manifest Schema](../../spec/schemas/plugin-manifest.schema.json)
- [Core Plugin API](../../packages/core/src/aicp/plugins/)
