from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProviderCredentials(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_key: str
    organization: str | None = None
    project: str | None = None

    @field_validator("api_key", mode="before")
    @classmethod
    def _validate_api_key(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("api_key must be a string")
        normalized = value.strip()
        if not normalized:
            raise ValueError("api_key must not be empty")
        return normalized

    @field_validator("organization", "project", mode="before")
    @classmethod
    def _normalize_optional_string(cls, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("value must be a string")
        normalized = value.strip()
        return normalized or None


class ProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_key: str | None = None
    base_url: str
    timeout_seconds: int = Field(default=30, ge=1)
    max_retries: int = Field(default=3, ge=0)
    retry_delay_ms: int = Field(default=1000, ge=0)
    extra_headers: dict[str, str] = Field(default_factory=dict)

    @field_validator("api_key", "base_url", mode="before")
    @classmethod
    def _normalize_string(cls, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("value must be a string")
        normalized = value.strip()
        if value is not None and normalized == "":
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("extra_headers", mode="before")
    @classmethod
    def _validate_headers(cls, value: Any) -> dict[str, str]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("extra_headers must be a dictionary")
        normalized: dict[str, str] = {}
        for header_name, header_value in value.items():
            if not isinstance(header_name, str) or not isinstance(header_value, str):
                raise ValueError("header names and values must be strings")
            key = header_name.strip()
            val = header_value.strip()
            if not key or not val:
                raise ValueError("header names and values must not be empty")
            normalized[key] = val
        return normalized
