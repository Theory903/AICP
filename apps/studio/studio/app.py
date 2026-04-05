"""Thin Studio seed for approvals and audit viewing."""

from __future__ import annotations

from enum import Enum
from html import escape
from typing import Any

from aicp_runtime.persistence.file import FileRuntimeStore
from aicp_runtime.persistence.memory import InMemoryRuntimeStore
from aicp_runtime.persistence.sqlite import SqliteRuntimeStore
from aicp_runtime.services import ApprovalService, AuditService
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator


class ApprovalDecision(str, Enum):
    """Allowed Studio approval decisions."""

    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalDecisionRequest(BaseModel):
    """Approval decision payload for Studio actions."""

    decision: ApprovalDecision
    approver: str = Field(min_length=1)
    reason: str | None = None
    modified_arguments: dict[str, Any] | None = None

    @field_validator("approver", mode="before")
    @classmethod
    def _normalize_approver(cls, value: Any) -> str:
        approver = str(value or "").strip()
        if not approver:
            raise ValueError("approver cannot be empty")
        return approver

    @field_validator("reason", mode="before")
    @classmethod
    def _normalize_reason(cls, value: Any) -> str | None:
        if value is None:
            return None
        reason = str(value).strip()
        return reason or None


def build_workflow_replay(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build a replay-oriented workflow timeline from audit entries."""
    title_map = {
        "workflow_created": "Workflow created",
        "workflow_step_executed": "Workflow step executed",
        "approval_request_created": "Approval requested",
        "approval_decision_made": "Approval decided",
        "workflow_resume_rejected": "Workflow resume rejected",
        "workflow_resumed_after_approval": "Workflow resumed after approval",
    }

    replay: list[dict[str, Any]] = []
    for entry in sorted(history, key=lambda item: str(item.get("timestamp", ""))):
        metadata = entry.get("metadata") or {}
        event_type = str(entry.get("event_type") or "event")
        replay.append(
            {
                "id": entry.get("id"),
                "timestamp": entry.get("timestamp"),
                "event_type": event_type,
                "title": title_map.get(event_type, event_type),
                "actor": entry.get("actor"),
                "status": entry.get("status"),
                "workflow_id": entry.get("workflow_id"),
                "step_id": entry.get("step_id"),
                "approval_request_id": entry.get("approval_request_id"),
                "approval_decision_id": entry.get("approval_decision_id"),
                "summary": _build_replay_summary(entry, metadata),
            }
        )
    return replay


def _build_replay_summary(entry: dict[str, Any], metadata: dict[str, Any]) -> str:
    """Build a human-readable summary for a replay item."""
    event_type = entry.get("event_type")

    if event_type == "workflow_created":
        return "Workflow entered runtime and was persisted."

    if event_type == "approval_request_created":
        return metadata.get("message") or "Approval required before continuation."

    if event_type == "approval_decision_made":
        decision = metadata.get("decision")
        reason = metadata.get("reason")
        if decision and reason:
            return f"Decision: {decision}. Reason: {reason}"
        if decision:
            return f"Decision: {decision}"
        return "Approval decision recorded."

    if event_type == "workflow_step_executed":
        if metadata.get("requires_confirmation"):
            return "Step executed and is waiting for approval."
        if metadata.get("success"):
            return "Step completed successfully."
        return metadata.get("error") or "Step execution failed."

    if event_type == "workflow_resume_rejected":
        return "Workflow could not continue because approval was not granted."

    if event_type == "workflow_resumed_after_approval":
        return metadata.get("error") or "Workflow resumed after approval."

    return "Runtime event recorded."


def create_studio_app(runtime_store=None) -> FastAPI:
    """Create a lightweight Studio app for approvals and audit viewing."""
    store = runtime_store or InMemoryRuntimeStore()
    audit_service = AuditService(store)
    approval_service = ApprovalService(store, audit_service=audit_service)

    app = FastAPI(title="AICP Studio", version="0.3.0")

    @app.get("/", response_class=HTMLResponse)
    async def studio_dashboard() -> str:
        return _dashboard_html()

    @app.get("/api/approvals")
    async def approvals_api() -> list[dict[str, Any]]:
        approvals = await approval_service.list_approvals()
        return sorted(
            approvals, key=lambda item: str(item.get("requested_at", "")), reverse=True
        )

    @app.post("/api/approvals/{approval_id}/decide")
    async def decide_approval_api(
        approval_id: str,
        request: ApprovalDecisionRequest,
    ) -> dict[str, Any]:
        try:
            return await approval_service.decide(
                approval_id,
                decision=request.decision.value,
                approver=request.approver,
                reason=request.reason,
                modified_arguments=request.modified_arguments,
            )
        except ValueError as exc:
            message = str(exc)
            lowered = message.lower()
            if "not found" in lowered:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=message,
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            ) from exc

    @app.get("/api/history")
    async def history_api() -> list[dict[str, Any]]:
        history = await audit_service.list_entries()
        return sorted(
            history, key=lambda item: str(item.get("timestamp", "")), reverse=True
        )

    @app.get("/api/workflows")
    async def workflows_api() -> list[dict[str, Any]]:
        workflows = await store.list_workflows()
        serialized = [
            workflow.model_dump(mode="json", exclude_none=True)
            for workflow in workflows
        ]
        return sorted(
            serialized, key=lambda item: str(item.get("updated_at", "")), reverse=True
        )

    @app.get("/api/workflows/{workflow_id}")
    async def workflow_detail_api(workflow_id: str) -> dict[str, Any]:
        workflow = await store.get_workflow(workflow_id)
        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")

        history = await audit_service.list_entries(workflow_id=workflow_id)
        replay = build_workflow_replay(history)

        return {
            "workflow": workflow.model_dump(mode="json", exclude_none=True),
            "history": history,
            "replay": replay,
        }

    @app.get("/workflows/{workflow_id}", response_class=HTMLResponse)
    async def workflow_detail_page(workflow_id: str) -> str:
        safe_workflow_id = escape(workflow_id)
        return _workflow_detail_html(safe_workflow_id)

    return app


def create_file_backed_studio_app(store_path: str) -> FastAPI:
    """Create a Studio app backed by a file runtime store."""
    return create_studio_app(runtime_store=FileRuntimeStore(store_path))


def create_sqlite_backed_studio_app(store_path: str = ".aicp-studio.db") -> FastAPI:
    """Create a Studio app backed by a SQLite runtime store."""
    return create_studio_app(runtime_store=SqliteRuntimeStore(store_path))


def _dashboard_html() -> str:
    """Render the Studio dashboard HTML."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AICP Studio</title>
  <style>
    :root {
      --bg: #0a0c12;
      --panel: #121722;
      --panel-2: #171d2a;
      --border: #283041;
      --text: #dde4f3;
      --muted: #8f9ab0;
      --gold: #d6a547;
      --green: #4abf7c;
      --red: #d86a6a;
      --blue: #74a7ff;
      --mono: "IBM Plex Mono", "SFMono-Regular", monospace;
      --sans: "Inter", "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background:
        radial-gradient(circle at top right, rgba(214,165,71,0.12), transparent 28%),
        linear-gradient(180deg, #0a0c12 0%, #0f1320 100%);
      color: var(--text);
      font-family: var(--sans);
    }
    .shell {
      max-width: 1200px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }
    .hero {
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 20px;
      margin-bottom: 20px;
    }
    .hero-card, .panel {
      background: rgba(18, 23, 34, 0.88);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 20px;
      backdrop-filter: blur(14px);
      box-shadow: 0 18px 60px rgba(0, 0, 0, 0.24);
    }
    .eyebrow {
      font: 12px/1.4 var(--mono);
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--gold);
      margin-bottom: 10px;
    }
    h1 {
      margin: 0 0 10px;
      font-size: clamp(32px, 5vw, 52px);
      line-height: 1;
    }
    .lede {
      margin: 0;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.65;
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
      margin-top: 18px;
    }
    .stat {
      background: var(--panel-2);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px;
    }
    .stat .label {
      color: var(--muted);
      font: 11px/1.4 var(--mono);
      text-transform: uppercase;
      letter-spacing: 0.1em;
    }
    .stat .value {
      font-size: 28px;
      margin-top: 8px;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
    }
    h2 {
      margin: 0 0 14px;
      font-size: 18px;
    }
    .list {
      display: grid;
      gap: 12px;
    }
    .item {
      background: var(--panel-2);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px;
    }
    .item-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-bottom: 8px;
    }
    .item-title {
      font-weight: 600;
    }
    .badge {
      font: 11px/1.4 var(--mono);
      letter-spacing: 0.08em;
      text-transform: uppercase;
      padding: 4px 8px;
      border-radius: 999px;
      border: 1px solid var(--border);
      color: var(--muted);
    }
    .badge.pending { color: var(--gold); border-color: rgba(214,165,71,0.35); }
    .badge.success { color: var(--green); border-color: rgba(74,191,124,0.35); }
    .badge.failure { color: var(--red); border-color: rgba(216,106,106,0.35); }
    .meta {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
    }
    .actions {
      display: flex;
      gap: 8px;
      margin-top: 12px;
      flex-wrap: wrap;
    }
    .button {
      border: 1px solid var(--border);
      background: transparent;
      color: var(--text);
      border-radius: 10px;
      padding: 8px 12px;
      cursor: pointer;
      font: 12px/1.2 var(--mono);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .button.approve { border-color: rgba(74,191,124,0.4); color: var(--green); }
    .button.reject { border-color: rgba(216,106,106,0.4); color: var(--red); }
    .empty {
      color: var(--muted);
      font-size: 14px;
      padding: 20px 0;
    }
    .error {
      color: var(--red);
      white-space: pre-wrap;
    }
    a { color: var(--blue); text-decoration: none; }
    @media (max-width: 860px) {
      .hero, .grid { grid-template-columns: 1fr; }
      .stats { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="hero-card">
        <div class="eyebrow">AICP Studio</div>
        <h1>Governed runtime control plane</h1>
        <p class="lede">A thin operational surface for approvals, audit, and workflow visibility. This seed stays intentionally small while still showing the core control-plane shape.</p>
      </div>
      <div class="hero-card">
        <div class="eyebrow">Current Signal</div>
        <div class="stats">
          <div class="stat"><div class="label">Pending approvals</div><div class="value" id="pending-count">0</div></div>
          <div class="stat"><div class="label">Audit events</div><div class="value" id="history-count">0</div></div>
          <div class="stat"><div class="label">Workflows</div><div class="value" id="workflow-count">0</div></div>
        </div>
      </div>
    </section>
    <section class="grid">
      <div class="panel">
        <h2>Approval Inbox</h2>
        <div id="approvals" class="list"><div class="empty">Loading approvals...</div></div>
      </div>
      <div class="panel">
        <h2>Workflow Timeline</h2>
        <div id="workflows" class="list"><div class="empty">Loading workflows...</div></div>
      </div>
      <div class="panel" style="grid-column: 1 / -1;">
        <h2>Audit History</h2>
        <div id="history" class="list"><div class="empty">Loading audit entries...</div></div>
      </div>
    </section>
  </div>
  <script>
    function escapeHtml(value) {
      return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }

    function badgeClass(status) {
      if (status === 'approved' || status === 'success' || status === 'completed') return 'success';
      if (status === 'rejected' || status === 'denied' || status === 'failed' || status === 'failure') return 'failure';
      return 'pending';
    }

    function renderList(el, items, renderItem, emptyText) {
      if (!items.length) {
        el.innerHTML = `<div class="empty">${escapeHtml(emptyText)}</div>`;
        return;
      }
      el.innerHTML = items.map(renderItem).join('');
    }

    async function fetchJson(url, options) {
      const response = await fetch(url, options);
      let payload = null;
      try {
        payload = await response.json();
      } catch (_) {
        payload = null;
      }
      if (!response.ok) {
        const detail = payload && payload.detail ? payload.detail : `Request failed: ${response.status}`;
        throw new Error(detail);
      }
      return payload;
    }

    async function decideApproval(approvalId, decision) {
      const approver = window.prompt('Approver identity', 'studio-operator');
      if (!approver) return;
      const reason = window.prompt(
        'Reason',
        decision === 'approved' ? 'Approved from Studio' : 'Rejected from Studio'
      );

      try {
        await fetchJson(`/api/approvals/${approvalId}/decide`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision, approver, reason })
        });
        await loadStudio();
      } catch (error) {
        window.alert(`Approval action failed: ${error.message}`);
      }
    }

    async function loadStudio() {
      try {
        const [approvals, history, workflows] = await Promise.all([
          fetchJson('/api/approvals'),
          fetchJson('/api/history'),
          fetchJson('/api/workflows')
        ]);

        document.getElementById('pending-count').textContent =
          approvals.filter(a => a.status === 'pending').length;
        document.getElementById('history-count').textContent = history.length;
        document.getElementById('workflow-count').textContent = workflows.length;

        renderList(
          document.getElementById('approvals'),
          approvals,
          (item) => `
            <div class="item">
              <div class="item-head">
                <div class="item-title">${escapeHtml(item.capability_name || 'unknown')}</div>
                <span class="badge ${badgeClass(item.status)}">${escapeHtml(item.status || 'pending')}</span>
              </div>
              <div class="meta">
                Requester: ${escapeHtml(item.requester || 'unknown')}<br>
                Requested at: ${escapeHtml(item.requested_at || 'n/a')}<br>
                Workflow: ${escapeHtml(item.workflow_id || 'n/a')}
              </div>
              ${item.status === 'pending'
                ? `<div class="actions">
                    <button class="button approve" onclick="decideApproval('${escapeHtml(item.id)}','approved')">Approve</button>
                    <button class="button reject" onclick="decideApproval('${escapeHtml(item.id)}','rejected')">Reject</button>
                  </div>`
                : ''}
            </div>`,
          'No approvals waiting.'
        );

        renderList(
          document.getElementById('workflows'),
          workflows,
          (item) => `
            <div class="item">
              <div class="item-head">
                <div class="item-title">${escapeHtml(item.name || item.id || 'workflow')}</div>
                <span class="badge ${badgeClass(item.status)}">${escapeHtml(item.status || 'unknown')}</span>
              </div>
              <div class="meta">
                Workflow ID: ${escapeHtml(item.id || 'n/a')}<br>
                Updated: ${escapeHtml(item.updated_at || 'n/a')}<br>
                Steps: ${Array.isArray(item.steps) ? item.steps.length : 0}<br>
                <a href="/workflows/${encodeURIComponent(item.id)}">Open workflow detail</a>
              </div>
            </div>`,
          'No workflows tracked yet.'
        );

        renderList(
          document.getElementById('history'),
          history,
          (item) => `
            <div class="item">
              <div class="item-head">
                <div class="item-title">${escapeHtml(item.event_type || 'event')}</div>
                <span class="badge ${badgeClass(item.status || 'pending')}">${escapeHtml(item.status || 'recorded')}</span>
              </div>
              <div class="meta">
                Actor: ${escapeHtml(item.actor || 'unknown')}<br>
                Timestamp: ${escapeHtml(item.timestamp || 'n/a')}<br>
                Workflow: ${escapeHtml(item.workflow_id || 'n/a')}<br>
                Approval: ${escapeHtml(item.approval_request_id || 'n/a')}
              </div>
            </div>`,
          'No audit events yet.'
        );
      } catch (error) {
        document.getElementById('approvals').innerHTML =
          `<div class="empty error">Failed to load Studio data: ${escapeHtml(error.message)}</div>`;
        document.getElementById('workflows').innerHTML = '';
        document.getElementById('history').innerHTML = '';
      }
    }

    loadStudio();
  </script>
