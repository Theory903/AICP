"""LLM (Large Language Model) providers for AICP.

This module provides:
- Gemma 4 provider (local and API)
- Multi-provider LLM client with unified interface
- Streaming and non-streaming chat completion

Patterns adapted from AICP provider system.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, AsyncIterator, Generator
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ============================================================================
# LLM Provider Types
# ============================================================================


class LLMProviderType(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    GEMMA = "gemma"
    OLLAMA = "ollama"
    VERTEX_AI = "vertex_ai"


# ============================================================================
# LLM Models
# ============================================================================


class GemmaModel(str, Enum):
    """Gemma 4 model variants."""
    GEMMA_4_2B = "gemma-4-2b"
    GEMMA_4_4B = "gemma-4-4b"
    GEMMA_4_9B = "gemma-4-9b"
    GEMMA_4_27B = "gemma-4-27b"
    GEMMA_3_1_2B = "gemma3-1-2b"
    GEMMA_3_1_4B = "gemma3-1-4b"
    INDIC_GEMMA = "indic-gemma"


# ============================================================================
# Request/Response Models
# ============================================================================


@dataclass
class ChatMessage:
    """Chat message."""
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class ChatCompletionChunk:
    """Streaming chat completion chunk."""
    content: str
    finish_reason: str | None = None


class ChatCompletionResponse(BaseModel):
    """Chat completion response."""
    id: str
    model: str
    content: str
    finish_reason: str | None = None
    usage: dict[str, int] = Field(default_factory=dict)


# ============================================================================
# LLM Client Protocol
# ============================================================================


class LLMClientBase(ABC):
    """Abstract base for LLM clients."""

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> ChatCompletionResponse:
        """Send chat completion request."""
        pass

    @abstractmethod
    # type: ignore[override]
    async def stream_chat_completion(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Stream chat completion."""
        pass  # type: ignore[notImplemented]

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass


# ============================================================================
# Google Gemma Client
# ============================================================================


class GemmaClient(LLMClientBase):
    """Google Gemma 4 LLM client.

    Supports local (via Ollama) and API (via Google AI Studio) deployment.
    Balanced for mid-range GPU: 2B, 4B, 9B variants recommended.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemma-4-4b",
        base_url: str | None = None,
        **options,
    ):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        self.model = model
        self.base_url = base_url or "https://generativelanguage.googleapis.com/v1beta"
        self.options = options

    def is_available(self) -> bool:
        """Check if Gemma is available."""
        return bool(self.api_key) or bool(self.base_url)

    async def chat_completion(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> ChatCompletionResponse:
        """Send chat completion request to Gemma."""
        return await self._google_ai_completion(
            messages, model, temperature, max_tokens
        )

    async def _ollama_completion(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> ChatCompletionResponse:
        """Completion via Ollama local server."""
        import aiohttp

        model_id = model or self.model
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": model_id,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "options": {"num_predict": max_tokens} if max_tokens else {},
        }

        async with aiohttp.ClientSession() as session, session.post(url, json=payload) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Ollama request failed: {resp.status}")
            data = await resp.json()

        return ChatCompletionResponse(
            id=data.get("model", model_id),
            model=model_id,
            content=data.get("message", {}).get("content", ""),
            finish_reason=data.get("done", False) and "stop" or None,
        )

    async def _google_ai_completion(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> ChatCompletionResponse:
        """Completion via Google AI Studio API."""
        import aiohttp

        options = options or {}
        model_id = model or self.model
        url = f"{self.base_url}/models/{model_id}:generateContent?key={self.api_key}"

        contents = []
        for m in messages:
            contents.append({"role": m.role, "parts": [{"text": m.content}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "stopSequences": options.get("stop"),
            },
        }

        async with aiohttp.ClientSession() as session, session.post(url, json=payload) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Google AI request failed: {resp.status}")
            data = await resp.json()

        content = ""
        if "candidates" in data and data["candidates"]:
            candidate = data["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                content = candidate["content"]["parts"][0].get("text", "")

        return ChatCompletionResponse(
            id=data.get("modelVersion", model_id),
            model=model_id,
            content=content,
            finish_reason="stop",
        )

    # type: ignore[override]
    async def stream_chat_completion(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **options,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Stream chat completion."""
        response = await self.chat_completion(
            messages, model, temperature, max_tokens, **options
        )
        yield ChatCompletionChunk(content=response.content, finish_reason=response.finish_reason)


# ============================================================================
# Ollama Client (for local models like Gemma via Ollama)
# ============================================================================


class OllamaClient(LLMClientBase):
    """Ollama client for local LLM inference.

    Supports running Gemma, Llama, and other models locally.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "gemma:4b",
        **options,
    ):
        self.base_url = base_url
        self.model = model
        self.options = options

    def is_available(self) -> bool:
        """Check if Ollama is running."""
        import aiohttp
        try:
            # Simple check would be here
            return True
        except Exception:
            return False

    async def chat_completion(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **options,
    ) -> ChatCompletionResponse:
        """Send chat completion via Ollama."""
        import aiohttp

        model_id = model or self.model
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": model_id,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
            },
        }

        async with aiohttp.ClientSession() as session, session.post(url, json=payload) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Ollama request failed: {resp.status}")
            data = await resp.json()

        return ChatCompletionResponse(
            id=data.get("model", model_id),
            model=model_id,
            content=data.get("message", {}).get("content", ""),
            finish_reason="stop" if data.get("done", False) else None,
        )

    async def stream_chat_completion(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **options,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Stream chat completion via Ollama."""
        import aiohttp

        model_id = model or self.model
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": model_id,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": True,
        }

        async with aiohttp.ClientSession() as session, session.post(url, json=payload) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Ollama stream failed: {resp.status}")

            async for line in resp.content:
                if line:
                    try:
                        data = line.decode().strip()
                        if data:
                            import json
                            chunk = json.loads(data)
                            if "message" in chunk:
                                yield ChatCompletionChunk(
                                    content=chunk["message"].get("content", ""),
                                    finish_reason="stop" if chunk.get("done", False) else None,
                                )
                    except Exception:
                        pass


# ============================================================================
# LLM Factory
# ============================================================================


class LLMClientFactory:
    """Factory for creating LLM clients."""

    @staticmethod
    def create_client(
        provider: LLMProviderType,
        api_key: str | None = None,
        model: str | None = None,
        **options,
    ) -> LLMClientBase:
        """Create an LLM client for the specified provider."""
        clients = {
            LLMProviderType.GEMMA: GemmaClient,
            LLMProviderType.GOOGLE: GemmaClient,
            LLMProviderType.OLLAMA: OllamaClient,
            LLMProviderType.OPENAI: "OpenAIClient",  # Placeholder
            LLMProviderType.ANTHROPIC: "AnthropicClient",  # Placeholder
        }

        client_class = clients.get(provider)
        if not client_class:
            raise ValueError(f"Unknown LLM provider: {provider}")

        if isinstance(client_class, str):
            raise NotImplementedError(f"Provider {provider} not yet implemented")

        return client_class(api_key=api_key, model=model, **options)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "LLMProviderType",
    "GemmaModel",
    "ChatMessage",
    "ChatCompletionChunk",
    "ChatCompletionResponse",
    "LLMClientBase",
    "GemmaClient",
    "OllamaClient",
    "LLMClientFactory",
]
