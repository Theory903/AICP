"""AICP Core - Protocol domain models and validation.

AICP (AI Capability Protocol) is a standard for capability-aware,
workflow-aware, and policy-aware AI execution.

Main exports:
- Capability models and kinds
- Policy engine interfaces and implementations
- Registry for managing capabilities and policies
- Executor for running capabilities with policy enforcement
- Adapters for HTTP, MCP, and other protocols
"""

__version__ = "0.1.0"

# Project config
from aicp.config import (
    AicpProjectConfig,
    PolicyRule,
    ProjectDefaults,
    RuntimeConfig,
    find_config_file,
    load_project_config,
    save_project_config,
)

# Risk inference
from aicp.risk import (
    RiskLevel,
    infer_risk,
    is_destructive,
    risk_to_default_effect,
)

# Capability export
from aicp.export import (
    capability_to_dict,
    export_all_capabilities,
    export_capability_yaml,
)

# Capability models
# Adapters
try:
    from aicp.adapters import HttpExecutionAdapter, McpAdapter
except ImportError:
    HttpExecutionAdapter = None
    McpAdapter = None

# API
from aicp.api import (
    APIVersion,
    DependencyHealthCheck,
    GracefulShutdown,
    HealthCheckBase,
    HealthCheckRouter,
    LivenessHealthCheck,
    ReadinessHealthCheck,
    VersionConfig,
)

# Approval (HITL)
from aicp.approval import (
    ApprovalContext,
    ApprovalDecision,
    ApprovalRequest,
    ApprovalRisk,
    ApprovalStatus,
    calculate_risk,
)
from aicp.approval_service import (
    ApprovalService,
    ApprovalStore,
    InMemoryApprovalStore,
)

# Authentication
from aicp.auth import (
    ApiKeyAuth,
    Auth,
    BasicAuth,
    BearerAuth,
    OAuth2Auth,
    OAuth2WithRefresh,
)

# Cache
from aicp.cache import (
    CacheDecorator,
    RateLimiterRedis,
    RedisCache,
)
from aicp.capability import (
    Capability,
    CapabilityKind,
    ContinuationSpec,
    InputSchema,
    OutputSchema,
    PolicyRef,
    ProviderInfo,
    RenderSpec,
)

# Error classes
from aicp.errors import (
    AicpError,
    DiscoveryError,
    ExecutionError,
    PolicyError,
    ValidationError,
)

# Core components
from aicp.executor import AicpExecutor

# Implementations
from aicp.implementations import InMemoryCapabilityRepository
from aicp.implementations.policy import DefaultPolicyEngine
from aicp.implementations.workflow import DefaultWorkflowRuntime

# Interfaces
from aicp.interfaces import (
    CapabilityProvider,
    DiscoveredCapability,
    DiscoverySource,
    ExecutionResult,
    ExecutionStatus,
    Executor,
    Policy,
    PolicyCondition,
    PolicyDecision,
    PolicyEffect,
    PolicyEngine,
    PolicySubject,
    Renderer,
    RenderHints,
    StepResult,
    WorkflowRuntime,
    WorkflowState,
    WorkflowStatus,
)

# Notifications
from aicp.notifications import (
    EmailChannel,
    Notification,
    NotificationChannel,
    NotificationService,
    SlackChannel,
    WebhookChannel,
)

# Observability
from aicp.observability import (
    HealthCheck,
    MetricsCollector,
    StructuredLogger,
    Tracer,
    get_logger,
    get_metrics,
    get_tracer,
)

# Plugin system
from aicp.plugins import (
    AuthProviderPlugin,
    CapabilitySourcePlugin,
    Plugin,
    PluginMetadata,
    PluginRegistry,
    TransportPlugin,
    get_plugin_registry,
    register_auth_provider,
    register_capability_source,
    register_transport,
)
from aicp.registry import AicpRegistry, TagSearchStrategy

# Reliability
from aicp.reliability import (
    BackoffStrategy,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerManager,
    CircuitBreakerOpenError,
    RetryConfig,
    RetryExhaustedError,
    retry_async,
    retry_sync,
)

# Secrets & Cloud
from aicp.secrets import (
    AWSSecretsManagerStore,
    CloudAuditStorage,
    EnvSecretStore,
    HashiCorpVaultStore,
    SecretManager,
    SecretStore,
)

# Security
from aicp.security import (
    ApiKeyRotator,
    AuditSigner,
    RateLimiter,
    RateLimitError,
    SecureAuditLog,
)

