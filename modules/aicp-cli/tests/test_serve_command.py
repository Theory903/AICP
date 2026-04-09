"""Tests for the modular serve command."""

import argparse

import pytest

from aicp_cli.commands.serve import cmd_serve


@pytest.mark.asyncio
async def test_cmd_serve_creates_minimal_app_and_runs_server(monkeypatch) -> None:
    seen = {}

    class FakeConfig:
        def __init__(self, app, host, port, reload):
            seen["app"] = app
            seen["host"] = host
            seen["port"] = port
            seen["reload"] = reload

    class FakeServer:
        def __init__(self, config):
            self.config = config

        async def serve(self):
            seen["served"] = True

    import aicp_cli.commands.serve as serve_module

    monkeypatch.setattr(serve_module, "_load_uvicorn", lambda: (FakeConfig, FakeServer))

    def fake_create_runtime_app(**kwargs):
        seen["runtime_app_kwargs"] = kwargs
        return object()

    monkeypatch.setattr(serve_module, "create_runtime_app", fake_create_runtime_app)
    args = argparse.Namespace(
        host="127.0.0.1",
        port=9000,
        app=None,
        discovery_path="/.well-known/aicp",
        store_path=None,
        reload=False,
    )

    exit_code = await cmd_serve(args)

    assert exit_code == 0
    assert seen["host"] == "127.0.0.1"
    assert seen["port"] == 9000
    assert seen["served"] is True
    assert seen["runtime_app_kwargs"] == {"store_path": None}


@pytest.mark.asyncio
async def test_cmd_serve_errors_for_bad_app_import(capsys) -> None:
    args = argparse.Namespace(
        host="127.0.0.1",
        port=8000,
        app="missing.module:app",
        discovery_path="/.well-known/aicp",
        store_path=None,
        reload=False,
    )

    exit_code = await cmd_serve(args)
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "Error loading app" in output


@pytest.mark.asyncio
async def test_cmd_serve_passes_store_path_to_runtime_app(
    monkeypatch, tmp_path
) -> None:
    seen = {}

    class FakeConfig:
        def __init__(self, app, host, port, reload):
            seen["app"] = app

    class FakeServer:
        def __init__(self, config):
            self.config = config

        async def serve(self):
            seen["served"] = True

    import aicp_cli.commands.serve as serve_module

    monkeypatch.setattr(serve_module, "_load_uvicorn", lambda: (FakeConfig, FakeServer))

    def fake_create_runtime_app(**kwargs):
        seen["runtime_app_kwargs"] = kwargs
        return object()

    monkeypatch.setattr(serve_module, "create_runtime_app", fake_create_runtime_app)
    args = argparse.Namespace(
        host="127.0.0.1",
        port=8001,
        app=None,
        discovery_path="/.well-known/aicp",
        store_path=str(tmp_path / "runtime-store"),
        reload=False,
    )

    exit_code = await cmd_serve(args)

    assert exit_code == 0
    assert seen["served"] is True
    assert seen["runtime_app_kwargs"]["store_path"] == str(tmp_path / "runtime-store")


@pytest.mark.asyncio
async def test_cmd_serve_passes_sqlite_backend_to_runtime_app(
    monkeypatch, tmp_path
) -> None:
    seen = {}

    class FakeConfig:
        def __init__(self, app, host, port, reload):
            seen["app"] = app

    class FakeServer:
        def __init__(self, config):
            self.config = config

        async def serve(self):
            seen["served"] = True

    import aicp_cli.commands.serve as serve_module

    monkeypatch.setattr(serve_module, "_load_uvicorn", lambda: (FakeConfig, FakeServer))

    def fake_create_runtime_app(**kwargs):
        seen["runtime_app_kwargs"] = kwargs
        return object()

    monkeypatch.setattr(serve_module, "create_runtime_app", fake_create_runtime_app)
    args = argparse.Namespace(
        host="127.0.0.1",
        port=8001,
        app=None,
        discovery_path="/.well-known/aicp",
        store_path=str(tmp_path / "runtime.db"),
        store_backend="sqlite",
        reload=False,
    )

    exit_code = await cmd_serve(args)

    assert exit_code == 0
    assert seen["served"] is True
    assert seen["runtime_app_kwargs"]["store_path"] == str(tmp_path / "runtime.db")
    assert seen["runtime_app_kwargs"]["store_backend"] == "sqlite"
