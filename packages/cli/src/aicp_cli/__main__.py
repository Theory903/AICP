"""AICP CLI entry point.

Delegates to the click-based CLI in main.py.
Kept for backward compatibility with existing entry points.
"""

import sys

from aicp_cli.main import cli


def main() -> int:
    """Entry point for the AICP CLI."""
    try:
        cli()
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
