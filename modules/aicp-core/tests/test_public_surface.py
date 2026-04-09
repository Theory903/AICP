"""Tests for the public AICP package surface."""

from aicp import AicpRegistry, ContinuationSpec, RenderSpec, __version__


def test_public_package_exports_render_types() -> None:
    assert RenderSpec.__name__ == "RenderSpec"
    assert ContinuationSpec.__name__ == "ContinuationSpec"


def test_render_spec_supports_table_columns() -> None:
    render = RenderSpec(format="table", table_columns=["id", "amount", "id"])

    assert render.table_columns == ["id", "amount"]


def test_public_version_matches_discovery_payload() -> None:
    registry = AicpRegistry()

    assert __version__ == "0.3.0"
    assert registry.discovery_response()["version"] == "0.3.0"
