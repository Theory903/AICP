"""AICP Mock Execution.

Provides a default handler that returns structured results for capabilities
to enable testing governance and execution flow without a live backend.
"""

from __future__ import annotations

import asyncio
import base64
import json
import mimetypes
import re
import time
from copy import deepcopy
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin

import httpx

from aicp.auth import ApiKeyAuth, BasicAuth, BearerAuth, OAuth2Auth
from aicp.config import AuthConfig
from aicp.interfaces.executor import ExecutionError, ExecutionResult, ExecutionStatus


class FailureClass(str, Enum):
    """Normalized execution failure classes for real HTTP backends."""

    VALIDATION = "validation_failed"
    AUTH = "authentication_failed"
    NOT_FOUND = "resource_not_found"
    RATE_LIMITED = "rate_limited"
    SERVER_ERROR = "server_error"
    CONNECTIVITY = "connectivity_error"
    TIMEOUT = "timeout"
    CIRCUIT_OPEN = "circuit_open"


_SHARED_HTTP_CLIENT: httpx.AsyncClient | None = None


def _shared_http_client() -> httpx.AsyncClient:
    global _SHARED_HTTP_CLIENT

    if _SHARED_HTTP_CLIENT is None:
        _SHARED_HTTP_CLIENT = httpx.AsyncClient(follow_redirects=True)

    return _SHARED_HTTP_CLIENT


class AuthInjector:
    """Apply configured auth material to outgoing HTTP requests."""

    def __init__(self, auth_config: AuthConfig | None) -> None:
        self._auth = self._build_auth(auth_config)

    async def apply(self, headers: dict[str, str], params: dict[str, Any]) -> None:
        if self._auth is None:
            return

        await self._auth.ensure_ready()
        self._auth.apply(headers, params)

    def _build_auth(self, auth_config: AuthConfig | None) -> Any:
        if auth_config is None:
            return None

        if auth_config.type == "bearer":
            return BearerAuth(auth_config.token or "")

        if auth_config.type == "api_key":
            return ApiKeyAuth(
                auth_config.api_key or "",
                header_name=auth_config.header_name or "Authorization",
                location=auth_config.location,
            )

        if auth_config.type == "basic":
            return BasicAuth(auth_config.username or "", auth_config.password or "")

        if auth_config.type == "oauth2_client_credentials":
            return OAuth2Auth(
                client_id=auth_config.client_id or "",
                client_secret=auth_config.client_secret or "",
                token_url=auth_config.token_url or "",
                scopes=list(auth_config.scopes),
                audience=auth_config.audience,
            )

        raise ValueError(f"Unsupported auth config type: {auth_config.type}")


