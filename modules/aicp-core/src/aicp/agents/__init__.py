"""AICP Agents - Internal subagents for repository integration and capability extraction."""

from aicp.agents.auto_integrate import (
    AicpAutoIntegrator,
    AutoProviderDetector,
    IntegrationResult,
    ProviderConfig,
    ProviderType,
    auto_integrate,
)
from aicp.agents.repo_integration import (
    AgentCapability,
    AgentSpec,
    RepoAnalysis,
    RepoIntegrationAgent,
    create_agent_md,
    extract_python_capabilities,
    extract_typescript_capabilities,
    integrate_github_repo,
)

__all__ = [
    "RepoIntegrationAgent",
    "RepoAnalysis",
    "AgentSpec",
    "AgentCapability",
    "extract_python_capabilities",
    "extract_typescript_capabilities",
    "create_agent_md",
    "integrate_github_repo",
    "AicpAutoIntegrator",
    "AutoProviderDetector",
    "IntegrationResult",
    "ProviderConfig",
    "ProviderType",
    "auto_integrate",
]
