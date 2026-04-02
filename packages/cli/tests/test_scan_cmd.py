"""Tests for scan command behavior."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI

from aicp_cli.commands.scan_cmd import _scan_fastapi


def test_placeholder() -> None:
    assert True


def test_scan_fastapi_prefers_openapi_import_path(monkeypatch, tmp_path: Path) -> None:
    app = FastAPI(title="Demo API")

    @app.get("/items")
    def list_items() -> list[dict[str, int]]:
        return [{"id": 1}]

    captured: dict[str, object] = {}

    def fake_handle(capabilities, **kwargs):
        captured["capabilities"] = capabilities
        captured["title"] = kwargs["title"]

    class FakeSource:
        def __init__(self, name, spec, spec_url=None, base_url=None):
            captured["name"] = name
            captured["spec"] = spec
            captured["spec_url"] = spec_url
            captured["base_url"] = base_url

        async def discover(self):
            return [type("Cap", (), {"name": "items.list", "kind": type("K", (), {"value": "query"})()})()]

    monkeypatch.setattr("aicp_cli.commands.scan_cmd._import_module", lambda module_name: type("M", (), {"app": app})())
    monkeypatch.setattr("aicp_cli.commands.scan_cmd._handle_scan_results", fake_handle)
    monkeypatch.setattr("aicp_cli.commands.scan_cmd._load_config", lambda: type("C", (), {"provider_name": "aicp", "capabilities_dir": str(tmp_path)})())
    monkeypatch.setitem(__import__("sys").modules, "aicp_connect_openapi", type("Mod", (), {"OpenAPIDiscoverySource": FakeSource})())

    asyncio.run(_scan_fastapi("demo:app", None, False))

    assert captured["name"] == "aicp"
    assert isinstance(captured["spec"], dict)
    assert captured["title"] == "Detected 1 Capabilities"
