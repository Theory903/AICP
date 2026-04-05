# AICP/Mammoth Implementation Guide

## Overview
This documentation covers the implemented enhancements to AICP/Mammoth based on Claude Code reference implementation.

## Design System

### Components
- **Theme**: Color palette and styling
- **ColorPalette**: Primary, secondary, accent, background colors
- **ThemedText**: Text with theme styling
- **ThemedBox**: Container with theme styling
- **Dialog**: Modal dialog
- **Pane**: Panel container

### Usage
```rust
use aicp_mammoth_ui::design_system::{Theme, ThemedText, Dialog};

let theme = Theme::default();
let text = ThemedText::new("Hello").theme(&theme);
let dialog = Dialog::new("Title", "Body");
```

## Authentication

### OAuth 2.0 with PKCE
```python
from aicp.auth.oauth import OAuth2Service, PKCEPair

service = OAuth2Service(
    client_id="client-id",
    auth_url="https://auth.example.com/authorize",
    token_url="https://auth.example.com/token"
)
url = service.get_authorization_url("state")
```

### Token Management
```python
from aicp.auth.token_manager import TokenManager

manager = TokenManager()
manager.store_tokens(access_token="...", refresh_token="...", expires_in=3600)
if manager.should_refresh():
    # refresh token
```

## Skills System

### Loading Skills
```python
from aicp.skills import SkillLoader, SkillManifest

loader = SkillLoader([Path("./skills")])
skills = loader.discover_skills()
manifest, path = loader.load_skill("github")
```

### Built-in Skills
- `github`: GitHub operations (commit, PR, branch)
- `debug`: Systematic debugging
- `verify`: Verification before completion
- `remember`: Memory storage

## Plugin System

### Plugin Manifest
```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "commands": ["./commands/"],
  "skills": ["./skills/"]
}
```

### Hooks
```python
from aicp.plugins.hooks import HookRegistry, HookEvent

registry = HookRegistry()
registry.register(HookEvent.AFTER_QUERY, handler)
```

## Session Storage

### JSONL Storage
```python
from aicp_runtime.services.session_storage import JSONLSessionStorage

storage = JSONLSessionStorage("/tmp/sessions")
storage.save("session-id", messages)
loaded = storage.load("session-id")
```

## UI Components

### Agent List
```rust
use crate::components::agent_list::{AgentList, Agent};

let agents = vec![Agent { name: "test".into(), status: "running".into(), model: "claude".into() }];
let list = AgentList::new(agents);
```

### Task Progress
```rust
use crate::components::tasks::{TaskList, TaskProgress, TaskStatus};

let mut task_list = TaskList::new();
task_list.add_task(TaskProgress::new("task-1".into(), "Test task".into()));
```

### Permission Request
```rust
use crate::components::permissions::PermissionRequest;

let req = PermissionRequest::new("bash".into(), "Run command".into(), true);
```

### Diff View
```rust
use crate::components::diff::{DiffView, DiffHunk, DiffLine};

let mut diff = DiffView::new();
```

### Settings Panel
```rust
use crate::components::settings::{SettingsPanel, SettingsTab};

let settings = SettingsPanel::new();
```

## VS Code Extension

Commands:
- `aicp.start`: Start AICP session
- `aicp.run`: Run capability
- `aicp.dev`: Start dev server
- `aicp.appr`: Show approval queue
