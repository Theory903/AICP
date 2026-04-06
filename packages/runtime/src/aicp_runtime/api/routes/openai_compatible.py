from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any, Protocol

from aicp.interfaces.executor import ExecutionError, ExecutionResult, ExecutionStatus
from fastapi import APIRouter, Header, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator



class ExecutionServiceLike(Protocol):
    async def execute(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult: ...


class DiscoveryServiceLike(Protocol):
    async def discover(self) -> dict[str, Any]: ...

    async def rank_capabilities(
        self,
        *,
        query: str = "",
        session: dict[str, Any] | None = None,
        interaction: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]: ...


class SessionServiceLike(Protocol):
    async def get_session(self, session_id: str) -> dict[str, Any] | None: ...


class OpenAIMessage(BaseModel):
    role: str = Field(min_length=1)
    content: str = Field(min_length=1)

    @field_validator("role", "content", mode="before")
    @classmethod
    def _normalize_text(cls, value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("must not be empty")
        return text


class OpenAIChatCompletionRequest(BaseModel):
    model: str = Field(min_length=1)
    messages: list[OpenAIMessage] = Field(min_length=1)
    stream: bool = False
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("model", mode="before")
    @classmethod
    def _normalize_model(cls, value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("model must not be empty")
        return text


class OpenAIEmbeddingsRequest(BaseModel):
    model: str = Field(min_length=1)
    input: str | list[str]

    @field_validator("model", mode="before")
    @classmethod
    def _normalize_model(cls, value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("model must not be empty")
        return text

    @field_validator("input", mode="before")
    @classmethod
    def _normalize_input(cls, value: Any) -> str | list[str]:
        if isinstance(value, str):
            text = value.strip()
            if not text:
                raise ValueError("input must not be empty")
            return text
        if isinstance(value, list):
            normalized = [str(item or "").strip() for item in value]
            filtered = [item for item in normalized if item]
            if not filtered:
                raise ValueError("input must contain at least one string")
            return filtered
        raise ValueError("input must be a string or array of strings")


class OpenAIModelResponse(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "aicp"


class OpenAIErrorBody(BaseModel):
    message: str
    type: str
    code: str | None = None


class OpenAIErrorEnvelope(BaseModel):
    error: OpenAIErrorBody


class OpenAIHTTPException(Exception):
    def __init__(self, *, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self.payload = payload
        super().__init__(payload["error"]["message"])


def build_openai_compatible_router(
    execution_service: ExecutionServiceLike,
    discovery_service: DiscoveryServiceLike,
    session_service: SessionServiceLike,
) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["openai-compatible"])

    @router.get("/models", response_model=None)
    async def list_models(
        authorization: str | None = Header(default=None),
    ) -> JSONResponse:
        try:
            await _require_session(session_service, authorization)
            await discovery_service.discover()
            payload = {
                "object": "list",
                "data": [
                    OpenAIModelResponse(
                        id="aicp-default",
                        created=int(time.time()),
                    ).model_dump(mode="json")
                ],
            }
            return JSONResponse(status_code=status.HTTP_200_OK, content=payload)
        except OpenAIHTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content=exc.payload)

    @router.post("/embeddings", response_model=None)
    async def create_embeddings(
        request: OpenAIEmbeddingsRequest,
        authorization: str | None = Header(default=None),
    ) -> JSONResponse:
        try:
            session = await _require_session(session_service, authorization)
            inputs = request.input if isinstance(request.input, list) else [request.input]
            data: list[dict[str, Any]] = []

            for index, item in enumerate(inputs):
                ranked = await discovery_service.rank_capabilities(
                    query=item,
                    session=session,
                    limit=8,
                )
                embedding = [
                    round(float(entry.get("score", 0)) / 100.0, 6) for entry in ranked
                ]
                data.append(
                    {
                        "object": "embedding",
                        "index": index,
                        "embedding": embedding or [0.0],
                    }
                )

            prompt_tokens = sum(len(item.split()) for item in inputs)
            payload = {
                "object": "list",
                "data": data,
                "model": request.model,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "total_tokens": prompt_tokens,
                },
            }
            return JSONResponse(status_code=status.HTTP_200_OK, content=payload)
        except OpenAIHTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content=exc.payload)

    @router.post("/chat/completions", response_model=None)
    async def create_chat_completion(
        request: OpenAIChatCompletionRequest,
        authorization: str | None = Header(default=None),
    ) -> JSONResponse | StreamingResponse:
        try:
            session = await _require_session(session_service, authorization)
            result = await _execute_chat_completion(
                execution_service=execution_service,
                capability_name=request.model,
                request=request,
                session=session,
            )
            content = _extract_completion_content(result)
            completion_id = f"chatcmpl_{uuid.uuid4().hex[:12]}"

            if request.stream:
                return StreamingResponse(
                    _stream_chat_completion(
                        completion_id=completion_id,
                        model=request.model,
                        content=content,
                    ),
                    media_type="text/event-stream",
                )

            prompt_tokens = sum(len(message.content.split()) for message in request.messages)
            completion_tokens = len(content.split())
            payload = {
                "id": completion_id,
                "object": "chat.completion",
                "created": int(time.time()),
                "model": request.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                },
            }
            return JSONResponse(status_code=status.HTTP_200_OK, content=payload)
        except OpenAIHTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content=exc.payload)

    return router


