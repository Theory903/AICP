# AICP Complete Knowledge Base

> **Last Updated:** 2026-04-07 | **Version:** 0.9.10

---

## Project Overview

**AICP (AI Capability Protocol)** is the control plane for secure agentic and organizational automation. It provides governed backend services: capabilities, workflows, policy, approvals, sessions, audit, discovery, and execution contracts.

| Attribute | Value |
|-----------|-------|
| **Current Version** | 0.9.10 |
| **Primary Language** | Python 3.10+ |
| **Secondary Language** | TypeScript 5.x (SDKs), Rust (Mammoth) |
| **Compliance Level** | L5 (Full Orchestration) |
| **Test Count** | 1224 (Python: 1038, Rust: 186) |
| **CLI Commands** | 28 |

---

## Architecture: 11 Planes

| # | Plane | Purpose | Status |
|---|-------|---------|--------|
| 0 | Signal | Event ingestion, routing | ✅ |
| 1 | Perception | a11y tree, DOM, screenshots | ✅ |
| 2 | AI | Planner, judge, memory | ✅ |
| 3 | Capability | Registry, schema, discovery | ✅ |
| 4 | Workflow | Sequential, parallel, loops, subflows | ✅ |
| 5 | Governance | Policy, trust tiers, approvals | ✅ |
| 6 | Execution | Realtime, transactional, event-driven | ✅ |
| 7 | Multi-Agent | Orchestrator/specialist/worker | ✅ |
| 8 | Federation | CRDT, DID, cross-org | ✅ |
| 9 | Supervision | Approval queue, replay | ✅ |
| 10 | Learning | Skill mining, drift detection | ✅ |

---

## 20 Modules

| # | Module | Plane | Status |
|---|--------|-------|--------|
| 1 | Principal and Org Control | Governance | ✅ Complete |
| 2 | Identity and Trust | Governance | ✅ Complete |
| 3 | Capability Registry | Capability | ✅ Complete |
| 4 | Tool Runtime | Execution | ✅ Complete |
| 5 | Workflow Engine | Workflow | ✅ Complete |
| 6 | Perception/Signal | Perception | ✅ Complete |
| 7 | Human Cognitive Protocols | Supervision | ✅ Complete |
| 8 | AI Plane | AI | ✅ Complete |
| 9 | Memory System | AI | ✅ Complete |
| 10 | Code Intelligence DB | AI | ✅ Complete |
| 11 | Discovery Engine | Capability | ✅ Complete |
| 12 | Governance/Policy | Governance | ✅ Complete |
| 13 | Execution Engine | Execution | ✅ Complete |
| 14 | Multi-Agent Hierarchy | Multi-Agent | ✅ Complete |
| 15 | Agent Communication Bus | Multi-Agent | ✅ Complete |
| 16 | Federation | Federation | ✅ Complete |
| 17 | Human Web Compatibility | Perception | ✅ Complete |
| 18 | Audit/Replay | Supervision | ✅ Complete |
| 19 | Learning | Learning | ✅ Complete |
| 20 | Domain Packs | Learning | ✅ Complete |

---

## Recent Work (Session ses_29b6)

### Completed This Session

1. **Voice/STT Service** (`modules/aicp-core/src/aicp/voice/stt_client.py`)
   - STT Providers: faster-whisper, Deepgram, OpenAI Whisper
   - TTS Providers: XTTS-v2, Qwen3-TTS, Sooktam2

2. **LLM Service** (`modules/aicp-core/src/aicp/llm/__init__.py`)
   - Providers: Gemma 4, Ollama, Google AI
   - 5/6 tests passing

3. **Provider Manifest** (`modules/aicp-core/src/aicp/providers/manifest.py`)
   - Added: `GEMMA`, `VERTEX_AI`
   - Capabilities: `stt`, `tts`, `ocr`, `face_recognition`

### Remaining Tasks

| Priority | Task | Status |
|----------|------|--------|
| HIGH | Fix LSP errors in `llm/__init__.py` (line 212: `options` undefined, lines 235/318 async return type mismatch) | Pending |
| HIGH | Fix LSP errors in `voice/stt_client.py` (faster_whisper import, TTS.api import) | Pending |
| MEDIUM | Implement Vision service (PaddleOCR, FLUX) | Pending |
| MEDIUM | Implement Face service (CompreFace) | Pending |
| LOW | Create plugin architecture for model switching | Pending |
| LOW | Update documentation | Pending |

---

## Key Files

| Path | Purpose |
|------|---------|
| `modules/aicp-core/src/aicp/voice/stt_client.py` | Voice/STT/TTS implementation |
| `modules/aicp-core/src/aicp/llm/__init__.py` | LLM/Gemma client implementation |
| `modules/aicp-core/src/aicp/providers/manifest.py` | Provider types and capabilities |
| `modules/aicp-core/tests/llm/test_llm_client.py` | LLM client tests |
| `session-ses_29b6.md` | Session file for voice/LLM work |

---

## Code Patterns

### Python Capability Definition
```python
class Capability(BaseModel):
    name: str
    description: str
    kind: CapabilityKind
    input_schema: dict
    output_schema: dict
    requires_approval: bool = False
    risk_level: str = "medium"
```

### LLM Client
```python
class LLMClientBase(ABC):
    @abstractmethod
    async def chat_completion(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> ChatCompletionResponse:
        pass
```

### Voice Client
```python
class VoiceClient:
    def __init__(
        self,
        stt_provider: STTProvider | None = None,
        tts_provider: TTSProvider | None = None,
        ...
    ):
        ...
```

---

## Build Commands

### Python
```bash
# Install all packages
pip install -e "packages/core[dev]" -e packages/runtime -e packages/cli

# Run tests
pytest packages/core/tests/ -v

# Lint
ruff check . && ruff format --check .
```

### Rust (Mammoth)
```bash
cd apps/mammoth
cargo build -p mammoth-cli
```

---

## Coding Standards

- **Python**: PEP 8, type hints everywhere, `Optional[X]` over `X | None`
- **TypeScript**: Google TypeScript Style Guide, explicit return types
- **No**: `as any`, `@ts-ignore`, empty catch blocks, silent exception swallowing
- **Custom exceptions**: Inherit from `AicpError`

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| 0.1.1-alpha | 2025 | Foundation |
| 0.3.0 | 2026-04-03 | Orchestration |
| 0.4.0 | 2026-04-04 | Agent Integration |
| 0.9.9 | 2026-04-05 | Production features |
| **0.9.10** | **2026-04-06** | **SDKs, Platforms, Integrations** |

---

## Next Steps

1. Fix LSP errors in `llm/__init__.py` and `voice/stt_client.py`
2. Implement Vision service with PaddleOCR and FLUX support
3. Implement Face service with CompreFace
4. Create plugin architecture for dynamic model switching
5. Run full test suite and verify all tests pass
