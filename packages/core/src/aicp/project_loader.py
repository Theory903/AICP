"""AICP Project Loader.

Loads the AICP project state (config, capabilities, policies) from the file system
and initializes the runtime components.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .capability import Capability
from .config import AicpProjectConfig, load_project_config
from .executor import AicpExecutor
from .implementations import InMemoryCapabilityRepository
from .implementations.execution import DefaultMockExecutionHandler, HttpCapabilityHandler
from .implementations.policy import ConfigPolicyEngine
from .interfaces.capability_provider import CapabilityProvider
from .interfaces.executor import Executor
from .interfaces.policy_engine import PolicyEngine


class LoadedProject(BaseModel):
    """Container for a fully loaded AICP project state."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    config: AicpProjectConfig
    repository: CapabilityProvider
    policy_engine: PolicyEngine
    executor: Executor
    capabilities: list[Capability]
    warnings: list[str] = Field(default_factory=list)


def _resolve_capability_dirs(root: Path, capabilities_dir: str) -> list[Path]:
    """Resolve capability directory paths following precedence rules.

    Order of precedence:
    1. canonical/ (high-level specifications)
    2. raw/ (raw discovery outputs)
    3. Flat root folder (fallback for simple setups)
    """
    base_dir = root / capabilities_dir
    canonical_dir = base_dir / "canonical"
    raw_dir = base_dir / "raw"

    resolved_dirs: list[Path] = []

    if canonical_dir.is_dir():
        resolved_dirs.append(canonical_dir)

    if raw_dir.is_dir():
        resolved_dirs.append(raw_dir)

    if not resolved_dirs and base_dir.is_dir():
        resolved_dirs.append(base_dir)

    return resolved_dirs


def _iter_capability_files(cap_dirs: Iterable[Path]) -> Iterable[Path]:
    """Iterate through capability definition files in stable order."""
    extensions = ("*.yaml", "*.yml")

    for cap_dir in cap_dirs:
        matched: list[Path] = []
        for extension in extensions:
            matched.extend(cap_dir.rglob(extension))

        for file_path in sorted(matched):
            if file_path.is_file():
                yield file_path


def _safe_relative_path(path: Path, root: Path) -> Path:
    """Return path relative to root when possible."""
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def _load_capability_file(yaml_file: Path) -> dict:
    """Load a raw capability YAML file."""
    with yaml_file.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        return {}

    if not isinstance(data, dict):
        raise ValueError("Root YAML value must be a mapping/object")

    return data


def load_project(project_root: str | Path | None = None) -> LoadedProject:
    """Load an AICP project with structured capability discovery.

    Resolution rules:
    - Files under canonical/ take precedence over raw/.
    - Files are loaded in deterministic order.
    - Duplicate capability names are ignored after the first load.
    """
    root = Path(project_root or os.getcwd()).resolve()
    config_path = root / "aicp.yaml"
    config = load_project_config(config_path)

    repo = InMemoryCapabilityRepository(name=config.provider_name)
    policy_engine = ConfigPolicyEngine(config)
    executor = AicpExecutor(
        capability_provider=repo,
        policy_engine=policy_engine,
        default_timeout_seconds=config.execution_timeout_seconds,
    )

    cap_dirs = _resolve_capability_dirs(root, config.capabilities_dir)
    mock_handler = DefaultMockExecutionHandler()
    loaded_caps: dict[str, Capability] = {}
    warnings: list[str] = []

    if not cap_dirs:
        warnings.append(f"No capability directory found under '{config.capabilities_dir}'.")

    for yaml_file in _iter_capability_files(cap_dirs):
        rel_path = _safe_relative_path(yaml_file, root)

        try:
            raw_data = _load_capability_file(yaml_file)
            if not raw_data:
                warnings.append(f"Skipping empty capability file: {rel_path}")
                continue

            capability = Capability.model_validate(raw_data)

            if capability.name in loaded_caps:
                previous = loaded_caps[capability.name]
                previous_source = getattr(previous, "_source_file", None)
                warnings.append(
                    "Duplicate capability name ignored: "
                    f"{capability.name} from {rel_path}"
                    + (f" (already loaded from {previous_source})" if previous_source else "")
                )
                continue

            # Keep source provenance attached for diagnostics only.
            source_capability = cast(Any, capability)
            source_capability._source_file = str(rel_path)

            if capability.provider is not None and not capability.provider.url and config.provider_url:
                capability.provider.url = config.provider_url

            handler = _handler_for_capability(capability, mock_handler, config)
            loaded_caps[capability.name] = capability
            repo.add_capability(capability, handler=handler)

        except Exception as exc:
            warnings.append(f"Skipping capability file {rel_path}: {exc}")

    if not loaded_caps:
        warnings.append(
            "No capabilities found in the project. Check your aicp.yaml 'capabilities_dir' and exported YAML files."
        )

    capabilities = sorted(loaded_caps.values(), key=lambda cap: cap.name)

    return LoadedProject(
        config=config,
        repository=repo,
        policy_engine=policy_engine,
        executor=executor,
        capabilities=capabilities,
        warnings=warnings,
    )


def _handler_for_capability(
    capability: Capability,
    mock_handler: DefaultMockExecutionHandler,
    config: AicpProjectConfig,
) -> Any:
    input_extra = getattr(capability.input_schema, "model_extra", {}) or {}
    if isinstance(input_extra, dict) and input_extra.get("x-aicp-http"):
        return HttpCapabilityHandler(
            capability,
            auth_config=config.auth,
            request_timeout_seconds=config.request_timeout_seconds,
            circuit_breaker_threshold=config.circuit_breaker_threshold,
            circuit_breaker_reset_seconds=config.circuit_breaker_reset_seconds,
        )
    return mock_handler
