# Provider Guide

> **Complete model provider reference for Mammoth.**
> All supported AI providers, configuration, model selection, cost management, and routing.

---

## Overview

Mammoth supports every major AI provider via a unified provider interface. The same conversation, tool execution, and governance model works regardless of which model is selected. Switching providers is a single command.

**Provider interface:** `apps/mammoth/crates/api/src/providers/mod.rs`

```rust
pub trait Provider: Send + Sync {
    fn name(&self) -> &str;
    fn available_models(&self) -> Vec<ModelInfo>;
    fn is_configured(&self) -> bool;
    async fn complete(&self, req: CompletionRequest) -> Result<CompletionResponse>;
    async fn stream(&self, req: CompletionRequest) -> Result<CompletionStream>;
    fn supports_tools(&self) -> bool;
    fn supports_vision(&self) -> bool;
    fn max_context_tokens(&self) -> usize;
    fn pricing(&self) -> Option<ModelPricing>;
}
```

---

## Supported Providers

### Anthropic

**Status:** Production. Primary recommended provider.

**Config:**
```json
{
  "providers": {
    "anthropic": {
      "api_key_env": "ANTHROPIC_API_KEY",
      "base_url": "https://api.anthropic.com",
      "default_model": "claude-sonnet-4-5",
      "max_retries": 3,
      "timeout_secs": 120
    }
  }
}
```

**Models:**

| Model | ID | Context | Input $/M | Output $/M | Strengths |
|-------|----|---------|-----------|------------|-----------|
| Claude Sonnet 4.5 | `claude-sonnet-4-5` | 200K | $3.00 | $15.00 | Recommended. Best balance of speed, intelligence, tool use |
| Claude Opus 4.5 | `claude-opus-4-5` | 200K | $15.00 | $75.00 | Max capability, complex reasoning, long-context synthesis |
| Claude Haiku 3.5 | `claude-haiku-3-5` | 200K | $0.25 | $1.25 | Fast, cheap, great for tool-heavy agentic loops |
| Claude Sonnet 3.7 | `claude-sonnet-3-7` | 200K | $3.00 | $15.00 | Extended thinking mode, deep reasoning chains |
| Claude Sonnet 3.5 | `claude-sonnet-3-5` | 200K | $3.00 | $15.00 | Previous generation, stable |

**Special features:**
- Extended thinking mode (Sonnet 3.7): `--thinking` flag, budget tokens configurable
- Computer use (Sonnet 3.5+): `--computer-use` enables screenshot+click tools
- Prompt caching: automatic for long AGENTS.md / instruction files
- Vision: all models support image input

**Implementation:** `apps/mammoth/crates/api/src/providers/mammoth_provider.rs`

---

### OpenAI

**Status:** Production.

**Config:**
```json
{
  "providers": {
    "openai": {
      "api_key_env": "OPENAI_API_KEY",
      "base_url": "https://api.openai.com/v1",
      "default_model": "gpt-4o",
      "organization": null,
      "project": null
    }
  }
}
```

**Models:**

| Model | ID | Context | Input $/M | Output $/M | Strengths |
|-------|----|---------|-----------|------------|-----------|
| GPT-4o | `gpt-4o` | 128K | $2.50 | $10.00 | Best OpenAI general model, fast tool calling |
| GPT-4o mini | `gpt-4o-mini` | 128K | $0.15 | $0.60 | Ultra-fast, cheap, good for simple tasks |
| o3 | `o3` | 200K | $10.00 | $40.00 | Best reasoning model, complex math/code |
| o4-mini | `o4-mini` | 200K | $1.10 | $4.40 | Fast reasoning, good cost/performance |
| o3-mini | `o3-mini` | 200K | $1.10 | $4.40 | Efficient reasoning |
| GPT-4.1 | `gpt-4.1` | 1M | $2.00 | $8.00 | 1M context window, long document analysis |
| GPT-4.1 mini | `gpt-4.1-mini` | 1M | $0.40 | $1.60 | Long context, affordable |

**Special features:**
- Reasoning models (o3, o4-mini): extended reasoning, configurable reasoning budget
- Vision: GPT-4o and GPT-4.1 models
- Structured outputs: enforced JSON schema adherence
- Function calling: full parallel tool execution

