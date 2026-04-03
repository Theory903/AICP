# How to Use AICP

> Complete usage reference — from CLI bootstrapping to programmatic API usage, authentication, security, and production patterns.

---

## Table of Contents

1. [The CLI Workflow](#the-cli-workflow)
2. [Core Programmatic Usage](#core-programmatic-usage)
3. [Authentication](#authentication)
4. [Capability Registry and Search](#capability-registry-and-search)
5. [Execution and Streaming](#execution-and-streaming)
6. [Security Features](#security-features)
7. [Multi-Tenancy](#multi-tenancy)
8. [Reliability Patterns](#reliability-patterns)
9. [Observability](#observability)
10. [Production API Features](#production-api-features)
11. [Transport Adapters](#transport-adapters)

---

## The CLI Workflow

Most applications follow a simple 4-step path:

```
1. bootstrap    → Read existing routes, create configurations
2. preview      → Understand how agents see each capability
3. protect      → Add approval requirements to risky actions
4. dev/start    → Run the engine in front of your application
```

### Bootstrapping

The fastest way to onboard an application:

```bash
# Bootstrap a FastAPI server
aicp bootstrap fastapi src.main:app

# Bootstrap an OpenAPI spec
aicp bootstrap openapi ./api.json
```

### Previewing Capabilities

See how agents see each capability and what policy applies:

```bash
aicp preview payments.transfer
```

Output shows:
- Extracted input/output schemas
- Applied tags (`[destructive]`, `[high-risk]`)
- Effective policy (`allow`, `ask`, `require_approval`, `deny`)

### Protecting Capabilities

Add approval requirements to risky actions:

```bash
# Require approval for a specific capability
aicp protect payments.transfer

# Add rate limits
aicp limit "users.read.*" --rpm 60
```

### Running the Runtime

```bash
# Start runtime with file-backed persistence
aicp serve --host 127.0.0.1 --port 8000 --store-path ./.aicp-runtime

# Start runtime with SQLite-backed persistence
aicp serve --host 127.0.0.1 --port 8000 --store-backend sqlite --store-path ./.aicp-runtime/runtime.db
```

### Development Mode

For local development with live reload:

```bash
aicp dev --port 8000
```

---

## Core Programmatic Usage

For developers building complex AI systems, interact directly with the Python SDK:

```python
from aicp import (
    Capability, 
    CapabilityKind, 
    AicpExecutor,
    InMemoryCapabilityRepository,
)

# 1. Register a capability
capability = Capability(
    name="payments.transfer",
    description="Transfer money between accounts",
    kind=CapabilityKind.ACTION,
    input_schema={
        "type": "object",
        "properties": {
            "amount": {"type": "number"},
            "recipient": {"type": "string"}
        },
        "required": ["amount", "recipient"]
    },
    output_schema={"type": "object"},
    requires_approval=True,
    risk_level="high",
)

# 2. Register it
repo = InMemoryCapabilityRepository()
repo.register(capability)

# 3. Execute
executor = AicpExecutor(repo)
result = await executor.execute("payments.transfer", {"amount": 100, "recipient": "rahul"})
print(result.status)  # "success" or "pending_approval"
print(result.execution_id)  # "exec_..."
print(result.allowed_next_actions)  # [...]
```

---

## Authentication

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

## Capability Registry and Search

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

### Search by Tags and Query

```python
results = registry.search_capabilities(
    query="user management",
    tags=["admin"],
    limit=10,
)
```

### Semantic Search (v0.2.0)

```python
results = registry.semantic_search(
    query="transfer money to another user",
    limit=5,
)
```

---

## Execution and Streaming

### Basic Execution

```python
from aicp import AicpExecutor

executor = AicpExecutor(capability_provider, policy_engine)
result = await executor.execute("tool.name", {"arg": "value"})
print(result.status)
print(result.data)
print(result.allowed_next_actions)
```

### Streaming Execution

```python
async for chunk in executor.execute_streaming("tool.name", {"arg": "value"}):
    print(chunk)
    # {"type": "start", "capability": "..."}
    # {"type": "progress", "message": "Processing..."}
    # {"type": "result", "status": "success", "data": ...}
    # {"type": "end"}
```

### Execution Envelope

Every execution returns the canonical envelope:

```json
{
  "execution_id": "exec_a1b2c3d4",
  "capability_name": "payments.transfer",
  "status": "success",
  "data": {"transaction_id": "txn_..."},
  "policy_result": {"effect": "allow", "trust_tier": 2},
  "allowed_next_actions": [{"name": "payment.confirm", "confidence": 0.95}],
  "rendered": "Transfer of ₹1000 completed",
  "execution_time_ms": 234
}
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
    result = await executor.execute("tool", {})
    # All operations in this context are tenant-isolated
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

result = await retry_async(my_function, config=config)
```

### Circuit Breaker

```python
from aicp import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpen

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

---

## Transport Adapters

### HTTP

```python
from aicp.adapters.protocol.http import HTTPTransport

transport = HTTPTransport(url="https://api.example.com")
result = await transport.send({"method": "execute", "capability": "...", "args": {...}})
```

### WebSocket

```python
from aicp.adapters.protocol.websocket import WebSocketTransport

transport = WebSocketTransport(url="ws://localhost:8765/ws")
await transport.connect()
result = await transport.send({"capability": "...", "args": {...}})

# Streaming
async for chunk in transport.send_stream(request):
    print(chunk)
```

### MCP (Model Context Protocol)

```python
from aicp.adapters.protocol.mcp import MCPClient

client = MCPClient()
tools = await client.list_tools()
result = await client.call_tool("tool_name", {"arg": "value"})
```

### OpenAPI Import

```bash
# Import OpenAPI spec as capabilities
aicp map openapi ./api.json

# Or programmatically
from aicp.adapters.importers.openapi import OpenAPIImporter

importer = OpenAPIImporter()
capabilities = importer.import_from_file("./api.json")
```

---

## Complete Example: Production Service

```python
from aicp import (
    FastAPI,
    AicpExecutor,
    AicpRegistry,
    Capability,
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
@app.post("/api/v1/execute/{capability_name}")
async def execute_capability(capability_name: str, request: dict):
    # Rate limit
    rate_limiter.check(tenant.id)
    metrics.increment_counter("executions_total", labels={"capability": capability_name})
    
    # Audit
    entry = audit_log.append({
        "capability": capability_name,
        "tenant": tenant.id,
        "args": request,
    })
    
    # Execute with retry
    result = await retry_async(
        lambda: executor.execute(capability_name, request),
        max_attempts=3,
    )
    
    return result.model_dump()
```

---

## See Also

- [CLI_REFERENCE.md](./CLI_REFERENCE.md) — 28 CLI commands
- [ARCHITECTURE.md](./ARCHITECTURE.md) — System design for contributors
- [RUN_RUNTIME_STUDIO.md](./RUN_RUNTIME_STUDIO.md) — Running runtime and Studio
- [Governance](../overview/GOVERNANCE.md) — Policy management
- [Action Surface](../overview/ACTION_SURFACE.md) — Capability model details
