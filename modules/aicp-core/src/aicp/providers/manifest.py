from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProviderType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    CUSTOM = "custom"
    GEMMA = "gemma"
    VERTEX_AI = "vertex_ai"
    NEO4J = "neo4j"


_ALLOWED_CAPABILITIES = {
    "chat",
    "completion",
    "embedding",
    "streaming",
    "vision",
    "function_calling",
    "stt",
    "tts",
    "ocr",
    "face_recognition",
    "graph_retrieval",
    "knowledge_graph_query",
}


class ProviderManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    provider_type: ProviderType
    base_url: str
    api_key_env: str
    models: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    max_tokens: int | None = Field(default=None, ge=1)
    rate_limit_rpm: int | None = Field(default=None, ge=1)
    timeout_seconds: int | None = Field(default=None, ge=1)

    @field_validator("id", "name", "base_url", "api_key_env", mode="before")
    @classmethod
    def _validate_required_string(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("value must be a string")
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("models", mode="before")
    @classmethod
    def _validate_models(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("models must be a list")
        normalized: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("model identifiers must be strings")
            model_id = item.strip()
            if not model_id:
                raise ValueError("model identifiers must not be empty")
            normalized.append(model_id)
        return normalized

    @field_validator("capabilities", mode="before")
    @classmethod
    def _validate_capabilities(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("capabilities must be a list")
        deduped: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                raise ValueError("capabilities must be strings")
            capability = item.strip()
            if capability not in _ALLOWED_CAPABILITIES:
                raise ValueError(f"unsupported capability: {capability}")
            if capability not in seen:
                deduped.append(capability)
                seen.add(capability)
        return deduped
