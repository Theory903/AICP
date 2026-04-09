from __future__ import annotations

from importlib import import_module

TokenCounter = import_module("aicp.cost_tracking").TokenCounter


class TestTokenCounter:
    def test_estimate_tokens(self) -> None:
        assert TokenCounter.estimate_tokens("hello world from aicp") == 5

    def test_estimate_messages_tokens(self) -> None:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Count these tokens please."},
        ]

        assert TokenCounter.estimate_messages_tokens(messages) == 13

    def test_empty_string_returns_zero(self) -> None:
        assert TokenCounter.estimate_tokens("") == 0
