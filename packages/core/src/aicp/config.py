"""AICP Project Configuration.

Loads and validates aicp.yaml — the single project config file
that drives init, scan, dev, and doctor commands.
"""

from pathlib import Path

from pydantic import BaseModel, Field


class ProjectDefaults(BaseModel):
    """Default policy effects by capability kind.

    These are applied when no explicit rule matches a capability.
    """

    queries: str = "allow"  # allow | ask | deny
    actions: str = "ask"  # allow | ask | deny
    destructive: str = "require_approval"  # allow | ask | deny | require_approval

    def effect_for_kind(self, kind: str, is_destructive: bool = False) -> str:
        """Get the default policy effect for a capability kind."""
        if is_destructive:
            return self.destructive
        if kind in ("query",):
            return self.queries
        return self.actions


class PolicyRule(BaseModel):
    """A declarative policy rule in aicp.yaml.

    Example:
        - match: notes.delete
          effect: require_approval
        - match: "*.list"
          effect: allow
        - match: search.web
          effect: limit
          rpm: 60
    """

    match: str  # capability name or glob pattern
    effect: str  # allow | deny | ask | require_approval | limit
    rpm: int | None = None  # for limit effect
    reason: str | None = None  # human-readable reason


class RuntimeConfig(BaseModel):
    """Runtime configuration section."""

    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True
    store_backend: str = "memory"  # memory | file | sqlite
    store_path: str | None = None


class AicpProjectConfig(BaseModel):
    """Root configuration loaded from aicp.yaml.

    This is the single source of truth for an AICP-enabled project.
    Everything else (CLI, runtime, adapter) reads from this.
    """

    # App detection
    app: str | None = None  # "fastapi:app.main:app"
    openapi: str | None = None  # "./openapi.yaml"

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
    version: str = "0.1.0"

    def find_rule(self, capability_name: str) -> PolicyRule | None:
        """Find the first matching rule for a capability name.

        Supports exact match and glob patterns:
        - "notes.delete" matches exactly
        - "notes.*" matches any capability in the notes namespace
        - "*.list" matches any .list capability
        """
        import fnmatch

        for rule in self.rules:
            if fnmatch.fnmatch(capability_name, rule.match):
                return rule
        return None

    def effective_effect(
        self, capability_name: str, kind: str, is_destructive: bool = False
    ) -> str:
        """Get the effective policy effect for a capability.

        First checks explicit rules, then falls back to defaults.
        """
        rule = self.find_rule(capability_name)
        if rule:
            return rule.effect
        return self.defaults.effect_for_kind(kind, is_destructive)


# --- Loader functions ---


def load_project_config(path: str | Path | None = None) -> AicpProjectConfig:
    """Load project config from aicp.yaml.

    Searches for config in this order:
    1. Explicit path if provided
    2. aicp.yaml in current directory
    3. .aicp.yaml in current directory
    4. aicp.yml in current directory

    Returns default config if no file found.
    """
    if path:
        config_path = Path(path)
        if config_path.exists():
            return _parse_config(config_path)
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Search in current directory
    candidates = [
        Path("aicp.yaml"),
        Path(".aicp.yaml"),
        Path("aicp.yml"),
        Path(".aicp.yml"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return _parse_config(candidate)

    return AicpProjectConfig()


def _parse_config(path: Path) -> AicpProjectConfig:
    """Parse a config file into AicpProjectConfig."""
    try:
        import yaml
    except ImportError:
        raise ImportError(
            "PyYAML is required for config loading. Install with: pip install pyyaml"
        )

    with open(path) as f:
        raw = yaml.safe_load(f)

    if not raw:
        return AicpProjectConfig()

    return AicpProjectConfig.model_validate(raw)


def find_config_file(base_path: str | Path = ".") -> Path | None:
    """Find an aicp.yaml config file starting from base_path."""
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
    config: AicpProjectConfig, path: str | Path = "aicp.yaml"
) -> Path:
    """Save project config to a YAML file."""
    try:
        import yaml
    except ImportError:
        raise ImportError(
            "PyYAML is required for config saving. Install with: pip install pyyaml"
        )

    output_path = Path(path)
    data = config.model_dump(exclude_none=True, exclude_defaults=True)

    # Clean up empty collections
    if not data.get("rules"):
        data.pop("rules", None)

    with open(output_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    return output_path