class DefaultMockExecutionHandler:
    """Default mock handler for capability execution.

    Supports:
    - success responses by default
    - optional forced failure via context/arguments
    - simple capability-aware next hints
    - predictable structured payloads for CLI and runtime testing
    """

    def __init__(
        self,
        *,
        include_arguments: bool = True,
        default_format_hint: str = "json",
    ) -> None:
        self.include_arguments = include_arguments
        self.default_format_hint = default_format_hint

    async def __call__(
        self,
        arguments: dict[str, Any] | None,
        context: dict[str, Any] | None,
    ) -> ExecutionResult:
        """Execute mock logic and return a standard ExecutionResult."""
        started = time.perf_counter()

        safe_arguments = arguments or {}
        safe_context = context or {}

        capability_name = safe_context.get("capability_name", "unknown")
        kind = safe_context.get("kind", "action")
        force_error = bool(safe_context.get("mock_error") or safe_arguments.get("__mock_error"))
        force_timeout = bool(
            safe_context.get("mock_timeout") or safe_arguments.get("__mock_timeout")
        )
        force_unavailable = bool(
            safe_context.get("mock_unavailable") or safe_arguments.get("__mock_unavailable")
        )

        if force_timeout:
            return ExecutionResult.failure(
                error=f"Mock timeout while executing {capability_name}",
                error_code="timeout",
                status=ExecutionStatus.TIMEOUT,
                execution_time_ms=self._elapsed_ms(started),
                next={
                    "action": "retry",
                    "capability": capability_name,
                    "hint": "Retry later or reduce request complexity.",
                },
                can_continue=True,
            )

        if force_unavailable:
            return ExecutionResult.failure(
                error=f"Mock backend unavailable for {capability_name}",
                error_code="unavailable",
                status=ExecutionStatus.UNAVAILABLE,
                execution_time_ms=self._elapsed_ms(started),
                next={
                    "action": "retry",
                    "capability": capability_name,
                    "hint": "The service is temporarily unavailable.",
                },
                can_continue=True,
            )

        if force_error:
            return ExecutionResult.failure(
                error=f"Mock execution failed for {capability_name}",
                error_code="mock_execution_failed",
                execution_time_ms=self._elapsed_ms(started),
                next={
                    "action": "inspect",
                    "capability": capability_name,
                    "hint": "Inspect arguments or clear the mock failure flag.",
                },
                can_continue=True,
            )

        payload: dict[str, Any] = {
            "mock": True,
            "capability_name": capability_name,
            "kind": kind,
            "message": f"Successfully executed {capability_name} (mock)",
        }

        if self.include_arguments:
            payload["arguments_received"] = safe_arguments

        next_hint = self._infer_next_hint(capability_name, kind)
        next_action = self._infer_next_action(kind)
        continuation_hint = f"Mock execution completed for {capability_name}."

        return ExecutionResult.success(
            data=payload,
            execution_time_ms=self._elapsed_ms(started),
            rendered=f"Mock result: '{capability_name}' completed safely.",
            format_hint=self.default_format_hint,
            next={
                "action": next_action,
                "capability": capability_name if next_action != "complete" else None,
                "hint": next_hint,
            },
            can_continue=True,
            continuation_hint=continuation_hint,
        )

    @staticmethod
    def _elapsed_ms(started: float) -> float:
        """Return elapsed time in milliseconds."""
        return (time.perf_counter() - started) * 1000

    @staticmethod
    def _infer_next_action(kind: str) -> str:
        """Infer a sensible next action from capability kind."""
        if kind == "query":
            return "complete"
        return "list"

    @staticmethod
    def _infer_next_hint(capability_name: str, kind: str) -> str:
        """Infer a human-friendly next hint."""
        name = capability_name.lower()

        if "create" in name or "register" in name:
            return "Try fetching or listing the newly created resource next."
        if "update" in name:
            return "Try reading the resource again to verify the update."
        if "delete" in name or "remove" in name:
            return "Try listing remaining resources to confirm deletion."
        if "login" in name or "auth" in name:
            return "Try calling an authenticated capability next."
        if kind == "query":
            return "This was a read operation. Continue only if you need a follow-up action."
        return "Try listing related resources next."