**Implementation:** `apps/mammoth/crates/api/src/providers/openai_compat.rs`

---

### Google (Gemini)

**Status:** Production.

**Config:**
```json
{
  "providers": {
    "google": {
      "api_key_env": "GOOGLE_API_KEY",
      "base_url": "https://generativelanguage.googleapis.com/v1beta",
      "default_model": "gemini-2.5-pro",
      "vertex_ai": {
        "enabled": false,
        "project_id": null,
        "location": "us-central1"
      }
    }
  }
}
```

**Models:**

| Model | ID | Context | Input $/M | Output $/M | Strengths |
|-------|----|---------|-----------|------------|-----------|
| Gemini 2.5 Pro | `gemini-2.5-pro` | 1M | $1.25 | $10.00 | 1M context, strong coding, reasoning |
| Gemini 2.5 Flash | `gemini-2.5-flash` | 1M | $0.15 | $0.60 | Fast, cheap, good for long-context tasks |
| Gemini 2.0 Flash | `gemini-2.0-flash` | 1M | $0.10 | $0.40 | Cheapest 1M context model |
| Gemini 2.0 Flash Thinking | `gemini-2.0-flash-thinking` | 32K | $0.10 | $0.40 | Thinking traces, experimental |
| Gemini 1.5 Pro | `gemini-1.5-pro` | 2M | $1.25 | $5.00 | 2M context (largest), legacy |

**Special features:**
- Massive context windows (up to 2M tokens)
- Grounding with Google Search
- Code execution tool (Gemini native)
- Image/video/audio input

**Vertex AI:** Supported via `vertex_ai.enabled: true`. Uses Application Default Credentials.

---

### Ollama (Local Models)

**Status:** Production. Zero cost, full privacy.

**Config:**
```json
{
  "providers": {
    "ollama": {
      "base_url": "http://localhost:11434",
      "default_model": "llama3.3-70b",
      "timeout_secs": 300,
      "auto_pull": false
    }
  }
}
```

**Recommended Models:**

| Model | Pull Command | Size | Strengths |
|-------|-------------|------|-----------|
| Llama 3.3 70B | `ollama pull llama3.3:70b` | 43 GB | Best local general model |
| Qwen2.5-Coder 32B | `ollama pull qwen2.5-coder:32b` | 19 GB | Best local coding model |
| Qwen2.5 72B | `ollama pull qwen2.5:72b` | 47 GB | Strong reasoning, multilingual |
| Gemma 3 27B | `ollama pull gemma3:27b` | 17 GB | Google, efficient |
| Gemma 4 31B | `ollama pull gemma4:31b` | 19 GB | Tau2-bench 86.4%, great for planning |
| E4B (Emergent) | `ollama pull e4b` | 3.5 GB | Edge devices, worker agents |
| DeepSeek-R1 32B | `ollama pull deepseek-r1:32b` | 20 GB | Strong reasoning, MIT license |
| Mistral Small 24B | `ollama pull mistral-small:24b` | 14 GB | Function calling focus |
| Phi-4 14B | `ollama pull phi-4:14b` | 8 GB | Microsoft, fast, small |

**Tool calling support:** Mammoth automatically detects whether the loaded model supports tool calling via Ollama's model metadata. Models without native tool support fall back to XML-style tool calling with a compatibility shim.

**Implementation:** `apps/mammoth/crates/api/src/providers/openai_compat.rs` (Ollama is OpenAI-compatible)

---

### OpenAI-Compatible (Custom Endpoints)

Any service exposing an OpenAI-compatible API works with Mammoth.

**Config:**
```json
{
  "providers": {
    "custom": [
      {
        "name": "together-ai",
        "base_url": "https://api.together.xyz/v1",
        "api_key_env": "TOGETHER_API_KEY",
        "models": [
          "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
          "Qwen/Qwen2.5-72B-Instruct-Turbo"
        ]
      },
      {
        "name": "groq",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"]
      },
      {
        "name": "fireworks",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "api_key_env": "FIREWORKS_API_KEY",
        "models": ["accounts/fireworks/models/llama-v3p1-405b-instruct"]
      },
      {
        "name": "lm-studio",
        "base_url": "http://localhost:1234/v1",
        "api_key_env": null,
        "models": ["auto"]
      }
    ]
  }
}
```