</body>
</html>"""


def _workflow_detail_html(workflow_id: str) -> str:
    """Render the workflow detail page HTML."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Workflow Detail</title>
  <style>
    body {{ margin: 0; background: #0b0f17; color: #e6ecf8; font-family: Inter, sans-serif; }}
    .wrap {{ max-width: 980px; margin: 0 auto; padding: 32px 20px 48px; }}
    .card {{ background: #141a26; border: 1px solid #263042; border-radius: 16px; padding: 20px; margin-bottom: 20px; }}
    .eyebrow {{ color: #d6a547; font: 12px/1.4 monospace; text-transform: uppercase; letter-spacing: 0.12em; }}
    h1 {{ margin: 10px 0 6px; font-size: 36px; }}
    .muted {{ color: #98a4ba; }}
    .timeline {{ display: grid; gap: 12px; margin-top: 16px; }}
    .event {{ background: #1a2231; border: 1px solid #2c374b; border-radius: 12px; padding: 14px; }}
    .title {{ font-weight: 600; margin-bottom: 6px; }}
    .summary {{ margin-top: 8px; color: #c8d1e0; }}
    a {{ color: #7db2ff; text-decoration: none; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <div class="eyebrow">Workflow Detail</div>
      <h1 id="workflow-name">{workflow_id}</h1>
      <p class="muted">Workflow detail and audit timeline for <strong>{workflow_id}</strong>.</p>
      <p><a href="/">Back to Studio</a></p>
    </div>
    <div class="card">
      <div class="eyebrow">Timeline</div>
      <div id="timeline" class="timeline"><div class="muted">Loading workflow timeline...</div></div>
    </div>
  </div>
  <script>
    function escapeHtml(value) {{
      return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }}

    async function fetchJson(url) {{
      const response = await fetch(url);
      const payload = await response.json();
      if (!response.ok) {{
        throw new Error(payload && payload.detail ? payload.detail : `Request failed: ${{response.status}}`);
      }}
      return payload;
    }}

    async function loadWorkflow() {{
      try {{
        const payload = await fetchJson('/api/workflows/{workflow_id}');
        if (payload.workflow) {{
          document.getElementById('workflow-name').textContent =
            `${{payload.workflow.name}} (${{payload.workflow.id}})`;
        }}
        const timeline = document.getElementById('timeline');
        const history = payload.replay || [];
        if (!history.length) {{
          timeline.innerHTML = '<div class="muted">No timeline events recorded yet.</div>';
          return;
        }}
        timeline.innerHTML = history.map((item) => `
          <div class="event">
            <div class="title">${{escapeHtml(item.title || item.event_type || 'event')}}</div>
            <div class="muted">
              ${{escapeHtml(item.timestamp || 'n/a')}} · actor=${{escapeHtml(item.actor || 'unknown')}}
              ${{item.status ? ' · status=' + escapeHtml(item.status) : ''}}
            </div>
            <div class="summary">${{escapeHtml(item.summary || '')}}</div>
          </div>
        `).join('');
      }} catch (error) {{
        document.getElementById('timeline').innerHTML =
          `<div class="muted">Failed to load workflow: ${{escapeHtml(error.message)}}</div>`;
      }}
    }}

    loadWorkflow();
  </script>
</body>
</html>"""
