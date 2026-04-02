"""AICP CLI entry point.

Delegates to the click-based CLI in main.py.
Kept for backward compatibility with existing entry points.
"""

from __future__ import annotations

import sys

from aicp_cli.main import cli


def _system_exit_code(exc: SystemExit) -> int:
    """Normalize SystemExit.code into an integer exit status."""
    code = exc.code

    if code is None:
        return 0

    if isinstance(code, int):
        return code

    # Click and other CLI systems may exit with a message object/string.
    # In that case, stderr/stdout is already handled elsewhere, and the
    # process should still return a failure code.
    return 1


def main() -> int:
    """Run the AICP CLI and return a process exit code."""
    try:
        cli()
        return 0
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except SystemExit as exc:
        return _system_exit_code(exc)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
