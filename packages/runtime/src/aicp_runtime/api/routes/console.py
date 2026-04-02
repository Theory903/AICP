"""Agent console HTML route."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


def build_console_router() -> APIRouter:
    """Build a lightweight agent console route."""
    router = APIRouter(tags=["console"])

    @router.get("/console", response_class=HTMLResponse)
    async def agent_console() -> str:
        return _console_html()

    return router


def _console_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AICP Agent Console</title>
  <style>
    :root {
      --bg: #090b11;
      --panel: rgba(17, 22, 32, 0.82);
      --panel-2: #0d121b;
      --panel-3: #121a26;
      --muted: #97a1b5;
      --text: #edf2ff;
      --border: #263044;
      --accent: #f3f5f7;
      --green: #5ed39a;
      --amber: #f4c86b;
      --red: #f17d7d;
      --blue: #84a8ff;
      --shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
      --mono: "SFMono-Regular", "Menlo", monospace;
      --sans: "Inter", "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(87, 125, 255, 0.14), transparent 24%),
        radial-gradient(circle at top right, rgba(244, 200, 107, 0.1), transparent 22%),
        linear-gradient(180deg, #080a10 0%, #0d1119 100%);
      color: var(--text);
      font-family: var(--sans);
    }
    button, select, input, textarea { font: inherit; color: var(--text); }
    button { cursor: pointer; transition: 140ms ease; }
    .shell {
      max-width: 1480px;
      margin: 0 auto;
      padding: 28px;
      display: grid;
      gap: 22px;
    }
    .hero, .panel {
      border: 1px solid var(--border);
      background: var(--panel);
      border-radius: 28px;
      backdrop-filter: blur(18px);
      box-shadow: var(--shadow);
    }
    .hero {
      padding: 28px;
      display: grid;
      gap: 18px;
      grid-template-columns: 1.15fr 0.85fr;
    }
    .hero-actions {
      display: flex;
      justify-content: flex-end;
      align-items: flex-end;
      gap: 12px;
      flex-wrap: wrap;
    }
    .eyebrow {
      color: var(--muted);
      font: 12px/1.4 var(--mono);
      text-transform: uppercase;
      letter-spacing: 0.18em;
    }
    h1 {
      margin: 10px 0 0;
      font-size: clamp(34px, 5vw, 58px);
      line-height: 0.95;
    }
    h3 {
      margin: 0;
      font-size: 15px;
    }
    .lede {
      margin: 14px 0 0;
      color: var(--muted);
      line-height: 1.7;
      max-width: 780px;
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 12px;
      margin-top: 18px;
    }
    .stat, .card {
      border: 1px solid var(--border);
      background: var(--panel-2);
      border-radius: 22px;
      padding: 16px;
    }
    .stat-value { font-size: 28px; margin-top: 8px; }
    .button-primary, .button-secondary {
      border-radius: 18px;
      padding: 12px 16px;
      border: 1px solid var(--border);
    }
    .button-primary {
      background: var(--accent);
      color: #111318;
      font-weight: 600;
    }
    .button-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .button-secondary { background: transparent; }
    .panel { padding: 22px; }
    .panel-header {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-bottom: 16px;
      flex-wrap: wrap;
    }
    .panel-title { font-size: 19px; font-weight: 600; }
    .panel-subtitle { color: var(--muted); font-size: 14px; }
    .grid-main, .grid-dual {
      display: grid;
      gap: 22px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .stack { display: grid; gap: 14px; }
    .row {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
    }
    .row > * { flex: 1; }
    label, .small-label {
      display: block;
      font-size: 13px;
      color: var(--muted);
      margin-bottom: 8px;
    }
    select, input, textarea {
      width: 100%;
      border-radius: 18px;
      background: var(--panel-2);
      border: 1px solid var(--border);
      padding: 14px 16px;
      outline: none;
    }
    textarea {
      min-height: 220px;
      resize: vertical;
      font-family: var(--mono);
      font-size: 13px;
    }
    .actions {
      display: flex;
      gap: 12px;
      margin-top: 16px;
      flex-wrap: wrap;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid var(--border);
      text-transform: uppercase;
      font-size: 11px;
      letter-spacing: 0.08em;
    }
    .badge.completed, .badge.success, .badge.approved, .badge.active, .badge.healthy { color: var(--green); border-color: rgba(94, 211, 154, 0.45); }
    .badge.failed, .badge.failure, .badge.rejected, .badge.cancelled, .badge.revoked, .badge.expired, .badge.invalid { color: var(--red); border-color: rgba(241, 125, 125, 0.45); }
    .badge.running, .badge.paused_for_approval, .badge.pending, .badge.rate_limited, .badge.timeout, .badge.unavailable { color: var(--amber); border-color: rgba(244, 200, 107, 0.45); }
    .badge.idle { color: var(--blue); border-color: rgba(132, 168, 255, 0.45); }
    .meta {
      display: grid;
      gap: 8px;
      color: #c7d0e0;
      font-size: 14px;
    }
    .meta span { color: var(--muted); }
    .muted { color: var(--muted); }
    .tiny { font-size: 12px; }
    .empty {
      padding: 22px;
      border-radius: 20px;
      border: 1px dashed var(--border);
      color: var(--muted);
      background: rgba(13, 18, 27, 0.5);
    }
    .json {
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font: 12px/1.7 var(--mono);
      color: #aab5c8;
      margin: 0;
    }
    .notice-approval {
      border-color: rgba(244, 200, 107, 0.35);
      background: rgba(120, 86, 20, 0.12);
    }
    .notice-error {
      border-color: rgba(241, 125, 125, 0.32);
      background: rgba(110, 24, 24, 0.16);
    }
    .list-grid {
      display: grid;
      gap: 12px;
      max-height: 420px;
      overflow: auto;
      padding-right: 4px;
    }
    .list-item {
      width: 100%;
      text-align: left;
      background: var(--panel-2);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 14px;
      color: var(--text);
    }
    .list-item.active {
      border-color: rgba(132, 168, 255, 0.5);
      background: var(--panel-3);
    }
    .split {
      display: grid;
      gap: 14px;
      grid-template-columns: 0.9fr 1.1fr;
    }
    .approval-grid, .session-grid, .workflow-grid, .history-grid, .interaction-grid {
      display: grid;
      gap: 14px;
    }
    .code-inline {
      font-family: var(--mono);
      font-size: 12px;
      color: #dce5ff;
      word-break: break-word;
    }
    @media (max-width: 1250px) {
      .hero, .grid-main, .grid-dual, .split { grid-template-columns: 1fr; }
      .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .hero-actions { justify-content: flex-start; }
    }
    @media (max-width: 720px) {
      .stats { grid-template-columns: 1fr; }
      .shell { padding: 16px; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div>
        <div class="eyebrow">AICP Agent Console</div>
        <h1>Runtime control plane for governed actions</h1>
        <p class="lede">
          Execute capabilities, inspect sessions and interactions, monitor workflow state,
          explore persisted executions, and clear the approval inbox from a single zero-build runtime surface.
        </p>
        <div class="stats">
          <div class="stat"><div class="small-label">Capabilities</div><div class="stat-value" id="stat-capabilities">0</div></div>
          <div class="stat"><div class="small-label">Pending approvals</div><div class="stat-value" id="stat-approvals">0</div></div>
          <div class="stat"><div class="small-label">Sessions</div><div class="stat-value" id="stat-sessions">0</div></div>
          <div class="stat"><div class="small-label">Workflows</div><div class="stat-value" id="stat-workflows">0</div></div>
          <div class="stat"><div class="small-label">Last status</div><div class="stat-value tiny" id="stat-last-status">idle</div></div>
        </div>
      </div>
      <div class="hero-actions">
        <button class="button-secondary" id="refresh-all">Refresh console</button>
      </div>
    </section>

    <section class="grid-main">
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Execute capability</div>
            <div class="panel-subtitle">Drive the runtime using the existing /v1 action surface.</div>
          </div>
        </div>
        <label for="capability-select">Capability</label>
        <select id="capability-select"></select>
        <div class="small-label" style="margin-top:16px;">Arguments JSON</div>
        <textarea id="payload-input">{}</textarea>
        <div class="actions">
          <button class="button-primary" id="run-capability">Run capability</button>
          <button class="button-secondary" id="reset-payload">Reset payload</button>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Last execution</div>
            <div class="panel-subtitle">Latest /v1/execute response including approval and continuation hints.</div>
          </div>
        </div>
        <div id="execution-pane" class="empty">No execution yet.</div>
      </div>
    </section>

    <section class="grid-dual">
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Session inspector</div>
            <div class="panel-subtitle">Inspect /v1/sessions and /v1/interactions together.</div>
          </div>
        </div>
        <div id="session-pane" class="session-grid"></div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Workflow monitor</div>
            <div class="panel-subtitle">Observe /workflows with recent /history entries.</div>
          </div>
          <select id="workflow-select"></select>
        </div>
        <div id="workflow-pane" class="workflow-grid"></div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-header">
        <div>
          <div class="panel-title">Execution explorer</div>
          <div class="panel-subtitle">Browse persisted execution records from /v1/executions.</div>
        </div>
      </div>
      <div class="split">
        <div>
          <div id="execution-list" class="list-grid"></div>
        </div>
        <div>
          <div id="execution-detail" class="empty">No execution record selected.</div>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-header">
        <div>
          <div class="panel-title">Approval inbox</div>
          <div class="panel-subtitle">Review and decide /v1/approvals without leaving the runtime.</div>
        </div>
        <div class="row" style="max-width:560px; width:100%;">
          <input id="approver-id" value="agent-operator" placeholder="Approver ID" />
          <select id="approval-filter">
            <option value="all">All</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </div>
      <div id="approvals-pane" class="approval-grid"></div>
    </section>
  </div>

  <script>
    const state = {
      capabilities: [],
      approvals: [],
      sessions: [],
      interactions: [],
      workflows: [],
      history: [],
      executions: [],
      selectedCapability: '',
      selectedWorkflowId: 'all',
      selectedExecutionId: '',
      result: null,
      loading: false,
    };

    const capabilitySelect = document.getElementById('capability-select');
    const payloadInput = document.getElementById('payload-input');
    const executionPane = document.getElementById('execution-pane');
    const sessionPane = document.getElementById('session-pane');
    const workflowPane = document.getElementById('workflow-pane');
    const workflowSelect = document.getElementById('workflow-select');
    const executionList = document.getElementById('execution-list');
    const executionDetail = document.getElementById('execution-detail');
    const approvalsPane = document.getElementById('approvals-pane');
    const approverInput = document.getElementById('approver-id');
    const approvalFilter = document.getElementById('approval-filter');
    const runButton = document.getElementById('run-capability');

    async function loadAll() {
      const responses = await Promise.all([
        fetch('/.well-known/aicp'),
        fetch('/v1/approvals'),
        fetch('/v1/sessions'),
        fetch('/v1/interactions'),
        fetch('/workflows'),
        fetch('/history'),
        fetch('/v1/executions?limit=24'),
      ]);

      const [discovery, approvals, sessions, interactions, workflows, history, executions] = await Promise.all(
        responses.map((response) => response.json())
      );

      state.capabilities = (discovery.capabilities || []).slice().sort((a, b) => a.name.localeCompare(b.name));
      state.approvals = approvals || [];
      state.sessions = sessions || [];
      state.interactions = interactions || [];
      state.workflows = workflows || [];
      state.history = history || [];
      state.executions = executions || [];

      if (!state.selectedCapability && state.capabilities.length) {
        state.selectedCapability = state.capabilities[0].name;
      }
      if (state.selectedWorkflowId !== 'all' && !state.workflows.some((workflow) => workflow.id === state.selectedWorkflowId)) {
        state.selectedWorkflowId = 'all';
      }
      if ((!state.selectedExecutionId || !state.executions.some((execution) => execution.execution_id === state.selectedExecutionId)) && state.executions.length) {
        state.selectedExecutionId = state.executions[0].execution_id;
      }
      render();
    }

    async function executeCapability() {
      setLoading(true);
      try {
        const parsed = JSON.parse(payloadInput.value || '{}');
        const response = await fetch('/v1/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            capability_name: state.selectedCapability,
            arguments: parsed,
            context: {},
          }),
        });
        state.result = await response.json();
        await loadAll();
      } catch (error) {
        state.result = {
          status: 'failed',
          error: {
            message: error instanceof Error ? error.message : 'Failed to execute capability',
            code: 'ui_execution_failed',
          },
        };
        renderExecution();
      } finally {
        setLoading(false);
      }
    }

    async function decideApproval(id, decision) {
      setLoading(true);
      try {
        const response = await fetch(`/v1/approvals/${id}/decide`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            decision,
            approver_id: approverInput.value || 'agent-operator',
            reason: decision === 'approved' ? 'Approved from agent console' : 'Rejected from agent console',
          }),
        });
        state.result = await response.json();
        await loadAll();
      } finally {
        setLoading(false);
      }
    }

    function setLoading(value) {
      state.loading = value;
      runButton.disabled = value || !state.selectedCapability;
      runButton.textContent = value ? 'Executing...' : 'Run capability';
    }

    function render() {
      renderCapabilities();
      renderExecution();
      renderSessions();
      renderWorkflows();
      renderExecutionExplorer();
      renderApprovals();
      renderStats();
    }

    function renderCapabilities() {
      capabilitySelect.innerHTML = '';
      for (const capability of state.capabilities) {
        const option = document.createElement('option');
        option.value = capability.name;
        option.textContent = capability.name;
        option.selected = capability.name === state.selectedCapability;
        capabilitySelect.appendChild(option);
      }
    }

    function renderExecution() {
      const result = state.result;
      if (!result) {
        executionPane.className = 'empty';
        executionPane.textContent = 'No execution yet.';
        return;
      }

      const approvalBlock = result.approval_request ? `
        <div class="card notice-approval">
          <div class="small-label">Approval required</div>
          <div>${escapeHtml(result.approval_request.trigger?.reason || 'Approval required')}</div>
          <div class="tiny muted" style="margin-top:10px;">Request ID: ${escapeHtml(result.approval_request.id || 'n/a')}</div>
        </div>
      ` : '';

      const errorBlock = result.error ? `
        <div class="card notice-error">
          <div class="small-label">Error</div>
          <div>${escapeHtml(result.error.message || 'Unknown error')}</div>
          ${result.error.fix_hint ? `<div class="tiny muted" style="margin-top:10px;">Fix hint: ${escapeHtml(result.error.fix_hint)}</div>` : ''}
        </div>
      ` : '';

      executionPane.className = 'stack';
      executionPane.innerHTML = `
        <div class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;">
            <div class="small-label">Status</div>
            ${statusBadge(result.status)}
          </div>
          <div class="meta" style="margin-top:14px;">
            <div><span>Capability:</span> ${escapeHtml(result.capability_name || 'n/a')}</div>
            <div><span>Execution ID:</span> ${escapeHtml(result.execution_id || 'n/a')}</div>
            <div><span>Workflow ID:</span> ${escapeHtml(result.workflow_id || 'n/a')}</div>
          </div>
        </div>
        ${errorBlock}
        ${approvalBlock}
        ${jsonCard('Data', result.data)}
        ${jsonCard('Next', result.next)}
      `;
    }

    function renderSessions() {
      const interactionsBySession = new Map();
      for (const interaction of state.interactions) {
        const sessionId = interaction.session_id || '__detached__';
        const current = interactionsBySession.get(sessionId) || [];
        current.push(interaction);
        interactionsBySession.set(sessionId, current);
      }

      const sessionCards = state.sessions.length ? state.sessions.map((session) => {
        const linkedInteractions = interactionsBySession.get(session.id) || [];
        return `
          <div class="card">
            <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">
              <div>
                <h3>${escapeHtml(session.provider_name || 'unknown provider')}</h3>
                <div class="tiny muted" style="margin-top:8px;">Session ID: <span class="code-inline">${escapeHtml(session.id || 'n/a')}</span></div>
              </div>
              ${statusBadge(session.health_status || (session.revoked_at ? 'revoked' : 'active'))}
            </div>
            <div class="meta" style="margin-top:14px;">
              <div><span>Auth mode:</span> ${escapeHtml(session.auth_mode || 'n/a')}</div>
              <div><span>Tenant:</span> ${escapeHtml(session.tenant_id || 'n/a')}</div>
              <div><span>User:</span> ${escapeHtml(session.user_id || 'n/a')}</div>
              <div><span>Expires:</span> ${escapeHtml(session.expires_at || 'n/a')}</div>
              <div><span>Refreshable:</span> ${escapeHtml(String(Boolean(session.refreshable)))}</div>
              <div><span>Requires reauth:</span> ${escapeHtml(String(Boolean(session.requires_reauth)))}</div>
              <div><span>Linked interactions:</span> ${escapeHtml(String(linkedInteractions.length))}</div>
            </div>
          </div>
        `;
      }).join('') : '<div class="empty">No sessions created yet.</div>';

      const interactionCards = state.interactions.length ? state.interactions.map((interaction) => `
        <div class="card">
          <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">
            <div>
              <h3>${escapeHtml(interaction.last_capability || 'Interaction state')}</h3>
              <div class="tiny muted" style="margin-top:8px;">Interaction ID: <span class="code-inline">${escapeHtml(interaction.id || 'n/a')}</span></div>
            </div>
            ${statusBadge(interaction.session_id ? 'active' : 'idle')}
          </div>
          <div class="meta" style="margin-top:14px;">
            <div><span>Session:</span> ${escapeHtml(interaction.session_id || 'detached')}</div>
            <div><span>Context keys:</span> ${escapeHtml(String(Object.keys(interaction.selected_context || {}).length))}</div>
            <div><span>Cached resources:</span> ${escapeHtml(String(Object.keys(interaction.resource_cache || {}).length))}</div>
            <div><span>Updated:</span> ${escapeHtml(interaction.updated_at || 'n/a')}</div>
          </div>
        </div>
      `).join('') : '<div class="empty">No interaction state yet.</div>';

      sessionPane.innerHTML = `
        <div class="stack">
          ${sessionCards}
        </div>
        <div>
          <div class="small-label" style="margin-bottom:12px;">Interaction memory</div>
          <div class="interaction-grid">${interactionCards}</div>
        </div>
      `;
    }

    function renderWorkflows() {
      workflowSelect.innerHTML = '';
      const allOption = document.createElement('option');
      allOption.value = 'all';
      allOption.textContent = 'All workflows';
      workflowSelect.appendChild(allOption);
      for (const workflow of state.workflows) {
        const option = document.createElement('option');
        option.value = workflow.id;
        option.textContent = workflow.name;
        option.selected = workflow.id === state.selectedWorkflowId;
        workflowSelect.appendChild(option);
      }
      workflowSelect.value = state.selectedWorkflowId;

      const workflows = state.workflows.length ? state.workflows.map((workflow) => `
        <div class="card">
          <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">
            <div>
              <h3>${escapeHtml(workflow.name || 'workflow')}</h3>
              <div class="tiny muted" style="margin-top:8px;">Workflow ID: <span class="code-inline">${escapeHtml(workflow.id || 'n/a')}</span></div>
            </div>
            ${statusBadge(workflow.status || 'idle')}
          </div>
          <div class="meta" style="margin-top:14px;">
            <div><span>Description:</span> ${escapeHtml(workflow.description || 'n/a')}</div>
            <div><span>Current step:</span> ${escapeHtml(workflow.current_step?.capability_name || workflow.current_step_capability || 'n/a')}</div>
            <div><span>Step status:</span> ${escapeHtml(workflow.current_step?.status || 'n/a')}</div>
          </div>
        </div>
      `).join('') : '<div class="empty">No workflows created yet.</div>';

      const filteredHistory = state.selectedWorkflowId === 'all'
        ? state.history.slice().reverse().slice(0, 8)
        : state.history.filter((entry) => entry.workflow_id === state.selectedWorkflowId).slice().reverse().slice(0, 8);

      const historyMarkup = filteredHistory.length ? filteredHistory.map((entry) => `
        <div class="card">
          <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">
            <div>
              <h3>${escapeHtml(entry.event_type || 'event')}</h3>
              <div class="tiny muted" style="margin-top:8px;">${escapeHtml(entry.timestamp || 'n/a')}</div>
            </div>
            ${statusBadge(entry.status || 'idle')}
          </div>
          <div class="meta" style="margin-top:14px;">
            <div><span>Actor:</span> ${escapeHtml(entry.actor || 'runtime')}</div>
            <div><span>Workflow:</span> ${escapeHtml(entry.workflow_id || 'n/a')}</div>
            <div><span>Capability:</span> ${escapeHtml(entry.capability_name || 'n/a')}</div>
            <div><span>Approval:</span> ${escapeHtml(entry.approval_request_id || 'n/a')}</div>
          </div>
        </div>
      `).join('') : '<div class="empty">No matching history entries.</div>';

      workflowPane.innerHTML = `
        <div>
          <div class="small-label" style="margin-bottom:12px;">Workflow state</div>
          <div class="workflow-grid">${workflows}</div>
        </div>
        <div>
          <div class="small-label" style="margin-bottom:12px;">Recent history</div>
          <div class="history-grid">${historyMarkup}</div>
        </div>
      `;
    }

    function renderExecutionExplorer() {
      if (!state.executions.length) {
        executionList.innerHTML = '<div class="empty">No persisted execution records yet.</div>';
        executionDetail.className = 'empty';
        executionDetail.textContent = 'No execution record selected.';
        return;
      }

      executionList.innerHTML = state.executions.map((execution) => `
        <button class="list-item ${execution.execution_id === state.selectedExecutionId ? 'active' : ''}" data-execution-id="${escapeHtml(execution.execution_id)}">
          <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">
            <div>
              <div style="font-weight:600;">${escapeHtml(execution.capability_name || 'unknown')}</div>
              <div class="tiny muted" style="margin-top:8px;">${escapeHtml(execution.execution_id || 'n/a')}</div>
            </div>
            ${statusBadge(execution.status || 'idle')}
          </div>
          <div class="tiny muted" style="margin-top:12px;">${escapeHtml(execution.created_at || 'n/a')}</div>
        </button>
      `).join('');

      executionList.querySelectorAll('[data-execution-id]').forEach((button) => {
        button.addEventListener('click', () => {
          state.selectedExecutionId = button.getAttribute('data-execution-id') || '';
          renderExecutionExplorer();
        });
      });

      const selected = state.executions.find((execution) => execution.execution_id === state.selectedExecutionId) || state.executions[0];
      if (selected && selected.execution_id !== state.selectedExecutionId) {
        state.selectedExecutionId = selected.execution_id;
      }

      executionDetail.className = 'stack';
      executionDetail.innerHTML = `
        <div class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;">
            <div>
              <div class="small-label">Execution record</div>
              <h3 style="margin-top:4px;">${escapeHtml(selected.capability_name || 'unknown')}</h3>
            </div>
            ${statusBadge(selected.status || 'idle')}
          </div>
          <div class="meta" style="margin-top:14px;">
            <div><span>Execution ID:</span> ${escapeHtml(selected.execution_id || 'n/a')}</div>
            <div><span>Created:</span> ${escapeHtml(selected.created_at || 'n/a')}</div>
            <div><span>Session ID:</span> ${escapeHtml(selected.context?.session_id || 'n/a')}</div>
            <div><span>Interaction ID:</span> ${escapeHtml(selected.context?.interaction_id || 'n/a')}</div>
          </div>
        </div>
        ${jsonCard('Arguments', selected.arguments)}
        ${jsonCard('Context', selected.context)}
        ${jsonCard('Result', selected.result)}
      `;
    }

    function renderApprovals() {
      const filter = approvalFilter.value;
      const approvals = filter === 'all'
        ? state.approvals
        : state.approvals.filter((approval) => approval.status === filter);

      if (!approvals.length) {
        approvalsPane.innerHTML = '<div class="empty">No approvals in this filter.</div>';
        return;
      }

      approvalsPane.innerHTML = approvals.map((approval) => `
        <div class="card">
          <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">
            <div>
              <h3>${escapeHtml(approval.capability_name || 'unknown')}</h3>
              <div class="muted" style="margin-top:8px;">${escapeHtml(approval.trigger?.reason || 'Approval required')}</div>
              <div class="tiny muted" style="margin-top:10px;">Approval ID: ${escapeHtml(approval.id || 'n/a')} · Workflow: ${escapeHtml(approval.workflow_id || 'n/a')}</div>
            </div>
            ${statusBadge(approval.status)}
          </div>
          <div class="tiny muted" style="margin-top:12px;">Effect: ${escapeHtml(approval.trigger?.effect || 'ask')}${approval.trigger?.policy_name ? ` · Policy: ${escapeHtml(approval.trigger.policy_name)}` : ''}</div>
          ${approval.status === 'pending' ? `
            <div class="actions" style="margin-top:14px;">
              <button class="button-secondary" data-approve="${escapeHtml(approval.id)}">Approve</button>
              <button class="button-secondary" data-reject="${escapeHtml(approval.id)}">Reject</button>
            </div>
          ` : ''}
        </div>
      `).join('');

      approvalsPane.querySelectorAll('[data-approve]').forEach((button) => {
        button.addEventListener('click', () => decideApproval(button.getAttribute('data-approve'), 'approved'));
      });
      approvalsPane.querySelectorAll('[data-reject]').forEach((button) => {
        button.addEventListener('click', () => decideApproval(button.getAttribute('data-reject'), 'rejected'));
      });
    }

    function renderStats() {
      document.getElementById('stat-capabilities').textContent = String(state.capabilities.length);
      document.getElementById('stat-approvals').textContent = String(state.approvals.filter((approval) => approval.status === 'pending').length);
      document.getElementById('stat-sessions').textContent = String(state.sessions.length);
      document.getElementById('stat-workflows').textContent = String(state.workflows.length);
      document.getElementById('stat-last-status').textContent = state.result?.status || 'idle';
    }

    function statusBadge(status) {
      return `<div class="badge ${escapeHtml((status || 'idle').toLowerCase())}">${escapeHtml(status || 'unknown')}</div>`;
    }

    function jsonCard(title, value) {
      return `
        <div class="card">
          <div class="small-label">${escapeHtml(title)}</div>
          <pre class="json">${escapeHtml(JSON.stringify(value ?? null, null, 2))}</pre>
        </div>
      `;
    }

    function escapeHtml(value) {
      return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }

    capabilitySelect.addEventListener('change', (event) => {
      state.selectedCapability = event.target.value;
      setLoading(state.loading);
    });
    workflowSelect.addEventListener('change', (event) => {
      state.selectedWorkflowId = event.target.value;
      renderWorkflows();
    });
    document.getElementById('refresh-all').addEventListener('click', () => void loadAll());
    document.getElementById('run-capability').addEventListener('click', () => void executeCapability());
    document.getElementById('reset-payload').addEventListener('click', () => {
      payloadInput.value = '{}';
    });
    approvalFilter.addEventListener('change', renderApprovals);
    void loadAll();
  </script>
</body>
</html>"""
