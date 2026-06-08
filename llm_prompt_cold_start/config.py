from __future__ import annotations

import os
from dataclasses import dataclass

try:  # optional convenience; safe if python-dotenv is absent
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional
    pass


def _as_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    """Runtime configuration, populated from environment variables.

    Everything here is optional when running in offline mode.
    """

    model: str = "gpt-4o-mini"
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.2
    max_tokens: int = 2000
    offline: bool = False

    @classmethod
    def load(cls) -> "Settings":
        return cls(
            model=os.getenv("COLD_START_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL") or None,
            temperature=float(os.getenv("COLD_START_TEMPERATURE", "0.2")),
            max_tokens=int(os.getenv("COLD_START_MAX_TOKENS", "2000")),
            offline=_as_bool(os.getenv("COLD_START_OFFLINE")),
        )

    @property
    def can_use_llm(self) -> bool:
        """True when an online LLM call is possible and not disabled."""
        return not self.offline and bool(self.api_key)
