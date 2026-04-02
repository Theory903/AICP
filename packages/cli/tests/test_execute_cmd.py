"""Tests for execute CLI behavior."""

from __future__ import annotations

from click.testing import CliRunner

from aicp_cli.commands.execute_cmd import run_cmd
from aicp_cli.commands.serve_cmd import serve_cmd


def test_run_cmd_shows_friendly_error_outside_project() -> None:
    runner = CliRunner()

    result = runner.invoke(run_cmd, ["health_health_get"])

    assert result.exit_code == 1
    assert "No AICP project found" in result.output
    assert "aicp init" in result.output
    assert "Traceback" not in result.output


def test_serve_cmd_shows_friendly_error_outside_project() -> None:
    runner = CliRunner()

    result = runner.invoke(serve_cmd)

    assert result.exit_code == 1
    assert "No AICP project found" in result.output
    assert "aicp init" in result.output
    assert "Traceback" not in result.output
