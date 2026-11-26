"""Load settings from environment variables, with validation."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

DEFAULT_MODEL = "gpt-4o-mini"


class ConfigError(Exception):
    """Raised when a setting is invalid. Messages never contain secrets."""


@dataclass(frozen=True)
class Settings:
    # repr=False keeps the key out of printed or logged Settings objects.
    openai_api_key: str | None = field(default=None, repr=False)
    openai_model: str = DEFAULT_MODEL
    timeout_seconds: float = 20.0
    max_retries: int = 2


def _read_number(env, name, default, cast, low, high):
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = cast(raw)
    except ValueError:
        raise ConfigError(f"{name} must be a number.") from None
    if not low <= value <= high:
        raise ConfigError(f"{name} must be between {low} and {high}.")
    return value


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Build Settings from env (defaults to the real environment)."""
    source = os.environ if env is None else env
    return Settings(
        openai_api_key=source.get("OPENAI_API_KEY", "").strip() or None,
        openai_model=source.get("OPENAI_MODEL", "").strip() or DEFAULT_MODEL,
        timeout_seconds=_read_number(
            source, "OPENAI_TIMEOUT_SECONDS", 20.0, float, 1, 120
        ),
        max_retries=_read_number(source, "OPENAI_MAX_RETRIES", 2, int, 0, 5),
    )
