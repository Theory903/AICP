"""Tests for CLI import commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from aicp_cli.commands.import_cmd import _run_import_openapi


@pytest.mark.asyncio
async def test_run_import_openapi_reads_spec_file_and_exports(tmp_path: Path) -> None:
    spec_file = tmp_path / "openapi.json"
    spec_file.write_text(
        json.dumps(
            {
                "openapi": "3.0.3",
                "info": {"title": "Mini API", "version": "1.0.0"},
                "paths": {},
            }
        ),
        encoding="utf-8",
    )

    captured: dict[str, object] = {}

    class FakeSource:
        def __init__(self, name: str, spec: dict, spec_url: str | None = None, base_url: str | None = None):
            captured["name"] = name
            captured["spec"] = spec
            captured["spec_url"] = spec_url
            captured["base_url"] = base_url

        async def discover(self):
            return []

    fake_module = ModuleType("aicp_connect_openapi")
    fake_module.OpenAPIDiscoverySource = FakeSource
    sys.modules["aicp_connect_openapi"] = fake_module

    try:
        exit_code = await _run_import_openapi(spec_file, "mini", "https://api.example.com", None)
    finally:
        sys.modules.pop("aicp_connect_openapi", None)

    assert exit_code == 0
    assert captured == {
        "name": "mini",
        "spec": {
            "openapi": "3.0.3",
            "info": {"title": "Mini API", "version": "1.0.0"},
            "paths": {},
        },
        "spec_url": str(spec_file),
        "base_url": "https://api.example.com",
    }