**Works with:** Together AI, Groq, Fireworks AI, Perplexity, Mistral AI, Cohere, LM Studio, vLLM, LocalAI, text-generation-webui, Jan.ai, LiteLLM proxy.

---

### Amazon Bedrock

**Status:** Planned (v0.4.0).

**Config:**
```json
{
  "providers": {
    "bedrock": {
      "region": "us-east-1",
      "profile": "default",
      "models": [
        "anthropic.claude-sonnet-4-5-v1:0",
        "amazon.nova-pro-v1:0",
        "meta.llama3-3-70b-instruct-v1:0"
      ]
    }
  }
}
```

Uses AWS credentials (environment variables, `~/.aws/credentials`, or IAM role).

---

### Azure OpenAI

**Status:** Planned (v0.4.0).

**Config:**
```json
{
  "providers": {
    "azure": {
      "endpoint": "https://myresource.openai.azure.com",
      "api_key_env": "AZURE_OPENAI_API_KEY",
      "api_version": "2024-02-01",
      "deployments": {
        "gpt-4o": "my-gpt4o-deployment",
        "gpt-4o-mini": "my-gpt4o-mini-deployment"
      }
    }
  }
}
```

---

## Model Routing

Mammoth supports automatic model routing for cost and performance optimization.

### Route Profiles

```json
{
  "routing": {
    "profile": "balanced",
    "rules": [
      {
        "condition": "task_type == 'simple_qa'",
        "model": "claude-haiku-3-5"
      },
      {
        "condition": "context_tokens > 100000",
        "model": "gemini-2.5-pro"
      },
      {
        "condition": "task_type == 'reasoning'",
        "model": "o3"
      },
      {
        "condition": "offline == true",
        "model": "ollama/qwen2.5-coder-32b"
      }
    ]
  }
}
```

### Built-in Profiles

| Profile | Description |
|---------|-------------|
| `performance` | Best model for each task, cost secondary |
| `balanced` | Default. Good performance/cost tradeoff |
| `economy` | Cheapest model that handles the task |
| `local` | Always use local Ollama models |
| `private` | Local models only, never send data externally |

---

## Model Router

`apps/mammoth/crates/runtime/src/model_router.rs`

The `ModelRouter` selects the best available model based on:

1. Explicit user selection (highest priority)
2. Task classification result
3. Active routing profile
4. Provider availability (falls back if unreachable)
5. Context window fit (switches to larger context model if needed)

```rust
pub struct ModelRouter {
    providers: HashMap<String, Box<dyn Provider>>,
    profile: RoutingProfile,
    classifier: TaskClassifier,
}

impl ModelRouter {
    pub async fn select(&self, ctx: &RequestContext) -> Result<ModelSelection>;
    pub async fn route(&self, req: CompletionRequest) -> Result<CompletionResponse>;
    pub fn set_profile(&mut self, profile: RoutingProfile);
    pub fn override_model(&mut self, model_id: &str);
}
```

---

## Provider Detection

Auto-detects configured providers on startup by checking:

1. Environment variables (API keys)
2. `~/.mammoth.json` configuration
3. Ollama availability (`http://localhost:11434`)
4. AWS credentials (for Bedrock)
5. Application Default Credentials (for Vertex AI)

```
[mammoth startup]
Checking providers...
  ✓ Anthropic (ANTHROPIC_API_KEY set)
  ✓ OpenAI (OPENAI_API_KEY set)
  ○ Google (GOOGLE_API_KEY not set)
  ✓ Ollama (http://localhost:11434 reachable, 3 models)
  ○ Azure (not configured)
```

---

## Cost Tracking

Mammoth tracks token usage and estimated cost per session, turn, and tool call.

### Session cost display (TUI header)
```
↑ $0.032
```

