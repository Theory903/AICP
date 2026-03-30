"""Variable substitution system for AICP.

Enables dynamic replacement of placeholders like ${VAR} or $VAR in configurations.
Supports environment variables, config variables, .env files, and custom loaders.
"""

import os
import re
from typing import Any
from pathlib import Path


def load_dotenv(env_file: str | Path = ".env", override: bool = False) -> dict[str, str]:
    """Load variables from a .env file into environment.
    
    Args:
        env_file: Path to .env file (default: ".env" in current directory)
        override: If True, override existing environment variables (default: False)
        
    Returns:
        Dictionary of loaded variables.
    """
    env_path = Path(env_file)
    if not env_path.exists():
        return {}
    
    loaded = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
            
        if "=" in line:
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            
            value = value.strip('"').strip("'")
            
            if override or key not in os.environ:
                os.environ[key] = value
            loaded[key] = value
            
    return loaded


class DotEnvLoader:
    """Variable loader that reads from .env files."""
    
    def __init__(self, env_file: str | Path = ".env", override: bool = False):
        self.env_file = Path(env_file)
        self.override = override
        self._loaded = False
        
    def load(self) -> dict[str, str]:
        """Load variables from .env file."""
        if not self._loaded:
            load_dotenv(self.env_file, self.override)
            self._loaded = True
        return dict(os.environ)
    
    def get(self, key: str, default: str | None = None) -> str | None:
        """Get a variable value."""
        return os.environ.get(key, default)


class VariableNotFoundError(Exception):
    """Raised when a required variable cannot be found."""

    def __init__(self, key: str):
        self.key = key
        super().__init__(f"Variable not found: {key}")


class VariableSubstitutor:
    """Variable substitution with hierarchical resolution.

    Resolves variables in order:
    1. Config variables (exact match)
    2. Custom variable loaders
    3. Environment variables

    Supports ${VAR} and $VAR syntax.
    """

    def __init__(self, variables: dict[str, str] | None = None):
        self._variables = variables or {}

    def substitute(
        self,
        obj: dict | list | str,
        namespace: str | None = None,
    ) -> Any:
        """Recursively substitute variables in nested data structures.

        Args:
            obj: Object to perform substitution on.
            namespace: Optional namespace for variable prefixing.

        Returns:
            Object with all variables replaced.

        Raises:
            VariableNotFoundError: If a variable cannot be resolved.
        """
        if isinstance(obj, str):
            return self._substitute_string(obj, namespace)
        elif isinstance(obj, dict):
            return {k: self.substitute(v, namespace) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.substitute(elem, namespace) for elem in obj]
        return obj

    def _substitute_string(self, s: str, namespace: str | None) -> str:
        if "$ref" in s and re.search(r"\$ref(?![a-zA-Z0-9_])", s):
            return s

        def replacer(match):
            var_name = match.group(1) or match.group(2)
            return self._get_variable(var_name, namespace)

        return re.sub(r"\$\{([a-zA-Z0-9_]+)\}|\$([a-zA-Z0-9_]+)", replacer, s)

    def _get_variable(self, key: str, namespace: str | None) -> str:
        full_key = f"{namespace}_{key}" if namespace else key

        if full_key in self._variables:
            return self._variables[full_key]

        if key in self._variables:
            return self._variables[key]

        env_val = os.environ.get(key) or os.environ.get(full_key)
        if env_val:
            return env_val

        raise VariableNotFoundError(key)

    def find_variables(self, obj: dict | list | str, namespace: str | None = None) -> list[str]:
        """Find all variable references in an object.

        Returns:
            List of unique variable names found.
        """
        if isinstance(obj, str):
            if "$ref" in obj and re.search(r"\$ref(?![a-zA-Z0-9_])", obj):
                return []

            matches = re.findall(r"\$\{([a-zA-Z0-9_]+)\}|\$([a-zA-Z0-9_]+)", obj)
            vars_found = []
            for match in matches:
                var = match[0] or match[1]
                full_var = f"{namespace}_{var}" if namespace else var
                vars_found.append(full_var)
            return list(set(vars_found))

        elif isinstance(obj, dict):
            result = []
            for v in obj.values():
                result.extend(self.find_variables(v, namespace))
            return result

        elif isinstance(obj, list):
            result = []
            for elem in obj:
                result.extend(self.find_variables(elem, namespace))
            return result

        return []