class HttpCapabilityHandler:
    """Execute a capability by making a real HTTP request."""

    def __init__(
        self,
        capability: Any,
        *,
        auth_config: AuthConfig | None = None,
        request_timeout_seconds: float = 30.0,
        circuit_breaker_threshold: int = 3,
        circuit_breaker_reset_seconds: float = 30.0,
    ) -> None:
        self._capability = capability
        self._auth_injector = AuthInjector(auth_config)
        self._request_timeout_seconds = request_timeout_seconds
        self._circuit_breaker_threshold = circuit_breaker_threshold
        self._circuit_breaker_reset_seconds = circuit_breaker_reset_seconds
        self._failure_count = 0
        self._circuit_open_until = 0.0

    async def __call__(
        self,
        arguments: dict[str, Any] | None,
        context: dict[str, Any] | None,
    ) -> Any:
        return await self._execute_with_retry(arguments or {}, context or {}, allow_repair=True)

    async def _execute_with_retry(
        self,
        arguments: dict[str, Any],
        context: dict[str, Any],
        *,
        allow_repair: bool,
        repair_metadata: dict[str, Any] | None = None,
    ) -> Any:
        last_error: ExecutionError | None = None

        for attempt in range(2):
            try:
                return await self._execute_once(
                    arguments,
                    context,
                    allow_repair=allow_repair,
                    repair_metadata=repair_metadata,
                )
            except ExecutionError as exc:
                last_error = exc
                if attempt >= 1 or exc.error_code not in {
                    FailureClass.SERVER_ERROR.value,
                    FailureClass.CONNECTIVITY.value,
                    FailureClass.TIMEOUT.value,
                }:
                    raise
                await asyncio.sleep(0.25 * (attempt + 1))

        assert last_error is not None
        raise last_error

    async def _execute_once(
        self,
        arguments: dict[str, Any],
        context: dict[str, Any],
        *,
        allow_repair: bool,
        repair_metadata: dict[str, Any] | None = None,
    ) -> Any:
        method, path = self._http_metadata()
        base_url = self._base_url(context)
        if not base_url:
            raise ExecutionError(
                "No backend base URL configured for real execution. "
                "Set provider_url in aicp.yaml or rescan with a configured base URL.",
                error_code="execution_failed",
            )

        now = time.monotonic()
        if now < self._circuit_open_until:
            raise ExecutionError(
                f"Circuit breaker open for {context.get('capability_name', 'backend')}.",
                error_code=FailureClass.CIRCUIT_OPEN.value,
            )

        path_params: dict[str, Any] = {}
        query_params: dict[str, Any] = {}
        headers: dict[str, str] = {}
        cookies: dict[str, str] = {}
        form_data: dict[str, Any] = {}
        file_parts: list[tuple[str, tuple[str, Any, str]]] = []
        opened_files: list[Any] = []
        body: Any = None

        try:
            properties = getattr(self._capability.input_schema, "properties", {}) or {}
            for name, schema in properties.items():
                if name not in arguments:
                    continue
                location = None
                if isinstance(schema, dict):
                    location = schema.get("x-location")
                if location == "path":
                    path_params[name] = arguments[name]
                elif location == "query":
                    query_params[name] = arguments[name]
                elif location == "header":
                    headers[name] = str(arguments[name])
                elif location == "body":
                    body = arguments[name]
                elif location == "form":
                    form_data[name] = self._coerce_form_value(arguments[name])
                elif location == "file":
                    file_parts.extend(
                        self._build_file_parts(
                            field_name=name,
                            value=arguments[name],
                            opened_files=opened_files,
                        )
                    )

            if body is not None and (form_data or file_parts):
                raise ExecutionError(
                    "Capabilities cannot mix x-location='body' with "
                    "multipart form fields or files.",
                    error_code="invalid_arguments",
                )

            url_path = path
            for key, value in path_params.items():
                url_path = url_path.replace("{" + key + "}", quote(str(value), safe=""))

            url = urljoin(base_url.rstrip("/") + "/", url_path.lstrip("/"))
            self._ensure_session_requirement(context)
            await self._auth_injector.apply(headers, query_params)
            self._apply_session_state(context, headers, cookies)
            if cookies and "Cookie" not in headers:
                headers["Cookie"] = "; ".join(
                    f"{name}={value}" for name, value in cookies.items()
                )

            try:
                response = await _shared_http_client().request(
                    method,
                    url,
                    params=query_params or None,
                    headers=headers,
                    json=None if file_parts or form_data else body,
                    data=form_data or None,
                    files=file_parts or None,
                    timeout=httpx.Timeout(self._request_timeout_seconds),
                )
                content_type = response.headers.get("Content-Type", "")
                raw = response.content
                response.raise_for_status()
                self._reset_circuit_breaker()
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text
                if allow_repair and exc.response.status_code == 422:
                    repaired_arguments = self._repair_validation_error(arguments, detail)
                    if repaired_arguments is not None:
                        metadata = self._build_repair_metadata(
                            arguments,
                            repaired_arguments,
                            detail,
                        )
                        return await self._execute_with_retry(
                            repaired_arguments,
                            context,
                            allow_repair=False,
                            repair_metadata=metadata,
                        )
                self._record_failure(exc.response.status_code)
                raise self._classify_http_status_error(exc, detail) from exc
            except httpx.TimeoutException as exc:
                self._record_failure(None)
                raise ExecutionError(
                    f"Backend request timed out after {self._request_timeout_seconds} seconds.",
                    error_code=FailureClass.TIMEOUT.value,
                ) from exc
            except httpx.RequestError as exc:
                self._record_failure(None)
                raise ExecutionError(
                    f"Backend request failed: {exc}",
                    error_code=FailureClass.CONNECTIVITY.value,
                ) from exc

            transport_metadata = self._build_transport_metadata(
                response=response,
                url=url,
                result=None,
            )

            if not raw:
                result: Any = {}
                return self._annotate_metadata(result, repair_metadata, transport_metadata)
            if "application/json" in content_type:
                result = response.json()
                transport_metadata = self._build_transport_metadata(
                    response=response,
                    url=url,
                    result=result,
                )
                return self._annotate_metadata(result, repair_metadata, transport_metadata)
            if self._is_file_response(response, content_type):
                result = self._build_file_response(response, raw)
                return self._annotate_metadata(result, repair_metadata, transport_metadata)
            return self._annotate_metadata(
                {"text": raw.decode("utf-8", errors="replace")},
                repair_metadata,
                transport_metadata,
            )
        finally:
            for handle in opened_files:
                try:
                    handle.close()
                except Exception:
                    continue

    def _classify_http_status_error(
        self,
        exc: httpx.HTTPStatusError,
        detail: str,
    ) -> ExecutionError:
        status_code = exc.response.status_code
        error_code = self._error_code_for_status(status_code)
        message = detail or f"HTTP {status_code} calling backend"
        return ExecutionError(message, error_code=error_code, details={"status_code": status_code})

    def _apply_session_state(
        self,
        context: dict[str, Any],
        headers: dict[str, str],
        cookies: dict[str, str],
    ) -> None:
        raw_session = context.get("resolved_session")
        if not isinstance(raw_session, dict):
            return

        session_provider = str(raw_session.get("provider_name") or "").strip()
        capability_provider = self._provider_name()
        if session_provider and capability_provider and session_provider != capability_provider:
            raise ExecutionError(
                (
                    f"Session provider mismatch: expected provider '{capability_provider}' "
                    f"but received session for '{session_provider}'."
                ),
                error_code="provider_session_mismatch",
            )

        recipe = raw_session.get("auth_recipe")
        if isinstance(recipe, dict) and self._apply_auth_recipe(
            recipe,
            raw_session,
            headers,
            cookies,
        ):
            tenant_id = str(raw_session.get("tenant_id") or "").strip()
            if tenant_id and "X-Tenant-Id" not in headers:
                headers["X-Tenant-Id"] = tenant_id
            return

        for key, value in (raw_session.get("headers") or {}).items():
            key_text = str(key).strip()
            value_text = str(value).strip()
            if key_text and value_text:
                headers[key_text] = value_text

        for cookie in raw_session.get("cookies") or []:
            if not isinstance(cookie, dict):
                continue
            name = str(cookie.get("name") or "").strip()
            value = str(cookie.get("value") or "").strip()
            if name and value:
                cookies[name] = value

        token_value = self._session_bearer_token(raw_session)
        if token_value:
            headers["Authorization"] = f"Bearer {token_value}"

        for header_name, token in (raw_session.get("csrf_tokens") or {}).items():
            header_text = str(header_name).strip()
            token_text = str(token).strip()
            if header_text and token_text:
                headers[header_text] = token_text

        tenant_id = str(raw_session.get("tenant_id") or "").strip()
        if tenant_id and "X-Tenant-Id" not in headers:
            headers["X-Tenant-Id"] = tenant_id

    def _provider_name(self) -> str:
        provider = getattr(self._capability, "provider", None)
        provider_name = getattr(provider, "name", None)
        return str(provider_name or "").strip()

    def _ensure_session_requirement(self, context: dict[str, Any]) -> None:
        auth_requirement = getattr(self._capability, "auth", None)
        if auth_requirement is None or not getattr(auth_requirement, "requires_session", False):
            return

        raw_session = context.get("resolved_session")
        if not isinstance(raw_session, dict):
            raise ExecutionError(
                "Capability requires a session_id in execution context.",
                error_code="missing_session",
            )

        if getattr(auth_requirement, "csrf_required", False) and not (
            raw_session.get("csrf_tokens") or {}
        ):
            raise ExecutionError(
                "Capability requires a CSRF token in the attached session.",
                error_code="needs_reauthentication",
            )

    def _session_bearer_token(self, raw_session: dict[str, Any]) -> str | None:
        tokens = raw_session.get("tokens") or {}
        if not isinstance(tokens, dict):
            return None
        for key in ("access_token", "bearer_token", "authorization"):
            value = tokens.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().removeprefix("Bearer ").strip()
        return None

    def _apply_auth_recipe(
        self,
        recipe: dict[str, Any],
        raw_session: dict[str, Any],
        headers: dict[str, str],
        cookies: dict[str, str],
    ) -> bool:
        kind = str(recipe.get("kind") or "").strip().lower()
        if not kind:
            return False

        self._copy_session_cookies(raw_session, cookies)

        if kind in {"bearer", "oauth_refresh_token"}:
            token_field = str(recipe.get("token_field") or "access_token").strip()
            token = self._token_from_session(raw_session, token_field)
            if token:
                headers["Authorization"] = f"Bearer {token}"
            self._apply_csrf_recipe(recipe, raw_session, headers)
            return True

        if kind == "api_key_header":
            header_name = str(recipe.get("header_name") or "X-API-Key").strip()
            token_field = str(recipe.get("token_field") or "api_key").strip()
            token = self._token_from_session(raw_session, token_field)
            if token:
                headers[header_name] = token
            return True

        if kind == "cookie_csrf":
            self._apply_csrf_recipe(recipe, raw_session, headers)
            return True

        if kind == "cookie_org_header":
            org_header_name = str(recipe.get("org_header_name") or "X-Org-Id").strip()
            org_context_field = str(recipe.get("org_context_field") or "org_id").strip()
            selected_context = raw_session.get("selected_context") or {}
            if isinstance(selected_context, dict):
                org_value = str(selected_context.get(org_context_field) or "").strip()
                if org_value:
                    headers[org_header_name] = org_value
            self._apply_csrf_recipe(recipe, raw_session, headers)
            return True

        return False

    def _copy_session_cookies(
        self,
        raw_session: dict[str, Any],
        cookies: dict[str, str],
    ) -> None:
        for cookie in raw_session.get("cookies") or []:
            if not isinstance(cookie, dict):
                continue
            name = str(cookie.get("name") or "").strip()
            value = str(cookie.get("value") or "").strip()
            if name and value:
                cookies[name] = value

    def _apply_csrf_recipe(
        self,
        recipe: dict[str, Any],
        raw_session: dict[str, Any],
        headers: dict[str, str],
    ) -> None:
        csrf_tokens = raw_session.get("csrf_tokens") or {}
        if not isinstance(csrf_tokens, dict):
            return
        header_name = str(recipe.get("csrf_header_name") or "").strip()
        token_field = str(recipe.get("csrf_token_field") or header_name).strip()
        if token_field:
            token = csrf_tokens.get(token_field)
            if isinstance(token, str) and token.strip():
                headers[header_name or token_field] = token.strip()

    def _token_from_session(self, raw_session: dict[str, Any], token_field: str) -> str | None:
        tokens = raw_session.get("tokens") or {}
        if not isinstance(tokens, dict):
            return None
        value = tokens.get(token_field)
        if isinstance(value, str) and value.strip():
            return value.strip().removeprefix("Bearer ").strip()
        return None

    def _error_code_for_status(self, status_code: int) -> str:
        if status_code in {401, 403}:
            return FailureClass.AUTH.value
        if status_code == 404:
            return FailureClass.NOT_FOUND.value
        if status_code == 408:
            return FailureClass.TIMEOUT.value
        if status_code == 422:
            return FailureClass.VALIDATION.value
        if status_code == 429:
            return FailureClass.RATE_LIMITED.value
        if 500 <= status_code <= 599:
            return FailureClass.SERVER_ERROR.value
        return "execution_failed"

    def _record_failure(self, status_code: int | None) -> None:
        if status_code is not None and status_code < 500 and status_code != 429:
            return

        self._failure_count += 1
        if self._failure_count >= self._circuit_breaker_threshold:
            self._circuit_open_until = time.monotonic() + self._circuit_breaker_reset_seconds

    def _reset_circuit_breaker(self) -> None:
        self._failure_count = 0
        self._circuit_open_until = 0.0

    def _http_metadata(self) -> tuple[str, str]:
        extra = getattr(self._capability.input_schema, "model_extra", {}) or {}
        http = extra.get("x-aicp-http") if isinstance(extra, dict) else None
        if not isinstance(http, dict):
            raise ValueError("Capability is missing HTTP execution metadata")
        method = str(http.get("method") or "GET").upper()
        path = str(http.get("path") or "").strip()
        if not path:
            raise ValueError("Capability HTTP execution metadata is missing a path")
        return method, path

    def _base_url(self, context: dict[str, Any]) -> str | None:
        if context.get("provider_url"):
            return str(context["provider_url"])
        provider = getattr(self._capability, "provider", None)
        if provider is not None and getattr(provider, "url", None):
            return str(provider.url)
        return None

    def _coerce_form_value(self, value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    def _build_file_parts(
        self,
        *,
        field_name: str,
        value: Any,
        opened_files: list[Any],
    ) -> list[tuple[str, tuple[str, Any, str]]]:
        if isinstance(value, list):
            parts: list[tuple[str, tuple[str, Any, str]]] = []
            for item in value:
                parts.extend(
                    self._build_file_parts(
                        field_name=field_name,
                        value=item,
                        opened_files=opened_files,
                    )
                )
            return parts

        if isinstance(value, (str, Path)):
            return [self._file_part_from_path(field_name, Path(value), opened_files, {})]

        if not isinstance(value, dict):
            raise ExecutionError(
                f"Unsupported file argument for '{field_name}'.",
                error_code="invalid_arguments",
            )

        if "path" in value:
            return [
                self._file_part_from_path(
                    field_name,
                    Path(str(value["path"])),
                    opened_files,
                    value,
                )
            ]

        if "content_base64" in value:
            try:
                content = base64.b64decode(str(value["content_base64"]))
            except Exception as exc:
                raise ExecutionError(
                    f"Invalid base64 file content for '{field_name}'.",
                    error_code="invalid_arguments",
                ) from exc
        elif "content" in value:
            inline_content = value["content"]
            content = inline_content if isinstance(inline_content, bytes) else str(inline_content).encode("utf-8")
        else:
            raise ExecutionError(
                f"File descriptor for '{field_name}' must include 'path', "
                "'content', or 'content_base64'.",
                error_code="invalid_arguments",
            )

        filename = str(value.get("filename") or field_name).strip() or field_name
        content_type = self._guess_content_type(filename, value.get("content_type"))
        return [(field_name, (filename, content, content_type))]

    def _file_part_from_path(
        self,
        field_name: str,
        path: Path,
        opened_files: list[Any],
        descriptor: dict[str, Any],
    ) -> tuple[str, tuple[str, Any, str]]:
        if not path.exists() or not path.is_file():
            raise ExecutionError(
                f"File path for '{field_name}' does not exist: {path}",
                error_code="invalid_arguments",
            )

        handle = path.open("rb")
        opened_files.append(handle)
        filename = str(descriptor.get("filename") or path.name).strip() or path.name
        content_type = self._guess_content_type(filename, descriptor.get("content_type"))
        return (field_name, (filename, handle, content_type))

    def _guess_content_type(self, filename: str, explicit: Any) -> str:
        if explicit is not None:
            explicit_text = str(explicit).strip()
            if explicit_text:
                return explicit_text
        guessed, _ = mimetypes.guess_type(filename)
        return guessed or "application/octet-stream"

    def _is_file_response(self, response: httpx.Response, content_type: str) -> bool:
        disposition = response.headers.get("Content-Disposition", "")
        lowered_type = content_type.lower()
        return (
            "attachment" in disposition.lower()
            or lowered_type.startswith("application/octet-stream")
            or self._output_expects_binary()
            or (
                lowered_type.startswith("application/")
                and "json" not in lowered_type
                and "xml" not in lowered_type
            )
        )

    def _output_expects_binary(self) -> bool:
        output_schema = getattr(self._capability, "output_schema", None)
        if output_schema is None:
            return False
        extra = getattr(output_schema, "model_extra", {}) or {}
        return (
            getattr(output_schema, "type", None) == "string"
            and isinstance(extra, dict)
            and extra.get("format") == "binary"
        )

    def _build_file_response(self, response: httpx.Response, raw: bytes) -> dict[str, Any]:
        content_type = response.headers.get("Content-Type", "application/octet-stream")
        return {
            "file": {
                "filename": self._filename_from_response(response),
                "content_type": content_type.split(";", 1)[0].strip(),
                "content_length": len(raw),
                "content_base64": base64.b64encode(raw).decode("ascii"),
            }
        }

    def _filename_from_response(self, response: httpx.Response) -> str | None:
        disposition = response.headers.get("Content-Disposition", "")
        match = re.search(r'filename="?([^";]+)"?', disposition, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _build_transport_metadata(
        self,
        *,
        response: httpx.Response,
        url: str,
        result: Any,
    ) -> dict[str, Any] | None:
        continuation = getattr(self._capability, "continuation", None)
        if continuation is None:
            return None

        poll_capability = getattr(continuation, "poll_capability", None)
        poll_argument = getattr(continuation, "poll_argument", None)
        default_poll_after_ms = getattr(continuation, "poll_after_ms", None)
        if not poll_capability and default_poll_after_ms is None:
            return None

        poll_after_ms = self._poll_after_ms(response, default_poll_after_ms)
        poll_url = self._poll_url(response, url)
        poll_arguments = self._poll_arguments(result, poll_argument)

        if response.status_code != 202 and poll_url is None and poll_arguments is None:
            return None

        metadata: dict[str, Any] = {
            "capability": poll_capability,
            "poll_after_ms": poll_after_ms,
            "poll_url": poll_url,
            "arguments": poll_arguments,
        }
        return {key: value for key, value in metadata.items() if value is not None}

    def _poll_after_ms(self, response: httpx.Response, default_ms: int | None) -> int | None:
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            retry_after_text = retry_after.strip()
            if retry_after_text.isdigit():
                return int(retry_after_text) * 1000
        return default_ms

    def _poll_url(self, response: httpx.Response, url: str) -> str | None:
        location = response.headers.get("Location") or response.headers.get("Content-Location")
        if not location:
            return None
        return urljoin(url, location)

    def _poll_arguments(self, result: Any, poll_argument: str | None) -> dict[str, Any] | None:
        if poll_argument is None or not isinstance(result, dict):
            return None
        if poll_argument not in result:
            return None
        return {poll_argument: result[poll_argument]}

    def _repair_validation_error(
        self,
        arguments: dict[str, Any],
        detail: str,
    ) -> dict[str, Any] | None:
        try:
            payload = json.loads(detail)
        except json.JSONDecodeError:
            return None

        errors = payload.get("detail")
        if not isinstance(errors, list):
            return None

        repaired = deepcopy(arguments)
        changed = False

        for item in errors:
            if not isinstance(item, dict):
                continue
            loc = item.get("loc")
            if not isinstance(loc, list) or not loc:
                continue
            field_name = str(loc[-1])
            message = str(item.get("msg") or "")
            input_value = item.get("input")
            schema = self._schema_for_loc(loc)

            repaired_value = self._repair_from_schema(schema, input_value)
            schema_changed = self._assign_repaired_value(repaired, loc, field_name, repaired_value)
            changed = schema_changed or changed
            if repaired_value is not None and schema_changed:
                continue

            if self._looks_like_phone_field(field_name, message):
                repaired_value = self._repair_phone_value(input_value)
                changed = (
                    self._assign_repaired_value(repaired, loc, field_name, repaired_value)
                    or changed
                )
                continue

            if self._looks_like_string_trim_error(input_value, message):
                repaired_value = self._repair_trimmed_string(input_value)
                changed = (
                    self._assign_repaired_value(repaired, loc, field_name, repaired_value)
                    or changed
                )
                continue

            if self._looks_like_date_field(field_name, message):
                repaired_value = self._repair_date_value(input_value)
                changed = (
                    self._assign_repaired_value(repaired, loc, field_name, repaired_value)
                    or changed
                )
                continue

            if self._looks_like_boolean_field(field_name, message):
                repaired_value = self._repair_boolean_value(input_value)
                changed = (
                    self._assign_repaired_value(repaired, loc, field_name, repaired_value)
                    or changed
                )

        return repaired if changed else None

    def _schema_for_loc(self, loc: list[Any]) -> dict[str, Any] | None:
        properties = getattr(self._capability.input_schema, "properties", {}) or {}
        current: Any = properties

        for token in loc:
            if token == "body" and isinstance(current, dict) and "body" in current:
                current = current["body"]
                continue

            if isinstance(current, dict) and isinstance(current.get("properties"), dict):
                current = current["properties"].get(str(token))
                continue

            return None

        return current if isinstance(current, dict) else None

    def _repair_from_schema(self, schema: dict[str, Any] | None, value: Any) -> Any:
        if not isinstance(schema, dict):
            return None

        enum_values = schema.get("enum")
        if isinstance(enum_values, list):
            repaired_enum = self._repair_enum_value(value, enum_values)
            if repaired_enum is not None:
                return repaired_enum

        schema_type = schema.get("type")
        schema_format = schema.get("format")

        if schema_type == "integer":
            return self._repair_integer_value(value)
        if schema_type == "number":
            return self._repair_number_value(value)
        if schema_type == "boolean":
            return self._repair_boolean_value(value)
        if schema_type == "string" and schema_format == "date":
            return self._repair_date_value(value)
        if schema_type == "string":
            return self._repair_trimmed_string(value)

        return None

    def _assign_repaired_value(
        self,
        repaired: dict[str, Any],
        loc: list[Any],
        field_name: str,
        repaired_value: Any,
    ) -> bool:
        if repaired_value is None:
            return False
        if len(loc) >= 2 and loc[0] == "body" and isinstance(repaired.get("body"), dict):
            if repaired["body"].get(field_name) != repaired_value:
                repaired["body"][field_name] = repaired_value
                return True
            return False
        if repaired.get(field_name) != repaired_value:
            repaired[field_name] = repaired_value
            return True
        return False

    def _looks_like_phone_field(self, field_name: str, message: str) -> bool:
        lowered_name = field_name.lower()
        lowered_message = message.lower()
        return "phone" in lowered_name or "phone number" in lowered_message

    def _looks_like_string_trim_error(self, value: Any, message: str) -> bool:
        return (
            isinstance(value, str)
            and value != value.strip()
            and "must not be empty" not in message.lower()
        )

    def _looks_like_date_field(self, field_name: str, message: str) -> bool:
        lowered_name = field_name.lower()
        lowered_message = message.lower()
        return "date" in lowered_name or "date" in lowered_message

    def _looks_like_boolean_field(self, field_name: str, message: str) -> bool:
        lowered_name = field_name.lower()
        lowered_message = message.lower()
        return (
            lowered_name.startswith("is_")
            or lowered_name == "gender"
            or "boolean" in lowered_message
        )

    def _repair_phone_value(self, value: Any) -> str | None:
        digits = re.sub(r"\D", "", str(value or ""))
        if len(digits) < 9:
            return None
        return digits[-9:]

    def _repair_trimmed_string(self, value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        repaired = value.strip()
        return repaired or None

    def _repair_date_value(self, value: Any) -> str | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
            return raw
        if "T" in raw and re.fullmatch(r"\d{4}-\d{2}-\d{2}T.*", raw):
            return raw.split("T", 1)[0]
        match = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", raw)
        if match:
            day, month, year = match.groups()
            return f"{year}-{month}-{day}"
        return None

    def _repair_boolean_value(self, value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        lowered = str(value or "").strip().lower()
        if lowered in {"true", "1", "yes", "y", "male", "m"}:
            return True
        if lowered in {"false", "0", "no", "n", "female", "f"}:
            return False
        return None

    def _repair_integer_value(self, value: Any) -> int | None:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        try:
            text = str(value).strip()
            if re.fullmatch(r"[-+]?\d+", text):
                return int(text)
        except Exception:
            return None
        return None

    def _repair_number_value(self, value: Any) -> float | int | None:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
        try:
            text = str(value).strip()
            if re.fullmatch(r"[-+]?\d+", text):
                return int(text)
            if re.fullmatch(r"[-+]?\d*\.\d+", text):
                return float(text)
        except Exception:
            return None
        return None

    def _repair_enum_value(self, value: Any, enum_values: list[Any]) -> Any:
        raw = str(value or "").strip()
        if not raw:
            return None
        for candidate in enum_values:
            if str(candidate) == raw:
                return candidate
        lowered = raw.lower()
        for candidate in enum_values:
            if str(candidate).lower() == lowered:
                return candidate
        return None

    def _build_repair_metadata(
        self,
        original_arguments: dict[str, Any],
        repaired_arguments: dict[str, Any],
        detail: str,
    ) -> dict[str, Any]:
        repaired_fields = self._diff_repaired_fields(original_arguments, repaired_arguments)
        return {
            "self_healed": True,
            "repair_count": 1,
            "repaired_fields": repaired_fields,
            "repair_reason": "backend_validation_error",
            "original_error": detail,
        }

    def _diff_repaired_fields(
        self,
        original_arguments: dict[str, Any],
        repaired_arguments: dict[str, Any],
    ) -> list[str]:
        fields: list[str] = []
        original_body_value = original_arguments.get("body")
        repaired_body_value = repaired_arguments.get("body")
        original_body = original_body_value if isinstance(original_body_value, dict) else None
        repaired_body = repaired_body_value if isinstance(repaired_body_value, dict) else None
        if original_body is not None and repaired_body is not None:
            for key, value in repaired_body.items():
                if original_body.get(key) != value:
                    fields.append(key)
        for key, value in repaired_arguments.items():
            if key == "body":
                continue
            if original_arguments.get(key) != value:
                fields.append(key)
        return sorted(set(fields))

    def _annotate_metadata(
        self,
        result: Any,
        repair_metadata: dict[str, Any] | None,
        transport_metadata: dict[str, Any] | None,
    ) -> Any:
        if not repair_metadata and not transport_metadata:
            return result
        if isinstance(result, dict):
            annotated = dict(result)
            metadata: dict[str, Any] = {}
            if repair_metadata:
                metadata.update(repair_metadata)
            if transport_metadata:
                metadata["polling"] = transport_metadata
            annotated["_aicp"] = metadata
            return annotated
        return result
