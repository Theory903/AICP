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

# Capability models
# Adapters
try:
    from aicp.adapters import HttpExecutionAdapter, McpAdapter
except ImportError:
    HttpExecutionAdapter = None
    McpAdapter = None

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
from aicp.registry import AicpRegistry, TagSearchStrategy
from aicp.validator import AicpValidator
from aicp.validator import ValidationError as SchemaValidationError

# Authentication
from aicp.auth import (
    Auth,
    ApiKeyAuth,
    BasicAuth,
    BearerAuth,
    OAuth2Auth,
    OAuth2WithRefresh,
)

# Variable handling
from aicp.variables import (
    VariableNotFoundError,
    VariableSubstitutor,
    load_dotenv,
    DotEnvLoader,
)

# Security
from aicp.security import (
    RateLimitExceeded,
    RateLimiter,
    ApiKeyRotator,
    AuditSigner,
    SecureAuditLog,
)

# Plugin system
from aicp.plugins import (
    Plugin,
    PluginMetadata,
    TransportPlugin,
    AuthProviderPlugin,
    CapabilitySourcePlugin,
    PluginRegistry,
    get_plugin_registry,
    register_transport,
    register_auth_provider,
    register_capability_source,
)

# Multi-tenancy
from aicp.tenancy import (
    Tenant,
    TenantQuota,
    TenantContext,
    TenantManager,
    TenantIsolation,
)

# Reliability
from aicp.reliability import (
    RetryConfig,
    RetryExhausted,
    retry_async,
    retry_sync,
    BackoffStrategy,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpen,
    CircuitBreakerManager,
)

# Observability
from aicp.observability import (
    StructuredLogger,
    get_logger,
    MetricsCollector,
    get_metrics,
    Tracer,
    get_tracer,
    HealthCheck,
)

# Notifications
from aicp.notifications import (
    Notification,
    NotificationChannel,
    WebhookChannel,
    SlackChannel,
    EmailChannel,
    NotificationService,
)

# Secrets & Cloud
from aicp.secrets import (
    SecretStore,
    EnvSecretStore,
    HashiCorpVaultStore,
    AWSSecretsManagerStore,
    SecretManager,
    CloudAuditStorage,
)

# Cache
from aicp.cache import (
    RedisCache,
    CacheDecorator,
    RateLimiterRedis,
)

# API
from aicp.api import (
    APIVersion,
    VersionConfig,
    VersionManager,
    HealthCheckBase,
    LivenessHealthCheck,
    ReadinessHealthCheck,
    DependencyHealthCheck,
    HealthCheckRouter,
    GracefulShutdown,
    lifespan_context,
)

__all__ = [
    # Version
    "__version__",
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
    "RateLimitExceeded",
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
    "RetryExhausted",
    "retry_async",
    "retry_sync",
    "BackoffStrategy",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerOpen",
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
