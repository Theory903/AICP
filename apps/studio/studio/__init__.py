"""AICP Studio seed app public export."""

from __future__ import annotations

from fastapi import FastAPI

from studio.app import create_studio_app as _create_studio_app

__all__ = ["create_studio_app"]


def create_studio_app(*args, **kwargs) -> FastAPI:
    """Create the AICP Studio application."""
    return _create_studio_app(*args, **kwargs)
