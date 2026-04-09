from __future__ import annotations


class CostEstimator:
    _rates: dict[str, tuple[float, float]] = {
        "gpt-4": (0.03, 0.06),
        "gpt-3.5-turbo": (0.0015, 0.002),
        "claude-3-opus": (0.015, 0.075),
        "claude-3-sonnet": (0.003, 0.015),
        "claude-3-haiku": (0.00025, 0.00125),
        "gemini-pro": (0.0005, 0.0015),
        "llama-3-70b": (0.00059, 0.00079),
    }

    @classmethod
    def estimate(cls, model_id: str, tokens_in: int, tokens_out: int) -> float:
        in_rate, out_rate = cls._rates.get(model_id, (0.001, 0.002))
        return (tokens_in / 1_000_000) * in_rate + (tokens_out / 1_000_000) * out_rate

    @classmethod
    def register_rate(cls, model_id: str, in_rate: float, out_rate: float) -> None:
        cls._rates[model_id] = (in_rate, out_rate)

    @classmethod
    def list_rates(cls) -> dict[str, tuple[float, float]]:
        return dict(cls._rates)
