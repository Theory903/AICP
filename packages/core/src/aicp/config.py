"""AICP Project Configuration.

Loads and validates aicp.yaml — the single project config file
that drives init, scan, dev, doctor, runtime, and governance behavior.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

PolicyEffectName = Literal["allow", "deny", "ask", "require_approval", "limit"]
StoreBackendName = Literal["memory", "file", "sqlite"]
AuthTypeName = Literal["bearer", "api_key", "basic", "oauth2_client_credentials"]


class ConfigError(ValueError):
    """Raised when project configuration is invalid."""


class ProjectDefaults(BaseModel):
    """Default policy effects by capability kind.

    These are applied when no explicit rule matches a capability.
    """

    queries: PolicyEffectName = "allow"
    actions: PolicyEffectName = "ask"
    destructive: PolicyEffectName = "require_approval"

    def effect_for_kind(self, kind: str, is_destructive: bool = False) -> PolicyEffectName:
        """Get the default policy effect for a capability kind."""
        if is_destructive:
            return self.destructive
        if kind == "query":
            return self.queries
        return self.actions


class PolicyRule(BaseModel):
    """A declarative policy rule in aicp.yaml.

    Example:
        - match: notes.delete
          effect: require_approval
        - match: notes.*
          effect: allow
        - match: auth.login
          effect: limit
          rpm: 60
    """

    match: str
    effect: PolicyEffectName
    rpm: int | None = None
    reason: str | None = None

    @field_validator("match")
    @classmethod
    def validate_match(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("match cannot be empty")
        return value

    @field_validator("rpm")
    @classmethod
    def validate_rpm(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("rpm must be > 0")
        return value

    @model_validator(mode="after")
    def validate_limit_rule(self) -> PolicyRule:
        if self.effect == "limit" and self.rpm is None:
            raise ValueError("rpm is required when effect='limit'")
        if self.effect != "limit" and self.rpm is not None:
            raise ValueError("rpm is only allowed when effect='limit'")
        return self


class RuntimeConfig(BaseModel):
    """Runtime configuration section."""

    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True
    store_backend: StoreBackendName = "memory"
    store_path: str | None = None

    @field_validator("host")
    @classmethod
    def validate_host(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("host cannot be empty")
        return value

    @field_validator("port")
    @classmethod
    def validate_port(cls, value: int) -> int:
        if not (1 <= value <= 65535):
            raise ValueError("port must be between 1 and 65535")
        return value

    @model_validator(mode="after")
    def validate_store_path(self) -> RuntimeConfig:
        if self.store_backend in {"file", "sqlite"} and not self.store_path:
            raise ValueError(f"store_path is required when store_backend='{self.store_backend}'")
        return self


class AuthConfig(BaseModel):
    """Authentication configuration for HTTP-backed capabilities."""

    type: AuthTypeName
    token: str | None = None
    api_key: str | None = None
    header_name: str | None = None
    location: Literal["header", "query"] = "header"
    username: str | None = None
    password: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    token_url: str | None = None
    scopes: list[str] = Field(default_factory=list)
    audience: str | None = None

    @field_validator(
        "token",
        "api_key",
        "header_name",
        "username",
        "password",
        "client_id",
        "client_secret",
        "token_url",
        "audience",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_required_fields(self) -> AuthConfig:
        if self.type == "bearer" and not self.token:
            raise ValueError("token is required when auth.type='bearer'")

        if self.type == "api_key":
            if not self.api_key:
                raise ValueError("api_key is required when auth.type='api_key'")
            if not self.header_name:
                raise ValueError("header_name is required when auth.type='api_key'")

        if self.type == "basic":
            if not self.username:
                raise ValueError("username is required when auth.type='basic'")
            if self.password is None:
                raise ValueError("password is required when auth.type='basic'")

        if self.type == "oauth2_client_credentials":
            missing: list[str] = []
            if not self.client_id:
                missing.append("client_id")
            if not self.client_secret:
                missing.append("client_secret")
            if not self.token_url:
                missing.append("token_url")
            if missing:
                joined = ", ".join(missing)
                raise ValueError(f"Missing required auth fields for oauth2_client_credentials: {joined}")

        return self


class AicpProjectConfig(BaseModel):
    """Root configuration loaded from aicp.yaml.

    This is the single source of truth for an AICP-enabled project.
    Everything else (CLI, runtime, adapter) reads from this.
    """

    # App detection
    app: str | None = None
    openapi: str | None = None

    # Default policy behavior
    defaults: ProjectDefaults = Field(default_factory=ProjectDefaults)

    # Explicit policy rules
    rules: list[PolicyRule] = Field(default_factory=list)

    # Directory conventions
    capabilities_dir: str = "aicp/capabilities"
    policies_dir: str = "aicp/policies"
    workflows_dir: str = "aicp/workflows"
    fixtures_dir: str = "aicp/fixtures"

    # Runtime settings
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)

    # Provider metadata
    provider_name: str = "aicp"
    provider_url: str | None = None
    version: str = "0.3.0"
    auth: AuthConfig | None = None
    request_timeout_seconds: float = 30.0
    execution_timeout_seconds: float = 35.0
    circuit_breaker_threshold: int = 3
    circuit_breaker_reset_seconds: float = 30.0

    @field_validator(
        "capabilities_dir",
        "policies_dir",
        "workflows_dir",
        "fixtures_dir",
        "provider_name",
        "version",
    )
    @classmethod
    def validate_non_empty_strings(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be empty")
        return value

    @field_validator("provider_url")
    @classmethod
    def validate_provider_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        return value

    @field_validator(
        "request_timeout_seconds",
        "execution_timeout_seconds",
        "circuit_breaker_reset_seconds",
    )
    @classmethod
    def validate_positive_float(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("value must be greater than 0")
        return value

    @field_validator("circuit_breaker_threshold")
    @classmethod
    def validate_circuit_breaker_threshold(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("circuit_breaker_threshold must be greater than 0")
        return value

    @model_validator(mode="after")
    def validate_sources(self) -> AicpProjectConfig:
        if self.app and self.openapi:
            raise ValueError("only one of 'app' or 'openapi' may be set")
        return self

    def find_rule(self, capability_name: str) -> PolicyRule | None:
        """Find the first matching rule for a capability name.

        Supports exact match and glob patterns:
        - notes.delete matches exactly
        - notes.* matches any capability in the notes namespace
        - *.list matches any .list capability
        """
        import fnmatch

        for rule in self.rules:
            if fnmatch.fnmatch(capability_name, rule.match):
                return rule
        return None

    def effective_effect(
        self,
        capability_name: str,
        kind: str,
        is_destructive: bool = False,
    ) -> PolicyEffectName:
        """Get the effective policy effect for a capability.

        First checks explicit rules, then falls back to defaults.
        """
        rule = self.find_rule(capability_name)
        if rule is not None:
            return rule.effect
        return self.defaults.effect_for_kind(kind, is_destructive)

    def effective_rpm(self, capability_name: str) -> int | None:
        """Get rate limit for a capability if a matching limit rule exists."""
        rule = self.find_rule(capability_name)
        if rule and rule.effect == "limit":
            return rule.rpm
        return None

    def resolve_dir(self, root: str | Path, attr_name: str) -> Path:
        """Resolve a configured directory against a project root."""
        value = getattr(self, attr_name)
        return Path(root) / value


def load_project_config(path: str | Path | None = None) -> AicpProjectConfig:
    """Load project config from disk.

    Search order:
    1. Explicit path if provided
    2. aicp.yaml in current directory
    3. .aicp.yaml in current directory
    4. aicp.yml in current directory
    5. .aicp.yml in current directory
    """
    if path is not None:
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        return _parse_config(config_path)

    found = find_config_file(".")
    if found is not None:
        return _parse_config(found)

    return AicpProjectConfig()


def _parse_config(path: Path) -> AicpProjectConfig:
    """Parse a YAML config file into AicpProjectConfig."""
    try:
        import yaml
    except ImportError as exc:
        raise ImportError("PyYAML is required for config loading. Install with: pip install pyyaml") from exc

    try:
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except OSError as exc:
        raise ConfigError(f"Failed to read config file '{path}': {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in config file '{path}': {exc}") from exc

    if raw is None:
        return AicpProjectConfig()

    if not isinstance(raw, dict):
        raise ConfigError(f"Config file '{path}' must contain a YAML mapping/object")

    try:
        return AicpProjectConfig.model_validate(raw)
    except Exception as exc:
        raise ConfigError(f"Invalid config in '{path}': {exc}") from exc


def find_config_file(base_path: str | Path = ".") -> Path | None:
    """Find an AICP config file starting from base_path."""
    base = Path(base_path)
    candidates = [
        base / "aicp.yaml",
        base / ".aicp.yaml",
        base / "aicp.yml",
        base / ".aicp.yml",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def save_project_config(
    config: AicpProjectConfig,
    path: str | Path = "aicp.yaml",
) -> Path:
    """Save project config to a YAML file."""
    try:
        import yaml
    except ImportError as exc:
        raise ImportError("PyYAML is required for config saving. Install with: pip install pyyaml") from exc

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = config.model_dump(exclude_none=True)

    # Keep file clean. Humans already do enough damage without noisy config.
    if not data.get("rules"):
        data.pop("rules", None)

    try:
        with output_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(
                data,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
    except OSError as exc:
        raise ConfigError(f"Failed to save config to '{output_path}': {exc}") from exc

    return output_path
