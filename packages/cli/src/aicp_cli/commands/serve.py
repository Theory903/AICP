"""Serve command for the AICP CLI."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from aicp_runtime.server.app import create_app as create_runtime_app


def _load_uvicorn():
    """Load uvicorn classes lazily."""
    import uvicorn

    return uvicorn.Config, uvicorn.Server


def _load_user_app(app_spec: str) -> Any:
    """Load a user application from module:app notation."""
    if ":" not in app_spec:
        raise ValueError("App must be in 'module:app' format")

    module_path, app_name = app_spec.rsplit(":", 1)
    if not module_path.strip() or not app_name.strip():
        raise ValueError("App must be in 'module:app' format")

    module = import_module(module_path)
    try:
        return getattr(module, app_name)
    except AttributeError as exc:
        raise ValueError(
            f"Module '{module_path}' has no attribute '{app_name}'"
        ) from exc


def _try_mount_aicp(app: Any, discovery_path: str) -> None:
    """Try to mount AICP routes into a framework app."""
    try:
        from aicp.adapters.framework.fastapi import mount_aicp
    except ImportError as exc:
        raise RuntimeError("FastAPI adapter not available") from exc

    mount_aicp(
        app,
        enable_discovery=True,
        discovery_path=discovery_path,
    )


def _build_runtime_app(args: Any) -> Any:
    """Create the standalone runtime app."""
    runtime_kwargs: dict[str, Any] = {"store_path": args.store_path}

    if hasattr(args, "store_backend") and args.store_backend is not None:
        runtime_kwargs["store_backend"] = args.store_backend

    return create_runtime_app(**runtime_kwargs)


def _build_server_config(Config: Any, app: Any, args: Any) -> Any:
    """Create uvicorn config."""
    return Config(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


def _print_startup_info(args: Any) -> None:
    """Print startup details."""
    print(f"Starting AICP server on {args.host}:{args.port}")
    print(f"Discovery endpoint: http://{args.host}:{args.port}{args.discovery_path}")


async def cmd_serve(args) -> int:
    """Start an AICP server."""
    if args.app:
        try:
            app = _load_user_app(args.app)
        except Exception as exc:
            print(f"Error loading app '{args.app}': {exc}")
            return 1

        try:
            _try_mount_aicp(app, args.discovery_path)
        except RuntimeError as exc:
            print(f"Warning: {exc}, serving app without mounted AICP adapter")
        except Exception as exc:
            print(f"Warning: Failed to mount AICP adapter: {exc}")

    else:
        try:
            app = _build_runtime_app(args)
        except ImportError as exc:
            print(f"Error: FastAPI not available: {exc}")
            print("Install with: pip install aicp[fastapi]")
            return 1
        except Exception as exc:
            print(f"Error creating runtime app: {exc}")
            return 1

    try:
        Config, Server = _load_uvicorn()
    except ImportError:
        print("Error: uvicorn not installed. Install with: pip install uvicorn")
        return 1

    try:
        config = _build_server_config(Config, app, args)
    except Exception as exc:
        print(f"Error configuring server: {exc}")
        return 1

    _print_startup_info(args)

    server = Server(config)
    await server.serve()
    return 0
