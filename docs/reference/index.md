# Reference

API reference documentation for AICP.

## Python SDK

### Core Models

- `Capability` - Main capability model
- `CapabilityKind` - Enum for capability types (action, query, workflow, etc.)
- `InputSchema` / `OutputSchema` - JSON Schema definitions
- `Policy` - Access control policies
- `PolicyEffect` - Enum for policy effects (allow, deny, ask, limit)

### Registry & Executor

- `AicpRegistry` - Capability registry
- `AicpExecutor` - Capability executor with policy enforcement
- `DefaultPolicyEngine` - Policy evaluation engine
- `DefaultWorkflowRuntime` - Workflow execution

### Adapters

- `HttpExecutionAdapter` - HTTP protocol adapter
- `McpAdapter` - MCP protocol adapter

## JSON Schemas

See `/spec/schemas/` for protocol schemas:
- `capability.schema.json`
- `policy.schema.json`
- `workflow.schema.json`
- `execution-result.schema.json`
- `discovery.schema.json`
- `error.schema.json`

## CLI

```bash
# Register a capability
aicp register --name payments.transfer --kind action

# List capabilities
aicp list

# Execute a capability
aicp call payments.transfer --args '{"amount": 100}'
```
