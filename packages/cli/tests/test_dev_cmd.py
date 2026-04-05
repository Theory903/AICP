"""Tests for dev command UX."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from aicp_cli.commands.dev_cmd import _dev, _print_project_summary


def test_print_startup_summary_uses_history_route(capsys) -> None:
    config = SimpleNamespace(
        effective_effect=lambda capability_name, kind, is_destructive: "allow",
        capabilities_dir="aicp/capabilities",
    )
    project = SimpleNamespace(capabilities=[], warnings=[])

    _print_project_summary(
        project=project,
        config=config,
        host="127.0.0.1",
        port=8000,
        mounted=False,
        app_path=None,
        reload_enabled=False,
    )

    output = capsys.readouterr().out

    assert "http://127.0.0.1:8000/history" in output
    assert "/audit/" not in output


@pytest.mark.asyncio
async def test_dev_starts_runtime_without_project_config(monkeypatch, tmp_path) -> None:
    seen: dict[str, object] = {}

    async def fake_serve_app(app, *, host, port, reload_enabled, app_import_path) -> None:
        seen["app"] = app
        seen["host"] = host
        seen["port"] = port
        seen["reload_enabled"] = reload_enabled
        seen["app_import_path"] = app_import_path

    import aicp_cli.commands.dev_cmd as dev_module

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(dev_module, "_serve_app", fake_serve_app)

    await _dev("127.0.0.1", 1000, None, reload_enabled=False)

    assert seen["host"] == "127.0.0.1"
    assert seen["port"] == 1000
    assert seen["reload_enabled"] is False
    assert seen["app_import_path"] is None