async def _require_session(
    session_service: SessionServiceLike,
    authorization: str | None,
) -> dict[str, Any]:
    scheme, token = _parse_authorization_header(authorization)
    if scheme != "bearer" or not token:
        _raise_openai_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="Authorization header must be Bearer <token>",
            error_type="invalid_request_error",
            code="invalid_api_key",
        )
    session = await session_service.get_session(token)
    if session is None:
        _raise_openai_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="Invalid bearer token",
            error_type="invalid_request_error",
            code="invalid_api_key",
        )
    assert session is not None
    return session


def _parse_authorization_header(authorization: str | None) -> tuple[str, str]:
    if not isinstance(authorization, str):
        return "", ""
    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2:
        return "", ""
    return parts[0].strip().lower(), parts[1].strip()


async def _execute_chat_completion(
    *,
    execution_service: ExecutionServiceLike,
    capability_name: str,
    request: OpenAIChatCompletionRequest,
    session: dict[str, Any],
) -> ExecutionResult:
    result: ExecutionResult | None = None
    try:
        result = await execution_service.execute(
            capability_name=capability_name,
            arguments={
                "messages": [message.model_dump(mode="json") for message in request.messages],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "metadata": request.metadata,
            },
            context={
                "session_id": str(session.get("id") or ""),
                "messages": [message.model_dump(mode="json") for message in request.messages],
                "openai": {
                    "model": request.model,
                    "stream": request.stream,
                },
            },
        )
    except ExecutionError as exc:
        _raise_mapped_error(message=str(exc), error_code=exc.error_code)
    except ValueError as exc:
        _raise_mapped_error(message=str(exc), error_code="invalid_input")
    except Exception as exc:
        _raise_mapped_error(message=f"Execution failed: {exc}", error_code="execution_failed")

    if result is None:
        _raise_mapped_error(message="Execution failed", error_code="execution_failed")
    assert result is not None

    if result.status != ExecutionStatus.SUCCESS:
        _raise_mapped_error(
            message=result.error or "Execution failed",
            error_code=result.error_code,
        )
    return result


def _extract_completion_content(result: ExecutionResult) -> str:
    if isinstance(result.rendered, str) and result.rendered.strip():
        return result.rendered.strip()
    if isinstance(result.data, str) and result.data.strip():
        return result.data.strip()
    if isinstance(result.data, dict):
        for key in ("message", "reply", "content", "text"):
            value = result.data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return json.dumps(result.data, separators=(",", ":"))
    return json.dumps(result.data, separators=(",", ":")) if result.data is not None else ""


async def _stream_chat_completion(
    *,
    completion_id: str,
    model: str,
    content: str,
) -> AsyncIterator[str]:
    payload = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"content": content},
                "finish_reason": None,
            }
        ],
    }
    yield f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"
    done_payload = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(done_payload, separators=(',', ':'))}\n\n"
    yield "data: [DONE]\n\n"


def _raise_mapped_error(message: str, error_code: str | None) -> None:
    status_code, error_type = _map_error(error_code)
    _raise_openai_error(
        status_code=status_code,
        message=message,
        error_type=error_type,
        code=error_code,
    )


def _map_error(error_code: str | None) -> tuple[int, str]:
    normalized = str(error_code or "execution_failed").strip().lower()
    if normalized in {"invalid_input", "validation_error"}:
        return status.HTTP_400_BAD_REQUEST, "invalid_request_error"
    if normalized in {"capability_not_found", "not_found"}:
        return status.HTTP_404_NOT_FOUND, "invalid_request_error"
    if normalized in {"policy_denied"}:
        return status.HTTP_403_FORBIDDEN, "permission_error"
    if normalized in {"rate_limited"}:
        return status.HTTP_429_TOO_MANY_REQUESTS, "rate_limit_error"
    if normalized in {"missing_session", "needs_reauthentication"}:
        return status.HTTP_401_UNAUTHORIZED, "invalid_request_error"
    return status.HTTP_500_INTERNAL_SERVER_ERROR, "api_error"


def _raise_openai_error(
    *,
    status_code: int,
    message: str,
    error_type: str,
    code: str | None,
) -> None:
    payload = OpenAIErrorEnvelope(
        error=OpenAIErrorBody(
            message=message,
            type=error_type,
            code=code,
        )
    )
    raise OpenAIHTTPException(
        status_code=status_code,
        payload=payload.model_dump(mode="json"),
    )
