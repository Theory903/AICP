"""Serve command for the AICP CLI."""

from importlib import import_module

from aicp_runtime.server.app import create_app as create_runtime_app


def _load_uvicorn():
    import uvicorn

    return uvicorn.Config, uvicorn.Server


async def cmd_serve(args) -> int:
    """Start an AICP server."""
    try:
        Config, Server = _load_uvicorn()
    except ImportError:
        print("Error: uvicorn not installed. Install with: pip install uvicorn")
        return 1

    if args.app:
        try:
            module_path, app_name = args.app.rsplit(":", 1)
            module = import_module(module_path)
            app = getattr(module, app_name)
        except Exception as e:
            print(f"Error loading app: {e}")
            return 1

        try:
            from aicp.adapters.framework.fastapi import mount_aicp

            mount_aicp(
                app,
                enable_discovery=True,
                discovery_path=args.discovery_path,
            )
        except ImportError:
            print("Warning: FastAPI adapter not available, serving basic discovery only")

        config = Config(
            app,
            host=args.host,
            port=args.port,
            reload=args.reload,
        )
    else:
        try:
            runtime_kwargs = {"store_path": args.store_path}
            if hasattr(args, "store_backend"):
                runtime_kwargs["store_backend"] = args.store_backend
            app = create_runtime_app(**runtime_kwargs)

            config = Config(
                app,
                host=args.host,
                port=args.port,
                reload=args.reload,
            )
        except ImportError as e:
            print(f"Error: FastAPI not available: {e}")
            print("Install with: pip install aicp[fastapi]")
            return 1

    server = Server(config)
    print(f"Starting AICP server on {args.host}:{args.port}")
    print(f"Discovery endpoint: http://{args.host}:{args.port}{args.discovery_path}")

    await server.serve()
    return 0
