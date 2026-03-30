"""Thin Studio seed for approvals and audit viewing."""

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import HTMLResponse

from aicp_runtime.persistence.file import FileRuntimeStore
from aicp_runtime.persistence.memory import InMemoryRuntimeStore
from aicp_runtime.persistence.sqlite import SqliteRuntimeStore
from aicp_runtime.services import ApprovalService, AuditService


class ApprovalDecisionRequest(BaseModel):
    """Approval decision payload for Studio actions."""

    decision: str
    approver: str
    reason: str | None = None
    modified_arguments: dict | None = None


def build_workflow_replay(history: list[dict]) -> list[dict]:
    """Build a simple replay-oriented timeline from audit entries."""
    title_map = {
        "workflow_created": "Workflow created",
        "approval_request_created": "Approval requested",
        "approval_decision_made": "Approval decided",
    }

    replay = []
    for entry in history:
        replay.append(
            {
                "id": entry.get("id"),
                "timestamp": entry.get("timestamp"),
                "event_type": entry.get("event_type"),
                "title": title_map.get(entry.get("event_type"), entry.get("event_type", "event")),
                "actor": entry.get("actor"),
                "status": entry.get("status"),
                "workflow_id": entry.get("workflow_id"),
                "approval_request_id": entry.get("approval_request_id"),
            }
        )
    return replay


def create_studio_app(runtime_store=None) -> FastAPI:
    store = runtime_store or InMemoryRuntimeStore()
    audit_service = AuditService(store)
    approval_service = ApprovalService(store, audit_service=audit_service)

    app = FastAPI(title="AICP Studio")

    @app.get("/", response_class=HTMLResponse)
    async def studio_dashboard() -> str:
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
        <p class="lede">A thin operational surface for approvals, audit, and workflow visibility. This seed proves the control-plane shape without pretending the UI is the product center.</p>
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
    function badgeClass(status) {
      if (status === 'approved' || status === 'success' || status === 'completed') return 'success';
      if (status === 'denied' || status === 'failed' || status === 'failure') return 'failure';
      return 'pending';
    }

    function renderList(el, items, renderItem, emptyText) {
      if (!items.length) {
        el.innerHTML = `<div class="empty">${emptyText}</div>`;
        return;
      }
      el.innerHTML = items.map(renderItem).join('');
    }

    async function decideApproval(approvalId, decision) {
      const approver = window.prompt('Approver identity', 'studio-operator');
      if (!approver) return;
      const reason = window.prompt('Reason', decision === 'approved' ? 'Approved from Studio' : 'Rejected from Studio');
      await fetch(`/api/approvals/${approvalId}/decide`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, approver, reason })
      });
      await loadStudio();
    }

    async function loadStudio() {
      const [approvalsRes, historyRes, workflowsRes] = await Promise.all([
        fetch('/api/approvals'),
        fetch('/api/history'),
        fetch('/api/workflows')
      ]);
      const approvals = await approvalsRes.json();
      const history = await historyRes.json();
      const workflows = await workflowsRes.json();

      document.getElementById('pending-count').textContent = approvals.filter(a => a.status === 'pending').length;
      document.getElementById('history-count').textContent = history.length;
      document.getElementById('workflow-count').textContent = workflows.length;

      renderList(
        document.getElementById('approvals'),
        approvals,
        (item) => `
          <div class="item">
            <div class="item-head">
              <div class="item-title">${item.capability_name}</div>
              <span class="badge ${badgeClass(item.status)}">${item.status}</span>
            </div>
            <div class="meta">Requester: ${item.requester || 'unknown'}<br>Requested at: ${item.requested_at || 'n/a'}<br>Workflow: ${item.workflow_id || 'n/a'}</div>
            ${item.status === 'pending' ? `<div class="actions"><button class="button approve" onclick="decideApproval('${item.id}','approved')">Approve</button><button class="button reject" onclick="decideApproval('${item.id}','denied')">Reject</button></div>` : ''}
          </div>`,
        'No approvals waiting.'
      );

      renderList(
        document.getElementById('workflows'),
        workflows,
        (item) => `
          <div class="item">
            <div class="item-head">
              <div class="item-title">${item.name}</div>
              <span class="badge ${badgeClass(item.status)}">${item.status}</span>
            </div>
            <div class="meta">Workflow ID: ${item.id}<br>Updated: ${item.updated_at || 'n/a'}<br>Steps: ${item.steps.length}<br><a href="/workflows/${item.id}">Open workflow detail</a></div>
          </div>`,
        'No workflows tracked yet.'
      );

      renderList(
        document.getElementById('history'),
        history,
        (item) => `
          <div class="item">
            <div class="item-head">
              <div class="item-title">${item.event_type}</div>
              <span class="badge ${badgeClass(item.status || 'pending')}">${item.status || 'recorded'}</span>
            </div>
            <div class="meta">Actor: ${item.actor}<br>Timestamp: ${item.timestamp}<br>Workflow: ${item.workflow_id || 'n/a'}<br>Approval: ${item.approval_request_id || 'n/a'}</div>
          </div>`,
        'No audit events yet.'
      );
    }

    loadStudio().catch((error) => {
      document.getElementById('approvals').innerHTML = `<div class="empty">Failed to load Studio data: ${error}</div>`;
    });
  </script>
