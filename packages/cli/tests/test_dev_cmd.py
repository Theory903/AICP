"""Tests for dev command UX."""

from __future__ import annotations

from types import SimpleNamespace

from aicp_cli.commands.dev_cmd import _print_project_summary


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
