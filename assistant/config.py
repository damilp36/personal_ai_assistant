"""Runtime configuration for local and hosted use."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

LOCAL_OLLAMA_URL = "http://localhost:11434"


@dataclass(frozen=True)
class AppConfig:
    """Validated settings used by the Streamlit app."""

    cloud_mode: bool
    ollama_base_url: str
    ollama_api_key: str
    allowed_models: tuple[str, ...]
    access_password: str
    requests_per_minute: int
    errors: tuple[str, ...]


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _models(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        items = value.split(",")
    elif isinstance(value, (list, tuple)):
        items = value
    else:
        items = []
    return tuple(
        dict.fromkeys(str(item).strip() for item in items if str(item).strip())
    )


def load_app_config(
    secrets: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> AppConfig:
    """Load settings, giving Streamlit secrets priority over environment values."""

    secret_values = secrets or {}
    environment = environ if environ is not None else os.environ

    def value(name: str, default: Any = "") -> Any:
        if name in secret_values:
            return secret_values[name]
        return environment.get(name, default)

    cloud_mode = _as_bool(value("NOTE_TAKER_CLOUD_MODE", False))
    base_url = str(value("OLLAMA_BASE_URL", LOCAL_OLLAMA_URL)).strip()
    api_key = str(value("OLLAMA_API_KEY", "")).strip()
    allowed_models = _models(value("OLLAMA_ALLOWED_MODELS", ()))
    access_password = str(value("NOTE_TAKER_ACCESS_PASSWORD", ""))

    errors: list[str] = []
    try:
        requests_per_minute = int(value("NOTE_TAKER_REQUESTS_PER_MINUTE", 6))
    except (TypeError, ValueError):
        requests_per_minute = 6
        errors.append("NOTE_TAKER_REQUESTS_PER_MINUTE must be a number.")

    if not 1 <= requests_per_minute <= 60:
        errors.append("NOTE_TAKER_REQUESTS_PER_MINUTE must be from 1 to 60.")

    if cloud_mode:
        if not base_url.startswith("https://"):
            errors.append("Cloud mode needs an HTTPS OLLAMA_BASE_URL.")
        if not api_key:
            errors.append("Cloud mode needs OLLAMA_API_KEY.")
        if not allowed_models:
            errors.append("Cloud mode needs at least one OLLAMA_ALLOWED_MODELS entry.")
        if len(access_password) < 12:
            errors.append(
                "Cloud mode needs a NOTE_TAKER_ACCESS_PASSWORD of at least 12 characters."
            )

    return AppConfig(
        cloud_mode=cloud_mode,
        ollama_base_url=base_url,
        ollama_api_key=api_key,
        allowed_models=allowed_models,
        access_password=access_password,
        requests_per_minute=requests_per_minute,
        errors=tuple(errors),
    )
