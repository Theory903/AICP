"""Compatibility wrapper for the Connect OpenAPI adapter.

This module preserves the old import path while delegating to the
OpenAPI adapter package. If the adapter is not installed, the imports
will fail with a clear error message.
"""

from __future__ import annotations

try:
    from aicp_connect_openapi import OpenAPIDiscoverySource
except ImportError:  # pragma: no cover
    def _missing_adapter(*args, **kwargs):
        raise RuntimeError(
            "OpenAPI adapter is not installed. "
            "Install the OpenAPI adapter package to use these helpers."
        )

    OpenAPIDiscoverySource = _missing_adapter


__all__ = [
    "OpenAPIDiscoverySource",
]