</body>
</html>"""

    @app.get("/api/approvals")
    async def approvals_api():
        return await approval_service.list_approvals()

    @app.post("/api/approvals/{approval_id}/decide")
    async def decide_approval_api(approval_id: str, request: ApprovalDecisionRequest):
        return await approval_service.decide(
            approval_id,
            decision=request.decision,
            approver=request.approver,
            reason=request.reason,
            modified_arguments=request.modified_arguments,
        )

    @app.get("/api/history")
    async def history_api():
        return await audit_service.list_entries()

    @app.get("/api/workflows")
    async def workflows_api():
        return [workflow.model_dump(mode="json") for workflow in await store.list_workflows()]

    @app.get("/api/workflows/{workflow_id}")
    async def workflow_detail_api(workflow_id: str):
        workflow = await store.get_workflow(workflow_id)
        history = await audit_service.list_entries(workflow_id=workflow_id)
        return {
            "workflow": workflow.model_dump(mode="json") if workflow is not None else None,
            "history": history,
            "replay": build_workflow_replay(history),
        }

    @app.get("/workflows/{workflow_id}", response_class=HTMLResponse)
    async def workflow_detail_page(workflow_id: str) -> str:
        return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
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
    a {{ color: #7db2ff; text-decoration: none; }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"card\">
      <div class=\"eyebrow\">Workflow Detail</div>
      <h1 id=\"workflow-name\">{workflow_id}</h1>
      <p class=\"muted\">Workflow detail and audit timeline for <strong>{workflow_id}</strong>.</p>
      <p><a href=\"/\">Back to Studio</a></p>
    </div>
    <div class=\"card\">
      <div class=\"eyebrow\">Timeline</div>
      <div id=\"timeline\" class=\"timeline\"><div class=\"muted\">Loading workflow timeline...</div></div>
    </div>
  </div>
  <script>
    async function loadWorkflow() {{
      const response = await fetch('/api/workflows/{workflow_id}');
      const payload = await response.json();
      if (payload.workflow) {{
        document.getElementById('workflow-name').textContent = payload.workflow.name + ' (' + payload.workflow.id + ')';
      }}
      const timeline = document.getElementById('timeline');
      const history = payload.replay || [];
      if (!history.length) {{
        timeline.innerHTML = '<div class=\"muted\">No timeline events recorded yet.</div>';
        return;
      }}
      timeline.innerHTML = history.map((item) => `<div class=\"event\"><strong>${{item.title}}</strong><br><span class=\"muted\">${{item.timestamp}} · actor=${{item.actor || 'unknown'}}${{item.status ? ' · status=' + item.status : ''}}</span></div>`).join('');
    }}
    loadWorkflow();
  </script>
</body>
</html>"""

    return app


def create_file_backed_studio_app(store_path: str) -> FastAPI:
    """Create a Studio app backed by a file runtime store."""
    return create_studio_app(runtime_store=FileRuntimeStore(store_path))


def create_sqlite_backed_studio_app(store_path: str = ".aicp-studio.db") -> FastAPI:
    """Create a Studio app backed by a SQLite runtime store."""
    return create_studio_app(runtime_store=SqliteRuntimeStore(store_path))