# Multi-tenancy
from aicp.tenancy import (
    Tenant,
    TenantContext,
    TenantIsolation,
    TenantManager,
    TenantQuota,
)
from aicp.validator import AicpValidator
from aicp.validator import ValidationError as SchemaValidationError

# Variable handling
from aicp.variables import (
    DotEnvLoader,
    VariableNotFoundError,
    VariableSubstitutor,
    load_dotenv,
)

__all__ = [
    # Version
    "__version__",
    # Project config
    "AicpProjectConfig",
    "PolicyRule",
    "ProjectDefaults",
    "RuntimeConfig",
    "find_config_file",
    "load_project_config",
    "save_project_config",
    # Risk inference
    "RiskLevel",
    "infer_risk",
    "is_destructive",
    "risk_to_default_effect",
    # Capability export
    "capability_to_dict",
    "export_all_capabilities",
    "export_capability_yaml",
    # Capability models
    "Capability",
    "CapabilityKind",
    "ContinuationSpec",
    "InputSchema",
    "OutputSchema",
    "PolicyRef",
    "ProviderInfo",
    "RenderSpec",
    # Error classes
    "AicpError",
    "DiscoveryError",
    "ExecutionError",
    "PolicyError",
    "ValidationError",
    "SchemaValidationError",
    # Interfaces
    "CapabilityProvider",
    "DiscoverySource",
    "DiscoveredCapability",
    "Executor",
    "ExecutionResult",
    "ExecutionStatus",
    "Policy",
    "PolicyDecision",
    "PolicyEngine",
    "PolicyEffect",
    "PolicySubject",
    "PolicyCondition",
    # Approval (HITL)
    "ApprovalContext",
    "ApprovalDecision",
    "ApprovalRequest",
    "ApprovalRisk",
    "ApprovalService",
    "ApprovalStatus",
    "ApprovalStore",
    "InMemoryApprovalStore",
    "calculate_risk",
    "Renderer",
    "RenderHints",
    "StepResult",
    "WorkflowRuntime",
    "WorkflowState",
    "WorkflowStatus",
    # Implementations
    "InMemoryCapabilityRepository",
    "DefaultPolicyEngine",
    "DefaultWorkflowRuntime",
    # Core components
    "AicpRegistry",
    "TagSearchStrategy",
    "AicpValidator",
    "AicpExecutor",
    # Adapters
    "HttpExecutionAdapter",
    "McpAdapter",
    # Authentication
    "Auth",
    "ApiKeyAuth",
    "BasicAuth",
    "BearerAuth",
    "OAuth2Auth",
    "OAuth2WithRefresh",
    # Variables
    "VariableNotFoundError",
    "VariableSubstitutor",
    "load_dotenv",
    "DotEnvLoader",
    # Security
    "RateLimitError",
    "RateLimiter",
    "ApiKeyRotator",
    "AuditSigner",
    "SecureAuditLog",
    # Plugin system
    "Plugin",
    "PluginMetadata",
    "TransportPlugin",
    "AuthProviderPlugin",
    "CapabilitySourcePlugin",
    "PluginRegistry",
    "get_plugin_registry",
    "register_transport",
    "register_auth_provider",
    "register_capability_source",
    # Multi-tenancy
    "Tenant",
    "TenantQuota",
    "TenantContext",
    "TenantManager",
    "TenantIsolation",
    # Reliability
    "RetryConfig",
    "RetryExhaustedError",
    "retry_async",
    "retry_sync",
    "BackoffStrategy",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerOpenError",
    "CircuitBreakerManager",
    # Observability
    "StructuredLogger",
    "get_logger",
    "MetricsCollector",
    "get_metrics",
    "Tracer",
    "get_tracer",
    "HealthCheck",
    # Notifications
    "Notification",
    "NotificationChannel",
    "WebhookChannel",
    "SlackChannel",
    "EmailChannel",
    "NotificationService",
    # Secrets & Cloud
    "SecretStore",
    "EnvSecretStore",
    "HashiCorpVaultStore",
    "AWSSecretsManagerStore",
    "SecretManager",
    "CloudAuditStorage",
    # Cache
    "RedisCache",
    "CacheDecorator",
    "RateLimiterRedis",
    # API
    "APIVersion",
    "VersionConfig",
    "VersionManager",
    "HealthCheckBase",
    "LivenessHealthCheck",
    "ReadinessHealthCheck",
    "DependencyHealthCheck",
    "HealthCheckRouter",
    "GracefulShutdown",
    "lifespan_context",
]
