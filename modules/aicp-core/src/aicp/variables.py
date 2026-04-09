"""Variable substitution system for AICP.

Enables dynamic replacement of placeholders like ${VAR} or $VAR in configurations.
Supports environment variables, config variables, .env files, namespacing,
and optional default values via ${VAR:-default}.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

_VARIABLE_PATTERN = re.compile(
    r"""
    \$\{(?P<braced>[A-Za-z_][A-Za-z0-9_]*)(?::-(?P<default>[^}]*))?\}
    |
    \$(?P<bare>[A-Za-z_][A-Za-z0-9_]*)
    """,
    re.VERBOSE,
)


def load_dotenv(env_file: str | Path = ".env", override: bool = False) -> dict[str, str]:
    """Load variables from a .env file into the environment.

    Supported lines:
        KEY=value
        export KEY=value
        # comments

    Args:
        env_file: Path to .env file.
        override: Whether to override existing environment variables.

    Returns:
        Dictionary of variables parsed from the file.
    """
    env_path = Path(env_file)
    if not env_path.exists():
        return {}

    loaded: dict[str, str] = {}

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[len("export ") :].strip()

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            continue

        # Strip matching quotes only
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        loaded[key] = value

        if override or key not in os.environ:
            os.environ[key] = value

    return loaded


class DotEnvLoader:
    """Variable loader that reads from .env files."""

    def __init__(self, env_file: str | Path = ".env", override: bool = False):
        self.env_file = Path(env_file)
        self.override = override
        self._loaded_values: dict[str, str] = {}
        self._loaded = False

    def load(self) -> dict[str, str]:
        """Load variables from .env file once and return loaded values."""
        if not self._loaded:
            self._loaded_values = load_dotenv(self.env_file, self.override)
            self._loaded = True
        return dict(self._loaded_values)

    def get(self, key: str, default: str | None = None) -> str | None:
        """Get a variable value, loading the file first if needed."""
        self.load()
        return os.environ.get(key, default)


class VariableNotFoundError(Exception):
    """Raised when a required variable cannot be found."""

    def __init__(self, key: str):
        self.key = key
        super().__init__(f"Variable not found: {key}")


class VariableSubstitutor:
    """Variable substitution with hierarchical resolution.

    Resolution order:
    1. Namespaced config variable (namespace_KEY)
    2. Direct config variable (KEY)
    3. Namespaced environment variable (namespace_KEY)
    4. Direct environment variable (KEY)
    5. Inline default in ${KEY:-default}

    Supports:
    - ${VAR}
    - $VAR
    - ${VAR:-default}
    """

    def __init__(self, variables: dict[str, str] | None = None):
        self._variables = dict(variables or {})

    def substitute(
        self,
        obj: dict[str, Any] | list[Any] | str,
        namespace: str | None = None,
    ) -> Any:
        """Recursively substitute variables in nested data structures."""
        if isinstance(obj, str):
            return self._substitute_string(obj, namespace)
        if isinstance(obj, dict):
            return {key: self.substitute(value, namespace) for key, value in obj.items()}
        if isinstance(obj, list):
            return [self.substitute(item, namespace) for item in obj]
        return obj

    def _substitute_string(self, value: str, namespace: str | None) -> str:
        """Substitute variables in a single string."""
        # Preserve JSON schema refs and similar literal markers
        if value.strip() == "$ref":
            return value

        def replacer(match: re.Match[str]) -> str:
            key = match.group("braced") or match.group("bare")
            default = match.group("default")
            if key is None:
                return match.group(0)
            return self._get_variable(key, namespace=namespace, default=default)

        return _VARIABLE_PATTERN.sub(replacer, value)

    def _get_variable(
        self,
        key: str,
        namespace: str | None = None,
        default: str | None = None,
    ) -> str:
        """Resolve a variable by key and optional namespace."""
        candidates: list[str] = []
        if namespace:
            candidates.append(f"{namespace}_{key}")
        candidates.append(key)

        for candidate in candidates:
            if candidate in self._variables:
                return self._variables[candidate]

        for candidate in candidates:
            env_value = os.environ.get(candidate)
            if env_value is not None:
                return env_value

        if default is not None:
            return default

        raise VariableNotFoundError(key)

    def find_variables(
        self,
        obj: dict[str, Any] | list[Any] | str,
        namespace: str | None = None,
    ) -> list[str]:
        """Find all variable references in an object.

        Returns:
            Sorted list of unique variable names found.
        """
        found: set[str] = set()

        def visit(value: Any) -> None:
            if isinstance(value, str):
                if value.strip() == "$ref":
                    return
                for match in _VARIABLE_PATTERN.finditer(value):
                    key = match.group("braced") or match.group("bare")
                    if key:
                        found.add(f"{namespace}_{key}" if namespace else key)
                return

            if isinstance(value, dict):
                for nested in value.values():
                    visit(nested)
                return

            if isinstance(value, list):
                for nested in value:
                    visit(nested)

        visit(obj)
        return sorted(found)
