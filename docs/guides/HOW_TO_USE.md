# AICP Complete Usage Guide

This guide covers all features of the AICP (AI Capability Protocol) platform.

---

## Table of Contents

### Part 1: The CLI Workflow
1. [The Fast Path: Bootstrapping](#the-fast-path-bootstrapping)
2. [CLI Full Reference](CLI_REFERENCE.md)

### Part 2: Advanced Programmatic Engine
3. [Core Programmatic Usage](#core-programmatic-usage)
4. [Authentication](#authentication)
5. [Variable Substitution](#variable-substitution)
6. [Capability Registry & Search](#capability-registry--search)
7. [Execution & Streaming](#execution--streaming)
8. [Plugin System](#plugin-system)
9. [Security Features](#security-features)
10. [Multi-Tenancy](#multi-tenancy)
11. [Reliability Patterns](#reliability-patterns)
12. [Observability](#observability)
13. [Notifications](#notifications)
14. [Secrets Management](#secrets-management)
15. [Caching](#caching)
16. [Production API Features](#production-api-features)
17. [Transport Adapters](#transport-adapters)

---

## The Fast Path: Bootstrapping

If you are trying to expose an existing FastAPI or Node application to AI agents safely, **you usually don't need to write any Python code.**

AICP acts as a configuration-first governance layer. Using the CLI, you simply scan your app, preview your actions, modify your risk profiles, and start the engine in front of it!

> **→ Complete Guide:** Please refer to the [**CLI Reference Guide**](CLI_REFERENCE.md) to master `aicp bootstrap`, `aicp preview`, and `aicp protect`. 

---

## Core Programmatic Usage

While the CLI manages standard execution, developers building complex, distributed AI systems or customized protocol adapters can interact with the raw Python `aicp-core` SDK.

Below is the traditional way to programmatically assemble an Executor without using the CLI configurations.

```python
from aicp import (
    Capability, 
    CapabilityKind, 
    AicpExecutor,
    InMemoryCapabilityRepository,
)

# 1. Provide capability mappings manually in memory without Yaml
capability = Capability(
    name="payments.transfer",
    description="Transfer money between accounts",
    kind=CapabilityKind.ACTION,
    input_schema={"type": "object", "properties": {"amount": {"type": "number"}}},
    output_schema={"type": "object"},
)

# 2. Register it
repo = InMemoryCapabilityRepository()
repo.register(capability)

# 3. Execute payload
executor = AicpExecutor(repo)
result = await executor.execute("payments.transfer", {"amount": 100})
print(result.status)  # "success"
```

---

## Authentication

AICP supports multiple authentication methods:

### API Key
```python
from aicp import ApiKeyAuth

auth = ApiKeyAuth(
    api_key="sk-xxx",
    header_name="X-API-Key",
    location="header",  # or "query"
)
auth.apply(headers={}, params={})
```

### Basic Auth
```python
from aicp import BasicAuth

auth = BasicAuth(username="user", password="pass")
auth.apply(headers={}, params={})
```

### Bearer Token
```python
from aicp import BearerAuth

auth = BearerAuth(token="eyJhbGciOiJIUzI1NiIs...")
auth.apply(headers={}, params={})
```

### OAuth2 (Client Credentials)
```python
from aicp import OAuth2Auth

auth = OAuth2Auth(
    client_id="my-client-id",
    client_secret="my-secret",
    token_url="https://auth.example.com/oauth/token",
    scopes=["read", "write"],
)

# Fetch token
token = await auth.fetch_token()
```

---

## Variable Substitution

### Load from .env file
```python
from aicp import load_dotenv, DotEnvLoader

# Simple usage
load_dotenv(".env")

# With loader
loader = DotEnvLoader(".env", override=False)
vars = loader.load()
```

### Variable Substitution in Configs
```python
from aicp import VariableSubstitutor

sub = VariableSubstitutor({"api_url": "https://api.example.com"})

config = {
    "endpoint": "${api_url}/v1",
    "timeout": 30,
}

result = sub.substitute(config)
# Result: {"endpoint": "https://api.example.com/v1", "timeout": 30}
```

---

## Capability Registry & Search

### Register Capabilities
```python
from aicp import AicpRegistry, Capability, CapabilityKind

registry = AicpRegistry()
registry.register_capability(Capability(
    name="users.list",
    description="List all users",
    kind=CapabilityKind.QUERY,
    tags=["admin", "users"],
))
```

### Search by Tags
```python
# Search with query and tags
results = registry.search_capabilities(
    query="user management",
    tags=["admin"],
    limit=10,
)
```

---

## Execution & Streaming

### Basic Execution
```python
from aicp import AicpExecutor

executor = AicpExecutor(capability_provider, policy_engine)
result = await executor.execute("tool.name", {"arg": "value"})
```

### Streaming Execution
```python
async for chunk in executor.execute_streaming("tool.name", {"arg": "value"}):
    print(chunk)
    # {"type": "start", "capability": "..."}
    # {"type": "result", "status": "success", "data": ...}
    # {"type": "end"}
```

---

## Plugin System

### Register Transport Plugin
```python
from aicp import register_transport, PluginMetadata

@register_transport("custom")
class CustomTransport(TransportPlugin):
    @property
    def metadata(self):
        return PluginMetadata(name="custom", version="1.0.0")
    
    async def send(self, request):
        # Your implementation
        pass
```

### Use Plugin Registry
```python
from aicp import get_plugin_registry

registry = get_plugin_registry()
transports = registry.list_transports()
```

---

## Security Features

### Rate Limiting
```python
from aicp import RateLimiter, RateLimitExceeded

limiter = RateLimiter(requests_per_window=60, window_seconds=60)

try:
    limiter.check("user-123")
except RateLimitExceeded:
    print("Too many requests!")
```

### API Key Rotation
```python
from aicp import ApiKeyRotator

rotator = ApiKeyRotator()
key_id = rotator.create_key("sk-xxx", expires_in_seconds=3600)

# Verify
tenant_id = rotator.verify_key("sk-xxx")

# Rotate
rotator.rotate_key()
```

### Audit Signing
```python
from aicp import SecureAuditLog

log = SecureAuditLog("your-secret-key")
entry = log.append({"event": "execution", "tool": "test"})

# Verify integrity
valid, invalid = log.verify()
```

---

## Multi-Tenancy

### Create Tenant
```python
from aicp import TenantManager

manager = TenantManager()
tenant = manager.create_tenant(
    name="Acme Corp",
    config={"max_workflows": 100},
)

# Create API key
api_key, key_id = manager.create_api_key(tenant.id)
```

### Tenant Context
```python
from aicp import TenantContext

with TenantContext(tenant_id="abc123"):
    # All operations in this context are tenant-isolated
    result = await executor.execute("tool", {})
```

### Quotas
```python
from aicp import TenantQuota

quota = TenantQuota(
    tenant_id="abc123",
    max_api_calls_per_minute=60,
    max_concurrent_requests=10,
)
manager.update_quota("abc123", quota)
```

---

## Reliability Patterns

### Retry with Backoff
```python
from aicp import retry_async, RetryConfig, BackoffStrategy

config = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    strategy=BackoffStrategy.EXPONENTIAL,
    jitter=True,
)

result = await retry_async(
    my_function,
    config=config,
)
```

### Circuit Breaker
```python
from aicp import CircuitBreaker, CircuitBreakerConfig

cb = CircuitBreaker("external-api", CircuitBreakerConfig(
    failure_threshold=5,
    timeout=30.0,
))

try:
    result = await cb.call(my_function)
except CircuitBreakerOpen:
    print("Service unavailable!")
```

---

## Observability

### Structured Logging
```python
from aicp import get_logger

logger = get_logger("my-service")
logger.info("Processing request", request_id="123", user="john")
# Output: {"timestamp": "...", "level": "info", "message": "Processing request", "request_id": "123", ...}
```

### Metrics
```python
from aicp import get_metrics

metrics = get_metrics()
metrics.increment_counter("requests_total", labels={"endpoint": "/api"})
metrics.record_histogram("request_duration_ms", 150.0)
print(metrics.to_prometheus())
```

### Tracing
```python
from aicp import get_tracer

tracer = get_tracer("my-service")

with tracer.start_span("execute-tool") as span:
    span.set_attribute("tool", "payments.transfer")
    result = await executor.execute("payments.transfer", {})
```

### Health Checks
```python
from aicp import HealthCheckRouter, DependencyHealthCheck

router = HealthCheckRouter()
router.add_check(DependencyHealthCheck("redis", check_redis_connection))

app.include_router(router.create_router())
# Endpoints: /health, /health/live, /health/ready
```

---

## Notifications

### Webhook
```python
from aicp import WebhookChannel, NotificationService

webhook = WebhookChannel(
    url="https://example.com/webhook",
    secret="my-secret",
)

service = NotificationService()
service.add_channel("webhook", webhook)
service.subscribe("approval_required", "webhook")

# Send notification
await service.notify(
    event_type="approval_required",
    title="Approval Needed",
    message="Please approve this request",
    data={"request_id": "123"},
)
```

### Slack
```python
from aicp import SlackChannel

slack = SlackChannel(
    webhook_url="https://hooks.slack.com/...",
    channel="#alerts",
)

service.add_channel("slack", slack)
service.subscribe("approval_required", "slack")
```

---

## Secrets Management

### Environment Variables
```python
from aicp import EnvSecretStore

store = EnvSecretStore(prefix="MYAPP_")
value = await store.get("API_KEY")
```

### HashiCorp Vault
```python
from aicp import HashiCorpVaultStore

store = HashiCorpVaultStore(
    url="https://vault.example.com",
    token="vault-token",
)
value = await store.get("secret/data/mykey")
```

### AWS Secrets Manager
```python
from aicp import AWSSecretsManagerStore

store = AWSSecretsManagerStore(region_name="us-east-1")
value = await store.get("my-secret-name")
```

### With Caching
```python
from aicp import SecretManager, EnvSecretStore

store = EnvSecretStore()
manager = SecretManager(store, cache_ttl=300)  # 5 min TTL
value = await manager.get("API_KEY")
```

---

## Caching

### Redis Cache
```python
from aicp import RedisCache

cache = RedisCache(host="localhost", prefix="myapp:")

# Set
await cache.set("key", {"data": "value"}, ttl=60)

# Get
value = await cache.get("key")

# Check exists
exists = await cache.exists("key")
```

### Distributed Rate Limiting
```python
from aicp import RedisCache, RateLimiterRedis

cache = RedisCache(url="redis://localhost")
limiter = RateLimiterRedis(cache, key="api", limit=100, window=60)

allowed = await limiter.check()
remaining = await limiter.get_remaining()
```

---

## Production API Features

### API Versioning
```python
from aicp import VersionManager, APIVersion

manager = VersionManager()
config = manager.get_config(APIVersion.V2)

# Get deprecation headers
headers = manager.get_deprecation_headers(APIVersion.V1)
```

### Graceful Shutdown
```python
from aicp import GracefulShutdown, lifespan_context
from fastapi import FastAPI

app = FastAPI(lifespan=lifespan_context)

shutdown = GracefulShutdown(app)
shutdown.register_shutdown_task(cleanup_database)
shutdown.register_shutdown_task(close_connections)
```

### Health Checks Router
```python
from aicp import HealthCheckRouter, ReadinessHealthCheck

router = HealthCheckRouter()
app.include_router(router.create_router())
# GET /health
# GET /health/live
# GET /health/ready
```

---

## Transport Adapters

### WebSocket
```python
from aicp.adapters.protocol.websocket import WebSocketTransport

transport = WebSocketTransport(url="ws://localhost:8765/ws")
await transport.connect()
result = await transport.send({"method": "execute", "tool": "..."})

# Streaming
async for chunk in transport.send_stream(request):
    print(chunk)
```

### SSE (Server-Sent Events)
```python
from aicp.adapters.protocol.sse import SSETransport

transport = SSETransport(url="http://localhost:8080")

async for event in transport.stream_events(request):
    print(event)
```

### GraphQL
```python
from aicp.adapters.protocol.graphql import GraphQLTransport

transport = GraphQLTransport(url="http://localhost:4000/graphql")

result = await transport.send({
    "query": "mutation { executeTool(name: $name) { result } }",
    "variables": {"name": "payments.transfer"},
})
```

---

## Complete Example: Production Service

```python
from aicp import (
    FastAPI,
    AicpExecutor,
    AicpRegistry,
    Capability,
    OAuth2Auth,
    RateLimiter,
    SecureAuditLog,
    TenantManager,
    HealthCheckRouter,
    get_logger,
    get_metrics,
    retry_async,
    CircuitBreaker,
)

# 1. Setup
app = FastAPI()
logger = get_logger("production")
metrics = get_metrics()

# 2. Multi-tenant
tenant_manager = TenantManager()
tenant = tenant_manager.create_tenant("Acme Corp")

# 3. Capabilities
registry = AicpRegistry()
registry.register_capability(Capability(
    name="payments.transfer",
    description="Transfer funds",
    tags=["finance"],
))

# 4. Executor with rate limiting
executor = AicpExecutor(registry)
rate_limiter = RateLimiter(60, 60)

# 5. Audit logging
audit_log = SecureAuditLog("production-secret")

# 6. Health checks
health_router = HealthCheckRouter()
app.include_router(health_router.create_router())

# 7. API endpoint
@app.post("/api/v1/execute/{tool_name}")
async def execute_tool(tool_name: str, request: dict):
    # Rate limit
    rate_limiter.check(tenant.id)
    metrics.increment_counter("executions_total", labels={"tool": tool_name})
    
    # Audit
    entry = audit_log.append({
        "tool": tool_name,
        "tenant": tenant.id,
        "args": request,
    })
    
    # Execute with retry
    result = await retry_async(
        lambda: executor.execute(tool_name, request),
        max_attempts=3,
    )
    
    return result.model_dump()
```

---

## What's Next?

- Check out [Architecture](ARCHITECTURE.md) for system design
- See [API Reference](../reference/index.md) for full API docs
- Review [Governance](../overview/GOVERNANCE.md) for policy management
