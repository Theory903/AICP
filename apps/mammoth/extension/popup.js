/**
 * Mammoth Extension — popup script
 *
 * Manages the popup UI state:
 *  - Displays conversation messages.
 *  - Sends user messages to the background service worker.
 *  - Renders approval requests and collects human decisions.
 */

const messagesEl = document.getElementById("messages");
const inputEl = document.getElementById("msg-input");
const sendBtn = document.getElementById("send-btn");
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");

// ---------------------------------------------------------------------------
// Connection status
// ---------------------------------------------------------------------------

function setConnected(connected) {
  if (connected) {
    statusDot.classList.remove("disconnected");
    statusText.textContent = "Connected";
  } else {
    statusDot.classList.add("disconnected");
    statusText.textContent = "Disconnected";
  }
}

// Check connection by pinging the server
chrome.storage.local.get(["serverBase"], (result) => {
  const base = result.serverBase || "http://localhost:3000";
  fetch(`${base}/health`, { signal: AbortSignal.timeout(2000) })
    .then((r) => setConnected(r.ok))
    .catch(() => setConnected(false));
});

// ---------------------------------------------------------------------------
// Message display
// ---------------------------------------------------------------------------

function appendMessage(role, text) {
  const el = document.createElement("div");
  el.className = `msg ${role}`;
  el.textContent = text;
  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return el;
}

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

// ---------------------------------------------------------------------------
// Background message listener
// ---------------------------------------------------------------------------

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "mammoth_message") {
    const text =
      typeof message.payload?.content === "string"
        ? message.payload.content
        : JSON.stringify(message.payload);
    appendMessage("assistant", text);
    setConnected(true);
  }

  if (message.type === "mammoth_approval_request") {
    appendApprovalRequest(message.payload);
  }
});

// ---------------------------------------------------------------------------
// Send message
// ---------------------------------------------------------------------------

async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text) return;
  inputEl.value = "";
  inputEl.style.height = "auto";
  sendBtn.disabled = true;
  appendMessage("user", text);

  try {
    const response = await chrome.runtime.sendMessage({
      type: "mammoth_send",
      text,
    });
    if (!response?.ok) {
      appendMessage("system", `Error: ${response?.error ?? "unknown"}`);
      setConnected(false);
    }
  } catch (err) {
    appendMessage("system", `Error: ${err.message}`);
    setConnected(false);
  } finally {
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

sendBtn.addEventListener("click", sendMessage);
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});
inputEl.addEventListener("input", () => {
  inputEl.style.height = "auto";
  inputEl.style.height = `${Math.min(inputEl.scrollHeight, 120)}px`;
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
