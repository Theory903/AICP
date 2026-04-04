/**
 * Mammoth Extension — background service worker (MV3)
 *
 * Responsibilities:
 *  1. Maintain a persistent SSE connection to the Mammoth Web channel
 *     extension bridge at `GET /ext/events`.
 *  2. Relay incoming `ExtEvent`s to the popup (and optionally content scripts).
 *  3. Forward outbound messages from the popup/content script to
 *     `POST /ext/message`.
 */

const DEFAULT_SERVER = "http://localhost:3000";

let serverBase = DEFAULT_SERVER;
let eventSource = null;

// ---------------------------------------------------------------------------
// SSE connection to Mammoth Web channel extension bridge
// ---------------------------------------------------------------------------

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
    // Show a badge so the user knows action is needed
    chrome.action.setBadgeText({ text: "!" });
    chrome.action.setBadgeBackgroundColor({ color: "#e53935" });
  });

  eventSource.onerror = () => {
    // Retry with exponential back-off handled by EventSource natively.
    console.warn("[Mammoth] SSE connection error — will retry automatically.");
  };

  eventSource.onopen = () => {
    console.info("[Mammoth] SSE connected to", url);
    chrome.action.setBadgeText({ text: "" });
  };
}

// ---------------------------------------------------------------------------
// Message relay: popup → Mammoth server
// ---------------------------------------------------------------------------

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "mammoth_send") {
    sendToMammoth(message.text)
      .then(() => sendResponse({ ok: true }))
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true; // keep channel open for async response
  }

  if (message.type === "mammoth_config_set_server") {
    serverBase = message.serverBase || DEFAULT_SERVER;
    chrome.storage.local.set({ serverBase });
    connectToMammoth();
    sendResponse({ ok: true });
    return true;
  }
});

async function sendToMammoth(text) {
  const res = await fetch(`${serverBase}/ext/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: text }),
  });
  if (!res.ok) {
    throw new Error(`Server returned ${res.status}`);
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function broadcastToPopup(message) {
  chrome.runtime.sendMessage(message).catch(() => {
    // Popup may not be open — ignore.
  });
}

function tryParseJson(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

chrome.storage.local.get(["serverBase"], (result) => {
  if (result.serverBase) {
    serverBase = result.serverBase;
  }
  connectToMammoth();
});
