from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class CouncilConfig:
    models: list[str] = field(default_factory=lambda: [
        "openai/gpt-4.5",
        "google/gemini-2.0-flash",
        "anthropic/claude-sonnet-4-20250514",
    ])
    chairman_model: str = "google/gemini-2.0-flash"
    api_base: str = "https://openrouter.ai/api/v1/chat/completions"
    api_key: str | None = None
    max_retries: int = 2

    def __post_init__(self) -> None:
        if not self.models:
            raise ValueError("council requires at least one model")
        if not self.chairman_model:
            self.chairman_model = self.models[0]
        if not self.api_key:
            self.api_key = os.getenv("OPENROUTER_API_KEY")
            if not self.api_key:
                raise ValueError("OPENROUTER_API_KEY required")


@dataclass
class CouncilResponse:
    model: str
    content: str
    reasoning: str | None = None


@dataclass
class CouncilRanking:
    model: str
    evaluation: str
    parsed_ranking: list[str]


class LLMCouncil:
    def __init__(self, config: CouncilConfig) -> None:
        self.config = config
        self.client = httpx.AsyncClient(timeout=60.0)

    async def close(self) -> None:
        await self.client.aclose()

    async def _query_model(
        self,
        model: str,
        messages: list[dict[str, str]],
        retries: int = 0,
    ) -> CouncilResponse | None:
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://aicp.dev",
            "X-Title": "AICP Council",
        }
        payload = {
            "model": model,
            "messages": messages,
        }
        try:
            resp = await self.client.post(
                self.config.api_base,
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            reasoning = data["choices"][0].get("reasoning")
            return CouncilResponse(model=model, content=content, reasoning=reasoning)
        except Exception:
            if retries < self.config.max_retries:
                await asyncio.sleep(1)
                return await self._query_model(model, messages, retries + 1)
            return None

    async def query_models_parallel(
        self,
        messages: list[dict[str, str]],
    ) -> dict[str, CouncilResponse | None]:
        tasks = [
            self._query_model(model, messages)
            for model in self.config.models
        ]
        results = await asyncio.gather(*tasks)
        return {model: result for model, result in zip(self.config.models, results)}

    async def stage1_collect_responses(self, user_query: str) -> list[CouncilResponse]:
        messages = [{"role": "user", "content": user_query}]
        responses = await self.query_models_parallel(messages)
        return [r for r in responses.values() if r is not None]

    async def stage2_collect_rankings(
        self,
        user_query: str,
        stage1_results: list[CouncilResponse],
    ) -> tuple[list[CouncilRanking], dict[str, str]]:
        if not stage1_results:
            return [], {}

        labels = [f"Response {chr(65 + i)}" for i in range(len(stage1_results))]
        label_to_model = {
            label: result.model for label, result in zip(labels, stage1_results)
        }

        responses_text = "\n\n".join([
            f"{label}:\n{result.content}"
            for label, result in zip(labels, stage1_results)
        ])

        ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")

Example:

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

        messages = [{"role": "user", "content": ranking_prompt}]
        responses = await self.query_models_parallel(messages)

        rankings = []
        for model, response in responses.items():
            if response is None:
                continue
            parsed = self._parse_ranking_from_text(response.content)
            rankings.append(CouncilRanking(
                model=model,
                evaluation=response.content,
                parsed_ranking=parsed,
            ))

        return rankings, label_to_model

    def _parse_ranking_from_text(self, text: str) -> list[str]:
        match = re.search(r"FINAL RANKING:\s*\n(.+)", text, re.DOTALL)
        if not match:
            fallback = re.findall(r"Response [A-Z]", text)
            return list(dict.fromkeys(fallback))[:5]

        ranking_section = match.group(1)
        lines = ranking_section.strip().split("\n")
        parsed = []
        for line in lines:
            match = re.search(r"(\d+)\.\s*(Response [A-Z])", line)
            if match:
                parsed.append(match.group(2))
        return parsed

    def calculate_aggregate_rankings(
        self,
        rankings: list[CouncilRanking],
        label_to_model: dict[str, str],
    ) -> dict[str, float]:
        from collections import defaultdict

        if not rankings:
            return {}

        model_positions: dict[str, list[int]] = defaultdict(list)

        for ranking in rankings:
            for position, label in enumerate(ranking.parsed_ranking):
                model = label_to_model.get(label)
                if model:
                    model_positions[model].append(position)

        return {
            model: sum(positions) / len(positions)
            for model, positions in model_positions.items()
            if positions
        }

    async def stage3_synthesize_final(
        self,
        user_query: str,
        stage1_results: list[CouncilResponse],
        stage2_rankings: list[CouncilRanking],
        aggregate_rankings: dict[str, float],
    ) -> CouncilResponse:
        responses_text = "\n\n".join([
            f"Model: {r.model}\nResponse: {r.content}"
            for r in stage1_results
        ])

        rankings_text = "\n\n".join([
            f"Model: {r.model}\n{r.evaluation}"
            for r in stage2_rankings
        ])

        synthesis_prompt = f"""You are the Chairman of the LLM Council. Your role is to synthesize the best answer from multiple LLM perspectives.

Original Question: {user_query}

Individual Responses:
{responses_text}

Peer Reviews and Rankings:
{rankings_text}

Aggregate Rankings (lower position = better):
{json.dumps(aggregate_rankings, indent=2)}

Your task: Provide the final, synthesized answer that combines the best insights from all models. Cite specific models when appropriate."""

        messages = [{"role": "user", "content": synthesis_prompt}]
        result = await self._query_model(self.config.chairman_model, messages)
        return result or CouncilResponse(
            model=self.config.chairman_model,
            content="No synthesis available",
        )

    async def run_council(self, query: str) -> dict[str, Any]:
        stage1 = await self.stage1_collect_responses(query)

        stage2, label_to_model = await self.stage2_collect_rankings(query, stage1)

        aggregate = self.calculate_aggregate_rankings(stage2, label_to_model)

        stage3 = await self.stage3_synthesize_final(query, stage1, stage2, aggregate)

        return {
            "query": query,
            "stage1": [
                {"model": r.model, "response": r.content, "reasoning": r.reasoning}
                for r in stage1
            ],
            "stage2": [
                {
                    "model": r.model,
                    "evaluation": r.evaluation,
                    "parsed_ranking": r.parsed_ranking,
                }
                for r in stage2
            ],
            "stage3": {
                "model": stage3.model,
                "response": stage3.content,
            },
            "aggregate_rankings": aggregate,
            "label_to_model": label_to_model,
        }


async def run_council(query: str, config: CouncilConfig | None = None) -> dict[str, Any]:
    cfg = config or CouncilConfig()
    council = LLMCouncil(cfg)
    try:
        return await council.run_council(query)
    finally:
        await council.close()
