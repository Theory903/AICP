"""Tests for the thin Studio seed app."""

from fastapi.testclient import TestClient

from aicp.interfaces.workflow_runtime import WorkflowState
from aicp_runtime.persistence.file import FileRuntimeStore

from studio.app import create_studio_app


def test_studio_serves_dashboard_html(tmp_path) -> None:
    store = FileRuntimeStore(tmp_path / "runtime-store")
    app = create_studio_app(runtime_store=store)
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "AICP Studio" in response.text
    assert "Approval Inbox" in response.text


def test_studio_exposes_approvals_and_history_api(tmp_path) -> None:
    store = FileRuntimeStore(tmp_path / "runtime-store")
    app = create_studio_app(runtime_store=store)
    client = TestClient(app)

    import asyncio

    asyncio.run(
        store.save_approval_request(
            {
                "id": "apr-1",
                "capability_name": "payments.transfer",
                "requester": "agent-1",
                "requested_at": "2026-03-30T12:00:00Z",
                "status": "pending",
            }
        )
    )
    asyncio.run(
        store.append_audit_entry(
            {
                "id": "audit-1",
                "timestamp": "2026-03-30T12:00:00Z",
                "event_type": "approval_request_created",
                "actor": "agent-1",
                "approval_request_id": "apr-1",
            }
        )
    )
    asyncio.run(store.save_workflow(WorkflowState(id="wf-1", name="transfer_flow", steps=[])))

    approvals_response = client.get("/api/approvals")
    history_response = client.get("/api/history")
    workflows_response = client.get("/api/workflows")

    assert approvals_response.status_code == 200
    assert approvals_response.json()[0]["id"] == "apr-1"
    assert history_response.status_code == 200
    assert history_response.json()[0]["event_type"] == "approval_request_created"
    assert workflows_response.status_code == 200
    assert workflows_response.json()[0]["id"] == "wf-1"


def test_studio_can_decide_approval_requests(tmp_path) -> None:
    store = FileRuntimeStore(tmp_path / "runtime-store")
    app = create_studio_app(runtime_store=store)
    client = TestClient(app)

    import asyncio

    asyncio.run(
        store.save_approval_request(
            {
                "id": "apr-1",
                "capability_name": "payments.transfer",
                "requester": "agent-1",
                "requested_at": "2026-03-30T12:00:00Z",
                "status": "pending",
            }
        )
    )

    decide_response = client.post(
        "/api/approvals/apr-1/decide",
        json={"decision": "approved", "approver": "manager-1", "reason": "Looks good"},
    )
    approvals_response = client.get("/api/approvals")
    history_response = client.get("/api/history")

    assert decide_response.status_code == 200
    assert decide_response.json()["decision"] == "approved"
    assert approvals_response.json()[0]["status"] == "approved"
    assert any(entry["event_type"] == "approval_decision_made" for entry in history_response.json())


def test_studio_serves_workflow_detail_page_and_api(tmp_path) -> None:
    store = FileRuntimeStore(tmp_path / "runtime-store")
    app = create_studio_app(runtime_store=store)
    client = TestClient(app)

    import asyncio

    asyncio.run(store.save_workflow(WorkflowState(id="wf-42", name="checkout_flow", steps=[])))
    asyncio.run(
        store.append_audit_entry(
            {
                "id": "audit-42",
                "timestamp": "2026-03-30T12:00:00Z",
                "event_type": "workflow_created",
                "actor": "runtime",
                "workflow_id": "wf-42",
            }
        )
    )

    page_response = client.get("/workflows/wf-42")
    api_response = client.get("/api/workflows/wf-42")

    assert page_response.status_code == 200
    assert "Workflow Detail" in page_response.text
    assert "wf-42" in page_response.text
    assert api_response.status_code == 200
    assert api_response.json()["workflow"]["id"] == "wf-42"
    assert api_response.json()["history"][0]["event_type"] == "workflow_created"
    assert api_response.json()["replay"][0]["title"] == "Workflow created"


def test_studio_workflow_detail_groups_replay_events(tmp_path) -> None:
    store = FileRuntimeStore(tmp_path / "runtime-store")
    app = create_studio_app(runtime_store=store)
    client = TestClient(app)

    import asyncio

    asyncio.run(store.save_workflow(WorkflowState(id="wf-group", name="grouped_flow", steps=[])))
    asyncio.run(
        store.append_audit_entry(
            {
                "id": "audit-1",
                "timestamp": "2026-03-30T12:00:00Z",
                "event_type": "workflow_created",
                "actor": "runtime",
                "workflow_id": "wf-group",
            }
        )
    )
    asyncio.run(
        store.append_audit_entry(
            {
                "id": "audit-2",
                "timestamp": "2026-03-30T12:01:00Z",
                "event_type": "approval_request_created",
                "actor": "agent-1",
                "workflow_id": "wf-group",
                "approval_request_id": "apr-1",
            }
        )
    )
    asyncio.run(
        store.append_audit_entry(
            {
                "id": "audit-3",
                "timestamp": "2026-03-30T12:02:00Z",
                "event_type": "approval_decision_made",
                "actor": "manager-1",
                "workflow_id": "wf-group",
                "approval_request_id": "apr-1",
                "status": "success",
            }
        )
    )

    api_response = client.get("/api/workflows/wf-group")
    payload = api_response.json()

    assert api_response.status_code == 200
    assert len(payload["replay"]) == 3
    assert payload["replay"][1]["title"] == "Approval requested"
    assert payload["replay"][2]["title"] == "Approval decided"
