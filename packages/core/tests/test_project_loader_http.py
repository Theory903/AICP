"""Tests for HTTP-backed capability loading and execution."""

from __future__ import annotations

import base64
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from aicp.project_loader import load_project


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            payload = json.dumps({"message": "ok"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_error(404)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def test_load_project_executes_http_backed_capability(tmp_path: Path) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        (tmp_path / "aicp").mkdir()
        (tmp_path / "aicp" / "capabilities").mkdir(parents=True)
        (tmp_path / "aicp.yaml").write_text(
            f"""
defaults:
  queries: allow
  actions: ask
  destructive: require_approval
capabilities_dir: aicp/capabilities
policies_dir: aicp/policies
workflows_dir: aicp/workflows
fixtures_dir: aicp/fixtures
runtime:
  host: 127.0.0.1
  port: 8000
  reload: false
  store_backend: memory
provider_name: aicp
provider_url: http://127.0.0.1:{server.server_port}
version: 0.1.0
""",
            encoding="utf-8",
        )
        (tmp_path / "aicp" / "capabilities" / "health.list.yaml").write_text(
            """
name: health.list
kind: query
description: Health
input_schema:
  type: object
  properties: {}
  required: []
  x-aicp-http:
    method: GET
    path: /health
output_schema:
  type: object
  properties: {}
provider:
  name: aicp
  type: openapi
render:
  format: json
""",
            encoding="utf-8",
        )

        project = load_project(tmp_path)

        result = __import__("asyncio").run(project.executor.execute("health.list", {}))

        assert result.status.value == "success"
        assert result.data == {"message": "ok"}
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_http_backed_capability_retries_once_with_phone_repair(tmp_path: Path) -> None:
    class RepairHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            payload = json.loads(raw.decode("utf-8"))
            if payload.get("guardian_phone_no") == "999999999":
                body = json.dumps({"id": 1, **payload}).encode("utf-8")
                self.send_response(201)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            body = json.dumps(
                {
                    "detail": [
                        {
                            "type": "value_error",
                            "loc": ["body", "guardian_phone_no"],
                            "msg": "Value error, Please Enter a valid phone number.",
                            "input": payload.get("guardian_phone_no"),
                        }
                    ]
                }
            ).encode("utf-8")
            self.send_response(422)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), RepairHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        (tmp_path / "aicp").mkdir()
        (tmp_path / "aicp" / "capabilities").mkdir(parents=True)
        (tmp_path / "aicp.yaml").write_text(
            f"""
defaults:
  queries: allow
  actions: allow
  destructive: require_approval
capabilities_dir: aicp/capabilities
policies_dir: aicp/policies
workflows_dir: aicp/workflows
fixtures_dir: aicp/fixtures
runtime:
  host: 127.0.0.1
  port: 8000
  reload: false
  store_backend: memory
provider_name: aicp
provider_url: http://127.0.0.1:{server.server_port}
version: 0.1.0
""",
            encoding="utf-8",
        )
        (tmp_path / "aicp" / "capabilities" / "students.create.yaml").write_text(
            """
name: students.create
kind: action
description: Create student
input_schema:
  type: object
  properties:
    body:
      type: object
      properties:
        guardian_phone_no:
          type: string
      required:
        - guardian_phone_no
      x-location: body
  required:
    - body
  x-aicp-http:
    method: POST
    path: /students
output_schema:
  type: object
  properties: {}
provider:
  name: aicp
  type: openapi
render:
  format: json
""",
            encoding="utf-8",
        )

        project = load_project(tmp_path)

        result = __import__("asyncio").run(
            project.executor.execute(
                "students.create",
                {"body": {"guardian_phone_no": "9999999999"}},
            )
        )

        assert result.status.value == "success"
        assert result.data["guardian_phone_no"] == "999999999"
        assert result.data["_aicp"]["self_healed"] is True
        assert result.data["_aicp"]["repaired_fields"] == ["guardian_phone_no"]
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_http_backed_capability_repairs_values_using_schema_hints(tmp_path: Path) -> None:
    class RepairHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            payload = json.loads(raw.decode("utf-8"))
            if payload == {
                "date_of_birth": "2004-01-01",
                "enabled": True,
                "level": 7,
                "mode": "active",
            }:
                body = json.dumps({"ok": True, **payload}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            body = json.dumps(
                {
                    "detail": [
                        {
                            "loc": ["body", "date_of_birth"],
                            "msg": "invalid date",
                            "input": payload.get("date_of_birth"),
                        },
                        {
                            "loc": ["body", "enabled"],
                            "msg": "invalid boolean",
                            "input": payload.get("enabled"),
                        },
                        {
                            "loc": ["body", "level"],
                            "msg": "invalid integer",
                            "input": payload.get("level"),
                        },
                        {
                            "loc": ["body", "mode"],
                            "msg": "invalid enum",
                            "input": payload.get("mode"),
                        },
                    ]
                }
            ).encode("utf-8")
            self.send_response(422)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), RepairHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        (tmp_path / "aicp").mkdir()
        (tmp_path / "aicp" / "capabilities").mkdir(parents=True)
        (tmp_path / "aicp.yaml").write_text(
            f"""
defaults:
  queries: allow
  actions: allow
  destructive: require_approval
capabilities_dir: aicp/capabilities
policies_dir: aicp/policies
workflows_dir: aicp/workflows
fixtures_dir: aicp/fixtures
runtime:
  host: 127.0.0.1
  port: 8000
  reload: false
  store_backend: memory
provider_name: aicp
provider_url: http://127.0.0.1:{server.server_port}
version: 0.1.0
""",
            encoding="utf-8",
        )
        (tmp_path / "aicp" / "capabilities" / "demo.create.yaml").write_text(
            """
name: demo.create
kind: action
description: Create demo object
input_schema:
  type: object
  properties:
    body:
      type: object
      properties:
        date_of_birth:
          type: string
          format: date
        enabled:
          type: boolean
        level:
          type: integer
        mode:
          type: string
          enum:
            - active
            - inactive
      required:
        - date_of_birth
        - enabled
        - level
        - mode
      x-location: body
  required:
    - body
  x-aicp-http:
    method: POST
    path: /demo
output_schema:
  type: object
  properties: {}
provider:
  name: aicp
  type: openapi
render:
  format: json
""",
            encoding="utf-8",
        )

        project = load_project(tmp_path)
        result = __import__("asyncio").run(
            project.executor.execute(
                "demo.create",
                {
                    "body": {
                        "date_of_birth": "2004-01-01T00:00:00",
                        "enabled": "yes",
                        "level": "7",
                        "mode": "ACTIVE",
                    }
                },
            )
        )

        assert result.status.value == "success"
        assert result.data["date_of_birth"] == "2004-01-01"
        assert result.data["enabled"] is True
        assert result.data["level"] == 7
        assert result.data["mode"] == "active"
        assert result.data["_aicp"]["repaired_fields"] == [
            "date_of_birth",
            "enabled",
            "level",
            "mode",
        ]
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_http_backed_capability_injects_bearer_auth_from_config(tmp_path: Path) -> None:
    class AuthHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.headers.get("Authorization") != "Bearer top-secret":
                body = json.dumps({"detail": "missing auth"}).encode("utf-8")
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            body = json.dumps({"message": "secure ok"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), AuthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        (tmp_path / "aicp").mkdir()
        (tmp_path / "aicp" / "capabilities").mkdir(parents=True)
        (tmp_path / "aicp.yaml").write_text(
            f"""
defaults:
  queries: allow
  actions: allow
  destructive: require_approval
capabilities_dir: aicp/capabilities
runtime:
  host: 127.0.0.1
  port: 8000
  reload: false
  store_backend: memory
provider_name: aicp
provider_url: http://127.0.0.1:{server.server_port}
auth:
  type: bearer
  token: top-secret
version: 0.1.0
""",
            encoding="utf-8",
        )
        (tmp_path / "aicp" / "capabilities" / "secure.list.yaml").write_text(
            """
name: secure.list
kind: query
description: Secure list
input_schema:
  type: object
  properties: {}
  required: []
  x-aicp-http:
    method: GET
    path: /secure
output_schema:
  type: object
  properties: {}
provider:
  name: aicp
  type: openapi
render:
  format: json
""",
            encoding="utf-8",
        )

        project = load_project(tmp_path)
        result = __import__("asyncio").run(project.executor.execute("secure.list", {}))

        assert result.status.value == "success"
        assert result.data == {"message": "secure ok"}
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_http_backed_capability_classifies_auth_failures(tmp_path: Path) -> None:
    class AuthHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            body = json.dumps({"detail": "missing auth"}).encode("utf-8")
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), AuthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        (tmp_path / "aicp").mkdir()
        (tmp_path / "aicp" / "capabilities").mkdir(parents=True)
        (tmp_path / "aicp.yaml").write_text(
            f"""
defaults:
  queries: allow
  actions: allow
  destructive: require_approval
capabilities_dir: aicp/capabilities
runtime:
  host: 127.0.0.1
  port: 8000
  reload: false
  store_backend: memory
provider_name: aicp
provider_url: http://127.0.0.1:{server.server_port}
version: 0.1.0
""",
            encoding="utf-8",
        )
        (tmp_path / "aicp" / "capabilities" / "secure.list.yaml").write_text(
            """
name: secure.list
kind: query
description: Secure list
input_schema:
  type: object
  properties: {}
  required: []
  x-aicp-http:
    method: GET
    path: /secure
output_schema:
  type: object
  properties: {}
provider:
  name: aicp
  type: openapi
render:
  format: json
""",
            encoding="utf-8",
        )

        project = load_project(tmp_path)
        result = __import__("asyncio").run(project.executor.execute("secure.list", {}))

        assert result.status.value == "failure"
        assert result.error_code == "authentication_failed"
        assert result.next is not None
        assert result.next["action"] == "inspect"
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_http_backed_capability_times_out_cleanly(tmp_path: Path) -> None:
    class SlowHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            time.sleep(0.2)
            body = json.dumps({"message": "late"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), SlowHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        (tmp_path / "aicp").mkdir()
        (tmp_path / "aicp" / "capabilities").mkdir(parents=True)
        (tmp_path / "aicp.yaml").write_text(
            f"""
defaults:
  queries: allow
  actions: allow
  destructive: require_approval
capabilities_dir: aicp/capabilities
runtime:
  host: 127.0.0.1
  port: 8000
  reload: false
  store_backend: memory
provider_name: aicp
provider_url: http://127.0.0.1:{server.server_port}
request_timeout_seconds: 0.05
execution_timeout_seconds: 0.1
version: 0.1.0
""",
            encoding="utf-8",
        )
        (tmp_path / "aicp" / "capabilities" / "slow.list.yaml").write_text(
            """
name: slow.list
kind: query
description: Slow list
input_schema:
  type: object
  properties: {}
  required: []
  x-aicp-http:
    method: GET
    path: /slow
output_schema:
  type: object
  properties: {}
provider:
  name: aicp
  type: openapi
render:
  format: json
""",
            encoding="utf-8",
        )

        project = load_project(tmp_path)
        result = __import__("asyncio").run(project.executor.execute("slow.list", {}))

        assert result.status.value == "timeout"
        assert result.error_code == "timeout"
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_load_project_warns_and_skips_invalid_capability_files(tmp_path: Path) -> None:
    (tmp_path / "aicp").mkdir()
    (tmp_path / "aicp" / "capabilities").mkdir(parents=True)
    (tmp_path / "aicp.yaml").write_text(
        """
defaults:
  queries: allow
  actions: allow
  destructive: require_approval
capabilities_dir: aicp/capabilities
runtime:
  host: 127.0.0.1
  port: 8000
  reload: false
  store_backend: memory
provider_name: aicp
version: 0.1.0
""",
        encoding="utf-8",
    )
    (tmp_path / "aicp" / "capabilities" / "valid.list.yaml").write_text(
        """
name: valid.list
kind: query
description: Valid capability
input_schema:
  type: object
  properties: {}
  required: []
output_schema:
  type: object
  properties: {}
""",
        encoding="utf-8",
    )
    (tmp_path / "aicp" / "capabilities" / "broken.yaml").write_text(
        "name: [unterminated\n",
        encoding="utf-8",
    )

    project = load_project(tmp_path)

    assert [cap.name for cap in project.capabilities] == ["valid.list"]
    assert any("Skipping capability file" in warning for warning in project.warnings)


def test_http_backed_capability_supports_multipart_uploads(tmp_path: Path) -> None:
    class UploadHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            content_type = self.headers.get("Content-Type", "")

            assert "multipart/form-data" in content_type
            assert b'name="title"' in raw
            assert b"Quarterly export" in raw
            assert b'name="upload_path"; filename="sample.txt"' in raw
            assert b"path payload" in raw
            assert b'name="upload_inline"; filename="inline.txt"' in raw
            assert b"inline payload" in raw

            body = json.dumps({"uploaded": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), UploadHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        upload_file = tmp_path / "sample.txt"
        upload_file.write_text("path payload", encoding="utf-8")

        (tmp_path / "aicp").mkdir()
        (tmp_path / "aicp" / "capabilities").mkdir(parents=True)
        (tmp_path / "aicp.yaml").write_text(
            f"""
defaults:
  queries: allow
  actions: allow
  destructive: require_approval
capabilities_dir: aicp/capabilities
provider_name: aicp
provider_url: http://127.0.0.1:{server.server_port}
version: 0.1.0
""",
            encoding="utf-8",
        )
        (tmp_path / "aicp" / "capabilities" / "files.upload.yaml").write_text(
            """
name: files.upload
kind: action
description: Upload files
input_schema:
  type: object
  properties:
    title:
      type: string
      x-location: form
    upload_path:
      type: string
      format: binary
      x-location: file
    upload_inline:
      type: string
      format: binary
      x-location: file
  required:
    - title
    - upload_path
    - upload_inline
  x-aicp-http:
    method: POST
    path: /upload
output_schema:
  type: object
  properties: {}
provider:
  name: aicp
  type: openapi
render:
  format: json
""",
            encoding="utf-8",
        )

        project = load_project(tmp_path)
        result = __import__("asyncio").run(
            project.executor.execute(
                "files.upload",
                {
                    "title": "Quarterly export",
                    "upload_path": str(upload_file),
                    "upload_inline": {
                        "filename": "inline.txt",
                        "content": "inline payload",
                        "content_type": "text/plain",
                    },
                },
            )
        )

        assert result.status.value == "success"
        assert result.data == {"uploaded": True}
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_http_backed_capability_returns_structured_download_metadata(tmp_path: Path) -> None:
    class DownloadHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            payload = b"abc"
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", 'attachment; filename="report.bin"')
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), DownloadHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        (tmp_path / "aicp").mkdir()
        (tmp_path / "aicp" / "capabilities").mkdir(parents=True)
        (tmp_path / "aicp.yaml").write_text(
            f"""
defaults:
  queries: allow
  actions: allow
  destructive: require_approval
capabilities_dir: aicp/capabilities
provider_name: aicp
provider_url: http://127.0.0.1:{server.server_port}
version: 0.1.0
""",
            encoding="utf-8",
        )
        (tmp_path / "aicp" / "capabilities" / "files.download.yaml").write_text(
            """
name: files.download
kind: query
description: Download file
input_schema:
  type: object
  properties: {}
  x-aicp-http:
    method: GET
    path: /download
output_schema:
  type: object
  properties: {}
provider:
  name: aicp
  type: openapi
render:
  format: json
""",
            encoding="utf-8",
        )

        project = load_project(tmp_path)
        result = __import__("asyncio").run(project.executor.execute("files.download", {}))

        assert result.status.value == "success"
        assert result.data == {
            "file": {
                "filename": "report.bin",
                "content_type": "application/octet-stream",
                "content_length": 3,
                "content_base64": base64.b64encode(b"abc").decode("ascii"),
            }
        }
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_http_backed_capability_surfaces_polling_hints(tmp_path: Path) -> None:
    class AsyncJobHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            body = json.dumps({"job_id": "job-123", "state": "queued"}).encode("utf-8")
            self.send_response(202)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Location", "/jobs/job-123")
            self.send_header("Retry-After", "2")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), AsyncJobHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        (tmp_path / "aicp").mkdir()
        (tmp_path / "aicp" / "capabilities").mkdir(parents=True)
        (tmp_path / "aicp.yaml").write_text(
            f"""
defaults:
  queries: allow
  actions: allow
  destructive: require_approval
capabilities_dir: aicp/capabilities
provider_name: aicp
provider_url: http://127.0.0.1:{server.server_port}
version: 0.1.0
""",
            encoding="utf-8",
        )
        (tmp_path / "aicp" / "capabilities" / "exports.create.yaml").write_text(
            """
name: exports.create
kind: async_action
description: Start export job
input_schema:
  type: object
  properties: {}
  x-aicp-http:
    method: POST
    path: /exports
output_schema:
  type: object
  properties: {}
continuation:
  can_continue: true
  next_hint: Poll for completion.
  poll_capability: exports.get
  poll_after_ms: 1000
  poll_argument: job_id
provider:
  name: aicp
  type: openapi
render:
  format: json
""",
            encoding="utf-8",
        )

        project = load_project(tmp_path)
        result = __import__("asyncio").run(project.executor.execute("exports.create", {}))

        assert result.status.value == "success"
        assert result.next == {
            "action": "wait",
            "capability": "exports.get",
            "arguments": {"job_id": "job-123"},
            "hint": "Poll for completion.",
            "poll_after_ms": 2000,
            "poll_url": f"http://127.0.0.1:{server.server_port}/jobs/job-123",
        }
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()
