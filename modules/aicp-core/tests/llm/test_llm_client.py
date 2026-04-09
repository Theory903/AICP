"""Tests for LLM (Gemma) client."""

from __future__ import annotations

import pytest

from aicp.llm import (
    ChatMessage,
    ChatCompletionResponse,
    LLMClientFactory,
    LLMProviderType,
)


class TestLLMClientFactory:
    def test_create_gemma_client(self) -> None:
        """Test creating Gemma client."""
        client = LLMClientFactory.create_client(
            provider=LLMProviderType.GEMMA,
            api_key="test-key",
            model="gemma-4-4b",
        )

        assert client is not None
        # Check that it's a GemmaClient instance
        assert "GemmaClient" in str(type(client))

    def test_create_ollama_client(self) -> None:
        """Test creating Ollama client."""
        client = LLMClientFactory.create_client(
            provider=LLMProviderType.OLLAMA,
            model="gemma:4b",
        )

        assert client is not None
        # Check that it's an OllamaClient instance
        assert "OllamaClient" in str(type(client))

    def test_create_client_with_options(self) -> None:
        """Test creating client with custom options."""
        client = LLMClientFactory.create_client(
            provider=LLMProviderType.GEMMA,
            api_key="test-key",
            model="gemma-4-2b",
            base_url="http://localhost:11434",
        )

        assert client is not None
        assert "GemmaClient" in str(type(client))

    def test_unknown_provider_raises(self) -> None:
        """Test that unknown provider raises ValueError."""
        with pytest.raises(ValueError, match="not a valid LLMProviderType"):
            LLMClientFactory.create_client(
                provider=LLMProviderType("unknown"),
                api_key="test",
            )


class TestChatMessage:
    def test_create_message(self) -> None:
        """Test creating a chat message."""
        msg = ChatMessage(role="user", content="Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"


class TestChatCompletionResponse:
    def test_create_response(self) -> None:
        """Test creating a chat completion response."""
        resp = ChatCompletionResponse(
            id="test-123",
            model="gemma-4-4b",
            content="Hello! How can I help?",
            finish_reason="stop",
        )

        assert resp.id == "test-123"
        assert resp.content == "Hello! How can I help?"
        assert resp.finish_reason == "stop"
