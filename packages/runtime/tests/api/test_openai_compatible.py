from __future__ import annotations

from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aicp.interfaces.executor import ExecutionError, ExecutionResult, ExecutionStatus
from aicp_runtime.api.routes.openai_compatible import build_openai_compatible_router


class StubExecutionService:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.result: ExecutionResult = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            data={"reply": "hello"},
            rendered="hello",
            next={"action": "complete"},
        )
        self.error: Exception | None = None

    async def execute(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        self.calls.append(
            {
                "capability_name": capability_name,
                "arguments": arguments,
                "context": context or {},
            }
        )
        if self.error is not None:
            raise self.error
        return self.result


class StubDiscoveryService:
    def __init__(self) -> None:
        self.rank_calls: list[dict[str, Any]] = []
        self.discover_calls = 0
        self.ranked: list[dict[str, Any]] = [
            {
                "capability": {"name": "notes.search"},
                "score": 95,
                "reasons": ["semantic:embedding_match"],
            },
            {
                "capability": {"name": "notes.create"},
                "score": 45,
                "reasons": ["name:contains"],
            },
        ]
        self.document = {
            "capabilities": [
                {"name": "notes.search", "description": "Search notes"},
                {"name": "notes.create", "description": "Create note"},
            ]
        }

    async def rank_capabilities(
        self,
        *,
        query: str = "",
        session: dict[str, Any] | None = None,
        interaction: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        self.rank_calls.append(
            {
                "query": query,
                "session": session,
                "interaction": interaction,
                "limit": limit,
            }
        )
        return self.ranked[:limit]

    async def discover(self) -> dict[str, Any]:
        self.discover_calls += 1
        return self.document


class StubSessionService:
    def __init__(self) -> None:
        self.sessions: dict[str, dict[str, Any]] = {
            "valid-token": {
                "id": "valid-token",
                "provider_name": "runtime-test",
                "auth_mode": "bearer",
            }
        }
        self.calls: list[str] = []

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        self.calls.append(session_id)
        return self.sessions.get(session_id)


@pytest.fixture()
def services() -> dict[str, Any]:
    execution = StubExecutionService()
    discovery = StubDiscoveryService()
    sessions = StubSessionService()
    app = FastAPI()
    app.include_router(
        build_openai_compatible_router(
            cast(Any, execution),
            cast(Any, discovery),
            cast(Any, sessions),
        )
    )
    return {
        "app": app,
        "execution": execution,
        "discovery": discovery,
        "sessions": sessions,
    }


@pytest.fixture()
def client(services: dict[str, Any]) -> TestClient:
    return TestClient(services["app"])


def _auth_header(token: str = "valid-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestOpenAICompatibleChatCompletions:
    def test_chat_completions_returns_openai_shape(
        self, client: TestClient, services: dict[str, Any]
    ) -> None:
        response = client.post(
            "/v1/chat/completions",
            headers=_auth_header(),
            json={
                "model": "aicp-default",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "chat.completion"
        assert data["model"] == "aicp-default"
        assert data["choices"][0]["message"]["content"] == "hello"
        assert data["choices"][0]["finish_reason"] == "stop"
        assert services["execution"].calls[0]["capability_name"] == "aicp-default"
        assert services["execution"].calls[0]["context"]["messages"] == [
            {"role": "user", "content": "hello"}
        ]

    def test_chat_completions_streams_sse_chunks(
        self, client: TestClient, services: dict[str, Any]
    ) -> None:
        services["execution"].result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            data={"reply": "streamed hello"},
            rendered="streamed hello",
            next={"action": "complete"},
        )

        with client.stream(
            "POST",
            "/v1/chat/completions",
            headers=_auth_header(),
            json={
                "model": "aicp-default",
                "stream": True,
                "messages": [{"role": "user", "content": "hello"}],
            },
        ) as response:
            body = "".join(response.iter_text())

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert "data: {\"id\":" in body
        assert "streamed hello" in body
        assert "data: [DONE]" in body

    def test_chat_completions_uses_data_when_rendered_missing(
        self, client: TestClient, services: dict[str, Any]
    ) -> None:
        services["execution"].result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            data={"message": "from-data"},
            next={"action": "complete"},
        )

        response = client.post(
            "/v1/chat/completions",
            headers=_auth_header(),
            json={
                "model": "aicp-default",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

        assert response.status_code == 200
        assert response.json()["choices"][0]["message"]["content"] == "from-data"

    def test_chat_completions_requires_bearer_auth(self, client: TestClient) -> None:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "aicp-default",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

        assert response.status_code == 401
        assert response.json()["error"]["type"] == "invalid_request_error"

    def test_chat_completions_rejects_invalid_bearer_token(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/v1/chat/completions",
            headers=_auth_header("missing-token"),
            json={
                "model": "aicp-default",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

        assert response.status_code == 401
        assert response.json()["error"]["message"] == "Invalid bearer token"

    def test_chat_completions_maps_invalid_input_errors_to_400(
        self, client: TestClient, services: dict[str, Any]
    ) -> None:
        services["execution"].result = ExecutionResult(
            status=ExecutionStatus.FAILURE,
            error="Bad request",
            error_code="invalid_input",
            next={"action": "retry"},
        )

        response = client.post(
            "/v1/chat/completions",
            headers=_auth_header(),
            json={
                "model": "aicp-default",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_input"

    def test_chat_completions_maps_missing_capability_to_404(
        self, client: TestClient, services: dict[str, Any]
    ) -> None:
        services["execution"].error = ExecutionError(
            "Capability not found: aicp-default",
            capability_name="aicp-default",
            error_code="capability_not_found",
        )

        response = client.post(
            "/v1/chat/completions",
            headers=_auth_header(),
            json={
                "model": "aicp-default",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

        assert response.status_code == 404
        assert response.json()["error"]["type"] == "invalid_request_error"


class TestOpenAICompatibleModels:
    def test_models_list_returns_openai_list_shape(
        self, client: TestClient, services: dict[str, Any]
    ) -> None:
        response = client.get("/v1/models", headers=_auth_header())

        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert data["data"][0]["id"] == "aicp-default"
        assert data["data"][0]["object"] == "model"
        assert services["discovery"].discover_calls == 1

    def test_models_list_requires_auth(self, client: TestClient) -> None:
        response = client.get("/v1/models")
        assert response.status_code == 401


class TestOpenAICompatibleEmbeddings:
    def test_embeddings_returns_vectors_for_single_string(
        self, client: TestClient, services: dict[str, Any]
    ) -> None:
        response = client.post(
            "/v1/embeddings",
            headers=_auth_header(),
            json={"model": "aicp-default", "input": "find my notes"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert data["model"] == "aicp-default"
        assert data["data"][0]["object"] == "embedding"
        assert data["data"][0]["index"] == 0
        assert len(data["data"][0]["embedding"]) == 2
        assert services["discovery"].rank_calls[0]["query"] == "find my notes"
        assert services["discovery"].rank_calls[0]["session"]["id"] == "valid-token"

    def test_embeddings_returns_vectors_for_multiple_inputs(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/v1/embeddings",
            headers=_auth_header(),
            json={"model": "aicp-default", "input": ["find", "create"]},
        )

        assert response.status_code == 200
        assert len(response.json()["data"]) == 2

    def test_embeddings_rejects_empty_input_array(self, client: TestClient) -> None:
        response = client.post(
            "/v1/embeddings",
            headers=_auth_header(),
            json={"model": "aicp-default", "input": []},
        )

        assert response.status_code == 422
