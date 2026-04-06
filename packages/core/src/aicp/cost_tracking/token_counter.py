from __future__ import annotations

import re


class TokenCounter:
    @staticmethod
    def estimate_tokens(text: str) -> int:
        if not text:
            return 0
        words = len(re.findall(r"\b\w+\b", text))
        return max(1, int(words * 1.3))

    @staticmethod
    def estimate_messages_tokens(messages: list[dict[str, str]]) -> int:
        total = 0
        for message in messages:
            content = message.get("content", "")
            role = message.get("role", "")
            total += TokenCounter.estimate_tokens(content)
            total += TokenCounter.estimate_tokens(role)
        return total
