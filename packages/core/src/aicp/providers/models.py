from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ModelAlias:
    alias: str
    actual_model_id: str
    provider_id: str
    pinned: bool = False


class ModelRegistry:
    def __init__(self) -> None:
        self._aliases: dict[str, list[ModelAlias]] = {}

    def register(self, alias: ModelAlias) -> None:
        self._aliases.setdefault(alias.alias, []).append(alias)

    def resolve(self, alias: str, provider_id: str) -> str:
        matches = self._aliases.get(alias, [])
        for record in matches:
            if record.provider_id == provider_id:
                return record.actual_model_id
        if matches:
            return matches[0].actual_model_id
        return alias

    def list_aliases(self, provider_id: str) -> list[str]:
        aliases: list[str] = []
        for alias_name, records in self._aliases.items():
            if any(record.provider_id == provider_id for record in records):
                aliases.append(alias_name)
        return sorted(aliases)
