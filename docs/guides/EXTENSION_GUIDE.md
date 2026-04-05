# Mammoth Chrome Extension — Implementation Guide

**Status:** Core bridge implemented · Approval flow implemented · Page context injection planned
**Source:** `apps/mammoth/extension/`
**Server bridge:** `apps/mammoth/crates/server/src/lib.rs`
**Channel abstraction:** `apps/mammoth/crates/runtime/src/channel.rs`
**Runtime config:** `apps/mammoth/crates/runtime/src/config.rs`

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Installation](#3-installation)
4. [Connecting to Mammoth](#4-connecting-to-mammoth)
5. [Page Context Capture](#5-page-context-capture)
6. [Approval UI](#6-approval-ui)
7. [Highlight Command](#7-highlight-command)
8. [Configuration](#8-configuration)
9. [Security Model](#9-security-model)
10. [Extension Events Reference](#10-extension-events-reference)
11. [Building from Source](#11-building-from-source)
12. [Debugging](#12-debugging)
13. [Future Roadmap](#13-future-roadmap)

---

## 1. Overview

The Mammoth Chrome Extension is the `Extension` channel — one of four interaction surfaces in the Mammoth Interaction OS:

| Channel | Surface | Entry point |
|---------|---------|-------------|
| `Terminal` | Interactive REPL in a terminal | `mammoth` binary (Rust) |
| `Web` | Studio supervision console | `GET /` served by `server` crate |
| `Cli` | Multi-channel command dispatcher | `mammoth serve`, `mammoth ext`, … |
| `Extension` | Chrome MV3 popup + content script | `apps/mammoth/extension/` |

The extension brings a governed, policy-evaluated AICP agent session into any browser tab. The user types into the popup; their message travels to a locally-running Mammoth server; the server evaluates it through the full AICP control plane (capability registry → policy engine → workflow engine → audit journal) and streams the assistant response back over Server-Sent Events.

Every message the extension sends or receives is backed by the same AICP execution layer as the Terminal and Web channels. The browser is a rendering surface; no AI logic runs inside the extension.

### What the extension does today

- Opens a persistent SSE connection (`GET /ext/events`) from the background service worker to the Mammoth server.
- Relays user messages from the popup to the server (`POST /ext/message`).
- Receives streamed assistant responses and approval requests via SSE.
- Renders an approval card (Allow / Deny) in the popup when a capability requires human sign-off.
- Sets a red badge `"!"` on the toolbar icon when an approval is pending.
- Captures page context (URL, title, selected text, meta description, H1) in every tab — ready for injection into the AI prompt.
- Applies CSS outline highlights to page elements via the `mammoth_highlight` message.

---

## 2. Architecture

### Component map

```
┌────────────────────────────────────────────────────────────────┐
│ Chrome browser                                                  │
│                                                                 │
│  ┌──────────────────┐  chrome.runtime.sendMessage  ┌─────────┐ │
│  │    popup.js      │◄────────────────────────────►│         │ │
│  │  (popup UI)      │                              │  back-  │ │
│  └──────────────────┘                              │  ground │ │
│                                                    │  .js    │ │
│  ┌──────────────────┐  chrome.runtime.sendMessage  │  (svc   │ │
│  │   content.js     │◄────────────────────────────►│  wkr)   │ │
│  │ (every page)     │                              └────┬────┘ │
└──────────────────────────────────────────────────────┼─────────┘
                                                        │
                             SSE  GET /ext/events ──────┤
                             HTTP POST /ext/message ────┘
                                                        │
┌───────────────────────────────────────────────────────▼────────┐
│  Mammoth Server  (axum — apps/mammoth/crates/server/src/lib.rs)│
│                                                                 │
│  GET /ext/events  ──►  ExtBroadcast (tokio::broadcast, cap=64) │
│  POST /ext/message ──►  ExtEvent::Message → runtime            │
│  AICP runtime triggers  ──►  ExtEvent::ApprovalRequest         │
│                                                                 │
│  GET /health                                                    │
└─────────────────────────────────┬──────────────────────────────┘
                                  │
┌─────────────────────────────────▼──────────────────────────────┐
│  AICP Runtime  (packages/runtime/)                             │
│                                                                 │
│  Capability Registry → Policy Engine → Workflow Engine         │
│  Approval Lifecycle → Audit Journal → Execution Envelope       │
└────────────────────────────────────────────────────────────────┘
```

### Data flow — outbound (user → AICP)

```
popup.js
  → chrome.runtime.sendMessage({ type: "mammoth_send", text })
  → background.js
  → POST /ext/message  { "message": "<text>" }
  → server ext_send_message()
  → ExtBroadcast → AICP runtime
```

### Data flow — inbound (AICP → user)

```
AICP runtime
  → server broadcasts ExtEvent::Message { content }
  → SSE frame  event: message\ndata: {...}\n\n
  → background.js EventSource "message" handler
  → chrome.runtime.sendMessage({ type: "mammoth_message", payload })
  → popup.js chrome.runtime.onMessage
  → appendMessage("assistant", ...)
```

### Data flow — approval

```
AICP policy engine (effect = "require_approval")
  → server broadcasts ExtEvent::ApprovalRequest { approval_id, capability_name, description }
  → SSE frame  event: approval_request\ndata: {...}\n\n
  → background.js: broadcastToPopup + chrome.action.setBadgeText("!")
  → popup.js: appendApprovalRequest() → Allow/Deny buttons rendered
  → user clicks Allow
  → handleApproval() → chrome.runtime.sendMessage({ type: "mammoth_send", text: JSON.stringify(decision) })
  → background.js → POST /ext/message
  → server → AICP runtime resolves ApprovalDecision
```

### File structure

```
apps/mammoth/extension/
├── manifest.json       # MV3 manifest — permissions, icons, entry points
├── background.js       # Service worker — SSE connection, message relay, badge
├── content.js          # Content script — page context, highlight command
├── popup.html          # Popup shell — dark-themed chat UI (inline CSS)
└── popup.js            # Popup logic — chat, connection check, approval rendering

apps/mammoth/crates/server/src/lib.rs       # GET /ext/events, POST /ext/message, ExtEvent
apps/mammoth/crates/runtime/src/channel.rs  # ChannelKind, ApprovalRequest, ApprovalDecision
apps/mammoth/crates/runtime/src/config.rs   # AicpConfig, ConfigLoader, MAMMOTH_CONFIG_HOME
```

### MV3 component roles

| Component | Type | Lifetime | Key API |
|-----------|------|---------|---------|
| `background.js` | Service worker | Event-driven; may be suspended by Chrome | `EventSource`, `fetch`, `chrome.runtime`, `chrome.action`, `chrome.storage` |
| `content.js` | Content script | Lives with the page; one instance per tab | `chrome.runtime.onMessage`, `window.getSelection`, `document.querySelectorAll` |
| `popup.js` | Extension page | Lives only while popup is open | `chrome.runtime.sendMessage`, `chrome.runtime.onMessage`, `chrome.storage`, `fetch` |

---

## 3. Installation

### Prerequisites

- Chrome 88+ (MV3 minimum) or any Chromium-based browser.
- A running Mammoth server (default: `http://localhost:3000`). Start it with:

  ```bash
  # From apps/mammoth/
  cargo run -p mammoth-cli -- serve
  ```

- The `apps/mammoth/extension/icons/` directory must contain `icon16.png`, `icon48.png`, `icon128.png`.  
  **Note:** The `icons/` directory and PNG files are not committed in the repository at the time of writing (see [Known Gaps](#known-gaps)). You must create placeholder icons before loading the extension.

### Developer mode install (unpacked)

1. Open Chrome and navigate to `chrome://extensions`.
2. Enable **Developer mode** (top-right toggle).
3. Click **Load unpacked**.
4. Select `apps/mammoth/extension/`.
5. The Mammoth icon appears in the Chrome toolbar.

### Verifying the connection

1. Start the Mammoth server.
2. Click the Mammoth toolbar icon.
3. The popup status indicator should show **Connected** (green dot).
4. Type a message and press Enter — the assistant response appears in the chat.

If the status shows **Disconnected**:
- Confirm the server is running: `curl http://localhost:3000/health`.
- Check the service worker console (see [Debugging](#12-debugging)) for `SSE connection error`.

### Reloading after source changes

1. Go to `chrome://extensions`.
2. Find the Mammoth card.
3. Click the refresh icon (↺).

The popup and content script reload immediately. The service worker may require closing and reopening the browser in some Chrome versions.

### Production CRX packaging

Chrome supports packaging an unpacked extension into a signed `.crx` file for distribution outside the Web Store:

```bash
# Using Chrome's built-in packer (no external tools needed)
chrome --pack-extension=apps/mammoth/extension \
       --pack-extension-key=mammoth-extension.pem
```

This produces `mammoth/extension.crx` and (on first run) `mammoth/extension.pem`. Store `extension.pem` securely — it is the signing key. Subsequent releases must use the same key to allow in-place updates.

> **Web Store publication:** Not currently planned. The extension communicates only with `localhost` and has no value for end users who do not run a local Mammoth server.

---

## 4. Connecting to Mammoth

### Server base URL

The background service worker stores the server base URL in `chrome.storage.local` under the key `"serverBase"`. Default:

```js
// apps/mammoth/extension/background.js:12
const DEFAULT_SERVER = "http://localhost:3000";
```

On startup, the service worker reads the persisted value:

```js
// apps/mammoth/extension/background.js:110-114
chrome.storage.local.get(["serverBase"], (result) => {
  if (result.serverBase) {
    serverBase = result.serverBase;
  }
  connectToMammoth();
});
```

### `connectToMammoth()` — SSE lifecycle

```js
// apps/mammoth/extension/background.js:21-54
function connectToMammoth() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }

  const url = `${serverBase}/ext/events`;
  eventSource = new EventSource(url);

  eventSource.addEventListener("message", (e) => {
    const data = tryParseJson(e.data);
    if (!data) return;
    broadcastToPopup({ type: "mammoth_message", payload: data });
  });

  eventSource.addEventListener("approval_request", (e) => {
    const data = tryParseJson(e.data);
    if (!data) return;
    broadcastToPopup({ type: "mammoth_approval_request", payload: data });
    chrome.action.setBadgeText({ text: "!" });
    chrome.action.setBadgeBackgroundColor({ color: "#e53935" });
  });

  eventSource.onerror = () => {
    console.warn("[Mammoth] SSE connection error — will retry automatically.");
  };

  eventSource.onopen = () => {
    console.info("[Mammoth] SSE connected to", url);
    chrome.action.setBadgeText({ text: "" });
  };
}
```

**Key behaviors:**

- Any existing `EventSource` is closed before opening a new one — prevents double-subscription on reconnect or URL change.
- `onopen` clears the badge so reconnects after an acknowledged approval do not leave stale state.
- `onerror` is intentionally minimal: the browser's `EventSource` implementation retries automatically with exponential back-off. The service worker logs the error and waits.
- The service worker may be terminated by Chrome when idle (MV3 restriction). On the next event (e.g., a `chrome.runtime.onMessage`), Chrome wakes the service worker and `connectToMammoth()` re-establishes the SSE stream via the startup sequence.

### SSE reconnect behavior

`EventSource` reconnects automatically after network errors. The browser sends the `Last-Event-ID` header if the server sets event IDs. The Mammoth server does **not** set event IDs on `ExtEvent` frames, so no replay-from-ID occurs on reconnect — events emitted during a disconnection are lost.

### Popup health check

Every time the popup is opened, `popup.js` pings `GET /health`:

```js
// apps/mammoth/extension/popup.js:31-36
chrome.storage.local.get(["serverBase"], (result) => {
  const base = result.serverBase || "http://localhost:3000";
  fetch(`${base}/health`, { signal: AbortSignal.timeout(2000) })
    .then((r) => setConnected(r.ok))
    .catch(() => setConnected(false));
});
```

The server responds with:

```json
{"status":"ok","service":"mammoth-web"}
```

The 2 000 ms timeout prevents the popup from hanging if the server is unreachable.

---

## 5. Page Context Capture

### What it captures

The content script (`content.js`) exposes a `capturePageContext()` function that builds a structured snapshot of the current page:

```js
// apps/mammoth/extension/content.js:28-37
function capturePageContext() {
  return {
    url: location.href,
    title: document.title,
    selectedText: window.getSelection()?.toString()?.slice(0, 2000) ?? "",
    metaDescription:
      document.querySelector('meta[name="description"]')?.getAttribute("content") ?? "",
    h1: document.querySelector("h1")?.textContent?.trim()?.slice(0, 200) ?? "",
  };
}
```

| Field | Source element | Max length | Notes |
|-------|---------------|------------|-------|
| `url` | `location.href` | Unbounded | Full URL including query string and hash |
| `title` | `document.title` | Unbounded | Page `<title>` element |
| `selectedText` | `window.getSelection().toString()` | 2 000 chars | User's active text selection; empty string if none |
| `metaDescription` | `<meta name="description">` | Unbounded | First matching meta tag; empty string if absent |
| `h1` | First `<h1>` (trimmed) | 200 chars | Empty string if no H1 exists |

The length limits on `selectedText` (2 000) and `h1` (200) prevent runaway context from very long pages bloating the prompt payload.

### When it fires

Context capture is **pull-based**: the content script does not proactively push context anywhere. It only runs `capturePageContext()` when the background or popup sends a `mammoth_get_page_context` message:

```js
// apps/mammoth/extension/content.js:43-47
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  switch (message.type) {
    case "mammoth_get_page_context":
      sendResponse({ ok: true, context: capturePageContext() });
      break;
```

### Double-injection guard

```js
// apps/mammoth/extension/content.js:17-18
if (window.__mammothContentScriptLoaded) return;
window.__mammothContentScriptLoaded = true;
```

If `scripting.executeScript()` is called programmatically to inject `content.js` while the declarative content script is already active on the page (both declared in `manifest.json` and injected programmatically), this guard prevents the script body from executing twice.

### Current integration status

`capturePageContext()` is **implemented but not yet injected into the AI prompt**. To use it, the caller must:

1. Send `{ type: "mammoth_get_page_context" }` via `chrome.tabs.sendMessage(tabId, …)` to the active tab.
2. Receive the `{ ok: true, context: { … } }` response.
3. Prepend the context to the user's message before sending to `POST /ext/message`.

This wiring (step 3) is listed as a planned feature — see [Section 13](#13-future-roadmap).

---

## 6. Approval UI

### How approval requests arrive

When the AICP policy engine evaluates a capability execution and sets `effect = "require_approval"`, the runtime constructs an `ApprovalRequest` (defined in `channel.rs`) and emits it over the `ExtBroadcast` channel. The server serializes it as an SSE frame with event name `approval_request`.

The `ApprovalRequest` Rust struct (from `apps/mammoth/crates/runtime/src/channel.rs:54-66`):

```rust
/// An approval request surfaced from the AICP execution layer to the channel.
///
/// When the policy engine sets `effect = "require_approval"`, the runtime
/// emits an `ApprovalRequest` and pauses execution until the channel delivers
/// an `ApprovalDecision`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ApprovalRequest {
    /// Unique identifier for this approval checkpoint.
    pub approval_id: String,
    /// The capability name that requires human sign-off.
    pub capability_name: String,
    /// Human-readable description of the action to be taken.
    pub description: String,
    /// Risk metadata from the AICP policy engine.
    pub risk_summary: Option<String>,
    /// Channel that should present this request to the human.
    pub channel: ChannelKind,
}
```

The `ExtEvent::ApprovalRequest` variant (from `apps/mammoth/crates/server/src/lib.rs:147-151`) carries a subset of these fields over SSE:

```rust
/// Events forwarded to the Chrome extension bridge SSE stream.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ExtEvent {
    /// A new message to display in the extension popup.
    Message { content: String },
    /// An approval request that the extension must surface to the user.
    ApprovalRequest {
        approval_id: String,
        capability_name: String,
        description: String,
    },
}
```

> `risk_summary` and `channel` are present on the internal `ApprovalRequest` struct but are **not** forwarded in `ExtEvent::ApprovalRequest`. The extension popup does not display risk metadata in the current implementation.

### Badge behavior

When the background receives an `approval_request` SSE event:

```js
// apps/mammoth/extension/background.js:36-43
eventSource.addEventListener("approval_request", (e) => {
  const data = tryParseJson(e.data);
  if (!data) return;
  broadcastToPopup({ type: "mammoth_approval_request", payload: data });
  // Show a badge so the user knows action is needed
  chrome.action.setBadgeText({ text: "!" });
  chrome.action.setBadgeBackgroundColor({ color: "#e53935" });
});
```

The red `"!"` badge on the toolbar icon is visible even when the popup is closed, alerting the operator that action is needed. The badge is cleared in two places:

1. In `background.js:52` when the SSE connection opens (reconnect cleanup).
2. In `popup.js:72` inside `appendApprovalRequest()` — immediately after the card is rendered and the user has seen it.

### Approval card rendering

When `popup.js` receives `mammoth_approval_request`:

```js
// apps/mammoth/extension/popup.js:51-73
function appendApprovalRequest(payload) {
  const el = document.createElement("div");
  el.className = "msg approval";
  el.innerHTML = `
    <strong>Approval required</strong><br/>
    <em>${escapeHtml(payload.capability_name)}</em><br/>
    ${escapeHtml(payload.description)}
    <div class="approval-actions">
      <button class="btn-approve" data-id="${escapeHtml(payload.approval_id)}">Allow</button>
      <button class="btn-deny" data-id="${escapeHtml(payload.approval_id)}">Deny</button>
    </div>
  `;
  el.querySelector(".btn-approve").addEventListener("click", () =>
    handleApproval(payload.approval_id, true, el)
  );
  el.querySelector(".btn-deny").addEventListener("click", () =>
    handleApproval(payload.approval_id, false, el)
  );
  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  // Clear badge
  chrome.action.setBadgeText({ text: "" }).catch(() => {});
}
```

### Approval decision handling

```js
// apps/mammoth/extension/popup.js:75-91
async function handleApproval(approvalId, approved, el) {
  el.querySelectorAll("button").forEach((b) => (b.disabled = true));
  const label = approved ? "✓ Approved" : "✗ Denied";
  el.querySelector(".approval-actions").textContent = label;

  // In a full implementation this would call POST /approvals/{id}/decision
  // on the AICP runtime. For now we echo the decision into the ext/message
  // channel as a structured payload.
  await chrome.runtime.sendMessage({
    type: "mammoth_send",
    text: JSON.stringify({
      type: "approval_decision",
      approval_id: approvalId,
      approved,
    }),
  });
}
```

After the user clicks:
1. Both buttons are disabled immediately — prevents double-submission.
2. The button area is replaced with a `"✓ Approved"` or `"✗ Denied"` label.
3. The decision is serialized to JSON and sent via the `mammoth_send` relay to `POST /ext/message`.
4. The server receives the JSON string as the `message` field and routes it to the AICP approval lifecycle.

The `ApprovalDecision` Rust struct (from `apps/mammoth/crates/runtime/src/channel.rs:69-79`):

```rust
/// The human's response to an `ApprovalRequest`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ApprovalDecision {
    /// Must match the originating `ApprovalRequest::approval_id`.
    pub approval_id: String,
    /// `true` = approved, `false` = denied.
    pub approved: bool,
    /// Optional free-text comment from the human (shown in audit trail).
    pub comment: Option<String>,
    /// Who made the decision (user id, extension context, etc.).
    pub decided_by: Option<String>,
}
```

In the current extension implementation, `comment` and `decided_by` are always `null` — the popup does not collect them.

### Known gap: popup closed during approval

If the popup is closed when an approval request arrives over SSE, the badge `"!"` is set (background.js fires), but the popup does not receive the `mammoth_approval_request` event and no approval card is rendered. When the operator opens the popup later, they see the badge but no card. The approval remains pending on the server. This is tracked as a planned feature (approval persistence across popup open/close) — see [Section 13](#13-future-roadmap).

---

## 7. Highlight Command

### What it does

The `mammoth_highlight` message directs the content script to apply a CSS `outline` to all elements matching a CSS selector on the current page:

```js
// apps/mammoth/extension/content.js:49-62
case "mammoth_highlight": {
  // Future: highlight a CSS selector on the page
  const { selector, color = "#ffe082" } = message;
  try {
    document.querySelectorAll(selector).forEach((el) => {
      el.style.outline = `3px solid ${color}`;
      el.style.outlineOffset = "2px";
    });
    sendResponse({ ok: true });
  } catch (err) {
    sendResponse({ ok: false, error: String(err) });
  }
  break;
}
```

### How Mammoth triggers it

The background service worker forwards the `mammoth_highlight` message from the server's SSE stream to the content script of the active tab:

```js
// Not yet wired — this shows the intended call pattern:
chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
  chrome.tabs.sendMessage(tab.id, {
    type: "mammoth_highlight",
    selector: "button.checkout",
    color: "#ffe082",  // amber — default
  });
});
```

> **Current status:** The content script handler is implemented. The server-side `ExtEvent` variant that would trigger the highlight from the AI layer is not yet defined — the highlight can be triggered today only by sending a message from the popup/background directly to the content script. The `ExtEvent` enum will need a `Highlight` variant when this is wired end-to-end.

### Default color

The default highlight color is `#ffe082` (amber). It can be overridden by setting `color` in the message payload. No color validation is performed; invalid CSS values silently produce no visible outline.

### Cleanup

Highlights are **not automatically removed**. They persist until the page is reloaded, the user navigates away, or another message explicitly removes them (e.g., by setting `el.style.outline = ""`). There is no `mammoth_unhighlight` command in the current implementation.

### Use cases

- AI-directed visual annotation: "Click the button I've highlighted in amber."
- Page context grounding: highlight the element the assistant is reasoning about.
- Operator supervision: visually confirm which element an agent action targets before approving.

---

## 8. Configuration

### Extension-side configuration

The extension has one runtime-configurable value: the Mammoth server base URL.

| Key | Storage | Default | Description |
|-----|---------|---------|-------------|
| `serverBase` | `chrome.storage.local` | `"http://localhost:3000"` | Base URL for `GET /ext/events` and `POST /ext/message` |

To update `serverBase` programmatically from any context with access to `chrome.runtime`:

```js
chrome.runtime.sendMessage({
  type: "mammoth_config_set_server",
  serverBase: "http://localhost:8080",
});
```

The service worker handler (from `apps/mammoth/extension/background.js:68-74`):

```js
if (message.type === "mammoth_config_set_server") {
  serverBase = message.serverBase || DEFAULT_SERVER;
  chrome.storage.local.set({ serverBase });
  connectToMammoth();
  sendResponse({ ok: true });
  return true;
}
```

The change is immediate: the old SSE stream is closed, `serverBase` is persisted, and `connectToMammoth()` opens a fresh stream to the new URL. The change survives browser restart.

To reset to the default: send `"http://localhost:3000"` or clear `serverBase` from `chrome://extensions` → Service Worker → Application → Storage → Local Storage.

### Manifest-level configuration

All manifest-level settings are in `apps/mammoth/extension/manifest.json`:

```json
{
  "manifest_version": 3,
  "name": "Mammoth",
  "version": "0.1.0",
  "description": "Mammoth Extension channel — bring Mammoth to every web page.",
  "permissions": [
    "activeTab",
    "storage",
    "scripting"
  ],
  "host_permissions": [
    "http://localhost/*",
    "https://localhost/*"
  ],
  "background": {
    "service_worker": "background.js",
    "type": "module"
  },
  "content_scripts": [
    {
      "matches": ["<all_urls>"],
      "js": ["content.js"],
      "run_at": "document_idle"
    }
  ],
  "action": {
    "default_popup": "popup.html",
    "default_title": "Mammoth"
  },
  "icons": {
    "16": "icons/icon16.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  }
}
```

| Field | Value | Effect |
|-------|-------|--------|
| `manifest_version` | `3` | Required for all new extensions. MV3 uses service workers (not persistent background pages) and stricter CSP. |
| `background.type` | `"module"` | Enables ES module syntax in the service worker. |
| `content_scripts.run_at` | `"document_idle"` | Script runs after HTML is parsed and deferred scripts have executed — `document.querySelector` and `getSelection()` are reliable. |
| `host_permissions` | `localhost` only | Limits network requests to local Mammoth server only. See [Section 9](#9-security-model). |

### Server-side AICP configuration

The Mammoth runtime reads `AicpConfig` from `~/.mammoth/settings.json` or `.mammoth/settings.json` in the project directory (from `apps/mammoth/crates/runtime/src/config.rs:61-81`):

```rust
/// Configuration for the AICP execution governance layer.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AicpConfig {
    /// Base URL of the AICP runtime (default: `http://localhost:10003`).
    pub url: String,
    /// Whether AICP governance is active for this session.
    pub enabled: bool,
    /// Trust tier passed to the policy engine.
    pub trust_tier: String,
    /// Optional session ID for resumable execution context.
    pub session_id: Option<String>,
}
```

The `AICP_URL` environment variable overrides `AicpConfig::url` (from `config.rs:89-91`):

```rust
pub fn resolve_url(&self) -> String {
    std::env::var("AICP_URL").unwrap_or_else(|_| self.url.clone())
}
```

Example settings file:

```json
{
  "aicp": {
    "url": "http://localhost:10003",
    "enabled": true,
    "trustTier": "2",
    "sessionId": null
  }
}
```

Config resolution precedence (lowest to highest):

1. `~/.mammoth.json` (user legacy)
2. `~/.mammoth/settings.json` (user)
3. `.mammoth.json` (project)
4. `.mammoth/settings.json` (project)
5. `.mammoth/settings.local.json` (local override — gitignored)
6. Environment variables (`AICP_URL`, `MAMMOTH_CONFIG_HOME`)

The Mammoth server port (`3000`) is not currently read from a config file — it is the default for `axum::serve` in `mammoth-cli`. To run on a different port, set it when starting the server and update `serverBase` in the extension.

---

## 9. Security Model

### Host permissions — localhost only

The manifest declares `host_permissions` for `http://localhost/*` and `https://localhost/*` only:

```json
"host_permissions": [
  "http://localhost/*",
  "https://localhost/*"
]
```

Chrome enforces this at the network level. The extension **cannot** make cross-origin `fetch` or `EventSource` requests to any non-localhost origin. This means:

- No data exfiltration to remote servers.
- The `mammoth_config_set_server` handler can only point to localhost URLs — a call with a remote URL will fail at the `fetch()` level with `net::ERR_FAILED`.
- An operator cannot accidentally (or maliciously) route the extension to a remote server by reconfiguring `serverBase`.

### Content Security Policy (MV3)

MV3 imposes a strict CSP on all extension pages (`popup.html`, any options page):

- `eval()` and `new Function()` are disallowed.
- Inline `<script>` blocks are disallowed.
- Remote script sources are disallowed.

`popup.html` loads `popup.js` as a local file via `<script src="popup.js">`. No remote scripts are loaded anywhere in the extension.

### No remote code execution

The extension does not load any scripts from remote URLs at any point. All JavaScript (`background.js`, `content.js`, `popup.js`) is bundled with the extension and loaded from the extension package.

### Minimal permissions

| Permission | Required for | Not used for |
|------------|-------------|-------------|
| `activeTab` | Querying focused tab URL/title for page context | Persistent tab monitoring; background tab access |
| `storage` | Persisting `serverBase` across sessions | `chrome.storage.sync` (no Google account sync) |
| `scripting` | Programmatic content script injection (highlight) | Injecting remote scripts; modifying page DOM beyond annotation |

The extension does not request: `tabs`, `history`, `cookies`, `webRequest`, `webRequestBlocking`, `bookmarks`, `downloads`, `notifications`, `geolocation`, `camera`, `microphone`, `identity`, or any other sensitive permission.

### Content script isolation

`content.js` runs in an isolated world — it shares the DOM with the page but has a separate JavaScript execution context. It cannot access page-defined JavaScript variables; it can only read DOM state via the standard DOM API. Page scripts cannot call into `content.js` functions directly.

### Internal message origin

`chrome.runtime.onMessage` listeners in the background and content script receive messages only from extension contexts (popup, other content scripts, the service worker itself). External web pages cannot send messages to the extension's service worker unless the manifest declares `externally_connectable` — which it does not.

### XSS prevention in popup

All user-supplied and server-supplied text inserted into the popup DOM is passed through `escapeHtml()` (from `apps/mammoth/extension/popup.js:158-163`):

```js
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
```

This prevents XSS from assistant responses or capability names that contain HTML-like content.

---

## 10. Extension Events Reference

All events flow over the SSE stream (`GET /ext/events`) or the `chrome.runtime` message bus. The following tables document every event type, its direction, and its full JSON shape.

### SSE events — server → extension (background.js)

These events are emitted by the Mammoth server and consumed by the background service worker's `EventSource`.

---

#### `message`

An assistant response to display in the popup.

**SSE frame:**
```
event: message
data: {"type":"message","content":"The order has been placed. Order ID: ord_m3n4o5p6."}
```

**JSON shape:**
```json
{
  "type": "message",
  "content": "<assistant response text>"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | `"message"` | Discriminant (set by `#[serde(tag = "type")]`) |
| `content` | `String` | The assistant's response text |

**Source:** `ExtEvent::Message` in `apps/mammoth/crates/server/src/lib.rs:145`

---

#### `approval_request`

An approval request requiring human sign-off before execution continues.

**SSE frame:**
```
event: approval_request
data: {"type":"approval_request","approval_id":"apr_abc123","capability_name":"files.delete","description":"Delete /tmp/report.pdf"}
```

**JSON shape:**
```json
{
  "type": "approval_request",
  "approval_id": "<unique approval checkpoint ID>",
  "capability_name": "<AICP capability name, e.g. files.delete>",
  "description": "<human-readable description of the action>"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | `"approval_request"` | Discriminant |
| `approval_id` | `String` | Must be echoed back in the `ApprovalDecision` |
| `capability_name` | `String` | The capability requiring approval |
| `description` | `String` | Human-readable description |

**Source:** `ExtEvent::ApprovalRequest` in `apps/mammoth/crates/server/src/lib.rs:147-151`

---

#### SSE keepalive

Every 15 seconds, the server sends an SSE keepalive comment to prevent proxy timeouts:

```
: keep-alive
```

This is handled transparently by the browser's `EventSource` — no `addEventListener` is needed for keepalives.

**Source:** `KeepAlive::new().interval(Duration::from_secs(15))` in `apps/mammoth/crates/server/src/lib.rs:432`

---

### `chrome.runtime` messages — background ↔ popup ↔ content script

These messages flow over the internal extension message bus.

---

#### `mammoth_message` (background → popup)

Relays a server `message` SSE event to the popup.

```json
{
  "type": "mammoth_message",
  "payload": {
    "type": "message",
    "content": "<assistant response text>"
  }
}
```

**Handler:** `popup.js:98-105`

---

#### `mammoth_approval_request` (background → popup)

Relays a server `approval_request` SSE event to the popup.

```json
{
  "type": "mammoth_approval_request",
  "payload": {
    "type": "approval_request",
    "approval_id": "apr_abc123",
    "capability_name": "files.delete",
    "description": "Delete /tmp/report.pdf"
  }
}
```

**Handler:** `popup.js:107-109`

---

#### `mammoth_send` (popup → background)

Sends a user message or approval decision to the server via `POST /ext/message`.

**Plain chat message:**
```json
{
  "type": "mammoth_send",
  "text": "What is the status of order #12345?"
}
```

**Approval decision (serialized JSON string in `text`):**
```json
{
  "type": "mammoth_send",
  "text": "{\"type\":\"approval_decision\",\"approval_id\":\"apr_abc123\",\"approved\":true}"
}
```

**Handler:** `background.js:61-65`

---

#### `mammoth_config_set_server` (any → background)

Updates the Mammoth server base URL.

```json
{
  "type": "mammoth_config_set_server",
  "serverBase": "http://localhost:8080"
}
```

**Handler:** `background.js:68-74`

---

#### `mammoth_get_page_context` (background/popup → content script)

Requests a page context snapshot from the content script.

**Request:**
```json
{
  "type": "mammoth_get_page_context"
}
```

**Response:**
```json
{
  "ok": true,
  "context": {
    "url": "https://example.com/checkout",
    "title": "Checkout — Example Store",
    "selectedText": "Premium Widget (qty: 2)",
    "metaDescription": "Fast, secure checkout for all your needs.",
    "h1": "Complete Your Purchase"
  }
}
```

**Handler:** `content.js:45-47`

---

#### `mammoth_highlight` (background → content script)

Applies a CSS outline to elements matching a CSS selector.

**Request:**
```json
{
  "type": "mammoth_highlight",
  "selector": "button.checkout-confirm",
  "color": "#ffe082"
}
```

**Response (success):**
```json
{ "ok": true }
```

**Response (error — invalid selector):**
```json
{ "ok": false, "error": "SyntaxError: '.invalid..selector' is not a valid selector" }
```

**Handler:** `content.js:49-62`

---

### HTTP endpoints — extension → server

---

#### `GET /ext/events`

Opens the SSE stream. Returns `text/event-stream`.

**Request:** No body, no query params.

**Response:** Streaming SSE. Frames documented above under "SSE events."

**Source:** `ext_stream_events()` in `apps/mammoth/crates/server/src/lib.rs:413-433`

---

#### `POST /ext/message`

Sends a message from the extension to the server.

**Request body:**
```json
{ "message": "<user text or JSON-encoded decision>" }
```

**Response:** `204 No Content`

**Source:** `ext_send_message()` in `apps/mammoth/crates/server/src/lib.rs:438-445`

---

#### `GET /health`

Health check used by the popup to verify server reachability.

**Response:**
```json
{ "status": "ok", "service": "mammoth-web" }
```

**Source:** `health_check()` in `apps/mammoth/crates/server/src/lib.rs:385-391`

---

## 11. Building from Source

### Prerequisites

- Rust toolchain (edition 2021). Install via [rustup.rs](https://rustup.rs).
- Chrome 88+ or Chromium.

### Build the Mammoth server

```bash
# From apps/mammoth/
cargo build --workspace
```

For a release build (smaller binary, faster startup):

```bash
cargo build --workspace --release
```

The server binary is at `apps/mammoth/target/debug/mammoth-cli` (or `target/release/`).

### Start the server

```bash
# Debug
./target/debug/mammoth-cli serve

# Release
./target/release/mammoth-cli serve

# Or with cargo run:
cargo run -p mammoth-cli -- serve
```

The server starts on `http://localhost:3000` by default. Logs confirm the listening address.

### The extension requires no build step

The extension is plain JavaScript — no bundler, no TypeScript transpilation, no npm install. The files in `apps/mammoth/extension/` are loaded directly by Chrome.

### Run the test suite

```bash
# From apps/mammoth/
cargo test --workspace
```

Server-specific tests (including the `ext_stream_events` behavior) are in `apps/mammoth/crates/server/src/lib.rs` under `#[cfg(test)] mod tests`. They spawn an in-process test server using `TcpListener::bind("127.0.0.1:0")` to avoid port conflicts.

### Lint and format

```bash
cargo fmt --check          # verify formatting
cargo fmt                  # apply formatting
cargo clippy --workspace --all-targets -- -D warnings
```

### Pack the extension as a CRX (optional)

```bash
# First-time: generates extension.pem and extension.crx
google-chrome --pack-extension=$(pwd)/apps/mammoth/extension

# Subsequent releases: sign with the existing key
google-chrome --pack-extension=$(pwd)/apps/mammoth/extension \
              --pack-extension-key=$(pwd)/mammoth-extension.pem
```

Store `mammoth-extension.pem` outside the repository. It is the extension's signing identity.

---

## 12. Debugging

### Background service worker (background.js)

1. Go to `chrome://extensions`.
2. Find the Mammoth card.
3. Click **Service Worker** (blue link under the extension ID).
4. A DevTools window opens for the service worker context.
5. Check the **Console** tab for `[Mammoth]` prefixed log messages.

Useful log messages:

| Message | Meaning |
|---------|---------|
| `[Mammoth] SSE connected to http://localhost:3000/ext/events` | Connection established successfully |
| `[Mammoth] SSE connection error — will retry automatically.` | Server unreachable; browser will retry with back-off |

To inspect `chrome.storage.local`:

```js
// Run in the service worker console:
chrome.storage.local.get(null, console.log);
// Expected: { serverBase: "http://localhost:3000" }
```

To manually trigger a reconnect:

```js
// Run in the service worker console:
connectToMammoth();
```

To change the server URL without reloading:

```js
// Run in the service worker console:
chrome.runtime.sendMessage({
  type: "mammoth_config_set_server",
  serverBase: "http://localhost:8080"
});
```

### Content script (content.js)

1. Open any web page.
2. Open Chrome DevTools (`F12`).
3. In the **Console** tab, select the page's origin from the context dropdown (not the `top` frame).

   > The content script runs in the page's world (but an isolated JS context), so its logs appear in the page console.

4. Send a test `mammoth_get_page_context` message from the console to verify the content script is loaded:

   ```js
   // Run in the DevTools console of the page (not the extension context):
   chrome.runtime.sendMessage({ type: "mammoth_get_page_context" }, console.log);
   // Expected: { ok: true, context: { url: ..., title: ..., ... } }
   ```

### Popup (popup.js)

1. Right-click the Mammoth toolbar icon.
2. Select **Inspect Popup**.
3. DevTools opens for the popup context.
4. Check the **Console** for errors. Check the **Network** tab to verify the `/health` fetch.

### Common errors and fixes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Status shows "Disconnected" on popup open | Server not running | Start `mammoth-cli serve` |
| Status shows "Disconnected" + service worker console shows `SSE connection error` | Server running but `serverBase` points to wrong port | Update via `mammoth_config_set_server` or reset `chrome.storage.local` |
| Badge `"!"` visible but no approval card in popup | Popup was closed when approval arrived | Re-open popup; if no card appears, approval card persistence is not yet implemented — check server logs for the pending approval |
| `net::ERR_BLOCKED_BY_CLIENT` in network tab | Ad blocker or firewall blocking localhost requests | Disable the extension for `localhost` or add an exception |
| `Extension manifest must request permission to access the respective host` | `host_permissions` missing a port or protocol | Edit `manifest.json` and reload the extension |
| Content script not responding to messages | `window.__mammothContentScriptLoaded` guard triggered twice | This indicates double-injection; inspect via DevTools — confirm the guard flag is set: `window.__mammothContentScriptLoaded` |
| Popup shows `Error: Server returned 404` | Sending to an endpoint that doesn't exist on the server | Verify server is running the correct version — check `GET /health` first |
| Service worker terminated between messages | MV3 idle suspension | Normal behavior; the worker wakes on the next event. If SSE events are lost during suspension, see planned feature "keepalive ping" |

### Testing the SSE stream directly

```bash
# Using curl — watch raw SSE frames:
curl -N http://localhost:3000/ext/events

# Send a test message that will echo back as ExtEvent::Message:
curl -X POST http://localhost:3000/ext/message \
     -H "Content-Type: application/json" \
     -d '{"message": "hello from curl"}'

# The curl SSE stream should print:
# event: message
# data: {"type":"message","content":"hello from curl"}
```

### Testing the approval flow directly

```bash
# This requires triggering an approval from the AICP runtime.
# In development, you can manually broadcast an ApprovalRequest
# by adding a test endpoint to the server (not included in the current code).
# Alternatively, trigger a capability execution with a policy that requires approval
# via the AICP Python runtime (packages/runtime/).
```

---

## 13. Future Roadmap

The following features are planned but not yet implemented. Sources: `ROADMAP.md` phases 3–9, inline `// Future:` comments in the extension source, and the `content.js` file comment:

> _"Listening for Mammoth annotation commands injected by the background service worker (future: highlight elements, show tooltips, etc.)"_

### Near-term (v0.4.0 — Mammoth + Agent Integration)

| Feature | Description | Files affected |
|---------|-------------|----------------|
| **Page context injection** | Automatically include `capturePageContext()` result in the AI prompt payload when sending a message | `popup.js`, `background.js`, `content.js`, `POST /ext/message` body |
| **Approval card persistence** | Queue `mammoth_approval_request` events in the service worker; replay them when the popup opens so no approval is lost when the popup was closed | `background.js`, `popup.js` |
| **Element annotation from server** | Implement `ExtEvent::Highlight` variant on the server; background.js forwards it to content.js `mammoth_highlight` | `channel.rs`, `server/src/lib.rs`, `background.js` |
| **Settings page** | `options.html` + `options.js` for configuring `serverBase`, clearing chat history, and viewing connection logs | `options.html`, `options.js`, `manifest.json` (add `"options_page"`) |

### Medium-term (v0.5.0 — Perception)

| Feature | Description | Files affected |
|---------|-------------|----------------|
| **Full a11y tree capture** | Expand `capturePageContext()` to walk the accessibility tree and return a structured representation of interactive elements | `content.js`, `POST /ext/message` |
| **Screenshot capture** | Use `chrome.tabs.captureVisibleTab()` in the service worker to attach a screenshot to the AI prompt | `background.js`, `manifest.json` (add permission) |
| **Behavioral signals** | Record DOM mutations, scroll events, and click events in `content.js` and emit them as structured signals | `content.js`, new `ExtEvent::Signal` variant |
| **DOM observation** | Use `MutationObserver` in `content.js` to emit page state changes proactively (not only on request) | `content.js` |

### Multi-tab and session support (v0.5.0–v0.6.0)

| Feature | Description | Files affected |
|---------|-------------|----------------|
| **Per-tab session routing** | Associate each browser tab with a Mammoth session ID; route page context and approvals per-tab rather than globally | `background.js`, `content.js`, server `ExtEvent` |
| **Multi-tab awareness** | When multiple tabs are open, the AI can reason about and act on multiple pages simultaneously | `background.js`, server |

### Cross-browser compatibility (v0.9.0)

| Feature | Description | Files affected |
|---------|-------------|----------------|
| **Firefox / Edge compatibility** | Adapt `manifest.json` to MV3 cross-browser conventions; feature-detect `chrome.*` vs `browser.*` namespace via a thin polyfill | `manifest.json`, all JS files |

### v1.0.0 vision

By v1.0.0 (Agentic Web OS), the extension is expected to serve as a fully-capable perception and action surface:

- The AI can **see** any page (via a11y tree, screenshots, behavioral signals from the Perception plane — module #6).
- The AI can **annotate** pages for operator review before acting.
- The AI can **fill forms**, navigate multi-step flows, and trigger browser automation as AICP capabilities.
- Approvals and supervision are integrated with the full 5-view supervision dashboard (module #7) that is being absorbed into Mammoth.

---

## Known Gaps

The following details were missing or unclear from the source at the time this guide was written. Future engineers should be aware of them:

1. **`icons/` directory not present.** `apps/mammoth/extension/icons/` is referenced in `manifest.json` (`icons/icon16.png`, `icons/icon48.png`, `icons/icon128.png`) but the directory and PNG files do not exist in the repository. Loading the unpacked extension fails until placeholder icons are created.

2. **Server port not configurable via config file.** The Mammoth server binds to port 3000 by default. There is no `serverPort` field in `AicpConfig` or any settings file. The extension default `DEFAULT_SERVER = "http://localhost:3000"` is a hardcoded constant in `background.js:12`. To use a different port, both the server startup command and the extension's `serverBase` must be changed manually.

3. **`approval_decision` JSON is sent as a plain string.** The `POST /ext/message` endpoint accepts `{ "message": String }`. When an approval decision is sent from `popup.js`, it is serialized to JSON and passed as the `message` string value. The server must detect and parse this JSON-within-JSON. The routing of `approval_decision` payloads from the `ext_send_message` handler to the AICP approval lifecycle is referenced in `lib.rs:569` as a comment but is not shown in the current server code — future implementors must verify this routing exists before relying on it.

4. **`risk_summary` not forwarded over SSE.** The `ApprovalRequest` Rust struct has a `risk_summary: Option<String>` field, but `ExtEvent::ApprovalRequest` does not include it. The popup approval card shows only `capability_name` and `description`. If risk metadata is needed in the browser UI, `ExtEvent::ApprovalRequest` must be extended.

5. **No event replay on reconnect.** The `ExtBroadcast` channel has a capacity of 64. Events emitted while no SSE client is connected (e.g., during service worker suspension) are dropped. There is no replay-from-cursor mechanism. Approval requests that arrive during an SSE gap are lost unless the AICP runtime also surfaces them through a polling endpoint.

6. **`options.js` / `options.html` not present.** Referenced as a planned feature in the original extension comments. The `manifest.json` does not declare `"options_page"` or `"options_ui"`. There is currently no UI for changing `serverBase` without using the DevTools console.

---

*Guide generated from source at `apps/mammoth/` — Mammoth v0.1.0 / AICP v0.3.0 (2026-04-05).*