### Detailed breakdown (`/cost`)
```
  SESSION COST BREAKDOWN

  Model: claude-sonnet-4-5

  Turns:    12
  Input:    4,821 tokens    $0.014
  Output:   2,034 tokens    $0.031
  Cache:    12,430 tokens   $0.002   (cached reads)
  ─────────────────────────────────
  Total:                    $0.047

  TOOL CALLS (8)
  bash ×5               0 tokens    $0.000
  read_file ×2          0 tokens    $0.000
  edit_file ×1          0 tokens    $0.000

  SESSION TOTAL:  $0.047
```

### Budget limits
```json
{
  "budget": {
    "session_limit_usd": 1.00,
    "turn_limit_usd": 0.10,
    "warn_at_percent": 80,
    "hard_stop": true
  }
}
```

---

## Environment Variables

Quick reference for all provider credentials:

```bash
# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# OpenAI
export OPENAI_API_KEY="sk-..."
export OPENAI_ORG_ID="org-..."       # optional

# Google
export GOOGLE_API_KEY="AIza..."      # Gemini API
# OR use Application Default Credentials for Vertex AI

# Together AI
export TOGETHER_API_KEY="..."

# Groq
export GROQ_API_KEY="gsk_..."

# Fireworks AI
export FIREWORKS_API_KEY="fw_..."

# AWS Bedrock (uses standard AWS credentials)
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_REGION="us-east-1"

# Azure OpenAI
export AZURE_OPENAI_API_KEY="..."
export AZURE_OPENAI_ENDPOINT="https://myresource.openai.azure.com"
```

---

## Provider Health

`/doctor` checks all provider connectivity. Programmatic access:

```bash
aicp providers health
```

```json
{
  "providers": [
    {
      "name": "anthropic",
      "status": "healthy",
      "latency_ms": 142,
      "last_checked": "2026-04-05T13:42:07Z"
    },
    {
      "name": "ollama",
      "status": "healthy",
      "latency_ms": 8,
      "models_loaded": ["llama3.3:70b", "qwen2.5-coder:32b", "gemma3:27b"]
    }
  ]
}
```

---

## Implementation Guide

### Adding a New Provider

1. Create `apps/mammoth/crates/api/src/providers/<name>.rs`
2. Implement the `Provider` trait
3. Register in `apps/mammoth/crates/api/src/providers/mod.rs`
4. Add config schema to `apps/mammoth/crates/runtime/src/config.rs`
5. Add to provider detection in `apps/mammoth/crates/runtime/src/bootstrap.rs`
6. Add to `/doctor` checks in `apps/mammoth/crates/mammoth-cli/src/commands/doctor.rs`
7. Add integration test in `apps/mammoth/crates/api/tests/`

### Minimal provider implementation

```rust
use async_trait::async_trait;
use crate::providers::{Provider, ModelInfo, CompletionRequest, CompletionResponse, ModelPricing};

pub struct MyProvider {
    api_key: String,
    client: reqwest::Client,
}

#[async_trait]
impl Provider for MyProvider {
    fn name(&self) -> &str { "my-provider" }

    fn available_models(&self) -> Vec<ModelInfo> {
        vec![
            ModelInfo {
                id: "my-model-v1".to_string(),
                display_name: "My Model V1".to_string(),
                context_window: 128_000,
                supports_tools: true,
                supports_vision: false,
                pricing: Some(ModelPricing {
                    input_per_million: 1.00,
                    output_per_million: 4.00,
                }),
            }
        ]
    }

    fn is_configured(&self) -> bool {
        !self.api_key.is_empty()
    }

    async fn complete(&self, req: CompletionRequest) -> anyhow::Result<CompletionResponse> {
        // Call your API, return CompletionResponse
        todo!()
    }

    async fn stream(&self, req: CompletionRequest) -> anyhow::Result<CompletionStream> {
        // Return streaming response
        todo!()
    }

    fn supports_tools(&self) -> bool { true }
    fn supports_vision(&self) -> bool { false }
    fn max_context_tokens(&self) -> usize { 128_000 }
}
```

---

## See Also

- [TUI_REFERENCE.md](./TUI_REFERENCE.md) — Model picker UI
- [MULTI_AGENT.md](./MULTI_AGENT.md) — Model selection for worker agents
- [DOCTOR_DIAGNOSTICS.md](./DOCTOR_DIAGNOSTICS.md) — Provider health checks
